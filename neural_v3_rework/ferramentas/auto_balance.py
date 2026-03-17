"""
NEURAL FIGHTS â€” Auto Balance Tournament  [F02]
===============================================
Roda um torneio round-robin headless e imprime win-rates por personagem,
classe e arma. Usado para medir o efeito de mudanÃ§as em balance_config.py.

Uso:
    python ferramentas/auto_balance.py                  # 50 lutas por matchup
    python ferramentas/auto_balance.py --fights 200     # 200 lutas por matchup
    python ferramentas/auto_balance.py --top 20         # mostrar top 20
    python ferramentas/auto_balance.py --sample 8       # 8 personagens aleatÃ³rios

Fluxo:
    1. Carrega personagens do AppState.
    2. Gera todos os matchups Ãºnicos (round-robin).
    3. Para cada matchup, roda N lutas headless (sem pygame window).
    4. Agrega win-rates e imprime relatÃ³rio.
    5. (Opcional) grava resultados em BattleDB.
"""

import os
import sys
import time
import random
import argparse
import logging
from collections import defaultdict
from typing import Optional

# â”€â”€ Headless pygame â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)
_log = logging.getLogger("auto_balance")

# â”€â”€ Constantes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MAX_FRAMES_PER_FIGHT = 60 * 90   # 90s timeout
DEFAULT_FIGHTS       = 50        # lutas por matchup
DEFAULT_TOP          = 20
DEFAULT_SAMPLE       = 0         # 0 = usar todos os personagens


# =============================================================================
# CORE: rodar uma luta headless
# =============================================================================

def _run_fight(state, p1_nome: str, p2_nome: str, cenario: str = "Arena") -> Optional[str]:
    """
    Roda uma luta headless entre p1 e p2.
    Retorna nome do vencedor, ou None em caso de empate/timeout.
    """
    from simulacao.simulacao import Simulador

    state.update_match_config(
        p1_nome=p1_nome,
        p2_nome=p2_nome,
        cenario=cenario,
    )

    try:
        sim = Simulador()
    except Exception as e:
        _log.warning("Falha ao criar Simulador(%s vs %s): %s", p1_nome, p2_nome, e)
        return None

    if not sim.p1 or not sim.p2:
        return None

    dt = 1.0 / 60.0
    for _ in range(MAX_FRAMES_PER_FIGHT):
        sim.update(dt)
        if sim.p1.morto or sim.p2.morto:
            break

    if sim.p1.morto and not sim.p2.morto:
        return p2_nome
    if sim.p2.morto and not sim.p1.morto:
        return p1_nome
    # Timeout ou double KO: vence quem tem mais HP restante
    if sim.p1.hp > sim.p2.hp:
        return p1_nome
    if sim.p2.hp > sim.p1.hp:
        return p2_nome
    return None  # empate real


# =============================================================================
# AGREGAÃ‡ÃƒO
# =============================================================================

class MatchupStats:
    """Agrega resultados de um matchup A vs B."""

    def __init__(self, a: str, b: str):
        self.a = a
        self.b = b
        self.wins_a = 0
        self.wins_b = 0
        self.draws  = 0

    @property
    def total(self) -> int:
        return self.wins_a + self.wins_b + self.draws

    @property
    def wr_a(self) -> float:
        return self.wins_a / max(1, self.total)

    @property
    def wr_b(self) -> float:
        return self.wins_b / max(1, self.total)

    def record(self, winner: Optional[str]) -> None:
        if winner == self.a:
            self.wins_a += 1
        elif winner == self.b:
            self.wins_b += 1
        else:
            self.draws += 1


# =============================================================================
# RELATÃ“RIO
# =============================================================================

def _print_report(
    matchups: list,
    char_meta: dict,
    top: int,
    elapsed: float,
) -> None:
    """Imprime relatÃ³rio completo de win-rates."""

    # Agregar por personagem
    char_wins   = defaultdict(int)
    char_played = defaultdict(int)

    for ms in matchups:
        char_played[ms.a] += ms.total
        char_played[ms.b] += ms.total
        char_wins[ms.a]   += ms.wins_a
        char_wins[ms.b]   += ms.wins_b

    # Ordenar por win-rate
    ranking = sorted(
        char_played.keys(),
        key=lambda n: char_wins[n] / max(1, char_played[n]),
        reverse=True,
    )

    total_fights = sum(ms.total for ms in matchups)

    print()
    print("=" * 70)
    print(f"  AUTO BALANCE REPORT â€” {total_fights} lutas em {elapsed:.1f}s")
    print("=" * 70)

    # â”€â”€ Ranking geral â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"\n{'#':>3} {'Personagem':<22} {'Classe':<15} {'Arma':<18} {'W':>4} {'G':>4} {'WR%':>6}")
    print("-" * 70)
    for i, nome in enumerate(ranking[:top], 1):
        meta = char_meta.get(nome, {})
        wr = char_wins[nome] / max(1, char_played[nome]) * 100
        classe = meta.get("classe", "?")[:14]
        arma   = meta.get("arma", "?")[:17]
        print(f"{i:>3} {nome:<22} {classe:<15} {arma:<18} "
              f"{char_wins[nome]:>4} {char_played[nome]:>4} {wr:>5.1f}%")

    # â”€â”€ Win-rate por classe â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    class_wins   = defaultdict(int)
    class_played = defaultdict(int)
    for nome in char_played:
        meta = char_meta.get(nome, {})
        cls  = meta.get("classe", "Desconhecida")
        class_wins[cls]   += char_wins[nome]
        class_played[cls] += char_played[nome]

    print(f"\n{'Classe':<25} {'W':>5} {'G':>6} {'WR%':>7}")
    print("-" * 45)
    for cls in sorted(class_played, key=lambda c: class_wins[c] / max(1, class_played[c]), reverse=True):
        wr = class_wins[cls] / max(1, class_played[cls]) * 100
        print(f"{cls:<25} {class_wins[cls]:>5} {class_played[cls]:>6} {wr:>6.1f}%")

    # â”€â”€ Matchups desequilibrados (WR > 70%) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    problematic = [ms for ms in matchups if ms.total >= 10 and (ms.wr_a > 0.70 or ms.wr_b > 0.70)]
    if problematic:
        print(f"\nâš   MATCHUPS DESEQUILIBRADOS (WR > 70% em {len(problematic)} matchups):")
        print(f"{'A':<22} {'B':<22} {'G':>4} {'A WR%':>7} {'B WR%':>7}")
        print("-" * 65)
        for ms in sorted(problematic, key=lambda m: max(m.wr_a, m.wr_b), reverse=True)[:15]:
            print(f"{ms.a:<22} {ms.b:<22} {ms.total:>4} {ms.wr_a*100:>6.1f}% {ms.wr_b*100:>6.1f}%")

    print("=" * 70)
    print()


# =============================================================================
# MAIN
# =============================================================================

def run(fights: int = DEFAULT_FIGHTS, top: int = DEFAULT_TOP, sample: int = DEFAULT_SAMPLE) -> None:
    from dados.app_state import AppState

    state = AppState.get()
    chars = state.characters

    if not chars:
        print("âŒ  Nenhum personagem no AppState. Rode o gerador de database primeiro.")
        return

    if sample > 0 and sample < len(chars):
        chars = random.sample(chars, sample)

    print(f"â–¶  {len(chars)} personagens | {fights} luta(s)/matchup | headless")

    # Metadados para o relatÃ³rio
    char_meta = {
        c.nome: {
            "classe": getattr(c, "classe", "?"),
            "arma":   getattr(c, "nome_arma", "?") or "Nenhuma",
        }
        for c in chars
    }

    # Gerar matchups round-robin
    names = [c.nome for c in chars]
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    total = len(pairs) * fights

    print(f"â–¶  {len(pairs)} matchups Ã— {fights} = {total} lutas totais\n")

    matchups_stats = [MatchupStats(a, b) for a, b in pairs]
    t0 = time.time()
    done = 0

    for ms in matchups_stats:
        for _ in range(fights):
            # Alterna quem vai primeiro para neutralizar side-bias
            if random.random() < 0.5:
                winner = _run_fight(state, ms.a, ms.b)
            else:
                winner = _run_fight(state, ms.b, ms.a)
            ms.record(winner)
            done += 1

        # Progress indicator
        pct = done / total * 100
        print(f"\r  {done}/{total} ({pct:.0f}%)  {ms.a} vs {ms.b}        ", end="", flush=True)

    elapsed = time.time() - t0
    print()  # newline apÃ³s progress

    _print_report(matchups_stats, char_meta, top, elapsed)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Roda torneio headless e mede win-rates para balance."
    )
    parser.add_argument(
        "--fights", type=int, default=DEFAULT_FIGHTS,
        help=f"Lutas por matchup (padrÃ£o: {DEFAULT_FIGHTS})"
    )
    parser.add_argument(
        "--top", type=int, default=DEFAULT_TOP,
        help=f"Mostrar top N personagens (padrÃ£o: {DEFAULT_TOP})"
    )
    parser.add_argument(
        "--sample", type=int, default=DEFAULT_SAMPLE,
        help="Usar N personagens aleatÃ³rios (0 = todos)"
    )
    args = parser.parse_args()
    run(fights=args.fights, top=args.top, sample=args.sample)

