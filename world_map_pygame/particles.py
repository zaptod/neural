"""
world_map_pygame/particles.py
Sistema de partículas leve para feedback visual de seleção/eventos.
"""
import math, random
from typing import List
import pygame


class Particle:
    __slots__ = ["x", "y", "vx", "vy", "col", "life", "ml", "sz"]

    def __init__(self, x, y, vx, vy, col, life, sz=2):
        self.x, self.y   = x, y
        self.vx, self.vy = vx, vy
        self.col  = col
        self.life = life
        self.ml   = life
        self.sz   = sz

    def update(self, dt: float):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.life -= dt

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def alpha(self) -> int:
        return int(220 * max(0.0, self.life / self.ml))


class Particles:
    MAX_PARTICLES = 300

    def __init__(self):
        self._ps: List[Particle] = []
        self._surf_cache: dict = {}  # (sz,) → Surface

    def _get_surf(self, sz: int) -> pygame.Surface:
        """Get or create a reusable particle surface for the given size."""
        if sz not in self._surf_cache:
            self._surf_cache[sz] = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
        return self._surf_cache[sz]

    def emit(self, x: float, y: float, col,
             n: int = 10, spd: float = 55, life: float = 1.1, sz: int = 2):
        budget = max(0, self.MAX_PARTICLES - len(self._ps))
        n = min(n, budget)
        for _ in range(n):
            a  = random.uniform(0, math.pi * 2)
            sp = random.uniform(spd * 0.35, spd)
            self._ps.append(Particle(
                x + random.uniform(-3, 3),
                y + random.uniform(-3, 3),
                math.cos(a) * sp, math.sin(a) * sp,
                col, random.uniform(life * 0.45, life), sz,
            ))

    def update(self, dt: float):
        self._ps = [p for p in self._ps if p.alive]
        for p in self._ps:
            p.update(dt)

    def draw(self, screen: pygame.Surface):
        for p in self._ps:
            s = self._get_surf(p.sz)
            s.fill((0, 0, 0, 0))
            pygame.draw.circle(s, (*p.col[:3], p.alpha), (p.sz, p.sz), p.sz)
            screen.blit(s, (int(p.x - p.sz), int(p.y - p.sz)))
