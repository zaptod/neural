from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.audit_project import DEFAULT_OUTPUT_DIR, PROJECT_ROOT, WORKSPACE_ROOT, iter_workspace_files
except ImportError:  # pragma: no cover - direct script fallback
    from audit_project import DEFAULT_OUTPUT_DIR, PROJECT_ROOT, WORKSPACE_ROOT, iter_workspace_files


NEURAL_ROOT = PROJECT_ROOT.parent


def _timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _run_command(args: list[str], cwd: Path, extra_env: dict[str, str] | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    if extra_env:
        env.update(extra_env)
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": args,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "status": "ok" if completed.returncode == 0 else "erro",
    }


def _syntax_report(workspace_root: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    checked = 0
    for path in iter_workspace_files(workspace_root):
        if path.suffix.lower() != ".py":
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8-sig", errors="strict")
            ast.parse(text, filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            issues.append({"path": str(path.relative_to(workspace_root)), "error": str(exc)})
    return {
        "name": "syntax_ast",
        "status": "ok" if not issues else "erro",
        "checked_files": checked,
        "issues": issues,
    }


def build_checklist(workspace_root: Path, skip_pytest: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(_syntax_report(workspace_root))
    checks.append(_run_command([sys.executable, "run.py", "--smoke"], PROJECT_ROOT))
    checks.append(_run_command([sys.executable, "run_tournament.py", "--smoke"], PROJECT_ROOT))
    checks.append(
        _run_command(
            [sys.executable, "run_tournament.py", "--smoke"],
            PROJECT_ROOT,
            extra_env={"PYTHONIOENCODING": "cp1252"},
        )
    )
    checks.append(_run_command([sys.executable, "run_postos.py", "--help"], PROJECT_ROOT))
    checks.append(_run_command([sys.executable, "run_posto_simulacao.py", "--help"], PROJECT_ROOT))
    checks.append(_run_command([sys.executable, "run_posto_headless.py", "--help"], PROJECT_ROOT))
    checks.append(_run_command([sys.executable, "run_posto_pipeline.py", "--help"], PROJECT_ROOT))
    checks.append(_run_command([sys.executable, "RUN_GAME.py", "--smoke"], NEURAL_ROOT))
    checks.append(_run_command([sys.executable, "RUN_WORLDMAP.py", "--smoke"], NEURAL_ROOT))
    checks.append(_run_command([sys.executable, "-m", "world_map_pygame.main", "--smoke"], NEURAL_ROOT))
    if not skip_pytest:
        checks.append(_run_command([sys.executable, "-m", "pytest", "-q"], PROJECT_ROOT))

    ok = sum(1 for item in checks if item["status"] == "ok")
    erro = sum(1 for item in checks if item["status"] != "ok")
    return {
        "generated_at": _timestamp(),
        "workspace_root": str(workspace_root),
        "project_root": str(PROJECT_ROOT),
        "summary": {
            "total_checks": len(checks),
            "ok": ok,
            "erro": erro,
        },
        "checks": checks,
    }


def write_outputs(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "audit_checklist.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Audit Checklist",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Checks: `{report['summary']['total_checks']}`",
        f"- OK: `{report['summary']['ok']}`",
        f"- Errors: `{report['summary']['erro']}`",
        "",
    ]
    for item in report["checks"]:
        command = " ".join(item.get("command", [])) if "command" in item else item["name"]
        lines.append(f"- `{item['status']}` `{command}`")
        if item.get("issues"):
            lines.append(f"  issues: {len(item['issues'])}")
    (output_dir / "audit_checklist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run executable audit checks for the project.")
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args(argv)

    report = build_checklist(args.workspace_root, skip_pytest=args.skip_pytest)
    write_outputs(report, args.output_dir)
    print(f"[audit] checklist written to {args.output_dir}")
    return 0 if report["summary"]["erro"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
