#!/usr/bin/env python3
"""
Neural Fights v3 rework - ponto de entrada principal.
"""

from __future__ import annotations

import argparse
import os
import sys


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neural Fights v3 rework launcher")
    parser.add_argument("--sim", action="store_true", help="Inicia a simulacao automatica (IA vs IA).")
    parser.add_argument("--test", action="store_true", help="Inicia o modo de teste manual.")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Valida imports e contrato de bootstrap sem abrir janelas.",
    )
    return parser


def _resolve_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.sim and args.test:
        parser.error("Use apenas um entre --sim e --test.")
    if args.sim:
        return "sim"
    if args.test:
        return "test"
    return "launcher"


def _run_smoke(mode: str) -> int:
    if mode == "sim":
        from simulacao import Simulador  # noqa: F401

        target = "simulacao.Simulador"
    elif mode == "test":
        from utilitarios.test_manual import SimuladorManual  # noqa: F401

        target = "utilitarios.test_manual.SimuladorManual"
    else:
        from interface.main import main as run_launcher  # noqa: F401

        target = "interface.main"
    print(f"[smoke] bootstrap ok: {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = _resolve_mode(args, parser)

    if args.smoke:
        return _run_smoke(mode)

    if mode == "sim":
        from simulacao import Simulador

        sim = Simulador()
        sim.executar()
        return 0

    if mode == "test":
        from utilitarios.test_manual import SimuladorManual

        sim = SimuladorManual()
        sim.executar()
        return 0

    from interface.main import main as run_launcher

    run_launcher()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
