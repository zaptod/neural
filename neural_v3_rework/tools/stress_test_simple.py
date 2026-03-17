"""
Simplified Stress Test: Battle Simulator
Runs battles with personality variations and collects performance data.
"""
import os
import sys
import json
import random
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List

# Headless pygame setup
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data.app_state import AppState
from simulation.simulacao import Simulador


@dataclass
class BattleResult:
    """Store result of a single battle."""
    p1_name: str
    p1_personality: str
    p2_name: str
    p2_personality: str
    winner: str  # "p1", "p2", or "timeout"
    duration_frames: int
    p1_damage_dealt: float
    p2_damage_dealt: float


def load_available_characters() -> List[str]:
    """Load available character names from personagens.json."""
    chars_file = os.path.join(BASE_DIR, "data", "personagens.json")
    if not os.path.exists(chars_file):
        return ["Yasuo da Aurora", "Medea"]
    
    with open(chars_file, "r", encoding="utf-8") as f:
        characters = json.load(f)
    
    return [c["nome"] for c in characters]


# All available personalities
PERSONALITIES = [
    "Agressivo", "Berserker", "Perseguidor", "Destruidor", "Viking",
    "Zerg Rush", "Pugilista", "Predador Alfa",
    "Defensivo", "Protetor", "Fantasma", "Masoquista",
    "Tático", "Samurai", "Contemplativo", "Psicopata",
    "Sombrio", "Assassino", "Acrobático", "Capoeirista", "Showman"
]


def simulate_battle(
    p1_name: str,
    p1_personality: str,
    p2_name: str,
    p2_personality: str,
    max_duration_frames: int = 2000
) -> BattleResult:
    """
    Simulate a battle between two characters with different personalities.
    """
    state = AppState.get()
    original_match = state.match_config

    try:
        # Force personalities by updating match config
        match_config = {
            **original_match,
            "p1_nome": p1_name,
            "p2_nome": p2_name,
            "cenario": original_match.get("cenario", "Arena"),
        }
        
        state.set_match_config(match_config)

        sim = Simulador()
        p1 = sim.p1
        p2 = sim.p2

        if not p1 or not p2:
            raise RuntimeError("Failed to create combatants")

        # Override personalities
        if p1.brain:
            p1.dados.personalidade = p1_personality
            # Rebuild brain with new personality
            p1.brain.personalidade = p1_personality
        
        if p2.brain:
            p2.dados.personalidade = p2_personality
            p2.brain.personalidade = p2_personality

        dt = 1.0 / 60.0
        frames = 0
        max_frames = max_duration_frames

        # Track damage
        p1_damage = 0.0
        p2_damage = 0.0

        while frames < max_frames and not p1.morto and not p2.morto:
            sim.update(dt)

            # Track damage taken
            p1_damage = p1.vida_max - p1.vida if p1.vida_max > 0 else 0
            p2_damage = p2.vida_max - p2.vida if p2.vida_max > 0 else 0

            frames += 1

        # Determine winner
        if p1.morto and not p2.morto:
            winner = "p2"
        elif p2.morto and not p1.morto:
            winner = "p1"
        else:
            winner = "timeout"

        return BattleResult(
            p1_name=p1_name,
            p1_personality=p1_personality,
            p2_name=p2_name,
            p2_personality=p2_personality,
            winner=winner,
            duration_frames=frames,
            p1_damage_dealt=p1_damage,
            p2_damage_dealt=p2_damage,
        )

    except Exception as e:
        print(f"    Error: {str(e)[:50]}")
        return None
    finally:
        state.set_match_config(original_match)
        try:
            import pygame
            pygame.display.quit()
            pygame.mixer.quit()
        except Exception as _e:  # E02 Sprint 12
            import logging as _lg; _lg.getLogger('tools').debug('pygame cleanup: %s', _e)


def run_stress_test(num_battles: int = 200, output_dir: str = "stress_test_data") -> List[BattleResult]:
    """
    Run battles with different personality combinations.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Load available characters
    available_chars = load_available_characters()
    if len(available_chars) < 2:
        available_chars = ["Yasuo da Aurora", "Medea"]
    
    results = []
    failed = 0
    
    print(f"\n{'='*80}")
    print(f"STRESS TEST: Personality Variations ({num_battles} battles)")
    print(f"{'='*80}\n")
    print(f"Available characters: {', '.join(available_chars[:3])}{'...' if len(available_chars) > 3 else ''}\n")
    
    start_time = time.time()
    
    for i in range(num_battles):
        # Pick two random characters and personalities
        p1_name = random.choice(available_chars)
        p2_name = random.choice(available_chars)
        p1_pers = random.choice(PERSONALITIES)
        p2_pers = random.choice(PERSONALITIES)
        
        print(f"  [{i+1:3d}/{num_battles}] {p1_name:20s} ({p1_pers:15s}) vs {p2_name:20s} ({p2_pers:15s})... ", end="", flush=True)
        
        result = simulate_battle(p1_name, p1_pers, p2_name, p2_pers)
        
        if result:
            results.append(result)
            winner = "P1" if result.winner == "p1" else ("P2" if result.winner == "p2" else "TO")
            print(f"✓ {winner}")
        else:
            failed += 1
            print(f"✗")
        
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (num_battles - i - 1) / rate if rate > 0 else 0
            print(f"  Progress: {i+1}/{num_battles} ({rate:.1f} battles/sec, ~{remaining:.0f}s remaining)\n")
    
    elapsed_time = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"STRESS TEST COMPLETE")
    print(f"{'='*80}")
    print(f"Battles completed: {len(results)}")
    print(f"Battles failed:    {failed}")
    print(f"Time elapsed:      {elapsed_time:.1f}s")
    if len(results) > 0:
        print(f"Rate:              {len(results)/elapsed_time:.1f} battles/sec\n")
    
    # Save results
    results_file = os.path.join(output_dir, "battle_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to {results_file}\n")
    
    return results


if __name__ == "__main__":
    results = run_stress_test(num_battles=200)
    
    if results:
        print(f"✓ Stress test completed with {len(results)} battles")
