"""
world_map_pygame/config.py
Constantes visuais, dimensões e paletas.
SCREEN_W/SCREEN_H são detectados automaticamente a partir da tela real.

[FASE 1] Mudanças:
  - Paleta sépia/pergaminho substituindo o azul-frio cartográfico
  - TEX_W/H aumentados de 1024×717 → 2048×1434 (melhora qualidade no zoom)
  - UI_SCALE calculado em runtime baseado em SCREEN_H (resolve textos pequenos)
  - MAP_Y_OFFSET removido — câmera recebe map_y dinâmico da UI
  - Novas constantes de layout: FILTER_BAR_H, BOTTOM_PANEL_H
  - GOLD promovido para cor de destaque primária (era CYAN)
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

# ─── JANELA ───────────────────────────────────────────────────────────────────
try:
    import pygame
    pygame.display.init()
    _di = pygame.display.Info()
    SCREEN_W = min(1440, _di.current_w)
    SCREEN_H = min(900,  _di.current_h - 60)
    del _di
except Exception:
    SCREEN_W = 1280
    SCREEN_H = 720

FPS = 60

# ─── ESCALA DE UI ─────────────────────────────────────────────────────────────
UI_SCALE: float = max(0.7, min(2.0, SCREEN_H / 900.0))

def scaled(size: int) -> int:
    return max(8, int(size * UI_SCALE))

# ─── NOVO LAYOUT ──────────────────────────────────────────────────────────────
FILTER_BAR_H   = scaled(36)
BOTTOM_PANEL_H = scaled(180)

# Mantido por compatibilidade (painel lateral removido)
PANEL_W_MIN = 0
PANEL_W_MAX = 0

# ─── ESPAÇO DO MUNDO ──────────────────────────────────────────────────────────
WORLD_W = 2000
WORLD_H = 1400

# ─── TEXTURA (2048×1434 resolve pixelado no zoom alto) ───────────────────────
TEX_W = 2048
TEX_H = 1434

# ─── GERAÇÃO DO HEIGHTMAP ────────────────────────────────────────────────────
TERRAIN_SEED   = 12345
SEA_LEVEL      = 0.42
TERRITORY_SEED = 77
VORONOI_WARP   = 0.38

# ─── PALETA CARTOGRÁFICA — PERGAMINHO ENVELHECIDO ────────────────────────────
import numpy as np

OCEAN_PALETTE = [
    np.array([ 48,  62,  92], dtype=np.float32),
    np.array([ 58,  74, 108], dtype=np.float32),
    np.array([ 68,  88, 120], dtype=np.float32),
    np.array([ 80, 100, 135], dtype=np.float32),
    np.array([ 96, 118, 152], dtype=np.float32),
]
C_SHORE   = np.array([128, 148, 172], dtype=np.float32)
C_LAND    = np.array([210, 195, 162], dtype=np.float32)
C_LAND_HI = np.array([185, 168, 135], dtype=np.float32)
C_RIVER   = (110, 130, 155)
C_BORDER  = (155, 138, 108)

# ─── PALETA UI — DOURADO MEDIEVAL ────────────────────────────────────────────
UI_BG     = ( 18,  14,  10)
UI_BG2    = ( 28,  22,  16)
UI_LINE   = ( 65,  52,  35)
UI_PANEL  = ( 22,  18,  12)
GOLD      = (210, 175,  80)
GOLD_DIM  = (155, 128,  55)
CRIMSON   = (180,  40,  40)
CYAN      = ( 80, 160, 200)
TXT       = (235, 225, 200)
TXT_DIM   = (155, 140, 115)
TXT_MUTED = ( 95,  85,  68)

# ─── TINTS POR NATUREZA ───────────────────────────────────────────────────────
NATURE_TINT = {
    "balanced": (  0, 190, 230,  32),
    "fire":     (210,  65,  10,  50),
    "ice":      (130, 200, 240,  32),
    "darkness": ( 80,  10, 170,  58),
    "nature":   ( 25, 150,  45,  42),
    "chaos":    (170,  15, 130,  48),
    "void":     ( 10,  45, 170,  58),
    "greed":    (200, 155,  10,  48),
    "fear":     ( 90,   5, 155,  55),
    "arcane":   ( 80, 110, 210,  42),
    "blood":    (190,  10,  10,  55),
    "ancient":  (155, 115,  20,  58),
    "unclaimed":( 65,  72,  88,  10),
}

NATURE_COLOR = {
    "balanced": (  0, 200, 240),
    "fire":     (240,  80,  20),
    "ice":      (150, 215, 250),
    "darkness": (120,  35, 210),
    "nature":   ( 55, 185,  70),
    "chaos":    (210,  35, 170),
    "void":     ( 35,  70, 210),
    "greed":    (220, 178,  20),
    "fear":     (150,  25, 210),
    "arcane":   (110, 140, 230),
    "blood":    (220,  20,  20),
    "ancient":  (190, 145,  35),
    "unclaimed":(100, 110, 132),
}

SEAL_COLOR = {
    "sleeping": (120,  35, 210),
    "stirring": GOLD,
    "awakened": (  0, 200, 240),
    "broken":   CRIMSON,
}

# ─── LOD (Level-of-Detail) — ZOOM THRESHOLDS ─────────────────────────────────
# LOD 0: Strategic (zoomed out)  — region blobs, large names, no zone boundaries
# LOD 1: Regional               — zone boundaries, zone names, ownership colors
# LOD 2: Tactical               — structure icons, nature tinting, badges, roads
# LOD 3: Detail                 — pixel-art buildings, landmarks, vegetation
# LOD 4: Close-up               — sub-district markers, detailed buildings, POIs
LOD_THRESHOLDS = [0.35, 0.90, 2.0, 3.5]   # zoom >= threshold → next LOD

def get_lod(zoom: float) -> int:
    """Return LOD level (0–4) for given zoom."""
    lod = 0
    for t in LOD_THRESHOLDS:
        if zoom >= t:
            lod += 1
        else:
            break
    return lod

# ─── STRUCTURE TYPES ──────────────────────────────────────────────────────────
STRUCTURE_TYPES = {
    "fortress":  {"icon": "▲", "color": (180, 160, 130), "size_range": (10, 16)},
    "city":      {"icon": "■", "color": (200, 185, 155), "size_range": (8, 14)},
    "village":   {"icon": "◆", "color": (170, 155, 125), "size_range": (6, 10)},
    "ruins":     {"icon": "✕", "color": (140, 125, 100), "size_range": (8, 12)},
    "temple":    {"icon": "◎", "color": (190, 170, 220), "size_range": (10, 14)},
    "market":    {"icon": "▬", "color": (210, 190, 80),  "size_range": (8, 12)},
    "outpost":   {"icon": "△", "color": (160, 145, 115), "size_range": (6, 10)},
    "sacred":    {"icon": "❋", "color": (100, 180, 100), "size_range": (8, 12)},
    "port":      {"icon": "⚓", "color": (100, 140, 180), "size_range": (8, 12)},
    "mine":      {"icon": "⛏", "color": (150, 130, 100), "size_range": (6, 10)},
    "tower":     {"icon": "⌂", "color": (165, 150, 120), "size_range": (6, 10)},
}

# ─── NATURE VFX CONFIG ────────────────────────────────────────────────────────
NATURE_VFX = {
    "fire":     {"particles": "ember",    "overlay": "cracks",   "intensity": 0.7},
    "ice":      {"particles": "snow",     "overlay": "frost",    "intensity": 0.5},
    "darkness": {"particles": "shadow",   "overlay": "tendrils", "intensity": 0.8},
    "nature":   {"particles": "leaf",     "overlay": "vines",    "intensity": 0.6},
    "chaos":    {"particles": "glitch",   "overlay": "distort",  "intensity": 0.9},
    "void":     {"particles": "void",     "overlay": "warp",     "intensity": 0.7},
    "greed":    {"particles": "gold",     "overlay": "sparkle",  "intensity": 0.5},
    "fear":     {"particles": "fog",      "overlay": "eyes",     "intensity": 0.8},
    "balanced": {"particles": "glow",     "overlay": "aura",     "intensity": 0.3},
    "arcane":   {"particles": "sigil",    "overlay": "runes",    "intensity": 0.6},
    "blood":    {"particles": "drip",     "overlay": "veins",    "intensity": 0.7},
    "ancient":  {"particles": "dust",     "overlay": "glyphs",   "intensity": 0.5},
    "unclaimed":{"particles": None,       "overlay": None,       "intensity": 0.0},
}

# ─── LIVE SYNC ────────────────────────────────────────────────────────────────
SYNC_POLL_INTERVAL = 3.0   # seconds between JSON checks
SYNC_TRANSITION_SPEED = 2.0  # seconds for ownership transition animation

# ─── STRUCTURE PALETTES PER NATURE ────────────────────────────────────────────
NATURE_BUILDING_PALETTE = {
    "balanced": [(185, 170, 140), (200, 185, 155), (165, 150, 120), (140, 125, 95)],
    "fire":     [(180,  80,  30), (210, 100,  20), (150,  60,  15), (120,  40,  10)],
    "ice":      [(160, 200, 230), (180, 215, 240), (140, 185, 215), (120, 165, 195)],
    "darkness": [(100,  50, 120), (120,  60, 140), ( 80,  40, 100), ( 60,  30,  80)],
    "nature":   [( 80, 140,  60), (100, 160,  80), ( 60, 120,  40), ( 50, 100,  35)],
    "chaos":    [(180,  50, 150), (200,  60, 170), (160,  40, 130), (140,  30, 110)],
    "void":     [( 50,  60, 140), ( 70,  80, 160), ( 40,  50, 120), ( 30,  40, 100)],
    "greed":    [(200, 170,  50), (220, 190,  60), (180, 150,  40), (160, 130,  30)],
    "fear":     [(120,  40, 160), (140,  50, 180), (100,  30, 140), ( 80,  20, 120)],
    "arcane":   [(100, 120, 200), (120, 140, 220), ( 80, 100, 180), ( 60,  80, 160)],
    "blood":    [(180,  30,  30), (200,  40,  40), (160,  20,  20), (140,  15,  15)],
    "ancient":  [(170, 140,  60), (190, 160,  80), (150, 120,  40), (130, 100,  30)],
    "unclaimed":[(150, 140, 125), (165, 155, 140), (135, 125, 110), (120, 110,  95)],
}
