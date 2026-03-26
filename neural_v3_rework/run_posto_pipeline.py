#!/usr/bin/env python3
"""Atalho para o posto de pipeline de videos."""

from __future__ import annotations

import argparse
import sys

from run_postos import main as run_postos_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neural Fights - atalho para o posto de pipeline")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Argumentos encaminhados para o pipeline de video.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parsed = build_parser().parse_args(argv)
    return run_postos_main(["pipeline", *parsed.args])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
