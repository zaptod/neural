"""
NEURAL FIGHTS - Módulo UI
Interfaces gráficas do usuário.
"""

from ui.theme import (
    COR_BG, COR_BG_SECUNDARIO, COR_HEADER, COR_ACCENT,
    COR_SUCCESS, COR_TEXTO, COR_TEXTO_DIM, COR_WARNING, COR_DANGER,
    CORES_RARIDADE, CORES_CLASSE, COR_P1, COR_P2, CATEGORIAS_CLASSE,
)
from ui.view_armas import TelaArmas
from ui.view_chars import TelaPersonagens
from ui.view_luta import TelaLuta

__all__ = [
    # Tema
    'COR_BG', 'COR_BG_SECUNDARIO', 'COR_HEADER', 'COR_ACCENT',
    'COR_SUCCESS', 'COR_TEXTO', 'COR_TEXTO_DIM', 'COR_WARNING', 'COR_DANGER',
    'CORES_RARIDADE', 'CORES_CLASSE', 'COR_P1', 'COR_P2', 'CATEGORIAS_CLASSE',
    # Telas
    'TelaArmas', 'TelaPersonagens', 'TelaLuta',
]
