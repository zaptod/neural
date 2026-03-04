"""
world_map_pygame/renderer.py
MapRenderer — renderiza o mapa na área (map_x, map_y, map_w, map_h).
Todos os draws são clipados a essa área para não invadir painéis.

[PHASE 17] Total rework:
  - Multi-LOD rendering pipeline (5 levels: Strategic → Close-up)
  - Nature corruption tint overlay (fire, ice, darkness, etc.)
  - Pixel-art structure rendering (buildings, temples, etc.)
  - Sub-district labels and markers
  - Region name labels at LOD 0
  - Roads between structures at LOD 2+
  - Ambient VFX integration points
  - Corruption overlay at LOD 3+
"""
import math
import pygame
import numpy as np
from scipy.ndimage import binary_erosion, binary_dilation
from typing import Dict, Optional, Tuple, List

from . import config
from .config import (
    WORLD_W, WORLD_H, TEX_W, TEX_H,
    CYAN, GOLD, GOLD_DIM, CRIMSON, TXT, TXT_DIM, TXT_MUTED,
    NATURE_COLOR, SEAL_COLOR, UI_BG, scaled, get_lod,
    STRUCTURE_TYPES,
)
from .camera import Camera
from .data_loader import Zone, God
from .world_events import EventLog, EventType, EVENT_VFX, SEVERITY_COLOR
from .lod import LODManager
from .structures import StructureManager


class MapRenderer:
    def __init__(self, map_surf, zone_idx, zone_list, zones, gods, cam,
                 structure_mgr: Optional[StructureManager] = None,
                 nature_vfx=None):
        self.surf      = map_surf
        self.zone_idx  = zone_idx
        self.zone_list = zone_list
        self.zones     = zones
        self.gods      = gods
        self.cam       = cam
        self.structure_mgr = structure_mgr
        self.nature_vfx = nature_vfx
        self.lod       = LODManager()
        self._compass  = _build_compass(scaled(56))
        self._lfonts:  Dict[tuple, pygame.font.Font] = {}
        self._ownership_surf: Optional[pygame.Surface] = None
        self._ownership_key  = None
        self._mask_cache: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray]] = {}
        self._filter_surf: Optional[pygame.Surface] = None
        self._filter_key  = None
        self._zone_work_surf: Optional[pygame.Surface] = None
        _sw, _sh = config.SCREEN_W, config.SCREEN_H
        self._marker_surf = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._seal_surf   = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._badge_surf  = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._struct_surf = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._road_surf   = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        self._subdist_surf = pygame.Surface((_sw, _sh), pygame.SRCALPHA)

        # Region name cache (LOD 0)
        self._region_data = self._build_region_data()

    def _build_region_data(self) -> list:
        """Build region centroids from zone data for LOD 0 labels."""
        regions: Dict[str, dict] = {}
        for zone in self.zones.values():
            rid = zone.region_id
            if rid not in regions:
                regions[rid] = {
                    "name": zone.region_name,
                    "xs": [], "ys": [],
                    "nature": zone.base_nature,
                }
            regions[rid]["xs"].append(zone.centroid[0])
            regions[rid]["ys"].append(zone.centroid[1])

        result = []
        for rid, data in regions.items():
            cx = sum(data["xs"]) / len(data["xs"])
            cy = sum(data["ys"]) / len(data["ys"])
            result.append({
                "id": rid,
                "name": data["name"],
                "cx": cx, "cy": cy,
                "nature": data["nature"],
            })
        return result

    def _lf(self, size: int, serif: bool = False) -> pygame.font.Font:
        k = (size, serif)
        if k not in self._lfonts:
            if serif:
                self._lfonts[k] = pygame.font.SysFont("georgia,times new roman,serif", size)
            else:
                self._lfonts[k] = pygame.font.SysFont("consolas", size)
        return self._lfonts[k]

    def draw(self, screen, ownership, selected_zone, hover_zone,
             ancient_seals, t: float, map_x: int, map_w: int,
             active_filter: str = "all", map_h: int = 0,
             event_log=None, dt: float = 0.016):
        """
        Main draw method with LOD-based rendering pipeline.

        LOD 0: Strategic view — region names, no zone borders
        LOD 1: Regional view — zones, names, ownership, seals
        LOD 2: Tactical view — structure icons, nature tint, roads
        LOD 3: Detail view — pixel-art buildings, corruption overlay
        LOD 4: Close-up — sub-districts, POIs, full VFX
        """
        cam   = self.cam
        map_y = cam.map_y
        if map_h <= 0:
            map_h = config.SCREEN_H - map_y
        clip  = pygame.Rect(map_x, map_y, map_w, map_h)

        # Update LOD
        self.lod.update(cam.zoom, dt)
        lod = self.lod.level
        feat = self.lod.features

        # ── Viewport da textura ───────────────────────────────────────────
        wl, wt = cam.s2w(map_x, map_y)
        wr, wb = cam.s2w(map_x + map_w, map_y + map_h)
        wl = max(0.0, wl); wt = max(0.0, wt)
        wr = min(float(WORLD_W), wr)
        wb = min(float(WORLD_H), wb)

        if wr <= wl or wb <= wt:
            pygame.draw.rect(screen, (48, 62, 92), clip)
            return

        tx0 = int(wl / WORLD_W * TEX_W)
        ty0 = int(wt / WORLD_H * TEX_H)
        tx1 = min(TEX_W, int(wr / WORLD_W * TEX_W) + 1)
        ty1 = min(TEX_H, int(wb / WORLD_H * TEX_H) + 1)
        src = pygame.Rect(tx0, ty0, max(1, tx1 - tx0), max(1, ty1 - ty0))

        sx0, sy0 = cam.w2s(wl, wt)
        dw = max(1, int((wr - wl) * cam.zoom))
        dh = max(1, int((wb - wt) * cam.zoom))

        # ── 1. Ocean fill ─────────────────────────────────────────────────
        screen.fill((48, 62, 92), clip)

        # ── 2. Base terrain texture ───────────────────────────────────────
        chunk = self.surf.subsurface(src)
        scaled_surf = pygame.transform.smoothscale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled_surf, (sx0, sy0))
        screen.set_clip(None)

        # ── 3. Ownership overlay (LOD 1+) ─────────────────────────────────
        if feat.show_ownership and ownership:
            self._draw_ownership(screen, ownership, clip)

        # ── 4. Nature tint overlay (LOD 2+) ───────────────────────────────
        if feat.show_nature_tint and self.nature_vfx:
            tint_surf = self.nature_vfx.build_nature_tint(ownership, self.gods)
            self.nature_vfx.draw_tint_viewport(screen, tint_surf, cam, clip)

        # ── 5. Corruption overlay (LOD 3+) ────────────────────────────────
        if feat.show_nature_vfx and self.nature_vfx:
            corr_surf = self.nature_vfx.build_corruption_overlay(
                ownership, self.gods, t)
            self.nature_vfx.draw_tint_viewport(screen, corr_surf, cam, clip)

        # ── 6. Event markers (LOD 1+) ─────────────────────────────────────
        if feat.show_events and event_log is not None and event_log.events:
            self._draw_event_markers(screen, event_log, t, clip)

        # ── 7. Roads between structures (LOD 2+) ──────────────────────────
        if feat.show_roads and self.structure_mgr:
            self._draw_roads(screen, ownership, t, clip)

        # ── 8. Hover overlay ──────────────────────────────────────────────
        if hover_zone and hover_zone != selected_zone:
            self._draw_zone_overlay_indexed(
                screen, hover_zone, clip,
                (*GOLD, 22), (*GOLD, 200), max(3, int(5 * cam.zoom))
            )

        # ── 9. Seal icons (LOD 1+) ───────────────────────────────────────
        if feat.show_seals and cam.zoom >= 0.40:
            self._draw_seal_icons(screen, ancient_seals, t, clip)

        # ── 10. Selection overlay ──────────────────────────────────────────
        if selected_zone:
            pa = int(70 + math.sin(t * 3) * 55)
            self._draw_zone_overlay_indexed(
                screen, selected_zone, clip,
                (*GOLD, pa // 2), (*GOLD, 220),
                max(3, int(3.5 * cam.zoom))
            )

        # ── 11. Structure icons (LOD 2) ───────────────────────────────────
        if feat.show_structure_icons and self.structure_mgr:
            self._draw_structure_icons(screen, ownership, clip, lod)

        # ── 12. Pixel-art buildings (LOD 3+) ──────────────────────────────
        if feat.show_buildings and self.structure_mgr:
            self._draw_buildings(screen, ownership, clip)

        # ── 13. Sub-district markers (LOD 4) ──────────────────────────────
        if feat.show_subdistricts and self.structure_mgr:
            self._draw_subdistricts(screen, ownership, t, clip)

        # ── 14. Owner badges (LOD 1-2) ────────────────────────────────────
        if feat.show_god_badges and 0.35 <= cam.zoom <= 2.5:
            self._draw_owner_badges(screen, ownership, clip)

        # ── 15. Labels ────────────────────────────────────────────────────
        if lod == 0:
            self._draw_region_labels(screen, clip, t)
        elif feat.show_zone_names:
            self._draw_labels(screen, ownership, clip, lod)

        # ── 16. Ambient VFX particles (LOD 3+) ───────────────────────────
        if feat.show_nature_vfx and self.nature_vfx:
            self.nature_vfx.draw_particles(screen, cam, clip)

        # ── 17. Filter overlay ────────────────────────────────────────────
        if active_filter != "all":
            self._draw_filter_overlay(screen, active_filter, selected_zone, clip)

        # ── 18. Compass rose ──────────────────────────────────────────────
        cx_ = map_x + map_w - self._compass.get_width() - scaled(12)
        cy_ = map_y + map_h - self._compass.get_height() - scaled(12)
        screen.blit(self._compass, (cx_, cy_))

        # ── 19. Pulsating border ──────────────────────────────────────────
        p = int(160 + math.sin(t * 1.8) * 50)
        gold_pulse = (p, int(p * 0.83), int(p * 0.38))
        pygame.draw.rect(screen, gold_pulse, clip, 2)

        # ── 20. LOD indicator ─────────────────────────────────────────────
        self._draw_lod_indicator(screen, clip, lod)

    # ── LOD indicator ─────────────────────────────────────────────────────
    def _draw_lod_indicator(self, screen, clip, lod):
        lod_names = ["STRATEGIC", "REGIONAL", "TACTICAL", "DETAIL", "CLOSE-UP"]
        name = lod_names[min(lod, 4)]
        font = self._lf(scaled(8), serif=False)
        txt = font.render(f"LOD {lod}: {name}", True, GOLD_DIM)
        x = clip.right - txt.get_width() - scaled(8)
        y = clip.top + scaled(4)
        bg = pygame.Surface((txt.get_width() + 6, txt.get_height() + 2), pygame.SRCALPHA)
        bg.fill((*UI_BG, 180))
        screen.blit(bg, (x - 3, y - 1))
        screen.blit(txt, (x, y))

    # ── Region labels (LOD 0) ─────────────────────────────────────────────
    def _draw_region_labels(self, screen, clip, t):
        cam = self.cam
        fsz = max(scaled(16), min(scaled(32), int(scaled(24) / max(0.2, cam.zoom))))
        font = self._lf(fsz, serif=True)
        small_font = self._lf(max(scaled(8), fsz // 2), serif=True)

        screen.set_clip(clip)
        for reg in self._region_data:
            sx, sy = cam.w2s(reg["cx"], reg["cy"])
            if not clip.collidepoint(sx, sy):
                continue

            col = NATURE_COLOR.get(reg["nature"], TXT)
            name = reg["name"]

            alpha = int(200 + math.sin(t * 0.8 + hash(reg["id"]) % 10) * 40)

            label = font.render(name, True, col)
            r = label.get_rect(center=(sx, sy))
            bg = pygame.Surface((r.width + scaled(16), r.height + scaled(8)), pygame.SRCALPHA)
            bg.fill((*UI_BG, min(200, alpha - 40)))
            screen.blit(bg, (r.x - scaled(8), r.y - scaled(4)))

            shadow = font.render(name, True, (0, 0, 0))
            screen.blit(shadow, r.move(2, 2))
            shadow2 = font.render(name, True, (30, 22, 10))
            screen.blit(shadow2, r.move(1, 1))
            screen.blit(label, r)

            nat_surf = small_font.render(reg["nature"].upper(), True, (*col[:3],))
            nr = nat_surf.get_rect(center=(sx, sy + fsz + scaled(4)))
            nat_shadow = small_font.render(reg["nature"].upper(), True, (0, 0, 0))
            screen.blit(nat_shadow, nr.move(1, 1))
            screen.blit(nat_surf, nr)

        screen.set_clip(None)

    # ── Event markers ─────────────────────────────────────────────────────
    def _draw_event_markers(self, screen, event_log: EventLog, t: float,
                             clip: pygame.Rect):
        cam  = self.cam
        surf = self._marker_surf
        surf.fill((0, 0, 0, 0), clip)

        PULSE  = {"critical": 4.5, "high": 2.5, "medium": 0.0, "low": 0.0}
        R_BASE = scaled(6)
        OFFSET = scaled(14)

        for zone in self.zones.values():
            if zone.ancient_seal:
                continue
            ev = event_log.worst_for_zone(zone.zone_id)
            if ev is None:
                continue

            sx, sy = cam.w2s(*zone.centroid)
            mx = sx + OFFSET
            my = sy - OFFSET
            if not clip.collidepoint(mx, my):
                continue

            lx, ly = mx, my
            col = SEVERITY_COLOR[ev.severity]
            ps  = PULSE.get(ev.severity, 0.0)
            if ps > 0:
                a_fill   = int(140 + math.sin(t * ps) * 80)
                a_border = int(220 + math.sin(t * ps + 0.8) * 35)
            else:
                a_fill, a_border = 130, 200

            r     = R_BASE
            shape = EVENT_VFX.get(ev.type, {}).get("shape", "circle")
            vc    = EVENT_VFX.get(ev.type, {}).get("color", col)

            if shape == "diamond":
                pts = [(lx, ly - r), (lx + r, ly), (lx, ly + r), (lx - r, ly)]
                pygame.draw.polygon(surf, (*col, a_fill),   pts)
                pygame.draw.polygon(surf, (*vc,  a_border), pts, max(1, r // 3))
            elif shape == "triangle":
                pts = [(lx, ly - r), (lx + r, ly + r), (lx - r, ly + r)]
                pygame.draw.polygon(surf, (*col, a_fill),   pts)
                pygame.draw.polygon(surf, (*vc,  a_border), pts, max(1, r // 3))
            elif shape == "square":
                sr = pygame.Rect(lx - r, ly - r, r * 2, r * 2)
                pygame.draw.rect(surf, (*col, a_fill),   sr, border_radius=2)
                pygame.draw.rect(surf, (*vc,  a_border), sr, max(1, r // 3),
                                 border_radius=2)
            else:
                pygame.draw.circle(surf, (*col, a_fill),   (lx, ly), r)
                pygame.draw.circle(surf, (*vc,  a_border), (lx, ly), r,
                                   max(1, r // 3))

            if ev.severity in ("critical", "high"):
                pygame.draw.circle(surf, (*vc, min(255, a_border)),
                                   (lx, ly), max(2, r // 3))

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Structure icons (LOD 2) ───────────────────────────────────────────
    def _draw_structure_icons(self, screen, ownership, clip, lod):
        cam = self.cam
        surf = self._struct_surf
        surf.fill((0, 0, 0, 0), clip)

        min_importance = 3 if lod <= 2 else 2 if lod == 3 else 1

        for zone in self.zones.values():
            structs = self.structure_mgr.get_zone_structures(
                zone.zone_id, min_importance=min_importance)
            if not structs:
                continue

            for st in structs:
                sx, sy = cam.w2s(st.world_x, st.world_y)
                if not clip.collidepoint(sx, sy):
                    continue

                icon = self.structure_mgr.get_icon(st.struct_type)
                if icon:
                    isz = icon.get_width()
                    draw_sz = max(6, int(isz * min(2.0, cam.zoom)))
                    if draw_sz != isz:
                        icon = pygame.transform.smoothscale(icon, (draw_sz, draw_sz))
                    surf.blit(icon, (sx - draw_sz // 2, sy - draw_sz // 2))

                if st.importance >= 3 and cam.zoom >= 1.2:
                    fsz_l = max(scaled(7), min(scaled(11), int(scaled(9) * cam.zoom)))
                    font = self._lf(fsz_l, serif=True)
                    cfg = STRUCTURE_TYPES.get(st.struct_type, {})
                    col = cfg.get("color", TXT_DIM)
                    txt_s = font.render(st.name, True, col)
                    txt_r = txt_s.get_rect(center=(sx, sy + draw_sz // 2 + fsz_l))
                    bg = pygame.Surface(
                        (txt_r.width + 4, txt_r.height + 2), pygame.SRCALPHA)
                    bg.fill((*UI_BG, 160))
                    surf.blit(bg, (txt_r.x - 2, txt_r.y - 1))
                    shadow = font.render(st.name, True, (0, 0, 0))
                    surf.blit(shadow, txt_r.move(1, 1))
                    surf.blit(txt_s, txt_r)

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Pixel-art buildings (LOD 3+) ──────────────────────────────────────
    def _draw_buildings(self, screen, ownership, clip):
        cam = self.cam
        zoom = cam.zoom

        screen.set_clip(clip)
        for zone in self.zones.values():
            structs = self.structure_mgr.get_zone_structures(zone.zone_id)
            sprites = self.structure_mgr._sprites.get(zone.zone_id, {})

            for st in structs:
                sx, sy = cam.w2s(st.world_x, st.world_y)
                if not clip.collidepoint(sx, sy):
                    continue

                sprite = sprites.get(st.name)
                if not sprite:
                    continue

                base_sz = sprite.get_width()
                draw_sz = max(6, int(base_sz * zoom * 0.8))
                if draw_sz != base_sz:
                    drawn = pygame.transform.scale(sprite, (draw_sz, draw_sz))
                else:
                    drawn = sprite

                screen.blit(drawn, (sx - draw_sz // 2, sy - draw_sz // 2))

                fsz_l = max(scaled(6), min(scaled(10), int(scaled(8) * zoom * 0.5)))
                font = self._lf(fsz_l, serif=True)
                cfg = STRUCTURE_TYPES.get(st.struct_type, {})
                col = cfg.get("color", TXT_DIM)

                txt_s = font.render(st.name, True, col)
                txt_r = txt_s.get_rect(center=(sx, sy + draw_sz // 2 + fsz_l + 2))
                shadow = font.render(st.name, True, (0, 0, 0))
                screen.blit(shadow, txt_r.move(1, 1))
                screen.blit(txt_s, txt_r)

        screen.set_clip(None)

    # ── Roads (LOD 2+) ────────────────────────────────────────────────────
    def _draw_roads(self, screen, ownership, t, clip):
        cam = self.cam
        surf = self._road_surf
        surf.fill((0, 0, 0, 0), clip)

        road_col = (120, 105, 75, 80)

        for zone in self.zones.values():
            structs = self.structure_mgr.get_zone_structures(
                zone.zone_id, min_importance=2)
            if len(structs) < 2:
                continue

            cx, cy = zone.centroid
            scx, scy = cam.w2s(cx, cy)

            for st in structs:
                sx, sy = cam.w2s(st.world_x, st.world_y)
                if not clip.collidepoint(sx, sy) and not clip.collidepoint(scx, scy):
                    continue

                dx = sx - scx
                dy = sy - scy
                dist = math.hypot(dx, dy)
                if dist < 3:
                    continue

                dash_len = max(3, int(6 * cam.zoom))
                gap_len = max(2, int(4 * cam.zoom))
                steps = int(dist / max(1, dash_len + gap_len))

                for i in range(steps):
                    frac = i / max(1, steps)
                    frac2 = min(1.0, (i + 0.6) / max(1, steps))
                    px1 = int(scx + dx * frac)
                    py1 = int(scy + dy * frac)
                    px2 = int(scx + dx * frac2)
                    py2 = int(scy + dy * frac2)
                    pygame.draw.line(surf, road_col, (px1, py1), (px2, py2),
                                    max(1, int(1.5 * cam.zoom)))

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Sub-districts (LOD 4) ─────────────────────────────────────────────
    def _draw_subdistricts(self, screen, ownership, t, clip):
        cam = self.cam
        surf = self._subdist_surf
        surf.fill((0, 0, 0, 0), clip)

        for zone in self.zones.values():
            subs = self.structure_mgr.get_subdistricts(zone.zone_id)
            if not subs:
                continue

            for sub in subs:
                sx, sy = cam.w2s(sub.world_x, sub.world_y)
                if not clip.collidepoint(sx, sy):
                    continue

                r = int(sub.radius * cam.zoom)
                if r < 5:
                    continue

                nc = NATURE_COLOR.get(zone.base_nature, TXT_DIM)

                segments = max(12, r // 2)
                for i in range(0, segments, 2):
                    a1 = (2 * math.pi * i) / segments
                    a2 = (2 * math.pi * (i + 1)) / segments
                    p1 = (int(sx + math.cos(a1) * r), int(sy + math.sin(a1) * r))
                    p2 = (int(sx + math.cos(a2) * r), int(sy + math.sin(a2) * r))
                    pygame.draw.line(surf, (*nc, 100), p1, p2, 1)

                pygame.draw.circle(surf, (*nc, 140), (sx, sy), max(2, r // 10))

                fsz_l = max(scaled(6), min(scaled(10), int(scaled(8) * cam.zoom * 0.4)))
                font = self._lf(fsz_l, serif=True)
                txt_s = font.render(sub.name, True, (*nc,))
                txt_r = txt_s.get_rect(center=(sx, sy - r - fsz_l))

                bg = pygame.Surface(
                    (txt_r.width + 4, txt_r.height + 2), pygame.SRCALPHA)
                bg.fill((*UI_BG, 140))
                surf.blit(bg, (txt_r.x - 2, txt_r.y - 1))

                shadow = font.render(sub.name, True, (0, 0, 0))
                surf.blit(shadow, txt_r.move(1, 1))
                surf.blit(txt_s, txt_r)

                if cam.zoom >= 4.5 and sub.description:
                    dsz = max(scaled(5), fsz_l - 2)
                    dfont = self._lf(dsz, serif=True)
                    dtxt = dfont.render(sub.description, True, TXT_DIM)
                    dr = dtxt.get_rect(center=(sx, sy + r + dsz + 2))
                    dsh = dfont.render(sub.description, True, (0, 0, 0))
                    surf.blit(dsh, dr.move(1, 1))
                    surf.blit(dtxt, dr)

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Zone overlay (hover / selection) ──────────────────────────────────
    def _draw_zone_overlay_indexed(self, screen, zone, clip,
                                    fill_col, border_col, border_w):
        try:
            zone_i = self.zone_list.index(zone)
        except ValueError:
            return

        cam   = self.cam
        map_y = cam.map_y
        map_h = clip.height

        wl, wt = cam.s2w(clip.x, map_y)
        wr, wb = cam.s2w(clip.x + clip.width, map_y + map_h)
        wl = max(0.0, wl); wt = max(0.0, wt)
        wr = min(float(WORLD_W), wr)
        wb = min(float(WORLD_H), wb)
        if wr <= wl or wb <= wt:
            return

        tx0 = int(wl / WORLD_W * TEX_W)
        ty0 = int(wt / WORLD_H * TEX_H)
        tx1 = min(TEX_W, int(wr / WORLD_W * TEX_W) + 1)
        ty1 = min(TEX_H, int(wb / WORLD_H * TEX_H) + 1)
        vw, vh = tx1 - tx0, ty1 - ty0
        if vw <= 0 or vh <= 0:
            return

        bw_key   = int(border_w)
        mask_key = (zone_i, bw_key)
        if mask_key not in self._mask_cache:
            mask    = (self.zone_idx == zone_i)
            eroded  = binary_erosion(mask,  iterations=max(1, bw_key))
            dilated = binary_dilation(mask, iterations=max(1, bw_key // 2 + 1))
            border  = dilated & ~eroded
            self._mask_cache[mask_key] = (mask.T.copy(), border.T.copy())

        mask_t, border_t = self._mask_cache[mask_key]

        if self._zone_work_surf is None:
            self._zone_work_surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)

        surf = self._zone_work_surf
        surf.fill((0, 0, 0, 0), pygame.Rect(tx0, ty0, vw, vh))

        vp_mask   = mask_t  [tx0:tx1, ty0:ty1]
        vp_border = border_t[tx0:tx1, ty0:ty1]

        fa = fill_col[3]   if len(fill_col)   > 3 else 40
        ba = border_col[3] if len(border_col) > 3 else 200

        rgb_arr   = pygame.surfarray.pixels3d(surf)
        alpha_arr = pygame.surfarray.pixels_alpha(surf)

        sub_rgb   = rgb_arr  [tx0:tx1, ty0:ty1]
        sub_alpha = alpha_arr[tx0:tx1, ty0:ty1]

        sub_rgb  [vp_mask,   0] = fill_col[0]
        sub_rgb  [vp_mask,   1] = fill_col[1]
        sub_rgb  [vp_mask,   2] = fill_col[2]
        sub_alpha[vp_mask]      = fa

        sub_rgb  [vp_border, 0] = border_col[0]
        sub_rgb  [vp_border, 1] = border_col[1]
        sub_rgb  [vp_border, 2] = border_col[2]
        sub_alpha[vp_border]    = ba

        del rgb_arr, alpha_arr

        src_r  = pygame.Rect(tx0, ty0, vw, vh)
        sx0_, sy0_ = cam.w2s(wl, wt)
        dw_ = max(1, int((wr - wl) * cam.zoom))
        dh_ = max(1, int((wb - wt) * cam.zoom))

        chunk_   = surf.subsurface(src_r)
        scaled_s = pygame.transform.smoothscale(chunk_, (dw_, dh_))
        screen.set_clip(clip)
        screen.blit(scaled_s, (sx0_, sy0_))
        screen.set_clip(None)

    # ── Ownership ─────────────────────────────────────────────────────────
    def _draw_ownership(self, screen, ownership, clip):
        key = tuple(sorted(ownership.items()))
        if key != self._ownership_key or self._ownership_surf is None:
            self._ownership_surf = self._build_ownership_texture(ownership)
            self._ownership_key  = key

        cam   = self.cam
        map_y = cam.map_y
        map_h = clip.height

        wl, wt = cam.s2w(clip.x, map_y)
        wr, wb = cam.s2w(clip.x + clip.width, map_y + map_h)
        wl = max(0.0, wl); wt = max(0.0, wt)
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

        chunk  = self._ownership_surf.subsurface(src)
        scaled_ow = pygame.transform.smoothscale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled_ow, (sx0, sy0))
        screen.set_clip(None)

    def _build_ownership_texture(self, ownership) -> pygame.Surface:
        surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        rgb_arr   = pygame.surfarray.pixels3d(surf)
        alpha_arr = pygame.surfarray.pixels_alpha(surf)
        idx_t = self.zone_idx.T

        for i, zone in enumerate(self.zone_list):
            gid = ownership.get(zone.zone_id)
            if not gid:
                continue
            god = self.gods.get(gid)
            if not god:
                continue
            r, g, b = god.rgb()
            mask = (idx_t == i)
            rgb_arr[mask, 0] = r
            rgb_arr[mask, 1] = g
            rgb_arr[mask, 2] = b
            alpha_arr[mask]  = 52

        idx = self.zone_idx
        alpha_t = alpha_arr.T

        h_diff = (idx[:, :-1] != idx[:, 1:])
        v_diff = (idx[:-1, :] != idx[1:, :])

        h_both = h_diff & (alpha_t[:, :-1] > 0) & (alpha_t[:, 1:] > 0)
        v_both = v_diff & (alpha_t[:-1, :] > 0) & (alpha_t[1:, :] > 0)

        alpha_t[:, :-1][h_both] = 180
        alpha_t[:, 1:][h_both]  = 180
        alpha_t[:-1, :][v_both] = 180
        alpha_t[1:, :][v_both]  = 180

        del rgb_arr, alpha_arr
        return surf

    # ── Seal icons ────────────────────────────────────────────────────────
    def _draw_seal_icons(self, screen, ancient_seals, t, clip):
        cam  = self.cam
        surf = self._seal_surf
        surf.fill((0, 0, 0, 0), clip)

        for zone in self.zones.values():
            if not zone.ancient_seal:
                continue
            sd     = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            col    = SEAL_COLOR.get(status, (120, 35, 210))

            sx, sy = cam.w2s(*zone.centroid)
            if not clip.collidepoint(sx, sy):
                continue

            r = max(7, min(22, int(16 * cam.zoom)))

            pulse_speed = {"sleeping": 1.2, "stirring": 2.2, "awakened": 3.5, "broken": 0.5}
            ps = pulse_speed.get(status, 1.5)
            a_outer = int(60  + math.sin(t * ps) * 40)
            a_inner = int(140 + math.sin(t * ps + 1.0) * 70)
            a_lines = int(100 + math.sin(t * ps + 0.5) * 50)

            pygame.draw.circle(surf, (*col, a_outer), (sx, sy), r)
            pygame.draw.circle(surf, (*col, a_inner), (sx, sy), max(3, r // 2), max(1, r // 5))
            for angle_deg in [45, 135]:
                angle = math.radians(angle_deg)
                dx = math.cos(angle) * r * 0.75
                dy = math.sin(angle) * r * 0.75
                pygame.draw.line(surf, (*col, a_lines),
                                 (int(sx - dx), int(sy - dy)),
                                 (int(sx + dx), int(sy + dy)),
                                 max(1, r // 6))
            pygame.draw.circle(surf, (*col, min(255, a_inner + 40)), (sx, sy), max(2, r // 4))

            # Crack indicators
            crack = sd.get("crack_level", 0)
            if crack > 0:
                for ci in range(crack):
                    ca = math.radians(360 / 5 * ci - 90)
                    cx_ = int(sx + math.cos(ca) * (r + 4))
                    cy_ = int(sy + math.sin(ca) * (r + 4))
                    pygame.draw.line(surf, (*CRIMSON, 200),
                                    (cx_, cy_), (cx_ + 2, cy_ + 3), 2)

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Owner badges ──────────────────────────────────────────────────────
    def _draw_owner_badges(self, screen, ownership, clip):
        cam  = self.cam
        surf = self._badge_surf
        surf.fill((0, 0, 0, 0), clip)

        badge_r   = max(8, min(18, int(13 * cam.zoom)))
        font_size = max(7, min(14, int(10 * cam.zoom)))
        font      = self._lf(font_size, serif=False)

        for zone in self.zones.values():
            gid = ownership.get(zone.zone_id)
            if not gid:
                continue
            god = self.gods.get(gid)
            if not god:
                continue

            sx, sy = cam.w2s(*zone.centroid)
            badge_y = sy + badge_r + scaled(4)
            if not clip.collidepoint(sx, badge_y):
                continue

            r, g, b = god.rgb()
            initials = "".join(w[0].upper() for w in god.god_name.split()[:2])

            pygame.draw.circle(surf, (r, g, b, 160), (sx, badge_y), badge_r)
            pygame.draw.circle(surf, (*GOLD, 200), (sx, badge_y), badge_r, max(1, badge_r // 5))

            txt_surf = font.render(initials, True, (240, 235, 215))
            txt_rect = txt_surf.get_rect(center=(sx, badge_y))
            surf.blit(txt_surf, txt_rect)

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Labels ────────────────────────────────────────────────────────────
    def _draw_labels(self, screen, ownership, clip: pygame.Rect, lod: int = 1):
        cam = self.cam

        fsz  = max(scaled(9), min(scaled(20), int(scaled(14) * cam.zoom)))
        font = self._lf(fsz, serif=True)

        screen.set_clip(clip)
        for zone in self.zones.values():
            sx, sy = cam.w2s(*zone.centroid)
            if not clip.collidepoint(sx, sy):
                continue

            gid = ownership.get(zone.zone_id)
            col = TXT if gid else (175, 165, 145)

            label = font.render(zone.zone_name, True, col)
            shadow_dark  = font.render(zone.zone_name, True, (0, 0, 0))
            shadow_sepia = font.render(zone.zone_name, True, (40, 30, 15))
            r = label.get_rect(center=(sx, sy))

            bg = pygame.Surface((r.width + scaled(10), r.height + scaled(4)), pygame.SRCALPHA)
            bg.fill((*UI_BG, 130))
            screen.blit(bg, (r.x - scaled(5), r.y - scaled(2)))

            screen.blit(shadow_dark,  r.move(2, 2))
            screen.blit(shadow_sepia, r.move(1, 1))
            screen.blit(label, r)

            if gid and cam.zoom >= 0.85:
                god = self.gods.get(gid)
                if god:
                    gf  = self._lf(max(scaled(7), fsz - scaled(3)), serif=True)
                    gs  = gf.render(god.god_name, True, god.rgb())
                    gsh = gf.render(god.god_name, True, (0, 0, 0))
                    gr  = gs.get_rect(center=(sx, sy + fsz + scaled(5)))
                    screen.blit(gsh, gr.move(1, 1))
                    screen.blit(gs,  gr)

            if lod >= 2 or cam.zoom >= 0.55:
                nf  = self._lf(max(scaled(7), fsz - scaled(4)), serif=True)
                nc  = NATURE_COLOR.get(zone.base_nature, TXT_DIM)
                ns  = nf.render(zone.base_nature.upper(), True, nc)
                nsh = nf.render(zone.base_nature.upper(), True, (0, 0, 0))
                nr  = ns.get_rect(center=(sx, sy - fsz - scaled(4)))
                screen.blit(nsh, nr.move(1, 1))
                screen.blit(ns,  nr)

            # Lore snippet at LOD 3+
            if lod >= 3 and zone.lore and cam.zoom >= 2.5:
                lf = self._lf(max(scaled(6), fsz - scaled(5)), serif=True)
                lore_text = zone.lore[:60] + ("..." if len(zone.lore) > 60 else "")
                ls = lf.render(lore_text, True, TXT_MUTED)
                lr = ls.get_rect(center=(sx, sy + fsz * 2 + scaled(12)))
                lsh = lf.render(lore_text, True, (0, 0, 0))
                screen.blit(lsh, lr.move(1, 1))
                screen.blit(ls, lr)

            # Origin star for Caleb's birthplace
            if zone.zone_id == "slum_district":
                star_r = max(4, int(8 * cam.zoom))
                star_y = sy - fsz - scaled(12) - star_r
                pts = []
                for i_s in range(10):
                    a_s = math.radians(i_s * 36 - 90)
                    sr = star_r if i_s % 2 == 0 else star_r * 0.4
                    pts.append((sx + math.cos(a_s) * sr, star_y + math.sin(a_s) * sr))
                pygame.draw.polygon(screen, GOLD, pts)

        screen.set_clip(None)

    # ── Filter overlay ────────────────────────────────────────────────────
    def _draw_filter_overlay(self, screen, active_filter: str,
                              selected_zone, clip: pygame.Rect):
        cam   = self.cam
        map_y = cam.map_y
        map_h = clip.height

        sel_id = None
        if selected_zone:
            try:
                sel_id = self.zone_list.index(selected_zone)
            except ValueError:
                pass

        filter_key = (active_filter, sel_id)
        if filter_key != self._filter_key or self._filter_surf is None:
            surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            rgb_arr   = pygame.surfarray.pixels3d(surf)
            alpha_arr = pygame.surfarray.pixels_alpha(surf)

            for i, zone in enumerate(self.zone_list):
                if zone.base_nature == active_filter:
                    continue
                if i == sel_id:
                    continue
                mask_t = (self.zone_idx == i).T
                rgb_arr[mask_t, 0] = 12
                rgb_arr[mask_t, 1] = 8
                rgb_arr[mask_t, 2] = 4
                alpha_arr[mask_t]  = 165

            del rgb_arr, alpha_arr
            self._filter_surf = surf
            self._filter_key  = filter_key

        wl, wt = cam.s2w(clip.x, map_y)
        wr, wb = cam.s2w(clip.x + clip.width, map_y + map_h)
        wl = max(0.0, wl); wt = max(0.0, wt)
        wr = min(float(WORLD_W), wr)
        wb = min(float(WORLD_H), wb)
        if wr <= wl or wb <= wt:
            return

        tx0 = int(wl / WORLD_W * TEX_W)
        ty0 = int(wt / WORLD_H * TEX_H)
        tx1 = min(TEX_W, int(wr / WORLD_W * TEX_W) + 1)
        ty1 = min(TEX_H, int(wb / WORLD_H * TEX_H) + 1)
        src  = pygame.Rect(tx0, ty0, max(1, tx1 - tx0), max(1, ty1 - ty0))
        sx0_, sy0_ = cam.w2s(wl, wt)
        dw_ = max(1, int((wr - wl) * cam.zoom))
        dh_ = max(1, int((wb - wt) * cam.zoom))

        chunk = self._filter_surf.subsurface(src)
        scaled_f = pygame.transform.smoothscale(chunk, (dw_, dh_))
        screen.set_clip(clip)
        screen.blit(scaled_f, (sx0_, sy0_))
        screen.set_clip(None)


# ── Rosa dos Ventos ───────────────────────────────────────────────────────────
def _build_compass(r: int) -> pygame.Surface:
    sz = r * 2 + 6
    s  = pygame.Surface((sz, sz), pygame.SRCALPHA)
    cx = cy = sz // 2

    GOLD_C  = (210, 175,  80, 220)
    GOLD_D  = (130, 105,  25, 180)
    DARK_C  = ( 18,  12,   6, 215)
    RING_C  = (100,  78,  28, 120)

    pygame.draw.circle(s, RING_C, (cx, cy), r, 2)

    for adeg, length, col in [
        (0,   r * 0.94, GOLD_C),
        (180, r * 0.80, GOLD_D),
        (90,  r * 0.72, GOLD_D),
        (270, r * 0.72, GOLD_D),
    ]:
        a   = math.radians(adeg - 90)
        tip = (cx + math.cos(a) * length, cy + math.sin(a) * length)
        la  = a + math.pi / 2
        bw  = r * 0.16
        lp  = (cx + math.cos(la) * bw, cy + math.sin(la) * bw)
        rp  = (cx - math.cos(la) * bw, cy - math.sin(la) * bw)
        pygame.draw.polygon(s, col, [tip, lp, rp])
        mid = (cx + math.cos(a) * length * 0.28, cy + math.sin(a) * length * 0.28)
        pygame.draw.polygon(s, DARK_C, [tip, mid, lp])

    for adeg in [45, 135, 225, 315]:
        a   = math.radians(adeg - 90)
        tip = (cx + math.cos(a) * r * 0.50, cy + math.sin(a) * r * 0.50)
        la  = a + math.pi / 2
        bw  = r * 0.08
        lp  = (cx + math.cos(la) * bw, cy + math.sin(la) * bw)
        rp  = (cx - math.cos(la) * bw, cy - math.sin(la) * bw)
        pygame.draw.polygon(s, GOLD_D, [tip, lp, rp])

    pygame.draw.circle(s, DARK_C, (cx, cy), int(r * 0.16))
    pygame.draw.circle(s, GOLD_C, (cx, cy), int(r * 0.10))
    pygame.draw.circle(s, (240, 235, 215, 200), (cx, cy), int(r * 0.05))
    return s
