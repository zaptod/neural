from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEURAL_ROOT = PROJECT_ROOT.parent


def _run(args: list[str], cwd: Path, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def test_run_py_help() -> None:
    completed = _run(["run.py", "--help"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "Neural Fights v3 rework launcher" in completed.stdout


def test_run_py_smoke() -> None:
    completed = _run(["run.py", "--smoke"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "bootstrap ok" in completed.stdout


def test_run_tournament_smoke() -> None:
    completed = _run(["run_tournament.py", "--smoke"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "bootstrap ok" in completed.stdout


def test_run_tournament_smoke_cp1252_safe() -> None:
    completed = _run(["run_tournament.py", "--smoke"], PROJECT_ROOT, PYTHONIOENCODING="cp1252")
    assert completed.returncode == 0
    assert "bootstrap ok" in completed.stdout


def test_run_postos_help() -> None:
    completed = _run(["run_postos.py", "--help"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "Hub dos postos operacionais" in completed.stdout


def test_run_posto_simulacao_help() -> None:
    completed = _run(["run_posto_simulacao.py", "--help"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "posto de simulacao completa" in completed.stdout


def test_run_posto_headless_help() -> None:
    completed = _run(["run_posto_headless.py", "--help"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "atalho para o posto headless" in completed.stdout


def test_run_posto_pipeline_help() -> None:
    completed = _run(["run_posto_pipeline.py", "--help"], PROJECT_ROOT)
    assert completed.returncode == 0
    assert "atalho para o posto de pipeline" in completed.stdout


def test_root_run_game_smoke() -> None:
    completed = _run(["RUN_GAME.py", "--smoke"], NEURAL_ROOT)
    assert completed.returncode == 0
    assert "bootstrap ok" in completed.stdout


def test_root_run_worldmap_smoke() -> None:
    completed = _run(["RUN_WORLDMAP.py", "--smoke"], NEURAL_ROOT)
    assert completed.returncode == 0
    assert "world_map_pygame.main" in completed.stdout


def test_world_map_module_smoke() -> None:
    completed = _run(["-m", "world_map_pygame.main", "--smoke"], NEURAL_ROOT)
    assert completed.returncode == 0
    assert "world_map_pygame.main" in completed.stdout
