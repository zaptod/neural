"""
world_map_pygame/camera.py
Câmera estilo Google Maps: pan com inércia, zoom ancorado no cursor, fly-to animado.
Agora considera map_y (offset do HUD) nas conversões de coordenada.
"""
import math
from . import config
from .config import WORLD_W, WORLD_H

MAP_Y_OFFSET = 40  # deve bater com UI.HUD_H


class Camera:
    MIN_ZOOM  = 0.20
    MAX_ZOOM  = 6.0
    ZOOM_STEP = 1.13
    FRICTION  = 0.78
    FLY_SPEED = 0.10

    def __init__(self, map_x: int, map_w: int):
        self.map_x = map_x
        self.map_w = map_w
        self.map_y = MAP_Y_OFFSET
        map_h      = config.SCREEN_H - MAP_Y_OFFSET

        fit = min(map_w / WORLD_W, map_h / WORLD_H) * 0.90
        self.zoom     = fit
        self.offset_x = WORLD_W / 2 - (map_w  / 2) / fit
        self.offset_y = WORLD_H / 2 - (map_h  / 2) / fit

        self.vx = self.vy = 0.0
        self.dragging = False
        self._dsx = self._dsy = 0
        self._dox = self._doy = 0.0
        self._lsx = self._lsy = 0

        self.flying = False
        self._fox = self._foy = self._fz = 0.0

    # ── Conversões ────────────────────────────────────────────────────────
    def w2s(self, wx: float, wy: float):
        """World-units → pixel de tela."""
        return (
            int((wx - self.offset_x) * self.zoom) + self.map_x,
            int((wy - self.offset_y) * self.zoom) + self.map_y,
        )

    def s2w(self, sx: float, sy: float):
        """Pixel de tela → world-units."""
        return (
            (sx - self.map_x) / self.zoom + self.offset_x,
            (sy - self.map_y) / self.zoom + self.offset_y,
        )

    # ── Zoom ──────────────────────────────────────────────────────────────
    def zoom_at(self, sx: float, sy: float, factor: float):
        wx, wy = self.s2w(sx, sy)
        nz = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if nz == self.zoom:
            return
        self.zoom     = nz
        self.offset_x = wx - (sx - self.map_x) / self.zoom
        self.offset_y = wy - (sy - self.map_y) / self.zoom
        self.vx = self.vy = 0.0

    # ── Pan ───────────────────────────────────────────────────────────────
    def start_drag(self, sx: float, sy: float):
        self.dragging = True
        self.flying   = False
        self._dsx, self._dsy = sx, sy
        self._dox, self._doy = self.offset_x, self.offset_y
        self._lsx, self._lsy = sx, sy
        self.vx = self.vy = 0.0

    def update_drag(self, sx: float, sy: float):
        if not self.dragging:
            return
        self.vx = (self._lsx - sx) / self.zoom
        self.vy = (self._lsy - sy) / self.zoom
        self._lsx, self._lsy = sx, sy
        self.offset_x = self._dox - (sx - self._dsx) / self.zoom
        self.offset_y = self._doy - (sy - self._dsy) / self.zoom

    def end_drag(self):
        self.dragging = False

    # ── Fly-to ────────────────────────────────────────────────────────────
    def fly_to(self, wx: float, wy: float, tz: float = None):
        map_h = config.SCREEN_H - self.map_y
        if tz is None:
            tz = min(self.MAX_ZOOM * 0.6, max(self.zoom * 1.9, 1.6))
        self._fox = wx - (self.map_w / 2) / tz
        self._foy = wy - (map_h       / 2) / tz
        self._fz  = tz
        self.flying = True
        self.vx = self.vy = 0.0

    def fly_home(self):
        map_h = config.SCREEN_H - self.map_y
        fit = min(self.map_w / WORLD_W, map_h / WORLD_H) * 0.90
        self.fly_to(WORLD_W / 2, WORLD_H / 2, fit)

    # ── Update ────────────────────────────────────────────────────────────
    def update(self):
        if self.flying:
            sp = self.FLY_SPEED
            self.offset_x += (self._fox - self.offset_x) * sp
            self.offset_y += (self._foy - self.offset_y) * sp
            self.zoom     += (self._fz  - self.zoom)     * sp
            if (math.hypot(self.offset_x - self._fox,
                           self.offset_y - self._foy) < 0.5
                    and abs(self.zoom - self._fz) < 0.002):
                self.offset_x, self.offset_y, self.zoom = \
                    self._fox, self._foy, self._fz
                self.flying = False
        elif not self.dragging:
            if abs(self.vx) < 0.22 and abs(self.vy) < 0.22:
                self.vx = self.vy = 0.0
            else:
                self.offset_x += self.vx
                self.offset_y += self.vy
                self.vx *= self.FRICTION
                self.vy *= self.FRICTION
