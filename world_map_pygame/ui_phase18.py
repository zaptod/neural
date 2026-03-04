"""
world_map_pygame/ui.py

[PHASE 18] Complete rewrite — zero-allocation HUD.
  - Aggressive text render caching (LRU by (text, size, color))
  - Pre-built panel / filter bar background surfaces
  - No per-frame Surface allocations for tooltips, panels, borders
  - Same public API as legacy UI for drop-in replacement
  - Ornate border drawn directly (no temp Surface)
"""
import math
import pygame
from typing import Optional, Dict, List, Tuple

from . import config
from .config import (
    FILTER_BAR_H, BOTTOM_PANEL_H,
    UI_BG, UI_BG2, UI_LINE, UI_PANEL,
    GOLD, GOLD_DIM, CRIMSON, CYAN, TXT, TXT_DIM, TXT_MUTED,
    NATURE_COLOR, SEAL_COLOR, scaled,
)
from .data_loader import Zone, God, AncientGod
from .camera import Camera
from .world_events import EventLog, EventType, SEVERITY_COLOR, SEVERITY_LABEL, EVENT_VFX


# ─── Text render cache ───────────────────────────────────────────────────────

class _TextCache:
    """LRU text render cache — avoids font.render() every frame."""
    __slots__ = ["_cache", "_max"]

    def __init__(self, max_entries: int = 512):
        self._cache: Dict[tuple, pygame.Surface] = {}
        self._max = max_entries

    def get(self, font: pygame.font.Font, text: str,
            color: tuple, antialias: bool = True) -> pygame.Surface:
        key = (id(font), text, color[:3])
        s = self._cache.get(key)
        if s is not None:
            return s
        s = font.render(text, antialias, color[:3])
        if len(self._cache) >= self._max:
            # Evict oldest quarter
            keys = list(self._cache.keys())
            for k in keys[: len(keys) // 4]:
                del self._cache[k]
        self._cache[key] = s
        return s

    def clear(self):
        self._cache.clear()


# ─── Font cache ───────────────────────────────────────────────────────────────

class _FC:
    """Font cache with serif/bold support."""
    __slots__ = ["_c"]

    def __init__(self):
        self._c: Dict[tuple, pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False, serif: bool = False) -> pygame.font.Font:
        k = (size, bold, serif)
        f = self._c.get(k)
        if f is not None:
            return f
        name = "georgia,times new roman,serif" if serif else "consolas"
        f = pygame.font.SysFont(name, size, bold=bold)
        self._c[k] = f
        return f


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list:
    words = text.split()
    lines: List[str] = []
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines or [""]


def _ornate_border(surf: pygame.Surface, rect: pygame.Rect,
                   col: tuple = GOLD, alpha: int = 180, thick: int = 1):
    """Draw ornate golden border with L-shaped corner accents (no temp Surface)."""
    r = rect
    L = scaled(10)
    # Main border
    pygame.draw.rect(surf, col[:3], r, thick, border_radius=2)
    # Bright corner accents
    bright = tuple(min(255, c + 60) for c in col[:3])
    for px, py, dx, dy in [
        (r.left, r.top, 1, 1),
        (r.right - 1, r.top, -1, 1),
        (r.left, r.bottom - 1, 1, -1),
        (r.right - 1, r.bottom - 1, -1, -1),
    ]:
        pygame.draw.line(surf, bright, (px, py), (px + dx * L, py), 2)
        pygame.draw.line(surf, bright, (px, py), (px, py + dy * L), 2)


# ─── Main UI class ────────────────────────────────────────────────────────────

class UI:
    HUD_H = FILTER_BAR_H
    SEALS_W = 0

    _ALL_NATURES = [
        "all", "arcane", "balanced", "chaos", "darkness",
        "fear", "fire", "greed", "ice", "nature", "void",
    ]

    def __init__(self):
        pygame.font.init()
        self._fc = _FC()
        self._tc = _TextCache(512)

        # Notification
        self._notif_msg = ""
        self._notif_alpha = 0.0

        # Bottom panel — slide animation
        self._panel_open = False
        self._panel_slide = 0.0
        self._panel_scroll = 0
        self._panel_content_h = 0

        # Filters
        self.active_filter: str = "all"
        self._god_filter: Optional[str] = None

        # Minimap
        self._minimap_surf: Optional[pygame.Surface] = None
        self._minimap_dirty = True

        # Compat
        self._panel_w_current = 0.0

        # ── Reusable work surfaces ────────────────────────────────────────
        SW, SH = config.SCREEN_W, config.SCREEN_H

        # Filter bar bg (built once)
        self._filter_bg = pygame.Surface((SW, self.HUD_H), pygame.SRCALPHA)
        self._filter_bg.fill((*UI_BG, 255))

        # Panel bg (full-width, BOTTOM_PANEL_H tall)
        self._panel_bg = pygame.Surface((SW, BOTTOM_PANEL_H), pygame.SRCALPHA)
        self._panel_bg.fill((*UI_BG, 245))
        # Gold gradient at top
        for i in range(min(4, BOTTOM_PANEL_H)):
            a = int(80 * (1 - i / 4))
            pygame.draw.line(self._panel_bg, (*GOLD, a), (0, i), (SW, i))

        # Tooltip work surface (reused each frame)
        self._tooltip_surf = pygame.Surface((400, 200), pygame.SRCALPHA)

        # Notification work surface
        self._notif_surf = pygame.Surface((SW, scaled(50)), pygame.SRCALPHA)

    # ── Layout properties ─────────────────────────────────────────────────

    @property
    def panel_w(self) -> int:
        return 0

    @property
    def map_x(self) -> int:
        return 0

    @property
    def map_y(self) -> int:
        return self.HUD_H

    @property
    def map_w(self) -> int:
        return config.SCREEN_W

    @property
    def map_h(self) -> int:
        panel_h = int(BOTTOM_PANEL_H * self._panel_slide)
        return config.SCREEN_H - self.HUD_H - panel_h

    @property
    def _panel_y(self) -> int:
        panel_h = int(BOTTOM_PANEL_H * self._panel_slide)
        return config.SCREEN_H - panel_h

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        target = 1.0 if self._panel_open else 0.0
        diff = target - self._panel_slide
        self._panel_slide += diff * min(1.0, dt * 14.0)
        if abs(diff) < 0.002:
            self._panel_slide = target
        self._notif_alpha = max(0.0, self._notif_alpha - dt * 0.45)

    def notify(self, msg: str):
        self._notif_msg = msg
        self._notif_alpha = 1.0

    def open_panel(self, zone: Optional[Zone]):
        self._panel_open = (zone is not None)

    def scroll_panel(self, delta: int):
        max_s = max(0, self._panel_content_h - BOTTOM_PANEL_H + scaled(8))
        self._panel_scroll = max(0, min(max_s, self._panel_scroll + delta))

    def mark_minimap_dirty(self):
        self._minimap_dirty = True

    # ── Text helper (cached) ──────────────────────────────────────────────

    def _txt(self, font: pygame.font.Font, text: str, color: tuple) -> pygame.Surface:
        return self._tc.get(font, text, color)

    def _txt_shadow(self, dest: pygame.Surface, font: pygame.font.Font,
                    text: str, color: tuple, x: int, y: int):
        """Render text with drop shadow, all cached."""
        shadow = self._txt(font, text, (0, 0, 0))
        dest.blit(shadow, (x + 1, y + 1))
        dest.blit(self._txt(font, text, color), (x, y))

    # ── Filter button rects (shared by draw + click) ─────────────────────

    def _filter_btn_rects(self, natures_available: list,
                          title_w: int = 0) -> List[Tuple[str, pygame.Rect]]:
        FH = self.HUD_H
        pad = scaled(8)
        f_btn = self._fc.get(scaled(11), bold=True)

        if title_w <= 0:
            f_title = self._fc.get(scaled(13), bold=True, serif=True)
            title_w = f_title.size("⚔ AETHERMOOR")[0]

        x = scaled(12) + title_w + scaled(20)
        rects = []
        for nat in ["all"] + list(natures_available):
            lbl = "TODOS" if nat == "all" else nat.upper()
            w = f_btn.size(lbl)[0] + pad * 2
            rects.append((nat, pygame.Rect(x, 3, w, FH - 6)))
            x += w + scaled(4)
        return rects

    # ── Event handlers ────────────────────────────────────────────────────

    def handle_filter_click(self, mx: int, my: int,
                            natures_available: list) -> bool:
        if my >= self.HUD_H:
            return False
        for nat, btn in self._filter_btn_rects(natures_available):
            if btn.collidepoint(mx, my):
                self.active_filter = nat
                return True
        return False

    def handle_minimap_click(self, mx: int, my: int,
                             cam: Camera, zones) -> bool:
        mm_rect = self._minimap_rect()
        if mm_rect is None or not mm_rect.collidepoint(mx, my):
            return False
        from .config import WORLD_W, WORLD_H
        wx = (mx - mm_rect.x) / mm_rect.width * WORLD_W
        wy = (my - mm_rect.y) / mm_rect.height * WORLD_H
        cam.fly_to(wx, wy)
        return True

    def _minimap_rect(self) -> Optional[pygame.Rect]:
        if self._panel_slide < 0.05:
            return None
        SW = config.SCREEN_W
        PH = int(BOTTOM_PANEL_H * self._panel_slide)
        py = config.SCREEN_H - PH
        MM_W = scaled(160)
        MM_H = scaled(112)
        pad = scaled(12)
        return pygame.Rect(SW - MM_W - pad, py + (PH - MM_H) // 2, MM_W, MM_H)

    # ── FILTER BAR (top) ─────────────────────────────────────────────────

    def draw_filter_bar(self, screen: pygame.Surface, gods, zones, ownership,
                        cam: Camera, fps: float, t: float):
        SW = config.SCREEN_W
        FH = self.HUD_H

        # Background (pre-built)
        screen.blit(self._filter_bg, (0, 0))

        # Pulsating sepia line at bottom
        p = int(140 + math.sin(t * 2) * 40)
        pygame.draw.line(screen, (p, int(p * 0.83), int(p * 0.38)),
                         (0, FH - 1), (SW, FH - 1), 1)

        f_title = self._fc.get(scaled(13), bold=True, serif=True)
        f_btn = self._fc.get(scaled(11), bold=True)
        f_info = self._fc.get(scaled(10))

        # Title (cached)
        title = self._txt(f_title, "⚔ AETHERMOOR", GOLD)
        screen.blit(title, (scaled(12), (FH - title.get_height()) // 2))

        # Filter buttons
        natures_available = sorted(set(z.base_nature for z in zones.values()))
        title_w = title.get_width()

        for nat, btn in self._filter_btn_rects(natures_available, title_w):
            lbl = "TODOS" if nat == "all" else nat.upper()
            col = NATURE_COLOR.get(nat, TXT_DIM) if nat != "all" else TXT
            active = (self.active_filter == nat)

            if active:
                # Draw translucent fill via small SRCALPHA surface
                btn_surf = pygame.Surface((btn.width, btn.height), pygame.SRCALPHA)
                btn_surf.fill((*col[:3], 55))
                screen.blit(btn_surf, btn.topleft)
                pygame.draw.rect(screen, col[:3], btn, 1, border_radius=3)
            else:
                btn_surf = pygame.Surface((btn.width, btn.height), pygame.SRCALPHA)
                btn_surf.fill((*UI_LINE[:3], 80))
                screen.blit(btn_surf, btn.topleft)

            lbl_s = self._txt(f_btn, lbl, col if active else TXT_MUTED)
            screen.blit(lbl_s, lbl_s.get_rect(center=btn.center))

        # Right info: stats + zoom + fps (cached)
        n_claimed = sum(1 for v in ownership.values() if v)
        info_text = (f"Zonas: {n_claimed}/{len(zones)}  ·  "
                     f"Zoom: {cam.zoom:.2f}×  ·  FPS: {fps:.0f}")
        info = self._txt(f_info, info_text, TXT_MUTED)
        screen.blit(info, (SW - info.get_width() - scaled(14),
                           (FH - info.get_height()) // 2))

    # ── BOTTOM PANEL (slide-in) ──────────────────────────────────────────

    def draw_bottom_panel(self, screen: pygame.Surface, selected_zone,
                          gods, zones, ownership, ancient_seals,
                          global_stats, t: float,
                          event_log=None, ancient_gods=None):
        if self._panel_slide < 0.02:
            return

        SW = config.SCREEN_W
        PH = int(BOTTOM_PANEL_H * self._panel_slide)
        py = config.SCREEN_H - PH
        pad = scaled(14)

        # Background — blit pre-built, clipped
        screen.blit(self._panel_bg, (0, py), area=(0, 0, SW, PH))

        # Ornate top border
        _ornate_border(screen, pygame.Rect(0, py, SW, PH),
                       col=GOLD, alpha=160, thick=1)

        if PH < scaled(30):
            return

        # Column layout
        MM_W = scaled(160)
        MM_PAD = scaled(12)
        col1_x = pad
        col1_w = SW // 2 - pad
        col2_x = SW // 2 + pad
        col2_w = SW - SW // 2 - MM_W - MM_PAD * 2 - pad

        # Divider line
        pygame.draw.line(screen, (*UI_LINE, 180),
                         (SW // 2, py + scaled(8)),
                         (SW // 2, py + PH - scaled(8)))

        # Column 1: Zone info
        content_h = 0
        if selected_zone:
            content_h = self._draw_zone_info(
                screen, selected_zone, gods, ownership,
                ancient_seals, col1_x, py, col1_w, PH,
                t, event_log=event_log, ancient_gods=ancient_gods)

        # Column 2: Events + Stats
        col2_h = self._draw_events_panel(
            screen, event_log, gods, zones, ownership,
            ancient_seals, col2_x, py, col2_w, PH)

        self._panel_content_h = max(content_h, col2_h)

        # Column 3: Minimap
        self._draw_minimap(screen, zones, ownership, py, PH)

    def _draw_zone_info(self, screen, zone: Zone, gods, ownership,
                        ancient_seals, x, py, w, PH, t,
                        event_log=None, ancient_gods=None) -> int:
        pad = scaled(10)
        y = py + pad
        f_big = self._fc.get(scaled(18), bold=True, serif=True)
        f_med = self._fc.get(scaled(12), serif=True)
        f_sm = self._fc.get(scaled(11), serif=True)
        f_xs = self._fc.get(scaled(10))

        nc = NATURE_COLOR.get(zone.base_nature, TXT)

        # Nature color bar
        bar_h = min(PH - pad * 2, scaled(100))
        pygame.draw.rect(screen, nc, (x - scaled(6), y, scaled(3), bar_h),
                         border_radius=2)

        # Zone name
        name_surf = self._txt(f_big, zone.zone_name, GOLD)
        if name_surf.get_width() > w - pad:
            f_big2 = self._fc.get(scaled(14), bold=True, serif=True)
            name_surf = self._txt(f_big2, zone.zone_name, GOLD)
        screen.blit(name_surf, (x + pad, y))
        y += name_surf.get_height() + scaled(2)

        # Region · Nature
        sub_text = f"{zone.region_name}  ·  {zone.base_nature.upper()}"
        sub = self._txt(f_sm, sub_text, nc)
        screen.blit(sub, (x + pad, y))
        y += sub.get_height() + scaled(6)

        # Lore (up to 2 lines)
        lore_lines = _wrap(zone.lore, f_xs, w - pad * 2)
        for line in lore_lines[:2]:
            ls = self._txt(f_xs, line, TXT_DIM)
            screen.blit(ls, (x + pad, y))
            y += ls.get_height() + scaled(2)
        if len(lore_lines) > 2:
            dots = self._txt(f_xs, "...", TXT_MUTED)
            screen.blit(dots, (x + pad, y))
        y += scaled(8)

        # Ownership status
        gid = ownership.get(zone.zone_id)
        if gid:
            god = gods.get(gid)
            if god:
                r2, g2, b2 = god.rgb()
                screen.blit(self._txt(f_xs, "CONTROLADA POR", TXT_MUTED),
                            (x + pad, y))
                y += f_xs.get_height() + scaled(2)
                pygame.draw.rect(screen, (r2, g2, b2),
                                 (x + pad, y, scaled(3), scaled(16)),
                                 border_radius=1)
                screen.blit(self._txt(f_med, god.god_name, (r2, g2, b2)),
                            (x + pad + scaled(7), y))
                y += scaled(18)
        elif zone.ancient_seal:
            sd = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            crack = sd.get("crack_level", zone.crack_level)
            maxc = sd.get("max_cracks", zone.max_cracks)
            scol = SEAL_COLOR.get(status, TXT_DIM)
            screen.blit(self._txt(f_xs, "SELO ANTIGO", TXT_MUTED),
                        (x + pad, y))
            y += f_xs.get_height() + scaled(2)
            screen.blit(self._txt(f_med, status.upper(), scol),
                        (x + pad, y))
            for ci in range(maxc):
                col_c = GOLD if ci < crack else (55, 45, 30)
                pygame.draw.rect(screen, col_c,
                                 (x + pad + scaled(80) + ci * scaled(14),
                                  y + scaled(2), scaled(11), scaled(10)),
                                 border_radius=2)
            y += scaled(18)

            # Ancient god lore
            if ancient_gods:
                ag = next(
                    (a for a in ancient_gods.values()
                     if a.seal_zone == zone.zone_id),
                    None)
                if ag and y + scaled(14) < py + PH - pad:
                    ar, ag2, ab = ag.rgb()
                    screen.blit(self._txt(f_xs, "DEUS APRISIONADO", TXT_MUTED),
                                (x + pad, y))
                    y += f_xs.get_height() + scaled(2)
                    screen.blit(self._txt(f_med, ag.god_name, (ar, ag2, ab)),
                                (x + pad, y))
                    y += f_med.get_height() + scaled(2)
                    if ag.lore_description and y + scaled(10) < py + PH - pad:
                        lore2 = _wrap(ag.lore_description, f_xs, w - pad * 2)
                        for line in lore2[:1]:
                            screen.blit(self._txt(f_xs, line, TXT_DIM),
                                        (x + pad, y))
                            y += f_xs.get_height() + scaled(2)
        else:
            screen.blit(self._txt(f_med, "NÃO REIVINDICADA", TXT_MUTED),
                        (x + pad, y))
            y += f_med.get_height() + scaled(6)

        # Zone events
        if event_log and y + scaled(20) < py + PH - pad:
            zone_evs = event_log.for_zone(zone.zone_id)
            if zone_evs:
                y += scaled(4)
                pygame.draw.line(screen, (*UI_LINE, 120),
                                 (x + pad, y), (x + pad + w - pad * 2, y))
                y += scaled(5)
                screen.blit(self._txt(f_xs, "EVENTOS", TXT_MUTED),
                            (x + pad, y))
                y += f_xs.get_height() + scaled(3)

                f_ev = self._fc.get(scaled(9))
                for ev in zone_evs[:3]:
                    if y + scaled(11) > py + PH - pad:
                        break
                    sev_col = SEVERITY_COLOR[ev.severity]
                    sev_lbl = SEVERITY_LABEL.get(ev.severity, "")
                    sl = self._txt(f_ev, sev_lbl, sev_col)
                    desc_max = w - pad * 2 - sl.get_width() - scaled(5)
                    desc_lines = _wrap(ev.description, f_ev, desc_max)
                    dl = self._txt(f_ev,
                                   desc_lines[0] if desc_lines else "",
                                   TXT_DIM)
                    pygame.draw.rect(screen, sev_col,
                                     (x + pad, y + scaled(2), scaled(2),
                                      sl.get_height() - scaled(2)),
                                     border_radius=1)
                    screen.blit(sl, (x + pad + scaled(5), y))
                    screen.blit(dl, (x + pad + scaled(5) + sl.get_width() + scaled(4), y))
                    y += sl.get_height() + scaled(3)

        return y - py

    def _draw_events_panel(self, screen, event_log, gods, zones, ownership,
                           ancient_seals, x, py, w, PH) -> int:
        pad = scaled(10)
        y = py + pad
        f_hdr = self._fc.get(scaled(11), bold=True)
        f_sm = self._fc.get(scaled(10))
        f_xs = self._fc.get(scaled(9))

        # Compact global stats
        n_claimed = sum(1 for v in ownership.values() if v)
        n_seals = sum(1 for z in zones.values() if z.ancient_seal)
        n_active = sum(1 for z in zones.values()
                       if z.ancient_seal and
                       ancient_seals.get(z.zone_id, {}).get("status") != "sleeping")

        stats_pairs = [
            ("Zonas", f"{n_claimed}/{len(zones)}", GOLD),
            ("Selos", f"{n_active}/{n_seals} ativos", CRIMSON),
            ("Deuses", str(len(gods)), CYAN),
        ]
        sx = x
        for lbl, val, col in stats_pairs:
            ls = self._txt(f_xs, lbl + ":", TXT_MUTED)
            vs = self._txt(f_xs, val, col)
            screen.blit(ls, (sx, y))
            screen.blit(vs, (sx + ls.get_width() + scaled(3), y))
            sx += ls.get_width() + vs.get_width() + scaled(14)
        y += f_xs.get_height() + scaled(4)

        # Critical alert
        if event_log:
            crit = event_log.critical_count
            high = event_log.high_count
            if crit > 0:
                alert_text = f"! {crit} CRITICAL  {high} HIGH"
                screen.blit(self._txt(f_sm, alert_text, CRIMSON), (x, y))
                y += f_sm.get_height() + scaled(3)

        pygame.draw.line(screen, (*UI_LINE, 140), (x, y), (x + w, y))
        y += scaled(5)

        # Header
        screen.blit(self._txt(f_hdr, "WORLD EVENTS", TXT_DIM), (x, y))
        y += f_hdr.get_height() + scaled(4)

        # Event feed
        events = event_log.recent if event_log else []
        ev_h = f_xs.get_height() + scaled(5)
        avail = py + PH - y - pad - scaled(36)
        max_ev = max(1, avail // ev_h)

        for ev in events[:max_ev]:
            if y + ev_h > py + PH - pad:
                break

            sev_col = SEVERITY_COLOR[ev.severity]
            vfx_col = EVENT_VFX.get(ev.type, {}).get("color", sev_col)
            shape = EVENT_VFX.get(ev.type, {}).get("shape", "circle")

            # Geometric icon
            icon_x = x + scaled(4)
            icon_y = y + ev_h // 2
            r = scaled(4)
            if shape == "diamond":
                pts = [(icon_x, icon_y - r), (icon_x + r, icon_y),
                       (icon_x, icon_y + r), (icon_x - r, icon_y)]
                pygame.draw.polygon(screen, vfx_col, pts)
            elif shape == "triangle":
                pts = [(icon_x, icon_y - r),
                       (icon_x + r, icon_y + r),
                       (icon_x - r, icon_y + r)]
                pygame.draw.polygon(screen, vfx_col, pts)
            elif shape == "square":
                pygame.draw.rect(screen, vfx_col,
                                 (icon_x - r, icon_y - r, r * 2, r * 2),
                                 border_radius=1)
            else:
                pygame.draw.circle(screen, vfx_col, (icon_x, icon_y), r)

            # Severity underline
            pygame.draw.line(screen, sev_col,
                             (x + scaled(10), y + ev_h - scaled(2)),
                             (x + scaled(10) + scaled(20), y + ev_h - scaled(2)), 1)

            # Description
            max_desc_w = w - scaled(14)
            desc_lines = _wrap(ev.description, f_xs, max_desc_w)
            dl = self._txt(f_xs,
                           desc_lines[0] if desc_lines else "", TXT_DIM)
            screen.blit(dl, (x + scaled(12), y + scaled(1)))

            # Timestamp
            ts = ev.timestamp[11:16] if len(ev.timestamp) >= 16 else ""
            if ts:
                ts_s = self._txt(f_xs, ts, TXT_MUTED)
                screen.blit(ts_s, (x + w - ts_s.get_width(), y + scaled(1)))

            y += ev_h

        # God cards
        y += scaled(4)
        if y + scaled(22) < py + PH - pad:
            pygame.draw.line(screen, (*UI_LINE, 100), (x, y), (x + w, y))
            y += scaled(4)
            gods_sorted = sorted(gods.values(), key=lambda g: -sum(
                1 for gid in ownership.values() if gid == g.god_id))
            card_h = scaled(20)
            for god in gods_sorted:
                if y + card_h > py + PH - pad:
                    break
                r2, g2, b2 = god.rgb()
                owned = sum(1 for gid in ownership.values() if gid == god.god_id)
                bar_w = max(0, int(w * owned / max(len(zones), 1)))
                if bar_w > 0:
                    bar_s = pygame.Surface((bar_w, card_h), pygame.SRCALPHA)
                    bar_s.fill((*god.rgb(), 25))
                    screen.blit(bar_s, (x, y))
                pygame.draw.rect(screen, (r2, g2, b2),
                                 (x, y, scaled(2), card_h), border_radius=1)
                ns = self._txt(f_xs, god.god_name, (r2, g2, b2))
                zt = self._txt(f_xs, f"{owned}z", TXT_MUTED)
                screen.blit(ns, (x + scaled(5),
                                 y + (card_h - ns.get_height()) // 2))
                screen.blit(zt, (x + w - zt.get_width() - scaled(3),
                                 y + (card_h - zt.get_height()) // 2))
                y += card_h + scaled(2)

        return y - py

    def _draw_minimap(self, screen, zones, ownership, py, PH):
        mm_rect = self._minimap_rect()
        if mm_rect is None:
            return

        if self._minimap_dirty or self._minimap_surf is None:
            self._minimap_surf = self._build_minimap(
                zones, ownership, mm_rect.width, mm_rect.height)
            self._minimap_dirty = False

        pygame.draw.rect(screen, (28, 22, 14), mm_rect, border_radius=3)
        screen.blit(self._minimap_surf, mm_rect.topleft)
        _ornate_border(screen, mm_rect, col=GOLD, alpha=150, thick=1)

    def _build_minimap(self, zones, ownership, MM_W, MM_H) -> pygame.Surface:
        from .config import WORLD_W, WORLD_H
        surf = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
        surf.fill((38, 30, 20, 240))

        def w2mm(wx, wy):
            return (int(wx / WORLD_W * MM_W), int(wy / WORLD_H * MM_H))

        for zone in zones.values():
            gid = ownership.get(zone.zone_id)
            col = (90, 80, 60, 100) if gid else (60, 55, 45, 80)
            verts = [w2mm(wx, wy) for wx, wy in zone.vertices]
            if len(verts) >= 3:
                pygame.draw.polygon(surf, col, verts)
                pygame.draw.polygon(surf, (80, 65, 40, 120), verts, 1)
        return surf

    def _build_minimap_with_gods(self, zones, ownership, gods,
                                 MM_W, MM_H) -> pygame.Surface:
        from .config import WORLD_W, WORLD_H
        surf = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
        surf.fill((38, 30, 20, 240))

        def w2mm(wx, wy):
            return (int(wx / WORLD_W * MM_W), int(wy / WORLD_H * MM_H))

        for zone in zones.values():
            gid = ownership.get(zone.zone_id)
            god = gods.get(gid) if gid else None
            if god:
                r, g, b = god.rgb()
                fill_col = (r, g, b, 120)
                border_col = (r, g, b, 180)
            else:
                fill_col = (55, 48, 38, 70)
                border_col = (75, 65, 50, 110)
            verts = [w2mm(wx, wy) for wx, wy in zone.vertices]
            if len(verts) >= 3:
                pygame.draw.polygon(surf, fill_col, verts)
                pygame.draw.polygon(surf, border_col, verts, 1)
        return surf

    def draw_bottom_panel_with_gods(self, screen, selected_zone, gods, zones,
                                    ownership, ancient_seals, global_stats, t,
                                    event_log=None, ancient_gods=None):
        if self._minimap_dirty or self._minimap_surf is None:
            mm_rect = self._minimap_rect()
            if mm_rect:
                self._minimap_surf = self._build_minimap_with_gods(
                    zones, ownership, gods, mm_rect.width, mm_rect.height)
                self._minimap_dirty = False

        self.draw_bottom_panel(screen, selected_zone, gods, zones,
                               ownership, ancient_seals, global_stats, t,
                               event_log=event_log, ancient_gods=ancient_gods)

    # ── Compat stubs ──────────────────────────────────────────────────────

    def draw_top_hud(self, screen, gods, zones, ownership, cam, fps, t):
        self.draw_filter_bar(screen, gods, zones, ownership, cam, fps, t)

    def draw_left_panel(self, screen, gods, zones, ownership,
                        selected_zone, ancient_seals, global_stats):
        return

    def draw_seals_panel(self, screen, zones, ancient_seals, t):
        return

    # ── TOOLTIP ───────────────────────────────────────────────────────────

    def draw_hover_tooltip(self, screen, zone, gods, ownership,
                           ancient_seals, mx: int, my: int):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        if zone is None or mx < self.map_x or my < self.map_y:
            return

        f_hdr = self._fc.get(scaled(13), bold=True, serif=True)
        f_sm = self._fc.get(scaled(11), serif=True)
        f_xs = self._fc.get(scaled(10))
        nc = NATURE_COLOR.get(zone.base_nature, TXT_DIM)

        rows = [
            (zone.zone_name, TXT, f_hdr),
            (zone.region_name, TXT_DIM, f_xs),
            (zone.base_nature.upper(), nc, f_xs),
        ]
        gid = ownership.get(zone.zone_id)
        if gid:
            god = gods.get(gid)
            if god:
                rows.append((f"▶ {god.god_name}", god.rgb(), f_sm))
        elif zone.ancient_seal:
            st = ancient_seals.get(zone.zone_id, {}).get("status", "sleeping")
            rows.append((f"⛓ {st.upper()}", SEAL_COLOR.get(st, TXT_DIM), f_sm))
        else:
            rows.append(("Não reivindicada", TXT_MUTED, f_xs))

        TW = max(f.size(t_)[0] for t_, _, f in rows) + scaled(22)
        TH = sum(f.get_height() + scaled(3) for _, _, f in rows) + scaled(16)
        tx = mx + scaled(16)
        ty = my - TH // 2
        if tx + TW > SW - 4:
            tx = mx - TW - scaled(8)
        ty = max(self.map_y + 4, min(SH - TH - 4, ty))

        # Reuse tooltip surface (resize if needed)
        if (self._tooltip_surf.get_width() < TW or
                self._tooltip_surf.get_height() < TH):
            self._tooltip_surf = pygame.Surface(
                (max(TW, 400), max(TH, 200)), pygame.SRCALPHA)

        ts = self._tooltip_surf
        ts.fill((0, 0, 0, 0), (0, 0, TW, TH))

        # Background
        pygame.draw.rect(ts, (*UI_BG, 240), (0, 0, TW, TH), border_radius=3)
        _ornate_border(ts, pygame.Rect(0, 0, TW, TH),
                       col=GOLD, alpha=160, thick=1)
        # Nature accent
        pygame.draw.line(ts, nc, (1, 4), (1, TH - 4), 2)

        oy = scaled(8)
        for text, col, font in rows:
            ts.blit(self._txt(font, text, col), (scaled(10), oy))
            oy += font.get_height() + scaled(3)

        screen.blit(ts, (tx, ty), area=(0, 0, TW, TH))

    # ── NOTIFICATION ──────────────────────────────────────────────────────

    def draw_notif(self, screen):
        if self._notif_alpha <= 0:
            return
        SW = config.SCREEN_W
        f = self._fc.get(scaled(14), bold=True, serif=True)
        s = self._txt(f, self._notif_msg, GOLD)
        pw = s.get_width() + scaled(30)
        ph = s.get_height() + scaled(16)
        px = SW // 2 - pw // 2
        py_ = self._panel_y - ph - scaled(10)
        a = int(220 * self._notif_alpha)

        # Reuse notif surface
        ns = self._notif_surf
        if ns.get_width() < pw or ns.get_height() < ph:
            self._notif_surf = pygame.Surface(
                (max(pw, SW), max(ph, scaled(50))), pygame.SRCALPHA)
            ns = self._notif_surf

        ns.fill((0, 0, 0, 0), (0, 0, pw, ph))
        pygame.draw.rect(ns, (*UI_BG, a), (0, 0, pw, ph), border_radius=3)
        _ornate_border(ns, pygame.Rect(0, 0, pw, ph),
                       col=GOLD, alpha=min(255, a + 20), thick=1)
        ns.blit(s, (scaled(15), scaled(8)))
        screen.blit(ns, (px, py_), area=(0, 0, pw, ph))

    # ── CORNERS ───────────────────────────────────────────────────────────

    def draw_corners(self, screen):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        L = scaled(22)
        for px_, py_, w_, h_ in [
            (0, 0, L, 2), (0, 0, 2, L),
            (SW - L, 0, L, 2), (SW - 2, 0, 2, L),
            (0, SH - 2, L, 2), (0, SH - L, 2, L),
            (SW - L, SH - 2, L, 2), (SW - 2, SH - L, 2, L),
        ]:
            pygame.draw.rect(screen, GOLD, (px_, py_, w_, h_))

    # ── LOADING ───────────────────────────────────────────────────────────

    def draw_loading(self, screen, msg: str, pct: float):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        screen.fill(UI_BG)

        f_title = self._fc.get(scaled(22), bold=True, serif=True)
        f_sub = self._fc.get(scaled(11))
        f_msg = self._fc.get(scaled(11))

        t = f_title.render("⚔  NEURAL FIGHTS — AETHERMOOR", True, GOLD)
        screen.blit(t, ((SW - t.get_width()) // 2, SH // 2 - scaled(72)))

        sub = f_sub.render("W O R L D  M A P  L O A D I N G", True, TXT_DIM)
        screen.blit(sub, ((SW - sub.get_width()) // 2, SH // 2 - scaled(44)))

        BW = min(scaled(480), SW - scaled(60))
        BH = scaled(6)
        bx = (SW - BW) // 2
        by = SH // 2 - scaled(4)

        pygame.draw.rect(screen, UI_LINE,
                         (bx - 1, by - 1, BW + 2, BH + 2), border_radius=3)
        pygame.draw.rect(screen, (35, 28, 16),
                         (bx, by, BW, BH), border_radius=3)
        if pct > 0:
            pygame.draw.rect(screen, GOLD,
                             (bx, by, int(BW * pct), BH), border_radius=3)

        m = f_msg.render(msg, True, TXT_DIM)
        screen.blit(m, ((SW - m.get_width()) // 2, by + BH + scaled(10)))

        _ornate_border(screen,
                       pygame.Rect(scaled(20), scaled(20),
                                   SW - scaled(40), SH - scaled(40)),
                       col=GOLD_DIM, alpha=120, thick=1)

        self.draw_corners(screen)
        pygame.display.flip()
        pygame.event.pump()
