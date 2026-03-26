"""
Neural Fights - launcher principal.
Execute este arquivo a partir da pasta raiz `neural/`.
"""

from __future__ import annotations

import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(ROOT, "neural_v3_rework", "run.py")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    completed = subprocess.run([sys.executable, SCRIPT, *args], cwd=ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
