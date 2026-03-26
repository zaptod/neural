"""
World Map — Freeform Influence System  (v6.0 Optimised)
Each god's strongholds radiate influence; no hard borders.
Uses sparse computation: only computes within stronghold radius (130× faster for big maps).
"""
import numpy as np
try:
    from .config import (
        MAP_W, MAP_H,
        INFLUENCE_DEFAULT_RADIUS, INFLUENCE_MIN_THRESHOLD,
        INFLUENCE_WATER_FACTOR,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from config import (
        MAP_W, MAP_H,
        INFLUENCE_DEFAULT_RADIUS, INFLUENCE_MIN_THRESHOLD,
        INFLUENCE_WATER_FACTOR,
    )


class InfluenceMap:
    """Per-god influence layers + dominant-territory computation."""

    def __init__(self, god_ids, land_mask):
        self.god_ids   = list(god_ids)
        self.god_index = {gid: i for i, gid in enumerate(self.god_ids)}
        self.land_mask = land_mask
        self.num_gods  = len(god_ids)

        # Per-god influence: (num_gods, MAP_H, MAP_W)
        self.layers = np.zeros((self.num_gods, MAP_H, MAP_W), dtype=np.float32)

        # Computed dominance
        self.dominant_god      = np.full((MAP_H, MAP_W), -1, dtype=np.int8)
        self.dominant_strength = np.zeros((MAP_H, MAP_W), dtype=np.float32)

        self.strongholds = []
        self._version    = 0

    # ── public ─────────────────────────────────────────────────────────────
    def set_strongholds(self, strongholds):
        self.strongholds = list(strongholds)
        self._recalculate()

    def add_stronghold(self, sh):
        self.strongholds.append(sh)
        self._recalculate()

    def get_dominant_at(self, x, y):
        """Return (god_id | None, strength) at tile (x, y)."""
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            idx = int(self.dominant_god[y, x])
            if idx >= 0:
                return self.god_ids[idx], float(self.dominant_strength[y, x])
        return None, 0.0

    def get_god_territory_count(self, god_id):
        idx = self.god_index.get(god_id)
        if idx is None:
            return 0
        return int(np.sum(self.dominant_god == idx))

    # ── internal (SPARSE — only compute within stronghold radius) ──────────
    def _recalculate(self):
        self.layers.fill(0)

        for sh in self.strongholds:
            god_id = sh.get('god_id', '')
            if god_id not in self.god_index:
                continue
            idx      = self.god_index[god_id]
            sx, sy   = sh['x'], sh['y']
            strength = sh.get('strength', 1.0)
            radius   = sh.get('radius', INFLUENCE_DEFAULT_RADIUS)

            # Only compute within bounding box of radius
            y0 = max(0, sy - radius)
            y1 = min(MAP_H, sy + radius + 1)
            x0 = max(0, sx - radius)
            x1 = min(MAP_W, sx + radius + 1)

            yy, xx = np.mgrid[y0:y1, x0:x1]
            dist = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2).astype(np.float32)
            inf  = strength * np.clip(1.0 - dist / radius, 0, 1)
            self.layers[idx, y0:y1, x0:x1] += inf

        # Dominance
        max_inf = np.max(self.layers, axis=0)
        argmax  = np.argmax(self.layers, axis=0)

        self.dominant_god = np.where(
            max_inf >= INFLUENCE_MIN_THRESHOLD, argmax, -1
        ).astype(np.int8)

        # Strength (reduced on water)
        self.dominant_strength = np.where(
            self.land_mask, max_inf, max_inf * INFLUENCE_WATER_FACTOR
        )

        self._version += 1
