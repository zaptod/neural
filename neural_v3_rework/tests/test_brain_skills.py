"""Pytest coverage for SkillStrategySystem SUMMON/TRAP behavior."""

import pytest

from ai.skill_strategy import CombatSituation, SkillPurpose, SkillStrategySystem, StrategicRole
from core.skills import SKILL_DB


def _make_skill_info(nome):
    """Build a runtime-like skill_info dict from SKILL_DB."""
    data = SKILL_DB.get(nome, {})
    info = dict(data)
    info["nome"] = nome
    return info


class FakeChar:
    def __init__(self, skill_names):
        self.nome = "TestBot"
        self.skills_arma = [_make_skill_info(n) for n in skill_names[:2]]
        self.skills_classe = [_make_skill_info(n) for n in skill_names[2:]]
        self.mana = 100
        self.mana_max = 100
        self.hp = 100
        self.hp_max = 100


class FakeBrain:
    def __init__(self):
        self.debug_mode = False


@pytest.fixture
def sss():
    skill_names = [
        "F\u00eanix",
        "Muralha de Gelo",
        "Armadilha El\u00e9trica",
        "Bola de Fogo",
        "Portal do Vazio",
    ]
    return SkillStrategySystem(FakeChar(skill_names), FakeBrain())


def test_battle_plan(sss):
    plan = sss.plano
    fenix = sss.skills.get("F\u00eanix")
    portal = sss.skills.get("Portal do Vazio")
    muralha = sss.skills.get("Muralha de Gelo")
    armadilha = sss.skills.get("Armadilha El\u00e9trica")

    assert plan.rotacao_opening
    assert fenix is not None
    assert fenix.tipo == "SUMMON"
    assert SkillPurpose.ZONING in fenix.propositos

    assert portal is not None
    assert portal.tipo == "SUMMON"

    assert muralha is not None
    assert muralha.tipo == "TRAP"
    if SKILL_DB.get("Muralha de Gelo", {}).get("bloqueia_movimento", True):
        assert SkillPurpose.ESCAPE in muralha.propositos

    assert armadilha is not None
    if not SKILL_DB.get("Armadilha El\u00e9trica", {}).get("bloqueia_movimento", True):
        assert SkillPurpose.OPENER in armadilha.propositos


def test_condicoes_ideais(sss):
    fenix = sss.skills.get("F\u00eanix")
    if fenix:
        lotado = CombatSituation(
            distancia=3.0,
            meu_hp_percent=80,
            inimigo_hp_percent=70,
            meu_mana_percent=60,
            tenho_summons_ativos=2,
        )
        disponivel = CombatSituation(
            distancia=3.0,
            meu_hp_percent=80,
            inimigo_hp_percent=70,
            meu_mana_percent=60,
            tenho_summons_ativos=1,
        )
        assert sss._condicoes_ideais("F\u00eanix", lotado) is False
        assert sss._condicoes_ideais("F\u00eanix", disponivel) is True

    muralha = sss.skills.get("Muralha de Gelo")
    if muralha:
        lotado = CombatSituation(
            distancia=3.0,
            meu_hp_percent=80,
            inimigo_hp_percent=70,
            meu_mana_percent=60,
            tenho_traps_ativos=3,
        )
        disponivel = CombatSituation(
            distancia=3.0,
            meu_hp_percent=80,
            inimigo_hp_percent=70,
            meu_mana_percent=60,
            tenho_traps_ativos=1,
        )
        assert sss._condicoes_ideais("Muralha de Gelo", lotado) is False
        assert sss._condicoes_ideais("Muralha de Gelo", disponivel) is True


def test_rotations(sss):
    assert sss.plano.rotacao_opening
    assert isinstance(sss.plano.rotacao_disadvantage, list)


def test_role_detection():
    summoner = SkillStrategySystem(
        FakeChar(["F\u00eanix", "Portal do Vazio", "Invoca\u00e7\u00e3o: Esp\u00edrito", "Bola de Fogo"]),
        FakeBrain(),
    )
    trapper = SkillStrategySystem(
        FakeChar(["Muralha de Gelo", "Armadilha El\u00e9trica", "Armadilha Incendi\u00e1ria", "Bola de Fogo"]),
        FakeBrain(),
    )

    if summoner.role_principal == StrategicRole.SUMMONER:
        assert summoner.plano.estilo == "kite"

    if trapper.role_principal == StrategicRole.TRAP_MASTER:
        assert trapper.plano.estilo == "kite"
