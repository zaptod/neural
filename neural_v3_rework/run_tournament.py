"""
Neural Fights v3 rework - lancador do modo torneio.
"""

from __future__ import annotations

import argparse
import os
import sys


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neural Fights - modo torneio")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Valida imports e contrato do launcher sem abrir janelas.",
    )
    return parser


def _load_tournament_window():
    try:
        import customtkinter as ctk
    except ImportError:
        print("=" * 60)
        print("  ERRO: CustomTkinter nao instalado.")
        print("=" * 60)
        print("  Execute: pip install customtkinter")
        return None, None

    from interface.view_torneio import TournamentWindow

    return ctk, TournamentWindow


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ctk, tournament_window = _load_tournament_window()
    if ctk is None or tournament_window is None:
        return 1

    if args.smoke:
        print("[smoke] bootstrap ok: run_tournament -> interface.view_torneio.TournamentWindow")
        return 0

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    print("=" * 60)
    print("  NEURAL FIGHTS - MODO TORNEIO")
    print("=" * 60)
    print("  Iniciando janela do torneio...")

    root = ctk.CTk()
    root.withdraw()

    window = tournament_window(root)
    window.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
