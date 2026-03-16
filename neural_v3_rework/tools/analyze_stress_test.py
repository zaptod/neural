"""
Stress Test Data Analysis
Analyzes battle results to identify problematic personalities, classes, and attributes.
"""
import os
import sys
import json
import statistics
from collections import defaultdict, Counter
from typing import Dict, List, Tuple
import warnings

warnings.filterwarnings("ignore")

def load_battle_results(results_file: str = "stress_test_data/battle_results.json") -> List[Dict]:
    """Load battle results from JSON."""
    if not os.path.exists(results_file):
        print(f"❌ File not found: {results_file}")
        return []
    
    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_characters(chars_file: str = "stress_test_data/test_characters.json") -> Dict:
    """Load characters and create lookup."""
    if not os.path.exists(chars_file):
        return {}
    
    with open(chars_file, "r", encoding="utf-8") as f:
        chars = json.load(f)
    
    return {c["nome"]: c for c in chars}


def calculate_win_rates_by_personality(results: List[Dict]) -> Dict:
    """Calculate win rates grouped by personality."""
    personality_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    
    for battle in results:
        p1_pers = battle["p1_personality"]
        p2_pers = battle["p2_personality"]
        winner = battle["winner"]
        
        # P1 stats
        personality_stats[p1_pers]["total"] += 1
        if winner == "p1":
            personality_stats[p1_pers]["wins"] += 1
        elif winner == "p2":
            personality_stats[p1_pers]["losses"] += 1
        else:
            personality_stats[p1_pers]["draws"] += 1
        
        # P2 stats
        personality_stats[p2_pers]["total"] += 1
        if winner == "p2":
            personality_stats[p2_pers]["wins"] += 1
        elif winner == "p1":
            personality_stats[p2_pers]["losses"] += 1
        else:
            personality_stats[p2_pers]["draws"] += 1
    
    return dict(personality_stats)


def calculate_win_rates_by_class(results: List[Dict]) -> Dict:
    """Calculate win rates grouped by class."""
    class_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "total": 0})
    
    for battle in results:
        p1_class = battle["p1_class"]
        p2_class = battle["p2_class"]
        winner = battle["winner"]
        
        # P1 stats
        class_stats[p1_class]["total"] += 1
        if winner == "p1":
            class_stats[p1_class]["wins"] += 1
        elif winner == "p2":
            class_stats[p1_class]["losses"] += 1
        else:
            class_stats[p1_class]["draws"] += 1
        
        # P2 stats
        class_stats[p2_class]["total"] += 1
        if winner == "p2":
            class_stats[p2_class]["wins"] += 1
        elif winner == "p1":
            class_stats[p2_class]["losses"] += 1
        else:
            class_stats[p2_class]["draws"] += 1
    
    return dict(class_stats)


def calculate_attribute_correlation(results: List[Dict]) -> Dict:
    """Analyze correlation between attributes and win rates."""
    # P1 attacker analysis
    p1_winners = [b for b in results if b["winner"] == "p1"]
    p1_losers = [b for b in results if b["winner"] == "p2"]
    p1_draws = [b for b in results if b["winner"] == "draw"]
    
    def get_avg(battles, key):
        if not battles:
            return 0
        return sum(b[key] for b in battles) / len(battles)
    
    correlation = {
        "size": {
            "winners_avg": get_avg(p1_winners, "p1_size"),
            "losers_avg": get_avg(p1_losers, "p1_size"),
            "draws_avg": get_avg(p1_draws, "p1_size"),
        },
        "force": {
            "winners_avg": get_avg(p1_winners, "p1_force"),
            "losers_avg": get_avg(p1_losers, "p1_force"),
            "draws_avg": get_avg(p1_draws, "p1_force"),
        },
        "mana": {
            "winners_avg": get_avg(p1_winners, "p1_mana"),
            "losers_avg": get_avg(p1_losers, "p1_mana"),
            "draws_avg": get_avg(p1_draws, "p1_mana"),
        },
    }
    
    return correlation


def analyze_matchups(results: List[Dict]) -> Dict:
    """Analyze personality matchups."""
    matchup_stats = defaultdict(lambda: {"p1_wins": 0, "p2_wins": 0, "draws": 0, "total": 0})
    
    for battle in results:
        matchup = (battle["p1_personality"], battle["p2_personality"])
        winner = battle["winner"]
        
        matchup_stats[matchup]["total"] += 1
        if winner == "p1":
            matchup_stats[matchup]["p1_wins"] += 1
        elif winner == "p2":
            matchup_stats[matchup]["p2_wins"] += 1
        else:
            matchup_stats[matchup]["draws"] += 1
    
    return dict(matchup_stats)


def identify_issues(results: List[Dict]) -> List[str]:
    """Identify problematic personalities, classes, or matchups."""
    issues = []
    
    # Win rate analysis by personality
    pers_stats = calculate_win_rates_by_personality(results)
    
    print("\n" + "=" * 80)
    print("PERSONALITY WIN RATES")
    print("=" * 80)
    
    # Sort by win rate
    pers_rates = {}
    for pers, stats in pers_stats.items():
        if stats["total"] > 0:
            pers_rates[pers] = stats["wins"] / stats["total"]
            win_pct = pers_rates[pers] * 100
            print(f"  {pers:20s}: {win_pct:5.1f}% ({stats['wins']:3d}W {stats['losses']:3d}L {stats['draws']:3d}D, n={stats['total']})")
    
    # Find problematic personalities
    sorted_pers = sorted(pers_rates.items(), key=lambda x: x[1])
    worst_pers = sorted_pers[:3]  # 3 worst
    best_pers = sorted_pers[-3:]  # 3 best
    
    for pers, rate in worst_pers:
        if rate < 0.40:  # Win rate below 40%
            issues.append(f"⚠️  Personality '{pers}' is underperforming ({rate*100:.1f}% win rate)")
    
    for pers, rate in best_pers:
        if rate > 0.60:  # Win rate above 60%
            issues.append(f"⚠️  Personality '{pers}' is overpowered ({rate*100:.1f}% win rate)")
    
    # Win rate analysis by class
    class_stats = calculate_win_rates_by_class(results)
    
    print("\n" + "=" * 80)
    print("CLASS WIN RATES")
    print("=" * 80)
    
    class_rates = {}
    for cls, stats in class_stats.items():
        if stats["total"] > 0:
            class_rates[cls] = stats["wins"] / stats["total"]
            win_pct = class_rates[cls] * 100
            short_cls = cls[:30]
            print(f"  {short_cls:30s}: {win_pct:5.1f}% ({stats['wins']:3d}W {stats['losses']:3d}L {stats['draws']:3d}D, n={stats['total']})")
    
    # Find problematic classes
    sorted_classes = sorted(class_rates.items(), key=lambda x: x[1])
    worst_classes = sorted_classes[:3]
    best_classes = sorted_classes[-3:]
    
    for cls, rate in worst_classes:
        if rate < 0.40:
            issues.append(f"⚠️  Class '{cls}' is underperforming ({rate*100:.1f}% win rate)")
    
    for cls, rate in best_classes:
        if rate > 0.60:
            issues.append(f"⚠️  Class '{cls}' is overpowered ({rate*100:.1f}% win rate)")
    
    # Attribute correlation
    print("\n" + "=" * 80)
    print("ATTRIBUTE CORRELATION WITH WIN RATE")
    print("=" * 80)
    
    correlation = calculate_attribute_correlation(results)
    
    for attr, stats in correlation.items():
        winner_avg = stats["winners_avg"]
        loser_avg = stats["losers_avg"]
        diff = winner_avg - loser_avg
        
        print(f"\n  {attr.upper()}:")
        print(f"    Winners (P1):  {winner_avg:.2f}")
        print(f"    Losers (P1):   {loser_avg:.2f}")
        print(f"    Difference:    {diff:+.2f} ({abs(diff)/loser_avg*100:.1f}% change)")
        
        if abs(diff) < 0.1:
            issues.append(f"⚠️  Attribute '{attr}' has minimal impact on win rate (may need adjustment)")
    
    # Matchup analysis (find most imbalanced)
    print("\n" + "=" * 80)
    print("MOST IMBALANCED MATCHUPS (P1 Perspective)")
    print("=" * 80)
    
    matchups = analyze_matchups(results)
    matchup_rates = {}
    
    for (p1_pers, p2_pers), stats in matchups.items():
        if stats["total"] >= 3:  # Only consider matchups with at least 3 battles
            p1_win_rate = stats["p1_wins"] / stats["total"]
            matchup_rates[(p1_pers, p2_pers)] = p1_win_rate
    
    sorted_matchups = sorted(matchup_rates.items(), key=lambda x: abs(0.5 - x[1]), reverse=True)
    
    for (p1_pers, p2_pers), rate in sorted_matchups[:5]:
        print(f"  {p1_pers:15s} vs {p2_pers:15s}: {rate*100:5.1f}% (P1 win rate)")
        if rate < 0.25 or rate > 0.75:
            issues.append(f"⚠️  Matchup '{p1_pers} vs {p2_pers}' is heavily imbalanced ({rate*100:.1f}%)")
    
    return issues


def generate_report(results_file: str = "stress_test_data/battle_results.json") -> None:
    """Generate comprehensive analysis report."""
    print("\n" + "#" * 80)
    print("# STRESS TEST DATA ANALYSIS")
    print("#" * 80)
    
    results = load_battle_results(results_file)
    characters = load_characters()
    
    if not results:
        print("❌ No results to analyze")
        return
    
    print(f"\n✓ Analyzing {len(results)} battle results...")
    
    # Overall statistics
    print("\n" + "=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    
    p1_wins = sum(1 for r in results if r["winner"] == "p1")
    p2_wins = sum(1 for r in results if r["winner"] == "p2")
    draws = sum(1 for r in results if r["winner"] == "draw")
    
    print(f"  Total Battles:     {len(results)}")
    print(f"  P1 Wins:           {p1_wins} ({p1_wins/len(results)*100:.1f}%)")
    print(f"  P2 Wins:           {p2_wins} ({p2_wins/len(results)*100:.1f}%)")
    print(f"  Draws:             {draws} ({draws/len(results)*100:.1f}%)")
    
    # Duration statistics
    durations = [r["duration_frames"] for r in results]
    print(f"\n  Battle Duration (frames):")
    print(f"    Min:       {min(durations)}")
    print(f"    Max:       {max(durations)}")
    print(f"    Average:   {statistics.mean(durations):.0f}")
    print(f"    Median:    {statistics.median(durations):.0f}")
    print(f"    Stdev:     {statistics.stdev(durations):.0f}")
    
    # Damage statistics
    p1_damage_dealt = [r["p1_damage_dealt"] for r in results]
    print(f"\n  P1 Damage Dealt (to opponents):")
    print(f"    Min:       {min(p1_damage_dealt):.1f}")
    print(f"    Max:       {max(p1_damage_dealt):.1f}")
    print(f"    Average:   {statistics.mean(p1_damage_dealt):.1f}")
    
    # Identify issues
    issues = identify_issues(results)
    
    # Report issues
    print("\n" + "=" * 80)
    print("IDENTIFIED CONCERNS")
    print("=" * 80)
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n  ✓ No major imbalances detected!")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if any("underperform" in issue.lower() for issue in issues):
        print("  • Adjust personality multipliers for underperforming archetypes")
        print("  • Consider increasing approach_weight or reducing retreat_weight")
    
    if any("overpowered" in issue.lower() for issue in issues):
        print("  • Fine-tune multipliers for overpowered personalities")
        print("  • Consider reducing combo_tendencia or skill_agressividade")
    
    if any("imbalanced" in issue.lower() for issue in issues):
        print("  • Review personality matchup-specific behavior")
        print("  • Consider adding personality-aware decision logic")
    
    print(f"\n  ✓ Analysis complete!\n")


if __name__ == "__main__":
    generate_report()
