"""Runtime-focused regression tests for active AI flow."""

import random
from types import SimpleNamespace

import pytest

from ia.skill_strategy import SkillProfile
from nucleo.entities import Lutador
from modelos import Arma, Personagem
from simulacao.sim_combat import AttackImpactVector, SimuladorCombat
from utilitarios.config import PPM


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
    sim.impact_flashes = []
    sim.magic_clashes = []
    sim.shockwaves = []
    sim.hit_sparks = []
    sim.hit_stop_timer = 0.0
    sim.time_scale = 1.0
    sim.slow_mo_timer = 0.0
    sim.game_feel = None
    sim.choreographer = None
    sim.attack_anims = None
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

    def record_attack_attempt(self, *args, **kwargs):
        self.attempts.append((args, kwargs))

    def record_hit(self, *args, **kwargs):
        self.hits.append((args, kwargs))

    def record_death(self, *args, **kwargs):
        self.deaths.append((args, kwargs))


def test_combat_helper_blocks_direct_hitbox_for_ranged_types():
    sim = _make_sim_stub()

    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="Arremesso")) is False
    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="Arco")) is False
    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="MÃ¡gica")) is False
    assert SimuladorCombat._arma_usa_hitbox_direta(sim, SimpleNamespace(tipo="Reta")) is True


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
    sim = _make_sim_stub()
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
    resultado = SimuladorCombat._aplicar_mecanicas_corrente(sim, atacante, defensor, arma, 12.0, vetor)

    assert resultado.dano == pytest.approx(24.0)
    assert resultado.knockback_mult == pytest.approx(0.5)
    assert resultado.label == "CRACK!"
    assert defensor.atacando is False
    assert defensor.cooldown_ataque == pytest.approx(0.3)


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

