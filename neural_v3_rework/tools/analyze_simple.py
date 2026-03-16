"""
Simplified Stress Test Analysis
Analyzes available battle results data
"""
import os
import json
import statistics
from collections import defaultdict, Counter

def generate_simple_report(results_file: str = "stress_test_data/battle_results.json"):
    """Generate analysis report from battle results."""
    if not os.path.exists(results_file):
        print("❌ No battle results found")
        return
    
    with open(results_file, "r") as f:
        results = json.load(f)
    
    print("\n" + "#" * 80)
    print("# STRESS TEST - DATA ANALYSIS REPORT")
    print("#" * 80)
    print(f"\n✓ Analyzing {len(results)} battle results...\n")
    
    # ===== Overall Statistics =====
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)
    
    p1_wins = sum(1 for r in results if r["winner"] == "p1")
    p2_wins = sum(1 for r in results if r["winner"] == "p2")
    timeouts = sum(1 for r in results if r["winner"] == "timeout")
    
    print(f"Total Battles:        {len(results)}")
    print(f"P1 Wins:              {p1_wins} ({p1_wins/len(results)*100:.1f}%)")
    print(f"P2 Wins:              {p2_wins} ({p2_wins/len(results)*100:.1f}%)")
    print(f"Timeouts (draws):     {timeouts} ({timeouts/len(results)*100:.1f}%)")
    
    # Duration stats
    durations = [r["duration_frames"] for r in results]
    print(f"\nBattle Duration (frames):")
    print(f"  Min:                {min(durations)}")
    print(f"  Max:                {max(durations)}")
    print(f"  Average:            {statistics.mean(durations):.0f}")
    print(f"  Median:             {statistics.median(durations):.0f}")
    
    # ===== Personality Analysis =====
    print("\n" + "=" * 80)
    print("PERSONALITY WIN RATES (AS P1 ATTACKER)")
    print("=" * 80)
    
    pers_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "timeouts": 0})
    
    for battle in results:
        p1_pers = battle["p1_personality"]
        winner = battle["winner"]
        
        pers_stats[p1_pers]["total_battles"] = pers_stats[p1_pers].get("total_battles", 0) + 1
        
        if winner == "p1":
            pers_stats[p1_pers]["wins"] += 1
        elif winner == "p2":
            pers_stats[p1_pers]["losses"] += 1
        elif winner == "timeout":
            pers_stats[p1_pers]["timeouts"] += 1
    
    # Sort by win rate
    sorted_pers = sorted(pers_stats.items(), 
                        key=lambda x: x[1]["wins"] / x[1].get("total_battles", 1),
                        reverse=True)
    
    print(f"\n{' Personality':<20} {'Win Rate':<12} {'W-L':<15} {'Battles':<8}")
    print("-" * 80)
    
    issues = []
    for pers, stats in sorted_pers:
        total = stats.get("total_battles", 1)
        win_rate = stats["wins"] / total * 100
        print(f"{pers:<20} {win_rate:>6.1f}%      {stats['wins']:>2d}W-{stats['losses']:>2d}L"   f"      {total:>3d}")
        
        if win_rate < 30:
            issues.append(f"WEAK: {pers} ({win_rate:.1f}% win rate)")
        elif win_rate > 65:
            issues.append(f"STRONG: {pers} ({win_rate:.1f}% win rate)")
    
    # ===== Matchup Analysis =====
    print("\n" + "=" * 80)
    print("PERSONALITY MATCHUP ANALYSIS")
    print("=" * 80)
    
    matchups = defaultdict(lambda: {"p1_wins": 0, "p2_wins": 0, "timeouts": 0})
    
    for battle in results:
        key = (battle["p1_personality"], battle["p2_personality"])
        winner = battle["winner"]
        
        matchups[key]["total"] = matchups[key].get("total", 0) + 1
        
        if winner == "p1":
            matchups[key]["p1_wins"] += 1
        elif winner == "p2":
            matchups[key]["p2_wins"] += 1
        elif winner == "timeout":
            matchups[key]["timeouts"] += 1
    
    # Find most imbalanced matchups
    imbalanced = []
    for (p1_pers, p2_pers), stats in matchups.items():
        total = stats.get("total", 1)
        if total >= 2:  # Only consider matchups with at least 2 battles
            p1_win_rate = stats["p1_wins"] / total
            imbalance = abs(0.5 - p1_win_rate)
            imbalanced.append(((p1_pers, p2_pers), p1_win_rate, total))
    
    imbalanced.sort(key=lambda x: x[1], reverse=False)
    
    print(f"\nMost Lopsided Matchups (P1 Perspective):\n")
    print(f"{'P1 Personality':<20} {'vs P2':<20} {'P1 Win %':<12} {'Battles':<8}")
    print("-" * 80)
    
    for (p1_pers, p2_pers), win_rate, total in imbalanced[:8]:
        print(f"{p1_pers:<20} {p2_pers:<20} {win_rate*100:>6.1f}%      {total:>3d}")
        
        if win_rate < 0.20 or win_rate > 0.80:
            matchup_str = f"{p1_pers} vs {p2_pers}"
            issues.append(f"IMBALANCE: {matchup_str} ({win_rate*100:.1f}% P1 win rate)")
    
    # ===== Issues Report =====
    print("\n" + "=" * 80)
    print("IDENTIFIED CONCERNS")
    print("=" * 80)
    
    if issues:
        for issue in issues:
            if "WEAK" in issue:
                print(f"  ⚠️  {issue}")
            elif "STRONG" in issue:
                print(f"  ⚠️  {issue}")
            elif "IMBALANCE" in issue:
                print(f"  ⚠️  {issue}")
    else:
        print("\n  ✓ No major imbalances detected!")
    
    # ===== Recommendations =====
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS FOR BALANCING")
    print("=" * 80)
    
    weak_personalities = [i for i in issues if "WEAK" in i]
    strong_personalities = [i for i in issues if "STRONG" in i]
    imbalanced_matchups = [i for i in issues if "IMBALANCE" in i]
    
    if weak_personalities:
        print("\n1. WEAK PERSONALITIES (Win Rate < 30%):")
        for pers in weak_personalities:
            print(f"   • {pers}")
        print("   → Action: Increase approach_weight, combo_tendencia, or skill_agressividade")
        print("   → Action: Reduce recuar_threshold to be more aggressive")
    
    if strong_personalities:
        print("\n2. STRONG PERSONALITIES (Win Rate > 65%):")
        for pers in strong_personalities:
            print(f"   • {pers}")
        print("   → Action: Decrease combo_tendencia or skill_agressividade")
        print("   → Action: Increase recuar_threshold to be more conservative")
    
    if imbalanced_matchups:
        print("\n3. IMBALANCED MATCHUPS:")
        for matchup in imbalanced_matchups[:3]:
            print(f"   • {matchup}")
        print("   → Action: Add personality-aware decision logic")
        print("   → Action: Adjust weapon effectiveness for specific pairs")
    
    print("\n" + "=" * 80)
    print(f"✓ Analysis Complete!\n")


if __name__ == "__main__":
    generate_simple_report()
