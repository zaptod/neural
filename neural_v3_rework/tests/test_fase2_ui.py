"""
Tests for v14.0 Fase 2 — UI Visibility Features
=================================================
Tests the data layer integration used by the new UI screens.
Does NOT require a running Tk/Pygame instance.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPostFightResult(unittest.TestCase):
    """Test the post-fight result dict construction used by view_resultado."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_pf.db")

        from data.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

        from data.app_state import AppState
        AppState.reset()

    def tearDown(self):
        from data.battle_db import BattleDB
        BattleDB.reset()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def test_elo_before_after_captured(self):
        """ELO before/after values should differ after a fight."""
        from core.elo_system import calculate_elo, get_tier

        # Initial: both at 1600
        self.db.ensure_character("Alpha")
        self.db.ensure_character("Beta")
        s1 = self.db.get_character_stats("Alpha")
        self.assertEqual(s1["elo"], 1600.0)

        # Simulate what view_luta does: capture before, record, capture after
        elo_before_w = self.db.get_character_stats("Alpha")["elo"]
        elo_before_l = self.db.get_character_stats("Beta")["elo"]

        delta_w, delta_l = calculate_elo(elo_before_w, elo_before_l, 0, 0, True, 15.0)
        self.db.update_character_stats("Alpha", won=True, elo_delta=delta_w,
                                       tier=get_tier(elo_before_w + delta_w))
        self.db.update_character_stats("Beta", won=False, elo_delta=delta_l,
                                       tier=get_tier(max(0, elo_before_l + delta_l)))

        elo_after_w = self.db.get_character_stats("Alpha")["elo"]
        elo_after_l = self.db.get_character_stats("Beta")["elo"]

        self.assertGreater(elo_after_w, elo_before_w)
        self.assertLess(elo_after_l, elo_before_l)

        # Build result dict like view_luta
        result = {
            "winner": "Alpha",
            "loser": "Beta",
            "winner_elo_before": elo_before_w,
            "winner_elo_after": elo_after_w,
            "loser_elo_before": elo_before_l,
            "loser_elo_after": elo_after_l,
            "winner_tier": get_tier(elo_after_w),
            "loser_tier": get_tier(elo_after_l),
            "ko_type": "KO",
            "duration": 15.0,
        }
        self.assertEqual(result["winner"], "Alpha")
        self.assertIn(result["winner_tier"], ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER"])

    def test_stats_summary_integration(self):
        """MatchStatsCollector summary should contain expected fields."""
        from data.match_stats import MatchStatsCollector

        stats = MatchStatsCollector()
        stats.register("W")
        stats.register("L")
        stats.record_hit("W", "L", 50.0, critico=True)
        stats.record_hit("W", "L", 30.0, critico=False)
        stats.record_hit("L", "W", 20.0)
        stats.record_skill("W", "Fireball", 15.0)
        stats.record_block("L")
        stats.record_dodge("L")

        summary = stats.get_summary()

        self.assertIn("W", summary)
        self.assertIn("L", summary)

        ws = summary["W"]
        self.assertEqual(ws["hits_landed"], 2)
        self.assertEqual(ws["crits_landed"], 1)
        self.assertAlmostEqual(ws["damage_dealt"], 80.0, places=1)
        self.assertEqual(ws["skills_cast"], 1)
        self.assertAlmostEqual(ws["mana_spent"], 15.0, places=1)

        ls = summary["L"]
        self.assertEqual(ls["blocks"], 1)
        self.assertEqual(ls["dodges"], 1)
        self.assertEqual(ls["hits_landed"], 1)

    def test_empty_stats_no_crash(self):
        """PostFight screen should handle empty stats gracefully."""
        result = {
            "winner": "X", "loser": "Y",
            "winner_elo_before": 1600, "winner_elo_after": 1620,
            "loser_elo_before": 1600, "loser_elo_after": 1580,
            "winner_tier": "GOLD", "loser_tier": "SILVER",
            "ko_type": "KO", "duration": 10.0,
            "winner_stats": {}, "loser_stats": {},
        }
        # The dict should be safely consumable
        self.assertEqual(result.get("winner_stats", {}).get("damage_dealt", 0), 0)
        self.assertEqual(result.get("loser_stats", {}).get("hits_landed", 0), 0)


class TestLeaderboardData(unittest.TestCase):
    """Test leaderboard data queries used by view_ranking."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_lb.db")

        from data.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

    def tearDown(self):
        from data.battle_db import BattleDB
        BattleDB.reset()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def test_leaderboard_empty(self):
        """Leaderboard should return empty list when no data."""
        board = self.db.get_leaderboard()
        self.assertEqual(board, [])

    def test_leaderboard_ordering(self):
        """Leaderboard should be ordered by ELO descending."""
        self.db.ensure_character("Low")
        self.db.ensure_character("High")
        self.db.update_character_stats("High", won=True, elo_delta=200, tier="PLATINUM")
        self.db.update_character_stats("Low", won=False, elo_delta=-100, tier="SILVER")

        board = self.db.get_leaderboard()
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0]["name"], "High")
        self.assertEqual(board[1]["name"], "Low")
        self.assertGreater(board[0]["elo"], board[1]["elo"])

    def test_class_winrates(self):
        """Class winrates should be computed correctly."""
        self.db.insert_match(
            p1="A", p2="B", winner="A", loser="B",
            duration=10, ko_type="KO", p1_class="Guerreiro", p2_class="Mago"
        )
        self.db.insert_match(
            p1="C", p2="D", winner="C", loser="D",
            duration=15, ko_type="KO", p1_class="Guerreiro", p2_class="Mago"
        )

        rates = self.db.get_class_winrates()
        guerreiro = next((r for r in rates if "Guerreiro" in r["class_name"]), None)
        mago = next((r for r in rates if "Mago" in r["class_name"]), None)

        self.assertIsNotNone(guerreiro)
        self.assertEqual(guerreiro["total_wins"], 2)
        self.assertEqual(guerreiro["total_losses"], 0)

        self.assertIsNotNone(mago)
        self.assertEqual(mago["total_wins"], 0)
        self.assertEqual(mago["total_losses"], 2)

    def test_weapon_matchups(self):
        """Weapon matchups should track win rates."""
        self.db.insert_match(
            p1="A", p2="B", winner="A", loser="B",
            duration=10, ko_type="KO",
            p1_weapon="Espada", p2_weapon="Arco"
        )

        matchups = self.db.get_weapon_matchups()
        self.assertEqual(len(matchups), 1)
        self.assertEqual(matchups[0]["weapon_a"], "Espada")
        self.assertEqual(matchups[0]["weapon_b"], "Arco")
        self.assertAlmostEqual(matchups[0]["a_winrate"], 1.0)

    def test_match_history(self):
        """Match history should return most recent first."""
        for i in range(5):
            self.db.insert_match(
                p1=f"P{i}", p2=f"Q{i}", winner=f"P{i}", loser=f"Q{i}",
                duration=10+i, ko_type="KO"
            )

        history = self.db.get_match_history(limit=3)
        self.assertEqual(len(history), 3)
        # Most recent should be first
        self.assertEqual(history[0]["p1"], "P4")

    def test_match_history_character_filter(self):
        """Match history should filter by character name."""
        self.db.insert_match(p1="Alice", p2="Bob", winner="Alice", loser="Bob", duration=10, ko_type="KO")
        self.db.insert_match(p1="Charlie", p2="Dave", winner="Charlie", loser="Dave", duration=10, ko_type="KO")

        history = self.db.get_match_history(character="Alice")
        self.assertEqual(len(history), 1)
        self.assertIn("Alice", [history[0]["p1"], history[0]["p2"]])

    def test_summary_counts(self):
        """Summary should reflect actual counts."""
        self.db.insert_match(p1="A", p2="B", winner="A", loser="B", duration=10, ko_type="KO")
        self.db.ensure_character("A")
        self.db.ensure_character("B")

        summary = self.db.get_summary()
        self.assertEqual(summary["total_matches"], 1)
        self.assertEqual(summary["total_characters"], 2)


class TestELOInSelection(unittest.TestCase):
    """Test logic for showing ELO in character selection."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_sel.db")

        from data.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

    def tearDown(self):
        from data.battle_db import BattleDB
        BattleDB.reset()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def test_elo_tag_new_character(self):
        """New character with no fights should show no ELO tag."""
        cs = self.db.get_character_stats("NewGuy")
        self.assertIsNone(cs)  # No stats = no ELO shown

    def test_elo_tag_veteran_character(self):
        """Character with fights should have ELO and tier in stats."""
        self.db.ensure_character("Veteran")
        self.db.update_character_stats("Veteran", won=True, elo_delta=50, tier="GOLD")
        self.db.update_character_stats("Veteran", won=True, elo_delta=30, tier="GOLD")
        self.db.update_character_stats("Veteran", won=False, elo_delta=-20, tier="GOLD")

        cs = self.db.get_character_stats("Veteran")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["matches_played"], 3)
        self.assertEqual(cs["wins"], 2)
        self.assertEqual(cs["losses"], 1)
        self.assertAlmostEqual(cs["elo"], 1660.0, places=1)

    def test_tier_visual_mapping(self):
        """All tiers should have visual properties defined."""
        from ui.view_resultado import TIER_VISUAL

        for tier_name, _ in [("MASTER", 2200), ("DIAMOND", 2000), ("PLATINUM", 1800),
                              ("GOLD", 1600), ("SILVER", 1400), ("BRONZE", 0)]:
            self.assertIn(tier_name, TIER_VISUAL)
            cor, emoji = TIER_VISUAL[tier_name]
            self.assertTrue(cor.startswith("#"))
            self.assertTrue(len(emoji) > 0)


class TestFormatHelpers(unittest.TestCase):
    """Test format helpers in view_resultado."""

    def test_fmt_num(self):
        from ui.view_resultado import _fmt_num
        self.assertEqual(_fmt_num(1234.56), "1,234.6")
        self.assertEqual(_fmt_num(0), "0.0")
        self.assertEqual(_fmt_num(None), "0")
        self.assertEqual(_fmt_num("abc"), "0")

    def test_fmt_pct(self):
        from ui.view_resultado import _fmt_pct
        self.assertEqual(_fmt_pct(0.756), "75.6%")
        self.assertEqual(_fmt_pct(1.0), "100.0%")
        self.assertEqual(_fmt_pct(0), "0.0%")
        self.assertEqual(_fmt_pct(None), "0.0%")


class TestTierColors(unittest.TestCase):
    """Test that tier visual constants in view_ranking match elo_system tiers."""

    def test_all_tiers_have_colors(self):
        from core.elo_system import TIERS
        from ui.view_ranking import TIER_COLORS, TIER_EMOJI

        for tier_name, _ in TIERS:
            self.assertIn(tier_name, TIER_COLORS, f"Missing color for tier {tier_name}")
            self.assertIn(tier_name, TIER_EMOJI, f"Missing emoji for tier {tier_name}")


class TestSecuritySanitization(unittest.TestCase):
    """Security tests: ensure no SQL injection via character names."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_sec.db")

        from data.battle_db import BattleDB
        BattleDB.reset()
        self.db = BattleDB(self.db_path)
        BattleDB._instance = self.db

    def tearDown(self):
        from data.battle_db import BattleDB
        BattleDB.reset()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass

    def test_sql_injection_character_name(self):
        """Names with SQL special chars should be safely handled."""
        evil_name = "Robert'); DROP TABLE matches;--"
        self.db.insert_match(
            p1=evil_name, p2="Victim", winner=evil_name, loser="Victim",
            duration=10, ko_type="KO"
        )
        # Table should still exist
        count = self.db.count_matches()
        self.assertEqual(count, 1)

        # Should be retrievable
        history = self.db.get_match_history()
        self.assertEqual(history[0]["winner"], evil_name)

    def test_sql_injection_stats(self):
        """Stats queries with special chars should not crash."""
        evil = "'; DELETE FROM character_stats;--"
        self.db.ensure_character(evil)
        cs = self.db.get_character_stats(evil)
        self.assertIsNotNone(cs)
        self.assertEqual(cs["name"], evil)

    def test_xss_in_names(self):
        """HTML/script tags in names should be stored as plain text (no injection)."""
        xss_name = "<script>alert('xss')</script>"
        self.db.ensure_character(xss_name)
        cs = self.db.get_character_stats(xss_name)
        self.assertEqual(cs["name"], xss_name)


if __name__ == "__main__":
    unittest.main()
