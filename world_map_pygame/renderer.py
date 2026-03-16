"""
World Map — Chunk-Based Pixel Art Renderer  (v6.0 LIVING WORLD)
Terrain + influence overlay + material layer + minimap.
Uses a chunk system for performance: only re-renders tiles that changed.
Supports massive maps (1600×1000+) without lag.
"""
import pygame
import numpy as np
from config import (
    MAP_W, MAP_H, TOPBAR_H, SCR,
    BIOME_COLORS, GOD_COLORS,
    INFLUENCE_TINT_STRENGTH, INFLUENCE_WATER_FACTOR,
    MINIMAP_W, MINIMAP_H, MINIMAP_MARGIN,
    CHUNK_SIZE,
)
from tools import MATERIALS, MAT_NAMES, MAT_INDEX

# Pre-compute material colour LUT: (num_materials, 3)
_MAT_COLOR_LUT = np.zeros((len(MAT_NAMES), 3), dtype=np.uint8)
for _i, _n in enumerate(MAT_NAMES):
    c = MATERIALS.get(_n, {}).get('color')
    if c:
        _MAT_COLOR_LUT[_i] = c


# ═══════════════════════════════════════════════════════════════════════════════
# Chunk Cache — pre-renders 64×64 tile chunks, only rebuilds on change
# ═══════════════════════════════════════════════════════════════════════════════

class _ChunkCache:
    """Cache of pre-rendered chunk surfaces at 1px/tile."""

    def __init__(self, terrain_colors, color_noise, influence, material_layer):
        self.terrain_colors = terrain_colors
        self.color_noise    = color_noise
        self.influence      = influence
        self.material_layer = material_layer

        self.cols = (MAP_W + CHUNK_SIZE - 1) // CHUNK_SIZE
        self.rows = (MAP_H + CHUNK_SIZE - 1) // CHUNK_SIZE

        # Pre-rendered surfaces: (cx, cy) → pygame.Surface (CHUNK×CHUNK)
        self._surfaces = {}
        # Version tracking per chunk
        self._inf_ver = {}    # (cx,cy) → int
        self._mat_ver = {}    # (cx,cy) → int
        # Animation tick (forces fire chunks to flicker)
        self._anim_tick = 0

    def tick_animation(self):
        """Call each frame to advance fire/lava flicker."""
        self._anim_tick += 1

    def get(self, cx, cy):
        """Get chunk surface, rebuilding if stale."""
        key = (cx, cy)
        inf_ver = self.influence._version
        mat_ver = self.material_layer._version if self.material_layer else -1

        need_rebuild = (
            key not in self._surfaces
            or self._inf_ver.get(key, -1) != inf_ver
            or self._mat_ver.get(key, -1) != mat_ver
        )

        # Force rebuild for fire/lava animation every 6 frames
        if not need_rebuild and self._anim_tick % 6 == 0 and self.material_layer:
            x0 = cx * CHUNK_SIZE
            y0 = cy * CHUNK_SIZE
            x1 = min(x0 + CHUNK_SIZE, MAP_W)
            y1 = min(y0 + CHUNK_SIZE, MAP_H)
            mat_sl = self.material_layer.mat[y0:y1, x0:x1]
            fire_idx = MAT_INDEX.get('fire', 0)
            lava_idx = MAT_INDEX.get('lava', 0)
            hf_idx = MAT_INDEX.get('hellfire', 0)
            if fire_idx and np.any((mat_sl == fire_idx) | (mat_sl == lava_idx)):
                need_rebuild = True
            elif hf_idx and np.any(mat_sl == hf_idx):
                need_rebuild = True

        if need_rebuild:
            self._build(cx, cy)
            self._inf_ver[key] = inf_ver
            self._mat_ver[key] = mat_ver

        return self._surfaces[key]

    def invalidate_all(self):
        """Force full rebuild (e.g. biome reclassification)."""
        self._surfaces.clear()
        self._inf_ver.clear()
        self._mat_ver.clear()

    def invalidate_region(self, x0, y0, x1, y1):
        """Invalidate chunks overlapping pixel region."""
        cx0 = max(0, x0 // CHUNK_SIZE)
        cy0 = max(0, y0 // CHUNK_SIZE)
        cx1 = min(self.cols - 1, (x1 - 1) // CHUNK_SIZE)
        cy1 = min(self.rows - 1, (y1 - 1) // CHUNK_SIZE)
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                self._surfaces.pop((cx, cy), None)
                self._inf_ver.pop((cx, cy), None)
                self._mat_ver.pop((cx, cy), None)

    # ── internal build ─────────────────────────────────────────────────────
    def _build(self, cx, cy):
        x0 = cx * CHUNK_SIZE
        y0 = cy * CHUNK_SIZE
        x1 = min(x0 + CHUNK_SIZE, MAP_W)
        y1 = min(y0 + CHUNK_SIZE, MAP_H)
        cw = x1 - x0
        ch = y1 - y0

        # Base terrain + noise
        tc = self.terrain_colors[y0:y1, x0:x1].astype(np.int16)
        tc = tc + self.color_noise[y0:y1, x0:x1]

        # Influence tinting
        dom  = self.influence.dominant_god[y0:y1, x0:x1]
        land = self.influence.land_mask[y0:y1, x0:x1]

        for gi in range(self.influence.num_gods):
            god_id  = self.influence.god_ids[gi]
            god_col = np.array(GOD_COLORS.get(god_id, (128, 128, 128)), dtype=np.int16)
            is_dom  = (dom == gi)
            if not np.any(is_dom):
                continue
            inf_sl = self.influence.layers[gi, y0:y1, x0:x1]
            tint   = np.clip(inf_sl * INFLUENCE_TINT_STRENGTH, 0, INFLUENCE_TINT_STRENGTH)
            tint   = np.where(land, tint, tint * INFLUENCE_WATER_FACTOR)
            tint   = tint * is_dom
            t3     = tint[:, :, np.newaxis]
            tc     = np.where(t3 > 0,
                              tc * (1.0 - t3) + god_col * t3,
                              tc)

        # Material overlay
        if self.material_layer is not None:
            mat_slice = self.material_layer.mat[y0:y1, x0:x1]
            has_mat   = mat_slice > 0
            if np.any(has_mat):
                mat_colors = _MAT_COLOR_LUT[mat_slice]
                blend = 0.75
                tc = np.where(
                    has_mat[:, :, np.newaxis],
                    tc * (1.0 - blend) + mat_colors.astype(np.int16) * blend,
                    tc)

                # Fire/lava/hellfire flicker
                fire_idx = MAT_INDEX.get('fire', 0)
                lava_idx = MAT_INDEX.get('lava', 0)
                hf_idx   = MAT_INDEX.get('hellfire', 0)
                fire_mask = (mat_slice == fire_idx) | (mat_slice == lava_idx)
                if hf_idx:
                    fire_mask |= (mat_slice == hf_idx)
                if np.any(fire_mask):
                    flicker = np.random.randint(-20, 25,
                                                size=(ch, cw, 3)).astype(np.int16)
                    tc = np.where(fire_mask[:, :, np.newaxis], tc + flicker, tc)

        tc = np.clip(tc, 0, 255).astype(np.uint8)

        # numpy (H,W,3) → surfarray (W,H,3)
        surf = pygame.surfarray.make_surface(
            np.ascontiguousarray(tc.transpose(1, 0, 2)))
        self._surfaces[(cx, cy)] = surf


# ═══════════════════════════════════════════════════════════════════════════════
# Main Renderer
# ═══════════════════════════════════════════════════════════════════════════════

class Renderer:
    def __init__(self, screen, terrain_data, influence_map, material_layer=None):
        self.screen = screen
        self.heightmap, self.moisture, self.biome_map, self.biome_names = terrain_data
        self.influence = influence_map
        self.material_layer = material_layer

        # Pre-build base terrain colours: (MAP_H, MAP_W, 3) uint8
        self.terrain_colors = self._build_base_colors()

        # Per-tile colour noise for pixel-art texture
        rng = np.random.RandomState(999)
        self.color_noise = rng.randint(-6, 7, size=(MAP_H, MAP_W, 3)).astype(np.int16)

        # Chunk cache
        self.chunks = _ChunkCache(
            self.terrain_colors, self.color_noise,
            self.influence, self.material_layer)

        # Composition surface cache (avoid re-creating every frame)
        self._comp_surf  = None
        self._comp_size  = (0, 0)

        # Minimap
        self.minimap_surface  = None
        self._minimap_inf_ver = -1
        self._minimap_mat_ver = -1

    # ── base terrain colours ───────────────────────────────────────────────
    def _build_base_colors(self):
        colors = np.zeros((MAP_H, MAP_W, 3), dtype=np.uint8)
        for i, name in enumerate(self.biome_names):
            mask = self.biome_map == i
            r, g, b = BIOME_COLORS.get(name, (128, 128, 128))
            colors[mask] = [r, g, b]
        return colors

    # ── dirty flag ─────────────────────────────────────────────────────────
    def mark_influence_dirty(self):
        self.chunks.invalidate_all()
        self._minimap_inf_ver = -1
        self._minimap_mat_ver = -1

    # ── main render (chunk-based, massive map friendly) ────────────────────
    def render_map_to_area(self, camera, y_offset=0):
        cell = camera.cell_size
        x0, y0, x1, y1 = camera.get_visible_rect()
        vis_w = x1 - x0
        vis_h = y1 - y0
        if vis_w <= 0 or vis_h <= 0:
            return

        self.chunks.tick_animation()

        # Determine visible chunk range
        cx0 = x0 // CHUNK_SIZE
        cy0 = y0 // CHUNK_SIZE
        cx1 = (x1 - 1) // CHUNK_SIZE
        cy1 = (y1 - 1) // CHUNK_SIZE

        # Composition surface at 1px/tile for visible area
        comp_w = vis_w
        comp_h = vis_h
        if self._comp_surf is None or self._comp_size != (comp_w, comp_h):
            self._comp_surf = pygame.Surface((comp_w, comp_h))
            self._comp_size = (comp_w, comp_h)

        # Blit each visible chunk onto composition surface
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                if cx < 0 or cy < 0 or cx >= self.chunks.cols or cy >= self.chunks.rows:
                    continue
                chunk_surf = self.chunks.get(cx, cy)

                # Where to blit on composition surface
                chunk_x0 = cx * CHUNK_SIZE
                chunk_y0 = cy * CHUNK_SIZE
                dst_x = chunk_x0 - x0
                dst_y = chunk_y0 - y0

                self._comp_surf.blit(chunk_surf, (dst_x, dst_y))

        # Scale composition surface to screen pixels
        screen_w = vis_w * cell
        screen_h = vis_h * cell
        scaled = pygame.transform.scale(self._comp_surf, (screen_w, screen_h))

        # Blit to screen with sub-tile offset
        ox = -int((camera.x - x0) * cell)
        oy = -int((camera.y - y0) * cell) + y_offset
        self.screen.blit(scaled, (ox, oy))

    # ── minimap ────────────────────────────────────────────────────────────
    def render_minimap(self, camera, y_offset=0):
        inf_ver = self.influence._version
        mat_ver = self.material_layer._version if self.material_layer else -1
        if (self._minimap_inf_ver != inf_ver
                or self._minimap_mat_ver != mat_ver
                or self.minimap_surface is None):
            self._build_minimap()
            self._minimap_inf_ver = inf_ver
            self._minimap_mat_ver = mat_ver

        mx = SCR.w - MINIMAP_W - MINIMAP_MARGIN
        my = MINIMAP_MARGIN + y_offset

        # Frame
        fr = pygame.Rect(mx - 2, my - 2, MINIMAP_W + 4, MINIMAP_H + 4)
        pygame.draw.rect(self.screen, (16, 16, 24), fr)
        pygame.draw.rect(self.screen, (70, 70, 90), fr, 1)

        self.screen.blit(self.minimap_surface, (mx, my))

        # Viewport rectangle
        vx = camera.x / MAP_W * MINIMAP_W
        vy = camera.y / MAP_H * MINIMAP_H
        vw = (SCR.w / camera.cell_size) / MAP_W * MINIMAP_W
        vh = (SCR.viewport_h / camera.cell_size) / MAP_H * MINIMAP_H
        vr = pygame.Rect(mx + vx, my + vy, min(vw, MINIMAP_W), min(vh, MINIMAP_H))
        pygame.draw.rect(self.screen, (255, 255, 255), vr, 1)

    def _build_minimap(self):
        ty_idx = np.clip((np.arange(MINIMAP_H) * MAP_H / MINIMAP_H).astype(int),
                         0, MAP_H - 1)
        tx_idx = np.clip((np.arange(MINIMAP_W) * MAP_W / MINIMAP_W).astype(int),
                         0, MAP_W - 1)

        sampled = self.terrain_colors[ty_idx][:, tx_idx].astype(np.int16)
        dom_s   = self.influence.dominant_god[ty_idx][:, tx_idx]
        str_s   = self.influence.dominant_strength[ty_idx][:, tx_idx]

        for gi in range(self.influence.num_gods):
            god_id = self.influence.god_ids[gi]
            gc     = np.array(GOD_COLORS.get(god_id, (128, 128, 128)), dtype=np.int16)
            mask   = dom_s == gi
            if not np.any(mask):
                continue
            tint = np.clip(str_s * 0.45, 0, 0.45)
            t3   = (tint * mask)[:, :, np.newaxis]
            sampled = np.where(t3 > 0, sampled * (1 - t3) + gc * t3, sampled)

        # Overlay active materials on minimap
        if self.material_layer is not None:
            mat_s = self.material_layer.mat[ty_idx][:, tx_idx]
            has_m = mat_s > 0
            if np.any(has_m):
                mat_c = _MAT_COLOR_LUT[mat_s].astype(np.int16)
                sampled = np.where(has_m[:, :, np.newaxis],
                                   sampled * 0.4 + mat_c * 0.6, sampled)

        sampled = np.clip(sampled, 0, 255).astype(np.uint8)
        arr = np.ascontiguousarray(sampled.transpose(1, 0, 2))
        self.minimap_surface = pygame.surfarray.make_surface(arr)
