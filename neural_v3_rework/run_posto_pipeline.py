#!/usr/bin/env python3
"""Atalho para o posto de pipeline de vídeos."""

from __future__ import annotations

import os
import subprocess
import sys

from utilitarios.postos_operacao import build_pipeline_env, create_session_dir, ensure_posto_dirs, write_session_manifest


ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(ROOT, "pipeline_video", "run_pipeline.py")


if __name__ == "__main__":
    ensure_posto_dirs()
    session_dir = create_session_dir("pipeline")
    write_session_manifest(
        session_dir,
        {"posto": "pipeline", "args": sys.argv[1:], "saida_logica": "saidas/pipeline"},
    )
    raise SystemExit(
        subprocess.run(
            [sys.executable, SCRIPT, *sys.argv[1:]],
            cwd=ROOT,
            env=build_pipeline_env(),
        ).returncode
    )
