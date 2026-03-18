#!/usr/bin/env python3
"""Atalho para o posto de simulação completa."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from utilitarios.postos_operacao import create_session_dir, ensure_posto_dirs, write_session_manifest


ROOT = os.path.dirname(os.path.abspath(__file__))
RUN_SCRIPT = os.path.join(ROOT, "run.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Neural Fights - Posto de simulacao completa")
    parser.add_argument(
        "--modo",
        choices=["launcher", "sim", "manual"],
        default="launcher",
        help="launcher abre a UI principal; sim abre a luta automatica; manual abre o modo de teste.",
    )
    args = parser.parse_args()

    ensure_posto_dirs()
    session_dir = create_session_dir("simulacao")
    write_session_manifest(
        session_dir,
        {"posto": "simulacao", "modo": args.modo, "args": sys.argv[1:], "saida_logica": "saidas/simulacao"},
    )

    cmd = [sys.executable, RUN_SCRIPT]
    if args.modo == "sim":
        cmd.append("--sim")
    elif args.modo == "manual":
        cmd.append("--test")
    return subprocess.run(cmd, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
