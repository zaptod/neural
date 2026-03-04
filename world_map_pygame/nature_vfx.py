"""
world_map_pygame/nature_vfx.py
Nature corruption visual effects — per-zone environmental VFX.

When a zone is owned by a god (or has a strong base_nature), the terrain
shows corruption effects: tinting, particles, ambient overlays.

Effects are rendered per-zone, cached as textures, and composited onto the map.
"""
import math
import random
import pygame
import numpy as np
from typing import Dict, List, Optional, Tuple

from .config import (
    TEX_W, TEX_H, WORLD_W, WORLD_H,
    NATURE_TINT, NATURE_COLOR, NATURE_VFX, scaled,
)


# ─── AMBIENT PARTICLE SYSTEM ─────────────────────────────────────────────────

class AmbientParticle:
    """A single ambient particle for nature VFX."""
    __slots__ = ["x", "y", "vx", "vy", "col", "life", "max_life", "size", "alpha"]

    def __init__(self, x, y, vx, vy, col, life, size=2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.col = col
        self.life = life
        self.max_life = life
        self.size = size
        self.alpha = 255


class NatureVFX:
    """
    Manages per-zone nature corruption visual effects.
    
    Features:
    - Nature tint overlay (cached texture layer)
    - Ambient particles (floating embers, snowflakes, leaves, etc.)
    - Zone border corruption effects (vines, cracks, frost, etc.)
    """

    # Particle configs per nature type
    _PARTICLE_CONFIG = {
        "ember":  {"color": (255, 140,  30), "speed": 25, "life": 2.0, "size": 2, "vy_bias": -20, "count": 3},
        "snow":   {"color": (220, 230, 250), "speed": 15, "life": 3.0, "size": 2, "vy_bias":  12, "count": 3},
        "shadow": {"color": ( 80,  30, 130), "speed": 10, "life": 2.5, "size": 3, "vy_bias":  -5, "count": 2},
        "leaf":   {"color": ( 80, 170,  50), "speed": 20, "life": 2.5, "size": 2, "vy_bias":   8, "count": 2},
        "glitch": {"color": (220,  60, 200), "speed": 40, "life": 0.5, "size": 2, "vy_bias":   0, "count": 4},
        "void":   {"color": ( 40,  50, 180), "speed":  8, "life": 3.5, "size": 3, "vy_bias":  -3, "count": 2},
        "gold":   {"color": (255, 210,  50), "speed": 18, "life": 2.0, "size": 1, "vy_bias": -10, "count": 3},
        "fog":    {"color": (100,  40, 150), "speed":  6, "life": 4.0, "size": 4, "vy_bias":   0, "count": 1},
        "glow":   {"color": (100, 220, 255), "speed": 12, "life": 2.5, "size": 2, "vy_bias":  -8, "count": 1},
        "sigil":  {"color": (140, 120, 240), "speed": 15, "life": 2.0, "size": 2, "vy_bias":  -5, "count": 2},
        "drip":   {"color": (200,  30,  30), "speed": 10, "life": 1.5, "size": 2, "vy_bias":  15, "count": 2},
        "dust":   {"color": (190, 160,  80), "speed":  8, "life": 3.0, "size": 2, "vy_bias":  -2, "count": 1},
    }

    def __init__(self, zones: dict, zone_idx: np.ndarray):
        self.zones = zones
        self.zone_idx = zone_idx
        self._particles: List[AmbientParticle] = []
        self._tint_surf: Optional[pygame.Surface] = None
        self._tint_key = None  # ownership hash for cache invalidation
        self._corruption_surf: Optional[pygame.Surface] = None
        self._corruption_key = None
        self._emit_timers: Dict[str, float] = {}  # zone_id → time until next emit
        self._rng = random.Random(42)

        # Pre-allocated particle surface
        self._particle_surfs: Dict[int, pygame.Surface] = {}

    def _get_particle_surf(self, size: int) -> pygame.Surface:
        """Get or create a reusable particle surface."""
        if size not in self._particle_surfs:
            s = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
            self._particle_surfs[size] = s
        return self._particle_surfs[size]

    def build_nature_tint(self, ownership: dict, gods: dict) -> pygame.Surface:
        """
        Build a texture-space RGBA surface that tints each zone by its nature.
        Owned zones use the god's nature; unowned use base_nature.
        Cached — only rebuilds when ownership changes.
        """
        key = tuple(sorted(ownership.items()))
        if key == self._tint_key and self._tint_surf is not None:
            return self._tint_surf

        if self._tint_surf is None:
            self._tint_surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)

        surf = self._tint_surf
        surf.fill((0, 0, 0, 0))

        rgb_arr = pygame.surfarray.pixels3d(surf)
        alpha_arr = pygame.surfarray.pixels_alpha(surf)
        idx_t = self.zone_idx.T  # (W, H)

        zone_list = list(self.zones.values())
        for i, zone in enumerate(zone_list):
            # Determine effective nature
            gid = ownership.get(zone.zone_id)
            if gid:
                god = gods.get(gid)
                nature = god.nature if god else zone.base_nature
            else:
                nature = zone.base_nature

            tint = NATURE_TINT.get(nature, NATURE_TINT.get("unclaimed"))
            if tint is None:
                continue

            mask = (idx_t == i)
            rgb_arr[mask, 0] = tint[0]
            rgb_arr[mask, 1] = tint[1]
            rgb_arr[mask, 2] = tint[2]
            alpha_arr[mask] = tint[3]

        del rgb_arr, alpha_arr
        self._tint_key = key
        return self._tint_surf

    def build_corruption_overlay(self, ownership: dict, gods: dict,
                                  t: float) -> pygame.Surface:
        """
        Build corruption overlay effects on zone borders.
        Cracks (fire), frost (ice), vines (nature), etc.
        This is drawn at higher LOD levels.
        """
        key = (tuple(sorted(ownership.items())), int(t * 2))
        if key == self._corruption_key and self._corruption_surf is not None:
            return self._corruption_surf

        if self._corruption_surf is None:
            self._corruption_surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)

        surf = self._corruption_surf
        surf.fill((0, 0, 0, 0))

        zone_list = list(self.zones.values())

        for i, zone in enumerate(zone_list):
            gid = ownership.get(zone.zone_id)
            if gid:
                god = gods.get(gid)
                nature = god.nature if god else zone.base_nature
            else:
                nature = zone.base_nature

            vfx_cfg = NATURE_VFX.get(nature)
            if not vfx_cfg or not vfx_cfg.get("overlay"):
                continue

            intensity = vfx_cfg["intensity"]
            nc = NATURE_COLOR.get(nature, (150, 150, 150))

            # Draw corruption lines radiating from centroid
            cx_w, cy_w = zone.centroid
            cx_t = int(cx_w / WORLD_W * TEX_W)
            cy_t = int(cy_w / WORLD_H * TEX_H)

            rng = random.Random(hash(zone.zone_id) & 0xFFFFFFFF)
            num_lines = int(6 * intensity)

            for _ in range(num_lines):
                angle = rng.uniform(0, math.pi * 2)
                length = rng.uniform(20, 80) * intensity
                segments = rng.randint(3, 6)

                px, py = cx_t, cy_t
                for s in range(segments):
                    a = angle + rng.uniform(-0.5, 0.5)
                    seg_len = length / segments
                    nx = int(px + math.cos(a) * seg_len)
                    ny = int(py + math.sin(a) * seg_len)
                    nx = max(0, min(TEX_W - 1, nx))
                    ny = max(0, min(TEX_H - 1, ny))

                    # Check if still in this zone
                    if 0 <= ny < TEX_H and 0 <= nx < TEX_W:
                        if self.zone_idx[ny, nx] != i:
                            break

                    alpha = int(120 * intensity * (1 - s / segments))
                    pygame.draw.line(surf, (*nc, alpha), (px, py), (nx, ny),
                                    max(1, int(2 * (1 - s / segments))))
                    px, py = nx, ny

        self._corruption_key = key
        return self._corruption_surf

    def update_particles(self, dt: float, cam, ownership: dict, gods: dict,
                          clip: pygame.Rect):
        """Update ambient particles and emit new ones near visible zones."""
        # Update existing particles
        alive = []
        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
            p.alpha = int(200 * max(0, p.life / p.max_life))
            if p.life > 0:
                alive.append(p)
        self._particles = alive

        # Cap particle count for performance
        MAX_PARTICLES = 200
        if len(self._particles) >= MAX_PARTICLES:
            return

        # Emit new particles for visible zones
        wl, wt = cam.s2w(clip.x, clip.y)
        wr, wb = cam.s2w(clip.x + clip.width, clip.y + clip.height)

        for zone in self.zones.values():
            cx, cy = zone.centroid
            if not (wl <= cx <= wr and wt <= cy <= wb):
                continue

            # Determine nature
            gid = ownership.get(zone.zone_id)
            if gid:
                god = gods.get(gid)
                nature = god.nature if god else zone.base_nature
            else:
                nature = zone.base_nature

            vfx_cfg = NATURE_VFX.get(nature)
            if not vfx_cfg or not vfx_cfg.get("particles"):
                continue

            pcfg = self._PARTICLE_CONFIG.get(vfx_cfg["particles"])
            if not pcfg:
                continue

            # Timer-based emission
            timer_key = zone.zone_id
            timer = self._emit_timers.get(timer_key, 0.0)
            timer -= dt
            if timer <= 0:
                emit_interval = 1.0 / max(1, pcfg["count"])
                timer = emit_interval + self._rng.uniform(0, 0.5)

                # Emit particle at random position near centroid
                spread = 60 * vfx_cfg["intensity"]
                px = cx + self._rng.uniform(-spread, spread)
                py = cy + self._rng.uniform(-spread, spread)

                angle = self._rng.uniform(0, math.pi * 2)
                spd = pcfg["speed"] + self._rng.uniform(-5, 5)
                vx = math.cos(angle) * spd * 0.3
                vy = pcfg["vy_bias"] + math.sin(angle) * spd * 0.3

                col = pcfg["color"]
                # Add some color variation
                col = tuple(max(0, min(255, c + self._rng.randint(-15, 15)))
                           for c in col)

                self._particles.append(AmbientParticle(
                    x=px, y=py, vx=vx, vy=vy,
                    col=col,
                    life=pcfg["life"] + self._rng.uniform(-0.3, 0.3),
                    size=pcfg["size"],
                ))

            self._emit_timers[timer_key] = timer

    def draw_particles(self, screen: pygame.Surface, cam, clip: pygame.Rect):
        """Draw ambient particles in screen space."""
        screen.set_clip(clip)
        for p in self._particles:
            sx, sy = cam.w2s(p.x, p.y)
            if not clip.collidepoint(sx, sy):
                continue

            sz = max(1, int(p.size * cam.zoom))
            if sz <= 1:
                col_with_alpha = (*p.col[:3], p.alpha)
                # Single pixel — just draw directly
                s = pygame.Surface((2, 2), pygame.SRCALPHA)
                s.fill(col_with_alpha)
                screen.blit(s, (sx - 1, sy - 1))
            else:
                s = self._get_particle_surf(sz)
                s.fill((0, 0, 0, 0))
                pygame.draw.circle(s, (*p.col[:3], p.alpha), (sz, sz), sz)
                screen.blit(s, (sx - sz, sy - sz))
        screen.set_clip(None)

    def draw_tint_viewport(self, screen: pygame.Surface, tint_surf: pygame.Surface,
                            cam, clip: pygame.Rect):
        """Blit the nature tint texture to screen, viewport-only."""
        map_y = cam.map_y
        map_h = clip.height

        wl, wt = cam.s2w(clip.x, map_y)
        wr, wb = cam.s2w(clip.x + clip.width, map_y + map_h)
        wl = max(0.0, wl)
        wt = max(0.0, wt)
        wr = min(float(WORLD_W), wr)
        wb = min(float(WORLD_H), wb)
        if wr <= wl or wb <= wt:
            return

        tx0 = int(wl / WORLD_W * TEX_W)
        ty0 = int(wt / WORLD_H * TEX_H)
        tx1 = min(TEX_W, int(wr / WORLD_W * TEX_W) + 1)
        ty1 = min(TEX_H, int(wb / WORLD_H * TEX_H) + 1)
        src = pygame.Rect(tx0, ty0, max(1, tx1 - tx0), max(1, ty1 - ty0))

        sx0, sy0 = cam.w2s(wl, wt)
        dw = max(1, int((wr - wl) * cam.zoom))
        dh = max(1, int((wb - wt) * cam.zoom))

        chunk = tint_surf.subsurface(src)
        scaled_ch = pygame.transform.smoothscale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled_ch, (sx0, sy0))
        screen.set_clip(None)
