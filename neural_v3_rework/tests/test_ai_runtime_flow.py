"""Runtime-focused regression tests for active AI flow."""

import random
from types import SimpleNamespace

import pytest

from ia.skill_strategy import SkillProfile
from nucleo.entities import Lutador
from modelos import Arma, Personagem
from simulacao.sim_combat import SimuladorCombat


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


def test_lutador_ai_alias_points_to_brain():
    fighter = _make_fighter("Alias")

    assert fighter.ai is fighter.brain

    replacement = SimpleNamespace(marker=True)
    fighter.ai = replacement

    assert fighter.brain is replacement
    assert fighter.ai is replacement


def test_block_and_parry_callbacks_reach_brain():
    fighter = _make_fighter("Defensor")
    sim = _make_sim_stub()
    proj = SimpleNamespace(x=1.0, y=1.0)
    calls = []

    fighter.brain.on_bloqueio_sucesso = lambda: calls.append("ok")

    SimuladorCombat._efeito_bloqueio(sim, proj, fighter, (0.0, 0.0))
    SimuladorCombat._efeito_parry(sim, proj, fighter)

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

