"""Migra o catalogo de armas para o schema v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modelos.weapons import Arma


ARQUIVO_ARMAS = ROOT / "dados" / "armas.json"


def migrar_catalogo(path: Path = ARQUIVO_ARMAS) -> int:
    bruto = json.loads(path.read_text(encoding="utf-8"))
    armas = [Arma.from_dict(item) for item in bruto]
    path.write_text(
        json.dumps([arma.to_dict() for arma in armas], ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return len(armas)


if __name__ == "__main__":
    total = migrar_catalogo()
    print(f"armas_migradas={total}")
