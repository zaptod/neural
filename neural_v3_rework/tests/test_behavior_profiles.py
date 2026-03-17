"""Tests for ia/behavior_profiles.py â€” Phase 1 AI Overhaul personality fidelity."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ia.behavior_profiles import (
    BEHAVIOR_PROFILES, TRAIT_EFFECTS, FALLBACK_PROFILE,
    get_behavior_profile, get_trait_effects,
)
from ia.personalities import (
    PERSONALIDADES_PRESETS, TODOS_TRACOS,
    TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
)


class TestBehaviorProfilesData(unittest.TestCase):
    """Validate behavior profile data integrity."""

    def test_all_presets_have_profiles(self):
        """Every preset in PERSONALIDADES_PRESETS must have a BEHAVIOR_PROFILES entry."""
        for preset_name in PERSONALIDADES_PRESETS:
            if preset_name == 'Aleat\u00f3rio':
                continue  # Aleat\u00f3rio is random, no fixed profile
            profile = get_behavior_profile(preset_name)
            self.assertIsNotNone(profile, f"Missing profile for preset '{preset_name}'")
            self.assertIsNot(profile, FALLBACK_PROFILE,
                             f"Preset '{preset_name}' fell back to FALLBACK_PROFILE")

    def test_fallback_profile_has_all_keys(self):
        """FALLBACK_PROFILE should have all expected keys."""
        required_keys = [
            "recuar_threshold", "ataque_min_chance", "ataque_bonus_chance",
            "perseguir_sempre", "nunca_recua", "dano_recebido_reacao",
            "bloqueio_mult", "esquiva_mult", "combo_tendencia",
            "skill_agressividade", "risco_tolerancia",
            "raiva_ganho_mult", "medo_ganho_mult",
            "pressao_mult", "paciencia_mult", "execute_threshold",
            "approach_weight", "retreat_weight", "flank_weight", "poke_weight",
        ]
        for key in required_keys:
            self.assertIn(key, FALLBACK_PROFILE, f"FALLBACK_PROFILE missing key '{key}'")

    def test_all_profiles_have_fallback_keys(self):
        """Every profile should have at least the same keys as FALLBACK."""
        for name, profile in BEHAVIOR_PROFILES.items():
            for key in FALLBACK_PROFILE:
                self.assertIn(key, profile,
                              f"Profile '{name}' missing key '{key}'")

    def test_profile_values_in_sane_ranges(self):
        """Numeric profile values should be within reasonable ranges."""
        for name, profile in BEHAVIOR_PROFILES.items():
            self.assertGreaterEqual(profile["recuar_threshold"], 0.0,
                                    f"{name}.recuar_threshold below 0")
            self.assertLessEqual(profile["recuar_threshold"], 1.0,
                                 f"{name}.recuar_threshold above 1")
            self.assertGreaterEqual(profile["ataque_min_chance"], 0.0)
            self.assertLessEqual(profile["ataque_min_chance"], 1.0)
            self.assertGreaterEqual(profile["approach_weight"], 0.0)
            self.assertLessEqual(profile["approach_weight"], 5.0)
            self.assertGreaterEqual(profile["retreat_weight"], 0.0)
            self.assertLessEqual(profile["retreat_weight"], 5.0)


class TestTraitEffects(unittest.TestCase):
    """Validate TRAIT_EFFECTS coverage."""

    def test_aggressive_traits_have_effects(self):
        """Every trait in TRACOS_AGRESSIVIDADE should have an entry in TRAIT_EFFECTS."""
        for trait in TRACOS_AGRESSIVIDADE:
            effects = get_trait_effects(trait)
            self.assertTrue(len(effects) > 0,
                            f"Aggressive trait '{trait}' has no effects in TRAIT_EFFECTS")

    def test_defensive_traits_have_effects(self):
        """Every trait in TRACOS_DEFENSIVO should have an entry."""
        for trait in TRACOS_DEFENSIVO:
            effects = get_trait_effects(trait)
            self.assertTrue(len(effects) > 0,
                            f"Defensive trait '{trait}' has no effects in TRAIT_EFFECTS")

    def test_unknown_trait_returns_empty(self):
        """Unknown trait should return empty dict, not crash."""
        effects = get_trait_effects("NONEXISTENT_TRAIT_12345")
        self.assertEqual(effects, {})

    def test_trait_effects_have_string_keys_float_values(self):
        """All entries: action keys are str, weights are numeric."""
        for trait, effects in TRAIT_EFFECTS.items():
            self.assertIsInstance(trait, str)
            for action, weight in effects.items():
                self.assertIsInstance(action, str,
                                     f"Trait '{trait}': action key not str: {action}")
                self.assertIsInstance(weight, (int, float),
                                     f"Trait '{trait}': weight not numeric: {weight}")


class TestPersonalityFidelity(unittest.TestCase):
    """Ensure aggressive profiles are measurably MORE aggressive than defensive ones."""

    def _sum_attack_weights(self, profile_name):
        """Sum up attack-related profile values for a given personality."""
        p = get_behavior_profile(profile_name)
        score = 0.0
        score += p.get("ataque_min_chance", 0.5)
        score += p.get("ataque_bonus_chance", 0.0)
        score += p.get("pressao_mult", 1.0) - 1.0  # above baseline
        score += p.get("approach_weight", 1.0) - 1.0
        score -= p.get("retreat_weight", 1.0) - 1.0  # retreat reduces attack
        if p.get("nunca_recua", False):
            score += 0.5
        if p.get("perseguir_sempre", False):
            score += 0.3
        score += p.get("risco_tolerancia", 0.5) - 0.5
        return score

    def test_agressivo_more_aggressive_than_defensivo(self):
        """Agressivo should have a higher aggression score than Defensivo."""
        agg = self._sum_attack_weights("Agressivo")
        defe = self._sum_attack_weights("Defensivo")
        self.assertGreater(agg, defe + 0.3,
                           f"Agressivo ({agg:.2f}) not sufficiently > Defensivo ({defe:.2f})")

    def test_berserker_most_aggressive(self):
        """Berserker should be among the most aggressive profiles."""
        berk = self._sum_attack_weights("Berserker")
        equilibrado = self._sum_attack_weights("Equilibrado")
        self.assertGreater(berk, equilibrado + 0.5,
                           f"Berserker ({berk:.2f}) not significantly > Equilibrado ({equilibrado:.2f})")

    def test_defensivo_retreats_more(self):
        """Defensivo should have higher retreat_weight than Agressivo."""
        p_def = get_behavior_profile("Defensivo")
        p_agg = get_behavior_profile("Agressivo")
        self.assertGreater(p_def["retreat_weight"], p_agg["retreat_weight"],
                           "Defensivo should retreat more than Agressivo")

    def test_assassino_flanks_more(self):
        """Assassino should have higher flank_weight than average."""
        p_ass = get_behavior_profile("Assassino")
        self.assertGreater(p_ass["flank_weight"], 1.0,
                           "Assassino should have flank_weight > 1.0")

    def test_fantasma_high_evasion(self):
        """Fantasma should have high esquiva_mult."""
        p_fan = get_behavior_profile("Fantasma")
        self.assertGreater(p_fan["esquiva_mult"], 1.3,
                           "Fantasma should have high esquiva_mult")

    def test_masoquista_never_retreats(self):
        """Masoquista should have damage -> rage and low retreat."""
        p_mas = get_behavior_profile("Masoquista")
        self.assertIn(p_mas["dano_recebido_reacao"], ("raiva", "FURIA"),
                      "Masoquista should react to damage with rage/furia")
        self.assertLessEqual(p_mas["retreat_weight"], 0.5,
                             "Masoquista should have low retreat_weight")

    def test_tatico_balanced_and_patient(self):
        """TÃ¡tico should have high paciencia_mult."""
        p_tat = get_behavior_profile(u"T\u00e1tico")
        self.assertGreater(p_tat["paciencia_mult"], 1.3,
                           "TÃ¡tico should be patient")

    def test_caotico_has_variety(self):
        """CaÃ³tico should have non-standard weights."""
        p_cao = get_behavior_profile(u"Ca\u00f3tico")
        # CaÃ³tico should not have all multipliers at exactly 1.0
        mults = [p_cao["approach_weight"], p_cao["retreat_weight"],
                 p_cao["flank_weight"], p_cao["poke_weight"]]
        self.assertFalse(all(m == 1.0 for m in mults),
                         "CaÃ³tico should have at least some non-1.0 weights")


class TestTraitEffectsFidelity(unittest.TestCase):
    """Verify that aggressive traits produce positive attack votes and
    defensive traits produce positive defense votes."""

    def test_berserker_trait_votes_attack(self):
        effects = get_trait_effects("BERSERKER")
        attack_vote = effects.get("MATAR", 0.0) + effects.get("ESMAGAR", 0.0)
        self.assertGreater(attack_vote, 0.5,
                           f"BERSERKER trait should vote heavily for attack: {effects}")

    def test_cauteloso_trait_votes_defense(self):
        effects = get_trait_effects("CAUTELOSO")
        defense_vote = effects.get("RECUAR", 0.0) + effects.get("COMBATE", 0.0)
        self.assertGreater(defense_vote, 0.0,
                           f"CAUTELOSO trait should vote for defense: {effects}")

    def test_evasivo_trait_votes_movement(self):
        effects = get_trait_effects("EVASIVO")
        move_vote = (effects.get("FLANQUEAR", 0.0) + effects.get("RECUAR", 0.0)
                     + effects.get("CIRCULAR", 0.0))
        self.assertGreater(move_vote, 0.0,
                           f"EVASIVO trait should vote for movement: {effects}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

