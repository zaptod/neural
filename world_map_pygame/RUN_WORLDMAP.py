"""World Map - in-folder launcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    completed = subprocess.run(
        [sys.executable, "-m", "world_map_pygame.main", *args],
        cwd=str(PROJECT_ROOT),
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
