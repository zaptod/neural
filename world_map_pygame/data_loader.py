"""
World Map — Data Loader
JSON I/O helpers for world state, gods, and game integration.
"""
import json, os
try:
    from .config import DATA_DIR, NEURAL_DIR
except ImportError:  # pragma: no cover - direct script fallback
    from config import DATA_DIR, NEURAL_DIR


def _load(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default.copy() if isinstance(default, dict) else default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[DataLoader] read error {path}: {e}")
        return default.copy() if isinstance(default, dict) else default


def _save(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[DataLoader] write error {path}: {e}")
        return False


def load_world_state():
    p = os.path.join(DATA_DIR, "world_state.json")
    return _load(p, {"strongholds": [], "world_events": [],
                      "_meta": {"version": "2.0"}})

def save_world_state(data):
    return _save(os.path.join(DATA_DIR, "world_state.json"), data)

def load_gods():
    return _load(os.path.join(DATA_DIR, "gods.json"), {"gods": []})

def save_gods(data):
    return _save(os.path.join(DATA_DIR, "gods.json"), data)

def load_game_gods():
    """Load god definitions from the combat game."""
    return _load(os.path.join(NEURAL_DIR, "data", "gods.json"), {"gods": {}})
