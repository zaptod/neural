from types import SimpleNamespace

from simulacao.horde_runtime import HordeWaveManager


class _DummyCollector:
    def __init__(self):
        self.names = []

    def register(self, name):
        self.names.append(name)


def _hero(nome):
    return SimpleNamespace(team_id=0, morto=False, dados=SimpleNamespace(nome=nome), vida=100, vida_max=100)


def test_horde_wave_manager_spawns_monsters_and_tracks_summary():
    sim = SimpleNamespace(
        fighters=[_hero("Astra")],
        teams={0: [_hero("Astra")]},
        rastros={},
        vida_visual={},
        _prev_z={},
        _prev_acao_ai={},
        _prev_stagger={},
        _prev_dash={},
        arena=SimpleNamespace(centro_x=15.0, centro_y=10.0, largura=30.0, altura=20.0),
        stats_collector=_DummyCollector(),
    )
    manager = HordeWaveManager(
        sim,
        {
            "label": "Teste",
            "waves": [{"label": "Wave 1", "entries": [{"monster_id": "zumbi_basico", "quantidade": 2}]}],
            "spawn_interval": 0.0,
            "inter_wave_delay": 0.1,
        },
    )

    manager.start()
    manager.update(0.016)
    manager.update(0.016)

    assert manager.total_spawned >= 2
    assert len(sim.fighters) >= 3
    assert manager.export_summary()["wave_atual"] == 1
