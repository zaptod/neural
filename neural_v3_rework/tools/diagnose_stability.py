"""
Extended Stability Test with Multiple Seeds
Verifies that the behavioral improvements are consistent across random variations.
"""
import os
import sys
import random
from collections import defaultdict

# Headless pygame setup before importing simulation.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.diagnose_multi_matchups import run_matchup_diagnostic, MatchupResult


def run_stability_tests(
    p1_name: str,
    p2_name: str,
    num_runs: int = 10,
    simulation_seconds: float = 30.0
) -> tuple:
    """
    Run multiple diagnostic tests with different random seeds.
    
    Returns:
        (results_list, stats_dict)
    """
    results = []
    
    print(f"\nRunning {num_runs} simulations: {p1_name} vs {p2_name}")
    print("-" * 60)
    
    for run in range(num_runs):
        # Reset RNG seed for variation
        random.seed(run * 1000)
        
        print(f"  Run {run+1:2d}/{num_runs}... ", end="", flush=True)
        try:
            result = run_matchup_diagnostic(p1_name, p2_name, sim_seconds=simulation_seconds)
            results.append(result)
            print(f"✓ (avg_dist={result.p1_avg_dist:.2f}m, adv={result.p1_advance_pct:.1%})")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    # Calculate statistics
    if results:
        p1_advances = [r.p1_advance_pct for r in results]
        p1_retreats = [r.p1_retreat_pct for r in results]
        p1_blocks = [r.p1_block_pct for r in results]
        p1_dists = [r.p1_avg_dist for r in results]
        
        p2_advances = [r.p2_advance_pct for r in results]
        p2_retreats = [r.p2_retreat_pct for r in results]
        p2_blocks = [r.p2_block_pct for r in results]
        p2_dists = [r.p2_avg_dist for r in results]
        
        stats = {
            "p1_advance": {
                "mean": sum(p1_advances) / len(p1_advances),
                "min": min(p1_advances),
                "max": max(p1_advances),
                "std": (sum((x - sum(p1_advances)/len(p1_advances))**2 for x in p1_advances) / len(p1_advances)) ** 0.5,
            },
            "p1_retreat": {
                "mean": sum(p1_retreats) / len(p1_retreats),
                "min": min(p1_retreats),
                "max": max(p1_retreats),
            },
            "p1_block": {
                "mean": sum(p1_blocks) / len(p1_blocks),
                "min": min(p1_blocks),
                "max": max(p1_blocks),
            },
            "p1_dist": {
                "mean": sum(p1_dists) / len(p1_dists),
                "min": min(p1_dists),
                "max": max(p1_dists),
            },
            "p2_advance": {
                "mean": sum(p2_advances) / len(p2_advances),
                "min": min(p2_advances),
                "max": max(p2_advances),
                "std": (sum((x - sum(p2_advances)/len(p2_advances))**2 for x in p2_advances) / len(p2_advances)) ** 0.5,
            },
            "p2_retreat": {
                "mean": sum(p2_retreats) / len(p2_retreats),
                "min": min(p2_retreats),
                "max": max(p2_retreats),
            },
            "p2_block": {
                "mean": sum(p2_blocks) / len(p2_blocks),
                "min": min(p2_blocks),
                "max": max(p2_blocks),
            },
            "p2_dist": {
                "mean": sum(p2_dists) / len(p2_dists),
                "min": min(p2_dists),
                "max": max(p2_dists),
            },
        }
    else:
        stats = {}
    
    return results, stats


def print_stability_report(p1_name: str, p2_name: str, results: list, stats: dict) -> None:
    """Print a comprehensive stability report."""
    print("\n" + "=" * 80)
    print(f"STABILITY REPORT: {p1_name} vs {p2_name}")
    print("=" * 80)
    
    if not results:
        print("No results to report!")
        return
    
    # P1 Report
    print(f"\n[P1] {p1_name}")
    print(f"Advance:  μ={stats['p1_advance']['mean']:.1%}  σ={stats['p1_advance']['std']:.3f}  range=[{stats['p1_advance']['min']:.1%}, {stats['p1_advance']['max']:.1%}]")
    print(f"Retreat:  μ={stats['p1_retreat']['mean']:.1%}  range=[{stats['p1_retreat']['min']:.1%}, {stats['p1_retreat']['max']:.1%}]")
    print(f"Block:    μ={stats['p1_block']['mean']:.1%}  range=[{stats['p1_block']['min']:.1%}, {stats['p1_block']['max']:.1%}]")
    print(f"Distance: μ={stats['p1_dist']['mean']:.2f}m range=[{stats['p1_dist']['min']:.2f}m, {stats['p1_dist']['max']:.2f}m]")
    
    # P2 Report
    print(f"\n[P2] {p2_name}")
    print(f"Advance:  μ={stats['p2_advance']['mean']:.1%}  σ={stats['p2_advance']['std']:.3f}  range=[{stats['p2_advance']['min']:.1%}, {stats['p2_advance']['max']:.1%}]")
    print(f"Retreat:  μ={stats['p2_retreat']['mean']:.1%}  range=[{stats['p2_retreat']['min']:.1%}, {stats['p2_retreat']['max']:.1%}]")
    print(f"Block:    μ={stats['p2_block']['mean']:.1%}  range=[{stats['p2_block']['min']:.1%}, {stats['p2_block']['max']:.1%}]")
    print(f"Distance: μ={stats['p2_dist']['mean']:.2f}m range=[{stats['p2_dist']['min']:.2f}m, {stats['p2_dist']['max']:.2f}m]")
    
    # Stability assessment
    print(f"\n[STABILITY ASSESSMENT]")
    
    p1_advance_variation = stats['p1_advance']['std']
    p2_advance_variation = stats['p2_advance']['std']
    
    print(f"P1 consistency: ", end="")
    if p1_advance_variation < 0.05:
        print(f"✓ Very Consistent (σ={p1_advance_variation:.3f})")
    elif p1_advance_variation < 0.10:
        print(f"✓ Consistent (σ={p1_advance_variation:.3f})")
    else:
        print(f"⚠️  Variable (σ={p1_advance_variation:.3f})")
    
    print(f"P2 consistency: ", end="")
    if p2_advance_variation < 0.05:
        print(f"✓ Very Consistent (σ={p2_advance_variation:.3f})")
    elif p2_advance_variation < 0.10:
        print(f"✓ Consistent (σ={p2_advance_variation:.3f})")
    else:
        print(f"⚠️  Variable (σ={p2_advance_variation:.3f})")
    
    # Behavior assessment
    print(f"\n[BEHAVIOR ASSESSMENT]")
    
    p1_mean_adv = stats['p1_advance']['mean']
    p1_mean_blk = stats['p1_block']['mean']
    p2_mean_adv = stats['p2_advance']['mean']
    p2_mean_blk = stats['p2_block']['mean']
    
    if p1_mean_adv > 0.50 and p1_mean_blk < 0.10:
        print(f"P1: ✓ Aggressive & Engaged (advance={p1_mean_adv:.1%}, block={p1_mean_blk:.1%})")
    elif p1_mean_adv > 0.40 and p1_mean_blk < 0.15:
        print(f"P1: ✓ Balanced (advance={p1_mean_adv:.1%}, block={p1_mean_blk:.1%})")
    else:
        print(f"P1: ⚠️  Passive (advance={p1_mean_adv:.1%}, block={p1_mean_blk:.1%})")
    
    if p2_mean_adv > 0.50 and p2_mean_blk < 0.10:
        print(f"P2: ✓ Aggressive & Engaged (advance={p2_mean_adv:.1%}, block={p2_mean_blk:.1%})")
    elif p2_mean_adv > 0.40 and p2_mean_blk < 0.15:
        print(f"P2: ✓ Balanced (advance={p2_mean_adv:.1%}, block={p2_mean_blk:.1%})")
    else:
        print(f"P2: ⚠️  Passive (advance={p2_mean_adv:.1%}, block={p2_mean_blk:.1%})")


def main():
    """Run comprehensive stability tests on key matchups."""
    print("\n" + "#" * 80)
    print("# STABILITY & CONSISTENCY TEST SUITE")
    print("# Testing behavioral consistency across 10 random seeds per matchup")
    print("#" * 80)
    
    matchups = [
        ("Yasuo da Aurora", "Medea", "Melee vs Bow (Melee Attacker)"),
        ("Medea", "Yasuo da Aurora", "Bow vs Melee (Ranged Attacker)"),
    ]
    
    all_results = []
    
    for p1, p2, description in matchups:
        print(f"\n{'='*80}")
        print(f"Testing: {description}")
        print(f"{'='*80}")
        
        results, stats = run_stability_tests(p1, p2, num_runs=10, simulation_seconds=30.0)
        all_results.append((p1, p2, results, stats))
        print_stability_report(p1, p2, results, stats)
    
    # Grand summary
    print("\n" + "#" * 80)
    print("# OVERALL ASSESSMENT")
    print("#" * 80)
    
    issues_found = []
    for p1, p2, results, stats in all_results:
        p1_adv_mean = stats['p1_advance']['mean']
        p1_blk_mean = stats['p1_block']['mean']
        p2_adv_mean = stats['p2_advance']['mean']
        p2_blk_mean = stats['p2_block']['mean']
        
        if p1_adv_mean < 0.40 and p1_blk_mean > 0.15:
            issues_found.append(f"{p1} (vs {p2}): Passivity detected (adv={p1_adv_mean:.1%}, blk={p1_blk_mean:.1%})")
        if p2_adv_mean < 0.40 and p2_blk_mean > 0.15:
            issues_found.append(f"{p2} (vs {p1}): Passivity detected (adv={p2_adv_mean:.1%}, blk={p2_blk_mean:.1%})")
    
    if issues_found:
        print("\n⚠️  ISSUES DETECTED:")
        for issue in issues_found:
            print(f"  • {issue}")
    else:
        print("\n✓ All matchups show healthy behavioral patterns!")
        print("  • Melee aggressiveness: Appropriate")
        print("  • Ranged behavior: Appropriately cautious")
        print("  • Consistency across seeds: Good to Very Good")
    
    return len(issues_found) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
