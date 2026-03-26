#!/usr/bin/env python3
"""Atalho para o posto headless de coleta rapida."""

from __future__ import annotations

import argparse
import sys

from run_postos import main as run_postos_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Neural Fights - atalho para o posto headless")
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Argumentos encaminhados para o runner headless.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parsed = build_parser().parse_args(argv)
    return run_postos_main(["headless", *parsed.args])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
