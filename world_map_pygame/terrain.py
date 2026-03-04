"""
world_map_pygame/terrain.py
Geração procedural do heightmap e textura cartográfica — FANTASY HAND-DRAWN.

[PHASE 18] Reescrita total:
  - Biome system baseado em elevation + moisture noise
  - Paleta fantasy: verdes vivos, deserto dourado, gelo azul, montanhas cinza
  - Ícones procedurais: montanhas triangulares, florestas, neve, cactos
  - Linhas de costa com wave shading
  - Rios mais visíveis com borda
  - Heightmap e land_mask exportados para placement de estruturas
"""
import math, random
import numpy as np
from numpy.fft import fft2, ifft2
from scipy.ndimage import binary_dilation, binary_erosion

from .config import (
    TEX_W, TEX_H, SEA_LEVEL, TERRAIN_SEED,
    C_RIVER, C_BORDER,
)


# ─── PERLIN fBm (sem dependências externas) ───────────────────────────────────
def _make_perm(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p   = rng.permutation(256).astype(np.int32)
    return np.concatenate([p, p, p])

def _grad2(h, x, y):
    h = h & 7
    u = np.where(h < 4, x, y)
    v = np.where(h < 4, y, x)
    return np.where(h & 1, -u, u) + np.where(h & 2, -v, v)

def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def _perlin2d(px, py, perm):
    xi = px.astype(np.int32) & 255
    yi = py.astype(np.int32) & 255
    xf = px - px.astype(np.int32)
    yf = py - py.astype(np.int32)
    u, v = _fade(xf), _fade(yf)
    aa = perm[perm[xi    ] + yi    ]
    ab = perm[perm[xi    ] + yi + 1]
    ba = perm[perm[xi + 1] + yi    ]
    bb = perm[perm[xi + 1] + yi + 1]
    lerp = lambda a, b, t: a + t * (b - a)
    x1 = lerp(_grad2(aa, xf,     yf    ), _grad2(ba, xf - 1, yf    ), u)
    x2 = lerp(_grad2(ab, xf,     yf - 1), _grad2(bb, xf - 1, yf - 1), u)
    return lerp(x1, x2, v)

def fbm(px, py, perm, octaves=8, lac=2.0, gain=0.48):
    val = np.zeros_like(px)
    amp, freq, tot = 1.0, 1.0, 0.0
    for _ in range(octaves):
        val += _perlin2d(px * freq, py * freq, perm) * amp
        tot += amp; amp *= gain; freq *= lac
    return val / tot


# ─── BIOME PALETTE ─────────────────────────────────────────────────────────────
# (r, g, b) for each biome, hand-drawn fantasy style

# Ocean depth bands (deep → shallow)
OCEAN_DEEP    = np.array([ 28,  45,  85], dtype=np.float32)
OCEAN_MID     = np.array([ 42,  68, 115], dtype=np.float32)
OCEAN_SHALLOW = np.array([ 58,  95, 140], dtype=np.float32)
OCEAN_COAST   = np.array([ 85, 128, 168], dtype=np.float32)

# Shore / beach
C_BEACH       = np.array([215, 200, 160], dtype=np.float32)

# Biome base colors (elevation × moisture matrix)
BIOME_COLORS = {
    "deep_water":    np.array([ 28,  45,  85], dtype=np.float32),
    "shallow_water": np.array([ 58,  95, 140], dtype=np.float32),
    "beach":         np.array([215, 200, 160], dtype=np.float32),
    "grassland":     np.array([115, 165,  65], dtype=np.float32),
    "forest":        np.array([ 55, 120,  45], dtype=np.float32),
    "dense_forest":  np.array([ 35,  85,  30], dtype=np.float32),
    "savanna":       np.array([175, 165,  85], dtype=np.float32),
    "desert":        np.array([210, 185, 110], dtype=np.float32),
    "tundra":        np.array([170, 185, 175], dtype=np.float32),
    "snow":          np.array([225, 235, 240], dtype=np.float32),
    "mountain":      np.array([135, 125, 110], dtype=np.float32),
    "high_mountain": np.array([165, 160, 155], dtype=np.float32),
    "peak":          np.array([210, 215, 220], dtype=np.float32),
}


def generate_heightmap(seed: int = TERRAIN_SEED) -> np.ndarray:
    """
    Retorna heightmap normalizado (TEX_H, TEX_W) float32 em [0,1].
    Continente estilo fantasia com costas orgânicas.
    """
    H, W = TEX_H, TEX_W
    perm = _make_perm(seed)

    xs = np.linspace(0, 5.0, W, dtype=np.float32)
    ys = np.linspace(0, 3.5, H, dtype=np.float32)
    px, py = np.meshgrid(xs, ys)

    # Base terrain noise
    h = fbm(px, py, perm, octaves=8)

    # Secondary detail noise
    perm2 = _make_perm(seed + 100)
    detail = fbm(px * 2.0, py * 2.0, perm2, octaves=4, gain=0.55) * 0.15
    h += detail

    # Island mask — forma irregular de continente
    cx = np.linspace(-1, 1, W, dtype=np.float32)
    cy = np.linspace(-1, 1, H, dtype=np.float32)
    gx, gy = np.meshgrid(cx, cy)

    # Multiple circle centers for a more interesting continent shape
    perm3 = _make_perm(seed + 200)
    shape_noise = fbm(px * 0.5, py * 0.5, perm3, octaves=3, gain=0.5) * 0.3

    dist = np.sqrt((gx + 0.02)**2 * 1.1 + (gy - 0.03)**2 * 0.95)
    island = np.clip(1.0 - dist * 1.15 + shape_noise, 0, 1) ** 0.65

    h = h * 0.45 + island * 0.65

    # FFT smoothing (gentler for more detail)
    H_f = fft2(h)
    fy  = np.fft.fftfreq(H).reshape(-1, 1).astype(np.float32)
    fx  = np.fft.fftfreq(W).reshape(1, -1).astype(np.float32)
    filt = np.exp(-0.5 * (np.sqrt(fx**2 + fy**2) / 0.18)**2)
    h = np.real(ifft2(H_f * filt)).astype(np.float32)

    h = (h - h.min()) / (h.max() - h.min() + 1e-9)
    return h


def generate_moisture(seed: int = TERRAIN_SEED + 50) -> np.ndarray:
    """
    Generate moisture map (0-1). Controls biome selection.
    High moisture → forest/tundra. Low → desert/savanna.
    """
    H, W = TEX_H, TEX_W
    perm = _make_perm(seed)
    xs = np.linspace(0, 3.5, W, dtype=np.float32)
    ys = np.linspace(0, 2.5, H, dtype=np.float32)
    px, py = np.meshgrid(xs, ys)
    m = fbm(px, py, perm, octaves=5, gain=0.5)
    m = (m - m.min()) / (m.max() - m.min() + 1e-9)
    return m


def get_biome(elev: float, moist: float) -> str:
    """Classify biome from elevation and moisture."""
    if elev < SEA_LEVEL * 0.5:
        return "deep_water"
    if elev < SEA_LEVEL:
        return "shallow_water"
    if elev < SEA_LEVEL + 0.03:
        return "beach"

    # Normalize land elevation (0=coast, 1=peak)
    land_e = (elev - SEA_LEVEL) / (1.0 - SEA_LEVEL + 1e-9)

    if land_e > 0.82:
        return "peak"
    if land_e > 0.65:
        return "high_mountain"
    if land_e > 0.50:
        return "mountain"
    if land_e > 0.40:
        if moist > 0.55:
            return "tundra"
        return "mountain"
    if land_e > 0.25:
        if moist > 0.6:
            return "dense_forest"
        if moist > 0.35:
            return "forest"
        return "savanna"
    # Low elevation
    if moist > 0.55:
        return "forest"
    if moist > 0.35:
        return "grassland"
    if moist > 0.20:
        return "savanna"
    return "desert"


# ─── RIOS ─────────────────────────────────────────────────────────────────────
def trace_rivers(h: np.ndarray, land_mask: np.ndarray,
                 n_seeds: int = 70, seed: int = 99) -> np.ndarray:
    H, W  = h.shape
    mask  = np.zeros((H, W), dtype=bool)
    rng   = random.Random(seed)
    dirs  = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

    for _ in range(n_seeds):
        sy = rng.randint(H // 6, 5 * H // 6)
        sx = rng.randint(W // 6, 5 * W // 6)
        if h[sy, sx] < SEA_LEVEL + 0.10:
            continue

        py_, px_ = sy, sx
        length   = 0

        for _step in range(600):
            mask[py_, px_] = True
            best_val  = h[py_, px_]
            best_d    = None
            for dy, dx in dirs:
                ny, nx = py_ + dy, px_ + dx
                if 0 <= ny < H and 0 <= nx < W:
                    v = h[ny, nx] + rng.uniform(-0.002, 0.002)
                    if v < best_val:
                        best_val = v; best_d = (dy, dx)
            if best_d is None:
                break
            py_ += best_d[0]; px_ += best_d[1]
            length += 1
            if h[py_, px_] < SEA_LEVEL:
                break

        if length < 12:
            mask[max(0, sy-2):sy+3, max(0, sx-2):sx+3] = False

    # Dilate rivers slightly for visibility
    mask = binary_dilation(mask, iterations=1) & land_mask
    return mask


# ─── PROCEDURAL DECORATIONS ──────────────────────────────────────────────────

def _draw_mountains(img: np.ndarray, h: np.ndarray, land_mask: np.ndarray,
                    seed: int = 42):
    """Draw small triangular mountain icons at high elevations."""
    H, W = h.shape
    rng = random.Random(seed)

    # Find mountain pixels
    mtn_mask = land_mask & (h > SEA_LEVEL + (1.0 - SEA_LEVEL) * 0.45)

    # Sample sparse positions
    ys, xs = np.where(mtn_mask)
    if len(ys) == 0:
        return

    # Sparse grid sampling
    step = max(16, min(32, W // 80))
    positions = []
    for y in range(step, H - step, step):
        for x in range(step, W - step, step):
            if mtn_mask[y, x]:
                jx = rng.randint(-3, 3)
                jy = rng.randint(-3, 3)
                py_ = max(4, min(H - 5, y + jy))
                px_ = max(4, min(W - 5, x + jx))
                if mtn_mask[py_, px_]:
                    elev_n = (h[py_, px_] - SEA_LEVEL) / (1.0 - SEA_LEVEL + 1e-9)
                    positions.append((px_, py_, elev_n))

    for px_, py_, en in positions:
        # Mountain size based on elevation
        mh = max(3, min(9, int(en * 10)))
        mw = max(4, int(mh * 1.4))
        half = mw // 2

        # Colors
        if en > 0.75:
            # Snow-capped peak
            peak_col = np.array([220, 225, 230], dtype=np.float32)
            body_col = np.array([140, 130, 120], dtype=np.float32)
            shade_col = np.array([105, 95, 85], dtype=np.float32)
        elif en > 0.55:
            peak_col = np.array([180, 175, 165], dtype=np.float32)
            body_col = np.array([125, 115, 100], dtype=np.float32)
            shade_col = np.array([95, 85, 75], dtype=np.float32)
        else:
            peak_col = np.array([155, 150, 140], dtype=np.float32)
            body_col = np.array([110, 105, 90], dtype=np.float32)
            shade_col = np.array([85, 80, 70], dtype=np.float32)

        # Draw triangle (left half = light, right half = shadow)
        for row in range(mh):
            frac = row / max(1, mh - 1)
            w_at_row = int(half * frac)
            cy_ = py_ - mh + row + 1

            if cy_ < 0 or cy_ >= H:
                continue

            for dx in range(-w_at_row, w_at_row + 1):
                cx_ = px_ + dx
                if 0 <= cx_ < W:
                    if row < 2:
                        img[cy_, cx_] = peak_col
                    elif dx < 0:
                        img[cy_, cx_] = body_col
                    else:
                        img[cy_, cx_] = shade_col


def _draw_trees(img: np.ndarray, h: np.ndarray, moisture: np.ndarray,
                land_mask: np.ndarray, seed: int = 55):
    """Draw small tree dots/clusters in forested areas."""
    H, W = h.shape
    rng = random.Random(seed)

    elev_norm = np.where(land_mask,
                         (h - SEA_LEVEL) / (1.0 - SEA_LEVEL + 1e-9),
                         0.0)
    forest_mask = land_mask & (moisture > 0.40) & (elev_norm < 0.50) & (elev_norm > 0.02)

    step = max(8, min(18, W // 120))
    for y in range(step, H - step, step):
        for x in range(step, W - step, step):
            if not forest_mask[y, x]:
                continue
            if rng.random() > 0.7:
                continue

            jx = rng.randint(-2, 2)
            jy = rng.randint(-2, 2)
            ty = max(2, min(H - 3, y + jy))
            tx = max(2, min(W - 3, x + jx))

            m = moisture[ty, tx]
            if m > 0.6:
                # Dense forest — darker green dots
                col_top = np.array([35 + rng.randint(-8, 8),
                                    85 + rng.randint(-12, 12),
                                    28], dtype=np.float32)
                col_trunk = np.array([80, 60, 35], dtype=np.float32)
            else:
                # Lighter forest
                col_top = np.array([60 + rng.randint(-8, 8),
                                    125 + rng.randint(-12, 12),
                                    40], dtype=np.float32)
                col_trunk = np.array([90, 70, 40], dtype=np.float32)

            # Tree: 2px trunk + 3px canopy
            if ty >= 2 and tx >= 1 and tx < W - 1:
                img[ty, tx] = col_trunk
                img[ty - 1, tx] = col_top
                img[ty - 1, tx - 1] = col_top * 0.85
                img[ty - 1, tx + 1] = col_top * 0.85
                if ty >= 3:
                    img[ty - 2, tx] = col_top * 0.9


def _draw_snow_patches(img: np.ndarray, h: np.ndarray, land_mask: np.ndarray,
                        seed: int = 77):
    """Add white snow speckle to high elevation and tundra."""
    H, W = h.shape
    rng = np.random.default_rng(seed)

    elev_norm = np.where(land_mask,
                         (h - SEA_LEVEL) / (1.0 - SEA_LEVEL + 1e-9),
                         0.0)
    snow_chance = np.clip((elev_norm - 0.60) * 3.0, 0, 1)
    noise = rng.uniform(0, 1, (H, W)).astype(np.float32)
    snow_mask = land_mask & (noise < snow_chance * 0.15)

    snow_col = np.array([230, 238, 242], dtype=np.float32)
    img[snow_mask] = snow_col


# ─── TEXTURA BASE ─────────────────────────────────────────────────────────────
def build_base_texture(h: np.ndarray, border_mask: np.ndarray,
                       moisture: np.ndarray = None) -> np.ndarray:
    """
    Constrói o array (H, W, 3) uint8 do mapa — estilo fantasy hand-drawn.
    Inclui biomes, decorações procedurais, montanhas e florestas.
    
    Se moisture não for fornecido, gera automaticamente.
    """
    H, W = h.shape
    img  = np.zeros((H, W, 3), dtype=np.float32)

    if moisture is None:
        moisture = generate_moisture()

    land_mask  = h >= SEA_LEVEL
    ocean_mask = ~land_mask

    # ── Ocean gradient (depth-based) ─────────────────────────────────────
    ocean_depth = np.where(ocean_mask, h / SEA_LEVEL, 1.0)

    # Deep ocean
    deep = ocean_mask & (ocean_depth < 0.4)
    img[deep] = OCEAN_DEEP

    # Mid ocean
    mid = ocean_mask & (ocean_depth >= 0.4) & (ocean_depth < 0.7)
    t_mid = (ocean_depth[mid] - 0.4) / 0.3
    img[mid] = (OCEAN_DEEP * (1 - t_mid[:, np.newaxis]) +
                OCEAN_MID * t_mid[:, np.newaxis])

    # Shallow
    shallow = ocean_mask & (ocean_depth >= 0.7) & (ocean_depth < 0.9)
    t_sh = (ocean_depth[shallow] - 0.7) / 0.2
    img[shallow] = (OCEAN_MID * (1 - t_sh[:, np.newaxis]) +
                    OCEAN_SHALLOW * t_sh[:, np.newaxis])

    # Coast water
    coast_w = ocean_mask & (ocean_depth >= 0.9)
    t_cw = np.clip((ocean_depth[coast_w] - 0.9) / 0.1, 0, 1)
    img[coast_w] = (OCEAN_SHALLOW * (1 - t_cw[:, np.newaxis]) +
                    OCEAN_COAST * t_cw[:, np.newaxis])

    # ── Shore / beach (thin land strip near coast) ───────────────────────
    shore = binary_dilation(ocean_mask, iterations=4) & land_mask
    beach_mask = shore & (h < SEA_LEVEL + 0.04)
    img[beach_mask] = C_BEACH

    # ── Land biomes ──────────────────────────────────────────────────────
    elev_norm = np.where(land_mask & ~beach_mask,
                         (h - SEA_LEVEL) / (1.0 - SEA_LEVEL + 1e-9),
                         -1.0)

    # Grassland
    gm = (elev_norm >= 0) & (elev_norm < 0.25) & (moisture >= 0.20) & (moisture < 0.55) & ~beach_mask
    img[gm] = BIOME_COLORS["grassland"]

    # Forest
    fm = (elev_norm >= 0) & (elev_norm < 0.35) & (moisture >= 0.40) & ~beach_mask
    dense_fm = fm & (moisture >= 0.60)
    light_fm = fm & (moisture < 0.60)
    img[dense_fm] = BIOME_COLORS["dense_forest"]
    img[light_fm] = BIOME_COLORS["forest"]

    # Savanna
    sm = (elev_norm >= 0) & (elev_norm < 0.30) & (moisture >= 0.15) & (moisture < 0.40) & ~beach_mask
    img[sm] = BIOME_COLORS["savanna"]

    # Desert
    dm = (elev_norm >= 0) & (elev_norm < 0.30) & (moisture < 0.20) & ~beach_mask
    img[dm] = BIOME_COLORS["desert"]

    # Tundra
    tm = (elev_norm > 0.35) & (elev_norm < 0.55) & (moisture >= 0.45) & ~beach_mask
    img[tm] = BIOME_COLORS["tundra"]

    # Mountain
    mm = (elev_norm >= 0.45) & (elev_norm < 0.65) & ~beach_mask
    img[mm] = BIOME_COLORS["mountain"]

    # High mountain
    hm = (elev_norm >= 0.65) & (elev_norm < 0.82) & ~beach_mask
    img[hm] = BIOME_COLORS["high_mountain"]

    # Peak
    pm = (elev_norm >= 0.82) & ~beach_mask
    img[pm] = BIOME_COLORS["peak"]

    # Fill any remaining uncolored land with grassland
    remaining = land_mask & ~beach_mask & (img.sum(axis=2) < 1.0)
    img[remaining] = BIOME_COLORS["grassland"]

    # ── Elevation shading (subtle) ───────────────────────────────────────
    # Add slight darkening/brightening based on slope
    land_only = land_mask & ~beach_mask
    el_factor = np.where(land_only, 0.85 + elev_norm * 0.25, 1.0)
    img[land_only] = np.clip(
        img[land_only] * el_factor[land_only, np.newaxis], 0, 255)

    # ── Texture grain (hand-drawn feel) ──────────────────────────────────
    rng2 = np.random.default_rng(7)
    noise = rng2.uniform(-1, 1, (H, W)).astype(np.float32)

    # Grain on land (stronger)
    grain_land = noise * 6.0
    img[land_mask] = np.clip(
        img[land_mask] + grain_land[land_mask, np.newaxis], 0, 255)

    # Slight grain on ocean
    grain_ocean = noise * 2.5
    img[ocean_mask] = np.clip(
        img[ocean_mask] + grain_ocean[ocean_mask, np.newaxis], 0, 255)

    # ── Decorations ──────────────────────────────────────────────────────
    _draw_mountains(img, h, land_mask)
    _draw_trees(img, h, moisture, land_mask)
    _draw_snow_patches(img, h, land_mask)

    img_u8 = np.clip(img, 0, 255).astype(np.uint8)

    # ── Rivers (blue with darker border for visibility) ──────────────────
    rivers = trace_rivers(h, land_mask)
    river_border = binary_dilation(rivers, iterations=1) & land_mask & ~rivers
    img_u8[river_border] = np.array([55, 85, 120], dtype=np.uint8)
    img_u8[rivers] = np.array([70, 115, 160], dtype=np.uint8)

    # ── Coastline highlight (wave line) ──────────────────────────────────
    coast_line = binary_dilation(land_mask, iterations=1) & ocean_mask
    img_u8[coast_line] = np.clip(
        img_u8[coast_line].astype(np.int16) + 25, 0, 255).astype(np.uint8)

    # Zone borders removed — ownership overlay handles them at runtime

    return img_u8
