from types import SimpleNamespace

import pygame

from simulacao.simulacao import FrameUpdateContext, Simulador


class _EffectStub:
    def __init__(self):
        self.vida = 1.0
        self.calls = []

    def update(self, dt):
        self.calls.append(dt)

    def atualizar(self, dt):
        self.calls.append(dt)


class _KeyState:
    def __init__(self, pressed=None):
        self.pressed = set(pressed or [])

    def __getitem__(self, key):
        return key in self.pressed


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


def test_aplicar_pressao_ritmo_runs_pipeline_in_order_when_pressure_is_active():
    sim = Simulador.__new__(Simulador)
    sim.pressao_ritmo = {"ativa": True, "intensidade": 0.3}
    sim.fighters = ["f1", "f2"]
    calls = []

    sim._calcular_hp_total_ativo = lambda: calls.append("hp") or 90.0
    sim._update_pressao_ritmo_damage_window = lambda estado, hp_total, dt: calls.append(("damage", estado, hp_total, dt))

    def _activate(estado, dt):
        calls.append(("activation", estado, dt))
        estado["ativa"] = True
        estado["intensidade"] = 0.35

    sim._update_pressao_ritmo_activation_state = _activate
    sim._reset_fighter_pressao_ritmo = lambda: calls.append("reset")
    sim._resolve_pressao_ritmo_center = lambda: calls.append("center") or (1.5, 2.5)
    sim._apply_pressao_ritmo_to_fighter = lambda fighter, intensidade, dt, cx, cy: calls.append(("fighter", fighter, intensidade, dt, cx, cy))

    sim._aplicar_pressao_ritmo(0.4)

    assert calls == [
        "hp",
        ("damage", sim.pressao_ritmo, 90.0, 0.4),
        ("activation", sim.pressao_ritmo, 0.4),
        "center",
        ("fighter", "f1", 0.35, 0.4, 1.5, 2.5),
        ("fighter", "f2", 0.35, 0.4, 1.5, 2.5),
    ]


def test_aplicar_pressao_ritmo_resets_fighters_when_pressure_is_inactive():
    sim = Simulador.__new__(Simulador)
    sim.pressao_ritmo = {"ativa": False, "intensidade": 0.0}
    sim.fighters = ["f1"]
    calls = []

    sim._calcular_hp_total_ativo = lambda: calls.append("hp") or 70.0
    sim._update_pressao_ritmo_damage_window = lambda estado, hp_total, dt: calls.append(("damage", estado, hp_total, dt))
    sim._update_pressao_ritmo_activation_state = lambda estado, dt: calls.append(("activation", estado, dt))
    sim._reset_fighter_pressao_ritmo = lambda: calls.append("reset")
    sim._resolve_pressao_ritmo_center = lambda: calls.append("center") or (0.0, 0.0)
    sim._apply_pressao_ritmo_to_fighter = lambda *args: calls.append("fighter")

    sim._aplicar_pressao_ritmo(0.2)

    assert calls == [
        "hp",
        ("damage", sim.pressao_ritmo, 70.0, 0.2),
        ("activation", sim.pressao_ritmo, 0.2),
        "reset",
    ]


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


def test_prepare_frame_update_runs_camera_transients_and_runtime_dt_pipeline():
    sim = Simulador.__new__(Simulador)
    calls = []
    frame = object()

    sim._update_runtime_camera_and_debug = lambda dt: calls.append(("camera", dt))
    sim._prepare_paused_frame = lambda dt: calls.append(("paused", dt)) or None
    sim._update_frame_transients = lambda dt: calls.append(("transients", dt))
    sim._resolve_runtime_frame_dt = lambda dt: calls.append(("frame_dt", dt)) or frame

    assert sim._prepare_frame_update(0.25) is frame
    assert calls == [
        ("camera", 0.25),
        ("paused", 0.25),
        ("transients", 0.25),
        ("frame_dt", 0.25),
    ]


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


def test_collect_pending_runtime_objects_dispatches_each_fighter_to_buffer_collector():
    sim = Simulador.__new__(Simulador)
    fighters = ["f1", "f2"]
    calls = []

    sim.fighters = fighters
    sim._collect_fighter_pending_runtime_objects = lambda fighter: calls.append(fighter)

    sim._collect_pending_runtime_objects()

    assert calls == fighters


def test_collect_fighter_pending_runtime_objects_runs_expected_buffer_pipeline():
    sim = Simulador.__new__(Simulador)
    calls = []
    fighter = object()

    sim._collect_runtime_buffer = lambda lutador, buffer_attr, target_attr: calls.append((lutador, buffer_attr, target_attr))
    sim._prepare_pending_orbs_runtime = lambda lutador: calls.append((lutador, "buffer_orbes", "prepare"))
    sim._collect_pending_summons = lambda lutador: calls.append((lutador, "buffer_summons", "summons"))

    sim._collect_fighter_pending_runtime_objects(fighter)

    assert calls == [
        (fighter, "buffer_projeteis", "projeteis"),
        (fighter, "buffer_orbes", "prepare"),
        (fighter, "buffer_areas", "areas"),
        (fighter, "buffer_beams", "beams"),
        (fighter, "buffer_summons", "summons"),
        (fighter, "buffer_traps", "traps"),
    ]


def test_update_slow_motion_state_triggers_feedback_when_timer_ends():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.slow_mo_timer = 0.05
    sim.time_scale = 0.4
    sim._play_slow_mo_end_feedback_once = lambda: calls.append("feedback")

    sim._update_slow_motion_state(0.1)

    assert sim.time_scale == 1.0
    assert calls == ["feedback"]


def test_ativar_direcao_cinematica_refreshes_existing_event_without_rebuilding():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.direcao_cinematica = {"evento_id": "evt"}
    perfil = {"tipo": "x"}

    sim._resolve_cinematic_direction_intensity = lambda payload: calls.append(("intensity", payload)) or 0.5
    sim._resolve_cinematic_direction_event_id = lambda payload, intensidade: calls.append(("event", payload, intensidade)) or "evt"
    sim._refresh_existing_cinematic_direction = lambda atual, evento_id, intensidade, payload: calls.append(("refresh", atual, evento_id, intensidade, payload)) or True
    sim._build_cinematic_direction_state = lambda *args: calls.append("build") or {}
    sim._apply_cinematic_direction_feedback = lambda *args: calls.append("feedback")

    sim._ativar_direcao_cinematica(perfil)

    assert calls == [
        ("intensity", perfil),
        ("event", perfil, 0.5),
        ("refresh", sim.direcao_cinematica, "evt", 0.5, perfil),
    ]


def test_ativar_direcao_cinematica_builds_new_state_and_feedback():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.direcao_cinematica = {}
    perfil = {"tipo": "x"}

    sim._resolve_cinematic_direction_intensity = lambda payload: calls.append(("intensity", payload)) or 0.6
    sim._resolve_cinematic_direction_event_id = lambda payload, intensidade: calls.append(("event", payload, intensidade)) or "novo"
    sim._refresh_existing_cinematic_direction = lambda *args: calls.append("refresh") or False
    sim._build_cinematic_direction_state = lambda payload, intensidade, evento_id: calls.append(("build", payload, intensidade, evento_id)) or {"evento_id": evento_id}
    sim._apply_cinematic_direction_feedback = lambda payload, intensidade: calls.append(("feedback", payload, intensidade))

    sim._ativar_direcao_cinematica(perfil)

    assert sim.direcao_cinematica == {"evento_id": "novo"}
    assert calls == [
        ("intensity", perfil),
        ("event", perfil, 0.6),
        "refresh",
        ("build", perfil, 0.6, "novo"),
        ("feedback", perfil, 0.6),
    ]


def test_handle_runtime_keydown_applies_actions_and_ui_sounds():
    sim = Simulador.__new__(Simulador)
    ui_calls = []
    sim.audio = SimpleNamespace(play_ui=lambda sound: ui_calls.append(sound))
    sim.cam = SimpleNamespace(modo="AUTO", zoom=1.0, x=0.0, y=0.0, target_zoom=1.0)
    sim.rodando = True
    sim.paused = False
    sim.show_hud = True
    sim.show_hitbox_debug = False
    sim.show_analysis = False
    sim.time_scale = 1.0
    sim.recarregar_tudo = lambda: ui_calls.append("reload")

    sim._handle_runtime_keydown(pygame.K_SPACE)
    sim._handle_runtime_keydown(pygame.K_g)
    sim._handle_runtime_keydown(pygame.K_2)
    sim._handle_runtime_keydown(pygame.K_ESCAPE)

    assert sim.paused is True
    assert sim.show_hud is False
    assert sim.cam.modo == "P2"
    assert sim.rodando is False
    assert ui_calls == ["select", "select", "select", "back"]


def test_apply_manual_camera_controls_moves_camera_and_sets_manual_mode():
    sim = Simulador.__new__(Simulador)
    sim.cam = SimpleNamespace(x=0.0, y=0.0, zoom=2.0, modo="AUTO")

    sim._apply_manual_camera_controls(_KeyState([pygame.K_w, pygame.K_d]))

    assert sim.cam.y == -7.5
    assert sim.cam.x == 7.5
    assert sim.cam.modo == "MANUAL"


def test_spawn_projectile_magic_impact_vfx_resolves_element_then_spawns():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.magic_vfx = SimpleNamespace(spawn_explosion=lambda *args, **kwargs: calls.append((args, kwargs)))
    sim._resolve_projectile_impact_element = lambda proj: "FOGO"
    proj = SimpleNamespace(x=2.0, y=3.0, dano=20)

    sim._spawn_projectile_magic_impact_vfx(proj)

    assert calls == [
        ((100.0, 150.0), {"elemento": "FOGO", "tamanho": 1.0, "dano": 20})
    ]


def test_get_projetil_elemento_prefers_direct_field_and_caches_result():
    sim = Simulador.__new__(Simulador)
    proj = SimpleNamespace(elemento="GELO")

    assert sim._get_projetil_elemento(proj) == "GELO"
    assert proj._cached_elemento == "GELO"


def test_get_projetil_elemento_resolves_keywords_when_field_is_missing():
    sim = Simulador.__new__(Simulador)
    proj = SimpleNamespace(nome="Nova de Fogo", tipo="")

    assert sim._get_projetil_elemento(proj) == "FOGO"


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


def test_update_runs_runtime_phases_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []

    def record(name, return_value=None):
        def _inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return return_value
        return _inner

    sim._prepare_frame_update = record(
        "prepare",
        FrameUpdateContext(dt=0.25, dt_efetivo=0.25, early_exit=False, reason=""),
    )
    sim._collect_pending_runtime_objects = record("collect")
    sim._update_runtime_effects = record("effects")
    sim._update_magic_vfx_runtime = record("magic_vfx")
    sim._update_projectile_phase = record("projectiles")
    sim._update_orb_phase = record("orbs")
    sim._update_area_phase = record("areas")
    sim._update_beam_phase = record("beams")
    sim._update_summon_phase = record("summons")
    sim._update_trap_phase = record("traps")
    sim._update_transformation_phase = record("transformations")
    sim._update_channel_phase = record("channels")
    sim._update_active_match_state = record("active_match")
    sim._update_post_frame_systems = record("post_frame")

    sim.update(0.25)

    assert [name for name, *_ in calls] == [
        "prepare",
        "collect",
        "effects",
        "magic_vfx",
        "projectiles",
        "orbs",
        "areas",
        "beams",
        "summons",
        "traps",
        "transformations",
        "channels",
        "active_match",
        "post_frame",
    ]
    assert calls[0][1] == (0.25,)
    assert calls[1][1] == ()
    for name, args, _kwargs in calls[2:]:
        assert args == (0.25,), name


def test_update_short_circuits_before_runtime_phases_when_prepare_frame_exits():
    sim = Simulador.__new__(Simulador)
    calls = []

    def record(name, return_value=None):
        def _inner(*args, **kwargs):
            calls.append(name)
            return return_value
        return _inner

    sim._prepare_frame_update = record(
        "prepare",
        FrameUpdateContext(dt=0.5, dt_efetivo=0.5, early_exit=True, reason="paused"),
    )
    sim._collect_pending_runtime_objects = record("collect")
    sim._update_runtime_effects = record("effects")
    sim._update_magic_vfx_runtime = record("magic_vfx")
    sim._update_projectile_phase = record("projectiles")
    sim._update_orb_phase = record("orbs")
    sim._update_area_phase = record("areas")
    sim._update_beam_phase = record("beams")
    sim._update_summon_phase = record("summons")
    sim._update_trap_phase = record("traps")
    sim._update_transformation_phase = record("transformations")
    sim._update_channel_phase = record("channels")
    sim._update_active_match_state = record("active_match")
    sim._update_post_frame_systems = record("post_frame")

    sim.update(0.5)

    assert calls == ["prepare"]


def test_recarregar_tudo_runs_reload_pipeline_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []

    def record(name):
        def _inner(*args, **kwargs):
            calls.append(name)
        return _inner

    sim._reload_match_payload = record("payload")
    sim._reset_runtime_state_for_reload = record("reset")
    sim._rebuild_runtime_match_groups = record("groups")
    sim._initialize_runtime_managers_after_reload = record("managers")
    sim._configure_arena_after_reload = record("arena")
    sim._initialize_runtime_tracking_after_reload = record("tracking")
    sim._initialize_match_services_after_reload = record("services")

    sim.recarregar_tudo()

    assert calls == ["payload", "reset", "groups", "managers", "arena", "tracking", "services"]


def test_initialize_runtime_state_defaults_runs_groups_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []

    sim._initialize_runtime_effect_state = lambda: calls.append("effects")
    sim._initialize_runtime_ui_state = lambda: calls.append("ui")
    sim._initialize_runtime_match_state = lambda: calls.append("match")
    sim._initialize_runtime_service_refs = lambda: calls.append("services")

    sim._initialize_runtime_state_defaults()

    assert calls == ["effects", "ui", "match", "services"]


def test_carregar_luta_dados_runs_team_pipeline_when_team_config_exists():
    sim = Simulador.__new__(Simulador)
    calls = []
    state = SimpleNamespace()
    config = {"teams": [{"team_id": 1}], "cenario": "Templo", "portrait_mode": True}

    sim._load_match_state_payload = lambda: calls.append("load") or (state, config)
    sim._apply_loaded_match_config = lambda runtime_config: calls.append(("apply", runtime_config))
    sim._create_match_character_resolver = lambda runtime_state: calls.append(("resolver", runtime_state)) or "montar"
    sim._resolve_match_scene_settings = lambda runtime_config: calls.append(("scene", runtime_config)) or ("Templo", True)
    sim._build_team_match_payload = lambda runtime_config, montar: calls.append(("team", runtime_config, montar)) or ("l1", "l2")
    sim._build_duel_match_payload = lambda *args: calls.append("duel") or ("x", "y")
    sim._load_duel_rival_memories = lambda *args: calls.append("memory")

    assert sim.carregar_luta_dados() == ("l1", "l2", "Templo", True)
    assert calls == [
        "load",
        ("apply", config),
        ("resolver", state),
        ("scene", config),
        ("team", config, "montar"),
    ]


def test_carregar_luta_dados_falls_back_to_duel_pipeline_when_team_payload_is_empty():
    sim = Simulador.__new__(Simulador)
    calls = []
    state = SimpleNamespace()
    config = {"p1_nome": "A", "p2_nome": "B", "cenario": "Arena", "portrait_mode": False}

    sim._load_match_state_payload = lambda: calls.append("load") or (state, config)
    sim._apply_loaded_match_config = lambda runtime_config: calls.append(("apply", runtime_config))
    sim._create_match_character_resolver = lambda runtime_state: calls.append(("resolver", runtime_state)) or "montar"
    sim._resolve_match_scene_settings = lambda runtime_config: calls.append(("scene", runtime_config)) or ("Arena", False)
    sim._build_team_match_payload = lambda runtime_config, montar: calls.append(("team", runtime_config, montar)) or None
    sim._build_duel_match_payload = lambda runtime_config, montar: calls.append(("duel", runtime_config, montar)) or ("l1", "l2")
    sim._load_duel_rival_memories = lambda l1, l2: calls.append(("memory", l1, l2))

    assert sim.carregar_luta_dados() == ("l1", "l2", "Arena", False)
    assert calls == [
        "load",
        ("apply", config),
        ("resolver", state),
        ("scene", config),
        ("team", config, "montar"),
        ("duel", config, "montar"),
        ("memory", "l1", "l2"),
    ]


def test_carregar_luta_dados_returns_safe_defaults_when_loading_fails():
    sim = Simulador.__new__(Simulador)
    sim._load_match_state_payload = lambda: (_ for _ in ()).throw(ValueError("boom"))

    assert sim.carregar_luta_dados() == (None, None, "Arena", False)


def test_update_active_match_state_runs_match_subsystems_in_order():
    sim = Simulador.__new__(Simulador)
    sim.vencedor = None
    calls = []

    def record(name):
        def _inner(*args, **kwargs):
            calls.append((name, args))
        return _inner

    sim._update_match_timer_and_victory = record("timer")
    sim._update_match_choreography = record("choreo")
    sim._update_match_fighter_runtime = record("fighters")
    sim._update_match_arena_runtime = record("arena")
    sim._finalize_match_visual_runtime = record("visual")

    sim._update_active_match_state(0.4)

    assert [name for name, _args in calls] == ["timer", "choreo", "fighters", "arena", "visual"]
    assert all(args == (0.4,) for _name, args in calls)


def test_finalize_match_visual_runtime_runs_visual_pipeline_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []

    sim._update_visual_health_runtime = lambda dt: calls.append(("health", dt))
    sim._finalize_match_motion_events = lambda: calls.append(("motion", None))

    sim._finalize_match_visual_runtime(0.3)

    assert calls == [("health", 0.3), ("motion", None)]


def test_update_visual_health_runtime_smooths_fighters_and_primary_bars():
    sim = Simulador.__new__(Simulador)
    fighter = type("FighterStub", (), {})()
    fighter.vida = 60.0
    sim.fighters = [fighter]
    sim.vida_visual = {fighter: 100.0}
    sim.p1 = SimpleNamespace(vida=80.0)
    sim.p2 = SimpleNamespace(vida=40.0)
    sim.vida_visual_p1 = 100.0
    sim.vida_visual_p2 = 20.0

    sim._update_visual_health_runtime(0.2)

    assert sim.vida_visual[fighter] == pytest.approx(60.0)
    assert sim.vida_visual_p1 == pytest.approx(80.0)
    assert sim.vida_visual_p2 == pytest.approx(40.0)


def test_processar_efeitos_arena_dispatches_each_effect_in_order():
    sim = Simulador.__new__(Simulador)
    sim.arena = SimpleNamespace(efeitos_ativos=["calor", "neblina", "chuva"])
    calls = []

    sim._process_single_arena_effect = lambda efeito, dt: calls.append((efeito, dt))

    sim._processar_efeitos_arena(0.3)

    assert calls == [("calor", 0.3), ("neblina", 0.3), ("chuva", 0.3)]


def test_process_single_arena_effect_routes_to_expected_handler():
    sim = Simulador.__new__(Simulador)
    calls = []

    sim._apply_arena_heat_effect = lambda dt: calls.append(("calor", dt))
    sim._apply_arena_slippery_effect = lambda dt: calls.append(("escorregadio", dt))
    sim._apply_arena_fog_effect = lambda: calls.append(("neblina", None))
    sim._apply_arena_rain_effect = lambda dt: calls.append(("chuva", dt))
    sim._apply_arena_dust_effect = lambda dt: calls.append(("poeira", dt))

    sim._process_single_arena_effect("calor", 0.5)
    sim._process_single_arena_effect("neve", 0.5)
    sim._process_single_arena_effect("neblina", 0.5)
    sim._process_single_arena_effect("chuva", 0.5)
    sim._process_single_arena_effect("poeira", 0.5)

    assert calls == [
        ("calor", 0.5),
        ("escorregadio", 0.5),
        ("neblina", None),
        ("chuva", 0.5),
        ("poeira", 0.5),
    ]


def test_update_area_phase_runs_cycle_and_finalize():
    sim = Simulador.__new__(Simulador)
    sim.areas = ["area_a", "area_b"]
    calls = []

    sim._run_area_updates = lambda dt: calls.append(("run", dt)) or ["nova"]
    sim._finalize_area_phase = lambda novas: calls.append(("finalize", list(novas)))

    sim._update_area_phase(0.3)

    assert calls == [("run", 0.3), ("finalize", ["nova"])]


def test_process_area_results_dispatches_each_result_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []
    area = object()
    novas = []
    resultado = [{"nova_onda": True}, {"meteoro": True}, {"pull": True}]

    sim._process_single_area_result = lambda runtime_area, res, dt, runtime_novas: calls.append((runtime_area, res, dt, runtime_novas))

    sim._process_area_results(area, resultado, 0.25, novas)

    assert calls == [
        (area, {"nova_onda": True}, 0.25, novas),
        (area, {"meteoro": True}, 0.25, novas),
        (area, {"pull": True}, 0.25, novas),
    ]


def test_process_single_area_result_routes_to_expected_handler():
    sim = Simulador.__new__(Simulador)
    calls = []
    area = object()
    novas = []

    sim._handle_area_nova_wave_result = lambda runtime_area, res, runtime_novas: calls.append(("nova", runtime_area, res, runtime_novas))
    sim._handle_area_meteor_result = lambda runtime_area, res, runtime_novas: calls.append(("meteoro", runtime_area, res, runtime_novas))
    sim._handle_area_pull_result = lambda runtime_area, res, dt: calls.append(("pull", runtime_area, res, dt))
    sim._handle_area_dot_tick_result = lambda runtime_area, res: calls.append(("dot", runtime_area, res))

    sim._process_single_area_result(area, {"nova_onda": True}, 0.1, novas)
    sim._process_single_area_result(area, {"meteoro": True}, 0.1, novas)
    sim._process_single_area_result(area, {"pull": True}, 0.1, novas)
    sim._process_single_area_result(area, {"dot_tick": True}, 0.1, novas)

    assert calls == [
        ("nova", area, {"nova_onda": True}, novas),
        ("meteoro", area, {"meteoro": True}, novas),
        ("pull", area, {"pull": True}, 0.1),
        ("dot", area, {"dot_tick": True}),
    ]


def test_process_area_collisions_dispatches_each_valid_target():
    sim = Simulador.__new__(Simulador)
    calls = []
    area = SimpleNamespace(ativo=True, ativado=True)
    alvo = object()

    sim._iter_area_collision_targets = lambda runtime_area: iter([(alvo, 1.0, 2.0, 3.0)])
    sim._apply_area_collision_hit = lambda runtime_area, runtime_alvo, dx, dy, dist: calls.append((runtime_area, runtime_alvo, dx, dy, dist))

    sim._process_area_collisions(area)

    assert calls == [(area, alvo, 1.0, 2.0, 3.0)]


def test_update_orb_phase_dispatches_each_runtime_orb():
    sim = Simulador.__new__(Simulador)
    calls = []

    sim._iter_runtime_orbs = lambda: iter(["orbe_a", "orbe_b"])
    sim._update_single_orb = lambda orbe: calls.append(orbe)

    sim._update_orb_phase(0.2)

    assert calls == ["orbe_a", "orbe_b"]


def test_update_single_orb_resolves_target_then_applies_hit():
    sim = Simulador.__new__(Simulador)
    calls = []
    alvo = object()
    orbe = SimpleNamespace(ativo=True, estado="disparando", colidir=lambda runtime_alvo: calls.append(("colidir", runtime_alvo)) or True)

    sim._resolve_orb_target = lambda runtime_orbe: calls.append(("target", runtime_orbe)) or alvo
    sim._apply_orb_hit = lambda runtime_orbe, runtime_alvo: calls.append(("hit", runtime_orbe, runtime_alvo))

    sim._update_single_orb(orbe)

    assert calls == [
        ("target", orbe),
        ("colidir", alvo),
        ("hit", orbe, alvo),
    ]


def test_update_summon_phase_runs_update_collision_and_finalize():
    sim = Simulador.__new__(Simulador)
    sim.summons = ["summon"]
    calls = []

    sim._run_summon_updates = lambda dt: calls.append(("run", dt))
    sim._process_projectile_vs_summon_phase = lambda: calls.append(("collision", None))
    sim._finalize_summon_phase = lambda: calls.append(("finalize", None))

    sim._update_summon_phase(0.15)

    assert calls == [("run", 0.15), ("collision", None), ("finalize", None)]


def test_process_projectile_vs_summon_phase_dispatches_each_projectile():
    sim = Simulador.__new__(Simulador)
    sim.projeteis = ["proj_a", "proj_b"]
    calls = []

    sim._process_single_projectile_vs_summons = lambda proj: calls.append(proj)

    sim._process_projectile_vs_summon_phase()

    assert calls == ["proj_a", "proj_b"]


def test_process_single_projectile_vs_summons_stops_after_first_collision():
    sim = Simulador.__new__(Simulador)
    proj = SimpleNamespace(ativo=True)
    summon_a = object()
    summon_b = object()
    sim.summons = [summon_a, summon_b]
    calls = []

    def _resolve(runtime_proj, summon):
        calls.append((runtime_proj, summon))
        return summon is summon_a

    sim._resolve_projectile_vs_single_summon = _resolve

    sim._process_single_projectile_vs_summons(proj)

    assert calls == [(proj, summon_a)]


def test_resolve_projectile_vs_single_summon_runs_pipeline_in_order():
    sim = Simulador.__new__(Simulador)
    owner = object()
    proj = SimpleNamespace(dono=owner)
    summon = SimpleNamespace(ativo=True, dono=object(), tomar_dano=lambda dano: {"morreu": True})
    calls = []

    sim._projectile_hits_summon = lambda runtime_proj, runtime_summon: calls.append(
        ("collide", runtime_proj, runtime_summon)
    ) or True
    sim._calcular_dano_projetil_vs_summon = lambda runtime_proj: calls.append(("damage", runtime_proj)) or 12
    sim._finalize_projectile_after_summon_hit = lambda runtime_proj: calls.append(("finalize", runtime_proj))
    sim._emit_projectile_vs_summon_feedback = lambda runtime_proj, runtime_summon, dano: calls.append(
        ("feedback", runtime_proj, runtime_summon, dano)
    )
    sim._handle_summon_damage_event = lambda evento: calls.append(("event", evento))

    resolved = sim._resolve_projectile_vs_single_summon(proj, summon)

    assert resolved is True
    assert calls == [
        ("collide", proj, summon),
        ("damage", proj),
        ("finalize", proj),
        ("feedback", proj, summon, 12),
        ("event", {"morreu": True}),
    ]


def test_run_summon_updates_dispatches_each_summon_to_single_update():
    sim = Simulador.__new__(Simulador)
    sim.summons = ["summon_a", "summon_b"]
    calls = []

    sim._update_single_summon = lambda summon, dt: calls.append((summon, dt))

    sim._run_summon_updates(0.2)

    assert calls == [("summon_a", 0.2), ("summon_b", 0.2)]


def test_update_single_summon_dispatches_each_result_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []
    summon = SimpleNamespace(atualizar=lambda dt, fighters: [{"tipo": "ataque"}, {"tipo": "aura"}, {"revive": True}])
    sim.fighters = ["f1", "f2"]

    sim._process_single_summon_result = lambda runtime_summon, res: calls.append((runtime_summon, res))

    sim._update_single_summon(summon, 0.3)

    assert calls == [
        (summon, {"tipo": "ataque"}),
        (summon, {"tipo": "aura"}),
        (summon, {"revive": True}),
    ]


def test_process_single_summon_result_routes_to_expected_handler():
    sim = Simulador.__new__(Simulador)
    calls = []
    summon = object()

    sim._handle_summon_attack_result = lambda runtime_summon, res: calls.append(("ataque", runtime_summon, res))
    sim._handle_summon_aura_result = lambda runtime_summon, res: calls.append(("aura", runtime_summon, res))
    sim._handle_summon_revive_result = lambda res: calls.append(("revive", res))

    sim._process_single_summon_result(summon, {"tipo": "ataque"})
    sim._process_single_summon_result(summon, {"tipo": "aura"})
    sim._process_single_summon_result(summon, {"revive": True})

    assert calls == [
        ("ataque", summon, {"tipo": "ataque"}),
        ("aura", summon, {"tipo": "aura"}),
        ("revive", {"revive": True}),
    ]


def test_update_beam_phase_runs_each_beam_then_finalizes():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.beams = ["beam_a", "beam_b"]

    sim._update_single_beam = lambda beam, dt: calls.append((beam, dt))
    sim._finalize_beam_phase = lambda: calls.append(("finalize", None))

    sim._update_beam_phase(0.35)

    assert calls == [("beam_a", 0.35), ("beam_b", 0.35), ("finalize", None)]


def test_update_single_beam_resolves_target_and_applies_hit():
    sim = Simulador.__new__(Simulador)
    calls = []
    alvo = object()
    beam = SimpleNamespace(ativo=True, hit_aplicado=False, atualizar=lambda dt: calls.append(("update", dt)))

    sim._resolve_beam_target = lambda runtime_beam: calls.append(("target", runtime_beam)) or alvo
    sim._beam_colide_alvo = lambda runtime_beam, runtime_alvo: calls.append(("collide", runtime_beam, runtime_alvo)) or True
    sim._apply_beam_hit = lambda runtime_beam, runtime_alvo: calls.append(("hit", runtime_beam, runtime_alvo))

    sim._update_single_beam(beam, 0.4)

    assert calls == [
        ("update", 0.4),
        ("target", beam),
        ("collide", beam, alvo),
        ("hit", beam, alvo),
    ]


def test_update_channel_phase_dispatches_each_fighter_to_single_channel_update():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.fighters = ["f1", "f2"]

    sim._update_single_channel = lambda fighter, dt: calls.append((fighter, dt))

    sim._update_channel_phase(0.5)

    assert calls == [("f1", 0.5), ("f2", 0.5)]


def test_process_single_channel_result_routes_to_expected_handler():
    sim = Simulador.__new__(Simulador)
    calls = []
    fighter = object()
    channel = object()

    sim._handle_channel_heal_result = lambda runtime_fighter, res: calls.append(("cura", runtime_fighter, res))
    sim._handle_channel_damage_result = lambda runtime_fighter, runtime_channel, res: calls.append(("dano", runtime_fighter, runtime_channel, res))

    sim._process_single_channel_result(fighter, channel, {"tipo": "cura"})
    sim._process_single_channel_result(fighter, channel, {"tipo": "dano"})

    assert calls == [
        ("cura", fighter, {"tipo": "cura"}),
        ("dano", fighter, channel, {"tipo": "dano"}),
    ]


def test_handle_channel_damage_result_runs_pipeline_in_order():
    sim = Simulador.__new__(Simulador)
    fighter = SimpleNamespace(dados=SimpleNamespace(nome="Caster"))
    channel = SimpleNamespace(nome="Beam")
    res = {"alvo": object(), "dano": 18, "efeito": "FOGO"}
    context = {"alvo": object(), "dano": 18, "efeito": "FOGO", "lutador": fighter, "channel": channel}
    calls = []

    sim._build_channel_damage_context = lambda runtime_fighter, runtime_channel, runtime_res: calls.append(
        ("context", runtime_fighter, runtime_channel, runtime_res)
    ) or context
    sim._registrar_channel_damage_stats = lambda runtime_contexto: calls.append(("stats", runtime_contexto))
    sim._apply_channel_damage = lambda runtime_contexto: calls.append(("damage", runtime_contexto)) or False
    sim._emit_channel_damage_feedback = lambda runtime_contexto, fatal: calls.append(
        ("feedback", runtime_contexto, fatal)
    )

    sim._handle_channel_damage_result(fighter, channel, res)

    assert calls == [
        ("context", fighter, channel, res),
        ("stats", context),
        ("damage", context),
        ("feedback", context, False),
    ]


def test_emit_channel_damage_feedback_registers_kill_on_fatal():
    sim = Simulador.__new__(Simulador)
    sim.textos = []
    calls = []
    alvo = SimpleNamespace(pos=[2.0, 3.0])
    contexto = {
        "alvo": alvo,
        "dano": 22,
        "efeito": "FOGO",
        "lutador": SimpleNamespace(dados=SimpleNamespace(nome="Caster")),
    }

    sim._registrar_kill = lambda runtime_alvo, killer: calls.append((runtime_alvo, killer))

    sim._emit_channel_damage_feedback(contexto, True)

    assert calls == [(alvo, "Caster")]
    assert len(sim.textos) == 1


def test_determinar_vencedor_por_tempo_routes_horde_duel_and_multi_modes():
    sim = Simulador.__new__(Simulador)

    sim.modo_partida = "horda"
    sim.horde_manager = object()
    sim._determinar_vencedor_horda_por_tempo = lambda: "horda"
    assert sim._determinar_vencedor_por_tempo() == "horda"

    sim.modo_partida = "duelo"
    sim.horde_manager = None
    sim.modo_multi = False
    sim._determinar_vencedor_duelo_por_tempo = lambda: "duelo"
    assert sim._determinar_vencedor_por_tempo() == "duelo"

    sim.modo_multi = True
    sim._determinar_vencedor_multi_por_tempo = lambda: "multi"
    assert sim._determinar_vencedor_por_tempo() == "multi"


def test_flush_match_stats_routes_known_match_in_order():
    sim = Simulador.__new__(Simulador)
    sim.stats_collector = object()
    state = object()
    calls = []

    sim._has_match_stats_to_flush = lambda: calls.append("has") or True
    sim._get_match_stats_app_state = lambda: calls.append("state") or state
    sim._resolve_match_stats_match_id = lambda runtime_state: calls.append(("match_id", runtime_state)) or 42
    sim._flush_match_stats_to_known_match = lambda match_id: calls.append(("flush", match_id))
    sim._queue_pending_match_stats = lambda runtime_state: calls.append(("queue", runtime_state))

    sim._flush_match_stats()

    assert calls == [
        "has",
        "state",
        ("match_id", state),
        ("flush", 42),
    ]


def test_flush_match_stats_queues_pending_collector_when_match_id_missing():
    from dados.app_state import AppState

    sim = Simulador.__new__(Simulador)
    sim.stats_collector = object()
    state = SimpleNamespace(_last_match_id=None, pending_stats_collector=None)
    original_get = AppState.__dict__["get"]

    try:
        AppState.get = classmethod(lambda cls: state)
        sim._flush_match_stats()
    finally:
        AppState.get = original_get

    assert state.pending_stats_collector is sim.stats_collector


def test_update_trap_phase_runs_update_collision_and_finalize():
    sim = Simulador.__new__(Simulador)
    sim.traps = ["trap"]
    calls = []

    sim._run_trap_updates = lambda dt: calls.append(("run", dt))
    sim._process_projectile_vs_trap_phase = lambda: calls.append(("collision", None))
    sim._finalize_trap_phase = lambda: calls.append(("finalize", None))

    sim._update_trap_phase(0.1)

    assert calls == [("run", 0.1), ("collision", None), ("finalize", None)]


def test_run_trap_updates_dispatches_each_trap_to_single_trap_update():
    sim = Simulador.__new__(Simulador)
    sim.traps = ["trap_a", "trap_b"]
    calls = []

    sim._update_single_trap = lambda trap, dt: calls.append((trap, dt))

    sim._run_trap_updates(0.25)

    assert calls == [("trap_a", 0.25), ("trap_b", 0.25)]


def test_update_single_trap_updates_runtime_before_processing_fighters():
    sim = Simulador.__new__(Simulador)
    calls = []
    sim.fighters = ["f1", "f2"]
    trap = SimpleNamespace(ativo=True, atualizar=lambda dt: calls.append(("atualizar", dt)))

    sim._update_single_trap_vs_fighter = lambda runtime_trap, fighter, dt: calls.append(("fighter", runtime_trap, fighter, dt))

    sim._update_single_trap(trap, 0.4)

    assert calls == [
        ("atualizar", 0.4),
        ("fighter", trap, "f1", 0.4),
        ("fighter", trap, "f2", 0.4),
    ]


def test_update_single_trap_vs_fighter_routes_wall_and_trigger_paths():
    sim = Simulador.__new__(Simulador)
    calls = []
    wall_trap = SimpleNamespace(bloqueia_movimento=True)
    trigger_trap = SimpleNamespace(bloqueia_movimento=False)
    fighter = SimpleNamespace(morto=False)

    sim._resolve_wall_trap_contact = lambda trap, lutador, dt: calls.append(("wall", trap, lutador, dt))
    sim._resolve_trigger_trap_contact = lambda trap, lutador: calls.append(("trigger", trap, lutador))

    sim._update_single_trap_vs_fighter(wall_trap, fighter, 0.3)
    sim._update_single_trap_vs_fighter(trigger_trap, fighter, 0.3)

    assert calls == [
        ("wall", wall_trap, fighter, 0.3),
        ("trigger", trigger_trap, fighter),
    ]


def test_resolve_trigger_trap_contact_runs_damage_then_feedback():
    sim = Simulador.__new__(Simulador)
    fighter = SimpleNamespace()
    trap = SimpleNamespace(tentar_trigger=lambda lutador: {"alvo": lutador, "dano": 15})
    calls = []

    sim._build_trigger_trap_contact_context = lambda runtime_trap, resultado: calls.append(
        ("context", runtime_trap, resultado)
    ) or {"trap": runtime_trap, "resultado": resultado}
    sim._apply_trigger_trap_damage = lambda contexto: calls.append(("damage", contexto)) or False
    sim._emit_trigger_trap_feedback = lambda contexto, fatal: calls.append(("feedback", contexto, fatal))

    sim._resolve_trigger_trap_contact(trap, fighter)

    assert calls == [
        ("context", trap, {"alvo": fighter, "dano": 15}),
        ("damage", {"trap": trap, "resultado": {"alvo": fighter, "dano": 15}}),
        ("feedback", {"trap": trap, "resultado": {"alvo": fighter, "dano": 15}}, False),
    ]


def test_process_projectile_vs_trap_phase_dispatches_each_projectile():
    sim = Simulador.__new__(Simulador)
    sim.projeteis = ["proj_a", "proj_b"]
    calls = []

    sim._process_single_projectile_vs_traps = lambda proj: calls.append(proj)

    sim._process_projectile_vs_trap_phase()

    assert calls == ["proj_a", "proj_b"]


def test_process_single_projectile_vs_traps_stops_after_first_collision():
    sim = Simulador.__new__(Simulador)
    proj = SimpleNamespace(ativo=True)
    trap_a = object()
    trap_b = object()
    sim.traps = [trap_a, trap_b]
    calls = []

    def _resolve(runtime_proj, trap):
        calls.append((runtime_proj, trap))
        return trap is trap_a

    sim._resolve_projectile_vs_single_trap = _resolve

    sim._process_single_projectile_vs_traps(proj)

    assert calls == [(proj, trap_a)]


def test_resolve_projectile_vs_single_trap_runs_pipeline_in_order():
    sim = Simulador.__new__(Simulador)
    proj = SimpleNamespace()
    trap = SimpleNamespace(tomar_dano=lambda dano: True)
    calls = []

    sim._projectile_can_hit_trap = lambda runtime_proj, runtime_trap: calls.append(
        ("can_hit", runtime_proj, runtime_trap)
    ) or True
    sim._calcular_dano_projetil_vs_trap = lambda runtime_proj: calls.append(("damage", runtime_proj)) or 11
    sim._finalize_projectile_after_trap_hit = lambda runtime_proj, runtime_trap: calls.append(
        ("finalize", runtime_proj, runtime_trap)
    )
    sim._emit_projectile_vs_trap_feedback = lambda runtime_proj, runtime_trap, dano: calls.append(
        ("feedback", runtime_proj, runtime_trap, dano)
    )
    sim._handle_trap_destroyed_by_projectile = lambda runtime_trap, destruida: calls.append(
        ("destroyed", runtime_trap, destruida)
    )

    resolved = sim._resolve_projectile_vs_single_trap(proj, trap)

    assert resolved is True
    assert calls == [
        ("can_hit", proj, trap),
        ("damage", proj),
        ("finalize", proj, trap),
        ("feedback", proj, trap, 11),
        ("destroyed", trap, True),
    ]


def test_update_projectile_phase_runs_clash_update_and_finalize():
    sim = Simulador.__new__(Simulador)
    calls = []

    sim._process_projectile_clash_phase = lambda: calls.append(("clash", None))
    sim._run_projectile_updates = lambda dt: calls.append(("run", dt)) or ["novo_proj"]
    sim._finalize_projectile_phase = lambda novos: calls.append(("finalize", list(novos)))

    sim._update_projectile_phase(0.2)

    assert calls == [("clash", None), ("run", 0.2), ("finalize", ["novo_proj"])]


def test_run_projectile_updates_dispatches_each_projectile_to_single_projectile_update():
    sim = Simulador.__new__(Simulador)
    sim.projeteis = ["proj_a", "proj_b"]
    calls = []

    def fake_update_single(proj, dt, novos):
        calls.append((proj, dt))
        novos.append(f"{proj}_novo")

    sim._update_single_projectile = fake_update_single

    novos = sim._run_projectile_updates(0.35)

    assert calls == [("proj_a", 0.35), ("proj_b", 0.35)]
    assert novos == ["proj_a_novo", "proj_b_novo"]


def test_update_single_projectile_runs_target_pipeline_until_hit():
    sim = Simulador.__new__(Simulador)
    sim.fighters = ["fighter_a", "fighter_b"]
    calls = []
    novos = []
    proj = SimpleNamespace(x=1.0, y=2.0, dono="owner")

    sim._call_runtime_update_with_targets = lambda runtime_obj, dt, targets: calls.append(("update", dt, list(targets))) or {"ok": True}
    sim._process_projectile_special_result = lambda runtime_obj, resultado, buffer: calls.append(("special", resultado)) or buffer.append("side_effect")
    sim._encontrar_alvo_mais_proximo = lambda x, y, dono: calls.append(("target", x, y, dono)) or "alvo"
    sim._projectile_neutralized_before_hit = lambda runtime_obj, alvo: calls.append(("neutralized", alvo)) or False
    sim._projectile_collides_with_target = lambda runtime_obj, alvo: calls.append(("collides", alvo)) or True
    sim._apply_projectile_hit = lambda runtime_obj, alvo, buffer: calls.append(("hit", alvo, list(buffer)))

    sim._update_single_projectile(proj, 0.4, novos)

    assert calls == [
        ("update", 0.4, ["fighter_a", "fighter_b"]),
        ("special", {"ok": True}),
        ("target", 1.0, 2.0, "owner"),
        ("neutralized", "alvo"),
        ("collides", "alvo"),
        ("hit", "alvo", ["side_effect"]),
    ]


def test_update_single_projectile_stops_when_projectile_is_neutralized():
    sim = Simulador.__new__(Simulador)
    sim.fighters = ["fighter_a"]
    calls = []
    proj = SimpleNamespace(x=5.0, y=6.0, dono="owner")

    sim._call_runtime_update_with_targets = lambda runtime_obj, dt, targets: None
    sim._process_projectile_special_result = lambda runtime_obj, resultado, buffer: calls.append("special")
    sim._encontrar_alvo_mais_proximo = lambda x, y, dono: calls.append("target") or "alvo"
    sim._projectile_neutralized_before_hit = lambda runtime_obj, alvo: calls.append("neutralized") or True
    sim._projectile_collides_with_target = lambda runtime_obj, alvo: calls.append("collides") or True
    sim._apply_projectile_hit = lambda runtime_obj, alvo, buffer: calls.append("hit")

    sim._update_single_projectile(proj, 0.1, [])

    assert calls == ["special", "target", "neutralized"]


def test_apply_projectile_hit_runs_subphases_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []
    proj = SimpleNamespace(ativo=True)
    alvo = SimpleNamespace()
    impacto = object()
    perfil = object()
    novos = []

    sim._create_projectile_impact_context = lambda runtime_proj, runtime_alvo: calls.append(("impacto", runtime_proj, runtime_alvo)) or impacto
    sim._apply_projectile_initial_feedback = lambda runtime_proj, runtime_impacto: calls.append(("feedback", runtime_proj, runtime_impacto))
    sim._build_projectile_damage_profile = lambda runtime_proj, runtime_alvo: calls.append(("perfil", runtime_proj, runtime_alvo)) or perfil
    sim._resolve_projectile_penetration_policy = lambda runtime_proj, runtime_alvo: calls.append(("penetracao", runtime_proj, runtime_alvo)) or True
    sim._apply_projectile_damage_and_primary_outcome = lambda runtime_proj, runtime_alvo, runtime_impacto, runtime_perfil: calls.append(("dano", runtime_proj, runtime_alvo, runtime_impacto, runtime_perfil))
    sim._apply_projectile_post_hit_effects = lambda runtime_proj, runtime_alvo, runtime_impacto, runtime_perfil, runtime_novos: calls.append(("pos", runtime_proj, runtime_alvo, runtime_impacto, runtime_perfil, runtime_novos))

    sim._apply_projectile_hit(proj, alvo, novos)

    assert calls == [
        ("impacto", proj, alvo),
        ("feedback", proj, impacto),
        ("perfil", proj, alvo),
        ("penetracao", proj, alvo),
        ("dano", proj, alvo, impacto, perfil),
        ("pos", proj, alvo, impacto, perfil, novos),
    ]


def test_apply_projectile_hit_stops_before_damage_when_penetration_policy_blocks():
    sim = Simulador.__new__(Simulador)
    calls = []
    proj = SimpleNamespace(ativo=True)
    alvo = SimpleNamespace()
    impacto = object()
    perfil = object()

    sim._create_projectile_impact_context = lambda runtime_proj, runtime_alvo: calls.append("impacto") or impacto
    sim._apply_projectile_initial_feedback = lambda runtime_proj, runtime_impacto: calls.append("feedback")
    sim._build_projectile_damage_profile = lambda runtime_proj, runtime_alvo: calls.append("perfil") or perfil
    sim._resolve_projectile_penetration_policy = lambda runtime_proj, runtime_alvo: calls.append("penetracao") or False
    sim._apply_projectile_damage_and_primary_outcome = lambda *args: calls.append("dano")
    sim._apply_projectile_post_hit_effects = lambda *args: calls.append("pos")

    sim._apply_projectile_hit(proj, alvo, [])

    assert calls == ["impacto", "feedback", "perfil", "penetracao"]


def test_build_projectile_damage_profile_runs_subphases_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []
    proj = SimpleNamespace()
    alvo = SimpleNamespace()
    perfil = SimpleNamespace(dano_final=33.0)

    sim._resolve_projectile_condition_bonus = lambda runtime_proj, runtime_alvo: calls.append(("bonus", runtime_proj, runtime_alvo)) or 1.5
    sim._resolve_projectile_elemental_reaction = lambda runtime_proj, runtime_alvo: calls.append(("reacao", runtime_proj, runtime_alvo)) or ("SURTO", "FOGO", 1.2)
    sim._finalize_projectile_damage_profile = lambda runtime_proj, bonus, nome, efeito, mult: calls.append(("finalizar", runtime_proj, bonus, nome, efeito, mult)) or perfil
    sim._apply_projectile_reaction_feedback = lambda runtime_alvo, runtime_nome: calls.append(("texto", runtime_alvo, runtime_nome))
    sim._apply_projectile_damage_tempo_feedback = lambda dano: calls.append(("tempo", dano))

    assert sim._build_projectile_damage_profile(proj, alvo) is perfil
    assert calls == [
        ("bonus", proj, alvo),
        ("reacao", proj, alvo),
        ("finalizar", proj, 1.5, "SURTO", "FOGO", 1.2),
        ("texto", alvo, "SURTO"),
        ("tempo", 33.0),
    ]


def test_apply_projectile_post_hit_effects_runs_special_subphases_in_order():
    sim = Simulador.__new__(Simulador)
    calls = []
    proj = SimpleNamespace()
    alvo = SimpleNamespace()
    impacto = object()
    perfil = object()
    novos = []

    sim._apply_projectile_lifesteal_effect = lambda runtime_proj, runtime_perfil: calls.append(("lifesteal", runtime_proj, runtime_perfil))
    sim._spawn_projectile_explosion_effect = lambda runtime_proj, runtime_impacto, runtime_perfil: calls.append(("explosao", runtime_proj, runtime_impacto, runtime_perfil))
    sim._apply_projectile_shatter_effect = lambda runtime_proj, runtime_alvo, runtime_perfil: calls.append(("shatter", runtime_proj, runtime_alvo, runtime_perfil))
    sim._apply_projectile_chain_effect = lambda runtime_proj, runtime_alvo, runtime_novos: calls.append(("chain", runtime_proj, runtime_alvo, runtime_novos))

    sim._apply_projectile_post_hit_effects(proj, alvo, impacto, perfil, novos)

    assert calls == [
        ("lifesteal", proj, perfil),
        ("explosao", proj, impacto, perfil),
        ("shatter", proj, alvo, perfil),
        ("chain", proj, alvo, novos),
    ]


def test_apply_projectile_chain_effect_runs_lookup_then_spawn():
    sim = Simulador.__new__(Simulador)
    calls = []
    proj = SimpleNamespace(chain=2, chain_count=0)
    alvo = SimpleNamespace()
    prox_alvo = object()
    novos = []

    sim._find_projectile_chain_target = lambda runtime_proj, runtime_alvo: calls.append(("find", runtime_proj, runtime_alvo)) or (prox_alvo, 3.0, 4.0)
    sim._spawn_projectile_chain_link = lambda runtime_proj, runtime_alvo, runtime_prox, dx, dy, runtime_novos: calls.append(("spawn", runtime_proj, runtime_alvo, runtime_prox, dx, dy, runtime_novos))

    sim._apply_projectile_chain_effect(proj, alvo, novos)

    assert calls == [
        ("find", proj, alvo),
        ("spawn", proj, alvo, prox_alvo, 3.0, 4.0, novos),
    ]
