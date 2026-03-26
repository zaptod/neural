from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from world_map_pygame import data_loader
from world_map_pygame.history import WorldHistory
from world_map_pygame.synergy import SynergyEngine
from world_map_pygame.tools import MaterialLayer


def test_world_map_data_loader_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(data_loader, "DATA_DIR", str(tmp_path))
    payload = {"strongholds": [{"id": "sh_1"}], "world_events": [], "_meta": {"version": "2.0"}}
    assert data_loader.save_world_state(payload) is True
    assert data_loader.load_world_state() == payload


def test_material_layer_paint_and_erase() -> None:
    layer = MaterialLayer(12, 12)
    layer.paint(5, 5, 2, "fire")
    assert layer.get_at(5, 5) == "fire"
    layer.erase(5, 5, 2)
    assert layer.get_at(5, 5) == "none"


def test_world_history_records_war_event() -> None:
    history = WorldHistory(["god_a", "god_b"])
    war = history.start_war("god_a", "god_b")
    assert war is not None
    assert history.events[-1].etype == "war_declared"


def test_synergy_engine_weather_affects_units() -> None:
    engine = SynergyEngine()
    unit = SimpleNamespace(alive=True, x=5, y=5, utype="warrior", hp=100.0)
    zone = SimpleNamespace(wtype="storm", x=5, y=5, radius=4)
    world = SimpleNamespace(
        weather=SimpleNamespace(zones=[zone]),
        units=SimpleNamespace(units=[unit]),
    )

    changed = engine._weather_affects_units(1.0, world)

    assert changed is True
    assert unit.hp < 100.0
    assert unit._weather_spd < 1.0
    assert unit._weather_atk < 1.0
