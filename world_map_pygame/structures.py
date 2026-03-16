"""
World Map — Pixel Art Structures
Small hand-drawn icons for strongholds, temples, ruins, etc.
"""
import pygame
from config import GOD_COLORS

# ── pixel-art templates ────────────────────────────────────────────────────────
# 0 = transparent, 1 = dark outline, 2 = main, 3 = highlight
_TEMPLATES = {
    'castle': [
        [0,1,0,1,0,1,0],
        [0,1,3,1,3,1,0],
        [0,1,2,2,2,1,0],
        [1,1,2,3,2,1,1],
        [1,2,2,2,2,2,1],
        [1,2,1,2,1,2,1],
        [1,1,1,1,1,1,1],
    ],
    'temple': [
        [0,0,0,3,0,0,0],
        [0,0,3,3,3,0,0],
        [0,1,2,2,2,1,0],
        [0,1,2,3,2,1,0],
        [0,1,2,2,2,1,0],
        [1,1,1,2,1,1,1],
        [1,1,1,1,1,1,1],
    ],
    'tower': [
        [0,1,1,1,0],
        [0,1,3,1,0],
        [0,1,2,1,0],
        [0,1,2,1,0],
        [1,1,1,1,1],
    ],
    'altar': [
        [0,0,3,0,0],
        [0,3,3,3,0],
        [1,2,2,2,1],
        [0,1,2,1,0],
        [0,1,1,1,0],
    ],
    'ruin': [
        [0,1,0,0,0],
        [1,2,0,1,0],
        [1,2,0,1,1],
        [1,2,1,2,1],
        [1,1,1,1,1],
    ],
    'village': [
        [0,0,1,0,0],
        [0,1,3,1,0],
        [0,1,2,1,0],
        [1,2,2,2,1],
        [1,1,1,1,1],
    ],
    'city': [
        [0,1,0,1,0,1,0],
        [0,1,3,1,3,1,0],
        [1,2,2,2,2,2,1],
        [1,2,3,2,3,2,1],
        [1,2,2,2,2,2,1],
        [1,2,1,1,1,2,1],
        [1,1,1,1,1,1,1],
    ],
    'farm': [
        [2,1,2,1,2],
        [1,2,1,2,1],
        [2,1,3,1,2],
        [1,2,1,2,1],
        [2,1,2,1,2],
    ],
    'mine': [
        [0,0,1,0,0],
        [0,1,1,1,0],
        [1,1,3,1,1],
        [0,1,2,1,0],
        [1,1,1,1,1],
    ],
    'port': [
        [0,0,3,0,0],
        [0,3,3,3,0],
        [1,2,2,2,1],
        [1,1,2,1,1],
        [0,1,1,1,0],
    ],
    'wall': [
        [1,1,1],
        [2,2,2],
        [1,1,1],
    ],
    'bridge': [
        [0,1,0,1,0],
        [1,2,2,2,1],
        [0,1,0,1,0],
    ],
    'workshop': [
        [0,1,1,1,0],
        [1,2,3,2,1],
        [1,3,2,3,1],
        [1,2,3,2,1],
        [1,1,1,1,1],
    ],
    'barracks': [
        [1,0,1,0,1],
        [1,2,2,2,1],
        [1,2,3,2,1],
        [1,2,2,2,1],
        [1,1,1,1,1],
    ],
    'graveyard': [
        [0,1,0,1,0],
        [1,1,0,1,1],
        [0,0,0,0,0],
        [0,1,0,1,0],
        [1,1,0,1,1],
    ],
    'citadel': [
        [0,1,0,1,0,1,0],
        [0,1,3,1,3,1,0],
        [0,1,2,2,2,1,0],
        [1,1,2,3,2,1,1],
        [1,2,2,2,2,2,1],
        [1,2,1,2,1,2,1],
        [1,1,1,1,1,1,1],
    ],
}


def _palette(god_color):
    r, g, b = god_color
    return {
        0: None,
        1: (max(0, r // 4), max(0, g // 4), max(0, b // 4)),
        2: (r, g, b),
        3: (min(255, r + 80), min(255, g + 80), min(255, b + 80)),
    }


class StructureRenderer:
    def __init__(self):
        self._cache = {}      # (type, god_id, scale) → Surface

    def render(self, screen, camera, strongholds):
        cell = camera.cell_size
        x0, y0, x1, y1 = camera.get_visible_rect()
        margin = 6

        for sh in strongholds:
            tx, ty = sh['x'], sh['y']
            if tx < x0 - margin or tx > x1 + margin:
                continue
            if ty < y0 - margin or ty > y1 + margin:
                continue

            sx, sy = camera.tile_to_screen(tx, ty)
            stype   = sh.get('type', 'castle')
            god_id  = sh.get('god_id', '')
            god_col = GOD_COLORS.get(god_id, (180, 180, 180))
            icon_sc = max(2, cell // 2)
            key     = (stype, god_id, icon_sc)

            if key not in self._cache:
                self._cache[key] = self._make(stype, god_col, icon_sc)

            icon = self._cache[key]
            ix = sx + cell // 2 - icon.get_width()  // 2
            iy = sy + cell // 2 - icon.get_height() // 2
            screen.blit(icon, (ix, iy))

    def clear_cache(self):
        self._cache.clear()

    # ── build icon surface ────────────────────────────────────────────────
    @staticmethod
    def _make(stype, god_color, scale):
        tmpl = _TEMPLATES.get(stype, _TEMPLATES['castle'])
        rows = len(tmpl)
        cols = len(tmpl[0]) if rows else 0
        pal  = _palette(god_color)

        surf = pygame.Surface((cols * scale, rows * scale), pygame.SRCALPHA)
        for py, row in enumerate(tmpl):
            for px, idx in enumerate(row):
                c = pal.get(idx)
                if c:
                    pygame.draw.rect(surf, c,
                                     (px * scale, py * scale, scale, scale))
        return surf
