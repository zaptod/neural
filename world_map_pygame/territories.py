"""
world_map_pygame/territories.py
Divisão orgânica de territórios via Voronoi com distorção de ruído.

Em vez de medir distância euclidiana pura ao centroide, aplicamos
dois campos de ruído (warp_x, warp_y) que deslocam o ponto de consulta
antes de calcular a distância — produzindo fronteiras que parecem
rios, cordilheiras e serras naturais.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional

from .config import (
    TEX_W, TEX_H, WORLD_W, WORLD_H,
    TERRITORY_SEED, VORONOI_WARP,
)
from .data_loader import Zone
from .terrain import fbm, _make_perm


def build_territory_maps(zones: Dict[str, "Zone"]) -> Tuple[np.ndarray, list]:
    """
    Calcula:
      zone_idx  (TEX_H, TEX_W) int32  — qual zona cada pixel pertence
      zone_list                list    — Zone na ordem dos índices

    Algoritmo:
      1. Gera dois campos de ruído (warp_x, warp_y) com fBm de baixa freq.
      2. Para cada centroide de zona, calcula distância de todos os pixels
         ao centroide DEPOIS de warpar as coords do pixel pelo ruído.
      3. Pixel ganha o índice da zona mais próxima.
    """
    H, W = TEX_H, TEX_W
    zone_list = list(zones.values())
    n = len(zone_list)

    # ── Coordenadas de textura dos centroides ─────────────────────────────
    cx = np.array([z.centroid[0] / WORLD_W * W for z in zone_list], dtype=np.float32)
    cy = np.array([z.centroid[1] / WORLD_H * H for z in zone_list], dtype=np.float32)

    # ── Campos de distorção (warp) ────────────────────────────────────────
    perm_x = _make_perm(TERRITORY_SEED)
    perm_y = _make_perm(TERRITORY_SEED + 1)

    # Grade de coordenadas normalizadas (0-4, 0-4) para o ruído
    xs = np.linspace(0, 4.0, W, dtype=np.float32)
    ys = np.linspace(0, 4.0, H, dtype=np.float32)
    gx, gy = np.meshgrid(xs, ys)

    # fBm de baixa frequência → campos de deslocamento
    amp = VORONOI_WARP * min(W, H)
    warp_x = fbm(gx, gy,             perm_x, octaves=4, lac=2.0, gain=0.5) * amp
    warp_y = fbm(gx + 5.3, gy + 9.1, perm_y, octaves=4, lac=2.0, gain=0.5) * amp

    # Coords de pixel warped
    px_w = gx / 4.0 * W + warp_x   # (H, W)
    py_w = gy / 4.0 * H + warp_y   # (H, W)

    # ── Voronoi: distância mínima ─────────────────────────────────────────
    best_dist = np.full((H, W), np.inf, dtype=np.float32)
    best_idx  = np.zeros((H, W),       dtype=np.int32)

    for i in range(n):
        d = (px_w - cx[i])**2 + (py_w - cy[i])**2
        mask = d < best_dist
        best_dist[mask] = d[mask]
        best_idx[mask]  = i

    return best_idx, zone_list


def extract_border_mask(zone_idx: np.ndarray) -> np.ndarray:
    """
    Retorna máscara booleana onde pixels de zonas diferentes se tocam.
    Espessura 1 pixel — o efeito de borda tracejada é aplicado depois.
    """
    H, W = zone_idx.shape
    border = np.zeros((H, W), dtype=bool)
    border[:, :-1] |= zone_idx[:, :-1] != zone_idx[:, 1:]
    border[:, 1:]  |= zone_idx[:, :-1] != zone_idx[:, 1:]
    border[:-1, :] |= zone_idx[:-1, :] != zone_idx[1:, :]
    border[1:,  :] |= zone_idx[:-1, :] != zone_idx[1:, :]
    return border


def zone_at_pixel(zone_idx: np.ndarray, zone_list: list,
                  tx: int, ty: int) -> Optional["Zone"]:
    """Retorna a Zone que ocupa o pixel (tx, ty) da textura."""
    tx = int(max(0, min(TEX_W - 1, tx)))
    ty = int(max(0, min(TEX_H - 1, ty)))
    idx = int(zone_idx[ty, tx])
    if 0 <= idx < len(zone_list):
        return zone_list[idx]
    return None


def world_to_tex(wx: float, wy: float) -> Tuple[int, int]:
    """Converte world-units → coordenadas de textura."""
    return (
        int(max(0, min(TEX_W - 1, wx / WORLD_W * TEX_W))),
        int(max(0, min(TEX_H - 1, wy / WORLD_H * TEX_H))),
    )
