"""
NEURAL FIGHTS - Módulo Effects (Wrapper de Compatibilidade)
Re-exporta todas as classes de efeitos do módulo effects/.
"""

# Importa do novo local
from effects import (
    # Partículas
    Particula,
    HitSpark,
    Shockwave,
    EncantamentoEffect,
    CORES_ENCANTAMENTOS,
    # Impacto
    ImpactFlash,
    MagicClash,
    BlockEffect,
    DashTrail,
    # Câmera
    Câmera,
    # Visual
    FloatingText,
    Decal,
)

__all__ = [
    'Particula',
    'HitSpark',
    'Shockwave',
    'EncantamentoEffect',
    'CORES_ENCANTAMENTOS',
    'ImpactFlash',
    'MagicClash',
    'BlockEffect',
    'DashTrail',
    'Câmera',
    'FloatingText',
    'Decal',
]
