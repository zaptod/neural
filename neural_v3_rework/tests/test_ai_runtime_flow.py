"""Runtime-focused regression tests for active AI flow."""

from types import SimpleNamespace

import pytest

from ai.skill_strategy import SkillProfile
from core.entities import Lutador
from models import Arma, Personagem
from simulation.sim_combat import SimuladorCombat


def _make_fighter(nome, weapon_type="Espada Reta", team_id=0, x=0.0, y=0.0):
    arma = Arma(
        nome=f"{weapon_type} de Teste",
        tipo=weapon_type,
        dano=8,
        peso=2,
        velocidade_ataque=1.0,
    )
    dados = Personagem(
        nome=nome,
        tamanho=1.5,
        forca=5.0,
        mana=5.0,
        classe="Guerreiro (ForÃ§a Bruta)",
    )
    dados.recalcular_com_arma(arma)
    return Lutador(dados, x, y, team_id=team_id)


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
    ranged = _make_fighter("Ranged", weapon_type="Arco")

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
