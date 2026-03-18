"""Regrava armas.json usando o schema v2 e o balanceamento atual."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modelos import Arma

ARMAS_PATH = ROOT / "dados" / "armas.json"


def main() -> None:
    armas_raw = json.loads(ARMAS_PATH.read_text(encoding="utf-8"))
    armas_norm = []
    for payload in armas_raw:
        arma = Arma.from_dict(payload)
        armas_norm.append(arma.to_dict())

    ARMAS_PATH.write_text(
        json.dumps(armas_norm, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    print(f"armas_normalizadas={len(armas_norm)}")


if __name__ == "__main__":
    main()
