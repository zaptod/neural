"""
NEURAL FIGHTS â€” nucleo/lutador/  [D03/D04 Sprint 8]
==================================================
Pacote do Lutador â€” resultado da divisÃ£o de entities.py (3078 L â†’ 5 arquivos).

Estrutura:
    entity.py       â€” Lutador: __init__ + update() central           (~260 L)
    stats.py        â€” StatsMixin: vida/mana, skills, channeling       (~120 L)
    physics_mixin.pyâ€” PhysicsMixin: fÃ­sica, movimento, trail         (~220 L)
    combat_mixin.py â€” CombatMixin: dano, status, buffs, morte        (~430 L)
    weapons_mixin.pyâ€” WeaponsMixin: ataques, skills, projÃ©teis       (~560 L)

CritÃ©rio de sucesso (plano D03):
    from nucleo.entities import Lutador   â† continua funcionando (shim)
    from nucleo.lutador import Lutador    â† importaÃ§Ã£o direta
    Nenhum componente ultrapassa 600 L  â† verificado

Retrocompatibilidade:
    StatusSnapshot continua importÃ¡vel de core.entities e core.fighter.
"""

from .entity import Lutador
from .combat_mixin import StatusSnapshot

__all__ = ["Lutador", "StatusSnapshot"]

