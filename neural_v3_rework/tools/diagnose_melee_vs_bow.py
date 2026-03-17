import os
import sys
from collections import Counter

# Headless pygame setup before importing simulation.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data.app_state import AppState
from simulation.simulacao import Simulador


def run_diagnostic(sim_seconds: float = 30.0):
    state = AppState.get()
    original_match = state.match_config

    try:
        # Force the known melee vs bow matchup available in current roster.
        state.set_match_config(
            {
                **original_match,
                "p1_nome": "Yasuo da Aurora",
                "p2_nome": "Medea",
                "cenario": original_match.get("cenario", "Arena"),
            }
        )

        sim = Simulador()
        p1 = sim.p1
        p2 = sim.p2

        # Enable decision debug logs for local run clarity.
        if p1 and p1.brain:
            p1.brain.DEBUG_AI_DECISIONS = True
        if p2 and p2.brain:
            p2.brain.DEBUG_AI_DECISIONS = True

        # We want melee as the actor under analysis.
        melee = p1
        bow = p2

        dt = 1.0 / 60.0
        frames = int(sim_seconds / dt)

        action_counts = Counter()
        advancing_actions = {"APROXIMAR", "PRESSIONAR", "FLANQUEAR", "MATAR", "ATAQUE_RAPIDO", "ESMAGAR"}
        retreat_actions = {"RECUAR", "FUGIR"}

        advancing_frames = 0
        retreat_frames = 0
        neutral_frames = 0
        blocked_frames = 0

        dist_start = None
        dist_end = None
        dist_min = 10**9
        dist_sum = 0.0

        timeline = []

        for i in range(frames):
            sim.update(dt)

            if melee.morto or bow.morto:
                break

            dx = bow.pos[0] - melee.pos[0]
            dy = bow.pos[1] - melee.pos[1]
            dist = (dx * dx + dy * dy) ** 0.5

            if dist_start is None:
                dist_start = dist
            dist_end = dist
            dist_min = min(dist_min, dist)
            dist_sum += dist

            acao = melee.brain.acao_atual if melee.brain else "SEM_BRAIN"
            action_counts[acao] += 1

            if acao in advancing_actions:
                advancing_frames += 1
            elif acao in retreat_actions:
                retreat_frames += 1
            elif acao == "BLOQUEAR":
                blocked_frames += 1
            elif acao == "NEUTRO":
                neutral_frames += 1

            if i % 120 == 0:
                timeline.append((i, round(dist, 2), acao))

        total_frames = sum(action_counts.values())
        avg_dist = (dist_sum / total_frames) if total_frames else 0.0

        print("=== DIAGNOSTICO MELEE VS ARCO ===")
        print(f"Melee: {melee.dados.nome} | Arma: {melee.dados.nome_arma}")
        print(f"Bow: {bow.dados.nome} | Arma: {bow.dados.nome_arma}")
        print("--- Distancia ---")
        print(f"dist_inicio={dist_start:.2f} dist_fim={dist_end:.2f} dist_min={dist_min:.2f} dist_media={avg_dist:.2f}")
        print("--- Frames por tipo de acao ---")
        if total_frames:
            print(f"avanco={advancing_frames} ({advancing_frames/total_frames:.1%})")
            print(f"recuo={retreat_frames} ({retreat_frames/total_frames:.1%})")
            print(f"bloqueio={blocked_frames} ({blocked_frames/total_frames:.1%})")
            print(f"neutro={neutral_frames} ({neutral_frames/total_frames:.1%})")
        else:
            print("Sem frames coletados")

        print("--- Top acoes ---")
        for acao, qtd in action_counts.most_common(8):
            pct = (qtd / total_frames) if total_frames else 0.0
            print(f"{acao}: {qtd} ({pct:.1%})")

        print("--- Timeline (a cada 120 frames) ---")
        for frm, d, ac in timeline:
            print(f"f={frm:4d} dist={d:5.2f} acao={ac}")

    finally:
        # Restore original match config to avoid polluting user state.
        state.set_match_config(original_match)
        try:
            import pygame

            pygame.display.quit()
            pygame.mixer.quit()
        except Exception as _e:  # E02 Sprint 12
            import logging as _lg; _lg.getLogger('tools').debug('pygame cleanup: %s', _e)


if __name__ == "__main__":
    run_diagnostic(30.0)
