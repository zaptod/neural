"""
world_map_pygame/ui.py

Layout:
  ┌─────────────────────────── SCREEN_W ────────────────────────────────────┐
  │         HUD TOPO (full width, y=0..HUD_H)                               │
  ├── PANEL_W ──┬──────────────────────────────────────────────────────────┤
  │  PAINEL ESQ │                  MAPA                                     │
  │  x=0        │  x=panel_w, y=HUD_H                                       │
  │  y=HUD_H    │                              ┌──────────────────────────┐ │
  │             │                              │  PAINEL SELOS (dir inf)  │ │
  └─────────────┴──────────────────────────────┴──────────────────────────┘
"""
import math
import pygame
from typing import Optional, Dict

# Importa o módulo inteiro para ler SCREEN_W/SCREEN_H dinamicamente
# (valores detectados em tempo de execução pelo config.py)
from . import config
from .config import (
    PANEL_W_MIN, PANEL_W_MAX,
    UI_BG, UI_LINE,
    CYAN, CRIMSON, GOLD, TXT, TXT_DIM, TXT_MUTED,
    NATURE_COLOR, SEAL_COLOR,
)
from .data_loader import Zone, God
from .camera import Camera


def _draw_text(dest, text, x, y, font, color=TXT, shadow=True) -> int:
    if shadow:
        dest.blit(font.render(text, True, (0, 0, 0)), (x + 1, y + 1))
    dest.blit(font.render(text, True, color), (x, y))
    return font.get_height()


def _wrap(text: str, font, max_w: int) -> list:
    words = text.split()
    lines, line = [], ""
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


def _rrect(surf, color, rect, r=4, alpha=None):
    if alpha is not None:
        tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (*color[:3], alpha), tmp.get_rect(), border_radius=r)
        surf.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=r)


class _FC:
    def __init__(self):
        self._c: Dict[tuple, pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        k = (size, bold)
        if k not in self._c:
            self._c[k] = pygame.font.SysFont("consolas", size, bold=bold)
        return self._c[k]


class UI:
    HUD_H   = 40
    SEALS_W = 245

    def __init__(self):
        pygame.font.init()
        self._fc = _FC()
        self._panel_w_target  = float(PANEL_W_MIN)
        self._panel_w_current = float(PANEL_W_MIN)
        self._notif_msg       = ""
        self._notif_alpha     = 0.0
        self._panel_scroll    = 0
        self._panel_content_h = 0

    # ── Layout helpers ────────────────────────────────────────────────────
    @property
    def panel_w(self) -> int:
        return int(self._panel_w_current)

    @property
    def map_x(self) -> int:
        return self.panel_w

    @property
    def map_y(self) -> int:
        return self.HUD_H

    @property
    def map_w(self) -> int:
        return config.SCREEN_W - self.panel_w

    @property
    def map_h(self) -> int:
        return config.SCREEN_H - self.HUD_H

    def update(self, dt: float):
        diff = self._panel_w_target - self._panel_w_current
        self._panel_w_current += diff * min(1.0, dt * 12.0)
        self._notif_alpha = max(0.0, self._notif_alpha - dt * 0.50)

    def notify(self, msg: str):
        self._notif_msg   = msg
        self._notif_alpha = 1.0

    def scroll_panel(self, delta: int):
        PH    = config.SCREEN_H - self.HUD_H
        max_s = max(0, self._panel_content_h - PH + 8)
        self._panel_scroll = max(0, min(max_s, self._panel_scroll + delta))

    # ── HUD TOPO (full width) ─────────────────────────────────────────────
    def draw_top_hud(self, screen, gods, zones, ownership, cam: Camera,
                     fps: float, t: float):
        SW = config.SCREEN_W
        HH = self.HUD_H

        pygame.draw.rect(screen, UI_BG, (0, 0, SW, HH))
        pygame.draw.line(screen, UI_LINE, (0, HH - 1), (SW, HH - 1))
        p = int(180 + math.sin(t * 2) * 55)
        pygame.draw.line(screen, (0, p // 2, p), (0, 0), (SW, 0), 2)
        pygame.draw.line(screen, CYAN, (self.panel_w, 0), (self.panel_w, HH))

        f14 = self._fc.get(14, bold=True)
        f9  = self._fc.get(9)

        title = f14.render("⚔  NEURAL FIGHTS — AETHERMOOR", True, (0, p // 2, p))
        tx = self.map_x + (self.map_w - title.get_width()) // 2
        screen.blit(title, (tx, (HH - title.get_height()) // 2))

        n_claimed = sum(1 for v in ownership.values() if v)
        st = f9.render(
            f"Gods:{len(gods)}  Zones:{n_claimed}/{len(zones)}"
            f"  Zoom:{cam.zoom:.2f}×  FPS:{fps:.0f}",
            True, TXT_DIM)
        screen.blit(st, (SW - st.get_width() - 12, (HH - st.get_height()) // 2))

    # ── PAINEL ESQUERDO ───────────────────────────────────────────────────
    def draw_left_panel(self, screen, gods, zones, ownership,
                        selected_zone, ancient_seals, global_stats):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        PW = max(1, self.panel_w)
        HH = self.HUD_H
        PH = SH - HH

        # Fundo sólido (abaixo do HUD)
        pygame.draw.rect(screen, UI_BG, (0, HH, PW, PH))
        # Linha separadora direita
        pygame.draw.line(screen, CYAN, (PW - 1, HH), (PW - 1, SH))

        # Ajusta largura alvo
        req_w = self._measure_w(gods, selected_zone)
        self._panel_w_target = float(max(PANEL_W_MIN, min(PANEL_W_MAX, req_w + 36)))

        # Surface virtual de conteúdo
        VIRT_H = max(PH * 3, 2800)
        content = pygame.Surface((PW, VIRT_H), pygame.SRCALPHA)
        real_h  = self._render_content(content, PW, gods, zones, ownership,
                                       selected_zone, ancient_seals, global_stats)

        self._panel_content_h = real_h
        max_scroll = max(0, real_h - PH + 8)
        self._panel_scroll = min(self._panel_scroll, max_scroll)

        # Blit com scroll, dentro da área do painel
        screen.set_clip(pygame.Rect(0, HH, PW, PH))
        screen.blit(content, (0, HH), (0, self._panel_scroll, PW, PH))
        screen.set_clip(None)

        # Scrollbar
        if max_scroll > 0:
            frac  = self._panel_scroll / max_scroll
            bar_h = max(24, int(PH * PH / real_h))
            bar_y = HH + int(frac * (PH - bar_h))
            pygame.draw.rect(screen, UI_LINE, (PW - 4, HH, 3, PH))
            pygame.draw.rect(screen, CYAN,    (PW - 4, bar_y, 3, bar_h))

    def _render_content(self, surf, PW, gods, zones, ownership,
                         selected_zone, ancient_seals, global_stats) -> int:
        PAD = 14
        f15 = self._fc.get(14, bold=True)
        f11 = self._fc.get(11, bold=True)
        f10 = self._fc.get(10)
        f9  = self._fc.get(9)
        y   = PAD

        # Cabeçalho
        t = f15.render("⚔  AETHERMOOR", True, CYAN)
        surf.blit(t, ((PW - t.get_width()) // 2, y)); y += t.get_height() + 2
        sub = f9.render("WORLD MAP  ·  GOD WAR", True, TXT_DIM)
        surf.blit(sub, ((PW - sub.get_width()) // 2, y)); y += sub.get_height() + 10
        pygame.draw.line(surf, UI_LINE, (PAD, y), (PW - PAD, y)); y += 10

        # Stats
        n_claimed = sum(1 for v in ownership.values() if v)
        n_seals   = sum(1 for z in zones.values() if z.ancient_seal)
        n_active  = sum(1 for z in zones.values()
                        if z.ancient_seal and
                        ancient_seals.get(z.zone_id, {}).get("status") != "sleeping")
        for lbl, val, col in [
            ("Deuses Ativos",        str(len(gods)),                CYAN),
            ("Zonas Reivindicadas",  f"{n_claimed}/{len(zones)}",   GOLD),
            ("Selos Antigos",        f"{n_active}/{n_seals} ativos", CRIMSON),
        ]:
            ls = f9.render(lbl, True, TXT_DIM)
            vs = f10.render(val, True, col)
            surf.blit(ls, (PAD, y))
            surf.blit(vs, (PW - vs.get_width() - PAD, y))
            y += ls.get_height() + 5
        pygame.draw.line(surf, UI_LINE, (PAD, y), (PW - PAD, y)); y += 10

        # Zona selecionada
        if selected_zone:
            hdr = f11.render("ZONA SELECIONADA", True, GOLD)
            surf.blit(hdr, (PAD, y)); y += hdr.get_height() + 5
            y = self._zone_card(surf, selected_zone, gods,
                                ownership, ancient_seals, PAD, y, PW)
            pygame.draw.line(surf, UI_LINE, (PAD, y), (PW - PAD, y)); y += 10

        # Deuses
        hdr2 = f11.render("DEUSES ATIVOS", True, CRIMSON)
        surf.blit(hdr2, (PAD, y)); y += hdr2.get_height() + 6

        for god in sorted(gods.values(), key=lambda g: -g.follower_count):
            r2, g2, b2 = god.rgb()
            owned  = sum(1 for gid in ownership.values() if gid == god.god_id)
            pct    = owned / max(len(zones), 1)
            card_h = 38
            _rrect(surf, (r2, g2, b2),
                   pygame.Rect(PAD, y, PW - PAD * 2, card_h), r=4, alpha=15)
            bw = int((PW - PAD * 2 - 2) * pct)
            if bw > 0:
                _rrect(surf, (r2, g2, b2),
                       pygame.Rect(PAD + 1, y, bw, card_h), r=4, alpha=28)
            pygame.draw.rect(surf, (r2, g2, b2),
                             (PAD, y, 4, card_h), border_radius=2)
            surf.blit(f10.render(god.god_name, True, (r2, g2, b2)), (PAD + 8, y + 3))
            nc = NATURE_COLOR.get(god.nature, TXT_DIM)
            surf.blit(f9.render(f"[{god.nature}]", True, nc),
                      (PAD + 8, y + 21))
            zt = f9.render(f"{owned} zona{'s' if owned != 1 else ''}", True, TXT_DIM)
            surf.blit(zt, (PW - zt.get_width() - PAD, y + 21))
            y += card_h + 4

        pygame.draw.line(surf, UI_LINE, (PAD, y), (PW - PAD, y)); y += 10

        # Legenda naturezas
        hdr3 = f11.render("NATUREZAS", True, TXT_DIM)
        surf.blit(hdr3, (PAD, y)); y += hdr3.get_height() + 4
        nats = sorted(set(z.base_nature for z in zones.values()))
        cw   = (PW - PAD * 2) // 2
        for i, nat in enumerate(nats):
            col = NATURE_COLOR.get(nat, TXT_DIM)
            cx_ = PAD + (i % 2) * cw
            cy_ = y + (i // 2) * 14
            pygame.draw.rect(surf, col, (cx_, cy_ + 3, 8, 8), border_radius=2)
            surf.blit(f9.render(nat, True, TXT_MUTED), (cx_ + 12, cy_))
        y += ((len(nats) + 1) // 2) * 14 + 8

        pygame.draw.line(surf, UI_LINE, (PAD, y), (PW - PAD, y)); y += 8

        # Controles
        for line in [
            "Drag = Pan     Scroll = Zoom",
            "Click = Zona   Dbl = Fly To",
            "H = Home       R = Reload",
            "Clique Dir. = Limpar seleção",
        ]:
            surf.blit(f9.render(line, True, TXT_MUTED), (PAD, y)); y += 13

        return y + 10

    def _zone_card(self, surf, zone: Zone, gods, ownership,
                    ancient_seals, pad, y, PW) -> int:
        f13 = self._fc.get(13, bold=True)
        f10 = self._fc.get(10)
        f9  = self._fc.get(9)
        nc  = NATURE_COLOR.get(zone.base_nature, TXT)
        sy0 = y

        _draw_text(surf, zone.zone_name, pad, y, f13, TXT); y += 18
        _draw_text(surf, f"{zone.region_name}  ·  {zone.base_nature.upper()}",
                   pad, y, f9, nc); y += 13
        for line in _wrap(zone.lore, f9, PW - pad * 2):
            _draw_text(surf, line, pad, y, f9, TXT_DIM, shadow=False); y += 11
        y += 4

        gid = ownership.get(zone.zone_id)
        if gid:
            god = gods.get(gid)
            if god:
                r2, g2, b2 = god.rgb()
                _draw_text(surf, "CONTROLADA POR", pad, y, f9, TXT_DIM, shadow=False)
                y += 12
                pygame.draw.rect(surf, (r2, g2, b2), (pad, y, 4, 18), border_radius=2)
                _draw_text(surf, god.god_name, pad + 8, y, f13, (r2, g2, b2))
                y += 20
        elif zone.ancient_seal:
            sd     = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            crack  = sd.get("crack_level", zone.crack_level)
            maxc   = sd.get("max_cracks",  zone.max_cracks)
            scol   = SEAL_COLOR.get(status, TXT_DIM)
            _draw_text(surf, "🔒 ANCIENT SEAL", pad, y, f13, GOLD); y += 16
            _draw_text(surf, status.upper(), pad, y, f10, scol)
            for ci in range(maxc):
                pygame.draw.rect(surf, GOLD if ci < crack else (40, 40, 60),
                                 (pad + 90 + ci * 14, y + 2, 11, 11), border_radius=2)
            y += 16
        else:
            _draw_text(surf, "UNCLAIMED", pad, y, f13, TXT_DIM); y += 18

        if zone.neighboring_zones:
            nb = f9.render("Viz: " + ", ".join(zone.neighboring_zones[:4]),
                           True, TXT_MUTED)
            surf.blit(nb, (pad, y)); y += 12

        pygame.draw.rect(surf, nc, (pad - 8, sy0, 3, y - sy0), border_radius=2)
        return y + 6

    # ── HOVER TOOLTIP ─────────────────────────────────────────────────────
    def draw_hover_tooltip(self, screen, zone, gods, ownership,
                            ancient_seals, mx: int, my: int):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        if zone is None or mx < self.map_x or my < self.map_y:
            return
        f11 = self._fc.get(11, bold=True)
        f9  = self._fc.get(9)
        nc  = NATURE_COLOR.get(zone.base_nature, TXT_DIM)
        rows = [
            (zone.zone_name,   TXT,     f11),
            (zone.region_name, TXT_DIM, f9),
            (zone.base_nature.upper(), nc, f9),
        ]
        gid = ownership.get(zone.zone_id)
        if gid:
            god = gods.get(gid)
            if god:
                rows.append((f"▶ {god.god_name}", god.rgb(), f9))
        elif zone.ancient_seal:
            st = ancient_seals.get(zone.zone_id, {}).get("status", "sleeping")
            rows.append((f"🔒 {st.upper()}", SEAL_COLOR.get(st, TXT_DIM), f9))
        else:
            rows.append(("Unclaimed", TXT_MUTED, f9))

        TW = max(f.size(t)[0] for t, _, f in rows) + 22
        TH = sum(f.get_height() + 2 for _, _, f in rows) + 14
        tx = mx + 16
        ty = my - TH // 2
        if tx + TW > SW - 4:
            tx = mx - TW - 8
        ty = max(self.HUD_H + 4, min(SH - TH - 4, ty))

        bg = pygame.Surface((TW, TH), pygame.SRCALPHA)
        bg.fill((*UI_BG, 235))
        pygame.draw.rect(bg, (*CYAN, 160), bg.get_rect(), 1, border_radius=4)
        pygame.draw.line(bg, (*nc, 200), (0, 2), (0, TH - 2), 3)
        screen.blit(bg, (tx, ty))
        oy = 7
        for text, col, font in rows:
            screen.blit(font.render(text, True, col), (tx + 10, ty + oy))
            oy += font.get_height() + 2

    # ── PAINEL DE SELOS ───────────────────────────────────────────────────
    def draw_seals_panel(self, screen, zones, ancient_seals, t: float):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        seal_zones = [z for z in zones.values() if z.ancient_seal]
        if not seal_zones:
            return
        f11 = self._fc.get(11, bold=True)
        f9  = self._fc.get(9)
        item_h = 40
        PW = self.SEALS_W
        PH = 28 + len(seal_zones) * item_h + 6
        sx = SW - PW - 8
        sy = max(self.HUD_H + 4, SH - PH - 8)

        bg = pygame.Surface((PW, PH), pygame.SRCALPHA)
        bg.fill((*UI_BG, 228))
        pygame.draw.rect(bg, (*UI_LINE, 190), bg.get_rect(), 1, border_radius=4)
        glow = int(180 + math.sin(t * 2) * 50)
        pygame.draw.line(bg, (glow, glow // 2, 0), (2, 1), (PW - 2, 1), 2)
        hdr = f11.render("🔒  ANCIENT SEALS", True, GOLD)
        bg.blit(hdr, ((PW - hdr.get_width()) // 2, 6))

        ry = 28
        for zone in seal_zones:
            sd     = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            crack  = sd.get("crack_level", zone.crack_level)
            maxc   = sd.get("max_cracks",  zone.max_cracks)
            scol   = SEAL_COLOR.get(status, TXT_DIM)
            _rrect(bg, scol, pygame.Rect(4, ry, PW - 8, item_h - 4), r=3, alpha=20)
            bg.blit(f11.render(zone.zone_name, True, TXT), (10, ry + 2))
            bg.blit(f9.render(status.upper(), True, scol),  (10, ry + 18))
            for ci in range(maxc):
                pygame.draw.rect(bg, GOLD if ci < crack else (40, 40, 60),
                                 (PW - maxc * 14 - 6 + ci * 14, ry + 18, 11, 10),
                                 border_radius=2)
            ry += item_h
        screen.blit(bg, (sx, sy))

    # ── NOTIFICAÇÃO ───────────────────────────────────────────────────────
    def draw_notif(self, screen):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        if self._notif_alpha <= 0:
            return
        f13 = self._fc.get(13, bold=True)
        s   = f13.render(self._notif_msg, True, CYAN)
        pw  = s.get_width() + 30
        ph  = s.get_height() + 16
        px  = self.map_x + self.map_w // 2 - pw // 2
        py  = SH - 80
        px  = max(self.map_x + 4, min(SW - pw - 4, px))
        a   = int(220 * self._notif_alpha)
        bg  = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((*UI_BG, a))
        pygame.draw.rect(bg, (*CYAN, min(255, a + 20)), bg.get_rect(), 1, border_radius=4)
        bg.blit(s, (15, 8))
        screen.blit(bg, (px, py))

    # ── CANTOS ────────────────────────────────────────────────────────────
    def draw_corners(self, screen):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        L  = 22
        for px_, py_, w_, h_ in [
            (0,    0,    L, 2), (0,    0,    2, L),
            (SW-L, 0,    L, 2), (SW-2, 0,    2, L),
            (0,    SH-2, L, 2), (0,    SH-L, 2, L),
            (SW-L, SH-2, L, 2), (SW-2, SH-L, 2, L),
        ]:
            pygame.draw.rect(screen, CYAN, (px_, py_, w_, h_))

    # ── LOADING ───────────────────────────────────────────────────────────
    def draw_loading(self, screen, msg: str, pct: float):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        screen.fill(UI_BG)
        f22 = self._fc.get(20, bold=True)
        f10 = self._fc.get(10)
        f9  = self._fc.get(9)

        t = f22.render("⚔  NEURAL FIGHTS — AETHERMOOR", True, CYAN)
        screen.blit(t, ((SW - t.get_width()) // 2, SH // 2 - 70))
        sub = f9.render("W O R L D  M A P  L O A D I N G", True, TXT_DIM)
        screen.blit(sub, ((SW - sub.get_width()) // 2, SH // 2 - 42))

        BW = min(480, SW - 60)
        BH = 6
        bx = (SW - BW) // 2
        by = SH // 2 - 4
        pygame.draw.rect(screen, UI_LINE, (bx - 1, by - 1, BW + 2, BH + 2), border_radius=3)
        pygame.draw.rect(screen, (0, 40, 60), (bx, by, BW, BH), border_radius=3)
        if pct > 0:
            pygame.draw.rect(screen, CYAN, (bx, by, int(BW * pct), BH), border_radius=3)

        m = f10.render(msg, True, TXT_DIM)
        screen.blit(m, ((SW - m.get_width()) // 2, by + BH + 10))

        L = 22
        for px_, py_, w_, h_ in [
            (0,    0,    L, 2), (0,    0,    2, L),
            (SW-L, 0,    L, 2), (SW-2, 0,    2, L),
            (0,    SH-2, L, 2), (0,    SH-L, 2, L),
            (SW-L, SH-2, L, 2), (SW-2, SH-L, 2, L),
        ]:
            pygame.draw.rect(screen, CYAN, (px_, py_, w_, h_))

        pygame.display.flip()
        pygame.event.pump()

    # ── Medição interna ───────────────────────────────────────────────────
    def _measure_w(self, gods, selected_zone) -> int:
        f13 = self._fc.get(13, bold=True)
        f10 = self._fc.get(10)
        f9  = self._fc.get(9)
        mw  = PANEL_W_MIN

        if selected_zone:
            mw = max(mw, f13.size(selected_zone.zone_name)[0] + 36)
            mw = max(mw, f9.size(
                f"{selected_zone.region_name}  ·  "
                f"{selected_zone.base_nature.upper()}")[0] + 36)

        for god in gods.values():
            mw = max(mw, f10.size(god.god_name)[0] + 60)

        return mw
