from types import SimpleNamespace

from simulacao.simulacao import Simulador


class _EffectStub:
    def __init__(self):
        self.vida = 1.0
        self.calls = []

    def update(self, dt):
        self.calls.append(dt)

    def atualizar(self, dt):
        self.calls.append(dt)


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


def test_prepare_frame_update_paused_short_circuits_before_transients():
    sim = Simulador.__new__(Simulador)
    text = _EffectStub()
    shockwave = _EffectStub()
    cam_calls = []

    sim.cam = SimpleNamespace(atualizar=lambda *args, **kwargs: cam_calls.append((args, kwargs)))
    sim.p1 = SimpleNamespace()
    sim.p2 = SimpleNamespace()
    sim.fighters = []
    sim.paused = True
    sim.textos = [text]
    sim.shockwaves = [shockwave]
    sim.game_feel = None
    sim.hit_stop_timer = 0.0

    frame = sim._prepare_frame_update(0.25)

    assert frame.early_exit is True
    assert frame.reason == "paused"
    assert cam_calls
    assert text.calls == []
    assert shockwave.calls == []


def test_prepare_frame_update_game_feel_hit_stop_updates_only_visuals_after_transients():
    sim = Simulador.__new__(Simulador)
    text = _EffectStub()
    shockwave = _EffectStub()
    flash = _EffectStub()
    spark = _EffectStub()

    sim.cam = SimpleNamespace(atualizar=lambda *args, **kwargs: None)
    sim.p1 = SimpleNamespace()
    sim.p2 = SimpleNamespace()
    sim.fighters = []
    sim.paused = False
    sim.textos = [text]
    sim.shockwaves = [shockwave]
    sim.impact_flashes = [flash]
    sim.hit_sparks = [spark]
    sim.game_feel = SimpleNamespace(update=lambda dt: 0.0)
    sim.hit_stop_timer = 0.0

    frame = sim._prepare_frame_update(0.5)

    assert frame.early_exit is True
    assert frame.reason == "game_feel_hit_stop"
    assert text.calls == [0.5]
    assert shockwave.calls == [0.5]
    assert flash.calls == [0.15]
    assert spark.calls == [0.15]


def test_collect_pending_runtime_objects_moves_buffers_and_spawns_summon_vfx():
    sim = Simulador.__new__(Simulador)
    summon_calls = []
    summon = SimpleNamespace(nome="Lobo de Fogo", x=2.0, y=3.0)
    fighter = SimpleNamespace(
        buffer_projeteis=["proj"],
        buffer_orbes=["orbe"],
        buffer_areas=["area"],
        buffer_beams=["beam"],
        buffer_summons=[summon],
        buffer_traps=["trap"],
    )

    sim.fighters = [fighter]
    sim.projeteis = []
    sim.magic_vfx = SimpleNamespace(spawn_summon=lambda *args: summon_calls.append(args))

    sim._collect_pending_runtime_objects()

    assert sim.projeteis == ["proj"]
    assert sim.areas == ["area"]
    assert sim.beams == ["beam"]
    assert sim.summons == [summon]
    assert sim.traps == ["trap"]
    assert fighter.buffer_projeteis == []
    assert fighter.buffer_areas == []
    assert fighter.buffer_beams == []
    assert fighter.buffer_summons == []
    assert fighter.buffer_traps == []
    assert summon_calls == [(100.0, 150.0, "FOGO")]


def test_update_post_frame_systems_updates_animators_and_caps_particles():
    sim = Simulador.__new__(Simulador)
    movement_calls = []
    attack_calls = []

    sim.movement_anims = SimpleNamespace(update=lambda dt: movement_calls.append(dt))
    sim.attack_anims = SimpleNamespace(update=lambda dt: attack_calls.append(dt))
    sim.decals = []
    sim.particulas = [_EffectStub() for _ in range(605)]
    for particula in sim.particulas:
        particula.cor = (0, 0, 0)
        particula.tamanho = 1.0
        particula.x = 0.0
        particula.y = 0.0

    sim._update_post_frame_systems(0.2)

    assert movement_calls == [0.2]
    assert attack_calls == [0.2]
    assert len(sim.particulas) == 600
