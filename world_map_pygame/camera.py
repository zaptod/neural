"""
World Map — Camera System
Pan / zoom with keyboard, mouse drag, and scroll wheel.
"""
import pygame
from config import MAP_W, MAP_H, ZOOM_LEVELS, DEFAULT_ZOOM, SCR


class Camera:
    def __init__(self):
        self.zoom_idx  = DEFAULT_ZOOM
        self.cell_size = ZOOM_LEVELS[self.zoom_idx]

        self.x = 0.0    # top-left in tile coords
        self.y = 0.0
        self.pan_speed = 5.0

        self.dragging       = False
        self._drag_start    = (0, 0)
        self._drag_cam      = (0.0, 0.0)
        self._clamp()

    # ── viewport helpers ───────────────────────────────────────────────────
    @property
    def viewport_tiles_w(self):
        cs = max(self.cell_size, 1)
        return SCR.w // cs + 2

    @property
    def viewport_tiles_h(self):
        cs = max(self.cell_size, 1)
        return SCR.viewport_h // cs + 2

    def get_visible_rect(self):
        """(x0, y0, x1, y1) tile range currently on screen."""
        cs = max(self.cell_size, 1)
        x0 = max(0, int(self.x))
        y0 = max(0, int(self.y))
        x1 = min(MAP_W,  int(self.x + SCR.w / cs) + 2)
        y1 = min(MAP_H, int(self.y + SCR.viewport_h / cs) + 2)
        return x0, y0, x1, y1

    # ── zoom ───────────────────────────────────────────────────────────────
    def zoom_in(self):
        if self.zoom_idx >= len(ZOOM_LEVELS) - 1:
            return
        cx, cy = self._center()
        self.zoom_idx += 1
        self.cell_size = ZOOM_LEVELS[self.zoom_idx]
        self._set_center(cx, cy)

    def zoom_out(self):
        if self.zoom_idx <= 0:
            return
        cx, cy = self._center()
        self.zoom_idx -= 1
        self.cell_size = ZOOM_LEVELS[self.zoom_idx]
        self._set_center(cx, cy)

    # ── pan ────────────────────────────────────────────────────────────────
    def pan(self, dtx, dty):
        self.x += dtx
        self.y += dty
        self._clamp()

    def handle_keys(self, dt):
        keys = pygame.key.get_pressed()
        spd  = self.pan_speed * (20.0 / self.cell_size) * dt
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.pan(-spd, 0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.pan( spd, 0)
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.pan(0, -spd)
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.pan(0,  spd)

    # ── mouse drag ─────────────────────────────────────────────────────────
    def start_drag(self, pos):
        self.dragging    = True
        self._drag_start = pos
        self._drag_cam   = (self.x, self.y)

    def update_drag(self, pos):
        if not self.dragging or self.cell_size < 1:
            return
        dx = (self._drag_start[0] - pos[0]) / self.cell_size
        dy = (self._drag_start[1] - pos[1]) / self.cell_size
        self.x = self._drag_cam[0] + dx
        self.y = self._drag_cam[1] + dy
        self._clamp()

    def stop_drag(self):
        self.dragging = False

    # ── coordinate conversion ──────────────────────────────────────────────
    def screen_to_tile(self, sx, sy):
        cs = max(self.cell_size, 1)
        return int(self.x + sx / cs), int(self.y + sy / cs)

    def tile_to_screen(self, tx, ty):
        return int((tx - self.x) * self.cell_size), int((ty - self.y) * self.cell_size)

    # ── internal ───────────────────────────────────────────────────────────
    def _center(self):
        cs = max(self.cell_size, 1)
        return (self.x + SCR.w / cs / 2,
                self.y + SCR.viewport_h / cs / 2)

    def _set_center(self, cx, cy):
        self.x = cx - SCR.w / self.cell_size / 2
        self.y = cy - SCR.viewport_h / self.cell_size / 2
        self._clamp()

    def _clamp(self):
        max_x = max(0.0, MAP_W  - SCR.w / self.cell_size)
        max_y = max(0.0, MAP_H - SCR.viewport_h / self.cell_size)
        self.x = max(0.0, min(self.x, max_x))
        self.y = max(0.0, min(self.y, max_y))
