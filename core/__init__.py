"""
NEURAL FIGHTS - Módulo Core
Funcionalidades essenciais do jogo.
"""

from core.physics import (
    normalizar_angulo,
    distancia_pontos,
    colisao_linha_circulo,
    intersect_line_circle,
    colisao_linha_linha
)
from core.skills import SKILL_DB, get_skill_data
from core.entities import Lutador
from core.game_feel import (
    GameFeelManager,
    HitStopManager,
    SuperArmorSystem,
    ChannelingSystem,
    CameraFeel,
    ChannelState,
    SuperArmorState,
)

__all__ = [
    'normalizar_angulo',
    'distancia_pontos',
    'colisao_linha_circulo',
    'intersect_line_circle',
    'colisao_linha_linha',
    'SKILL_DB',
    'get_skill_data',
    'Lutador',
    # Game Feel v8.0
    'GameFeelManager',
    'HitStopManager',
    'SuperArmorSystem',
    'ChannelingSystem',
    'CameraFeel',
    'ChannelState',
    'SuperArmorState',
]
