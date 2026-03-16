"""
NEURAL FIGHTS — Data Module
============================
Exports both the new AppState (recommended) and the legacy
function API so existing views continue working unchanged.

Recommended (new):
    from data.app_state import AppState
    state = AppState.get()

Legacy (still works):
    from data import carregar_armas, salvar_lista_armas, ...
"""

# ── New central store ─────────────────────────────────────────────────────────
from data.app_state import AppState

# ── Legacy compatibility shim ─────────────────────────────────────────────────
# These functions now delegate to AppState instead of hitting the disk directly.
# Old views continue to work without any changes.

def carregar_armas():
    """Legacy: return current weapons list from AppState."""
    return AppState.get().weapons

def carregar_personagens():
    """Legacy: return current characters list from AppState."""
    return AppState.get().characters

def salvar_lista_armas(lista):
    """Legacy: replace weapons list via AppState (triggers save + events)."""
    AppState.get().set_weapons(lista)

def salvar_lista_chars(lista):
    """Legacy: replace characters list via AppState (triggers save + events)."""
    AppState.get().set_characters(lista)

def carregar_arma_por_nome(nome):
    """Legacy: find a weapon by name."""
    return AppState.get().get_weapon(nome)

def carregar_json(arquivo):
    """Legacy: raw JSON read (still hits disk — use sparingly)."""
    import json, os
    if not os.path.exists(arquivo):
        return []
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def salvar_json(arquivo, dados):
    """Legacy: raw JSON write (bypasses AppState events — use sparingly)."""
    import json
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# Keep the old module reference for code that does `from data import database`
from data import database

# File path constants (unchanged)
from data.app_state import FILE_CHARS  as ARQUIVO_CHARS
from data.app_state import FILE_WEAPONS as ARQUIVO_ARMAS

__all__ = [
    # New
    "AppState",
    # Legacy
    "database",
    "carregar_json",
    "salvar_json",
    "carregar_armas",
    "carregar_personagens",
    "salvar_lista_armas",
    "salvar_lista_chars",
    "carregar_arma_por_nome",
    "ARQUIVO_CHARS",
    "ARQUIVO_ARMAS",
]
