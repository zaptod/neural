"""
world_map_pygame/config.py
Constantes visuais, dimensões e paletas.
SCREEN_W/SCREEN_H são detectados automaticamente a partir da tela real.
"""
import os

# ─── CAMINHOS ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_data_dir() -> str:
    candidates = [
        os.path.join(_HERE, "world_map_pygame", "data"),
        os.path.join(_HERE, "world_map_module", "data"),
        os.path.join(_HERE, "..", "world_map_module", "data"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return candidates[0]

# ─── JANELA — detecta tamanho real da tela ───────────────────────────────────
try:
    import pygame
    pygame.display.init()
    _di = pygame.display.Info()
    # usa no máximo 1440×900 mas nunca maior que a tela física
    # subtrai 60px vertical para não ficar atrás da barra de tarefas do Windows
    SCREEN_W = min(1440, _di.current_w)
    SCREEN_H = min(900,  _di.current_h - 60)
    del _di
except Exception:
    SCREEN_W = 1280
    SCREEN_H = 720

FPS = 60

# ─── PAINEL ESQUERDO ─────────────────────────────────────────────────────────
PANEL_W_MIN = 290
PANEL_W_MAX = 400

# ─── ESPAÇO DO MUNDO (world-units) ───────────────────────────────────────────
WORLD_W = 2000
WORLD_H = 1400

# ─── TEXTURA PRÉ-RENDERIZADA ─────────────────────────────────────────────────
TEX_W = 1024
TEX_H = 717

# ─── GERAÇÃO DO HEIGHTMAP ────────────────────────────────────────────────────
TERRAIN_SEED   = 12345
SEA_LEVEL      = 0.42
TERRITORY_SEED = 77
VORONOI_WARP   = 0.38

# ─── PALETA CARTOGRÁFICA ─────────────────────────────────────────────────────
import numpy as np

OCEAN_PALETTE = [
    np.array([ 85, 115, 170], dtype=np.float32),
    np.array([103, 133, 186], dtype=np.float32),
    np.array([122, 153, 202], dtype=np.float32),
    np.array([142, 173, 218], dtype=np.float32),
    np.array([163, 194, 230], dtype=np.float32),
]
C_SHORE   = np.array([188, 216, 240], dtype=np.float32)
C_LAND    = np.array([232, 244, 253], dtype=np.float32)
C_LAND_HI = np.array([217, 236, 251], dtype=np.float32)
C_RIVER   = (148, 190, 225)
C_BORDER  = (170, 200, 226)

# ─── PALETA UI ───────────────────────────────────────────────────────────────
UI_BG     = (6,   12,  28)
UI_BG2    = (10,  18,  42)
UI_LINE   = (22,  44,  90)
UI_PANEL  = (8,   16,  38)
CYAN      = (0,  217, 255)
CRIMSON   = (233,  69,  96)
GOLD      = (255, 210,  55)
TXT       = (215, 232, 248)
TXT_DIM   = (100, 128, 158)
TXT_MUTED = (55,  78, 110)

# ─── TINT POR NATUREZA ───────────────────────────────────────────────────────
NATURE_TINT = {
    "balanced": (  0, 210, 255, 38),
    "fire":     (230,  80,  10, 55),
    "ice":      (150, 220, 255, 38),
    "darkness": ( 90,  15, 190, 62),
    "nature":   ( 30, 170,  55, 48),
    "chaos":    (190,  20, 150, 50),
    "void":     ( 15,  55, 190, 62),
    "greed":    (220, 175,  10, 50),
    "fear":     (100,   8, 170, 58),
    "arcane":   ( 90, 125, 230, 45),
    "blood":    (210,  10,  10, 58),
    "ancient":  (170, 130,  25, 60),
    "unclaimed":( 80,  90, 115, 12),
}

NATURE_COLOR = {
    "balanced": (  0, 217, 255),
    "fire":     (255,  90,  20),
    "ice":      (160, 225, 255),
    "darkness": (130,  40, 220),
    "nature":   ( 60, 200,  80),
    "chaos":    (220,  40, 180),
    "void":     ( 40,  80, 220),
    "greed":    (230, 185,  20),
    "fear":     (160,  30, 220),
    "arcane":   (120, 150, 240),
    "blood":    (230,  20,  20),
    "ancient":  (200, 155,  40),
    "unclaimed":(110, 120, 145),
}

SEAL_COLOR = {
    "sleeping": (130,  40, 220),
    "stirring": GOLD,
    "awakened": CYAN,
    "broken":   CRIMSON,
}
