from types import SimpleNamespace

from simulacao.simulacao import Simulador


def _make_dummy_fighter(x, y, vida=100.0):
    return SimpleNamespace(
        morto=False,
        vida=vida,
        pos=[x, y],
        vel=[0.0, 0.0],
        brain=SimpleNamespace(
            pressao_ritmo=0.0,
            tedio=0.4,
            excitacao=0.1,
            _agressividade_temp_mod=0.0,
        ),
    )


def test_pressao_ritmo_activates_after_long_stall():
    sim = Simulador.__new__(Simulador)
    sim.fighters = [_make_dummy_fighter(-4.0, 0.0), _make_dummy_fighter(4.0, 0.0)]
    sim.arena = SimpleNamespace(centro_x=0.0, centro_y=0.0)
    sim.textos = []
    sim.screen_width = 1080
    sim.screen_height = 1920

    sim._resetar_pressao_ritmo()
    sim._aplicar_pressao_ritmo(6.2)

    assert sim.pressao_ritmo["ativa"] is True
    assert sim.pressao_ritmo["intensidade"] > 0.2
    assert sim.fighters[0].brain.pressao_ritmo > 0.0
    assert sim.fighters[0].vel[0] > 0.0
    assert sim.fighters[1].vel[0] < 0.0


def test_pressao_ritmo_resets_on_damage_event():
    sim = Simulador.__new__(Simulador)
    sim.fighters = [_make_dummy_fighter(-2.0, 0.0, vida=40.0), _make_dummy_fighter(2.0, 0.0, vida=40.0)]
    sim.arena = SimpleNamespace(centro_x=0.0, centro_y=0.0)
    sim.textos = []
    sim.screen_width = 1080
    sim.screen_height = 1920
    sim.pressao_ritmo = {
        "ativa": True,
        "intensidade": 0.6,
        "tempo_sem_dano": 9.0,
        "tempo_ativo": 2.0,
        "ultimo_hp_total": 100.0,
        "ultimo_evento": 1.0,
    }

    sim._aplicar_pressao_ritmo(0.1)

    assert sim.pressao_ritmo["ativa"] is False
    assert sim.pressao_ritmo["intensidade"] == 0.0
    assert sim.fighters[0].brain.pressao_ritmo == 0.0
