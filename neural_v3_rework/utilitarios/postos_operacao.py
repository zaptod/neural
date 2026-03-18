from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SAIDAS_DIR = ROOT / "saidas"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_posto_dirs() -> dict[str, Path]:
    dirs = {
        "root": SAIDAS_DIR,
        "headless": SAIDAS_DIR / "headless",
        "headless_logs": SAIDAS_DIR / "headless" / "logs",
        "headless_reports": SAIDAS_DIR / "headless" / "relatorios",
        "simulacao": SAIDAS_DIR / "simulacao",
        "simulacao_sessions": SAIDAS_DIR / "simulacao" / "sessoes",
        "pipeline": SAIDAS_DIR / "pipeline",
        "pipeline_output": SAIDAS_DIR / "pipeline" / "output",
        "pipeline_frames": SAIDAS_DIR / "pipeline" / "frames",
        "pipeline_portraits": SAIDAS_DIR / "pipeline" / "portraits",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def create_session_dir(posto: str) -> Path:
    dirs = ensure_posto_dirs()
    if posto == "headless":
        base = dirs["headless_logs"]
    elif posto == "simulacao":
        base = dirs["simulacao_sessions"]
    else:
        base = dirs["pipeline_output"]
    session_dir = base / _timestamp()
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def write_session_manifest(session_dir: Path, data: dict[str, Any]) -> Path:
    manifest = session_dir / "sessao.json"
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        **data,
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def write_session_report(session_dir: Path, data: dict[str, Any]) -> Path:
    report = session_dir / "relatorio_execucao.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        **data,
    }
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_command_captured(
    args: list[str],
    *,
    cwd: str | Path,
    session_dir: Path,
    env: dict[str, str] | None = None,
) -> tuple[int, Path, float]:
    log_path = session_dir / "exec.log"
    start = time.perf_counter()
    with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    duration = round(time.perf_counter() - start, 3)
    return completed.returncode, log_path, duration


def build_pipeline_env(env: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(os.environ if env is None else env)
    dirs = ensure_posto_dirs()
    merged["NF_PIPELINE_OUTPUT_DIR"] = str(dirs["pipeline_output"])
    merged["NF_PIPELINE_FRAMES_DIR"] = str(dirs["pipeline_frames"])
    merged["NF_PIPELINE_PORTRAITS_DIR"] = str(dirs["pipeline_portraits"])
    return merged
