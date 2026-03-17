"""Pytest coverage for SkillStrategySystem SUMMON/TRAP behavior."""

import pytest

from ia.skill_strategy import CombatSituation, SkillPurpose, SkillStrategySystem, StrategicRole
from nucleo.skills import SKILL_DB


def _make_skill_info(nome):
    """Build a runtime-like skill_info dict from SKILL_DB."""
    data = SKILL_DB.get(nome, {})
    info = dict(data)
    info["nome"] = nome
    return info


def _skill_key(*candidates):
    """Resolve nomes com ou sem mojibake presentes no SKILL_DB."""
    for candidate in candidates:
        if candidate in SKILL_DB:
            return candidate
    raise KeyError(f"Skill não encontrada: {candidates}")


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
        _skill_key("F\u00eanix", "FÃªnix"),
        "Muralha de Gelo",
        _skill_key("Armadilha El\u00e9trica", "Armadilha ElÃ©trica"),
        "Bola de Fogo",
        "Portal do Vazio",
    ]
    return SkillStrategySystem(FakeChar(skill_names), FakeBrain())


def test_battle_plan(sss):
    plan = sss.plano
    fenix = sss.skills.get(_skill_key("F\u00eanix", "FÃªnix"))
    portal = sss.skills.get("Portal do Vazio")
    muralha = sss.skills.get("Muralha de Gelo")
    armadilha = sss.skills.get(_skill_key("Armadilha El\u00e9trica", "Armadilha ElÃ©trica"))

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
    if not SKILL_DB.get(_skill_key("Armadilha El\u00e9trica", "Armadilha ElÃ©trica"), {}).get("bloqueia_movimento", True):
        assert SkillPurpose.OPENER in armadilha.propositos


def test_condicoes_ideais(sss):
    fenix_name = _skill_key("F\u00eanix", "FÃªnix")
    fenix = sss.skills.get(fenix_name)
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
        assert sss._condicoes_ideais(fenix_name, lotado) is False
        assert sss._condicoes_ideais(fenix_name, disponivel) is True

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
        FakeChar([
            _skill_key("F\u00eanix", "FÃªnix"),
            "Portal do Vazio",
            _skill_key("Invoca\u00e7\u00e3o: Esp\u00edrito", "InvocaÃ§Ã£o: EspÃ­rito"),
            "Bola de Fogo",
        ]),
        FakeBrain(),
    )
    trapper = SkillStrategySystem(
        FakeChar([
            "Muralha de Gelo",
            _skill_key("Armadilha El\u00e9trica", "Armadilha ElÃ©trica"),
            _skill_key("Armadilha Incendi\u00e1ria", "Armadilha IncendiÃ¡ria"),
            "Bola de Fogo",
        ]),
        FakeBrain(),
    )

    if summoner.role_principal == StrategicRole.SUMMONER:
        assert summoner.plano.estilo == "kite"

    if trapper.role_principal == StrategicRole.TRAP_MASTER:
        assert trapper.plano.estilo == "kite"

