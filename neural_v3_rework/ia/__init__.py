"""
=============================================================================
NEURAL FIGHTS - Sistema de IA v9.0 SPATIAL AWARENESS EDITION
=============================================================================
MÃ³dulo de InteligÃªncia Artificial modularizado.
Sistema de comportamento humano realista com:
- AntecipaÃ§Ã£o e leitura do oponente
- Desvios inteligentes com timing humano
- Baiting e fintas
- Janelas de oportunidade
- Momentum e pressÃ£o psicolÃ³gica
- Combos e follow-ups
- ConsciÃªncia espacial (paredes, obstÃ¡culos)
=============================================================================
"""

from ia.choreographer import CombatChoreographer
from ia.brain import AIBrain
from ia.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES
)

# LEGADO-01 (Sprint 4): EmotionSystem e SpatialAwarenessSystem
# foram removidos dos exports pÃºblicos do pacote.
# Esses mÃ³dulos (ia/emotions.py, ia/spatial.py) contÃªm lÃ³gica
# que foi replicada inline em AIBrain e nunca Ã© instanciada externamente.
# combat_tactics.py foi removido (MEL-ARQ-01 concluÃ­do).

# MÃ³dulo v10.0 - EstratÃ©gia de Skills
try:
    from ia.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority, StrategicRole
    SKILL_STRATEGY_AVAILABLE = True
except ImportError:
    SKILL_STRATEGY_AVAILABLE = False

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
    # Sistema de EstratÃ©gia de Skills
    'SkillStrategySystem',
    'CombatSituation',
    'SkillPriority',
    'StrategicRole',
]

