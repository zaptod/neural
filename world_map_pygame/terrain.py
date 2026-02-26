"""
world_map_pygame/terrain.py
Geração procedural do heightmap via fBm Perlin (numpy puro)
e construção da textura cartográfica base.
"""
import math, random
import numpy as np
from numpy.fft import fft2, ifft2
from scipy.ndimage import binary_dilation

from .config import (
    TEX_W, TEX_H, SEA_LEVEL, TERRAIN_SEED,
    OCEAN_PALETTE, C_SHORE, C_LAND, C_LAND_HI, C_RIVER,
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


def generate_heightmap(seed: int = TERRAIN_SEED) -> np.ndarray:
    """
    Retorna heightmap normalizado (TEX_H, TEX_W) float32 ∈ [0,1].
    ~39% terra, ~61% oceano — proporcional à imagem de referência.
    """
    H, W = TEX_H, TEX_W
    perm = _make_perm(seed)

    xs = np.linspace(0, 5.0, W, dtype=np.float32)
    ys = np.linspace(0, 3.5, H, dtype=np.float32)
    px, py = np.meshgrid(xs, ys)

    h = fbm(px, py, perm, octaves=8)

    # Máscara elíptica → continente central orgânico
    cx = np.linspace(-1, 1, W, dtype=np.float32)
    cy = np.linspace(-1, 1, H, dtype=np.float32)
    gx, gy = np.meshgrid(cx, cy)
    dist   = np.sqrt((gx + 0.04)**2 * 1.05 + (gy - 0.05)**2 * 0.92)
    island = np.clip(1.0 - dist * 1.25, 0, 1) ** 0.7
    h = h * 0.5 + island * 0.6

    # Suavização por FFT (remove artefatos de alta frequência)
    H_f = fft2(h)
    fy  = np.fft.fftfreq(H).reshape(-1, 1).astype(np.float32)
    fx  = np.fft.fftfreq(W).reshape(1, -1).astype(np.float32)
    filt = np.exp(-0.5 * (np.sqrt(fx**2 + fy**2) / 0.15)**2)
    h = np.real(ifft2(H_f * filt)).astype(np.float32)

    h = (h - h.min()) / (h.max() - h.min() + 1e-9)
    return h


# ─── RIOS ─────────────────────────────────────────────────────────────────────
def trace_rivers(h: np.ndarray, land_mask: np.ndarray,
                 n_seeds: int = 70, seed: int = 99) -> np.ndarray:
    """
    Traça rios seguindo gradiente descendente a partir de pontos altos.
    Retorna máscara booleana (H, W).
    """
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
            # rio muito curto — apaga
            mask[max(0, sy-2):sy+3, max(0, sx-2):sx+3] = False

    return mask


# ─── TEXTURA BASE ─────────────────────────────────────────────────────────────
def build_base_texture(h: np.ndarray,
                       border_mask: np.ndarray) -> np.ndarray:
    """
    Constrói o array (H, W, 3) uint8 do mapa base (sem tints de zona).
    border_mask: máscara booleana das fronteiras de zona a desenhar.
    Retorna img_u8.
    """
    H, W = h.shape
    img  = np.zeros((H, W, 3), dtype=np.float32)

    land_mask  = h >= SEA_LEVEL
    ocean_mask = ~land_mask

    # ── Bandas de profundidade oceânica ──────────────────────────────────
    n = len(OCEAN_PALETTE)
    for band in range(n):
        lo = band / n * SEA_LEVEL
        hi = (band + 1) / n * SEA_LEVEL
        bm = ocean_mask & (h >= lo) & (h < hi)
        img[bm] = OCEAN_PALETTE[band]

    # ── Shore ─────────────────────────────────────────────────────────────
    shore = binary_dilation(land_mask, iterations=3) & ocean_mask
    img[shore] = C_SHORE

    # ── Terra com gradiente de elevação ───────────────────────────────────
    elev  = np.where(land_mask, (h - SEA_LEVEL) / (1 - SEA_LEVEL + 1e-9), 0.0)
    lc    = (C_LAND[np.newaxis, np.newaxis, :]   * (1 - elev[:, :, np.newaxis]) +
             C_LAND_HI[np.newaxis, np.newaxis, :] *      elev[:, :, np.newaxis])
    img[land_mask] = lc[land_mask]

    # ── Ruído de textura pontilhado ───────────────────────────────────────
    rng2  = np.random.default_rng(7)
    noise = rng2.uniform(0, 1, (H, W)).astype(np.float32)
    dots  = land_mask & (noise < 0.014)
    img[dots] = np.clip(img[dots] - 18, 0, 255)

    img_u8 = np.clip(img, 0, 255).astype(np.uint8)

    # ── Rios ──────────────────────────────────────────────────────────────
    rivers = trace_rivers(h, land_mask)
    img_u8[rivers & land_mask] = np.array(C_RIVER, dtype=np.uint8)

    # ── Fronteiras de zona (tracejadas) ───────────────────────────────────
    ys_b, xs_b = np.where(border_mask & land_mask)
    dash = (xs_b + ys_b) % 4 < 2
    img_u8[ys_b[dash], xs_b[dash]] = np.array([170, 200, 226], dtype=np.uint8)

    return img_u8
