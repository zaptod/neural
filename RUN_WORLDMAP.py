"""
Aethermoor - World Map launcher.
Runs the pixel-art world map (pygame).
"""

from __future__ import annotations

import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    completed = subprocess.run(
        [sys.executable, "-m", "world_map_pygame.main", *args],
        cwd=ROOT,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
