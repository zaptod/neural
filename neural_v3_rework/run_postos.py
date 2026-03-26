#!/usr/bin/env python3
"""
Neural Fights - Hub operacional dos postos principais.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from utilitarios.postos_operacao import (
    build_pipeline_env,
    create_session_dir,
    ensure_posto_dirs,
    run_command_captured,
    write_session_manifest,
    write_session_report,
)

ROOT = os.path.dirname(os.path.abspath(__file__))


def _run_command(args: list[str], *, env: dict[str, str] | None = None) -> int:
    completed = subprocess.run(args, cwd=ROOT, env=env)
    return completed.returncode


def _headless_args(rest: list[str]) -> int:
    ensure_posto_dirs()
    session_dir = create_session_dir("headless")
    use_tatico = "--tatico" in rest
    forwarded = [arg for arg in rest if arg != "--tatico"]
    resumo_name = "harness_tatico_resumo.json" if use_tatico else "headless_resumo.json"
    resumo_path = session_dir / resumo_name
    write_session_manifest(
        session_dir,
        {
            "posto": "headless",
            "args": rest,
            "tipo_execucao": "harness_tatico" if use_tatico else "suite_headless",
            "saida_logica": "saidas/headless",
        },
    )
    script = (
        os.path.join(ROOT, "ferramentas", "harness_tatico.py")
        if use_tatico else
        os.path.join(ROOT, "utilitarios", "test_headless_battle.py")
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
            "args": rest,
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
    return returncode


def _simulacao_args(rest: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="run_postos.py simulacao")
    parser.add_argument(
        "--modo",
        choices=["launcher", "sim", "manual"],
        default="launcher",
        help="launcher abre a UI principal; sim abre a luta automatica; manual abre o modo de teste.",
    )
    args = parser.parse_args(rest)

    ensure_posto_dirs()
    session_dir = create_session_dir("simulacao")
    write_session_manifest(
        session_dir,
        {"posto": "simulacao", "modo": args.modo, "args": rest, "saida_logica": "saidas/simulacao"},
    )

    run_script = os.path.join(ROOT, "run.py")
    cmd = [sys.executable, run_script]
    if args.modo == "sim":
        cmd.append("--sim")
    elif args.modo == "manual":
        cmd.append("--test")
    return _run_command(cmd)


def _pipeline_args(rest: list[str]) -> int:
    ensure_posto_dirs()
    session_dir = create_session_dir("pipeline")
    write_session_manifest(
        session_dir,
        {"posto": "pipeline", "args": rest, "saida_logica": "saidas/pipeline"},
    )
    script = os.path.join(ROOT, "pipeline_video", "run_pipeline.py")
    return _run_command([sys.executable, script, *rest], env=build_pipeline_env())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Neural Fights - Hub dos postos operacionais")
    parser.add_argument(
        "posto",
        choices=["headless", "simulacao", "pipeline"],
        help="Escolha o posto a executar.",
    )
    args, rest = parser.parse_known_args(argv)

    if args.posto == "headless":
        return _headless_args(rest)
    if args.posto == "simulacao":
        return _simulacao_args(rest)
    if args.posto == "pipeline":
        return _pipeline_args(rest)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
