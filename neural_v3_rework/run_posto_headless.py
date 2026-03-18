#!/usr/bin/env python3
"""Atalho para o posto headless de coleta rápida."""

from __future__ import annotations

import os
import sys

from utilitarios.postos_operacao import (
    create_session_dir,
    ensure_posto_dirs,
    run_command_captured,
    write_session_manifest,
    write_session_report,
)


ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(ROOT, "utilitarios", "test_headless_battle.py")


if __name__ == "__main__":
    ensure_posto_dirs()
    session_dir = create_session_dir("headless")
    use_tatico = "--tatico" in sys.argv[1:]
    forwarded = [arg for arg in sys.argv[1:] if arg != "--tatico"]
    script = (
        os.path.join(ROOT, "ferramentas", "harness_tatico.py")
        if use_tatico else
        SCRIPT
    )
    resumo_path = session_dir / ("harness_tatico_resumo.json" if use_tatico else "headless_resumo.json")
    write_session_manifest(
        session_dir,
        {
            "posto": "headless",
            "args": sys.argv[1:],
            "tipo_execucao": "harness_tatico" if use_tatico else "suite_headless",
            "saida_logica": "saidas/headless",
        },
    )
    returncode, log_path, duration = run_command_captured(
        [sys.executable, script, *forwarded, "--json-out", str(resumo_path)],
        cwd=ROOT,
        session_dir=session_dir,
    )
    write_session_report(
        session_dir,
        {
            "posto": "headless",
            "args": sys.argv[1:],
            "tipo_execucao": "harness_tatico" if use_tatico else "suite_headless",
            "returncode": returncode,
            "duracao_seg": duration,
            "log_path": os.path.relpath(log_path, ROOT),
            "resumo_headless_path": os.path.relpath(resumo_path, ROOT),
            "status": "ok" if returncode == 0 else "erro",
        },
    )
    print(f"[posto headless] sessao: {session_dir}")
    print(f"[posto headless] log: {log_path}")
    raise SystemExit(returncode)
