"""Quick integration test: AppState â†’ BattleDB â†’ ELO.

Uses a temp directory for the DB so it never touches production data.
"""
import os
import shutil
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from dados.battle_db import BattleDB


class TestIntegrationAppStateDB(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        BattleDB._instance = None
        self.db = BattleDB(os.path.join(self.tmp_dir, "test_integration.db"))
        BattleDB._instance = self.db

        from dados.app_state import AppState
        AppState.reset()
        self.state = AppState.get()

    def tearDown(self):
        self.db.close()
        BattleDB._instance = None
        from dados.app_state import AppState
        AppState.reset()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_full_pipeline(self):
        """AppState.record_fight_result â†’ BattleDB + ELO end-to-end."""
        s = self.state
        match_id = s.record_fight_result("TestWinner", "TestLoser", 5.0, True)
        self.assertIsNotNone(match_id)

        m = self.db.get_match(match_id)
        self.assertEqual(m["winner"], "TestWinner")
        self.assertEqual(m["duration"], 5.0)
        self.assertEqual(m["ko_type"], "KO")

        # ELO updated
        w_stats = self.db.get_character_stats("TestWinner")
        l_stats = self.db.get_character_stats("TestLoser")
        self.assertGreater(w_stats["elo"], 1600)
        self.assertLess(l_stats["elo"], 1600)
        self.assertEqual(w_stats["wins"], 1)
        self.assertEqual(l_stats["losses"], 1)
        self.assertIn(w_stats["tier"], ("BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER"))

        # ELO snapshots in match
        self.assertEqual(m["p1_elo_before"], 1600.0)
        self.assertGreater(m["p1_elo_after"], 1600.0)
        self.assertLess(m["p2_elo_after"], 1600.0)

    def test_second_fight_and_leaderboard(self):
        s = self.state
        s.record_fight_result("TestWinner", "TestLoser", 5.0, True)
        match_id2 = s.record_fight_result("TestLoser", "TestWinner", 12.0, False)
        self.assertIsNotNone(match_id2)

        m2 = self.db.get_match(match_id2)
        self.assertEqual(m2["ko_type"], "TIMEOUT")
        self.assertEqual(self.db.count_matches(), 2)

        board = self.db.get_leaderboard()
        self.assertTrue(len(board) >= 2)


if __name__ == "__main__":
    unittest.main()

