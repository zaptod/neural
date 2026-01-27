"""
=============================================================================
NEURAL FIGHTS - Sistema de IA v7.0 IMPACT EDITION
=============================================================================
Módulo de Inteligência Artificial modularizado.
"""

from ai.choreographer import CombatChoreographer
from ai.brain import AIBrain
from ai.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES
)

__all__ = [
    'CombatChoreographer',
    'AIBrain',
    'TODOS_TRACOS',
    'TRACOS_AGRESSIVIDADE',
    'TRACOS_DEFENSIVO',
    'TRACOS_MOBILIDADE',
    'TRACOS_SKILLS',
    'TRACOS_MENTAL',
    'TRACOS_ESPECIAIS',
    'ARQUETIPO_DATA',
    'ESTILOS_LUTA',
    'QUIRKS',
    'FILOSOFIAS',
    'HUMORES',
]
