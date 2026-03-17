"""
NEURAL FIGHTS â€” nucleo/entities.py  [D03/D04 Sprint 8 â€” shim]
============================================================
âš ï¸  Este arquivo Ã© apenas um shim de retrocompatibilidade.
    O cÃ³digo real foi dividido em nucleo/lutador/:

        nucleo/lutador/entity.py        â€” Lutador (__init__ + update)
        nucleo/lutador/stats.py         â€” StatsMixin
        nucleo/lutador/physics_mixin.py â€” PhysicsMixin
        nucleo/lutador/combat_mixin.py  â€” CombatMixin + StatusSnapshot
        nucleo/lutador/weapons_mixin.py â€” WeaponsMixin

Qualquer cÃ³digo que fazia:
    from nucleo.entities import Lutador
    from nucleo.entities import StatusSnapshot
continua funcionando sem nenhuma alteraÃ§Ã£o.

Para cÃ³digo novo, prefira:
    from nucleo.lutador import Lutador
"""

from nucleo.lutador.entity import Lutador           # noqa: F401
from nucleo.lutador.combat_mixin import StatusSnapshot  # noqa: F401

__all__ = ["Lutador", "StatusSnapshot"]

# ---- ARQUIVO ORIGINAL REMOVIDO INTENCIONALMENTE ----
# O conteÃºdo anterior (3078 linhas) foi redistribuÃ­do nos mixins acima.
# O backup prÃ©-sprint estÃ¡ em nucleo/entities_original_sprint8_backup.py
# -------------------------------------------------------
_SHIM = True

