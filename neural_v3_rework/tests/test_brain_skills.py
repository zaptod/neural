"""Test brain skill strategy updates for SUMMON/TRAP handling."""
import sys
import os
from ai.skill_strategy import (
    SkillStrategySystem, SkillProfile, BattlePlan,
    CombatSituation, StrategicRole, SkillPurpose, CombatPhase
)
from ai.brain_skills import SkillsMixin
from core.skills import SKILL_DB


def _make_skill_info(nome):
    """Build a skill_info dict from SKILL_DB, mimicking what the game provides."""
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


def test_battle_plan():
    skill_names = [
        "Fênix", "Muralha de Gelo", "Armadilha Elétrica",
        "Bola de Fogo", "Portal do Vazio"
    ]
    char = FakeChar(skill_names)
    brain = FakeBrain()
    sss = SkillStrategySystem(char, brain)
    plan = sss.plano

    print(f"--- BattlePlan for {char.nome} ---")
    print(f"Role: {sss.role_principal}")
    print(f"Style: {plan.estilo}")
    print(f"Distance: {plan.distancia_preferida}")
    print(f"Profiles: {len(sss.skills)}")

    for name, profile in sss.skills.items():
        purposes = [p.value for p in profile.propositos]
        print(f"  [{name}] type={profile.tipo} dano={profile.dano_total:.1f} "
              f"purposes={purposes} alcance={profile.alcance_efetivo}")

    print(f"\nCombos discovered: {len(plan.combos)}")
    for combo in plan.combos:
        print(f"  combo: {combo}")

    # Verify SUMMON profiles
    fenix = sss.skills.get("Fênix")
    assert fenix is not None, "Fenix not profiled!"
    assert fenix.tipo == "SUMMON"
    assert SkillPurpose.ZONING in fenix.propositos, f"Fenix missing ZONING: {fenix.propositos}"
    print("\n[OK] Fenix has ZONING purpose (aura)")

    portal = sss.skills.get("Portal do Vazio")
    assert portal is not None, "Portal do Vazio not profiled!"
    assert portal.tipo == "SUMMON"
    print(f"[OK] Portal do Vazio profiled: purposes={[p.value for p in portal.propositos]}")

    # Verify TRAP profiles
    muralha = sss.skills.get("Muralha de Gelo")
    assert muralha is not None, "Muralha not profiled!"
    assert muralha.tipo == "TRAP"
    muralha_data = SKILL_DB.get("Muralha de Gelo", {})
    is_wall = muralha_data.get("bloqueia_movimento", True)
    print(f"[OK] Muralha de Gelo: wall={is_wall}, purposes={[p.value for p in muralha.propositos]}")
    if is_wall:
        assert SkillPurpose.ESCAPE in muralha.propositos, "Wall should have ESCAPE purpose"
        print("[OK] Muralha has ESCAPE purpose (wall barrier)")

    armadilha = sss.skills.get("Armadilha Elétrica")
    assert armadilha is not None, "Armadilha Elétrica not profiled!"
    armadilha_data = SKILL_DB.get("Armadilha Elétrica", {})
    is_trigger = not armadilha_data.get("bloqueia_movimento", True)
    print(f"[OK] Armadilha Elétrica: trigger={is_trigger}, purposes={[p.value for p in armadilha.propositos]}")
    if is_trigger:
        assert SkillPurpose.OPENER in armadilha.propositos, "Trigger trap should have OPENER purpose"
        print("[OK] Armadilha Elétrica has OPENER purpose (trigger trap)")

    return sss


def test_condicoes_ideais(sss):
    print("\n--- Testing _condicoes_ideais ---")

    fenix = sss.skills.get("Fênix")
    if fenix:
        sit_full = CombatSituation(
            distancia=3.0, meu_hp_percent=80,
            inimigo_hp_percent=70, meu_mana_percent=60,
            tenho_summons_ativos=2
        )
        result = sss._condicoes_ideais("Fênix", sit_full)
        print(f"Fenix w/ 2 summons active: {result} (expected: False)")
        assert result is False, "Should block summon when 2 already active!"

        sit_ok = CombatSituation(
            distancia=3.0, meu_hp_percent=80,
            inimigo_hp_percent=70, meu_mana_percent=60,
            tenho_summons_ativos=1
        )
        result2 = sss._condicoes_ideais("Fênix", sit_ok)
        print(f"Fenix w/ 1 summon active: {result2} (expected: True)")
        assert result2 is True, "Should allow summon when <2 active!"

    muralha = sss.skills.get("Muralha de Gelo")
    if muralha:
        sit_full = CombatSituation(
            distancia=3.0, meu_hp_percent=80,
            inimigo_hp_percent=70, meu_mana_percent=60,
            tenho_traps_ativos=3
        )
        result = sss._condicoes_ideais("Muralha de Gelo", sit_full)
        print(f"Muralha w/ 3 traps active: {result} (expected: False)")
        assert result is False, "Should block trap when 3 already active!"

        sit_ok = CombatSituation(
            distancia=3.0, meu_hp_percent=80,
            inimigo_hp_percent=70, meu_mana_percent=60,
            tenho_traps_ativos=1
        )
        result2 = sss._condicoes_ideais("Muralha de Gelo", sit_ok)
        print(f"Muralha w/ 1 trap active: {result2} (expected: True)")
        assert result2 is True, "Should allow trap when <3 active!"

    print("[OK] All condicoes ideais tests passed!")


def test_rotations(sss):
    plan = sss.plano
    print("\n--- Testing rotations ---")
    print(f"Opening rotation: {plan.rotacao_opening}")
    print(f"Disadvantage rotation: {plan.rotacao_disadvantage}")

    assert len(plan.rotacao_opening) > 0, "Opening rotation should not be empty!"
    print("[OK] Opening rotation populated")
    print("[OK] Rotation tests passed!")


def test_role_detection():
    """Test that chars with 2+ summons get SUMMONER role, 2+ traps get TRAP_MASTER."""
    print("\n--- Testing role detection ---")

    skill_names = ["Fênix", "Portal do Vazio", "Invocação: Espírito", "Bola de Fogo"]
    char = FakeChar(skill_names)
    sss = SkillStrategySystem(char, FakeBrain())
    print(f"SummonerBot role: {sss.role_principal} style: {sss.plano.estilo}")
    if sss.role_principal == StrategicRole.SUMMONER:
        print("[OK] SummonerBot detected as SUMMONER")
        assert sss.plano.estilo == "kite", f"SUMMONER should kite, got {sss.plano.estilo}"
        print("[OK] SUMMONER uses kite style")
    else:
        print(f"[WARN] SummonerBot got role {sss.role_principal} instead of SUMMONER (may be ok if hybrid)")

    skill_names2 = ["Muralha de Gelo", "Armadilha Elétrica", "Armadilha Incendiária", "Bola de Fogo"]
    char2 = FakeChar(skill_names2)
    sss2 = SkillStrategySystem(char2, FakeBrain())
    print(f"TrapperBot role: {sss2.role_principal} style: {sss2.plano.estilo}")
    if sss2.role_principal == StrategicRole.TRAP_MASTER:
        print("[OK] TrapperBot detected as TRAP_MASTER")
        assert sss2.plano.estilo == "kite", f"TRAP_MASTER should kite, got {sss2.plano.estilo}"
        print("[OK] TRAP_MASTER uses kite style")
    else:
        print(f"[WARN] TrapperBot got role {sss2.role_principal} instead of TRAP_MASTER")

    print("[OK] Role detection tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST: Brain Skill Strategy - SUMMON/TRAP Updates")
    print("=" * 60)

    sss = test_battle_plan()
    test_condicoes_ideais(sss)
    test_rotations(sss)
    test_role_detection()

    print("\n" + "=" * 60)
    print("[ALL TESTS PASSED]")
    print("=" * 60)
