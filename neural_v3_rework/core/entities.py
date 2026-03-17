"""
NEURAL FIGHTS — core/entities.py  [D03/D04 Sprint 8 — shim]
============================================================
⚠️  Este arquivo é apenas um shim de retrocompatibilidade.
    O código real foi dividido em core/fighter/:

        core/fighter/entity.py        — Lutador (__init__ + update)
        core/fighter/stats.py         — StatsMixin
        core/fighter/physics_mixin.py — PhysicsMixin
        core/fighter/combat_mixin.py  — CombatMixin + StatusSnapshot
        core/fighter/weapons_mixin.py — WeaponsMixin

Qualquer código que fazia:
    from core.entities import Lutador
    from core.entities import StatusSnapshot
continua funcionando sem nenhuma alteração.

Para código novo, prefira:
    from core.fighter import Lutador
"""

from core.fighter.entity import Lutador           # noqa: F401
from core.fighter.combat_mixin import StatusSnapshot  # noqa: F401

__all__ = ["Lutador", "StatusSnapshot"]

# ---- ARQUIVO ORIGINAL REMOVIDO INTENCIONALMENTE ----
# O conteúdo anterior (3078 linhas) foi redistribuído nos mixins acima.
# O backup pré-sprint está em core/entities_original_sprint8_backup.py
# -------------------------------------------------------
_SHIM = True
