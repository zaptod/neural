"""
Tests for tools/balance_report.py — BalanceReport
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.battle_db import BattleDB
from tools.balance_report import BalanceReport


class TestBalanceReport(unittest.TestCase):
    """Unit tests for the BalanceReport tool."""

    def setUp(self):
        BattleDB._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.db = BattleDB(os.path.join(self.tmp_dir, "test_report.db"))
        BattleDB._instance = self.db
        self.report = BalanceReport(self.db)

    def tearDown(self):
        BattleDB._instance = None
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _seed_data(self):
        """Insert sample matches for testing."""
        self.db.insert_match(
            p1="Caleb", p2="Bjorn", winner="Caleb", loser="Bjorn",
            duration=30.0, ko_type="KO",
            p1_class="Guerreiro", p2_class="Berserker",
            p1_weapon="Espada", p2_weapon="Machado",
        )
        self.db.update_character_stats("Caleb", won=True, elo_delta=25, tier="GOLD")
        self.db.update_character_stats("Bjorn", won=False, elo_delta=-25, tier="SILVER")

        self.db.insert_match(
            p1="Caleb", p2="Lyra", winner="Lyra", loser="Caleb",
            duration=60.0, ko_type="TIMEOUT",
            p1_class="Guerreiro", p2_class="Mago",
            p1_weapon="Espada", p2_weapon="Cajado",
        )
        self.db.update_character_stats("Lyra", won=True, elo_delta=30, tier="GOLD")
        self.db.update_character_stats("Caleb", won=False, elo_delta=-15, tier="SILVER")

    def test_empty_report(self):
        """Reports on empty DB should return 'no data' messages."""
        self.assertIn("No data", self.report.leaderboard())
        self.assertIn("No class data", self.report.class_winrates())
        self.assertIn("No weapon matchup", self.report.weapon_matchups())

    def test_summary_counts(self):
        self._seed_data()
        s = self.report.summary()
        self.assertIn("2", s)  # 2 matches

    def test_leaderboard_with_data(self):
        self._seed_data()
        lb = self.report.leaderboard()
        self.assertIn("Caleb", lb)
        self.assertIn("Lyra", lb)
        self.assertIn("Bjorn", lb)

    def test_class_winrates_with_data(self):
        self._seed_data()
        cw = self.report.class_winrates()
        self.assertIn("Guerreiro", cw)
        self.assertIn("Mago", cw)

    def test_weapon_matchups_with_data(self):
        self._seed_data()
        wm = self.report.weapon_matchups()
        self.assertIn("Espada", wm)
        self.assertIn("Machado", wm)

    def test_full_report_does_not_crash(self):
        """print_full_report should not raise even with data."""
        self._seed_data()
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.report.print_full_report()
        output = buf.getvalue()
        self.assertIn("BALANCE REPORT", output)
        self.assertIn("LEADERBOARD", output)


if __name__ == "__main__":
    unittest.main()
