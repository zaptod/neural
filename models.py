"""
NEURAL FIGHTS - Módulo Models (Wrapper de Compatibilidade)
Re-exporta todas as classes e constantes do módulo models/.
"""

# Importa do novo local
from models import (
    # Constantes
    RARIDADES, LISTA_RARIDADES,
    TIPOS_ARMA, LISTA_TIPOS_ARMA,
    ENCANTAMENTOS, LISTA_ENCANTAMENTOS, PASSIVAS_ARMA,
    LISTA_CLASSES, CLASSES_DATA,
    # Helpers
    get_raridade_data, get_tipo_arma_data, get_class_data,
    # Classes
    Arma, Personagem,
    # Funções
    gerar_passiva_arma,
    calcular_tamanho_arma,
    validar_arma_personagem,
    sugerir_tamanho_arma,
    get_escala_visual_arma,
)

__all__ = [
    # Constantes
    'RARIDADES', 'LISTA_RARIDADES',
    'TIPOS_ARMA', 'LISTA_TIPOS_ARMA',
    'ENCANTAMENTOS', 'LISTA_ENCANTAMENTOS', 'PASSIVAS_ARMA',
    'LISTA_CLASSES', 'CLASSES_DATA',
    # Helpers
    'get_raridade_data', 'get_tipo_arma_data', 'get_class_data',
    # Classes
    'Arma', 'Personagem',
    # Funções
    'gerar_passiva_arma',
    'calcular_tamanho_arma',
    'validar_arma_personagem',
    'sugerir_tamanho_arma',
    'get_escala_visual_arma',
]
