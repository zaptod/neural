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
from datetime import datetime
from copy import deepcopy
from typing import Optional

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
        print(f"[WorldBridge] Erro ao ler {path}: {e}")
        return deepcopy(default)


def _save_json_safe(path: str, data) -> bool:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[WorldBridge] Erro ao salvar {path}: {e}")
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
            print("[WorldBridge] World Map detectado — ponte ativa.")
        else:
            print(f"[WorldBridge] World Map não encontrado em {_WORLDMAP_DATA} — bridge desativada.")

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENTO PRINCIPAL — chamado após cada luta
    # ═══════════════════════════════════════════════════════════════════════════

    def on_fight_result(
        self,
        winner_name: str,
        loser_name: str,
        duration: float = 0.0,
        ko_type: str = "KO"
    ) -> Optional[str]:
        """
        Registra o resultado de uma luta e propaga efeitos no world map.
        Retorna o zone_id conquistado (ou None se nenhum).

        Chamado por:
          - view_luta.py   após sim.run() retornar
          - tournament_mode.py em record_match_result()
        """
        if not WORLDMAP_AVAILABLE or not winner_name:
            return None

        with self._lock_io:
            try:
                winner_god_id = self._get_god_id(winner_name)
                if not winner_god_id:
                    print(f"[WorldBridge] {winner_name} não tem god_id — sem conquista de território.")
                    return None

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
                    print(f"[WorldBridge] 🏴 {winner_name} ({winner_god_id}) conquistou '{conquered}'!")
                return conquered

            except Exception as e:
                import traceback
                print(f"[WorldBridge] Erro em on_fight_result: {e}")
                traceback.print_exc()
                return None

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
            print("[WorldBridge] Sem zonas neutras disponíveis.")
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
            except Exception:
                pass

        # Fallback: zona neutra aleatória
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
        print(f"[WorldBridge] Deus '{god_id}' adicionado ao world map.")

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
        except Exception:
            pass
