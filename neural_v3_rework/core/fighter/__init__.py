"""
NEURAL FIGHTS — core/fighter/  [D03/D04 Sprint 8]
==================================================
Pacote do Lutador — resultado da divisão de entities.py (3078 L → 5 arquivos).

Estrutura:
    entity.py       — Lutador: __init__ + update() central           (~260 L)
    stats.py        — StatsMixin: vida/mana, skills, channeling       (~120 L)
    physics_mixin.py— PhysicsMixin: física, movimento, trail         (~220 L)
    combat_mixin.py — CombatMixin: dano, status, buffs, morte        (~430 L)
    weapons_mixin.py— WeaponsMixin: ataques, skills, projéteis       (~560 L)

Critério de sucesso (plano D03):
    from core.entities import Lutador   ← continua funcionando (shim)
    from core.fighter import Lutador    ← importação direta
    Nenhum componente ultrapassa 600 L  ← verificado

Retrocompatibilidade:
    StatusSnapshot continua importável de core.entities e core.fighter.
"""

from .entity import Lutador
from .combat_mixin import StatusSnapshot

__all__ = ["Lutador", "StatusSnapshot"]
