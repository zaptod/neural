"""
Multi-Matchup Diagnostic Tool
Tests various weapon matchups to identify behavioral problems across combat scenarios.
"""
import os
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Headless pygame setup before importing simulation.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dados.app_state import AppState
from simulacao.simulacao import Simulador


@dataclass
class MatchupResult:
    """Store diagnostic results for a single matchup test."""
    p1_name: str
    p1_weapon: str
    p2_name: str
    p2_weapon: str
    p1_advance_pct: float
    p1_retreat_pct: float
    p1_block_pct: float
    p1_avg_dist: float
    p1_min_dist: float
    p2_advance_pct: float
    p2_retreat_pct: float
    p2_block_pct: float
    p2_avg_dist: float
    p2_min_dist: float
    match_duration: int  # frames completed
    
    def is_passive(self, player: int = 1) -> bool:
        """Check if a player shows passive behavior (low advance, high block)."""
        if player == 1:
            return self.p1_advance_pct < 0.40 and self.p1_block_pct > 0.15
        else:
            return self.p2_advance_pct < 0.40 and self.p2_block_pct > 0.15


def run_matchup_diagnostic(
    p1_name: str,
    p2_name: str,
    sim_seconds: float = 30.0,
    debug: bool = False
) -> MatchupResult:
    """
    Run a single matchup diagnostic.
    
    Returns MatchupResult with metrics for both players.
    """
    state = AppState.get()
    original_match = state.match_config

    try:
        # Force the specific matchup
        state.set_match_config(
            {
                **original_match,
                "p1_nome": p1_name,
                "p2_nome": p2_name,
                "cenario": original_match.get("cenario", "Arena"),
            }
        )

        sim = Simulador()
        p1 = sim.p1
        p2 = sim.p2

        # Enable debug logs if requested
        if debug:
            if p1 and p1.brain:
                p1.brain.DEBUG_AI_DECISIONS = True
            if p2 and p2.brain:
                p2.brain.DEBUG_AI_DECISIONS = True

        p1_weapon = p1.dados.nome_arma if p1 else "?"
        p2_weapon = p2.dados.nome_arma if p2 else "?"

        dt = 1.0 / 60.0
        frames = int(sim_seconds / dt)

        # Track actions for both players
        p1_actions = Counter()
        p2_actions = Counter()

        action_categories = {
            "advancing": {"APROXIMAR", "PRESSIONAR", "FLANQUEAR", "MATAR", "ATAQUE_RAPIDO", "ESMAGAR"},
            "retreating": {"RECUAR", "FUGIR"},
            "neutral": {"NEUTRO"},
            "blocking": {"BLOQUEAR"},
        }

        p1_stats = {
            "advancing": 0,
            "retreating": 0,
            "neutral": 0,
            "blocking": 0,
            "dist_sum": 0.0,
            "dist_min": 10**9,
            "dist_max": 0.0,
        }
        p2_stats = {
            "advancing": 0,
            "retreating": 0,
            "neutral": 0,
            "blocking": 0,
            "dist_sum": 0.0,
            "dist_min": 10**9,
            "dist_max": 0.0,
        }

        frame_count = 0

        for i in range(frames):
            sim.update(dt)

            if p1.morto or p2.morto:
                break

            # Distance between players
            dx = p2.pos[0] - p1.pos[0]
            dy = p2.pos[1] - p1.pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            # Track P1 actions
            p1_acao = p1.brain.acao_atual if p1.brain else "SEM_BRAIN"
            p1_actions[p1_acao] += 1
            for category, actions in action_categories.items():
                if p1_acao in actions:
                    p1_stats[category] += 1
            p1_stats["dist_sum"] += dist
            p1_stats["dist_min"] = min(p1_stats["dist_min"], dist)
            p1_stats["dist_max"] = max(p1_stats["dist_max"], dist)

            # Track P2 actions
            p2_acao = p2.brain.acao_atual if p2.brain else "SEM_BRAIN"
            p2_actions[p2_acao] += 1
            for category, actions in action_categories.items():
                if p2_acao in actions:
                    p2_stats[category] += 1
            p2_stats["dist_sum"] += dist
            p2_stats["dist_min"] = min(p2_stats["dist_min"], dist)
            p2_stats["dist_max"] = max(p2_stats["dist_max"], dist)

            frame_count += 1

        # Calculate percentages
        def get_percentages(stats, total):
            if total == 0:
                return 0.0, 0.0, 0.0, 0.0, 0.0
            advancing_pct = stats["advancing"] / total
            retreating_pct = stats["retreating"] / total
            blocking_pct = stats["blocking"] / total
            avg_dist = stats["dist_sum"] / total
            min_dist = stats["dist_min"] if stats["dist_min"] < 10**9 else 0.0
            return advancing_pct, retreating_pct, blocking_pct, avg_dist, min_dist

        p1_adv, p1_ret, p1_blk, p1_avg_dist, p1_min_dist = get_percentages(p1_stats, frame_count)
        p2_adv, p2_ret, p2_blk, p2_avg_dist, p2_min_dist = get_percentages(p2_stats, frame_count)

        return MatchupResult(
            p1_name=p1_name,
            p1_weapon=p1_weapon,
            p2_name=p2_name,
            p2_weapon=p2_weapon,
            p1_advance_pct=p1_adv,
            p1_retreat_pct=p1_ret,
            p1_block_pct=p1_blk,
            p1_avg_dist=p1_avg_dist,
            p1_min_dist=p1_min_dist,
            p2_advance_pct=p2_adv,
            p2_retreat_pct=p2_ret,
            p2_block_pct=p2_blk,
            p2_avg_dist=p2_avg_dist,
            p2_min_dist=p2_min_dist,
            match_duration=frame_count,
        )

    finally:
        # Restore original match config
        state.set_match_config(original_match)
        try:
            import pygame
            pygame.display.quit()
            pygame.mixer.quit()
        except Exception as _e:  # E02 Sprint 12
            import logging as _lg; _lg.getLogger('tools').debug('pygame cleanup: %s', _e)


def print_matchup_result(result: MatchupResult) -> None:
    """Pretty-print a single matchup result."""
    print("\n" + "=" * 80)
    print(f"MATCHUP: {result.p1_name} ({result.p1_weapon})")
    print(f"    vs  {result.p2_name} ({result.p2_weapon})")
    print("=" * 80)

    # P1 Stats
    print(f"\n[P1] {result.p1_name} ({result.p1_weapon})")
    print(f"  Advance:  {result.p1_advance_pct:6.1%}   Retreat:  {result.p1_retreat_pct:6.1%}   Block:  {result.p1_block_pct:6.1%}")
    print(f"  Distance: avg={result.p1_avg_dist:5.2f}m   min={result.p1_min_dist:5.2f}m")
    
    # P2 Stats
    print(f"\n[P2] {result.p2_name} ({result.p2_weapon})")
    print(f"  Advance:  {result.p2_advance_pct:6.1%}   Retreat:  {result.p2_retreat_pct:6.1%}   Block:  {result.p2_block_pct:6.1%}")
    print(f"  Distance: avg={result.p2_avg_dist:5.2f}m   min={result.p2_min_dist:5.2f}m")

    # Analysis
    print("\n[ANALYSIS]")
    p1_passive = result.is_passive(1)
    p2_passive = result.is_passive(2)
    
    if p1_passive:
        print(f"  âš ï¸  P1 shows PASSIVE behavior (advance: {result.p1_advance_pct:.1%}, block: {result.p1_block_pct:.1%})")
    else:
        print(f"  âœ“ P1 behavior OK")
    
    if p2_passive:
        print(f"  âš ï¸  P2 shows PASSIVE behavior (advance: {result.p2_advance_pct:.1%}, block: {result.p2_block_pct:.1%})")
    else:
        print(f"  âœ“ P2 behavior OK")
    
    print(f"  Duration: {result.match_duration} frames (~{result.match_duration/60:.1f}s)")


def run_comprehensive_tests():
    """Run all matchup combinations and report findings."""
    matchups = [
        # (P1 Name, P2 Name, Description)
        ("Yasuo da Aurora", "Medea", "Melee vs Bow"),
        ("Medea", "Yasuo da Aurora", "Bow vs Melee (reverse)"),
    ]

    results: List[MatchupResult] = []
    
    print("\n" + "#" * 80)
    print("# MULTI-MATCHUP DIAGNOSTIC SUITE")
    print("#" * 80)
    print(f"\nTesting {len(matchups)} matchups...")

    for idx, (p1, p2, desc) in enumerate(matchups, 1):
        print(f"\n[{idx}/{len(matchups)}] {desc}...", end=" ", flush=True)
        try:
            result = run_matchup_diagnostic(p1, p2, sim_seconds=30.0, debug=False)
            results.append(result)
            print("âœ“")
        except Exception as e:
            print(f"âœ— Error: {e}")

    # Print all results
    print("\n" + "#" * 80)
    print("# DETAILED RESULTS")
    print("#" * 80)
    
    for result in results:
        print_matchup_result(result)

    # Summary table
    print("\n" + "#" * 80)
    print("# SUMMARY TABLE")
    print("#" * 80)
    print("\n{:<30} {:<8} {:<8} {:<8}  {:<8}".format(
        "Matchup", "Advance", "Retreat", "Block", "Avg Dist"
    ))
    print("-" * 80)
    
    for result in results:
        matchup_str = f"{result.p1_name[:12]} vs {result.p2_name[:12]}"
        print("{:<30} {:<8.1%} {:<8.1%} {:<8.1%}  {:<8.2f}m".format(
            matchup_str,
            result.p1_advance_pct,
            result.p1_retreat_pct,
            result.p1_block_pct,
            result.p1_avg_dist,
        ))

    # Issues report
    print("\n" + "#" * 80)
    print("# ISSUES DETECTED")
    print("#" * 80)
    
    passive_issues = []
    for result in results:
        if result.is_passive(1):
            passive_issues.append(
                f"  â€¢ {result.p1_name} ({result.p1_weapon}) vs {result.p2_name} ({result.p2_weapon}): "
                f"Too much blocking ({result.p1_block_pct:.1%}), not enough advancing ({result.p1_advance_pct:.1%})"
            )
        if result.is_passive(2):
            passive_issues.append(
                f"  â€¢ {result.p2_name} ({result.p2_weapon}) vs {result.p1_name} ({result.p1_weapon}): "
                f"Too much blocking ({result.p2_block_pct:.1%}), not enough advancing ({result.p2_advance_pct:.1%})"
            )
    
    if passive_issues:
        print("\nPassive Behavior Issues Detected:\n")
        for issue in passive_issues:
            print(issue)
    else:
        print("\nâœ“ No significant passive behavior detected!")

    return results


if __name__ == "__main__":
    results = run_comprehensive_tests()
    
    # Exit with error code if issues found
    has_issues = any(r.is_passive(1) or r.is_passive(2) for r in results)
    sys.exit(1 if has_issues else 0)

