"""
Tests for dados/match_stats.py â€” MatchStatsCollector
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dados.match_stats import MatchStatsCollector


class TestMatchStatsCollector(unittest.TestCase):
    """Unit tests for the MatchStatsCollector."""

    def setUp(self):
        self.stats = MatchStatsCollector()
        self.stats.register("Caleb")
        self.stats.register("Bjorn")

    # â”€â”€ Registration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_register_creates_fighter_entry(self):
        s = self.stats._fighters
        self.assertIn("Caleb", s)
        self.assertIn("Bjorn", s)
        self.assertEqual(s["Caleb"]["damage_dealt"], 0.0)
        self.assertEqual(s["Bjorn"]["hits_landed"], 0)

    def test_register_unknown_fighter_is_ignored_in_recorders(self):
        """Recording for unregistered names should not crash."""
        self.stats.record_hit("Ghost", "Caleb", 10)
        self.stats.record_skill("Ghost", "Fireball")
        self.stats.record_block("Ghost")
        self.stats.record_dodge("Ghost")
        self.stats.record_death("Ghost")
        # No exception = pass

    # â”€â”€ record_hit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_record_hit_basic(self):
        self.stats.record_hit("Caleb", "Bjorn", 25.0)
        c = self.stats._fighters["Caleb"]
        b = self.stats._fighters["Bjorn"]
        self.assertEqual(c["damage_dealt"], 25.0)
        self.assertEqual(c["hits_landed"], 1)
        self.assertEqual(b["damage_taken"], 25.0)
        self.assertEqual(b["hits_received"], 1)

    def test_record_hit_critical(self):
        self.stats.record_hit("Caleb", "Bjorn", 40.0, critico=True)
        self.assertEqual(self.stats._fighters["Caleb"]["crits_landed"], 1)

    def test_record_hit_accumulates(self):
        self.stats.record_hit("Caleb", "Bjorn", 10)
        self.stats.record_hit("Caleb", "Bjorn", 15)
        c = self.stats._fighters["Caleb"]
        self.assertEqual(c["damage_dealt"], 25)
        self.assertEqual(c["hits_landed"], 2)

    def test_record_hit_creates_event(self):
        self.stats.set_frame(42)
        self.stats.record_hit("Caleb", "Bjorn", 20, critico=True, elemento="FOGO")
        events = self.stats.get_events()
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["frame"], 42)
        self.assertEqual(e["type"], "hit")
        self.assertEqual(e["damage"], 20.0)
        self.assertTrue(e["crit"])
        self.assertEqual(e["elem"], "FOGO")

    # â”€â”€ Combo tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_combo_tracking(self):
        self.stats.record_hit("Caleb", "Bjorn", 10)
        self.stats.record_hit("Caleb", "Bjorn", 10)
        self.stats.record_hit("Caleb", "Bjorn", 10)
        self.assertEqual(self.stats._fighters["Caleb"]["max_combo"], 3)
        self.assertEqual(self.stats._fighters["Caleb"]["current_combo"], 3)

    def test_combo_reset_on_receiving_hit(self):
        self.stats.record_hit("Caleb", "Bjorn", 10)
        self.stats.record_hit("Caleb", "Bjorn", 10)  # Caleb combo = 2
        self.stats.record_hit("Bjorn", "Caleb", 5)   # Caleb hit â†’ combo reset
        self.assertEqual(self.stats._fighters["Caleb"]["current_combo"], 0)
        self.assertEqual(self.stats._fighters["Caleb"]["max_combo"], 2)  # Peak preserved

    # â”€â”€ record_attack_attempt â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_record_attack_attempt(self):
        self.stats.record_attack_attempt("Caleb")
        self.stats.record_attack_attempt("Caleb")
        self.assertEqual(self.stats._fighters["Caleb"]["attacks_attempted"], 2)

    # â”€â”€ record_skill â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_record_skill(self):
        self.stats.record_skill("Caleb", "Bola de Fogo", mana_cost=15)
        c = self.stats._fighters["Caleb"]
        self.assertEqual(c["skills_cast"], 1)
        self.assertEqual(c["mana_spent"], 15)
        self.assertEqual(c["skills_detail"]["Bola de Fogo"], 1)

    def test_record_skill_creates_event(self):
        self.stats.set_frame(100)
        self.stats.record_skill("Caleb", "Ice Blast", mana_cost=20)
        events = self.stats.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "skill")
        self.assertEqual(events[0]["skill"], "Ice Blast")
        self.assertEqual(events[0]["cost"], 20.0)

    # â”€â”€ record_block / record_dodge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_record_block(self):
        self.stats.record_block("Bjorn")
        self.assertEqual(self.stats._fighters["Bjorn"]["blocks"], 1)

    def test_record_dodge(self):
        self.stats.record_dodge("Bjorn")
        self.assertEqual(self.stats._fighters["Bjorn"]["dodges"], 1)

    # â”€â”€ record_death â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_record_death(self):
        self.stats.record_death("Bjorn", killer="Caleb")
        self.assertEqual(self.stats._fighters["Bjorn"]["deaths"], 1)
        self.assertEqual(self.stats._fighters["Caleb"]["kills"], 1)

    def test_record_death_creates_event(self):
        self.stats.set_frame(500)
        self.stats.record_death("Bjorn", killer="Caleb")
        events = self.stats.get_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "death")
        self.assertEqual(events[0]["victim"], "Bjorn")

    # â”€â”€ get_summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_get_summary_accuracy(self):
        self.stats.record_attack_attempt("Caleb")
        self.stats.record_attack_attempt("Caleb")
        self.stats.record_hit("Caleb", "Bjorn", 10)
        summary = self.stats.get_summary()
        self.assertAlmostEqual(summary["Caleb"]["accuracy"], 0.5, places=2)

    def test_get_summary_no_current_combo(self):
        """current_combo is internal â€” should not appear in summary."""
        summary = self.stats.get_summary()
        self.assertNotIn("current_combo", summary["Caleb"])

    def test_get_summary_dps(self):
        self.stats.record_hit("Caleb", "Bjorn", 100)
        summary = self.stats.get_summary()
        # DPS = damage / elapsed. elapsed > 0 so dps should be > 0
        self.assertGreater(summary["Caleb"]["dps"], 0)

    # â”€â”€ flush_to_db â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_flush_to_db_writes_events(self):
        """flush_to_db should insert events into BattleDB without errors."""
        from dados.battle_db import BattleDB
        BattleDB._instance = None  # Reset singleton
        tmp_dir = tempfile.mkdtemp()
        try:
            # Create DB as singleton so flush_to_db's BattleDB.get() finds it
            db = BattleDB(os.path.join(tmp_dir, "test_stats.db"))
            BattleDB._instance = db

            # Need a match first (foreign key)
            match_id = db.insert_match(
                p1="Caleb", p2="Bjorn", winner="Caleb", loser="Bjorn",
                duration=30.0, ko_type="KO",
            )

            self.stats.set_frame(1)
            self.stats.record_hit("Caleb", "Bjorn", 25, critico=True)
            self.stats.set_frame(2)
            self.stats.record_skill("Caleb", "Fire", mana_cost=10)

            self.stats.flush_to_db(match_id)

            # Verify events were written
            summary = db.get_summary()
            self.assertEqual(summary["total_events"], 2)
        finally:
            BattleDB._instance = None
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestMatchStatsEdgeCases(unittest.TestCase):
    """Edge cases and stress tests."""

    def test_empty_stats_summary(self):
        stats = MatchStatsCollector()
        stats.register("Solo")
        summary = stats.get_summary()
        self.assertEqual(summary["Solo"]["damage_dealt"], 0.0)
        self.assertAlmostEqual(summary["Solo"]["accuracy"], 0.0)

    def test_get_events_returns_copy(self):
        stats = MatchStatsCollector()
        stats.register("A")
        stats.record_hit("A", "A", 10)
        events = stats.get_events()
        events.clear()
        self.assertEqual(len(stats.get_events()), 1)  # Original untouched


if __name__ == "__main__":
    unittest.main()

