"""
NEURAL FIGHTS - Tema Visual UI
Cores e estilos compartilhados entre todas as telas.
"""

from tkinter import ttk

# ============================================================================
# CORES DO TEMA PRINCIPAL
# ============================================================================
COR_BG = "#09111f"
COR_BG_SECUNDARIO = "#12233f"
COR_HEADER = "#173b69"
COR_ACCENT = "#ff6b57"
COR_SUCCESS = "#35d6ff"
COR_TEXTO = "#f5f7fb"
COR_TEXTO_DIM = "#9fb1c9"
COR_WARNING = "#f5c451"
COR_DANGER = "#ff5f5f"
COR_BG_CARD = "#162b4b"
COR_BG_CARD_SOFT = "#1b3155"
COR_BORDA = "#284564"
COR_TEXTO_SUB = "#c6d8f4"

# ============================================================================
# CORES DAS RARIDADES
# ============================================================================
CORES_RARIDADE = {
    "Comum": "#B4B4B4",
    "Incomum": "#64C864",
    "Raro": "#508CFF",
    "Épico": "#B450DC",
    "Lendário": "#FFB432",
    "Mítico": "#FF6464"
}

# ============================================================================
# CORES DAS CLASSES POR CATEGORIA
# ============================================================================
CORES_CLASSE = {
    # Físicos
    "Guerreiro (Força Bruta)": "#cd7f32",
    "Berserker (Fúria)": "#ff4444",
    "Gladiador (Combate)": "#b8860b",
    "Cavaleiro (Defesa)": "#4682b4",
    # Ágeis
    "Assassino (Crítico)": "#800080",
    "Ladino (Evasão)": "#505050",
    "Ninja (Velocidade)": "#2f2f2f",
    "Duelista (Precisão)": "#ffd700",
    # Mágicos
    "Mago (Arcano)": "#6495ed",
    "Piromante (Fogo)": "#ff6600",
    "Criomante (Gelo)": "#87ceeb",
    "Necromante (Trevas)": "#4b0082",
    # Híbridos
    "Paladino (Sagrado)": "#ffcc00",
    "Druida (Natureza)": "#228b22",
    "Feiticeiro (Caos)": "#9932cc",
    "Monge (Chi)": "#f5f5dc",
}

# Cores específicas para a tela de luta
COR_P1 = "#4aa8ff"
COR_P2 = "#ff6d8a"

# ============================================================================
# CATEGORIAS DE CLASSES
# ============================================================================
CATEGORIAS_CLASSE = {
    "⚔️ Físicos": ["Guerreiro (Força Bruta)", "Berserker (Fúria)", "Gladiador (Combate)", "Cavaleiro (Defesa)"],
    "🗡️ Ágeis": ["Assassino (Crítico)", "Ladino (Evasão)", "Ninja (Velocidade)", "Duelista (Precisão)"],
    "✨ Mágicos": ["Mago (Arcano)", "Piromante (Fogo)", "Criomante (Gelo)", "Necromante (Trevas)"],
    "⚡ Híbridos": ["Paladino (Sagrado)", "Druida (Natureza)", "Feiticeiro (Caos)", "Monge (Chi)"],
}

def apply_ttk_theme(master=None):
    """Aplica um tema ttk coeso para a interface."""
    style = ttk.Style(master)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        ".",
        background=COR_BG_SECUNDARIO,
        foreground=COR_TEXTO,
        fieldbackground=COR_BG,
        bordercolor=COR_BORDA,
        lightcolor=COR_BG_SECUNDARIO,
        darkcolor=COR_BG_SECUNDARIO,
        troughcolor=COR_BG,
    )
    style.configure(
        "TCombobox",
        fieldbackground=COR_BG,
        background=COR_BG_SECUNDARIO,
        foreground=COR_TEXTO,
        arrowcolor=COR_ACCENT,
        bordercolor=COR_BORDA,
        lightcolor=COR_BG_SECUNDARIO,
        darkcolor=COR_BG_SECUNDARIO,
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COR_BG), ("focus", COR_BG)],
        selectbackground=[("readonly", COR_BG_CARD)],
        selectforeground=[("readonly", COR_TEXTO)],
        background=[("readonly", COR_BG_SECUNDARIO)],
        foreground=[("disabled", COR_TEXTO_DIM), ("readonly", COR_TEXTO)],
    )
    style.configure(
        "Treeview",
        background=COR_BG,
        fieldbackground=COR_BG,
        foreground=COR_TEXTO,
        bordercolor=COR_BORDA,
        rowheight=28,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", COR_ACCENT)],
        foreground=[("selected", "#07131f")],
    )
    style.configure(
        "Treeview.Heading",
        background=COR_BG_SECUNDARIO,
        foreground=COR_TEXTO,
        relief="flat",
        padding=8,
        font=("Segoe UI", 9, "bold"),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", COR_BG_CARD)],
        foreground=[("active", COR_TEXTO)],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=COR_BG_CARD,
        troughcolor=COR_BG,
        bordercolor=COR_BORDA,
        arrowcolor=COR_TEXTO,
        relief="flat",
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=COR_BG_CARD,
        troughcolor=COR_BG,
        bordercolor=COR_BORDA,
        arrowcolor=COR_TEXTO,
        relief="flat",
    )

__all__ = [
    'COR_BG', 'COR_BG_SECUNDARIO', 'COR_HEADER', 'COR_ACCENT',
    'COR_SUCCESS', 'COR_TEXTO', 'COR_TEXTO_DIM', 'COR_WARNING', 'COR_DANGER',
    'COR_BG_CARD', 'COR_BG_CARD_SOFT', 'COR_BORDA', 'COR_TEXTO_SUB',
    'CORES_RARIDADE', 'CORES_CLASSE', 'COR_P1', 'COR_P2', 'CATEGORIAS_CLASSE', 'apply_ttk_theme',
]
