"""
World Map — VFX / Particle System
Ambient atmosphere particles: snow, leaves, waves, sand, mist, magic, clouds.
"""
import pygame
import random
import math
try:
    from .config import (
        MAP_W, MAP_H,
        MAX_PARTICLES, GOD_COLORS, SCR,
    )
except ImportError:  # pragma: no cover - direct script fallback
    from config import (
        MAP_W, MAP_H,
        MAX_PARTICLES, GOD_COLORS, SCR,
    )


class _P:
    """Lightweight particle."""
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life',
                 'color', 'size', 'kind', 'alpha')

    def __init__(self, x, y, vx, vy, life, color, size, kind):
        self.x = x; self.y = y; self.vx = vx; self.vy = vy
        self.life = life; self.max_life = life
        self.color = color; self.size = size; self.kind = kind
        self.alpha = 255


class ParticleSystem:
    def __init__(self):
        self.particles: list[_P] = []
        self._timer = 0.0

    # ── tick ───────────────────────────────────────────────────────────────
    def update(self, dt, camera, biome_map, biome_names, influence):
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.alpha = int(255 * min(p.life / p.max_life * 2, 1.0))
            alive.append(p)
        self.particles = alive

        self._timer += dt
        if self._timer >= 0.12 and len(self.particles) < MAX_PARTICLES:
            self._timer = 0.0
            self._spawn(camera, biome_map, biome_names, influence)

    # ── spawn ──────────────────────────────────────────────────────────────
    def _spawn(self, cam, bm, bn, inf):
        x0, y0, x1, y1 = cam.get_visible_rect()
        if x1 <= x0 or y1 <= y0:
            return
        tx = random.randint(max(0, x0), min(MAP_W - 1, x1 - 1))
        ty = random.randint(max(0, y0), min(MAP_H - 1, y1 - 1))
        biome = bn[bm[ty, tx]]

        R = random.random
        U = random.uniform

        if biome == 'snow':
            self._add(tx + R(), ty + R(), U(-0.3, 0.3), U(0.5, 1.5),
                      U(2, 5), (230, 240, 250), 1, 'snow')
        elif biome in ('forest', 'dense_forest') and R() < 0.4:
            self._add(tx + R(), ty + R(), U(-1, 1), U(-0.5, 0.5),
                      U(2, 4), (random.randint(60, 120),
                                random.randint(100, 160),
                                random.randint(20, 60)), 1, 'leaf')
        elif biome in ('deep_ocean', 'ocean', 'shallow_water') and R() < 0.3:
            self._add(tx + R(), ty + R(), U(-0.4, 0.4), U(-0.2, 0.2),
                      U(1, 3), (80, 140, 200), 1, 'wave')
        elif biome == 'desert' and R() < 0.25:
            self._add(tx + R(), ty + R(), U(1, 3), U(-0.5, 0.5),
                      U(1, 2), (210, 190, 130), 1, 'sand')
        elif biome == 'swamp' and R() < 0.3:
            self._add(tx + R(), ty + R(), U(-0.2, 0.2), U(-0.4, 0),
                      U(3, 6), (140, 160, 120), 2, 'mist')

        # Magic near strongholds
        gid, st = inf.get_dominant_at(tx, ty)
        if gid and st > 0.5 and R() < 0.2:
            gc = GOD_COLORS.get(gid, (200, 200, 200))
            self._add(tx + R(), ty + R(), U(-0.5, 0.5), U(-1.5, -0.5),
                      U(1, 3),
                      (min(255, gc[0]+50), min(255, gc[1]+50), min(255, gc[2]+50)),
                      1, 'magic')

        # Clouds (sparse)
        if R() < 0.12:
            self._add(tx, ty, U(0.3, 1.0), U(-0.1, 0.1),
                      U(6, 14), (200, 200, 215), 3, 'cloud')

    def _add(self, *a):
        self.particles.append(_P(*a))

    # ── draw ───────────────────────────────────────────────────────────────
    def render(self, screen, camera):
        cell = camera.cell_size
        for p in self.particles:
            sx, sy = camera.tile_to_screen(p.x, p.y)
            if sx < -20 or sx > SCR.w + 20 or sy < -20 or sy > SCR.viewport_h + 20:
                continue
            sz = max(1, int(p.size * cell / 4))
            a  = p.alpha

            if p.kind == 'cloud':
                sz2 = max(4, int(p.size * cell / 2))
                a2  = min(a, 50)
                cs  = pygame.Surface((sz2 * 3, sz2 * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(cs, (*p.color, a2), (0, 0, sz2 * 3, sz2 * 2))
                screen.blit(cs, (sx - sz2, sy - sz2 // 2))
            elif p.kind == 'magic':
                gs = sz * 3
                ms = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
                pygame.draw.circle(ms, (*p.color, a // 3), (gs, gs), gs)
                pygame.draw.circle(ms, (*p.color, a),       (gs, gs), sz)
                screen.blit(ms, (sx - gs, sy - gs))
            else:
                if a > 200:
                    pygame.draw.rect(screen, p.color, (sx, sy, sz, sz))
                else:
                    ps = pygame.Surface((sz, sz), pygame.SRCALPHA)
                    ps.fill((*p.color, a))
                    screen.blit(ps, (sx, sy))
