"""Runtime-focused regression tests for active AI flow."""

import random
from types import SimpleNamespace

import pytest

from ia.brain import AIBrain
from ia.skill_strategy import SkillProfile
from nucleo.entities import Lutador
from modelos import Arma, Personagem
from simulacao.sim_combat import (
    AttackImpactVector,
    AttackKnockbackResolution,
    AttackPreparationContext,
    ChainAttackResolution,
    DamageTextFeedback,
    DefensiveTempoFeedback,
    GameFeelHitResolution,
    PreparedHitResolution,
    SimuladorCombat,
)
from utilitarios.config import AMARELO_FAISCA, BRANCO, PPM


def _make_fighter(nome, weapon_type="Espada Reta", family=None, team_id=0, x=0.0, y=0.0):
    arma = Arma(
        nome=f"{weapon_type} de Teste",
        tipo=weapon_type,
        familia=family,
        dano=8,
        peso=2,
        velocidade_ataque=1.0,
    )
    dados = Personagem(
        nome=nome,
        tamanho=1.5,
        forca=5.0,
        mana=5.0,
        classe="Guerreiro (ForÃƒÂ§a Bruta)",
    )
    dados.recalcular_com_arma(arma)
    return Lutador(dados, x, y, team_id=team_id)


@pytest.fixture(autouse=True)
def _stable_random_seed():
    state = random.getstate()
    random.seed(12345)
    try:
        yield
    finally:
        random.setstate(state)


def _make_sim_stub():
    cam = SimpleNamespace(
        x=0.0,
        aplicar_shake=lambda *args, **kwargs: None,
    )
    return SimpleNamespace(
        audio=None,
        cam=cam,
        block_effects=[],
        textos=[],
        particulas=[],
        impact_flashes=[],
        shockwaves=[],
        hit_sparks=[],
        hit_stop_timer=0.0,
        time_scale=1.0,
        slow_mo_timer=0.0,
    )


def _make_combat_harness():
    sim = SimuladorCombat()
    sim.audio = None
    sim.cam = SimpleNamespace(
        x=0.0,
        aplicar_shake=lambda *args, **kwargs: None,
        zoom_punch=lambda *args, **kwargs: None,
    )
    sim.block_effects = []
    sim.textos = []
    sim.particulas = []
    sim.projeteis = []
    sim.impact_flashes = []
    sim.magic_clashes = []
    sim.shockwaves = []
    sim.hit_sparks = []
    sim.dash_trails = []
    sim.hit_stop_timer = 0.0
    sim.time_scale = 1.0
    sim.slow_mo_timer = 0.0
    sim.game_feel = None
    sim.choreographer = None
    sim.attack_anims = None
    sim.p1 = None
    sim.p2 = None
    sim.vencedor = None
    sim.spawn_particulas = lambda *args, **kwargs: None
    sim._criar_knockback_visual = lambda *args, **kwargs: None
    sim.ativar_slow_motion = lambda: None
    return sim


class _StatsCollectorSpy:
    def __init__(self):
        self.attempts = []
        self.hits = []
        self.deaths = []
        self.blocks = []
        self.dodges = []

    def record_attack_attempt(self, *args, **kwargs):
        self.attempts.append((args, kwargs))

    def record_hit(self, *args, **kwargs):
        self.hits.append((args, kwargs))

    def record_death(self, *args, **kwargs):
        self.deaths.append((args, kwargs))

    def record_block(self, *args, **kwargs):
        self.blocks.append((args, kwargs))

    def record_dodge(self, *args, **kwargs):
        self.dodges.append((args, kwargs))


def test_combat_helper_blocks_direct_hitbox_for_ranged_types():
    sim = _make_sim_stub()

    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="Arremesso")) is False
    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="Arco")) is False
    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="MÃ¡gica")) is False
    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="Reta")) is True


def test_brain_init_runs_setup_groups_before_generating_personality():
    brain = AIBrain.__new__(AIBrain)
    parent = SimpleNamespace(vida=77.0)
    calls = []

    brain._initialize_runtime_decision_state = lambda: calls.append("decision")
    brain._initialize_emotional_state = lambda: calls.append("emotions")
    brain._initialize_combat_memory_state = lambda runtime_parent: calls.append(("memory", runtime_parent))
    brain._initialize_personality_state = lambda: calls.append("personality")
    brain._initialize_internal_cooldowns_and_skill_state = lambda: calls.append("cooldowns")
    brain._initialize_choreography_state = lambda: calls.append("choreo")
    brain._initialize_human_behavior_state = lambda: calls.append("human")
    brain._initialize_spatial_and_weapon_awareness_state = lambda: calls.append("spatial")
    brain._initialize_multi_combat_state = lambda: calls.append("multi")
    brain._initialize_update_group_timers = lambda: calls.append("timers")
    brain._gerar_personalidade = lambda: calls.append("generate")

    AIBrain.__init__(brain, parent)

    assert brain.parent is parent
    assert calls == [
        "decision",
        "emotions",
        ("memory", parent),
        "personality",
        "cooldowns",
        "choreo",
        "human",
        "spatial",
        "multi",
        "timers",
        "generate",
    ]


def test_brain_init_smoke_populates_grouped_default_state():
    fighter = _make_fighter("Astra")
    brain = fighter.brain

    assert brain.acao_atual == "NEUTRO"
    assert brain.humor == "CALMO"
    assert brain.tempo_desde_dano == 5.0
    assert isinstance(brain.skills_por_tipo["PROJETIL"], list)
    assert brain.memoria_oponente["adaptacao_por_oponente"] == {}
    assert brain.leitura_oponente["reposicionando"] is False
    assert brain.multi_awareness["melhor_alvo"] is None
    assert brain.team_orders["role"] == "STRIKER"


def test_brain_processar_runs_pipeline_in_order_until_finalize():
    brain = AIBrain.__new__(AIBrain)
    enemy = SimpleNamespace(nome="Dummy")
    fighters = [SimpleNamespace(nome="A"), SimpleNamespace(nome="B")]
    calls = []

    brain._prepare_processar_frame = lambda dt, distancia, inimigo: calls.append(
        ("prepare", dt, distancia, inimigo)
    )
    brain._prepare_processar_random_and_debug = lambda distancia: calls.append(("random", distancia))
    brain._update_processar_team_and_awareness = (
        lambda dt, distancia, inimigo, todos: calls.append(("team", dt, distancia, inimigo, todos))
    )
    brain._update_processar_runtime_groups = lambda dt, distancia, inimigo: calls.append(
        ("runtime", dt, distancia, inimigo)
    )

    def _interruptions(dt, distancia, inimigo):
        calls.append(("interruptions", dt, distancia, inimigo))
        return False

    def _combat_priority(dt, distancia, inimigo):
        calls.append(("combat", dt, distancia, inimigo))
        return False

    brain._run_processar_interruptions = _interruptions
    brain._resolve_processar_combat_priority = _combat_priority
    brain._finalize_processar_frame = lambda dt, distancia, inimigo: calls.append(
        ("finalize", dt, distancia, inimigo)
    )

    AIBrain.processar(brain, 0.25, 42.0, enemy, fighters)

    assert calls == [
        ("prepare", 0.25, 42.0, enemy),
        ("random", 42.0),
        ("team", 0.25, 42.0, enemy, fighters),
        ("runtime", 0.25, 42.0, enemy),
        ("interruptions", 0.25, 42.0, enemy),
        ("combat", 0.25, 42.0, enemy),
        ("finalize", 0.25, 42.0, enemy),
    ]


def test_brain_processar_stops_when_interruptions_handle_frame():
    brain = AIBrain.__new__(AIBrain)
    calls = []

    brain._prepare_processar_frame = lambda *args: calls.append("prepare")
    brain._prepare_processar_random_and_debug = lambda *args: calls.append("random")
    brain._update_processar_team_and_awareness = lambda *args: calls.append("team")
    brain._update_processar_runtime_groups = lambda *args: calls.append("runtime")
    brain._run_processar_interruptions = lambda *args: calls.append("interruptions") or True
    brain._resolve_processar_combat_priority = lambda *args: calls.append("combat") or False
    brain._finalize_processar_frame = lambda *args: calls.append("finalize")

    AIBrain.processar(brain, 0.1, 10.0, SimpleNamespace(), [])

    assert calls == ["prepare", "random", "team", "runtime", "interruptions"]


def test_brain_processar_stops_when_combat_priority_handles_frame():
    brain = AIBrain.__new__(AIBrain)
    calls = []

    brain._prepare_processar_frame = lambda *args: calls.append("prepare")
    brain._prepare_processar_random_and_debug = lambda *args: calls.append("random")
    brain._update_processar_team_and_awareness = lambda *args: calls.append("team")
    brain._update_processar_runtime_groups = lambda *args: calls.append("runtime")
    brain._run_processar_interruptions = lambda *args: calls.append("interruptions") or False
    brain._resolve_processar_combat_priority = lambda *args: calls.append("combat") or True
    brain._finalize_processar_frame = lambda *args: calls.append("finalize")

    AIBrain.processar(brain, 0.1, 10.0, SimpleNamespace(), [])

    assert calls == ["prepare", "random", "team", "runtime", "interruptions", "combat"]


def test_brain_processar_team_and_awareness_only_updates_multi_when_fighters_present():
    brain = AIBrain.__new__(AIBrain)
    enemy = SimpleNamespace(nome="Boss")
    fighters = [SimpleNamespace(nome="A"), SimpleNamespace(nome="B")]
    calls = []

    brain._atualizar_multi_awareness = lambda dt, inimigo, todos: calls.append(
        ("multi", dt, inimigo, todos)
    )
    brain._aplicar_team_orders = lambda dt, distancia, inimigo, todos: calls.append(
        ("orders", dt, distancia, inimigo, todos)
    )

    AIBrain._update_processar_team_and_awareness(brain, 0.1, 12.0, enemy, None)
    AIBrain._update_processar_team_and_awareness(brain, 0.2, 8.0, enemy, fighters)

    assert calls == [
        ("orders", 0.1, 12.0, enemy, None),
        ("multi", 0.2, enemy, fighters),
        ("orders", 0.2, 8.0, enemy, fighters),
    ]


def test_brain_multi_awareness_runs_pipeline_in_order():
    brain = AIBrain.__new__(AIBrain)
    enemy = SimpleNamespace(nome="Boss")
    fighters = [SimpleNamespace(nome="A"), SimpleNamespace(nome="B")]
    calls = []

    brain._limpar_multi_awareness_contatos = lambda: calls.append("clear")
    brain._coletar_entidades_multi_awareness = lambda todos: calls.append(("collect", todos))
    brain._atualizar_resumo_multi_awareness = lambda: calls.append("summary")
    brain._calcular_ameaca_flanqueio_multi_awareness = lambda: calls.append("flank")
    brain._calcular_concentracao_inimiga_multi_awareness = lambda: calls.append("cluster")
    brain._detectar_aliado_perto_do_alvo_multi_awareness = lambda inimigo: calls.append(("ally-near", inimigo))
    brain._detectar_aliado_no_caminho_multi_awareness = lambda inimigo: calls.append(("friendly-fire", inimigo))
    brain._selecionar_melhor_alvo_multi_awareness = lambda inimigo: calls.append(("target", inimigo))

    AIBrain._atualizar_multi_awareness(brain, 0.16, enemy, fighters)

    assert calls == [
        "clear",
        ("collect", fighters),
        "summary",
        "flank",
        "cluster",
        ("ally-near", enemy),
        ("friendly-fire", enemy),
        ("target", enemy),
    ]


def test_brain_multi_awareness_collects_entities_and_derived_flags():
    observer = _make_fighter("Observer", team_id=0, x=0.0, y=0.0)
    ally = _make_fighter("Ally", team_id=0, x=2.0, y=0.0)
    enemy_a = _make_fighter("EnemyA", team_id=1, x=4.0, y=0.0)
    enemy_b = _make_fighter("EnemyB", team_id=1, x=-4.0, y=0.0)
    enemy_a.vida = enemy_a.vida_max * 0.2

    observer.brain._atualizar_multi_awareness(0.016, enemy_a, [observer, ally, enemy_a, enemy_b])
    awareness = observer.brain.multi_awareness

    assert len(awareness["inimigos"]) == 2
    assert len(awareness["aliados"]) == 1
    assert awareness["num_inimigos_vivos"] == 2
    assert awareness["num_aliados_vivos"] == 1
    assert awareness["modo_multialvo"] is True
    assert awareness["em_desvantagem_numerica"] is False
    assert awareness["ameaca_flanqueio"] == pytest.approx(1.0)
    assert awareness["concentracao_inimiga"] > 0.5
    assert awareness["aliado_perto_alvo"] is True
    assert awareness["aliado_no_caminho"] is True
    assert awareness["melhor_alvo"] is enemy_a


def test_brain_multi_awareness_falls_back_to_principal_target_without_enemies():
    observer = _make_fighter("Observer", team_id=0, x=0.0, y=0.0)
    ally = _make_fighter("Ally", team_id=0, x=1.5, y=0.0)
    principal = SimpleNamespace(pos=[5.0, 0.0])

    observer.brain._atualizar_multi_awareness(0.016, principal, [observer, ally])
    awareness = observer.brain.multi_awareness

    assert awareness["inimigos"] == []
    assert awareness["aliados"][0]["lutador"] is ally
    assert awareness["melhor_alvo"] is principal


def test_brain_team_orders_runs_pipeline_in_order_when_active():
    brain = AIBrain.__new__(AIBrain)
    brain.team_orders = {
        "alive_count": 2,
        "role": "SUPPORT",
        "tactic": "FOCUS_FIRE",
        "package_role": "defensor",
        "modo_horda": True,
    }
    calls = []

    brain._team_orders_estao_inativos = lambda orders: calls.append(("inactive-check", orders["alive_count"])) or False
    brain._aplicar_agressividade_por_role_team_orders = lambda dt, role: calls.append(("role", dt, role))
    brain._aplicar_ajustes_emocionais_por_tatica_team_orders = (
        lambda dt, role, tactic, orders: calls.append(("tactic", dt, role, tactic, orders["alive_count"]))
    )
    brain._aplicar_ajustes_modo_horda_team_orders = (
        lambda dt, package_role, modo_horda, orders: calls.append(
            ("horde", dt, package_role, modo_horda, orders["alive_count"])
        )
    )
    brain._aplicar_ajustes_desvantagem_numerica_team_orders = (
        lambda dt, orders: calls.append(("numbers", dt, orders["alive_count"]))
    )
    brain._aplicar_resposta_a_callouts_team_orders = (
        lambda role, orders: calls.append(("callouts", role, orders["alive_count"]))
    )
    brain._aplicar_sinergias_team_orders = lambda role, orders: calls.append(("synergy", role, orders["alive_count"]))
    brain._aplicar_posicionamento_relativo_team_orders = (
        lambda role, orders: calls.append(("position", role, orders["alive_count"]))
    )

    AIBrain._aplicar_team_orders(brain, 0.25, 4.0, SimpleNamespace(), [])

    assert calls == [
        ("inactive-check", 2),
        ("role", 0.25, "SUPPORT"),
        ("tactic", 0.25, "SUPPORT", "FOCUS_FIRE", 2),
        ("horde", 0.25, "defensor", True, 2),
        ("numbers", 0.25, 2),
        ("callouts", "SUPPORT", 2),
        ("synergy", "SUPPORT", 2),
        ("position", "SUPPORT", 2),
    ]


def test_brain_team_orders_returns_without_active_team_context():
    brain = AIBrain.__new__(AIBrain)
    brain.team_orders = {"alive_count": 1}
    calls = []

    brain._team_orders_estao_inativos = lambda orders: calls.append("inactive") or True
    brain._aplicar_agressividade_por_role_team_orders = lambda *args: calls.append("role")

    AIBrain._aplicar_team_orders(brain, 0.25, 4.0, SimpleNamespace(), [])

    assert calls == ["inactive"]


def test_brain_team_orders_support_help_callout_adjusts_state():
    fighter = _make_fighter("Support", team_id=0, x=0.0, y=0.0)
    brain = fighter.brain
    brain._agressividade_temp_mod = 0.0
    brain.confianca = 0.2
    brain.raiva = 0.1
    brain.impulso = 0.0
    brain.team_orders.update(
        {
            "alive_count": 2,
            "role": "SUPPORT",
            "tactic": "FULL_AGGRO",
            "callouts": [{"type": "HELP"}],
            "synergies": [],
            "team_center": (0.0, 0.0),
        }
    )

    brain._aplicar_team_orders(0.5, 3.0, None, [])

    assert brain._agressividade_temp_mod < 0.0
    assert brain.confianca > 0.2
    assert brain.raiva > 0.1
    assert brain.impulso == pytest.approx(0.1)


def test_brain_team_orders_cc_burst_striker_enters_burst_mode():
    striker = _make_fighter("Striker", team_id=0, x=0.0, y=0.0)
    partner = _make_fighter("Controller", team_id=0, x=1.0, y=0.0)
    brain = striker.brain
    brain._agressividade_temp_mod = 0.0
    brain.modo_burst = False
    brain.team_orders.update(
        {
            "alive_count": 2,
            "role": "STRIKER",
            "tactic": "FOCUS_FIRE",
            "synergies": [
                SimpleNamespace(tipo="cc_burst", fighter_a_id=id(striker), fighter_b_id=id(partner))
            ],
            "ally_intents": {
                id(partner): SimpleNamespace(skill_name="Prender Alvo")
            },
            "team_center": (0.0, 0.0),
        }
    )

    brain._aplicar_team_orders(0.1, 2.0, None, [striker, partner])

    assert brain.modo_burst is True
    assert brain._agressividade_temp_mod > 0.0


def test_brain_prefer_skills_runs_pipeline_in_order():
    brain = AIBrain.__new__(AIBrain)
    enemy = SimpleNamespace(nome="Enemy")
    calls = []
    context = {"familia": "foco"}

    brain._coletar_contexto_preferencia_skills = lambda distancia, inimigo: calls.append(
        ("context", distancia, inimigo)
    ) or context
    brain._resolver_baseline_preferencia_skills = lambda ctx: calls.append(("baseline", ctx)) or False
    brain._aplicar_familia_preferencia_skills = lambda ctx, prefer: calls.append(
        ("family", ctx, prefer)
    ) or True
    brain._aplicar_tatica_time_preferencia_skills = lambda ctx, prefer: calls.append(
        ("tactic", ctx, prefer)
    ) or prefer
    brain._aplicar_janelas_e_pacotes_preferencia_skills = lambda ctx, prefer: calls.append(
        ("windows", ctx, prefer)
    ) or prefer
    brain._aplicar_adaptacao_preferencia_skills = lambda ctx, prefer: calls.append(
        ("adaptive", ctx, prefer)
    ) or prefer

    result = AIBrain._preferir_skills_neste_frame(brain, 3.5, enemy)

    assert result is True
    assert calls == [
        ("context", 3.5, enemy),
        ("baseline", context),
        ("family", context, False),
        ("tactic", context, True),
        ("windows", context, True),
        ("adaptive", context, True),
    ]


def test_brain_prefer_skills_context_aggregates_runtime_state():
    fighter = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=4.0, y=0.0)
    brain = fighter.brain

    fighter.mana_max = 100.0
    fighter.mana = 40.0
    fighter.vida_max = 120.0
    fighter.vida = 90.0
    fighter.alcance_ideal = 5.5
    brain.arquetipo_composto = {"pacote_referencia": {"id": "mago_teste"}}
    brain.team_orders.update({"role": "ARTILLERY", "tactic": "KITE_AND_POKE"})
    brain._calcular_vies_skill_adaptativo = lambda: 0.2
    brain._obter_vies_oponente = lambda inimigo: {
        "vies_skill": 0.3,
        "vies_cautela": 0.1,
        "vies_agressao": 0.2,
    }
    brain._calcular_postura_risco_adaptativa = lambda distancia, inimigo: -0.4

    context = brain._coletar_contexto_preferencia_skills(4.0, enemy)

    assert context["parent"] is fighter
    assert context["arma"] is fighter.dados.arma_obj
    assert context["familia"] == "foco"
    assert context["pacote_id"] == "mago_teste"
    assert context["mana_pct"] == pytest.approx(0.4)
    assert context["team_role"] == "ARTILLERY"
    assert context["team_tactic"] == "KITE_AND_POKE"
    assert context["hp_pct"] == pytest.approx(0.75)
    assert context["alcance_ideal"] == pytest.approx(5.5)
    assert context["vies_skill_adaptativo"] == pytest.approx(0.2 + 0.3 * 0.42 + 0.1 * 0.10 - 0.2 * 0.12)
    assert context["postura_risco"] == pytest.approx(-0.4)
    assert context["distancia"] == pytest.approx(4.0)
    assert context["inimigo"] is enemy


def test_brain_target_score_runs_pipeline_in_order():
    brain = AIBrain.__new__(AIBrain)
    enemy = SimpleNamespace(nome="Enemy")
    info = {"lutador": enemy, "vida_pct": 0.4, "distancia": 2.0, "ameaca": 0.7}
    calls = []

    brain._score_execucao_alvo = lambda current: calls.append(("execute", current)) or 1.5
    brain._score_proximidade_alvo = lambda current: calls.append(("distance", current)) or 0.5
    brain._score_ameaca_e_memoria_alvo = lambda current: calls.append(("memory", current)) or 2.0
    brain._score_interceptacao_alvo = lambda lutador: calls.append(("intercept", lutador)) or 1.0
    brain._score_alvo_designado_time = lambda lutador: calls.append(("primary", lutador)) or 2.5
    brain._score_targeting_por_role_alvo = lambda lutador: calls.append(("role", lutador)) or 0.75
    brain._score_penalidade_overkill_alvo = lambda lutador: calls.append(("overkill", lutador)) or -0.5

    score = AIBrain._score_alvo(brain, info)

    assert score == pytest.approx(7.75)
    assert calls == [
        ("execute", info),
        ("distance", info),
        ("memory", info),
        ("intercept", enemy),
        ("primary", enemy),
        ("role", enemy),
        ("overkill", enemy),
    ]


def test_brain_rivalry_pressure_maps_profile_from_dominant_relation():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.0, y=0.0)

    fighter.brain._registrar_aprendizado_oponente(enemy, "relacao_vinganca", 0.55)

    pressao = fighter.brain._calcular_pressao_rivalidade(enemy)

    assert pressao["dominante"] == "vinganca"
    assert pressao["perfil"] == "revanche"
    assert pressao["intensidade"] >= 0.55


def test_decay_of_opponent_memory_removes_inert_non_current_bucket():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain.memoria_oponente["adaptacao_por_oponente"] = {
        "old": {
            "vies_skill": 0.005,
            "vies_agressao": 0.004,
            "vies_cautela": 0.003,
            "vies_pressao": 0.002,
            "vies_contra_ataque": 0.001,
            "relacao_respeito": 0.02,
            "relacao_vinganca": 0.01,
            "relacao_obsessao": 0.0,
            "relacao_caca": 0.0,
            "padroes": {},
            "ultimo_evento": "velho",
        }
    }
    fighter.brain.memoria_oponente["id_atual"] = "current"

    fighter.brain._decair_memoria_curta_oponentes(0.5)

    assert fighter.brain.memoria_oponente["adaptacao_por_oponente"] == {}


def test_combat_helper_tracks_repeated_targets_inside_same_attack():
    sim = _make_sim_stub()
    defensor = object()
    atacante = SimpleNamespace(alvos_atingidos_neste_ataque=set())

    assert SimuladorCombat._ja_acertou_alvo_neste_ataque(sim, atacante, defensor) is False

    SimuladorCombat._marcar_alvo_atingido_neste_ataque(sim, atacante, defensor)

    assert SimuladorCombat._ja_acertou_alvo_neste_ataque(sim, atacante, defensor) is True


def test_combat_helper_breaks_weapon_and_applies_damage_penalty_once():
    sim = _make_sim_stub()
    atacante = SimpleNamespace(pos=[2.0, 3.0])
    arma = SimpleNamespace(durabilidade=0.25)

    dano = SimuladorCombat._aplicar_desgaste_durabilidade_arma(sim, atacante, arma, 20.0, is_critico=False)

    assert dano == pytest.approx(10.0)
    assert arma.durabilidade == 0.0
    assert arma._aviso_quebrada_exibido is True
    assert len(sim.textos) == 1


def test_combat_helper_chicote_sweet_spot_applies_crack_and_interrupt():
    sim = _make_combat_harness()
    atacante = SimpleNamespace(pos=[0.0, 0.0], raio_fisico=1.0)
    defensor = SimpleNamespace(
        pos=[4.5, 0.0],
        atacando=True,
        cooldown_ataque=0.0,
        stun_timer=0.0,
        slow_timer=0.0,
        slow_fator=1.0,
        vel=[0.0, 0.0],
        dots_ativos=[],
    )
    arma = SimpleNamespace(tipo="Corrente", estilo="Chicote", dano=8)

    vetor = SimuladorCombat._calcular_vetor_impacto(sim, atacante, defensor)
    resultado = sim._aplicar_mecanicas_corrente(atacante, defensor, arma, 12.0, vetor)

    assert resultado.dano == pytest.approx(24.0)
    assert resultado.knockback_mult == pytest.approx(0.5)
    assert resultado.label == "CRACK!"
    assert defensor.atacando is False
    assert defensor.cooldown_ataque == pytest.approx(0.3)


def test_combat_helper_mangual_momentum_amplifica_dano_e_knockback():
    sim = _make_sim_stub()
    atacante = SimpleNamespace(chain_momentum=0.75)

    resultado = SimuladorCombat._resolver_corrente_mangual(sim, atacante, SimpleNamespace(dano=10.0, knockback_mult=1.0, label=None))

    assert resultado.dano == pytest.approx(14.5)
    assert resultado.knockback_mult == pytest.approx(1.6)
    assert resultado.label == "MOMENTUM!"
    assert atacante.chain_momentum == pytest.approx(1.0)


def test_combat_helper_kusarigama_mode_zero_aplica_corte_e_dot():
    sim = _make_sim_stub()
    atacante = SimpleNamespace(chain_mode=0)
    defensor = SimpleNamespace(dots_ativos=[], stun_timer=0.0)
    arma = SimpleNamespace(dano=12.0)

    resultado = SimuladorCombat._resolver_corrente_kusarigama(
        sim,
        atacante,
        defensor,
        arma,
        SimpleNamespace(dano=20.0, knockback_mult=1.0, label=None),
    )

    assert resultado.dano == pytest.approx(15.0)
    assert resultado.label == "CORTE!"
    assert len(defensor.dots_ativos) == 1


def test_combat_helper_kusarigama_mode_um_aplica_stun():
    sim = _make_sim_stub()
    atacante = SimpleNamespace(chain_mode=1)
    defensor = SimpleNamespace(dots_ativos=[], stun_timer=0.1)
    arma = SimpleNamespace(dano=12.0)

    resultado = SimuladorCombat._resolver_corrente_kusarigama(
        sim,
        atacante,
        defensor,
        arma,
        SimpleNamespace(dano=20.0, knockback_mult=1.0, label=None),
    )

    assert resultado.dano == pytest.approx(20.0)
    assert resultado.knockback_mult == pytest.approx(1.3)
    assert resultado.label == "STUN!"
    assert defensor.stun_timer == pytest.approx(0.4)


def test_combat_helper_corrente_com_peso_aplica_slow_e_puxao():
    sim = _make_sim_stub()
    atacante = SimpleNamespace(pos=[0.0, 0.0])
    defensor = SimpleNamespace(pos=[3.0, 4.0], vel=[0.0, 0.0], slow_timer=0.0, slow_fator=1.0)

    resultado = SimuladorCombat._resolver_corrente_com_peso(
        sim,
        atacante,
        defensor,
        SimpleNamespace(dano=18.0, knockback_mult=1.0, label=None),
    )

    assert resultado.knockback_mult == pytest.approx(0.3)
    assert resultado.label == "PUXÃƒO!"
    assert defensor.slow_timer == pytest.approx(1.5)
    assert defensor.slow_fator == pytest.approx(0.6)
    assert defensor.vel[0] < 0
    assert defensor.vel[1] < 0


def test_combat_helper_aplica_mecanicas_corrente_retorna_base_para_arma_nao_corrente():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    arma = SimpleNamespace(tipo="Reta")
    vetor = SimpleNamespace(vx=3.0, vy=4.0)

    resultado = sim._aplicar_mecanicas_corrente(atacante, defensor, arma, 12.0, vetor)

    assert resultado.dano == pytest.approx(12.0)
    assert resultado.knockback_mult == pytest.approx(1.0)
    assert resultado.label is None


def test_combat_helper_resolve_corrente_por_estilo_despacha_para_meteor_hammer():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    arma = SimpleNamespace(tipo="Corrente", estilo="Meteor Hammer")
    chain_result = ChainAttackResolution(dano=10.0)
    calls = []

    sim._resolver_corrente_meteor_hammer = lambda current_atacante, current_result: calls.append(
        (current_atacante, current_result)
    ) or ChainAttackResolution(dano=15.0, knockback_mult=0.8, label="ORBITA!")

    resultado = sim._resolver_corrente_por_estilo(atacante, defensor, arma, "Meteor Hammer", chain_result, 5.0)

    assert resultado.dano == pytest.approx(15.0)
    assert resultado.label == "ORBITA!"
    assert calls == [(atacante, chain_result)]


def test_combat_helper_aplica_mecanicas_corrente_orquestra_base_e_dispatch():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    arma = SimpleNamespace(tipo="Corrente", estilo="Chicote")
    vetor = SimpleNamespace(vx=3.0, vy=4.0)
    chain_result = ChainAttackResolution(dano=12.0)
    calls = []

    sim._criar_resultado_base_corrente = lambda dano: calls.append(("base", dano)) or chain_result
    sim._calcular_distancia_hit_corrente = lambda current_vetor: calls.append(("dist", current_vetor)) or 5.0
    sim._resolver_corrente_por_estilo = lambda *args: calls.append(("dispatch", args)) or ChainAttackResolution(
        dano=18.0,
        knockback_mult=0.5,
        label="CRACK!",
    )

    resultado = sim._aplicar_mecanicas_corrente(atacante, defensor, arma, 12.0, vetor)

    assert resultado.dano == pytest.approx(18.0)
    assert resultado.knockback_mult == pytest.approx(0.5)
    assert resultado.label == "CRACK!"
    assert calls == [
        ("base", 12.0),
        ("dist", vetor),
        ("dispatch", (atacante, defensor, arma, "Chicote", chain_result, 5.0)),
    ]


def test_combat_helper_tipo_golpe_uses_class_profile():
    sim = _make_sim_stub()
    bruto = SimpleNamespace(classe_nome="Berserker")
    agil = SimpleNamespace(classe_nome="Assassino")

    assert SimuladorCombat._determinar_tipo_golpe(sim, bruto, 18.0, False) == "MEDIO"
    assert SimuladorCombat._determinar_tipo_golpe(sim, bruto, 40.0, False) == "DEVASTADOR"
    assert SimuladorCombat._determinar_tipo_golpe(sim, agil, 12.0, False) == "LEVE"
    assert SimuladorCombat._determinar_tipo_golpe(sim, agil, 12.0, True) == "DEVASTADOR"


def test_combat_helper_prepara_contexto_melee_com_tentativa_e_marcacao(monkeypatch):
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()

    atacante = SimpleNamespace(
        pos=[0.0, 0.0],
        dados=SimpleNamespace(
            nome="Atacante",
            forca=6.0,
            arma_obj=SimpleNamespace(tipo="Reta", dano=10.0),
        ),
        alvos_atingidos_neste_ataque=set(),
    )
    defensor = SimpleNamespace(pos=[2.0, 0.0])

    monkeypatch.setattr("simulacao.sim_combat.verificar_hit", lambda *args, **kwargs: (True, "ok"))

    contexto = sim._preparar_contexto_ataque_melee(atacante, defensor)

    assert contexto is not None
    assert contexto.arma is atacante.dados.arma_obj
    assert contexto.dano > 0
    assert contexto.chain_kb_mult == pytest.approx(1.0)
    assert sim.stats_collector.attempts == [(("Atacante",), {})]
    assert id(defensor) in atacante.alvos_atingidos_neste_ataque


def test_combat_helper_prepara_contexto_melee_retorna_none_em_miss_mas_registra_tentativa(monkeypatch):
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()

    atacante = SimpleNamespace(
        pos=[0.0, 0.0],
        dados=SimpleNamespace(
            nome="Atacante",
            forca=6.0,
            arma_obj=SimpleNamespace(tipo="Reta", dano=10.0),
        ),
        alvos_atingidos_neste_ataque=set(),
    )
    defensor = SimpleNamespace(pos=[2.0, 0.0])

    monkeypatch.setattr("simulacao.sim_combat.verificar_hit", lambda *args, **kwargs: (False, "fora"))

    contexto = sim._preparar_contexto_ataque_melee(atacante, defensor)

    assert contexto is None
    assert sim.stats_collector.attempts == [(("Atacante",), {})]
    assert atacante.alvos_atingidos_neste_ataque == set()


def test_combat_helper_confirma_hit_melee_com_tentativa_e_marcacao(monkeypatch):
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()
    atacante = SimpleNamespace(
        dados=SimpleNamespace(nome="Atacante"),
        alvos_atingidos_neste_ataque=set(),
    )
    defensor = SimpleNamespace()

    monkeypatch.setattr("simulacao.sim_combat.verificar_hit", lambda *args, **kwargs: (True, "ok"))

    resultado = sim._confirmar_hit_ataque_melee(atacante, defensor)

    assert resultado is True
    assert sim.stats_collector.attempts == [(("Atacante",), {})]
    assert id(defensor) in atacante.alvos_atingidos_neste_ataque


def test_combat_helper_aplica_modificadores_contexto_melee_em_ordem():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    arma = SimpleNamespace(nome="Arma Teste")
    vetor = AttackImpactVector(
        dx_px=120,
        dy_px=80,
        vx=2.0,
        vy=1.0,
        mag=2.2360679775,
        direcao_impacto=0.5,
        posicao_mundo=(1.2, 0.8),
    )
    contexto = AttackPreparationContext(
        arma=arma,
        vetor_impacto=vetor,
        dano=14.0,
        is_critico=False,
    )

    sim._aplicar_desgaste_durabilidade_arma = lambda *args: calls.append(("desgaste", args)) or 11.0
    sim._aplicar_mecanicas_corrente = lambda *args: calls.append(("corrente", args)) or SimpleNamespace(
        dano=18.0,
        knockback_mult=1.5,
        label="CRACK!",
    )

    resultado = sim._aplicar_modificadores_contexto_ataque_melee(atacante, defensor, contexto)

    assert resultado.dano == pytest.approx(18.0)
    assert resultado.chain_kb_mult == pytest.approx(1.5)
    assert resultado.chain_label == "CRACK!"
    assert calls == [
        ("desgaste", (atacante, arma, 14.0, False)),
        ("corrente", (atacante, defensor, arma, 11.0, vetor)),
    ]


def test_combat_helper_aplica_desgaste_contexto_melee_delega_para_durabilidade():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    contexto = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )
    calls = []

    sim._aplicar_desgaste_durabilidade_arma = lambda *args: calls.append(args) or 11.0

    resultado = sim._aplicar_desgaste_contexto_ataque_melee(atacante, contexto)

    assert resultado == pytest.approx(11.0)
    assert calls == [(atacante, "arma", 14.0, True)]


def test_combat_helper_reempacota_contexto_modificado_ataque_melee():
    sim = _make_combat_harness()
    contexto = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=False,
    )
    chain_result = ChainAttackResolution(dano=18.0, knockback_mult=1.5, label="CRACK!")

    resultado = sim._reempacotar_contexto_modificado_ataque_melee(contexto, chain_result)

    assert resultado.arma == "arma"
    assert resultado.vetor_impacto == "vetor"
    assert resultado.dano == pytest.approx(18.0)
    assert resultado.is_critico is False
    assert resultado.chain_kb_mult == pytest.approx(1.5)
    assert resultado.chain_label == "CRACK!"


def test_combat_helper_aplica_modificadores_contexto_melee_orquestra_helpers():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    contexto = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=False,
    )
    chain_result = ChainAttackResolution(dano=18.0, knockback_mult=1.5, label="CRACK!")
    contexto_final = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=18.0,
        is_critico=False,
        chain_kb_mult=1.5,
        chain_label="CRACK!",
    )
    calls = []

    sim._aplicar_desgaste_contexto_ataque_melee = lambda current_atacante, current_contexto: calls.append(
        ("desgaste", current_atacante, current_contexto)
    ) or 11.0
    sim._resolver_corrente_contexto_ataque_melee = lambda current_atacante, current_defensor, current_contexto, dano: calls.append(
        ("corrente", current_atacante, current_defensor, current_contexto, dano)
    ) or chain_result
    sim._reempacotar_contexto_modificado_ataque_melee = lambda current_contexto, current_chain: calls.append(
        ("reempacotar", current_contexto, current_chain)
    ) or contexto_final

    resultado = sim._aplicar_modificadores_contexto_ataque_melee(atacante, defensor, contexto)

    assert resultado is contexto_final
    assert calls == [
        ("desgaste", atacante, contexto),
        ("corrente", atacante, defensor, contexto, 11.0),
        ("reempacotar", contexto, chain_result),
    ]


def test_combat_helper_prepara_contexto_melee_orquestra_subetapas():
    sim = _make_combat_harness()
    atacante = SimpleNamespace(dados=SimpleNamespace(arma_obj="arma"))
    defensor = SimpleNamespace()
    contexto_base = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=10.0,
        is_critico=False,
    )
    contexto_final = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=15.0,
        is_critico=False,
        chain_kb_mult=1.2,
        chain_label="CRACK!",
    )
    calls = []

    sim._pode_iniciar_ataque_melee = lambda current_atacante, current_defensor, current_arma: calls.append(
        ("gate", current_atacante, current_defensor, current_arma)
    ) or True
    sim._confirmar_hit_ataque_melee = lambda current_atacante, current_defensor: calls.append(
        ("confirmar", current_atacante, current_defensor)
    ) or True
    sim._criar_contexto_base_ataque_melee = lambda current_atacante, current_defensor, current_arma: calls.append(
        ("base", current_atacante, current_defensor, current_arma)
    ) or contexto_base
    sim._aplicar_modificadores_contexto_ataque_melee = lambda current_atacante, current_defensor, current_contexto: calls.append(
        ("mods", current_atacante, current_defensor, current_contexto)
    ) or contexto_final

    resultado = sim._preparar_contexto_ataque_melee(atacante, defensor)

    assert resultado is contexto_final
    assert calls == [
        ("gate", atacante, defensor, "arma"),
        ("confirmar", atacante, defensor),
        ("base", atacante, defensor, "arma"),
        ("mods", atacante, defensor, contexto_base),
    ]


def test_combat_helper_executa_feedback_pre_hit_orquestra_subetapas():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )
    game_feel = GameFeelHitResolution(dano=18.0, resultado_hit={"sofreu_stagger": True})

    sim._reproduzir_audio_ataque = lambda *args: calls.append(("audio", args))
    sim._notificar_coreografia_hit = lambda *args: calls.append(("choreo", args))
    sim._determinar_tipo_golpe = lambda *args: calls.append(("tipo", args)) or "DEVASTADOR"
    sim._processar_hit_game_feel = lambda *args: calls.append(("game_feel", args)) or game_feel

    resultado = sim._executar_feedback_pre_hit(atacante, defensor, ataque)

    assert resultado is game_feel
    assert calls == [
        ("audio", (atacante, "arma", 14.0, True)),
        ("choreo", (atacante, defensor, 14.0)),
        ("tipo", (atacante, 14.0, True)),
        ("game_feel", (atacante, defensor, 14.0, "DEVASTADOR", True, "vetor")),
    ]


def test_combat_helper_resolve_impacto_hit_preparado_orquestra_subetapas():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
        chain_kb_mult=1.4,
        chain_label="CRACK!",
    )
    resultado_hit = {"sofreu_stagger": True}
    knockback = AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5)

    sim._aplicar_feedback_impacto_ataque = lambda *args: calls.append(("impacto", args))
    sim._calcular_knockback_ataque = lambda *args: calls.append(("knockback", args)) or knockback
    sim._aplicar_feedback_attack_animation = lambda *args: calls.append(("anim", args))

    resultado = sim._resolver_impacto_hit_preparado(atacante, defensor, ataque, 18.0, resultado_hit)

    assert resultado is knockback
    assert calls == [
        ("impacto", ("arma", "CRACK!", "vetor")),
        ("knockback", (atacante, defensor, 18.0, 1.4, resultado_hit, "vetor")),
        ("anim", (atacante, defensor, 18.0, True, (1.2, 0.8), "vetor")),
    ]


def test_combat_helper_aplica_feedback_impacto_ataque_orquestra_subetapas():
    sim = _make_combat_harness()
    arma = SimpleNamespace()
    vetor = SimpleNamespace()
    calls = []

    sim._emitir_hit_spark_ataque = lambda current_vetor: calls.append(("spark", current_vetor))
    sim._emitir_impact_flash_ataque = lambda current_arma, current_vetor: calls.append(("flash", current_arma, current_vetor))
    sim._emitir_texto_chain_ataque = lambda current_label, current_vetor: calls.append(("texto", current_label, current_vetor))

    sim._aplicar_feedback_impacto_ataque(arma, "CRACK!", vetor)

    assert calls == [
        ("spark", vetor),
        ("flash", arma, vetor),
        ("texto", "CRACK!", vetor),
    ]


def test_combat_helper_obtem_cor_chain_label_ataque_aceita_label_legado():
    sim = _make_combat_harness()

    assert sim._obter_cor_chain_label_ataque("PUXÃƒO!") == (100, 255, 100)
    assert sim._obter_cor_chain_label_ataque("PUXÃO!") == (100, 255, 100)


def test_combat_helper_aplica_feedback_attack_animation_orquestra_manager_e_camera():
    sim = _make_combat_harness()
    sim.attack_anims = object()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    vetor = SimpleNamespace(direcao_impacto=0.5)
    impact_result = {"shake_intensity": 3.0, "shake_duration": 0.2, "zoom_punch": 0.1}
    calls = []

    sim._criar_resultado_attack_animation = lambda *args, **kwargs: calls.append(("criar", args, kwargs)) or impact_result
    sim._aplicar_feedback_camera_attack_animation = lambda current_result: calls.append(("camera", current_result))

    resultado = sim._aplicar_feedback_attack_animation(atacante, defensor, 18.0, True, (1.2, 0.8), vetor)

    assert resultado is impact_result
    assert calls == [
        ("criar", (sim.attack_anims,), {"atacante": atacante, "defensor": defensor, "dano": 18.0, "is_critico": True, "pos_impacto": (1.2, 0.8), "vetor_impacto": vetor}),
        ("camera", impact_result),
    ]


def test_combat_helper_resolve_impacto_hit_preparado_orquestra_helpers():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
        chain_kb_mult=1.4,
        chain_label="CRACK!",
    )
    resultado_hit = {"sofreu_stagger": True}
    knockback = AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5)
    calls = []

    sim._aplicar_feedback_visual_hit_preparado = lambda current_ataque: calls.append(("visual", current_ataque))
    sim._calcular_knockback_hit_preparado = lambda current_atacante, current_defensor, current_ataque, dano, current_resultado: calls.append(
        ("knockback", current_atacante, current_defensor, current_ataque, dano, current_resultado)
    ) or knockback
    sim._aplicar_animacao_hit_preparado = lambda current_atacante, current_defensor, current_ataque, dano, current_knockback: calls.append(
        ("animacao", current_atacante, current_defensor, current_ataque, dano, current_knockback)
    )

    resultado = sim._resolver_impacto_hit_preparado(atacante, defensor, ataque, 18.0, resultado_hit)

    assert resultado is knockback
    assert calls == [
        ("visual", ataque),
        ("knockback", atacante, defensor, ataque, 18.0, resultado_hit),
        ("animacao", atacante, defensor, ataque, 18.0, knockback),
    ]


def test_combat_helper_aplica_dano_e_finaliza_hit_preparado_rota_fatal():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace(dados=SimpleNamespace(forca=13.0))
    dano_recebido = []

    def _tomar_dano(*args, **kwargs):
        dano_recebido.append((args, kwargs))
        return True

    defensor = SimpleNamespace(tomar_dano=_tomar_dano)
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )
    knockback = AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5)

    sim._finalizar_hit_fatal = lambda *args: calls.append(("fatal", args)) or True
    sim._finalizar_hit_normal = lambda *args: calls.append(("normal", args)) or False

    resultado = sim._aplicar_dano_e_finalizar_hit_preparado(
        atacante,
        defensor,
        ataque,
        18.0,
        {"sofreu_stagger": True},
        knockback,
    )

    assert resultado is True
    assert dano_recebido == [((18.0, 6.0, 2.5, "NORMAL"), {"atacante": atacante})]
    assert calls == [
        ("fatal", (atacante, defensor, "arma", 18.0, True, "vetor")),
    ]


def test_combat_helper_aplica_dano_hit_preparado_delega_para_defensor():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    dano_recebido = []

    def _tomar_dano(*args, **kwargs):
        dano_recebido.append((args, kwargs))
        return False

    defensor = SimpleNamespace(tomar_dano=_tomar_dano)
    knockback = AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5)

    resultado = sim._aplicar_dano_hit_preparado(atacante, defensor, 18.0, knockback)

    assert resultado is False
    assert dano_recebido == [((18.0, 6.0, 2.5, "NORMAL"), {"atacante": atacante})]


def test_combat_helper_finaliza_hit_preparado_fatal_delega_para_finalizador():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )

    sim._finalizar_hit_fatal = lambda *args: calls.append(("fatal", args)) or True

    resultado = sim._finalizar_hit_preparado_fatal(atacante, defensor, ataque, 18.0)

    assert resultado is True
    assert calls == [
        ("fatal", (atacante, defensor, "arma", 18.0, True, "vetor")),
    ]


def test_combat_helper_finaliza_hit_preparado_normal_delega_forca_e_resultado():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace(dados=SimpleNamespace(forca=13.0))
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )
    resultado_hit = {"sofreu_stagger": True}

    sim._finalizar_hit_normal = lambda *args: calls.append(("normal", args)) or False

    resultado = sim._finalizar_hit_preparado_normal(atacante, defensor, ataque, 18.0, resultado_hit)

    assert resultado is False
    assert calls == [
        ("normal", (atacante, defensor, "arma", 18.0, True, 13.0, resultado_hit, "vetor")),
    ]


def test_combat_helper_finaliza_desfecho_hit_preparado_rota_fatal():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )
    calls = []

    sim._finalizar_hit_preparado_fatal = lambda current_atacante, current_defensor, current_ataque, dano: calls.append(
        ("fatal", current_atacante, current_defensor, current_ataque, dano)
    ) or True
    sim._finalizar_hit_preparado_normal = lambda *args: calls.append(("normal", args)) or False

    resultado = sim._finalizar_desfecho_hit_preparado(
        atacante,
        defensor,
        ataque,
        18.0,
        {"sofreu_stagger": True},
        True,
    )

    assert resultado is True
    assert calls == [
        ("fatal", atacante, defensor, ataque, 18.0),
    ]


def test_combat_helper_finaliza_desfecho_hit_preparado_rota_normal():
    sim = _make_combat_harness()
    calls = []
    atacante = SimpleNamespace(dados=SimpleNamespace(forca=13.0))
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )

    sim._finalizar_hit_preparado_fatal = lambda *args: calls.append(("fatal", args)) or True
    sim._finalizar_hit_preparado_normal = lambda current_atacante, current_defensor, current_ataque, dano, resultado_hit: calls.append(
        ("normal", current_atacante, current_defensor, current_ataque, dano, resultado_hit)
    ) or False

    resultado = sim._finalizar_desfecho_hit_preparado(
        atacante,
        defensor,
        ataque,
        18.0,
        {"sofreu_stagger": True},
        False,
    )

    assert resultado is False
    assert calls == [
        ("normal", atacante, defensor, ataque, 18.0, {"sofreu_stagger": True}),
    ]


def test_combat_helper_aplica_dano_e_finaliza_hit_preparado_orquestra_fases():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
    )
    knockback = AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5)
    calls = []

    sim._aplicar_dano_hit_preparado = lambda current_atacante, current_defensor, dano, current_knockback: calls.append(
        ("dano", current_atacante, current_defensor, dano, current_knockback)
    ) or True
    sim._finalizar_desfecho_hit_preparado = lambda current_atacante, current_defensor, current_ataque, dano, resultado_hit, fatal: calls.append(
        ("finalizar", current_atacante, current_defensor, current_ataque, dano, resultado_hit, fatal)
    ) or True

    resultado = sim._aplicar_dano_e_finalizar_hit_preparado(
        atacante,
        defensor,
        ataque,
        18.0,
        {"sofreu_stagger": True},
        knockback,
    )

    assert resultado is True
    assert calls == [
        ("dano", atacante, defensor, 18.0, knockback),
        ("finalizar", atacante, defensor, ataque, 18.0, {"sofreu_stagger": True}, True),
    ]


def test_combat_helper_resolve_hit_preparado_orquestra_subetapas():
    sim = _make_combat_harness()
    calls = []

    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
        chain_kb_mult=1.4,
        chain_label="CRACK!",
    )
    resultado_hit = {"sofreu_stagger": True}
    resolucao = PreparedHitResolution(
        dano=18.0,
        resultado_hit=resultado_hit,
        knockback=AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5),
    )

    sim._construir_resolucao_hit_preparado = lambda *args: calls.append(("construir", args)) or resolucao
    sim._aplicar_dano_e_finalizar_hit_preparado = lambda *args: calls.append(("final", args)) or False

    resultado = sim._resolver_hit_preparado(atacante, defensor, ataque)

    assert resultado is False
    assert calls == [
        ("construir", (atacante, defensor, ataque)),
        ("final", (atacante, defensor, ataque, 18.0, resultado_hit, resolucao.knockback)),
    ]


def test_checar_ataque_delega_para_resolver_hit_preparado():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = SimpleNamespace()
    calls = []

    sim._preparar_contexto_ataque_melee = lambda current_atacante, current_defensor: calls.append(
        ("preparar", current_atacante, current_defensor)
    ) or ataque
    sim._resolver_hit_preparado = lambda current_atacante, current_defensor, current_ataque: calls.append(
        ("resolver", current_atacante, current_defensor, current_ataque)
    ) or True

    resultado = sim.checar_ataque(atacante, defensor)

    assert resultado is True
    assert calls == [
        ("preparar", atacante, defensor),
        ("resolver", atacante, defensor, ataque),
    ]


def test_checar_ataque_retorna_false_quando_preparacao_falha():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    calls = []

    sim._preparar_contexto_ataque_melee = lambda current_atacante, current_defensor: calls.append(
        ("preparar", current_atacante, current_defensor)
    ) or None
    sim._resolver_hit_preparado = lambda *args: calls.append(("resolver", args)) or True

    resultado = sim.checar_ataque(atacante, defensor)

    assert resultado is False
    assert calls == [
        ("preparar", atacante, defensor),
    ]


def test_combat_helper_construir_resolucao_hit_preparado_orquestra_fases():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    ataque = AttackPreparationContext(
        arma="arma",
        vetor_impacto="vetor",
        dano=14.0,
        is_critico=True,
        chain_kb_mult=1.4,
        chain_label="CRACK!",
    )
    game_feel_resolution = GameFeelHitResolution(dano=18.0, resultado_hit={"sofreu_stagger": True})
    knockback = AttackKnockbackResolution(posicao_impacto=(1.2, 0.8), kb_x=6.0, kb_y=2.5)
    calls = []

    sim._executar_feedback_pre_hit = lambda current_atacante, current_defensor, current_ataque: calls.append(
        ("pre_hit", current_atacante, current_defensor, current_ataque)
    ) or game_feel_resolution
    sim._resolver_impacto_hit_preparado = lambda current_atacante, current_defensor, current_ataque, dano, resultado_hit: calls.append(
        ("impacto", current_atacante, current_defensor, current_ataque, dano, resultado_hit)
    ) or knockback

    resultado = sim._construir_resolucao_hit_preparado(atacante, defensor, ataque)

    assert resultado == PreparedHitResolution(
        dano=18.0,
        resultado_hit={"sofreu_stagger": True},
        knockback=knockback,
    )
    assert calls == [
        ("pre_hit", atacante, defensor, ataque),
        ("impacto", atacante, defensor, ataque, 18.0, {"sofreu_stagger": True}),
    ]


def test_combat_helper_finaliza_hit_fatal_com_encerramento_isolado():
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()

    particle_calls = []
    knockback_calls = []
    passive_calls = []
    slow_motion_calls = []

    sim.spawn_particulas = lambda *args, **kwargs: particle_calls.append((args, kwargs))
    sim._criar_knockback_visual = lambda *args, **kwargs: knockback_calls.append((args, kwargs))
    sim.ativar_slow_motion = lambda: slow_motion_calls.append(True)

    atacante = SimpleNamespace(
        dados=SimpleNamespace(nome="Atacante"),
        aplicar_passiva_em_hit=lambda dano, alvo: passive_calls.append((dano, alvo)),
    )
    defensor = SimpleNamespace(
        pos=[2.0, 1.0],
        dados=SimpleNamespace(nome="Defensor"),
    )
    arma = SimpleNamespace(nome="Espada Teste", elemento="FOGO")
    vetor = AttackImpactVector(
        dx_px=120,
        dy_px=80,
        vx=1.0,
        vy=0.5,
        mag=1.1180339887,
        direcao_impacto=0.5,
        posicao_mundo=(2.0, 1.0),
    )

    resultado = sim._finalizar_hit_fatal(atacante, defensor, arma, 30.0, True, vetor)

    assert resultado is True
    assert sim.vencedor == "Atacante"
    assert len(sim.stats_collector.hits) == 1
    assert len(sim.stats_collector.deaths) == 1
    assert len(passive_calls) == 1
    assert particle_calls[0][0][-1] == 50
    assert len(knockback_calls) == 1
    assert slow_motion_calls == [True]
    assert sim.hit_stop_timer == pytest.approx(0.25)
    assert len(sim.shockwaves) == 1
    assert len(sim.textos) == 1


def test_combat_helper_aplica_feedback_temporal_hit_fatal_sem_game_feel():
    sim = _make_combat_harness()
    shake_calls = []
    zoom_calls = []
    sim.cam = SimpleNamespace(
        x=0.0,
        aplicar_shake=lambda *args: shake_calls.append(args),
        zoom_punch=lambda *args: zoom_calls.append(args),
    )

    sim._aplicar_feedback_temporal_hit_fatal()

    assert shake_calls == [(18.0, 0.3)]
    assert zoom_calls == [(0.15, 0.15)]
    assert sim.hit_stop_timer == pytest.approx(0.25)


def test_combat_helper_adiciona_feedback_visual_hit_fatal_define_vencedor():
    sim = _make_combat_harness()
    slow_motion_calls = []
    sim.ativar_slow_motion = lambda: slow_motion_calls.append(True)
    atacante = SimpleNamespace(dados=SimpleNamespace(nome="Atacante"))
    vetor = AttackImpactVector(
        dx_px=120,
        dy_px=80,
        vx=1.0,
        vy=0.5,
        mag=1.1180339887,
        direcao_impacto=0.5,
        posicao_mundo=(2.0, 1.0),
    )

    sim._adicionar_feedback_visual_hit_fatal(atacante, vetor)

    assert len(sim.shockwaves) == 1
    assert len(sim.textos) == 1
    assert sim.vencedor == "Atacante"
    assert slow_motion_calls == [True]


def test_combat_helper_finaliza_hit_fatal_orquestra_subetapas():
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()
    calls = []
    atacante = SimpleNamespace(dados=SimpleNamespace(nome="Atacante"))
    defensor = SimpleNamespace(pos=[2.0, 1.0], dados=SimpleNamespace(nome="Defensor"))
    arma = SimpleNamespace(nome="Espada Teste", elemento="FOGO")
    vetor = AttackImpactVector(
        dx_px=120,
        dy_px=80,
        vx=1.0,
        vy=0.5,
        mag=1.1180339887,
        direcao_impacto=0.5,
        posicao_mundo=(2.0, 1.0),
    )

    sim._aplicar_passiva_hit_fatal = lambda *args: calls.append(("passiva", args))
    sim._reproduzir_audio_hit_fatal = lambda: calls.append(("audio",))
    sim._emitir_particulas_hit_fatal = lambda *args: calls.append(("particulas", args))
    sim._aplicar_knockback_visual_hit_fatal = lambda *args: calls.append(("knockback", args))
    sim._aplicar_feedback_temporal_hit_fatal = lambda: calls.append(("tempo",))
    sim._adicionar_feedback_visual_hit_fatal = lambda *args: calls.append(("visual", args))

    resultado = sim._finalizar_hit_fatal(atacante, defensor, arma, 30.0, True, vetor)

    assert resultado is True
    assert len(sim.stats_collector.hits) == 1
    assert len(sim.stats_collector.deaths) == 1
    assert calls == [
        ("passiva", (atacante, 30.0, defensor)),
        ("audio",),
        ("particulas", (defensor, vetor)),
        ("knockback", (defensor, 30.0, vetor)),
        ("tempo",),
        ("visual", (atacante, vetor)),
    ]


def test_combat_helper_finaliza_hit_normal_com_feedback_isolado():
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()

    particle_calls = []
    knockback_calls = []

    sim.spawn_particulas = lambda *args, **kwargs: particle_calls.append((args, kwargs))
    sim._criar_knockback_visual = lambda *args, **kwargs: knockback_calls.append((args, kwargs))

    atacante = SimpleNamespace(dados=SimpleNamespace(nome="Atacante"))
    defensor = SimpleNamespace(
        pos=[3.0, 1.5],
        dados=SimpleNamespace(nome="Defensor"),
    )
    arma = SimpleNamespace(nome="Machado Teste", elemento="")
    vetor = AttackImpactVector(
        dx_px=150,
        dy_px=90,
        vx=1.0,
        vy=0.0,
        mag=1.0,
        direcao_impacto=0.0,
        posicao_mundo=(3.0, 1.5),
    )

    resultado = sim._finalizar_hit_normal(
        atacante,
        defensor,
        arma,
        27.0,
        False,
        15.0,
        None,
        vetor,
    )

    assert resultado is False
    assert len(sim.stats_collector.hits) == 1
    assert sim.stats_collector.deaths == []
    assert len(knockback_calls) == 1
    assert particle_calls[0][0][-1] == 9
    assert sim.hit_stop_timer == pytest.approx(0.042)
    assert len(sim.shockwaves) == 1
    assert len(sim.textos) == 1


def test_combat_helper_determina_feedback_texto_dano_por_faixa():
    sim = _make_combat_harness()

    critico = sim._determinar_feedback_texto_dano(12.0, True)
    alto = sim._determinar_feedback_texto_dano(30.0, False)
    medio = sim._determinar_feedback_texto_dano(20.0, False)
    baixo = sim._determinar_feedback_texto_dano(10.0, False)

    assert critico == DamageTextFeedback(cor=(255, 50, 50), tamanho=32, critico=True)
    assert alto == DamageTextFeedback(cor=(255, 100, 100), tamanho=28, critico=False)
    assert medio == DamageTextFeedback(cor=(255, 200, 100), tamanho=24, critico=False)
    assert baixo == DamageTextFeedback(cor=BRANCO, tamanho=20, critico=False)


def test_combat_helper_adiciona_textos_hit_normal_inclui_banner_critico():
    sim = _make_combat_harness()
    vetor = AttackImpactVector(
        dx_px=150,
        dy_px=90,
        vx=1.0,
        vy=0.0,
        mag=1.0,
        direcao_impacto=0.0,
        posicao_mundo=(3.0, 1.5),
    )

    sim._adicionar_textos_hit_normal(27.0, True, vetor)

    assert len(sim.textos) == 2
    assert sim.textos[0].texto == "CRÃTICO!"
    assert sim.textos[1].texto == "27"


def test_combat_helper_finaliza_hit_normal_orquestra_subetapas():
    sim = _make_combat_harness()
    sim.stats_collector = _StatsCollectorSpy()
    calls = []
    atacante = SimpleNamespace(dados=SimpleNamespace(nome="Atacante"))
    defensor = SimpleNamespace(pos=[3.0, 1.5], dados=SimpleNamespace(nome="Defensor"))
    arma = SimpleNamespace(nome="Machado Teste", elemento="")
    vetor = AttackImpactVector(
        dx_px=150,
        dy_px=90,
        vx=1.0,
        vy=0.0,
        mag=1.0,
        direcao_impacto=0.0,
        posicao_mundo=(3.0, 1.5),
    )

    sim._reproduzir_audio_hit_normal = lambda *args: calls.append(("audio", args))
    sim._aplicar_knockback_visual_hit_normal = lambda *args: calls.append(("knockback", args))
    sim._emitir_particulas_hit_normal = lambda *args: calls.append(("particulas", args))
    sim._aplicar_feedback_temporal_hit_normal = lambda *args: calls.append(("tempo", args))
    sim._aplicar_shockwave_hit_normal = lambda *args: calls.append(("shockwave", args))
    sim._adicionar_textos_hit_normal = lambda *args: calls.append(("texto", args))

    resultado = sim._finalizar_hit_normal(
        atacante,
        defensor,
        arma,
        27.0,
        False,
        15.0,
        None,
        vetor,
    )

    assert resultado is False
    assert len(sim.stats_collector.hits) == 1
    assert calls == [
        ("audio", (27.0, defensor, False, None)),
        ("knockback", (defensor, 27.0, 15.0, vetor)),
        ("particulas", (defensor, 27.0, vetor)),
        ("tempo", (27.0,)),
        ("shockwave", (27.0, 15.0, vetor)),
        ("texto", (27.0, False, vetor)),
    ]


def test_combat_helper_processa_game_feel_e_super_armor_em_helper_isolado():
    sim = _make_combat_harness()
    calls = []

    class _GameFeelSpy:
        def verificar_super_armor(self, defensor, progresso_animacao, acao_atual):
            calls.append(("armor", progresso_animacao, acao_atual))

        def processar_hit(self, **kwargs):
            calls.append(("hit", kwargs))
            return {
                "dano_final": 18.0,
                "super_armor_ativa": True,
                "sofreu_stagger": False,
            }

    sim.game_feel = _GameFeelSpy()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace(
        atacando=True,
        timer_animacao=0.125,
        brain=SimpleNamespace(acao_atual="DEFENDER"),
    )
    vetor = AttackImpactVector(
        dx_px=110,
        dy_px=70,
        vx=2.0,
        vy=0.0,
        mag=2.0,
        direcao_impacto=0.0,
        posicao_mundo=(1.1, 0.7),
    )

    resultado = sim._processar_hit_game_feel(atacante, defensor, 12.0, "MEDIO", False, vetor)

    assert resultado.dano == pytest.approx(18.0)
    assert resultado.resultado_hit["super_armor_ativa"] is True
    assert calls[0] == ("armor", 0.5, "DEFENDER")
    assert calls[1][0] == "hit"
    assert len(sim.textos) == 1
    assert len(sim.particulas) == 8


def test_combat_helper_resolve_hit_sem_game_feel_cria_resolucao_base():
    sim = _make_combat_harness()

    resultado = sim._resolver_hit_sem_game_feel(12.0)

    assert resultado.dano == pytest.approx(12.0)
    assert resultado.resultado_hit is None


def test_combat_helper_resolve_hit_com_game_feel_orquestra_subetapas():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    vetor = AttackImpactVector(
        dx_px=110,
        dy_px=70,
        vx=2.0,
        vy=0.0,
        mag=2.0,
        direcao_impacto=0.0,
        posicao_mundo=(1.1, 0.7),
    )
    resultado_hit = {
        "dano_final": 18.0,
        "super_armor_ativa": True,
        "sofreu_stagger": False,
    }
    calls = []

    sim._calcular_progresso_animacao_defensiva = lambda current: calls.append(("progresso", current)) or 0.5
    sim._verificar_super_armor_hit_game_feel = lambda current, progresso: calls.append(("armor", current, progresso))
    sim._processar_hit_via_game_feel = lambda *args: calls.append(("hit", args)) or resultado_hit
    sim._aplicar_feedback_resultado_game_feel = lambda current, current_vetor: calls.append(("feedback", current, current_vetor))

    resultado = sim._resolver_hit_com_game_feel(atacante, defensor, 12.0, "MEDIO", False, vetor)

    assert resultado.dano == pytest.approx(18.0)
    assert resultado.resultado_hit is resultado_hit
    assert calls == [
        ("progresso", defensor),
        ("armor", defensor, 0.5),
        ("hit", (atacante, defensor, 12.0, "MEDIO", False, vetor)),
        ("feedback", resultado_hit, vetor),
    ]


def test_combat_helper_calcula_progresso_animacao_defensiva():
    sim = _make_combat_harness()
    defensor = SimpleNamespace(atacando=True, timer_animacao=0.125)

    progresso = sim._calcular_progresso_animacao_defensiva(defensor)

    assert progresso == pytest.approx(0.5)


def test_combat_helper_monta_knockback_game_feel_a_partir_do_vetor():
    sim = _make_combat_harness()
    vetor = AttackImpactVector(
        dx_px=110,
        dy_px=70,
        vx=2.0,
        vy=0.0,
        mag=2.0,
        direcao_impacto=0.0,
        posicao_mundo=(1.1, 0.7),
    )

    knockback = sim._montar_knockback_game_feel(vetor)

    assert knockback == pytest.approx((15.0, 0.0))


def test_combat_helper_processa_hit_game_feel_orquestra_subetapas():
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    vetor = AttackImpactVector(
        dx_px=110,
        dy_px=70,
        vx=2.0,
        vy=0.0,
        mag=2.0,
        direcao_impacto=0.0,
        posicao_mundo=(1.1, 0.7),
    )
    calls = []
    resultado_hit = {
        "dano_final": 18.0,
        "super_armor_ativa": True,
        "sofreu_stagger": False,
    }

    sim.game_feel = object()
    sim._resolver_hit_sem_game_feel = lambda current_dano: calls.append(("sem_manager", current_dano)) or GameFeelHitResolution(dano=current_dano)
    sim._resolver_hit_com_game_feel = lambda *args: calls.append(("com_manager", args)) or GameFeelHitResolution(
        dano=resultado_hit["dano_final"],
        resultado_hit=resultado_hit,
    )

    resultado = sim._processar_hit_game_feel(atacante, defensor, 12.0, "MEDIO", False, vetor)

    assert resultado.dano == pytest.approx(18.0)
    assert resultado.resultado_hit is resultado_hit
    assert calls == [
        ("com_manager", (atacante, defensor, 12.0, "MEDIO", False, vetor)),
    ]


def test_combat_helper_aplica_feedback_impacto_com_chain_label():
    sim = _make_combat_harness()
    arma = SimpleNamespace(r=10, g=20, b=30)
    vetor = AttackImpactVector(
        dx_px=90,
        dy_px=60,
        vx=1.0,
        vy=0.0,
        mag=1.0,
        direcao_impacto=0.0,
        posicao_mundo=(0.9, 0.6),
    )

    sim._aplicar_feedback_impacto_ataque(arma, "CRACK!", vetor)

    assert len(sim.hit_sparks) == 1
    assert len(sim.impact_flashes) == 1
    assert len(sim.textos) == 1


def test_combat_helper_calcula_knockback_com_multiplicadores(monkeypatch):
    sim = _make_combat_harness()
    atacante = SimpleNamespace()
    defensor = SimpleNamespace()
    vetor = AttackImpactVector(
        dx_px=90,
        dy_px=60,
        vx=1.0,
        vy=0.0,
        mag=1.0,
        direcao_impacto=0.0,
        posicao_mundo=(0.9, 0.6),
    )

    monkeypatch.setattr("simulacao.sim_combat.calcular_knockback_com_forca", lambda *args, **kwargs: (10.0, 4.0))

    resultado = sim._calcular_knockback_ataque(
        atacante,
        defensor,
        20.0,
        1.5,
        {"sofreu_stagger": False},
        vetor,
    )

    assert resultado.posicao_impacto == (0.9, 0.6)
    assert resultado.kb_x == pytest.approx(3.0)
    assert resultado.kb_y == pytest.approx(1.2)


def test_combat_helper_processa_clashes_somente_para_pares_validos():
    sim = _make_combat_harness()
    clash_calls = []
    effect_calls = []

    a = SimpleNamespace(nome="A", morto=False, dados=SimpleNamespace(arma_obj=object()))
    b = SimpleNamespace(nome="B", morto=False, dados=SimpleNamespace(arma_obj=object()))
    c = SimpleNamespace(nome="C", morto=True, dados=SimpleNamespace(arma_obj=object()))
    d = SimpleNamespace(nome="D", morto=False, dados=SimpleNamespace(arma_obj=None))

    sim.checar_clash_geral = lambda p1, p2: clash_calls.append((p1.nome, p2.nome)) or ((p1.nome, p2.nome) == ("A", "B"))
    sim.efeito_clash = lambda p1, p2: effect_calls.append((p1.nome, p2.nome))

    sim._processar_clashes_combate([a, b, c, d])

    assert clash_calls == [("A", "B")]
    assert effect_calls == [("A", "B")]


def test_combat_helper_processa_ataques_validos_e_finaliza_morte():
    sim = _make_combat_harness()
    attack_calls = []
    death_calls = []

    atacante = SimpleNamespace(nome="A", morto=False, atacando=True)
    defensor = SimpleNamespace(nome="B", morto=False, atacando=False)
    espectador = SimpleNamespace(nome="C", morto=False, atacando=False)
    morto = SimpleNamespace(nome="D", morto=True, atacando=False)

    sim.checar_ataque = lambda a, d: attack_calls.append((a.nome, d.nome)) or ((a.nome, d.nome) == ("A", "B"))
    sim._finalizar_morte_em_colisoes = lambda a, d: death_calls.append((a.nome, d.nome))

    sim._processar_ataques_combate([atacante, defensor, espectador, morto])

    assert attack_calls == [("A", "B"), ("A", "C")]
    assert death_calls == [("A", "B")]


def test_combat_helper_verificar_colisoes_orquestra_fases_em_ordem():
    sim = _make_combat_harness()
    fighters = [SimpleNamespace(nome="A"), SimpleNamespace(nome="B")]
    calls = []

    sim.fighters = fighters
    sim._processar_clashes_combate = lambda current: calls.append(("clashes", current))
    sim._processar_ataques_combate = lambda current: calls.append(("ataques", current))

    sim.verificar_colisoes_combate()

    assert calls == [("clashes", fighters), ("ataques", fighters)]


def test_combat_helper_finaliza_morte_em_colisoes_resolve_vencedor():
    sim = _make_combat_harness()
    slow_motion_calls = []
    sim.ativar_slow_motion = lambda: slow_motion_calls.append(True)
    sim._determinar_vencedor_por_morte = lambda morto: f"time-{morto.nome}"

    atacante = SimpleNamespace(dados=SimpleNamespace(nome="Atacante"))
    defensor = SimpleNamespace(nome="Defensor")

    sim._finalizar_morte_em_colisoes(atacante, defensor)

    assert slow_motion_calls == [True]
    assert sim.vencedor == "time-Defensor"


def test_combat_helper_checa_clash_geral_reta_reta_com_helper(monkeypatch):
    sim = _make_combat_harness()
    p1 = SimpleNamespace(dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Espada Reta")))
    p2 = SimpleNamespace(dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Katana Reta")))
    calls = []

    sim._checar_clash_duas_retas = lambda a, b: calls.append((a, b)) or True

    assert sim.checar_clash_geral(p1, p2) is True
    assert calls == [(p1, p2)]


def test_combat_helper_checa_clash_geral_reta_orbital_delega_espada_escudo():
    sim = _make_combat_harness()
    reta = SimpleNamespace(dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Espada Reta")))
    orbital = SimpleNamespace(dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Escudo Orbital")))
    calls = []

    sim.checar_clash_espada_escudo = lambda atacante, escudeiro: calls.append((atacante, escudeiro)) or True

    assert sim.checar_clash_geral(reta, orbital) is True
    assert calls == [(reta, orbital)]


def test_combat_helper_cria_contexto_visual_clash_com_cores_e_vetor():
    sim = _make_combat_harness()
    p1 = SimpleNamespace(
        pos=[1.0, 1.0],
        dados=SimpleNamespace(arma_obj=SimpleNamespace(r=10, g=20, b=30)),
    )
    p2 = SimpleNamespace(
        pos=[3.0, 2.0],
        dados=SimpleNamespace(arma_obj=SimpleNamespace()),
    )

    contexto = sim._criar_contexto_visual_clash(p1, p2)

    assert contexto.mx == pytest.approx(2.0 * PPM)
    assert contexto.my == pytest.approx(1.5 * PPM)
    assert contexto.cor1 == (10, 20, 30)
    assert contexto.cor2 == (255, 255, 255)
    assert contexto.mag > 0


def test_combat_helper_obtem_cor_arma_clash_com_fallback():
    sim = _make_combat_harness()
    colorido = SimpleNamespace(dados=SimpleNamespace(arma_obj=SimpleNamespace(r=10, g=20, b=30)))
    neutro = SimpleNamespace(dados=SimpleNamespace(arma_obj=SimpleNamespace()))

    assert sim._obter_cor_arma_clash(colorido) == (10, 20, 30)
    assert sim._obter_cor_arma_clash(neutro) == (255, 255, 255)


def test_combat_helper_cria_contexto_visual_clash_orquestra_subcalculos():
    sim = _make_combat_harness()
    p1 = SimpleNamespace()
    p2 = SimpleNamespace()
    calls = []

    sim._calcular_centro_visual_clash = lambda current_p1, current_p2: calls.append(("centro", current_p1, current_p2)) or (100.0, 80.0)
    sim._obter_cor_arma_clash = lambda current_lutador: calls.append(("cor", current_lutador)) or ((10, 20, 30) if current_lutador is p1 else (40, 50, 60))
    sim._calcular_vetor_visual_clash = lambda current_p1, current_p2: calls.append(("vetor", current_p1, current_p2)) or (0.5, -2.0, -1.0, 2.2360679775)

    contexto = sim._criar_contexto_visual_clash(p1, p2)

    assert contexto.mx == pytest.approx(100.0)
    assert contexto.my == pytest.approx(80.0)
    assert contexto.cor1 == (10, 20, 30)
    assert contexto.cor2 == (40, 50, 60)
    assert contexto.ang_p1_p2 == pytest.approx(0.5)
    assert contexto.vec_x == pytest.approx(-2.0)
    assert contexto.vec_y == pytest.approx(-1.0)
    assert contexto.mag == pytest.approx(2.2360679775)
    assert calls == [
        ("centro", p1, p2),
        ("cor", p1),
        ("cor", p2),
        ("vetor", p1, p2),
    ]


def test_combat_helper_efeito_clash_orquestra_subetapas_em_ordem():
    sim = _make_combat_harness()
    calls = []
    contexto = SimpleNamespace(mx=0.0, my=0.0)
    p1 = SimpleNamespace()
    p2 = SimpleNamespace()

    sim._criar_contexto_visual_clash = lambda a, b: calls.append(("contexto", a, b)) or contexto
    sim._emitir_particulas_clash = lambda current: calls.append(("particulas", current))
    sim._aplicar_vfx_clash = lambda current: calls.append(("vfx", current))
    sim._aplicar_empurrao_clash = lambda a, b, current: calls.append(("empurrao", a, b, current))
    sim._aplicar_feedback_camera_audio_clash = lambda current: calls.append(("camera_audio", current))

    sim.efeito_clash(p1, p2)

    assert calls == [
        ("contexto", p1, p2),
        ("particulas", contexto),
        ("vfx", contexto),
        ("empurrao", p1, p2, contexto),
        ("camera_audio", contexto),
    ]


def test_combat_helper_coleta_metricas_colisao_corpos():
    sim = _make_combat_harness()
    p1 = SimpleNamespace(pos=[1.0, 2.0], raio_fisico=1.5)
    p2 = SimpleNamespace(pos=[4.0, 6.0], raio_fisico=2.5)

    dx, dy, soma_raios, dist2 = sim._coletar_metricas_colisao_corpos(p1, p2)

    assert dx == pytest.approx(3.0)
    assert dy == pytest.approx(4.0)
    assert soma_raios == pytest.approx(4.0)
    assert dist2 == pytest.approx(25.0)


def test_combat_helper_calcula_normal_colisao_corpos_com_fallback(monkeypatch):
    sim = _make_combat_harness()

    monkeypatch.setattr("random.uniform", lambda a, b: 0.0)

    dist, nx, ny = sim._calcular_normal_colisao_corpos(0.0, 0.0, 0.0)

    assert dist == pytest.approx(0.0)
    assert nx == pytest.approx(1.0)
    assert ny == pytest.approx(0.0)


def test_combat_helper_cria_contexto_colisao_corpos_quando_ha_overlap():
    sim = _make_combat_harness()
    p1 = SimpleNamespace(pos=[0.0, 0.0], raio_fisico=1.0, z=0.0)
    p2 = SimpleNamespace(pos=[1.0, 0.0], raio_fisico=1.0, z=0.0)

    contexto = sim._criar_contexto_colisao_corpos(p1, p2)

    assert contexto is not None
    assert contexto.p1 is p1
    assert contexto.p2 is p2
    assert contexto.dist == pytest.approx(1.0)
    assert contexto.nx == pytest.approx(1.0)
    assert contexto.ny == pytest.approx(0.0)
    assert contexto.soma_raios == pytest.approx(2.0)


def test_combat_helper_cria_contexto_colisao_corpos_rejeita_par_separado():
    sim = _make_combat_harness()
    p1 = SimpleNamespace(pos=[0.0, 0.0], raio_fisico=1.0, z=0.0)
    p2 = SimpleNamespace(pos=[3.0, 0.0], raio_fisico=1.0, z=0.0)

    contexto = sim._criar_contexto_colisao_corpos(p1, p2)

    assert contexto is None


def test_combat_helper_resolve_iteracao_fisica_aplica_separacao_e_repulsao():
    sim = _make_combat_harness()
    p1 = SimpleNamespace(pos=[0.0, 0.0], vel=[0.0, 0.0], raio_fisico=1.0, z=0.0)
    p2 = SimpleNamespace(pos=[1.0, 0.0], vel=[0.0, 0.0], raio_fisico=1.0, z=0.0)

    houve_colisao = sim._resolver_iteracao_fisica_corpos([p1, p2], 6.0)

    assert houve_colisao is True
    assert p1.pos[0] < 0.0
    assert p2.pos[0] > 1.0
    assert p1.vel[0] == pytest.approx(-6.0)
    assert p2.vel[0] == pytest.approx(6.0)


def test_combat_helper_resolver_fisica_corpos_para_no_primeiro_early_exit():
    sim = _make_combat_harness()
    sim.fighters = [
        SimpleNamespace(morto=False),
        SimpleNamespace(morto=False),
    ]
    calls = []

    sim._resolver_iteracao_fisica_corpos = lambda vivos, fator: calls.append((vivos, fator)) or False

    sim.resolver_fisica_corpos(0.016)

    assert len(calls) == 1
    assert calls[0][1] == pytest.approx(6.0)


def test_combat_helper_executa_passes_fisica_corpos_respeita_early_exit():
    sim = _make_combat_harness()
    vivos = [SimpleNamespace(), SimpleNamespace()]
    calls = []
    respostas = iter([True, True, False])

    sim._resolver_iteracao_fisica_corpos = lambda current_vivos, fator: calls.append((current_vivos, fator)) or next(respostas)

    sim._executar_passes_fisica_corpos(vivos, 6.0, max_iteracoes=4)

    assert len(calls) == 3
    assert all(call == (vivos, 6.0) for call in calls)


def test_combat_helper_cria_contexto_clash_magico_com_defaults_e_pixels():
    sim = _make_combat_harness()
    proj1 = SimpleNamespace(x=2.0, y=4.0, cor=(10, 20, 30))
    proj2 = SimpleNamespace(x=4.0, y=6.0)

    contexto = sim._criar_contexto_clash_magico(proj1, proj2)

    assert contexto.mx == pytest.approx(3.0)
    assert contexto.my == pytest.approx(5.0)
    assert contexto.mx_px == pytest.approx(3.0 * PPM)
    assert contexto.my_px == pytest.approx(5.0 * PPM)
    assert contexto.cor1 == (10, 20, 30)
    assert contexto.cor2 == (100, 100, 255)


def test_combat_helper_executa_clash_magico_orquestra_subetapas_em_ordem():
    sim = _make_combat_harness()
    proj1 = SimpleNamespace()
    proj2 = SimpleNamespace()
    contexto = SimpleNamespace(mx=1.0, my=2.0)
    calls = []

    sim._desativar_projeteis_clash_magico = lambda a, b: calls.append(("desativar", a, b))
    sim._criar_contexto_clash_magico = lambda a, b: calls.append(("contexto", a, b)) or contexto
    sim._aplicar_vfx_clash_magico = lambda current: calls.append(("vfx", current))
    sim._aplicar_feedback_camera_audio_clash_magico = lambda current: calls.append(("feedback", current))
    sim._emitir_particulas_clash_magico = lambda current: calls.append(("particulas", current))

    sim._executar_clash_magico(proj1, proj2)

    assert calls == [
        ("desativar", proj1, proj2),
        ("contexto", proj1, proj2),
        ("vfx", contexto),
        ("feedback", contexto),
        ("particulas", contexto),
    ]


def test_combat_helper_desativa_projeteis_no_clash_magico():
    sim = _make_combat_harness()
    proj1 = SimpleNamespace(ativo=True)
    proj2 = SimpleNamespace(ativo=True)

    sim._desativar_projeteis_clash_magico(proj1, proj2)

    assert proj1.ativo is False
    assert proj2.ativo is False


def test_combat_helper_cancela_estado_sword_clash_resetando_ataques():
    sim = _make_combat_harness()
    p1 = SimpleNamespace(
        atacando=True,
        timer_animacao=0.25,
        cooldown_ataque=1.0,
        alvos_atingidos_neste_ataque={1, 2},
    )
    p2 = SimpleNamespace(
        atacando=True,
        timer_animacao=0.10,
        cooldown_ataque=1.0,
        alvos_atingidos_neste_ataque={3},
    )

    sim._cancelar_estado_sword_clash(p1, p2)

    assert p1.atacando is False
    assert p2.atacando is False
    assert p1.timer_animacao == 0
    assert p2.timer_animacao == 0
    assert p1.cooldown_ataque == pytest.approx(0.3)
    assert p2.cooldown_ataque == pytest.approx(0.3)
    assert p1.alvos_atingidos_neste_ataque == set()
    assert p2.alvos_atingidos_neste_ataque == set()


def test_combat_helper_cria_contexto_sword_clash_com_defaults_e_pixels(monkeypatch):
    sim = _make_combat_harness()
    p1 = SimpleNamespace(pos=[2.0, 4.0], dados=SimpleNamespace(cor=(10, 20, 30)))
    p2 = SimpleNamespace(pos=[4.0, 6.0], dados=SimpleNamespace())

    monkeypatch.setattr("random.choice", lambda options: "CLANG!")

    contexto = sim._criar_contexto_sword_clash(p1, p2)

    assert contexto.mx == pytest.approx(3.0)
    assert contexto.my == pytest.approx(5.0)
    assert contexto.mx_px == pytest.approx(3.0 * PPM)
    assert contexto.my_px == pytest.approx(5.0 * PPM)
    assert contexto.cor1 == (10, 20, 30)
    assert contexto.cor2 == (80, 180, 255)
    assert contexto.texto == "CLANG!"


def test_combat_helper_executa_sword_clash_orquestra_subetapas_em_ordem():
    sim = _make_combat_harness()
    sim.p1 = SimpleNamespace()
    sim.p2 = SimpleNamespace()
    contexto = SimpleNamespace(mx=1.0, my=2.0)
    calls = []

    sim._cancelar_estado_sword_clash = lambda a, b: calls.append(("cancelar", a, b))
    sim._criar_contexto_sword_clash = lambda a, b: calls.append(("contexto", a, b)) or contexto
    sim._aplicar_vfx_sword_clash = lambda current: calls.append(("vfx", current))
    sim._aplicar_feedback_camera_audio_sword_clash = lambda current: calls.append(("feedback", current))
    sim._emitir_particulas_sword_clash = lambda current: calls.append(("particulas", current))
    sim._aplicar_hit_spark_sword_clash = lambda current: calls.append(("spark", current))

    sim._executar_sword_clash()

    assert calls == [
        ("cancelar", sim.p1, sim.p2),
        ("contexto", sim.p1, sim.p2),
        ("vfx", contexto),
        ("feedback", contexto),
        ("particulas", contexto),
        ("spark", contexto),
    ]


def test_combat_helper_coleta_fontes_clash_projeteis_de_projeteis_e_orbes():
    sim = _make_combat_harness()
    owner = SimpleNamespace(buffer_orbes=[
        SimpleNamespace(ativo=True, estado="disparando"),
        SimpleNamespace(ativo=True, estado="orbitando"),
        SimpleNamespace(ativo=False, estado="disparando"),
    ])
    other = object()
    proj_owner_ativo = SimpleNamespace(dono=owner, ativo=True)
    proj_owner_inativo = SimpleNamespace(dono=owner, ativo=False)
    proj_other = SimpleNamespace(dono=other, ativo=True)
    sim.projeteis = [proj_owner_ativo, proj_owner_inativo, proj_other]

    fontes = sim._coletar_fontes_clash_projeteis(owner)

    assert fontes == [proj_owner_ativo, owner.buffer_orbes[0]]


def test_combat_helper_cria_contexto_clash_projeteis_com_distancia_e_raio():
    sim = _make_combat_harness()
    proj1 = SimpleNamespace(x=0.0, y=0.0, raio=0.3)
    proj2 = SimpleNamespace(x=0.4, y=0.0, raio=0.2)

    contexto = sim._criar_contexto_clash_projeteis(proj1, proj2)

    assert contexto.proj1 is proj1
    assert contexto.proj2 is proj2
    assert contexto.dist == pytest.approx(0.4)
    assert contexto.raio_colisao == pytest.approx(0.8)


def test_combat_helper_processa_clash_projeteis_entre_grupos_so_quando_colide():
    sim = _make_combat_harness()
    calls = []
    proj1 = SimpleNamespace(x=0.0, y=0.0, raio=0.2, ativo=True)
    proj2 = SimpleNamespace(x=0.1, y=0.0, raio=0.2, ativo=True)
    proj_inativo = SimpleNamespace(x=0.0, y=0.0, raio=0.2, ativo=False)
    proj_longe = SimpleNamespace(x=5.0, y=0.0, raio=0.2, ativo=True)

    sim._executar_clash_magico = lambda a, b: calls.append((a, b))

    sim._processar_clash_projeteis_entre_grupos([proj1, proj_inativo], [proj2, proj_longe])

    assert calls == [(proj1, proj2)]


def test_combat_helper_verifica_clash_projeteis_orquestra_grupos_dos_donos():
    sim = _make_combat_harness()
    sim.p1 = SimpleNamespace(buffer_orbes=[SimpleNamespace(ativo=True, estado="disparando", nome="orb1")])
    sim.p2 = SimpleNamespace(buffer_orbes=[SimpleNamespace(ativo=True, estado="disparando", nome="orb2")])
    proj1 = SimpleNamespace(dono=sim.p1, ativo=True, nome="proj1")
    proj2 = SimpleNamespace(dono=sim.p2, ativo=True, nome="proj2")
    sim.projeteis = [proj1, proj2]
    calls = []

    sim._processar_clash_projeteis_entre_grupos = lambda grupo1, grupo2: calls.append((grupo1, grupo2))

    sim._verificar_clash_projeteis()

    assert calls == [([proj1, sim.p1.buffer_orbes[0]], [proj2, sim.p2.buffer_orbes[0]])]


def test_combat_helper_detecta_bloqueio_escudo_orbital_retorna_posicao():
    sim = _make_combat_harness()
    proj = SimpleNamespace(x=2.2, y=2.0, raio=0.2)
    alvo = SimpleNamespace(
        dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Orbital")),
        get_escudo_info=lambda: ((100.0, 100.0), 20.0, 0.0, 180.0),
    )

    resultado = sim._detectar_bloqueio_escudo_orbital(proj, alvo)

    assert resultado == (100.0, 100.0)


def test_combat_helper_projetil_esta_no_arco_escudo_orbital_rejeita_fora_do_arco():
    sim = _make_combat_harness()

    assert sim._projetil_esta_no_arco_escudo_orbital(-20.0, 0.0, 0.0, 90.0) is False


def test_combat_helper_detecta_bloqueio_escudo_orbital_orquestra_metricas_e_arco():
    sim = _make_combat_harness()
    proj = SimpleNamespace(raio=0.2)
    alvo = SimpleNamespace(
        dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Orbital")),
        get_escudo_info=lambda: ((100.0, 100.0), 20.0, 0.0, 180.0),
    )
    calls = []

    sim._calcular_metricas_escudo_orbital = lambda current_proj, escudo_pos: calls.append(
        ("metricas", current_proj, escudo_pos)
    ) or (10.0, 0.0, 12.0)
    sim._projetil_atinge_raio_escudo_orbital = lambda current_proj, escudo_raio, dist_escudo: calls.append(
        ("raio", current_proj, escudo_raio, dist_escudo)
    ) or True
    sim._projetil_esta_no_arco_escudo_orbital = lambda dx, dy, ang, arco: calls.append(
        ("arco", dx, dy, ang, arco)
    ) or True

    resultado = sim._detectar_bloqueio_escudo_orbital(proj, alvo)

    assert resultado == (100.0, 100.0)
    assert calls == [
        ("metricas", proj, (100.0, 100.0)),
        ("raio", proj, 20.0, 12.0),
        ("arco", 10.0, 0.0, 0.0, 180.0),
    ]


def test_combat_helper_detecta_parry_projetil_com_interceptacao(monkeypatch):
    sim = _make_combat_harness()
    proj = SimpleNamespace(x=1.0, y=0.0, raio=0.2)
    alvo = SimpleNamespace(
        atacando=True,
        timer_animacao=0.2,
        dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Espada Reta")),
        get_pos_ponteira_arma=lambda: ((0.0, 0.0), (100.0, 0.0)),
    )

    monkeypatch.setattr("simulacao.sim_combat.colisao_linha_circulo", lambda *args, **kwargs: True)

    assert sim._detectar_parry_projetil(proj, alvo) is True


def test_combat_helper_tenta_bloqueio_escudo_projetil_aplica_efeito():
    sim = _make_combat_harness()
    calls = []
    proj = SimpleNamespace()
    alvo = SimpleNamespace()

    sim._detectar_bloqueio_escudo_orbital = lambda current_proj, current_alvo: (10.0, 20.0)
    sim._efeito_bloqueio = lambda current_proj, current_alvo, pos_escudo: calls.append(
        (current_proj, current_alvo, pos_escudo)
    )

    assert sim._tentar_bloqueio_escudo_projetil(proj, alvo) is True
    assert calls == [(proj, alvo, (10.0, 20.0))]


def test_combat_helper_tenta_desvio_dash_projetil_registra_coreografia():
    sim = _make_combat_harness()
    dodge_calls = []
    choreo_calls = []
    proj = SimpleNamespace(dono="attacker")
    alvo = SimpleNamespace()
    sim.choreographer = SimpleNamespace(registrar_esquiva=lambda *args: choreo_calls.append(args))

    sim._detectar_desvio_dash = lambda current_proj, current_alvo, dist: True
    sim._efeito_desvio_dash = lambda current_proj, current_alvo: dodge_calls.append((current_proj, current_alvo))

    assert sim._tentar_desvio_dash_projetil(proj, alvo, 0.4) is True
    assert dodge_calls == [(proj, alvo)]
    assert choreo_calls == [(alvo, "attacker")]


def test_combat_helper_verifica_bloqueio_projetil_prioriza_escudo():
    sim = _make_combat_harness()
    calls = []
    proj = SimpleNamespace(ativo=True, x=2.2, y=2.0, raio=0.2)
    alvo = SimpleNamespace(
        pos=[2.0, 2.0],
        raio_fisico=1.0,
        dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Orbital")),
        get_escudo_info=lambda: ((100.0, 100.0), 20.0, 0.0, 180.0),
    )

    sim._efeito_bloqueio = lambda current_proj, current_alvo, pos_escudo: calls.append((current_proj, current_alvo, pos_escudo))

    assert sim._verificar_bloqueio_projetil(proj, alvo) is True
    assert calls == [(proj, alvo, (100.0, 100.0))]


def test_combat_helper_verifica_bloqueio_projetil_orquestra_prioridades():
    sim = _make_combat_harness()
    proj = SimpleNamespace()
    alvo = SimpleNamespace()
    calls = []

    sim._preparar_janela_defesa_projetil = lambda current_proj, current_alvo: calls.append(
        ("janela", current_proj, current_alvo)
    ) or 0.4
    sim._tentar_bloqueio_escudo_projetil = lambda current_proj, current_alvo: calls.append(
        ("escudo", current_proj, current_alvo)
    ) or False
    sim._tentar_desvio_dash_projetil = lambda current_proj, current_alvo, dist: calls.append(
        ("dash", current_proj, current_alvo, dist)
    ) or False
    sim._tentar_parry_projetil = lambda current_proj, current_alvo: calls.append(
        ("parry", current_proj, current_alvo)
    ) or True

    assert sim._verificar_bloqueio_projetil(proj, alvo) is True
    assert calls == [
        ("janela", proj, alvo),
        ("escudo", proj, alvo),
        ("dash", proj, alvo, 0.4),
        ("parry", proj, alvo),
    ]


def test_combat_helper_verifica_bloqueio_projetil_rota_dash_registra_esquiva():
    sim = _make_combat_harness()
    dodge_calls = []
    choreo_calls = []
    proj = SimpleNamespace(ativo=True, x=0.4, y=0.0, raio=0.2, dono="attacker")
    alvo = SimpleNamespace(
        pos=[0.0, 0.0],
        raio_fisico=1.0,
        dados=SimpleNamespace(arma_obj=None),
        dash_timer=0.2,
        atacando=False,
        timer_animacao=0.0,
    )
    sim.choreographer = SimpleNamespace(registrar_esquiva=lambda *args: choreo_calls.append(args))
    sim._efeito_desvio_dash = lambda current_proj, current_alvo: dodge_calls.append((current_proj, current_alvo))

    assert sim._verificar_bloqueio_projetil(proj, alvo) is True
    assert dodge_calls == [(proj, alvo)]
    assert choreo_calls == [(alvo, "attacker")]


def test_combat_helper_verifica_bloqueio_projetil_rota_parry():
    sim = _make_combat_harness()
    parry_calls = []
    proj = SimpleNamespace(ativo=True, x=0.4, y=0.0, raio=0.2)
    alvo = SimpleNamespace(
        pos=[0.0, 0.0],
        raio_fisico=1.0,
        dados=SimpleNamespace(arma_obj=SimpleNamespace(tipo="Espada Reta")),
        dash_timer=0.0,
        atacando=True,
        timer_animacao=0.2,
    )

    sim._detectar_bloqueio_escudo_orbital = lambda *args, **kwargs: None
    sim._detectar_desvio_dash = lambda *args, **kwargs: False
    sim._detectar_parry_projetil = lambda *args, **kwargs: True
    sim._efeito_parry = lambda current_proj, current_alvo: parry_calls.append((current_proj, current_alvo))

    assert sim._verificar_bloqueio_projetil(proj, alvo) is True
    assert parry_calls == [(proj, alvo)]


def test_combat_helper_cria_contexto_visual_bloqueio_e_parry():
    sim = _make_combat_harness()
    proj = SimpleNamespace(x=1.0, y=2.0)
    lutador = SimpleNamespace(
        pos=[0.0, 0.0],
        dados=SimpleNamespace(cor_r=10, cor_g=20, cor_b=30),
    )

    contexto_bloqueio = sim._criar_contexto_visual_bloqueio(proj, lutador, (0.0, 0.0))
    contexto_parry = sim._criar_contexto_visual_parry(proj, lutador)

    assert contexto_bloqueio.proj_x_px == pytest.approx(1.0 * PPM)
    assert contexto_bloqueio.proj_y_px == pytest.approx(2.0 * PPM)
    assert contexto_bloqueio.cor_lutador == (10, 20, 30)
    assert contexto_parry.proj_x_px == pytest.approx(1.0 * PPM)
    assert contexto_parry.proj_y_px == pytest.approx(2.0 * PPM)
    assert contexto_parry.cor_lutador == (10, 20, 30)


def test_combat_helper_efeito_bloqueio_orquestra_subetapas():
    sim = _make_combat_harness()
    proj = SimpleNamespace()
    bloqueador = SimpleNamespace()
    contexto = SimpleNamespace(proj_x_px=10.0, proj_y_px=20.0, cor_lutador=(1, 2, 3), ang_impacto=0.5)
    calls = []

    sim._registrar_bloco_defensivo = lambda current: calls.append(("registrar", current))
    sim._reproduzir_audio_bloqueio = lambda: calls.append(("audio",))
    sim._criar_contexto_visual_bloqueio = lambda current_proj, current_lutador, pos_escudo: calls.append(("contexto", current_proj, current_lutador, pos_escudo)) or contexto
    sim._adicionar_texto_feedback_defensivo = lambda *args: calls.append(("texto", args))
    sim._emitir_particulas_bloqueio = lambda current: calls.append(("particulas", current))
    sim._aplicar_feedback_temporal_defensivo = lambda current: calls.append(("tempo", current))

    sim._efeito_bloqueio(proj, bloqueador, (0.0, 0.0))

    assert calls == [
        ("registrar", bloqueador),
        ("audio",),
        ("contexto", proj, bloqueador, (0.0, 0.0)),
        ("texto", (10.0, 20.0, "BLOCK!", (100, 200, 255), 22, -30)),
        ("particulas", contexto),
        ("tempo", DefensiveTempoFeedback(shake_intensity=5.0, shake_duration=0.06, hit_stop=0.03, time_scale=None, slow_mo_timer=0.0)),
    ]


def test_combat_helper_efeito_parry_orquestra_contexto():
    sim = _make_combat_harness()
    proj = SimpleNamespace()
    parryer = SimpleNamespace()
    contexto = SimpleNamespace(proj_x_px=10.0, proj_y_px=20.0, cor_lutador=(1, 2, 3), ang_impacto=0.5)
    calls = []

    sim._registrar_bloco_defensivo = lambda current: calls.append(("registrar", current))
    sim._criar_contexto_visual_parry = lambda current_proj, current_parryer: calls.append(("contexto", current_proj, current_parryer)) or contexto
    sim._adicionar_texto_feedback_defensivo = lambda *args: calls.append(("texto", args))
    sim._aplicar_feedback_temporal_defensivo = lambda current: calls.append(("tempo", current))

    sim._efeito_parry(proj, parryer)

    assert calls == [
        ("registrar", parryer),
        ("contexto", proj, parryer),
        ("texto", (10.0, 20.0, "PARRY!", AMARELO_FAISCA, 28, -40)),
        ("tempo", DefensiveTempoFeedback(shake_intensity=8.0, shake_duration=0.1, hit_stop=0.06, time_scale=0.4, slow_mo_timer=0.25)),
    ]


def test_combat_helper_cria_contexto_visual_desvio_dash_com_trilha():
    sim = _make_combat_harness()
    desviador = SimpleNamespace(
        pos=[2.0, 3.0],
        pos_historico=[
            (0.0, 0.0),
            (0.5, 0.5),
            (1.0, 1.0),
            (1.5, 2.0),
        ],
        dados=SimpleNamespace(cor_r=10, cor_g=20, cor_b=30),
    )

    contexto = sim._criar_contexto_visual_desvio_dash(desviador)

    assert contexto.pos_x_px == pytest.approx(2.0 * PPM)
    assert contexto.pos_y_px == pytest.approx(3.0 * PPM)
    assert contexto.cor_lutador == (10, 20, 30)
    assert contexto.trilha_posicoes == [
        (0.0 * PPM, 0.0 * PPM),
        (0.5 * PPM, 0.5 * PPM),
        (1.0 * PPM, 1.0 * PPM),
        (1.5 * PPM, 2.0 * PPM),
    ]


def test_combat_helper_aplica_trail_desvio_dash_somente_com_historico():
    sim = _make_combat_harness()
    contexto_com_trilha = SimpleNamespace(
        trilha_posicoes=[(1.0, 2.0), (3.0, 4.0)],
        cor_lutador=(10, 20, 30),
    )
    contexto_sem_trilha = SimpleNamespace(
        trilha_posicoes=[],
        cor_lutador=(10, 20, 30),
    )

    sim._aplicar_trail_desvio_dash(contexto_com_trilha)
    sim._aplicar_trail_desvio_dash(contexto_sem_trilha)

    assert len(sim.dash_trails) == 1


def test_combat_helper_efeito_desvio_dash_orquestra_subetapas():
    sim = _make_combat_harness()
    proj = SimpleNamespace()
    desviador = SimpleNamespace()
    contexto = SimpleNamespace()
    calls = []

    sim._registrar_esquiva_stats = lambda current: calls.append(("stats", current))
    sim._criar_contexto_visual_desvio_dash = lambda current: calls.append(("contexto", current)) or contexto
    sim._aplicar_trail_desvio_dash = lambda current: calls.append(("trail", current))
    sim._aplicar_feedback_desvio_dash = lambda current: calls.append(("feedback", current))

    sim._efeito_desvio_dash(proj, desviador)

    assert calls == [
        ("stats", desviador),
        ("contexto", desviador),
        ("trail", contexto),
        ("feedback", contexto),
    ]


def test_combat_helper_aplica_feedback_desvio_dash_usa_helpers_compartilhados():
    sim = _make_combat_harness()
    contexto = SimpleNamespace(pos_x_px=20.0, pos_y_px=40.0)
    calls = []

    sim._adicionar_texto_feedback_defensivo = lambda *args: calls.append(("texto", args))
    sim._aplicar_feedback_temporal_defensivo = lambda current: calls.append(("tempo", current))

    sim._aplicar_feedback_desvio_dash(contexto)

    assert calls == [
        ("texto", (20.0, 40.0, "DODGE!", (150, 255, 150), 24, -50)),
        ("tempo", DefensiveTempoFeedback(shake_intensity=0.0, shake_duration=0.0, hit_stop=0.0, time_scale=0.5, slow_mo_timer=0.3)),
    ]


def test_combat_helper_adiciona_texto_feedback_defensivo_com_offset():
    sim = _make_combat_harness()

    sim._adicionar_texto_feedback_defensivo(10.0, 20.0, "TXT", (1, 2, 3), 18, -7)

    assert len(sim.textos) == 1
    assert sim.textos[0].x == pytest.approx(10.0)
    assert sim.textos[0].y == pytest.approx(13.0)


def test_combat_helper_aplica_feedback_temporal_defensivo_completo():
    sim = _make_combat_harness()
    shake_calls = []
    sim.cam = SimpleNamespace(
        x=0.0,
        aplicar_shake=lambda *args: shake_calls.append(args),
        zoom_punch=lambda *args, **kwargs: None,
    )

    sim._aplicar_feedback_temporal_defensivo(
        DefensiveTempoFeedback(
            shake_intensity=7.0,
            shake_duration=0.09,
            hit_stop=0.04,
            time_scale=0.6,
            slow_mo_timer=0.2,
        )
    )

    assert shake_calls == [(7.0, 0.09)]
    assert sim.hit_stop_timer == pytest.approx(0.04)
    assert sim.time_scale == pytest.approx(0.6)
    assert sim.slow_mo_timer == pytest.approx(0.2)


def test_lutador_ai_alias_points_to_brain():
    fighter = _make_fighter("Alias")

    assert fighter.ai is fighter.brain

    replacement = SimpleNamespace(marker=True)
    fighter.ai = replacement

    assert fighter.brain is replacement
    assert fighter.ai is replacement


def test_block_and_parry_callbacks_reach_brain():
    fighter = _make_fighter("Defensor")
    sim = _make_combat_harness()
    proj = SimpleNamespace(x=1.0, y=1.0)
    calls = []

    fighter.brain.on_bloqueio_sucesso = lambda: calls.append("ok")

    sim._efeito_bloqueio(proj, fighter, (0.0, 0.0))
    sim._efeito_parry(proj, fighter)

    assert calls == ["ok", "ok"]


def test_opponent_recuing_window_uses_enemy_brain():
    fighter = _make_fighter("A", team_id=0, x=0.0, y=0.0)
    enemy = _make_fighter("B", team_id=1, x=2.0, y=0.0)

    enemy.brain.acao_atual = "RECUAR"
    fighter.brain.janela_ataque = {"aberta": False, "tipo": None, "duracao": 0.0, "qualidade": 0.0}

    fighter.brain._atualizar_janelas_oportunidade(0.016, 2.0, enemy)

    assert fighter.brain.janela_ataque["aberta"] is True
    assert fighter.brain.janela_ataque["tipo"] == "recuando"


def test_threat_score_reads_real_weapon_profile():
    observer = _make_fighter("Observer", weapon_type="Espada Reta")
    melee = _make_fighter("Melee", weapon_type="Espada Reta")
    ranged = _make_fighter("Ranged", weapon_type="Arco", family="disparo")

    melee_score = observer.brain._calcular_ameaca_lutador(melee, distancia=4.0, vida_pct=1.0)
    ranged_score = observer.brain._calcular_ameaca_lutador(ranged, distancia=4.0, vida_pct=1.0)

    assert ranged_score > melee_score


def test_area_skill_does_not_flag_ally_outside_real_blast_zone(monkeypatch):
    caster = _make_fighter("Caster", team_id=0, x=0.0, y=0.0)
    ally = _make_fighter("Ally", team_id=0, x=3.0, y=0.0)
    enemy = _make_fighter("Enemy", team_id=1, x=4.0, y=0.0)

    caster.brain.team_orders["alive_count"] = 2
    caster.brain.multi_awareness["aliados"] = [
        {"lutador": ally, "distancia": 3.0, "angulo": 0.0, "vida_pct": 1.0}
    ]

    area_skill = SkillProfile(
        nome="AoE Teste",
        tipo="AREA",
        custo=10.0,
        cooldown=1.0,
        data={"raio_area": 2.5},
        fonte="teste",
    )

    monkeypatch.setattr("random.random", lambda: 0.0)

    assert caster.brain._aliados_em_risco_por_skill(area_skill, enemy) == []
    assert caster.brain._skill_aoe_segura_para_time(area_skill, enemy, True) is True


def test_beam_skill_detects_ally_inside_line_of_fire():
    caster = _make_fighter("BeamCaster", team_id=0, x=0.0, y=0.0)
    ally = _make_fighter("BeamAlly", team_id=0, x=2.0, y=0.0)
    enemy = _make_fighter("BeamEnemy", team_id=1, x=4.0, y=0.0)

    caster.angulo_olhar = 0.0
    caster.brain.multi_awareness["aliados"] = [
        {"lutador": ally, "distancia": 2.0, "angulo": 0.0, "vida_pct": 1.0}
    ]
    caster.brain.multi_awareness["aliado_no_caminho"] = True

    beam_skill = SkillProfile(
        nome="Beam Teste",
        tipo="BEAM",
        custo=10.0,
        cooldown=1.0,
        data={"alcance": 5.0, "largura": 8.0},
        fonte="teste",
    )

    em_risco = caster.brain._aliados_em_risco_por_skill(beam_skill, enemy)

    assert len(em_risco) == 1
    assert em_risco[0]["lutador"] is ally


def test_focus_family_uses_ranged_strategy_dispatch(monkeypatch):
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=4.0, y=0.0)
    calls = []

    def fake_ranged(*args, **kwargs):
        calls.append("ranged")
        mage.brain.acao_atual = "COMBATE"

    mage.brain._estrategia_ranged = fake_ranged
    monkeypatch.setattr("random.random", lambda: 0.5)

    mage.brain._decidir_movimento(4.0, enemy)

    assert calls == ["ranged"]
    assert mage.brain.acao_atual == "COMBATE"


def test_melee_anti_kite_recognizes_disparo_family(monkeypatch):
    melee = _make_fighter("Melee", weapon_type="Espada Reta", family="lamina")
    archer = _make_fighter("Archer", weapon_type="Arco Longo", family="disparo", team_id=1, x=4.0, y=0.0)

    monkeypatch.setattr("random.random", lambda: 0.1)

    melee.brain._decidir_movimento(4.0, archer)

    assert melee.brain.acao_atual == "APROXIMAR"


def test_hibrida_range_changes_with_form():
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")

    fighter.dados.arma_obj.forma_atual = 1
    alcance_curto = fighter.brain._calcular_alcance_efetivo()

    fighter.dados.arma_obj.forma_atual = 2
    alcance_longo = fighter.brain._calcular_alcance_efetivo()

    assert alcance_longo > alcance_curto


def test_skill_strategy_uses_family_range_for_foco():
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")

    assert mage.brain.skill_strategy is not None
    assert mage.brain.skill_strategy.preferencias["distancia_preferida"] >= 4.0


def test_orbital_family_uses_orbital_strategy_dispatch(monkeypatch):
    fighter = _make_fighter("Orbital", weapon_type="Escudo Orbital", family="orbital")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    calls = []

    def fake_orbital(*args, **kwargs):
        calls.append("orbital")
        fighter.brain.acao_atual = "PRESSIONAR"

    fighter.brain._estrategia_orbital = fake_orbital
    monkeypatch.setattr("random.random", lambda: 0.5)

    fighter.brain._decidir_movimento(3.0, enemy)

    assert calls == ["orbital"]
    assert fighter.brain.acao_atual == "PRESSIONAR"


def test_hibrida_family_uses_hybrid_strategy_dispatch(monkeypatch):
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.0, y=0.0)
    calls = []

    def fake_hybrid(*args, **kwargs):
        calls.append("hibrida")
        fighter.brain.acao_atual = "POKE"

    fighter.brain._estrategia_hibrida = fake_hybrid
    monkeypatch.setattr("random.random", lambda: 0.5)

    fighter.brain._decidir_movimento(2.0, enemy)

    assert calls == ["hibrida"]
    assert fighter.brain.acao_atual == "POKE"


def test_perception_evades_enemy_orbital_burst(monkeypatch):
    fighter = _make_fighter("Target", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("OrbitalEnemy", weapon_type="Escudo Orbital", family="orbital", team_id=1, x=2.4, y=0.0)
    enemy.orbital_burst_cd = 0.0

    fighter.brain.percepcao_arma["estrategia_recomendada"] = "neutro"
    fighter.brain.percepcao_arma["matchup_favoravel"] = 0.0
    fighter.brain.percepcao_arma["arma_inimigo_tipo"] = "orbital"
    fighter.brain.percepcao_arma["alcance_inimigo"] = 2.5

    monkeypatch.setattr("random.random", lambda: 0.0)
    monkeypatch.setattr("random.choice", lambda seq: seq[0])

    fighter.brain._aplicar_modificadores_armas(2.4, enemy)

    assert fighter.brain.acao_atual == "CIRCULAR"


def test_perception_uses_focus_orb_window(monkeypatch):
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    mage.buffer_orbes = [
        SimpleNamespace(ativo=True, estado="orbitando"),
        SimpleNamespace(ativo=True, estado="orbitando"),
    ]

    mage.brain.percepcao_arma["estrategia_recomendada"] = "neutro"
    mage.brain.percepcao_arma["matchup_favoravel"] = 0.0
    mage.brain.percepcao_arma["arma_inimigo_tipo"] = "lamina"

    monkeypatch.setattr("random.random", lambda: 0.0)
    monkeypatch.setattr("random.choice", lambda seq: seq[0])

    mage.brain._aplicar_modificadores_armas(3.0, enemy)

    assert mage.brain.acao_atual == "COMBATE"


def test_personality_adjusts_focus_skill_plan():
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    mage.brain.tracos = ["CALCULISTA", "PACIENTE"]

    mage.brain._inicializar_skill_strategy()

    assert mage.brain.skill_strategy is not None
    assert mage.brain.skill_strategy.plano.estilo == "kite"
    assert mage.brain.skill_strategy.plano.foco_mana == "conserve"


def test_pos_skill_focus_respects_orb_weave():
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    mage.buffer_orbes = [SimpleNamespace(ativo=True, estado="orbitando")]

    projectile = SkillProfile(
        nome="Proj Teste",
        tipo="PROJETIL",
        custo=10.0,
        cooldown=1.0,
        data={},
        fonte="teste",
    )

    mage.brain._pos_uso_skill_estrategica(projectile)

    assert mage.brain.acao_atual == "COMBATE"


def test_pos_skill_hybrid_transform_respects_personality():
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")
    fighter.brain.tracos = ["CALCULISTA", "PACIENTE"]
    fighter.transform_forma = 1

    transform = SkillProfile(
        nome="Forma Teste",
        tipo="TRANSFORM",
        custo=10.0,
        cooldown=1.0,
        data={},
        fonte="teste",
    )

    fighter.brain._pos_uso_skill_estrategica(transform)

    assert fighter.brain.acao_atual == "POKE"


def test_focus_prefers_skills_with_patient_personality():
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=4.0, y=0.0)
    mage.brain.tracos = ["PACIENTE", "CALCULISTA"]

    assert mage.brain._preferir_skills_neste_frame(4.0, enemy) is True


def test_orbital_prefers_basic_attack_when_burst_ready():
    fighter = _make_fighter("Orbital", weapon_type="Escudo Orbital", family="orbital")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.8, y=0.0)
    fighter.orbital_burst_cd = 0.0

    assert fighter.brain._preferir_skills_neste_frame(2.8, enemy) is False


def test_bastiao_prismatico_holds_skills_when_burst_ready_and_mana_is_tight():
    state = random.getstate()
    try:
        fighter = _make_fighter("Bastion", weapon_type="Escudo Orbital", family="orbital")
        enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.8, y=0.0)
        fighter.orbital_burst_cd = 0.0
        fighter.mana_max = 100.0
        fighter.mana = 38.0
        fighter.brain.arquetipo_composto = {
            "pacote_referencia": {"id": "bastiao_prismatico"},
        }

        assert fighter.brain._preferir_skills_neste_frame(2.8, enemy) is False
    finally:
        random.setstate(state)


def test_hybrid_long_form_prefers_skills_for_patient_profile():
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.4, y=0.0)
    fighter.transform_forma = 1
    fighter.brain.tracos = ["CALCULISTA", "ADAPTAVEL"]

    assert fighter.brain._preferir_skills_neste_frame(3.4, enemy) is True


def test_artilheiro_orbital_projectile_keeps_safe_poke_after_cast():
    state = random.getstate()
    try:
        fighter = _make_fighter("Artillery", weapon_type="Drone Orbital", family="orbital")
        fighter.brain.arquetipo_composto = {
            "pacote_referencia": {"id": "artilheiro_de_orbita"},
        }

        projectile = SkillProfile(
            nome="Proj Teste",
            tipo="PROJETIL",
            custo=10.0,
            cooldown=1.0,
            data={},
            fonte="teste",
        )

        fighter.brain._pos_uso_skill_estrategica(projectile)

        assert fighter.brain.acao_atual == "POKE"
    finally:
        random.setstate(state)


def test_corrente_sweet_spot_prefers_basic_attack():
    fighter = _make_fighter("Chain", weapon_type="Kusarigama", family="corrente")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.1, y=0.0)
    fighter.brain.tracos = ["CALCULISTA", "PACIENTE"]

    assert fighter.brain._preferir_skills_neste_frame(2.1, enemy) is False


def test_adaptive_memory_persists_longer_for_calculist_than_erratic():
    calculist = _make_fighter("Calc", weapon_type="Cetro Arcano", family="foco")
    erratic = _make_fighter("Err", weapon_type="Cetro Arcano", family="foco")
    calculist.brain.tracos = ["CALCULISTA"]
    erratic.brain.tracos = ["ERRATICO"]

    calculist.brain._registrar_aprendizado_tatico("vies_skill", 0.5)
    erratic.brain._registrar_aprendizado_tatico("vies_skill", 0.5)

    calculist.brain._decair_memoria_adaptativa(1.0)
    erratic.brain._decair_memoria_adaptativa(1.0)

    assert calculist.brain.memoria_adaptativa["vies_skill"] > erratic.brain.memoria_adaptativa["vies_skill"]


def test_failed_skill_use_pushes_adaptive_skill_bias_negative():
    fighter = _make_fighter("Focus", weapon_type="Cetro Arcano", family="foco")
    fighter.brain.tracos = []

    fighter.brain.on_skill_usada("Erro Arcano", False)
    fighter.brain.on_skill_usada("Erro Arcano", False)

    assert fighter.brain._calcular_vies_skill_adaptativo() < 0.0
    assert fighter.brain.memoria_adaptativa["vies_cautela"] > 0.0


def test_counter_success_recovers_risk_posture_after_recent_damage():
    fighter = _make_fighter("Guard", weapon_type="Kusarigama", family="corrente")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.0, y=0.0)
    fighter.brain.tracos = ["PRUDENTE"]

    fighter.brain.on_hit_recebido(18.0)
    postura_apos_hit = fighter.brain._calcular_postura_risco_adaptativa(2.0, enemy)

    fighter.brain.on_bloqueio_sucesso()
    postura_apos_bloqueio = fighter.brain._calcular_postura_risco_adaptativa(2.0, enemy)

    assert postura_apos_bloqueio > postura_apos_hit


def test_successful_pressure_can_flip_hybrid_from_skill_first_to_attack_first():
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.4, y=0.0)
    fighter.transform_forma = 1
    fighter.brain.tracos = ["CALCULISTA", "ADAPTAVEL"]

    assert fighter.brain._preferir_skills_neste_frame(3.4, enemy) is True

    fighter.brain.on_hit_dado()
    fighter.brain.on_hit_dado()
    fighter.brain.on_hit_dado()
    fighter.brain.on_inimigo_fugiu()

    assert fighter.brain._preferir_skills_neste_frame(3.4, enemy) is False


def test_opponent_specific_memory_does_not_leak_between_enemies():
    fighter = _make_fighter("Reader", weapon_type="Cetro Arcano", family="foco")
    enemy_a = _make_fighter("EnemyA", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    enemy_b = _make_fighter("EnemyB", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)

    fighter.brain._registrar_aprendizado_oponente(enemy_a, "vies_cautela", 0.4, evento="teste")

    vies_a = fighter.brain._obter_vies_oponente(enemy_a)
    vies_b = fighter.brain._obter_vies_oponente(enemy_b)

    assert vies_a["vies_cautela"] > 0.0
    assert vies_b == {}


def test_opponent_specific_aggression_can_override_skill_first_for_same_matchup():
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")
    enemy_a = _make_fighter("EnemyA", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.4, y=0.0)
    enemy_b = _make_fighter("EnemyB", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.4, y=0.0)
    fighter.transform_forma = 1
    fighter.brain.tracos = ["CALCULISTA", "ADAPTAVEL"]

    assert fighter.brain._preferir_skills_neste_frame(3.4, enemy_a) is True

    fighter.brain._registrar_aprendizado_oponente(enemy_a, "vies_agressao", 0.9, evento="pressao_funcionou")
    fighter.brain._registrar_aprendizado_oponente(enemy_a, "vies_pressao", 0.8)

    assert fighter.brain._preferir_skills_neste_frame(3.4, enemy_a) is False
    assert fighter.brain._preferir_skills_neste_frame(3.4, enemy_b) is True


def test_target_scoring_prefers_enemy_with_successful_history():
    fighter = _make_fighter("Reader", weapon_type="Cetro Arcano", family="foco")
    enemy_a = _make_fighter("EnemyA", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    enemy_b = _make_fighter("EnemyB", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)

    info_a = {"lutador": enemy_a, "distancia": 3.0, "ameaca": 0.5, "vida_pct": 1.0}
    info_b = {"lutador": enemy_b, "distancia": 3.0, "ameaca": 0.5, "vida_pct": 1.0}

    fighter.brain._registrar_aprendizado_oponente(enemy_a, "vies_pressao", 0.7)
    fighter.brain._registrar_aprendizado_oponente(enemy_a, "vies_agressao", 0.4)

    assert fighter.brain._score_alvo(info_a) > fighter.brain._score_alvo(info_b)


def test_pattern_detection_marks_aggressive_entry():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)

    enemy.brain.acao_atual = "APROXIMAR"
    fighter.brain._observar_oponente(enemy, 3.0)
    enemy.brain.acao_atual = "MATAR"
    fighter.brain._observar_oponente(enemy, 3.0)

    assert fighter.brain.memoria_oponente["padrao_dominante"] == "entrada_agressiva"


def test_known_aggressive_entry_triggers_counter_reaction_for_calculist():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    fighter.brain.tracos = ["CALCULISTA"]

    fighter.brain._registrar_padrao_oponente(enemy, "entrada_agressiva", 1.2)
    fighter.brain.reacao_pendente = None
    fighter.brain._gerar_reacao_inteligente("MATAR", 3.0, enemy)

    assert fighter.brain.reacao_pendente == "CONTRA_ATAQUE"


def test_orbital_burst_pattern_triggers_escape_reaction():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("OrbitalEnemy", weapon_type="Escudo Orbital", family="orbital", team_id=1, x=2.8, y=0.0)
    enemy.orbital_burst_cd = 0.0

    fighter.brain._observar_oponente(enemy, 2.8)
    fighter.brain.reacao_pendente = None
    fighter.brain._gerar_reacao_inteligente("COMBATE", 2.8, enemy)

    assert fighter.brain.memoria_oponente["padrao_dominante"] == "prepara_burst_orbital"
    assert fighter.brain.reacao_pendente in {"ESQUIVAR", "RECUAR"}


def test_hybrid_burst_swap_pattern_triggers_cautious_response():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("HybridEnemy", weapon_type="Transformavel", family="hibrida", team_id=1, x=3.5, y=0.0)
    fighter.brain.tracos = ["PACIENTE"]

    enemy.transform_forma = 0
    fighter.brain._observar_oponente(enemy, 3.5)
    enemy.transform_forma = 1
    enemy.transform_bonus_timer = 1.0
    fighter.brain._observar_oponente(enemy, 3.5)
    fighter.brain.reacao_pendente = None
    fighter.brain._gerar_reacao_inteligente("COMBATE", 3.5, enemy)

    assert fighter.brain.memoria_oponente["padrao_dominante"] == "troca_forma_burst"
    assert fighter.brain.reacao_pendente == "CIRCULAR"


def test_pattern_window_opens_for_aggressive_entry_punish():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.2, y=0.0)

    fighter.brain._registrar_padrao_oponente(enemy, "entrada_agressiva", 1.1)
    enemy.brain.acao_atual = "APROXIMAR"
    fighter.brain.janela_ataque = {"aberta": False, "tipo": None, "duracao": 0.0, "qualidade": 0.0}

    fighter.brain._atualizar_janelas_oportunidade(0.016, 3.2, enemy)

    assert fighter.brain.janela_ataque["aberta"] is True
    assert fighter.brain.janela_ataque["tipo"] == "punir_entrada"


def test_pattern_window_opens_for_reactive_guard_break():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.6, y=0.0)

    fighter.brain._registrar_padrao_oponente(enemy, "guarda_reativa", 1.0)
    enemy.brain.acao_atual = "BLOQUEAR"
    fighter.brain.janela_ataque = {"aberta": False, "tipo": None, "duracao": 0.0, "qualidade": 0.0}

    fighter.brain._atualizar_janelas_oportunidade(0.016, 2.6, enemy)

    assert fighter.brain.janela_ataque["tipo"] == "quebrar_guarda_lida"


def test_attack_opportunity_uses_pattern_specific_action_for_entry_punish():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    fighter.brain.tracos = ["CALCULISTA"]

    janela = {"tipo": "punir_entrada", "qualidade": 0.9}
    fighter.brain._executar_ataque_oportunidade(janela, 3.0, enemy)

    assert fighter.brain.acao_atual == "CONTRA_ATAQUE"


def test_baiting_prefers_opening_fake_against_aggressive_entry(monkeypatch):
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=4.0, y=0.0)
    fighter.brain.tracos = ["TRICKSTER", "CALCULISTA"]
    fighter.brain.momentum = -0.6
    fighter.brain.leitura_oponente["agressividade_percebida"] = 0.8
    fighter.brain._registrar_padrao_oponente(enemy, "entrada_agressiva", 1.2)

    monkeypatch.setattr("random.random", lambda: 0.0)
    monkeypatch.setattr("random.choice", lambda seq: seq[0])
    monkeypatch.setattr("random.uniform", lambda a, b: 0.4)

    assert fighter.brain._processar_baiting(0.016, 4.0, enemy) is True
    assert fighter.brain.bait_state["tipo"] == "abertura_falsa"


def test_hybrid_pattern_punish_schedules_followup_combo():
    fighter = _make_fighter("Hybrid", weapon_type="Transformavel", family="hibrida")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.4, y=0.0)
    fighter.transform_forma = 1
    fighter.brain.tracos = ["PACIENTE", "CALCULISTA"]

    janela = {"tipo": "punir_troca_burst", "qualidade": 0.9}
    fighter.brain._executar_ataque_oportunidade(janela, 3.4, enemy)

    assert fighter.brain.acao_atual == "POKE"
    assert fighter.brain.combo_state["followup_forcado"] == "COMBATE"


def test_forced_followup_is_consumed_before_generic_combo_logic():
    fighter = _make_fighter("Orbital", weapon_type="Escudo Orbital", family="orbital")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.8, y=0.0)
    fighter.brain.combo_state["em_combo"] = True
    fighter.brain.combo_state["pode_followup"] = True
    fighter.brain.combo_state["timer_followup"] = 0.4
    fighter.brain.combo_state["followup_forcado"] = "COMBATE"
    fighter.brain.combo_state["ultimo_tipo_ataque"] = "ATAQUE_RAPIDO"

    assert fighter.brain._tentar_followup(2.8, enemy) is True
    assert fighter.brain.acao_atual == "COMBATE"
    assert fighter.brain.combo_state["followup_forcado"] is None


def test_corrente_entry_punish_gets_heavy_followup():
    fighter = _make_fighter("Chain", weapon_type="Kusarigama", family="corrente")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.4, y=0.0)

    janela = {"tipo": "punir_entrada", "qualidade": 0.9}
    fighter.brain._executar_ataque_oportunidade(janela, 2.4, enemy)

    assert fighter.brain.acao_atual == "CONTRA_ATAQUE"
    assert fighter.brain.combo_state["followup_forcado"] == "ESMAGAR"


def test_decay_of_opponent_memory_handles_nested_pattern_dict_without_crashing():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Escudo Orbital", family="orbital", team_id=1, x=2.8, y=0.0)

    fighter.brain._registrar_aprendizado_oponente(enemy, "vies_agressao", 0.4, evento="teste")
    fighter.brain._registrar_padrao_oponente(enemy, "prepara_burst_orbital", 1.0)

    fighter.brain._decair_memoria_curta_oponentes(0.5)

    bucket = fighter.brain._obter_vies_oponente(enemy)
    assert isinstance(bucket.get("padroes"), dict)
    assert bucket.get("padrao_dominante") in {"prepara_burst_orbital", None}


def test_assassin_signature_turns_entry_punish_into_fast_flank_sequence():
    fighter = _make_fighter("Assassin", weapon_type="Adagas", family="dupla")
    fighter.brain.arquetipo = "ASSASSINO"

    opener, followup, timer, _, _ = fighter.brain._resolver_plano_punish("punir_entrada", 2.4, None)

    assert opener == "ATAQUE_RAPIDO"
    assert followup == "FLANQUEAR"
    assert timer < 0.45


def test_calm_calculist_signature_makes_punish_more_controlled():
    fighter = _make_fighter("Tactician", weapon_type="Espada Reta", family="lamina")
    fighter.brain.tracos = ["CALCULISTA", "PACIENTE"]
    fighter.brain.humor = "GLACIAL"

    opener, followup, timer, _, _ = fighter.brain._resolver_plano_punish("punir_recuo", 3.0, None)

    assert opener == "APROXIMAR"
    assert followup == "COMBATE"
    assert timer > 0.45


def test_berserker_signature_escalates_followup_and_energy():
    fighter = _make_fighter("Berserker", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=2.8, y=0.0)
    fighter.brain.arquetipo = "BERSERKER"
    fighter.brain.humor = "FURIOSO"

    janela = {"tipo": "punir_troca_burst", "qualidade": 0.9}
    fighter.brain._executar_ataque_oportunidade(janela, 2.8, enemy)

    assert fighter.brain.combo_state["followup_forcado"] in {"ESMAGAR", "PRESSIONAR"}
    assert fighter.brain.combo_state["timer_followup"] < 0.45
    assert fighter.brain.adrenalina > 0.0


def test_emotional_fear_softens_punish_tone():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain.medo = 0.8
    fighter.brain.confianca = 0.3

    opener, followup, timer, _, _ = fighter.brain._resolver_plano_punish("punir_entrada", 2.5, None)

    assert opener == "CONTRA_ATAQUE"
    assert followup == "COMBATE"
    assert timer >= 0.52


def test_euphoric_state_accelerates_and_hardens_punish():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain.humor = "EUFORICO"
    fighter.brain.raiva = 0.85
    fighter.brain.excitacao = 0.9
    fighter.brain.momentum = 0.5

    opener, followup, timer, _, adrenalina = fighter.brain._resolver_plano_punish("punir_recuo", 3.0, None)

    assert opener == "MATAR"
    assert followup in {"ESMAGAR", "PRESSIONAR"}
    assert timer <= 0.32
    assert adrenalina >= 0.10


def test_high_confidence_pushes_followup_into_pressure():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain.confianca = 0.9
    fighter.brain.momentum = 0.35
    fighter.brain.medo = 0.1

    opener, followup, timer, _, _ = fighter.brain._resolver_plano_punish("punir_recuo", 3.0, None)

    assert opener == "APROXIMAR"
    assert followup == "PRESSIONAR"
    assert timer <= 0.40


def test_combo_streak_activates_scene_memory():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")

    fighter.brain.on_hit_dado()
    fighter.brain.on_hit_dado()
    fighter.brain.on_hit_dado()
    fighter.brain.on_hit_dado()

    assert fighter.brain.memoria_cena["tipo"] == "sequencia_perfeita"
    assert fighter.brain.memoria_cena["duracao"] > 0.0


def test_near_death_hit_activates_quase_morte_scene():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.vida = fighter.vida_max * 0.18

    fighter.brain.on_hit_recebido(20.0)

    assert fighter.brain.memoria_cena["tipo"] == "quase_morte"


def test_scene_memory_decays_and_clears():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain._ativar_memoria_cena("dominando", 0.7, 0.2)

    fighter.brain._decair_memoria_cena(0.3)

    assert fighter.brain.memoria_cena["tipo"] is None
    assert fighter.brain.memoria_cena["intensidade"] == 0.0


def test_sequencia_perfeita_scene_pushes_punish_into_pressure():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain._ativar_memoria_cena("sequencia_perfeita", 0.9, 1.5)

    opener, followup, timer, _, _ = fighter.brain._resolver_plano_punish("punir_recuo", 3.0, None)

    assert followup == "PRESSIONAR"
    assert timer <= 0.33


def test_quase_morte_scene_softens_punish_even_when_angry():
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    fighter.brain.humor = "EUFORICO"
    fighter.brain.raiva = 0.9
    fighter.brain.excitacao = 0.9
    fighter.brain.momentum = 0.6
    fighter.brain._ativar_memoria_cena("quase_morte", 0.9, 1.8)

    opener, followup, timer, _, _ = fighter.brain._resolver_plano_punish("punir_entrada", 2.6, None)

    assert opener == "CONTRA_ATAQUE"
    assert followup == "COMBATE"
    assert timer >= 0.54


def test_pressao_ritmo_breaks_retreat_bias(monkeypatch):
    fighter = _make_fighter("Reader", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.4, y=0.0)

    fighter.brain.medo = 0.85
    fighter.brain.confianca = 0.2
    fighter.brain.momentum = -0.5
    fighter.brain.pressao_ritmo = 0.95

    monkeypatch.setattr("random.random", lambda: 0.99)

    fighter.brain._decidir_movimento(3.4, enemy)

    assert fighter.brain.acao_atual in {"APROXIMAR", "PRESSIONAR", "COMBATE", "MATAR"}


def test_skill_arena_context_boosts_escape_when_inside_danger_zone():
    fighter = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)

    dash = SkillProfile(
        nome="Passo Astral",
        tipo="DASH",
        custo=10.0,
        cooldown=1.0,
        data={"teleporte": True},
        fonte="teste",
    )
    poke = SkillProfile(
        nome="Raio Fraco",
        tipo="PROJETIL",
        custo=10.0,
        cooldown=1.0,
        data={},
        fonte="teste",
    )

    fighter.brain.consciencia_espacial["zona_perigo_atual"] = "lava"

    dash_chance = fighter.brain._modular_chance_skill_por_arena(0.5, dash, 3.0)
    poke_chance = fighter.brain._modular_chance_skill_por_arena(0.5, poke, 3.0)

    assert dash_chance > poke_chance
    assert dash_chance > 0.5


def test_skill_arena_context_boosts_control_when_enemy_in_danger_zone():
    fighter = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")

    control = SkillProfile(
        nome="Prisao Arcana",
        tipo="CONTROL",
        custo=10.0,
        cooldown=1.0,
        data={"root": 1.5},
        fonte="teste",
    )
    burst = SkillProfile(
        nome="Lanca Arcana",
        tipo="PROJETIL",
        custo=10.0,
        cooldown=1.0,
        data={},
        fonte="teste",
    )

    fighter.brain.consciencia_espacial["zona_perigo_inimigo"] = "fogo"
    fighter.brain.consciencia_espacial["oponente_contra_parede"] = True

    control_chance = fighter.brain._modular_chance_skill_por_arena(0.5, control, 4.0)
    burst_chance = fighter.brain._modular_chance_skill_por_arena(0.5, burst, 4.0)

    assert control_chance > burst_chance
    assert control_chance > 0.5


def test_skill_context_snapshot_tracks_team_and_enemy_state():
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)

    mage.buffer_orbes = [
        SimpleNamespace(ativo=True, estado="orbitando"),
        SimpleNamespace(ativo=True, estado="orbitando"),
    ]
    mage.brain.team_orders.update({"alive_count": 2, "role": "SUPPORT", "is_weakest": False})
    mage.brain.leitura_oponente["reposicionando"] = True
    mage.brain.leitura_oponente["ataque_iminente"] = True
    mage.brain.consciencia_espacial["zona_perigo_atual"] = "lava"
    enemy.stun_timer = 1.0
    enemy.status_effects = [SimpleNamespace(nome="burning"), SimpleNamespace(nome="frozen")]
    enemy.dots_ativos = [SimpleNamespace(tipo="QUEIMANDO")]

    ctx = mage.brain._criar_contexto_skills(0.016, 3.0, enemy)

    assert ctx is not None
    assert ctx.familia_arma == "foco"
    assert ctx.orbes_orbitando == 2
    assert ctx.has_team is True
    assert ctx.team_role == "SUPPORT"
    assert ctx.inimigo_stunado is True
    assert ctx.inimigo_queimando is True
    assert ctx.inimigo_congelado is True
    assert ctx.inimigo_reposicionando is True
    assert ctx.inimigo_atk_iminente is True
    assert ctx.eu_em_zona is True


def test_skill_pipeline_stops_at_first_priority_handler(monkeypatch):
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    calls = []
    sentinel_ctx = SimpleNamespace(marker=True)
    order = [
        "_tentar_prioridade_time_skills",
        "_tentar_prioridade_sobrevivencia_skills",
        "_tentar_prioridade_reacao_skills",
        "_tentar_prioridade_janela_cc_skills",
        "_tentar_prioridade_combo_skills",
        "_tentar_prioridade_execucao_skills",
        "_tentar_prioridade_burst_skills",
        "_tentar_prioridade_opener_skills",
        "_tentar_prioridade_poke_skills",
        "_tentar_prioridade_manutencao_skills",
    ]

    monkeypatch.setattr(mage.brain, "_criar_contexto_skills", lambda *args: sentinel_ctx)

    for name in order:
        def _make_handler(label):
            return lambda ctx, target, _label=label: calls.append(_label) or (_label == "_tentar_prioridade_execucao_skills")

        monkeypatch.setattr(mage.brain, name, _make_handler(name))

    monkeypatch.setattr(mage.brain, "_tentar_prioridade_rotacao_skills", lambda *args: calls.append("rotacao") or True)

    assert mage.brain._processar_skills_estrategico(0.016, 3.0, enemy) is True
    assert calls == order[: order.index("_tentar_prioridade_execucao_skills") + 1]


def test_skill_pipeline_uses_rotation_after_priority_chain(monkeypatch):
    mage = _make_fighter("Mage", weapon_type="Cetro Arcano", family="foco")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    calls = []
    sentinel_ctx = SimpleNamespace(marker=True)
    order = [
        "_tentar_prioridade_time_skills",
        "_tentar_prioridade_sobrevivencia_skills",
        "_tentar_prioridade_reacao_skills",
        "_tentar_prioridade_janela_cc_skills",
        "_tentar_prioridade_combo_skills",
        "_tentar_prioridade_execucao_skills",
        "_tentar_prioridade_burst_skills",
        "_tentar_prioridade_opener_skills",
        "_tentar_prioridade_poke_skills",
        "_tentar_prioridade_manutencao_skills",
    ]

    monkeypatch.setattr(mage.brain, "_criar_contexto_skills", lambda *args: sentinel_ctx)

    for name in order:
        monkeypatch.setattr(mage.brain, name, lambda ctx, target, _label=name: calls.append(_label) or False)

    monkeypatch.setattr(
        mage.brain,
        "_tentar_prioridade_rotacao_skills",
        lambda ctx, target: calls.append("rotacao") or True,
    )

    assert mage.brain._processar_skills_estrategico(0.016, 3.0, enemy) is True
    assert calls == order + ["rotacao"]


def test_generic_combat_context_tracks_matchup_and_stall_state():
    fighter = _make_fighter("Melee", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Archer", weapon_type="Arco Longo", family="disparo", team_id=1, x=4.0, y=0.0)
    fighter.brain.tempo_desde_hit = 4.0
    fighter.atacando = False
    fighter.brain.pressao_ritmo = 0.7

    ctx = fighter.brain._criar_contexto_combate_generico(
        distancia=4.0,
        roll=0.5,
        hp_pct=1.0,
        inimigo_hp_pct=1.0,
        alcance_efetivo=2.0,
        alcance_ideal=1.5,
        inimigo=enemy,
    )

    assert ctx.minha_familia == "lamina"
    assert ctx.familia_inimigo == "disparo"
    assert ctx.sou_ranged is False
    assert ctx.stall_approaching is True
    assert ctx.longe is True
    assert ctx.pressao_ritmo == pytest.approx(0.7)


def test_generic_combat_strategy_runs_extracted_phases_in_order(monkeypatch):
    fighter = _make_fighter("Melee", weapon_type="Espada Reta", family="lamina")
    enemy = _make_fighter("Enemy", weapon_type="Espada Reta", family="lamina", team_id=1, x=3.0, y=0.0)
    calls = []
    sentinel_ctx = SimpleNamespace(marker=True)
    sentinel_bp = {"retreat_weight": 1.0}

    monkeypatch.setattr(fighter.brain, "_criar_contexto_combate_generico", lambda *args: sentinel_ctx)
    monkeypatch.setattr(fighter.brain, "_votar_base_generica", lambda ctx, pesos: calls.append("base"))
    monkeypatch.setattr(
        fighter.brain,
        "_votar_profile_traits_generico",
        lambda ctx, pesos: calls.append("profile") or sentinel_bp,
    )
    monkeypatch.setattr(
        fighter.brain,
        "_votar_estilo_emocao_generico",
        lambda ctx, pesos, bp: calls.append(("estilo", bp)),
    )
    monkeypatch.setattr(fighter.brain, "_votar_leitura_oponente_generico", lambda ctx, pesos: calls.append("leitura"))
    monkeypatch.setattr(fighter.brain, "_votar_modificadores_externos_generico", lambda ctx, pesos: calls.append("externos"))
    monkeypatch.setattr(fighter.brain, "_votar_time_generico", lambda ctx, pesos: calls.append("time"))
    monkeypatch.setattr(fighter.brain, "_compensar_matchup_generico", lambda ctx, pesos, bp: calls.append(("matchup", bp)))
    monkeypatch.setattr(fighter.brain, "_aplicar_anti_repeticao_generico", lambda ctx, pesos: calls.append("anti"))
    monkeypatch.setattr(
        fighter.brain,
        "_escolher_acao_generica",
        lambda ctx, pesos, debug=False: calls.append(("escolher", debug)) or "COMBATE",
    )

    fighter.brain._estrategia_generica(3.0, 0.5, 1.0, 1.0, 2.0, 1.5, enemy, debug=True)

    assert fighter.brain.acao_atual == "COMBATE"
    assert calls == [
        "base",
        "profile",
        ("estilo", sentinel_bp),
        "leitura",
        "externos",
        "time",
        ("matchup", sentinel_bp),
        "anti",
        ("escolher", True),
    ]

