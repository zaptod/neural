"""Tests for core/elo_system.py — ELO rating calculations."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.elo_system import calculate_elo, get_tier, get_tier_info, _k_factor, _expected_score


def test_equal_elo():
    """Equal-rated players: winner gains, loser loses roughly same amount."""
    dw, dl = calculate_elo(1600, 1600, ko=True)
    assert dw > 0, f"Winner should gain: {dw}"
    assert dl < 0, f"Loser should lose: {dl}"
    assert abs(dw + dl) < 5, f"Deltas should roughly cancel: {dw} + {dl}"
    print(f"  OK  T1: Equal ELO (delta_w={dw}, delta_l={dl})")


def test_upset_rewards_more():
    """Lower-rated player beating higher-rated gets bigger reward."""
    dw_upset, _ = calculate_elo(1400, 1800, ko=True)  # upset
    dw_normal, _ = calculate_elo(1800, 1400, ko=True)  # expected

    assert dw_upset > dw_normal, \
        f"Upset should reward more: {dw_upset} vs {dw_normal}"
    print(f"  OK  T2: Upset rewards more ({dw_upset:.1f} > {dw_normal:.1f})")


def test_ko_bonus():
    """KO victory should give higher delta than timeout."""
    dw_ko, _ = calculate_elo(1600, 1600, ko=True, duration=15.0)
    dw_timeout, _ = calculate_elo(1600, 1600, ko=False, duration=60.0)

    assert dw_ko > dw_timeout, \
        f"KO should give more: {dw_ko} vs {dw_timeout}"
    print(f"  OK  T3: KO bonus ({dw_ko:.1f} > {dw_timeout:.1f})")


def test_fast_ko_bonus():
    """Fast KO (< 10s) should give even more than normal KO."""
    dw_fast, _ = calculate_elo(1600, 1600, ko=True, duration=5.0)
    dw_normal, _ = calculate_elo(1600, 1600, ko=True, duration=25.0)

    assert dw_fast > dw_normal, \
        f"Fast KO should give more: {dw_fast} vs {dw_normal}"
    print(f"  OK  T4: Fast KO bonus ({dw_fast:.1f} > {dw_normal:.1f})")


def test_k_factor_adaptive():
    """K-factor should decrease with experience."""
    k_new = _k_factor(0)
    k_mid = _k_factor(15)
    k_vet = _k_factor(50)
    assert k_new > k_mid > k_vet, \
        f"K should decrease: {k_new} > {k_mid} > {k_vet}"
    print(f"  OK  T5: K-factor adaptive ({k_new} > {k_mid} > {k_vet})")


def test_experienced_player_stable():
    """Veteran (many matches) should have smaller rating swings."""
    dw_new, _ = calculate_elo(1600, 1600, winner_matches=0, ko=True)
    dw_vet, _ = calculate_elo(1600, 1600, winner_matches=50, ko=True)

    assert dw_new > dw_vet, \
        f"New player should swing more: {dw_new} vs {dw_vet}"
    print(f"  OK  T6: Experienced stability ({dw_new:.1f} > {dw_vet:.1f})")


def test_elo_floor():
    """Loser ELO delta should not take them below 0."""
    dw, dl = calculate_elo(1600, 5, ko=True)
    assert 5 + dl >= 0, f"ELO would go negative: 5 + {dl} = {5 + dl}"
    print(f"  OK  T7: ELO floor (5 + {dl} = {5 + dl})")


def test_tiers():
    assert get_tier(2500) == "MASTER"
    assert get_tier(2200) == "MASTER"
    assert get_tier(2100) == "DIAMOND"
    assert get_tier(1900) == "PLATINUM"
    assert get_tier(1700) == "GOLD"
    assert get_tier(1500) == "SILVER"
    assert get_tier(1300) == "BRONZE"
    assert get_tier(0) == "BRONZE"
    print("  OK  T8: Tier boundaries")


def test_tier_info():
    info = get_tier_info(1700)
    assert info["tier"] == "GOLD"
    assert info["next_tier"] == "PLATINUM"
    assert info["next_threshold"] == 1800
    assert 0 <= info["progress"] <= 1.0
    print(f"  OK  T9: Tier info (GOLD, progress={info['progress']:.2f})")


def test_expected_score_symmetry():
    """Expected scores should sum to 1."""
    e1 = _expected_score(1600, 1400)
    e2 = _expected_score(1400, 1600)
    assert abs(e1 + e2 - 1.0) < 0.001, f"{e1} + {e2} != 1.0"
    print(f"  OK  T10: Expected score symmetry ({e1:.3f} + {e2:.3f} = 1.0)")


def test_extreme_elo_difference():
    """Huge rating gap should still produce reasonable deltas."""
    dw, dl = calculate_elo(100, 3000, ko=True)
    assert dw > 0
    assert dl < 0
    assert dw < 50, f"Delta unreasonably large: {dw}"
    print(f"  OK  T11: Extreme difference (100 vs 3000, delta={dw:.1f})")


def test_full_elo_flow():
    """Simulate 5 matches and verify cumulative ELO makes sense."""
    elo_a = 1600.0
    elo_b = 1600.0
    matches_a = 0
    matches_b = 0

    # A wins 3 times
    for _ in range(3):
        dw, dl = calculate_elo(elo_a, elo_b, matches_a, matches_b, ko=True)
        elo_a += dw
        elo_b += dl
        matches_a += 1
        matches_b += 1

    # B wins 2 times
    for _ in range(2):
        dw, dl = calculate_elo(elo_b, elo_a, matches_b, matches_a, ko=True)
        elo_b += dw
        elo_a += dl
        matches_a += 1
        matches_b += 1

    assert elo_a > elo_b, f"A should be higher (3W vs 2W): A={elo_a:.1f} vs B={elo_b:.1f}"
    assert elo_a > 1600, f"A should be above start: {elo_a:.1f}"
    print(f"  OK  T12: Full flow (A={elo_a:.1f}, B={elo_b:.1f} after 5 matches)")


if __name__ == "__main__":
    tests = [
        test_equal_elo, test_upset_rewards_more, test_ko_bonus,
        test_fast_ko_bonus, test_k_factor_adaptive, test_experienced_player_stable,
        test_elo_floor, test_tiers, test_tier_info, test_expected_score_symmetry,
        test_extreme_elo_difference, test_full_elo_flow,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1

    print(f"\n=== ELO Tests: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed ===")
    if failed == 0:
        print("ALL TESTS PASSED!")
    sys.exit(failed)
