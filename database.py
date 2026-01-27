"""
NEURAL FIGHTS - Database (Wrapper de Compatibilidade)
Re-exporta do módulo data/.
"""
from data import (
    carregar_json,
    salvar_json,
    carregar_armas,
    carregar_personagens,
    salvar_lista_armas,
    salvar_lista_chars,
    ARQUIVO_CHARS,
    ARQUIVO_ARMAS,
)

__all__ = [
    'carregar_json',
    'salvar_json',
    'carregar_armas',
    'carregar_personagens',
    'salvar_lista_armas',
    'salvar_lista_chars',
    'ARQUIVO_CHARS',
    'ARQUIVO_ARMAS',
]
