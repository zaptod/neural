"""
NEURAL FIGHTS - MÃ³dulo Core
Funcionalidades essenciais do jogo.
"""

from nucleo.physics import (
    normalizar_angulo,
    distancia_pontos,
    colisao_linha_circulo,
    intersect_line_circle,
    colisao_linha_linha
)
from nucleo.skills import SKILL_DB, get_skill_data, get_skill_classification
from nucleo.entities import Lutador
from nucleo.game_feel import (
    GameFeelManager,
    HitStopManager,
    SuperArmorSystem,
    ChannelingSystem,
    CameraFeel,
    ChannelState,
    SuperArmorState,
)

# v10.0 - Combat e Hitbox movidos para core
from nucleo.combat import (
    ArmaProjetil, FlechaProjetil, OrbeMagico,
    Projetil, AreaEffect, Beam, Buff, DotEffect,
)
from nucleo.hitbox import (
    DEBUG_HITBOX, DEBUG_VISUAL,
    HitboxInfo, SistemaHitbox,
    sistema_hitbox, verificar_hit, get_debug_visual, atualizar_debug,
)

# v10.0 - Arena movida para core
from nucleo.arena import Arena

__all__ = [
    # Physics
    'normalizar_angulo',
    'distancia_pontos',
    'colisao_linha_circulo',
    'intersect_line_circle',
    'colisao_linha_linha',
    # Skills
    'SKILL_DB',
    'get_skill_data',
    'get_skill_classification',
    # Entities
    'Lutador',
    # Game Feel v8.0
    'GameFeelManager',
    'HitStopManager',
    'SuperArmorSystem',
    'ChannelingSystem',
    'CameraFeel',
    'ChannelState',
    'SuperArmorState',
    # Combat
    'ArmaProjetil', 'FlechaProjetil', 'OrbeMagico',
    'Projetil', 'AreaEffect', 'Beam', 'Buff', 'DotEffect',
    # Hitbox
    'DEBUG_HITBOX', 'DEBUG_VISUAL',
    'HitboxInfo', 'SistemaHitbox',
    'sistema_hitbox', 'verificar_hit', 'get_debug_visual', 'atualizar_debug',
    # Arena
    'Arena',
]

