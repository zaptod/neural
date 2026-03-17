"""
Stress Test: Battle Simulator
Runs hundreds of battles with generated characters and collects performance data.
"""
import os
import sys
import json
import random
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

# Headless pygame setup
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dados.app_state import AppState
from simulacao.simulacao import Simulador


@dataclass
class BattleResult:
    """Store result of a single battle."""
    p1_name: str
    p1_personality: str
    p1_class: str
    p1_weapon: str
    p1_size: float
    p1_force: float
    p1_mana: float
    p2_name: str
    p2_personality: str
    p2_class: str
    p2_weapon: str
    p2_size: float
    p2_force: float
    p2_mana: float
    winner: str  # "p1", "p2", or "draw"
    duration_frames: int
    p1_damage_dealt: float
    p2_damage_dealt: float
    p1_avg_advance_pct: float
    p1_avg_distance: float


def load_test_characters(chars_file: str) -> List[Dict]:
    """Load generated test characters."""
    if not os.path.exists(chars_file):
        print(f"âŒ File not found: {chars_file}")
        return []
    
    with open(chars_file, "r", encoding="utf-8") as f:
        return json.load(f)


def simulate_battle(p1_data: Dict, p2_data: Dict, max_duration_frames: int = 2000) -> BattleResult:
    """
    Simulate a single battle between two characters.
    """
    state = AppState.get()
    original_match = state.match_config

    try:
        # Set up match with generated characters
        state.set_match_config({
            **original_match,
            "p1_nome": p1_data["nome"],
            "p2_nome": p2_data["nome"],
            "p1_custom": p1_data,
            "p2_custom": p2_data,
            "cenario": original_match.get("cenario", "Arena"),
        })

        sim = Simulador()
        p1 = sim.p1
        p2 = sim.p2

        if not p1 or not p2:
            raise RuntimeError("Failed to create combatants")

        dt = 1.0 / 60.0
        frames = 0
        max_frames = max_duration_frames

        # Track stats
        p1_damage = 0.0
        p2_damage = 0.0
        p1_advance_frames = 0
        p1_distance_sum = 0.0
        p1_distance_count = 0

        advancing_actions = {"APROXIMAR", "PRESSIONAR", "FLANQUEAR", "MATAR", "ATAQUE_RAPIDO", "ESMAGAR"}

        while frames < max_frames and not p1.morto and not p2.morto:
            sim.update(dt)

            # Track damage
            p1_damage = p1.hp_original - p1.hp if p1.hp_original > 0 else 0
            p2_damage = p2.hp_original - p2.hp if p2.hp_original > 0 else 0

            # Track P1 actions
            p1_acao = p1.brain.acao_atual if p1.brain else "NEUTRO"
            if p1_acao in advancing_actions:
                p1_advance_frames += 1

            # Track distance
            dx = p2.pos[0] - p1.pos[0]
            dy = p2.pos[1] - p1.pos[1]
            dist = (dx * dx + dy * dy) ** 0.5
            p1_distance_sum += dist
            p1_distance_count += 1

            frames += 1

        # Determine winner
        if p1.morto and p2.morto:
            winner = "draw"
        elif p1.morto:
            winner = "p2"
        elif p2.morto:
            winner = "p1"
        else:
            # Draw if timeout
            winner = "draw"

        p1_avg_advance = p1_advance_frames / frames if frames > 0 else 0.0
        p1_avg_distance = p1_distance_sum / p1_distance_count if p1_distance_count > 0 else 0.0

        return BattleResult(
            p1_name=p1.dados.nome,
            p1_personality=p1.dados.personalidade,
            p1_class=p1.dados.classe,
            p1_weapon=p1.dados.nome_arma,
            p1_size=p1.dados.tamanho,
            p1_force=p1.dados.forca,
            p1_mana=p1.dados.mana,
            p2_name=p2.dados.nome,
            p2_personality=p2.dados.personalidade,
            p2_class=p2.dados.classe,
            p2_weapon=p2.dados.nome_arma,
            p2_size=p2.dados.tamanho,
            p2_force=p2.dados.forca,
            p2_mana=p2.dados.mana,
            winner=winner,
            duration_frames=frames,
            p1_damage_dealt=p1_damage,
            p2_damage_dealt=p2_damage,
            p1_avg_advance_pct=p1_avg_advance,
            p1_avg_distance=p1_avg_distance,
        )

    except Exception as e:
        print(f"  Error in battle {p1_data['nome']} vs {p2_data['nome']}: {e}")
        return None
    finally:
        state.set_match_config(original_match)
        try:
            import pygame
            pygame.display.quit()
            pygame.mixer.quit()
        except Exception as _e:  # E02 Sprint 12
            import logging as _lg; _lg.getLogger('tools').debug('pygame cleanup: %s', _e)


def run_stress_test(
    characters: List[Dict],
    num_battles: int = 500,
    output_dir: str = "stress_test_data"
) -> List[BattleResult]:
    """
    Run multiple battles and collect results.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    failed = 0
    
    print(f"\n{'='*80}")
    print(f"STRESS TEST: Running {num_battles} battles")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    
    for i in range(num_battles):
        # Pick two random characters
        p1_data = random.choice(characters)
        p2_data = random.choice(characters)
        
        # Avoid same character
        while p2_data["nome"] == p1_data["nome"]:
            p2_data = random.choice(characters)
        
        print(f"  [{i+1:4d}/{num_battles}] {p1_data['nome']:25s} vs {p2_data['nome']:25s}... ", end="", flush=True)
        
        result = simulate_battle(p1_data, p2_data)
        
        if result:
            results.append(result)
            winner_name = "P1" if result.winner == "p1" else ("P2" if result.winner == "p2" else "Draw")
            print(f"âœ“ {winner_name} ({result.duration_frames}f)")
        else:
            failed += 1
            print(f"âœ—")
        
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
    print(f"Rate:              {len(results)/elapsed_time:.1f} battles/sec\n")
    
    # Save results
    results_file = os.path.join(output_dir, "battle_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
    
    print(f"âœ“ Results saved to {results_file}\n")
    
    return results


if __name__ == "__main__":
    # Load characters
    chars_file = "stress_test_dados/test_characters.json"
    characters = load_test_characters(chars_file)
    
    if not characters:
        print("âŒ No characters loaded. Run generate_stress_test_characters.py first.")
        sys.exit(1)
    
    print(f"âœ“ Loaded {len(characters)} test characters\n")
    
    # Run stress test
    results = run_stress_test(characters, num_battles=500)
    
    if results:
        print(f"âœ“ Stress test completed with {len(results)} battles")

