"""
=============================================================================
NEURAL FIGHTS - Sistema de IA v9.0 SPATIAL AWARENESS EDITION
=============================================================================
Módulo de Inteligência Artificial modularizado.
Sistema de comportamento humano realista com:
- Antecipação e leitura do oponente
- Desvios inteligentes com timing humano
- Baiting e fintas
- Janelas de oportunidade
- Momentum e pressão psicológica
- Combos e follow-ups
- Consciência espacial (paredes, obstáculos)
=============================================================================
"""

from ai.choreographer import CombatChoreographer
from ai.brain import AIBrain
from ai.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES
)

# LEGADO-01 (Sprint 4): EmotionSystem, SpatialAwarenessSystem e CombatTacticsSystem
# foram removidos dos exports públicos do pacote.
# Esses módulos (ai/emotions.py, ai/spatial.py, ai/combat_tactics.py) contêm lógica
# que foi replicada inline em AIBrain e nunca é instanciada externamente.
# Exportá-los dava a falsa impressão de que faziam parte do sistema ativo.
# A decisão arquitetural final (adoptar via composição ou remover os arquivos)
# será tomada na Sprint 5 — MEL-ARQ-01.

# Módulo v10.0 - Estratégia de Skills
try:
    from ai.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority, StrategicRole
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
    # Sistema de Estratégia de Skills
    'SkillStrategySystem',
    'CombatSituation',
    'SkillPriority',
    'StrategicRole',
]
