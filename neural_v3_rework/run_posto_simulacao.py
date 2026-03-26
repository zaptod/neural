#!/usr/bin/env python3
"""Atalho para o posto de simulacao completa."""

from __future__ import annotations

import argparse
import sys

from run_postos import main as run_postos_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neural Fights - posto de simulacao completa")
    parser.add_argument(
        "--modo",
        choices=["launcher", "sim", "manual"],
        default="launcher",
        help="launcher abre a UI principal; sim abre a luta automatica; manual abre o modo de teste.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parsed = build_parser().parse_args(argv)
    return run_postos_main(["simulacao", "--modo", parsed.modo])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
