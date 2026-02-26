"""
NEURAL FIGHTS — AppState (Central Store)
=========================================
Single source of truth for the entire application.

Architecture:
  AppState (singleton)
    ├── weapons:          list[Arma]
    ├── characters:       list[Personagem]
    ├── match_config:     dict
    ├── tournament_state: dict
    ├── gods:             dict  (Neural Fights world state)
    └── session_stats:    dict

Usage:
    from data.app_state import AppState
    state = AppState.get()

    # Read
    weapons = state.weapons
    chars   = state.characters

    # Write (auto-saves to disk + notifies all subscribers)
    state.set_weapons(my_list)
    state.set_characters(my_list)
    state.update_match_config(p1="Caleb", p2="Bjorn")

    # Subscribe to changes
    state.subscribe("weapons_changed", my_callback)
    state.subscribe("characters_changed", my_callback)
    state.subscribe("match_config_changed", my_callback)
    state.subscribe("tournament_changed", my_callback)
    state.subscribe("gods_changed", my_callback)
    state.subscribe("any", my_callback)   # wildcard

    # Unsubscribe
    state.unsubscribe("weapons_changed", my_callback)
"""

import json
import os
import sys
import threading
from copy import deepcopy
from typing import Callable, Any

# ── path bootstrap ────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from models import Personagem, Arma

# ── File paths ────────────────────────────────────────────────────────────────
DATA_DIR          = _HERE
FILE_CHARS        = os.path.join(DATA_DIR, "personagens.json")
FILE_WEAPONS      = os.path.join(DATA_DIR, "armas.json")
FILE_MATCH        = os.path.join(DATA_DIR, "match_config.json")
FILE_TOURNAMENT   = os.path.join(DATA_DIR, "tournament_state.json")
FILE_GODS         = os.path.join(DATA_DIR, "gods.json")

# ── Default values ────────────────────────────────────────────────────────────
DEFAULT_MATCH_CONFIG = {
    "p1_nome": "",
    "p2_nome": "",
    "cenario": "Arena",
    "best_of": 1,
}

DEFAULT_TOURNAMENT_STATE = {
    "name": "Campeonato Neural Fights",
    "participants": [],
    "state": "waiting",
    "champion": None,
    "current_round": 0,
    "current_match": 0,
    "bracket": [],
    "stats": {
        "total_fights": 0,
        "total_kos": 0,
        "fastest_ko": None,
        "longest_fight": None,
        "most_aggressive": None,
    },
}

DEFAULT_GODS_STATE = {
    "gods": {},          # god_id → { name, nature, color, followers, territories }
    "territories": {},   # territory_id → { name, owner_god_id, visual_theme }
    "world_events": [],  # timeline of god actions
}


# ═══════════════════════════════════════════════════════════════════════════════
class AppState:
    """
    Singleton central store.  All data lives here.
    Views subscribe to events; mutations auto-persist to disk.
    """

    _instance: "AppState | None" = None
    _lock = threading.Lock()

    # ── Singleton access ──────────────────────────────────────────────────────
    @classmethod
    def get(cls) -> "AppState":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls.__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    @classmethod
    def reset(cls):
        """Force re-creation (useful for tests)."""
        with cls._lock:
            cls._instance = None

    # ── Private init ──────────────────────────────────────────────────────────
    def _init(self):
        self._weapons:    list[Arma]       = []
        self._characters: list[Personagem] = []
        self._match:      dict             = deepcopy(DEFAULT_MATCH_CONFIG)
        self._tournament: dict             = deepcopy(DEFAULT_TOURNAMENT_STATE)
        self._gods:       dict             = deepcopy(DEFAULT_GODS_STATE)
        self._session:    dict             = {
            "total_fights": 0,
            "total_kos": 0,
            "fight_log": [],
        }

        # event_name → list[callback]
        self._subscribers: dict[str, list[Callable]] = {}

        self._load_all()

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC — Data Access (read)
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def weapons(self) -> list[Arma]:
        return self._weapons

    @property
    def characters(self) -> list[Personagem]:
        return self._characters

    @property
    def match_config(self) -> dict:
        return deepcopy(self._match)

    @property
    def tournament_state(self) -> dict:
        return deepcopy(self._tournament)

    @property
    def gods(self) -> dict:
        return deepcopy(self._gods)

    @property
    def session_stats(self) -> dict:
        return deepcopy(self._session)

    # ── Convenience lookups ───────────────────────────────────────────────────

    def get_character(self, name: str) -> "Personagem | None":
        return next((p for p in self._characters if p.nome == name), None)

    def get_weapon(self, name: str) -> "Arma | None":
        return next((a for a in self._weapons if a.nome == name), None)

    def get_weapon_for_character(self, char: "Personagem") -> "Arma | None":
        return self.get_weapon(char.nome_arma) if char.nome_arma else None

    def get_characters_by_god(self, god_id: str) -> list[Personagem]:
        return [p for p in self._characters if p.god_id == god_id]

    def character_names(self) -> list[str]:
        return [p.nome for p in self._characters]

    def weapon_names(self) -> list[str]:
        return [a.nome for a in self._weapons]

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC — Mutations (write → auto-save → notify)
    # ═══════════════════════════════════════════════════════════════════════════

    # ── Weapons ───────────────────────────────────────────────────────────────

    def set_weapons(self, weapons: list[Arma]):
        """Replace the full weapons list."""
        self._weapons = list(weapons)
        self._save_weapons()
        self._notify("weapons_changed", self._weapons)

    def add_weapon(self, weapon: Arma):
        self._weapons.append(weapon)
        self._save_weapons()
        self._notify("weapons_changed", self._weapons)

    def update_weapon(self, index: int, weapon: Arma):
        if 0 <= index < len(self._weapons):
            self._weapons[index] = weapon
            self._save_weapons()
            self._notify("weapons_changed", self._weapons)

    def delete_weapon(self, index: int):
        if 0 <= index < len(self._weapons):
            del self._weapons[index]
            self._save_weapons()
            self._notify("weapons_changed", self._weapons)

    def delete_weapon_by_name(self, name: str):
        idx = next((i for i, a in enumerate(self._weapons) if a.nome == name), None)
        if idx is not None:
            self.delete_weapon(idx)

    # ── Characters ────────────────────────────────────────────────────────────

    def set_characters(self, characters: list[Personagem]):
        """Replace the full characters list."""
        self._characters = list(characters)
        self._save_characters()
        self._notify("characters_changed", self._characters)

    def add_character(self, character: Personagem):
        self._characters.append(character)
        self._save_characters()
        self._notify("characters_changed", self._characters)

    def update_character(self, index: int, character: Personagem):
        if 0 <= index < len(self._characters):
            self._characters[index] = character
            self._save_characters()
            self._notify("characters_changed", self._characters)

    def delete_character(self, index: int):
        if 0 <= index < len(self._characters):
            del self._characters[index]
            self._save_characters()
            self._notify("characters_changed", self._characters)

    def delete_character_by_name(self, name: str):
        idx = next((i for i, p in enumerate(self._characters) if p.nome == name), None)
        if idx is not None:
            self.delete_character(idx)

    def set_character_god(self, char_name: str, god_id: "str | None"):
        """Assign or remove a god allegiance from a character."""
        for p in self._characters:
            if p.nome == char_name:
                p.god_id = god_id
                break
        self._save_characters()
        self._notify("characters_changed", self._characters)
        self._notify("gods_changed", self._gods)

    # ── Match Config ──────────────────────────────────────────────────────────

    def update_match_config(self, **kwargs):
        """
        Update one or more match config fields.
        e.g. state.update_match_config(p1_nome="Caleb", cenario="Forest")
        """
        self._match.update(kwargs)
        self._save_match()
        self._notify("match_config_changed", self._match)

    def set_match_config(self, config: dict):
        self._match = {**DEFAULT_MATCH_CONFIG, **config}
        self._save_match()
        self._notify("match_config_changed", self._match)

    # ── Tournament State ──────────────────────────────────────────────────────

    def set_tournament_state(self, state: dict):
        self._tournament = deepcopy(state)
        self._save_tournament()
        self._notify("tournament_changed", self._tournament)

    def update_tournament(self, **kwargs):
        self._tournament.update(kwargs)
        self._save_tournament()
        self._notify("tournament_changed", self._tournament)

    def record_fight_result(self, winner: str, loser: str, duration: float, ko: bool):
        """Append a fight result to tournament stats and session log."""
        self._session["total_fights"] += 1
        if ko:
            self._session["total_kos"] += 1
        self._session["fight_log"].append({
            "winner": winner, "loser": loser,
            "duration": duration, "ko": ko,
        })
        stats = self._tournament.get("stats", {})
        stats["total_fights"] = stats.get("total_fights", 0) + 1
        if ko:
            stats["total_kos"] = stats.get("total_kos", 0) + 1
        if duration is not None:
            fastest = stats.get("fastest_ko")
            if ko and (fastest is None or duration < fastest):
                stats["fastest_ko"] = duration
            longest = stats.get("longest_fight")
            if longest is None or duration > longest:
                stats["longest_fight"] = duration
        self._tournament["stats"] = stats
        self._save_tournament()
        self._notify("tournament_changed", self._tournament)
        self._notify("session_stats_changed", self._session)

    # ── Gods / World State (Neural Fights Lore) ───────────────────────────────

    def register_god(self, god_id: str, name: str, nature: str,
                     color: tuple = (255, 255, 255), followers: int = 0):
        self._gods["gods"][god_id] = {
            "name": name,
            "nature": nature,
            "color": color,
            "followers": followers,
            "territories": [],
        }
        self._save_gods()
        self._notify("gods_changed", self._gods)

    def claim_territory(self, territory_id: str, territory_name: str, god_id: str,
                        visual_theme: dict = None):
        """A god claims a territory on the 3D Atlas."""
        self._gods["territories"][territory_id] = {
            "name": territory_name,
            "owner_god_id": god_id,
            "visual_theme": visual_theme or {},
        }
        god = self._gods["gods"].get(god_id)
        if god and territory_id not in god.get("territories", []):
            god.setdefault("territories", []).append(territory_id)
        self._gods["world_events"].append({
            "type": "territory_claimed",
            "god_id": god_id,
            "territory_id": territory_id,
        })
        self._save_gods()
        self._notify("gods_changed", self._gods)
        self._notify("territory_changed", {
            "territory_id": territory_id,
            "god_id": god_id,
        })

    def add_world_event(self, event: dict):
        self._gods["world_events"].append(event)
        self._save_gods()
        self._notify("gods_changed", self._gods)

    # ── Force full reload from disk ───────────────────────────────────────────

    def reload_all(self):
        """Re-read all JSON files from disk. Notifies all channels."""
        self._load_all()
        self._notify("weapons_changed",       self._weapons)
        self._notify("characters_changed",    self._characters)
        self._notify("match_config_changed",  self._match)
        self._notify("tournament_changed",    self._tournament)
        self._notify("gods_changed",          self._gods)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC — Event Bus
    # ═══════════════════════════════════════════════════════════════════════════

    def subscribe(self, event: str, callback: Callable):
        """
        Register a callback for an event.
        Use event="any" to receive all events.
        """
        self._subscribers.setdefault(event, [])
        if callback not in self._subscribers[event]:
            self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        if event in self._subscribers:
            try:
                self._subscribers[event].remove(callback)
            except ValueError:
                pass

    def unsubscribe_all(self, callback: Callable):
        """Remove a callback from every event it was subscribed to."""
        for listeners in self._subscribers.values():
            if callback in listeners:
                listeners.remove(callback)

    # ═══════════════════════════════════════════════════════════════════════════
    # PRIVATE — I/O
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_all(self):
        self._weapons    = self._load_weapons()
        self._characters = self._load_characters()
        self._match      = self._load_json(FILE_MATCH,      DEFAULT_MATCH_CONFIG)
        self._tournament = self._load_json(FILE_TOURNAMENT, DEFAULT_TOURNAMENT_STATE)
        self._gods       = self._load_json(FILE_GODS,       DEFAULT_GODS_STATE)

    # ── Loaders ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_json(path: str, default: dict) -> dict:
        if not os.path.exists(path):
            return deepcopy(default)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge missing top-level keys from default
            merged = deepcopy(default)
            merged.update(data)
            return merged
        except Exception as e:
            print(f"[AppState] Warning loading {path}: {e}")
            return deepcopy(default)

    def _load_weapons(self) -> list[Arma]:
        if not os.path.exists(FILE_WEAPONS):
            return []
        try:
            with open(FILE_WEAPONS, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return [Arma(**item) for item in raw]
        except Exception as e:
            print(f"[AppState] Warning loading weapons: {e}")
            return []

    def _load_characters(self) -> list[Personagem]:
        if not os.path.exists(FILE_CHARS):
            return []
        try:
            with open(FILE_CHARS, "r", encoding="utf-8") as f:
                raw_chars = json.load(f)
            # Build weapon-weight lookup from in-memory weapons (already loaded)
            weapon_weights = {a.nome: a.peso for a in self._weapons}
            result = []
            for item in raw_chars:
                nome_arma  = item.get("nome_arma", "")
                peso_arma  = weapon_weights.get(nome_arma, 0)
                p = Personagem(
                    item["nome"], item["tamanho"], item["forca"], item["mana"],
                    nome_arma, peso_arma,
                    item.get("cor_r", 200), item.get("cor_g", 50), item.get("cor_b", 50),
                    item.get("classe", "Guerreiro (Força Bruta)"),
                    item.get("personalidade", "Aleatório"),
                    item.get("god_id", None),
                )
                result.append(p)
            return result
        except Exception as e:
            print(f"[AppState] Warning loading characters: {e}")
            return []

    # ── Savers ────────────────────────────────────────────────────────────────

    def _save_weapons(self):
        self._write_json(FILE_WEAPONS, [a.to_dict() for a in self._weapons])

    def _save_characters(self):
        self._write_json(FILE_CHARS, [p.to_dict() for p in self._characters])

    def _save_match(self):
        self._write_json(FILE_MATCH, self._match)

    def _save_tournament(self):
        self._write_json(FILE_TOURNAMENT, self._tournament)

    def _save_gods(self):
        self._write_json(FILE_GODS, self._gods)

    @staticmethod
    def _write_json(path: str, data):
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(tmp, path)          # atomic rename — no corrupt files
        except Exception as e:
            print(f"[AppState] Error saving {path}: {e}")

    # ── Internal notify ───────────────────────────────────────────────────────

    def _notify(self, event: str, data: Any = None):
        # Specific subscribers
        for cb in list(self._subscribers.get(event, [])):
            try:
                cb(data)
            except Exception as e:
                print(f"[AppState] Subscriber error on '{event}': {e}")
        # Wildcard subscribers
        for cb in list(self._subscribers.get("any", [])):
            try:
                cb(event, data)
            except Exception as e:
                print(f"[AppState] Wildcard subscriber error: {e}")

    # ── Debug ─────────────────────────────────────────────────────────────────

    def __repr__(self):
        return (
            f"<AppState  weapons={len(self._weapons)}"
            f"  characters={len(self._characters)}"
            f"  gods={len(self._gods.get('gods', {}))}"
            f"  match={self._match.get('p1_nome')} vs {self._match.get('p2_nome')}>"
        )
