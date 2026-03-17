"""
NEURAL FIGHTS — WorldBridge
============================
Ponte de dados entre o sistema de luta/torneio e o World Map (pygame).

Quando uma luta termina, o vencedor conquista território para seu deus.
Os resultados são gravados em world_map_pygame/data/world_state.json e
world_map_pygame/data/gods.json em tempo real.

Uso:
    from data.world_bridge import WorldBridge
    WorldBridge.get().on_fight_result(winner_name, loser_name, duration, ko_type)

Também expõe leitura do estado do mapa para a UI Tkinter:
    WorldBridge.get().get_god_standings()  → list[dict]
    WorldBridge.get().get_territory_count(god_id) → int
"""

import json
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy
from typing import Optional, List
import logging
_log = logging.getLogger("world_bridge")


# ── GodEntry — objeto simples usado por view_chars.py ──────────────────────────
class GodEntry:
    """
    Representação de um deus para a UI de criação de personagens.
    Atributos são mutáveis para que view_chars.py possa editar antes de salvar.
    """
    def __init__(self, data: dict):
        self.god_id          = data.get("god_id", "")
        self.god_name        = data.get("god_name", self.god_id)
        self.nature          = data.get("nature", "Balanced")
        self.nature_element  = data.get("nature_element", "balanced")
        self.color_primary   = data.get("color_primary", "#00d9ff")
        self.follower_count  = data.get("follower_count", 0)
        self.owned_zones     = data.get("owned_zones", [])
        self.lore_description = data.get("lore_description", "")
        self.source          = data.get("source", "")

    def to_dict(self) -> dict:
        return {
            "god_id":           self.god_id,
            "god_name":         self.god_name,
            "nature":           self.nature,
            "nature_element":   self.nature_element,
            "color_primary":    self.color_primary,
            "follower_count":   self.follower_count,
            "owned_zones":      self.owned_zones,
            "lore_description": self.lore_description,
            "source":           self.source,
        }


# ── B04: Resultado explícito de on_fight_result ─────────────────────────────
@dataclass
class BridgeResult:
    """
    Retorno estruturado de WorldBridge.on_fight_result().

    Atributos:
        ok      — True se a operação foi executada (mesmo sem conquistar zona).
        zone_id — ID da zona conquistada, ou None se nenhuma disponível.
        reason  — Descrição legível do resultado (para logs/debug).

    Exemplos:
        res = WorldBridge.get().on_fight_result(winner, loser, dur, ko)
        if res.ok and res.zone_id:
            print(f"Conquistou {res.zone_id}")
        elif not res.ok:
            print(f"Bridge inativa: {res.reason}")
    """
    ok: bool
    zone_id: Optional[str]
    reason: str

# ── path bootstrap ─────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))         # data/
_NEURAL  = os.path.dirname(_HERE)                              # neural_v3_rework/
_ROOT    = os.path.dirname(_NEURAL)                            # projeto1.0/
_WORLDMAP_DATA = os.path.join(_ROOT, "world_map_pygame", "data")

# Verifica se o módulo world map existe
WORLDMAP_AVAILABLE = os.path.isdir(_WORLDMAP_DATA)


def _wm_path(filename: str) -> str:
    return os.path.join(_WORLDMAP_DATA, filename)


def _load_json_safe(path: str, default) -> dict:
    if not os.path.exists(path):
        return deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        _log.error("Erro ao ler %s: %s", path, e)
        return deepcopy(default)


def _save_json_safe(path: str, data) -> bool:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        _log.error("Erro ao salvar %s: %s", path, e)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
class WorldBridge:
    """
    Singleton que sincroniza resultados de luta com o World Map.
    Thread-safe via lock.
    """
    _instance: "WorldBridge | None" = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> "WorldBridge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls.__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self):
        self._lock_io = threading.Lock()
        if WORLDMAP_AVAILABLE:
            _log.info("World Map detectado — ponte ativa.")
        else:
            _log.warning("World Map não encontrado em %s — bridge desativada.", _WORLDMAP_DATA)

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENTO PRINCIPAL — chamado após cada luta
    # ═══════════════════════════════════════════════════════════════════════════

    def on_fight_result(
        self,
        winner_name: str,
        loser_name: str,
        duration: float = 0.0,
        ko_type: str = "KO"
    ) -> "BridgeResult":
        """
        Registra o resultado de uma luta e propaga efeitos no world map.
        Retorna BridgeResult com ok=True/False e zone_id conquistado (ou None).

        Chamado por:
          - view_luta.py   após sim.run() retornar
          - tournament_mode.py em record_match_result()
        """
        # B04: retornos explícitos em vez de None para tudo
        if not WORLDMAP_AVAILABLE:
            return BridgeResult(ok=False, zone_id=None, reason="worldmap indisponível")
        if not winner_name:
            return BridgeResult(ok=False, zone_id=None, reason="winner_name vazio")

        with self._lock_io:
            try:
                winner_god_id = self._get_god_id(winner_name)
                if not winner_god_id:
                    _log.warning("%s não tem god_id — sem conquista de território.", winner_name)
                    return BridgeResult(ok=True, zone_id=None, reason=f"{winner_name} sem god_id")

                # Garante que o deus existe no gods.json do worldmap
                self._ensure_god_in_worldmap(winner_god_id)

                # Conquista uma zona neutra
                conquered = self._claim_territory(winner_god_id)

                # Atualiza follower_count
                self._add_follower(winner_god_id)

                # Registra evento no world_state
                self._log_world_event({
                    "type": "territory_conquered",
                    "god_id": winner_god_id,
                    "champion": winner_name,
                    "defeated": loser_name,
                    "zone_id": conquered,
                    "duration": round(duration, 2),
                    "ko_type": ko_type,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # Também notifica AppState para quem escuta
                self._notify_app_state(winner_god_id, conquered)

                if conquered:
                    _log.info("🏴 %s (%s) conquistou '%s'!", winner_name, winner_god_id, conquered)
                    return BridgeResult(ok=True, zone_id=conquered, reason="território conquistado")
                else:
                    return BridgeResult(ok=True, zone_id=None, reason="sem zonas neutras disponíveis")

            except Exception as e:
                _log.exception("Erro em on_fight_result: %s", e)
                return BridgeResult(ok=False, zone_id=None, reason=f"exceção: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # LEITURA — para a UI Tkinter
    # ═══════════════════════════════════════════════════════════════════════════

    def get_god_standings(self) -> list:
        """
        Retorna lista de deuses com contagem de territórios e seguidores,
        ordenada por territórios (decrescente).
        Usada pela TelaWorldMap no Tkinter.
        """
        if not WORLDMAP_AVAILABLE:
            return []

        ws  = _load_json_safe(_wm_path("world_state.json"),  {})
        gds = _load_json_safe(_wm_path("gods.json"),         {"gods": []})

        ownership = ws.get("zone_ownership", {})

        # Conta territórios por deus
        territory_count: dict[str, int] = {}
        for zone_id, god_id in ownership.items():
            if god_id:
                territory_count[god_id] = territory_count.get(god_id, 0) + 1

        standings = []
        for g in gds.get("gods", []):
            gid = g["god_id"]
            standings.append({
                "god_id":       gid,
                "god_name":     g.get("god_name", gid),
                "nature":       g.get("nature_element", g.get("nature", "balanced")),
                "color":        g.get("color_primary", "#00d9ff"),
                "followers":    g.get("follower_count", 0),
                "territories":  territory_count.get(gid, 0),
            })

        standings.sort(key=lambda x: (x["territories"], x["followers"]), reverse=True)
        return standings

    def get_territory_count(self, god_id: str) -> int:
        if not WORLDMAP_AVAILABLE:
            return 0
        ws = _load_json_safe(_wm_path("world_state.json"), {})
        ownership = ws.get("zone_ownership", {})
        return sum(1 for v in ownership.values() if v == god_id)

    def get_total_zones(self) -> int:
        if not WORLDMAP_AVAILABLE:
            return 0
        ws = _load_json_safe(_wm_path("world_state.json"), {})
        return len(ws.get("zone_ownership", {}))

    def get_recent_events(self, limit: int = 8) -> list:
        """Retorna os eventos mais recentes registrados no world_state."""
        if not WORLDMAP_AVAILABLE:
            return []
        ws = _load_json_safe(_wm_path("world_state.json"), {})
        events = ws.get("world_events", [])
        return list(reversed(events[-limit:]))

    def get_all_gods(self) -> List[GodEntry]:
        """
        Retorna lista de todos os deuses como GodEntry.
        Usado por view_chars.py para o passo de seleção de divindade.
        """
        if not WORLDMAP_AVAILABLE:
            return []
        gds = _load_json_safe(_wm_path("gods.json"), {"gods": []})
        return [GodEntry(g) for g in gds.get("gods", [])]

    def get_god(self, god_id: str) -> Optional[GodEntry]:
        """
        Retorna um GodEntry pelo god_id, ou None se não encontrado.
        Usado por view_chars.py para exibir o deus vinculado atual.
        """
        if not WORLDMAP_AVAILABLE or not god_id:
            return None
        gds = _load_json_safe(_wm_path("gods.json"), {"gods": []})
        for g in gds.get("gods", []):
            if g.get("god_id") == god_id:
                return GodEntry(g)
        return None

    def create_god(self, god_name: str, nature: str, nature_element: str,
                   source: str = "manual") -> GodEntry:
        """
        Cria um novo deus no gods.json do worldmap e retorna GodEntry.
        Usado por view_chars.py no wizard de criação de deus.
        """
        import re
        # Gera god_id a partir do nome (snake_case sem acentos)
        god_id = re.sub(r'\W+', '_', god_name.lower()).strip('_') or "deus_desconhecido"
        # Garante unicidade
        gds = _load_json_safe(_wm_path("gods.json"), {"gods": []})
        existing = {g["god_id"] for g in gds.get("gods", [])}
        base_id, n = god_id, 2
        while god_id in existing:
            god_id = f"{base_id}_{n}"
            n += 1

        entry_data = {
            "god_id":           god_id,
            "god_name":         god_name,
            "nature":           nature,
            "nature_element":   nature_element,
            "color_primary":    "#00d9ff",
            "follower_count":   0,
            "owned_zones":      [],
            "lore_description": "",
            "source":           source,
            "registered_at":    datetime.utcnow().isoformat(),
        }
        gds.setdefault("gods", []).append(entry_data)
        _save_json_safe(_wm_path("gods.json"), gds)
        _log.info("Deus '%s' (%s) criado via UI.", god_name, god_id)
        return GodEntry(entry_data)

    def save_all(self):
        """
        Persiste alterações feitas em GodEntry de volta ao gods.json.
        view_chars.py chama este método após editar follower_count e lore_description.

        Nota: como GodEntry é uma cópia em memória, este método precisa da lista
        completa. Por isso view_chars.py deve usar o padrão:
            god = sync.create_god(...)
            god.follower_count = N
            sync.update_god(god)   ← usar update_god ao invés de save_all
        save_all() é mantido como no-op para não quebrar código existente.
        """
        pass  # WorldBridge salva atomicamente em cada operação — save_all é no-op

    def update_god(self, entry: GodEntry):
        """
        Atualiza os dados de um GodEntry existente no gods.json.
        Use após modificar atributos de um GodEntry retornado por create_god() ou get_god().
        """
        if not WORLDMAP_AVAILABLE:
            return
        gds = _load_json_safe(_wm_path("gods.json"), {"gods": []})
        for i, g in enumerate(gds.get("gods", [])):
            if g.get("god_id") == entry.god_id:
                gds["gods"][i] = entry.to_dict()
                break
        _save_json_safe(_wm_path("gods.json"), gds)

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVADOS
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_god_id(self, char_name: str) -> Optional[str]:
        """Busca god_id do personagem via AppState."""
        try:
            if _NEURAL not in sys.path:
                sys.path.insert(0, _NEURAL)
            from data.app_state import AppState
            char = AppState.get().get_character(char_name)
            return char.god_id if char else None
        except Exception:
            return None

    def _claim_territory(self, god_id: str) -> Optional[str]:
        """
        Escolhe e reivindica uma zona neutra para o deus.
        Prioriza zonas vizinhas a territórios já controlados.
        """
        ws = _load_json_safe(_wm_path("world_state.json"), {"zone_ownership": {}})
        ownership = ws.get("zone_ownership", {})

        already_owned = [z for z, g in ownership.items() if g == god_id]
        neutral_zones = [z for z, g in ownership.items() if g is None]

        if not neutral_zones:
            _log.warning("Sem zonas neutras disponíveis.")
            return None

        # Tenta encontrar zona vizinha (adjacente ao domínio atual)
        target_zone = None
        if already_owned:
            try:
                wr = _load_json_safe(_wm_path("world_regions.json"), {"regions": []})
                neighbor_map: dict[str, list] = {}
                for reg in wr.get("regions", []):
                    for z in reg.get("zones", []):
                        neighbor_map[z["zone_id"]] = z.get("neighboring_zones", [])

                for owned in already_owned:
                    for neighbor in neighbor_map.get(owned, []):
                        if neighbor in neutral_zones:
                            target_zone = neighbor
                            break
                    if target_zone:
                        break
            except Exception as _e:
                _log.warning("Erro ao calcular zona adjacente: %s", _e)
        if not target_zone:
            import random
            target_zone = random.choice(neutral_zones)

        # Aplica a conquista
        ownership[target_zone] = god_id
        ws["zone_ownership"] = ownership
        ws.setdefault("_meta", {})["last_updated"] = datetime.utcnow().isoformat()
        _save_json_safe(_wm_path("world_state.json"), ws)

        return target_zone

    def _ensure_god_in_worldmap(self, god_id: str):
        """
        Garante que o deus existe em world_map_pygame/data/gods.json.
        Se não existir, cria entrada a partir do gods.json do game.
        """
        gds = _load_json_safe(_wm_path("gods.json"), {"gods": [], "ancient_gods": []})
        existing_ids = {g["god_id"] for g in gds.get("gods", [])}

        if god_id in existing_ids:
            return

        # Busca no gods.json do game
        game_gods_path = os.path.join(_HERE, "gods.json")
        game_gods = _load_json_safe(game_gods_path, {"gods": {}})

        # O game usa dict; o worldmap usa list
        game_god = game_gods.get("gods", {}).get(god_id)

        if game_god:
            nature = game_god.get("nature", "balanced").lower()
            # Mapa de nature display → nature_element
            nature_map = {
                "balance": "balanced", "fire": "fire", "ice": "ice",
                "darkness": "darkness", "nature": "nature", "chaos": "chaos",
                "void": "void", "greed": "greed", "fear": "fear",
                "arcane": "arcane", "blood": "blood",
            }
            nature_elem = nature_map.get(nature, nature)
            color_tuple = game_god.get("color", [0, 217, 255])
            color_hex = "#{:02x}{:02x}{:02x}".format(*color_tuple) if isinstance(color_tuple, list) else "#00d9ff"
            new_entry = {
                "god_id":          god_id,
                "god_name":        game_god.get("name", god_id),
                "nature":          nature.capitalize(),
                "nature_element":  nature_elem,
                "color_primary":   color_hex,
                "follower_count":  game_god.get("followers", 0),
                "owned_zones":     [],
                "lore_description": "",
                "source": "game_sync",
                "registered_at": datetime.utcnow().isoformat(),
            }
        else:
            new_entry = {
                "god_id":         god_id,
                "god_name":       god_id,
                "nature":         "Balanced",
                "nature_element": "balanced",
                "color_primary":  "#00d9ff",
                "follower_count": 0,
                "owned_zones":    [],
                "lore_description": "",
                "source": "auto_created",
                "registered_at": datetime.utcnow().isoformat(),
            }

        gds.setdefault("gods", []).append(new_entry)
        _save_json_safe(_wm_path("gods.json"), gds)
        _log.info("Deus '%s' adicionado ao world map.", god_id)

    def _add_follower(self, god_id: str):
        """Incrementa follower_count do deus no worldmap gods.json."""
        gds = _load_json_safe(_wm_path("gods.json"), {"gods": []})
        for g in gds.get("gods", []):
            if g["god_id"] == god_id:
                g["follower_count"] = g.get("follower_count", 0) + 1
                break
        _save_json_safe(_wm_path("gods.json"), gds)

    def _log_world_event(self, event: dict):
        """Adiciona evento ao histórico no world_state.json."""
        ws = _load_json_safe(_wm_path("world_state.json"), {})
        ws.setdefault("world_events", []).append(event)
        # Mantém apenas os últimos 100 eventos
        ws["world_events"] = ws["world_events"][-100:]
        _save_json_safe(_wm_path("world_state.json"), ws)

    def _notify_app_state(self, god_id: str, zone_id: Optional[str]):
        """Notifica AppState sobre a conquista de território."""
        try:
            if _NEURAL not in sys.path:
                sys.path.insert(0, _NEURAL)
            from data.app_state import AppState
            if zone_id:
                AppState.get().claim_territory(zone_id, zone_id.replace("_", " ").title(), god_id)
        except Exception as _e:
            _log.warning("Erro ao notificar AppState sobre território: %s", _e)
