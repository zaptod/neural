"""
NEURAL FIGHTS — Balance Report Tool v14.0
===========================================
Generates balance analysis reports from the SQLite battle log.

Can be run standalone:
    python tools/balance_report.py

Or imported:
    from tools.balance_report import BalanceReport
    report = BalanceReport()
    report.print_full_report()
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.battle_db import BattleDB


class BalanceReport:
    """Generates balance analysis from battle history."""

    def __init__(self, db: BattleDB = None):
        self.db = db or BattleDB.get()

    def leaderboard(self, limit: int = 20) -> str:
        """Top characters by ELO."""
        board = self.db.get_leaderboard(limit)
        if not board:
            return "No data yet."

        lines = ["=" * 60]
        lines.append(f"{'#':>3} {'Name':<20} {'ELO':>7} {'Tier':<10} {'W':>4} {'L':>4} {'WR%':>6}")
        lines.append("-" * 60)
        for i, s in enumerate(board, 1):
            mp = max(s["matches_played"], 1)
            wr = s["wins"] / mp * 100
            lines.append(
                f"{i:>3} {s['name']:<20} {s['elo']:>7.1f} {s['tier']:<10} "
                f"{s['wins']:>4} {s['losses']:>4} {wr:>5.1f}%"
            )
        lines.append("=" * 60)
        return "\n".join(lines)

    def class_winrates(self) -> str:
        """Win rates by character class."""
        rates = self.db.get_class_winrates()
        if not rates:
            return "No class data yet."

        lines = ["=" * 50]
        lines.append(f"{'Class':<25} {'Wins':>5} {'Losses':>6} {'WR%':>7}")
        lines.append("-" * 50)
        for r in rates:
            wr = r["winrate"] * 100
            lines.append(
                f"{r['class_name']:<25} {r['total_wins']:>5} {r['total_losses']:>6} {wr:>6.1f}%"
            )
        lines.append("=" * 50)
        return "\n".join(lines)

    def weapon_matchups(self) -> str:
        """Weapon-vs-weapon win rates."""
        matchups = self.db.get_weapon_matchups()
        if not matchups:
            return "No weapon matchup data yet."

        lines = ["=" * 65]
        lines.append(f"{'Weapon A':<18} {'Weapon B':<18} {'Games':>5} {'A WR%':>7} {'B WR%':>7}")
        lines.append("-" * 65)
        for m in matchups:
            a_wr = m["a_winrate"] * 100
            b_wr = (1 - m["a_winrate"]) * 100
            lines.append(
                f"{m['weapon_a']:<18} {m['weapon_b']:<18} {m['total']:>5} "
                f"{a_wr:>6.1f}% {b_wr:>6.1f}%"
            )
        lines.append("=" * 65)
        return "\n".join(lines)

    def summary(self) -> str:
        """Database overview."""
        s = self.db.get_summary()
        return (
            f"Total Matches: {s['total_matches']}  |  "
            f"Total Events: {s['total_events']}  |  "
            f"Characters Tracked: {s['total_characters']}"
        )

    def print_full_report(self):
        """Print all reports to console."""
        print("\n" + "=" * 60)
        print("   NEURAL FIGHTS — BALANCE REPORT v14.0")
        print("=" * 60)
        print(f"\n{self.summary()}\n")

        print("\n--- LEADERBOARD ---")
        print(self.leaderboard())

        print("\n--- CLASS WIN RATES ---")
        print(self.class_winrates())

        print("\n--- WEAPON MATCHUPS ---")
        print(self.weapon_matchups())
        print()


if __name__ == "__main__":
    report = BalanceReport()
    report.print_full_report()
