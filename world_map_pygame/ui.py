"""
world_map_pygame/ui.py

[FASE 3] Redesign completo do layout:
  - Painel lateral REMOVIDO → mapa full-width
  - HUD de topo SUBSTITUÍDO → barra de filtros fina
  - Painel inferior NOVO → slide-in ao selecionar zona
      Contém: info da zona | lista de deuses + stats | minimap
  - Tipografia serif (Georgia) com UI_SCALE
  - Bordas ornamentais douradas
  - active_filter exposto para o renderer (Fase 4)
"""
import math
import pygame
from typing import Optional, Dict, List

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


# ── Helpers de desenho ────────────────────────────────────────────────────────

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
    if rect.width <= 0 or rect.height <= 0:
        return
    if alpha is not None:
        tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(tmp, (*color[:3], alpha), tmp.get_rect(), border_radius=r)
        surf.blit(tmp, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=r)


def _draw_ornate_border(surf, rect: pygame.Rect, col=GOLD, alpha=180, thick=1):
    """Borda dourada com pequenos ornamentos nos quatro cantos."""
    r = rect
    L = scaled(10)   # comprimento do ornamento de canto

    # Linha da borda completa
    tmp = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
    pygame.draw.rect(tmp, (*col, alpha), tmp.get_rect(), thick, border_radius=2)
    surf.blit(tmp, r.topleft)

    # Ornamentos de canto — linhas em L mais brilhantes
    bright = tuple(min(255, c + 60) for c in col)
    for px, py, dx, dy in [
        (r.left,       r.top,        1,  1),   # canto TL
        (r.right - 1,  r.top,       -1,  1),   # canto TR
        (r.left,       r.bottom - 1, 1, -1),   # canto BL
        (r.right - 1,  r.bottom - 1,-1, -1),   # canto BR
    ]:
        pygame.draw.line(surf, bright, (px, py), (px + dx * L, py), 2)
        pygame.draw.line(surf, bright, (px, py), (px, py + dy * L), 2)


class _FC:
    """Cache de fontes com suporte a serif e bold."""
    def __init__(self):
        self._c: Dict[tuple, pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False, serif: bool = False) -> pygame.font.Font:
        k = (size, bold, serif)
        if k not in self._c:
            if serif:
                name = "georgia,times new roman,serif"
            else:
                name = "consolas"
            self._c[k] = pygame.font.SysFont(name, size, bold=bold)
        return self._c[k]


class UI:
    HUD_H   = FILTER_BAR_H   # barra de filtros substitui o HUD de topo
    SEALS_W = 0               # painel de selos removido (integrado no bottom panel)

    # Naturezas disponíveis para filtro — "all" é o primeiro
    _ALL_NATURES = ["all", "arcane", "balanced", "chaos", "darkness",
                    "fear", "fire", "greed", "ice", "nature", "void"]

    def __init__(self):
        pygame.font.init()
        self._fc = _FC()

        # Notificação
        self._notif_msg   = ""
        self._notif_alpha = 0.0

        # Painel inferior — animação slide
        self._panel_open        = False
        self._panel_slide       = 0.0   # 0.0=fechado, 1.0=aberto
        self._panel_scroll      = 0
        self._panel_content_h   = 0

        # Filtros
        self.active_filter: str = "all"   # natureza ativa (exposto ao renderer)
        self._god_filter: Optional[str] = None  # god_id ou None

        # Minimap
        self._minimap_surf: Optional[pygame.Surface] = None
        self._minimap_dirty = True

        # Layout do painel
        self._panel_w_current = 0.0   # compatibilidade com main.py legado

    # ── Propriedades de layout ────────────────────────────────────────────

    @property
    def panel_w(self) -> int:
        return 0   # sem painel lateral

    @property
    def map_x(self) -> int:
        return 0   # mapa full-width

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
        """Posição Y do topo do painel inferior (animado)."""
        panel_h = int(BOTTOM_PANEL_H * self._panel_slide)
        return config.SCREEN_H - panel_h

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        target = 1.0 if self._panel_open else 0.0
        diff   = target - self._panel_slide
        self._panel_slide += diff * min(1.0, dt * 14.0)
        if abs(diff) < 0.002:
            self._panel_slide = target

        self._notif_alpha = max(0.0, self._notif_alpha - dt * 0.45)

    def notify(self, msg: str):
        self._notif_msg   = msg
        self._notif_alpha = 1.0

    def open_panel(self, zone: Optional[Zone]):
        self._panel_open = (zone is not None)

    def scroll_panel(self, delta: int):
        max_s = max(0, self._panel_content_h - BOTTOM_PANEL_H + scaled(8))
        self._panel_scroll = max(0, min(max_s, self._panel_scroll + delta))

    def mark_minimap_dirty(self):
        self._minimap_dirty = True

    # ── Handle events externos ────────────────────────────────────────────

    def handle_filter_click(self, mx: int, my: int, natures_available: list) -> bool:
        """
        Verifica clique na barra de filtros.
        Retorna True se o clique foi consumido.
        """
        if my >= self.HUD_H:
            return False
        SW  = config.SCREEN_W
        FH  = self.HUD_H
        pad = scaled(8)
        x   = scaled(80)   # após o título

        for nat in (["all"] + sorted(natures_available)):
            lbl  = nat.upper() if nat != "all" else "TODOS"
            font = self._fc.get(scaled(11), bold=True)
            w    = font.size(lbl)[0] + pad * 2
            btn  = pygame.Rect(x, 3, w, FH - 6)
            if btn.collidepoint(mx, my):
                self.active_filter = nat
                return True
            x += w + scaled(4)
        return False

    def handle_minimap_click(self, mx: int, my: int,
                              cam: Camera, zones) -> bool:
        """
        Clique no minimap faz câmera fly-to. Retorna True se consumido.
        """
        mm_rect = self._minimap_rect()
        if mm_rect is None or not mm_rect.collidepoint(mx, my):
            return False
        # Converte pixel do minimap para world-units
        MM_W = mm_rect.width
        MM_H = mm_rect.height
        from .config import WORLD_W, WORLD_H
        wx = (mx - mm_rect.x) / MM_W * WORLD_W
        wy = (my - mm_rect.y) / MM_H * WORLD_H
        cam.fly_to(wx, wy)
        return True

    def _minimap_rect(self) -> Optional[pygame.Rect]:
        if self._panel_slide < 0.05:
            return None
        SW   = config.SCREEN_W
        PH   = int(BOTTOM_PANEL_H * self._panel_slide)
        py   = config.SCREEN_H - PH
        MM_W = scaled(160)
        MM_H = scaled(112)
        pad  = scaled(12)
        return pygame.Rect(SW - MM_W - pad, py + (PH - MM_H) // 2, MM_W, MM_H)

    # ── BARRA DE FILTROS (topo) ───────────────────────────────────────────

    def draw_filter_bar(self, screen, gods, zones, ownership, cam: Camera,
                        fps: float, t: float):
        SW = config.SCREEN_W
        FH = self.HUD_H

        # Fundo
        pygame.draw.rect(screen, UI_BG, (0, 0, SW, FH))
        # Linha sépia na base
        p = int(140 + math.sin(t * 2) * 40)
        pygame.draw.line(screen, (p, int(p * 0.83), int(p * 0.38)),
                         (0, FH - 1), (SW, FH - 1), 1)

        f_title = self._fc.get(scaled(13), bold=True, serif=True)
        f_btn   = self._fc.get(scaled(11), bold=True)
        f_info  = self._fc.get(scaled(10))

        # Título
        title = f_title.render("⚔ AETHERMOOR", True, GOLD)
        screen.blit(title, (scaled(12), (FH - title.get_height()) // 2))

        # Botões de filtro por natureza
        natures_available = sorted(set(z.base_nature for z in zones.values()))
        pad = scaled(8)
        x   = scaled(12) + title.get_width() + scaled(20)

        for nat in (["all"] + natures_available):
            lbl    = "TODOS" if nat == "all" else nat.upper()
            col    = NATURE_COLOR.get(nat, TXT_DIM) if nat != "all" else TXT
            active = (self.active_filter == nat)

            w   = f_btn.size(lbl)[0] + pad * 2
            btn = pygame.Rect(x, 3, w, FH - 6)

            # Fundo do botão
            if active:
                _rrect(screen, col, btn, r=3, alpha=55)
                pygame.draw.rect(screen, col, btn, 1, border_radius=3)
            else:
                _rrect(screen, UI_LINE, btn, r=3, alpha=80)

            lbl_s = f_btn.render(lbl, True, col if active else TXT_MUTED)
            screen.blit(lbl_s, lbl_s.get_rect(center=btn.center))
            x += w + scaled(4)

        # Info direita: stats + zoom + fps
        n_claimed = sum(1 for v in ownership.values() if v)
        info = f_info.render(
            f"Zonas: {n_claimed}/{len(zones)}  ·  "
            f"Zoom: {cam.zoom:.2f}×  ·  FPS: {fps:.0f}",
            True, TXT_MUTED)
        screen.blit(info, (SW - info.get_width() - scaled(14),
                            (FH - info.get_height()) // 2))

    # ── PAINEL INFERIOR (slide-in) ────────────────────────────────────────

    def draw_bottom_panel(self, screen, selected_zone: Optional[Zone],
                          gods, zones, ownership, ancient_seals,
                          global_stats, t: float,
                          event_log=None, ancient_gods=None):
        if self._panel_slide < 0.02:
            return

        SW  = config.SCREEN_W
        PH  = int(BOTTOM_PANEL_H * self._panel_slide)
        py  = config.SCREEN_H - PH
        pad = scaled(14)

        # ── Fundo ────────────────────────────────────────────────────────
        bg = pygame.Surface((SW, PH), pygame.SRCALPHA)
        bg.fill((*UI_BG, 245))
        # gradiente de topo (linha mais clara)
        for i in range(min(4, PH)):
            a = int(80 * (1 - i / 4))
            pygame.draw.line(bg, (*GOLD, a), (0, i), (SW, i))
        screen.blit(bg, (0, py))

        # Borda ornamental superior
        _draw_ornate_border(screen,
                            pygame.Rect(0, py, SW, PH),
                            col=GOLD, alpha=160, thick=1)

        if PH < scaled(30):
            return   # muito pequeno para desenhar conteúdo

        # ── Divisão em 3 colunas ─────────────────────────────────────────
        MM_W   = scaled(160)
        MM_PAD = scaled(12)
        col1_x = pad
        col1_w = SW // 2 - pad
        col2_x = SW // 2 + pad
        col2_w = SW - SW // 2 - MM_W - MM_PAD * 2 - pad
        # col3 = minimap (desenhado separadamente)

        pygame.draw.line(screen,
                         (*UI_LINE, 180),
                         (SW // 2, py + scaled(8)),
                         (SW // 2, py + PH - scaled(8)))

        # ── Coluna 1: Zona selecionada ────────────────────────────────────
        content_h = 0
        if selected_zone:
            content_h = self._draw_zone_info(screen, selected_zone, gods, ownership,
                                             ancient_seals, col1_x, py, col1_w, PH,
                                             t, event_log=event_log,
                                             ancient_gods=ancient_gods)

        # ── Coluna 2: Events + Stats ──────────────────────────────────────
        col2_h = self._draw_events_panel(screen, event_log, gods, zones,
                                         ownership, ancient_seals,
                                         col2_x, py, col2_w, PH)
        self._panel_content_h = max(content_h, col2_h)

        # ── Coluna 3: Minimap ─────────────────────────────────────────────
        self._draw_minimap(screen, zones, ownership, py, PH)

    def _draw_zone_info(self, screen, zone: Zone, gods, ownership,
                         ancient_seals, x, py, w, PH, t,
                         event_log=None, ancient_gods=None) -> int:
        """Retorna a altura total do conteúdo desenhado (para scroll)."""
        pad   = scaled(10)
        y     = py + pad
        f_big = self._fc.get(scaled(18), bold=True, serif=True)
        f_med = self._fc.get(scaled(12), serif=True)
        f_sm  = self._fc.get(scaled(11), serif=True)
        f_xs  = self._fc.get(scaled(10))

        nc = NATURE_COLOR.get(zone.base_nature, TXT)

        # Barra de cor da natureza no lado esquerdo
        bar_h = min(PH - pad * 2, scaled(100))
        pygame.draw.rect(screen, nc, (x - scaled(6), y, scaled(3), bar_h), border_radius=2)

        # Nome da zona (grande, serif, dourado)
        name_surf = f_big.render(zone.zone_name, True, GOLD)
        if name_surf.get_width() > w - pad:
            f_big2 = self._fc.get(scaled(14), bold=True, serif=True)
            name_surf = f_big2.render(zone.zone_name, True, GOLD)
        screen.blit(name_surf, (x + pad, y))
        y += name_surf.get_height() + scaled(2)

        # Região · Natureza
        sub = f_sm.render(f"{zone.region_name}  ·  {zone.base_nature.upper()}",
                          True, nc)
        screen.blit(sub, (x + pad, y))
        y += sub.get_height() + scaled(6)

        # Lore (até 2 linhas)
        lore_lines = _wrap(zone.lore, f_xs, w - pad * 2)
        for i, line in enumerate(lore_lines[:2]):
            ls = f_xs.render(line, True, TXT_DIM)
            screen.blit(ls, (x + pad, y))
            y += ls.get_height() + scaled(2)
        if len(lore_lines) > 2:
            dots = f_xs.render("...", True, TXT_MUTED)
            screen.blit(dots, (x + pad, y))
        y += scaled(8)

        # Status de posse
        gid = ownership.get(zone.zone_id)
        if gid:
            god = gods.get(gid)
            if god:
                r2, g2, b2 = god.rgb()
                owner_lbl = f_xs.render("CONTROLADA POR", True, TXT_MUTED)
                screen.blit(owner_lbl, (x + pad, y))
                y += owner_lbl.get_height() + scaled(2)
                pygame.draw.rect(screen, (r2, g2, b2),
                                 (x + pad, y, scaled(3), scaled(16)),
                                 border_radius=1)
                owner_name = f_med.render(god.god_name, True, (r2, g2, b2))
                screen.blit(owner_name, (x + pad + scaled(7), y))
                y += scaled(18)
        elif zone.ancient_seal:
            sd     = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            crack  = sd.get("crack_level", zone.crack_level)
            maxc   = sd.get("max_cracks",  zone.max_cracks)
            scol   = SEAL_COLOR.get(status, TXT_DIM)
            seal_lbl = f_xs.render("SELO ANTIGO", True, TXT_MUTED)
            screen.blit(seal_lbl, (x + pad, y))
            y += seal_lbl.get_height() + scaled(2)
            status_s = f_med.render(status.upper(), True, scol)
            screen.blit(status_s, (x + pad, y))
            # Crackinhas
            for ci in range(maxc):
                col_c = GOLD if ci < crack else (55, 45, 30)
                pygame.draw.rect(screen, col_c,
                                 (x + pad + scaled(80) + ci * scaled(14),
                                  y + scaled(2), scaled(11), scaled(10)),
                                 border_radius=2)
            y += scaled(18)

            # Lore do deus antigo associado (se disponível)
            if ancient_gods:
                ag = next(
                    (a for a in ancient_gods.values() if a.seal_zone == zone.zone_id),
                    None,
                )
                if ag and y + scaled(14) < py + PH - pad:
                    ar, ag2, ab = ag.rgb()
                    ag_lbl = f_xs.render("DEUS APRISIONADO", True, TXT_MUTED)
                    screen.blit(ag_lbl, (x + pad, y))
                    y += ag_lbl.get_height() + scaled(2)
                    ag_name = f_med.render(ag.god_name, True, (ar, ag2, ab))
                    screen.blit(ag_name, (x + pad, y))
                    y += ag_name.get_height() + scaled(2)
                    if ag.lore_description and y + scaled(10) < py + PH - pad:
                        lore2 = _wrap(ag.lore_description, f_xs, w - pad * 2)
                        for line in lore2[:1]:
                            ls = f_xs.render(line, True, TXT_DIM)
                            screen.blit(ls, (x + pad, y))
                            y += ls.get_height() + scaled(2)
        else:
            uncl = f_med.render("NÃO REIVINDICADA", True, TXT_MUTED)
            screen.blit(uncl, (x + pad, y))
            y += uncl.get_height() + scaled(6)

        # ── Eventos desta zona ────────────────────────────────────────────
        if event_log and y + scaled(20) < py + PH - pad:
            zone_evs = event_log.for_zone(zone.zone_id)
            if zone_evs:
                y += scaled(4)
                pygame.draw.line(screen, (*UI_LINE, 120),
                                 (x + pad, y), (x + pad + w - pad * 2, y))
                y += scaled(5)
                ev_hdr = f_xs.render("EVENTOS", True, TXT_MUTED)
                screen.blit(ev_hdr, (x + pad, y))
                y += ev_hdr.get_height() + scaled(3)

                f_ev = self._fc.get(scaled(9))
                for ev in zone_evs[:3]:
                    if y + scaled(11) > py + PH - pad:
                        break
                    sev_col = SEVERITY_COLOR[ev.severity]
                    sev_lbl = SEVERITY_LABEL.get(ev.severity, "")
                    sl  = f_ev.render(sev_lbl, True, sev_col)
                    desc_max = w - pad * 2 - sl.get_width() - scaled(5)
                    desc_lines = _wrap(ev.description, f_ev, desc_max)
                    dl = f_ev.render(desc_lines[0] if desc_lines else "", True, TXT_DIM)
                    # Acento colorido
                    pygame.draw.rect(screen, sev_col,
                                     (x + pad, y + scaled(2), scaled(2),
                                      sl.get_height() - scaled(2)),
                                     border_radius=1)
                    screen.blit(sl, (x + pad + scaled(5), y))
                    screen.blit(dl, (x + pad + scaled(5) + sl.get_width() + scaled(4), y))
                    y += sl.get_height() + scaled(3)

        return y - py   # altura total do conteúdo

    def _draw_events_panel(self, screen, event_log, gods, zones, ownership,
                            ancient_seals, x, py, w, PH) -> int:
        """
        Coluna 2 do painel inferior:
          - Stats globais compactos (topo)
          - Feed de eventos recentes ordenado por severidade (corpo)
          - Deuses ativos em cards compactos (fim, se sobrar espaço)

        Retorna altura total do conteúdo para cálculo de scroll.
        """
        pad   = scaled(10)
        y     = py + pad
        f_hdr = self._fc.get(scaled(11), bold=True)
        f_med = self._fc.get(scaled(11), serif=True)
        f_sm  = self._fc.get(scaled(10))
        f_xs  = self._fc.get(scaled(9))

        # ── Stats globais compactos ───────────────────────────────────────
        n_claimed = sum(1 for v in ownership.values() if v)
        n_seals   = sum(1 for z in zones.values() if z.ancient_seal)
        n_active  = sum(1 for z in zones.values()
                        if z.ancient_seal and
                        ancient_seals.get(z.zone_id, {}).get("status") != "sleeping")

        stats_pairs = [
            ("Zonas",  f"{n_claimed}/{len(zones)}", GOLD),
            ("Selos",  f"{n_active}/{n_seals} ativos", CRIMSON),
            ("Deuses", str(len(gods)), CYAN),
        ]
        sx = x
        for lbl, val, col in stats_pairs:
            ls = f_xs.render(lbl + ":", True, TXT_MUTED)
            vs = f_xs.render(val,       True, col)
            screen.blit(ls, (sx, y))
            screen.blit(vs, (sx + ls.get_width() + scaled(3), y))
            sx += ls.get_width() + vs.get_width() + scaled(14)
        y += f_xs.get_height() + scaled(4)

        # ── Alerta de eventos críticos/high no topo ───────────────────────
        if event_log:
            crit = event_log.critical_count
            high = event_log.high_count
            if crit > 0:
                alert = f_sm.render(
                    f"! {crit} CRITICAL  {high} HIGH", True, CRIMSON)
                screen.blit(alert, (x, y))
                y += alert.get_height() + scaled(3)

        pygame.draw.line(screen, (*UI_LINE, 140),
                         (x, y), (x + w, y))
        y += scaled(5)

        # ── Cabeçalho da feed ─────────────────────────────────────────────
        hdr = f_hdr.render("WORLD EVENTS", True, TXT_DIM)
        screen.blit(hdr, (x, y))
        y += hdr.get_height() + scaled(4)

        # ── Feed de eventos ───────────────────────────────────────────────
        if event_log:
            events = event_log.recent
        else:
            events = []

        ev_h  = f_xs.get_height() + scaled(5)   # altura por evento
        avail = py + PH - y - pad - scaled(36)   # espaço disponível (reserva para god cards)
        max_ev = max(1, avail // ev_h)

        for ev in events[:max_ev]:
            if y + ev_h > py + PH - pad:
                break

            sev_col = SEVERITY_COLOR[ev.severity]
            vfx_col = EVENT_VFX.get(ev.type, {}).get("color", sev_col)
            shape   = EVENT_VFX.get(ev.type, {}).get("shape", "circle")

            # Ícone geométrico pequeno
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

            # Linha colorida de severidade
            pygame.draw.line(screen, sev_col,
                             (x + scaled(10), y + ev_h - scaled(2)),
                             (x + scaled(10) + scaled(20), y + ev_h - scaled(2)), 1)

            # Descrição
            max_desc_w = w - scaled(14)
            desc_lines = _wrap(ev.description, f_xs, max_desc_w)
            dl = f_xs.render(desc_lines[0] if desc_lines else "", True, TXT_DIM)
            screen.blit(dl, (x + scaled(12), y + scaled(1)))

            # Timestamp compacto à direita
            ts = ev.timestamp[11:16] if len(ev.timestamp) >= 16 else ""
            if ts:
                ts_s = f_xs.render(ts, True, TXT_MUTED)
                screen.blit(ts_s, (x + w - ts_s.get_width(), y + scaled(1)))

            y += ev_h

        # ── God cards compactos (se sobrou espaço) ────────────────────────
        y += scaled(4)
        if y + scaled(22) < py + PH - pad:
            pygame.draw.line(screen, (*UI_LINE, 100),
                             (x, y), (x + w, y))
            y += scaled(4)
            gods_sorted = sorted(gods.values(), key=lambda g: -sum(
                1 for gid in ownership.values() if gid == g.god_id))
            card_h = scaled(20)
            for god in gods_sorted:
                if y + card_h > py + PH - pad:
                    break
                r2, g2, b2 = god.rgb()
                owned = sum(1 for gid in ownership.values() if gid == god.god_id)
                # Barra fina de território
                bar_w = max(0, int(w * owned / max(len(zones), 1)))
                if bar_w > 0:
                    _rrect(screen, (r2, g2, b2),
                           pygame.Rect(x, y, bar_w, card_h), r=2, alpha=25)
                pygame.draw.rect(screen, (r2, g2, b2),
                                 (x, y, scaled(2), card_h), border_radius=1)
                ns = f_xs.render(god.god_name, True, (r2, g2, b2))
                zt = f_xs.render(f"{owned}z", True, TXT_MUTED)
                screen.blit(ns, (x + scaled(5), y + (card_h - ns.get_height()) // 2))
                screen.blit(zt, (x + w - zt.get_width() - scaled(3),
                                 y + (card_h - zt.get_height()) // 2))
                y += card_h + scaled(2)

        return y - py

    def _draw_minimap(self, screen, zones, ownership, py, PH):
        """
        Minimap: versão reduzida do mapa mostrando ownership por zona.
        Renderizado em Surface dedicada e cacheada (só recalcula quando dirty).
        """
        mm_rect = self._minimap_rect()
        if mm_rect is None:
            return

        MM_W = mm_rect.width
        MM_H = mm_rect.height

        if self._minimap_dirty or self._minimap_surf is None:
            self._minimap_surf = self._build_minimap(zones, ownership, MM_W, MM_H)
            self._minimap_dirty = False

        # Fundo do minimap
        pygame.draw.rect(screen, (28, 22, 14), mm_rect, border_radius=3)
        screen.blit(self._minimap_surf, mm_rect.topleft)
        _draw_ornate_border(screen, mm_rect, col=GOLD, alpha=150, thick=1)

    def _build_minimap(self, zones, ownership, MM_W, MM_H) -> pygame.Surface:
        from .config import WORLD_W, WORLD_H
        surf = pygame.Surface((MM_W, MM_H), pygame.SRCALPHA)
        surf.fill((38, 30, 20, 240))

        def w2mm(wx, wy):
            return (int(wx / WORLD_W * MM_W), int(wy / WORLD_H * MM_H))

        for zone in zones.values():
            gid = ownership.get(zone.zone_id)
            if not gid:
                col = (60, 55, 45, 80)
            else:
                # Precisaria de gods aqui — simplificamos com cor neutra
                col = (90, 80, 60, 100)

            verts = [w2mm(wx, wy) for wx, wy in zone.vertices]
            if len(verts) >= 3:
                pygame.draw.polygon(surf, col, verts)
                pygame.draw.polygon(surf, (80, 65, 40, 120), verts, 1)

        return surf

    def _build_minimap_with_gods(self, zones, ownership, gods, MM_W, MM_H) -> pygame.Surface:
        """Versão com cores dos deuses — chamada quando gods está disponível."""
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
                fill_col   = (r, g, b, 120)
                border_col = (r, g, b, 180)
            else:
                fill_col   = (55, 48, 38, 70)
                border_col = (75, 65, 50, 110)

            verts = [w2mm(wx, wy) for wx, wy in zone.vertices]
            if len(verts) >= 3:
                pygame.draw.polygon(surf, fill_col,   verts)
                pygame.draw.polygon(surf, border_col, verts, 1)

        return surf

    def draw_bottom_panel_with_gods(self, screen, selected_zone, gods, zones,
                                     ownership, ancient_seals, global_stats, t,
                                     event_log=None, ancient_gods=None):
        """
        Versão completa chamada pelo main.py.
        Reconstrói o minimap com cores reais dos deuses.
        Passa event_log e ancient_gods para o painel.
        """
        if self._minimap_dirty or self._minimap_surf is None:
            mm_rect = self._minimap_rect()
            if mm_rect:
                self._minimap_surf = self._build_minimap_with_gods(
                    zones, ownership, gods, mm_rect.width, mm_rect.height)
                self._minimap_dirty = False

        self.draw_bottom_panel(screen, selected_zone, gods, zones,
                               ownership, ancient_seals, global_stats, t,
                               event_log=event_log, ancient_gods=ancient_gods)

    # ── HUD topo (compat stub → chama filter bar) ─────────────────────────

    def draw_top_hud(self, screen, gods, zones, ownership, cam, fps, t):
        """[COMPAT] Agora chama draw_filter_bar."""
        self.draw_filter_bar(screen, gods, zones, ownership, cam, fps, t)

    # ── Stubs de compatibilidade (removidos na Fase 4) ────────────────────

    def draw_left_panel(self, screen, gods, zones, ownership,
                        selected_zone, ancient_seals, global_stats):
        """[REMOVIDO] Painel lateral não existe mais."""
        return

    def draw_seals_panel(self, screen, zones, ancient_seals, t):
        """[REMOVIDO] Integrado no bottom panel."""
        return

    # ── TOOLTIP de hover ─────────────────────────────────────────────────

    def draw_hover_tooltip(self, screen, zone, gods, ownership,
                            ancient_seals, mx: int, my: int):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        if zone is None or mx < self.map_x or my < self.map_y:
            return

        f_hdr = self._fc.get(scaled(13), bold=True, serif=True)
        f_sm  = self._fc.get(scaled(11), serif=True)
        f_xs  = self._fc.get(scaled(10))
        nc    = NATURE_COLOR.get(zone.base_nature, TXT_DIM)

        rows = [
            (zone.zone_name,   TXT,     f_hdr),
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

        # Fundo
        bg = pygame.Surface((TW, TH), pygame.SRCALPHA)
        bg.fill((*UI_BG, 240))
        screen.blit(bg, (tx, ty))

        # Borda ornamental
        _draw_ornate_border(screen,
                            pygame.Rect(tx, ty, TW, TH),
                            col=GOLD, alpha=160, thick=1)

        # Acento lateral na cor da natureza
        pygame.draw.line(screen, nc, (tx + 1, ty + 4), (tx + 1, ty + TH - 4), 2)

        oy = scaled(8)
        for text, col, font in rows:
            screen.blit(font.render(text, True, col), (tx + scaled(10), ty + oy))
            oy += font.get_height() + scaled(3)

    # ── NOTIFICAÇÃO ───────────────────────────────────────────────────────

    def draw_notif(self, screen):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        if self._notif_alpha <= 0:
            return
        f = self._fc.get(scaled(14), bold=True, serif=True)
        s = f.render(self._notif_msg, True, GOLD)
        pw = s.get_width() + scaled(30)
        ph = s.get_height() + scaled(16)
        px = SW // 2 - pw // 2
        py = self._panel_y - ph - scaled(10)
        a  = int(220 * self._notif_alpha)

        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((*UI_BG, a))
        screen.blit(bg, (px, py))
        _draw_ornate_border(screen,
                            pygame.Rect(px, py, pw, ph),
                            col=GOLD, alpha=min(255, a + 20), thick=1)
        bg.blit(s, (scaled(15), scaled(8)))
        screen.blit(s, (px + scaled(15), py + scaled(8)))

    # ── CANTOS DECORATIVOS ────────────────────────────────────────────────

    def draw_corners(self, screen):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        L  = scaled(22)
        for px_, py_, w_, h_ in [
            (0,      0,      L, 2), (0,      0,      2, L),
            (SW - L, 0,      L, 2), (SW - 2, 0,      2, L),
            (0,      SH - 2, L, 2), (0,      SH - L, 2, L),
            (SW - L, SH - 2, L, 2), (SW - 2, SH - L, 2, L),
        ]:
            pygame.draw.rect(screen, GOLD, (px_, py_, w_, h_))

    # ── LOADING ───────────────────────────────────────────────────────────

    def draw_loading(self, screen, msg: str, pct: float):
        SW = config.SCREEN_W
        SH = config.SCREEN_H
        screen.fill(UI_BG)

        f_title = self._fc.get(scaled(22), bold=True, serif=True)
        f_sub   = self._fc.get(scaled(11))
        f_msg   = self._fc.get(scaled(11))

        t = f_title.render("⚔  NEURAL FIGHTS — AETHERMOOR", True, GOLD)
        screen.blit(t, ((SW - t.get_width()) // 2, SH // 2 - scaled(72)))

        sub = f_sub.render("W O R L D  M A P  L O A D I N G", True, TXT_DIM)
        screen.blit(sub, ((SW - sub.get_width()) // 2, SH // 2 - scaled(44)))

        BW = min(scaled(480), SW - scaled(60))
        BH = scaled(6)
        bx = (SW - BW) // 2
        by = SH // 2 - scaled(4)

        pygame.draw.rect(screen, UI_LINE, (bx - 1, by - 1, BW + 2, BH + 2), border_radius=3)
        pygame.draw.rect(screen, (35, 28, 16), (bx, by, BW, BH), border_radius=3)
        if pct > 0:
            pygame.draw.rect(screen, GOLD, (bx, by, int(BW * pct), BH), border_radius=3)

        m = f_msg.render(msg, True, TXT_DIM)
        screen.blit(m, ((SW - m.get_width()) // 2, by + BH + scaled(10)))

        # Borda ornamental na tela de loading
        _draw_ornate_border(screen,
                            pygame.Rect(scaled(20), scaled(20),
                                        SW - scaled(40), SH - scaled(40)),
                            col=GOLD_DIM, alpha=120, thick=1)

        self.draw_corners(screen)
        pygame.display.flip()
        pygame.event.pump()
