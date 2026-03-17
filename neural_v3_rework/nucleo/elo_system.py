"""
NEURAL FIGHTS â€” ELO Rating System v1.0
========================================
Competitive ranking with adaptive K-factor and tier progression.

Uses standard ELO with modifications:
- Adaptive K-factor: new players shift faster, veterans are stable
- KO bonus: decisive victories earn more rating
- Tier system: BRONZE â†’ SILVER â†’ GOLD â†’ PLATINUM â†’ DIAMOND â†’ MASTER
- Floor: ELO never drops below 0

Usage:
    from nucleo.elo_system import calculate_elo, get_tier

    delta_w, delta_l = calculate_elo(
        winner_elo=1600, loser_elo=1550,
        winner_matches=10, loser_matches=5,
        ko=True, duration=15.0
    )
    # delta_w â‰ˆ +18.2, delta_l â‰ˆ -18.2

    tier = get_tier(1850)  # "GOLD"
"""

from typing import Tuple

# â”€â”€ Tier boundaries â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TIERS = [
    ("MASTER",   2200),
    ("DIAMOND",  2000),
    ("PLATINUM", 1800),
    ("GOLD",     1600),
    ("SILVER",   1400),
    ("BRONZE",      0),
]


def get_tier(elo: float) -> str:
    """Return the tier name for a given ELO value."""
    for name, threshold in TIERS:
        if elo >= threshold:
            return name
    return "BRONZE"


def get_tier_info(elo: float) -> dict:
    """Return tier name, current threshold, and next tier threshold."""
    for i, (name, threshold) in enumerate(TIERS):
        if elo >= threshold:
            next_tier = TIERS[i - 1][0] if i > 0 else None
            next_threshold = TIERS[i - 1][1] if i > 0 else None
            return {
                "tier": name,
                "threshold": threshold,
                "next_tier": next_tier,
                "next_threshold": next_threshold,
                "progress": ((elo - threshold) / (next_threshold - threshold))
                            if next_threshold else 1.0,
            }
    return {"tier": "BRONZE", "threshold": 0, "next_tier": "SILVER",
            "next_threshold": 1400, "progress": elo / 1400}


# â”€â”€ K-Factor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _k_factor(matches_played: int) -> float:
    """
    Adaptive K-factor:
    - New players (< 10 matches): K=40  (fast placement)
    - Developing (10-30 matches): K=32  (moderate shift)
    - Experienced (> 30 matches): K=24  (stable rating)
    """
    if matches_played < 10:
        return 40.0
    elif matches_played < 30:
        return 32.0
    else:
        return 24.0


# â”€â”€ Expected score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _expected_score(elo_a: float, elo_b: float) -> float:
    """Standard ELO expected score for player A vs player B."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


# â”€â”€ KO Multiplier â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _ko_multiplier(ko: bool, duration: float) -> float:
    """
    Bonus/penalty based on match outcome:
    - KO victory: 1.15x (decisive)
    - Fast KO (< 10s): 1.25x (dominant)
    - Timeout: 0.85x (inconclusive)
    """
    if not ko:
        return 0.85
    if duration < 10.0:
        return 1.25
    return 1.15


# â”€â”€ Main calculation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def calculate_elo(winner_elo: float, loser_elo: float,
                  winner_matches: int = 0, loser_matches: int = 0,
                  ko: bool = True, duration: float = 30.0) -> Tuple[float, float]:
    """
    Calculate ELO deltas for winner and loser.

    Returns:
        (winner_delta, loser_delta) â€” winner_delta is positive, loser_delta is negative.
    """
    # Expected scores
    exp_w = _expected_score(winner_elo, loser_elo)
    exp_l = 1.0 - exp_w

    # K-factors (each player has their own)
    k_w = _k_factor(winner_matches)
    k_l = _k_factor(loser_matches)

    # KO multiplier
    ko_mult = _ko_multiplier(ko, duration)

    # Deltas: actual_score - expected_score, scaled by K and KO multiplier
    delta_w = k_w * (1.0 - exp_w) * ko_mult
    delta_l = k_l * (0.0 - exp_l) * ko_mult

    # Ensure loser ELO doesn't go below 0
    if loser_elo + delta_l < 0:
        delta_l = -loser_elo

    return round(delta_w, 2), round(delta_l, 2)

