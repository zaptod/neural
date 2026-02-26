"""
world_map_pygame/renderer.py
MapRenderer — renderiza o mapa na área (map_x, map_y, map_w, map_h).
Todos os draws são clipados a essa área para não invadir painéis.
"""
import math
import pygame
import numpy as np
from typing import Dict, Optional

from . import config
from .config import (
    WORLD_W, WORLD_H, TEX_W, TEX_H,
    CYAN, GOLD, CRIMSON, TXT, TXT_DIM,
    NATURE_COLOR, SEAL_COLOR,
)
from .camera import Camera
from .data_loader import Zone, God

MAP_Y_OFFSET = 40  # deve bater com UI.HUD_H


class MapRenderer:
    def __init__(self, map_surf, zone_idx, zone_list, zones, gods, cam):
        self.surf      = map_surf
        self.zone_idx  = zone_idx
        self.zone_list = zone_list
        self.zones     = zones
        self.gods      = gods
        self.cam       = cam
        self._compass  = _build_compass(56)
        self._lfonts: Dict[int, pygame.font.Font] = {}

    def _lf(self, size: int) -> pygame.font.Font:
        if size not in self._lfonts:
            self._lfonts[size] = pygame.font.SysFont("consolas", size)
        return self._lfonts[size]

    def draw(self, screen, ownership, selected_zone, hover_zone,
             ancient_seals, t: float, map_x: int, map_w: int):

        cam    = self.cam
        map_y  = MAP_Y_OFFSET
        map_h  = config.SCREEN_H - map_y
        clip   = pygame.Rect(map_x, map_y, map_w, map_h)

        # ── Viewport da textura ───────────────────────────────────────────
        wl, wt = cam.s2w(map_x, map_y)
        wr, wb = cam.s2w(map_x + map_w, map_y + map_h)
        wl = max(0.0, wl); wt = max(0.0, wt)
        wr = min(float(WORLD_W), wr)
        wb = min(float(WORLD_H), wb)

        if wr <= wl or wb <= wt:
            pygame.draw.rect(screen, (50, 80, 130), clip)
            return

        tx0 = int(wl / WORLD_W * TEX_W)
        ty0 = int(wt / WORLD_H * TEX_H)
        tx1 = min(TEX_W, int(wr / WORLD_W * TEX_W) + 1)
        ty1 = min(TEX_H, int(wb / WORLD_H * TEX_H) + 1)
        src = pygame.Rect(tx0, ty0, max(1, tx1 - tx0), max(1, ty1 - ty0))

        sx0, sy0 = cam.w2s(wl, wt)
        dw = max(1, int((wr - wl) * cam.zoom))
        dh = max(1, int((wb - wt) * cam.zoom))

        # Fundo oceano
        screen.fill((85, 115, 170), clip)

        chunk  = self.surf.subsurface(src)
        scaled = pygame.transform.scale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled, (sx0, sy0))
        screen.set_clip(None)

        # Hover
        if hover_zone and hover_zone != selected_zone:
            self._draw_poly_overlay(screen, hover_zone.vertices, clip,
                                    (255, 255, 255, 18), (200, 220, 255, 80),
                                    max(1, int(1.5 * cam.zoom)))

        # Ownership
        if ownership:
            self._draw_ownership(screen, ownership, clip)

        # Selos
        self._draw_seals(screen, ancient_seals, t, clip)

        # Seleção
        if selected_zone:
            pa = int(80 + math.sin(t * 3) * 60)
            self._draw_poly_overlay(screen, selected_zone.vertices, clip,
                                    (255, 220, 50, pa), (255, 210, 40, 230),
                                    max(3, int(3 * cam.zoom)))

        # Labels
        if cam.zoom >= 0.42:
            self._draw_labels(screen, ownership, clip)

        # Rosa dos ventos
        screen.blit(self._compass,
                    (map_x + map_w - 70, map_y + map_h - 70))

        # Borda pulsante
        p = int(170 + math.sin(t * 1.8) * 55)
        pygame.draw.rect(screen, (0, p // 2, p), clip, 2)

    def _draw_poly_overlay(self, screen, verts_world, clip,
                            fill_col, border_col, border_w):
        cam  = self.cam
        surf = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        verts = [cam.w2s(wx, wy) for wx, wy in verts_world]
        if len(verts) >= 3:
            pygame.draw.polygon(surf, fill_col, verts)
            pygame.draw.polygon(surf, border_col, verts, border_w)
        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    def _draw_ownership(self, screen, ownership, clip):
        cam  = self.cam
        surf = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        for zone in self.zones.values():
            gid = ownership.get(zone.zone_id)
            if not gid:
                continue
            god = self.gods.get(gid)
            if not god:
                continue
            r, g, b = god.rgb()
            verts = [cam.w2s(wx, wy) for wx, wy in zone.vertices]
            if len(verts) >= 3:
                pygame.draw.polygon(surf, (r, g, b, 52), verts)
                pygame.draw.polygon(surf, (r, g, b, 200), verts,
                                    max(2, int(2.5 * cam.zoom)))
        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    def _draw_seals(self, screen, ancient_seals, t, clip):
        cam  = self.cam
        surf = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        for zone in self.zones.values():
            if not zone.ancient_seal:
                continue
            sd     = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            col    = SEAL_COLOR.get(status, (130, 40, 220))
            a      = int(55 + math.sin(t * 2.5) * 45)
            sx, sy = cam.w2s(*zone.centroid)
            rg     = max(10, int(42 * cam.zoom))
            pygame.draw.circle(surf, (*col, a),             (sx, sy), rg)
            pygame.draw.circle(surf, (*col, min(255, a*2)), (sx, sy), max(4, rg // 4))
        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    def _draw_labels(self, screen, ownership, clip: pygame.Rect):
        cam  = self.cam
        fsz  = max(8, min(14, int(10 * cam.zoom)))
        font = self._lf(fsz)

        screen.set_clip(clip)
        for zone in self.zones.values():
            sx, sy = cam.w2s(*zone.centroid)
            if not clip.collidepoint(sx, sy):
                continue

            gid = ownership.get(zone.zone_id)
            col = TXT if gid else TXT_DIM

            lb  = font.render(zone.zone_name, True, col)
            sh  = font.render(zone.zone_name, True, (0, 0, 0))
            r   = lb.get_rect(center=(sx, sy))

            bg = pygame.Surface((r.width + 8, r.height + 4), pygame.SRCALPHA)
            bg.fill((6, 12, 28, 115))
            screen.blit(bg, (r.x - 4, r.y - 2))
            screen.blit(sh, r.move(1, 1))
            screen.blit(lb, r)

            if gid and cam.zoom >= 0.85:
                god = self.gods.get(gid)
                if god:
                    gf = self._lf(max(7, fsz - 2))
                    gs = gf.render(god.god_name, True, god.rgb())
                    screen.blit(gs, gs.get_rect(center=(sx, sy + fsz + 4)))

            if 0.42 <= cam.zoom <= 0.75:
                rf = self._lf(max(7, fsz - 1))
                rc = NATURE_COLOR.get(zone.base_nature, TXT_DIM)
                rs = rf.render(zone.region_name, True, rc)
                screen.blit(rs, rs.get_rect(center=(sx, sy - fsz - 4)))

        screen.set_clip(None)


def _build_compass(r: int) -> pygame.Surface:
    sz = r * 2 + 6
    s  = pygame.Surface((sz, sz), pygame.SRCALPHA)
    cx = cy = sz // 2
    GC = (210, 180, 50, 220)
    GD = (130, 110, 25, 180)
    DC = (10, 6, 2, 215)
    pygame.draw.circle(s, (100, 80, 30, 110), (cx, cy), r, 2)
    for adeg, length, col in [
        (0, r*0.94, GC), (180, r*0.80, GD),
        (90, r*0.72, GD), (270, r*0.72, GD),
    ]:
        a   = math.radians(adeg - 90)
        tip = (cx + math.cos(a)*length, cy + math.sin(a)*length)
        la  = a + math.pi/2; bw = r*0.16
        lp  = (cx + math.cos(la)*bw, cy + math.sin(la)*bw)
        rp  = (cx - math.cos(la)*bw, cy - math.sin(la)*bw)
        pygame.draw.polygon(s, col, [tip, lp, rp])
        mid = (cx + math.cos(a)*length*0.28, cy + math.sin(a)*length*0.28)
        pygame.draw.polygon(s, DC, [tip, mid, lp])
    for adeg in [45, 135, 225, 315]:
        a   = math.radians(adeg - 90)
        tip = (cx + math.cos(a)*r*0.50, cy + math.sin(a)*r*0.50)
        la  = a + math.pi/2; bw = r*0.08
        lp  = (cx + math.cos(la)*bw, cy + math.sin(la)*bw)
        rp  = (cx - math.cos(la)*bw, cy - math.sin(la)*bw)
        pygame.draw.polygon(s, GD, [tip, lp, rp])
    pygame.draw.circle(s, DC, (cx, cy), int(r*0.16))
    pygame.draw.circle(s, GC, (cx, cy), int(r*0.10))
    pygame.draw.circle(s, (240, 235, 215, 200), (cx, cy), int(r*0.05))
    return s
