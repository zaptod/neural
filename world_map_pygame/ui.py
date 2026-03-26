"""
World Map — WorldBox-style UI
Left sidebar toolbar, top control bar, info panel, brush cursor.
"""
import pygame
import math
try:
    from .config import GOD_COLORS, SCR
    from .tools import TOOL_CATEGORIES, BRUSH_SIZES, MATERIALS, MAT_NAMES
except ImportError:  # pragma: no cover - direct script fallback
    from config import GOD_COLORS, SCR
    from tools import TOOL_CATEGORIES, BRUSH_SIZES, MATERIALS, MAT_NAMES

# ─── Layout ───────────────────────────────────────────────────────────────────
SIDEBAR_W       = 52
TOPBAR_H        = 32
INFO_PANEL_W    = 260
INFO_PANEL_H    = 340
TOOL_PANEL_W    = 180
BOTTOMBAR_H     = 80

# colours
C_BG_DARK   = (12, 12, 18)
C_BG_MID    = (22, 22, 32)
C_BG_LIGHT  = (32, 32, 46)
C_BORDER    = (50, 50, 66)
C_TEXT       = (180, 180, 200)
C_TEXT_DIM   = (100, 100, 120)
C_TEXT_BRIGHT= (230, 230, 240)
C_ACCENT     = (80, 160, 255)
C_HOVER      = (45, 45, 65)
C_SELECTED   = (55, 55, 80)

# ─── Pixel-art icon data (5x5 grids) ──────────────────────────────────────────
_ICONS = {
    'eye':     [[0,1,1,1,0],[1,0,1,0,1],[1,1,1,1,1],[1,0,1,0,1],[0,1,1,1,0]],
    'mountain':[[0,0,1,0,0],[0,1,1,1,0],[0,1,0,1,0],[1,1,0,1,1],[1,0,0,0,1]],
    'fire':    [[0,0,1,0,0],[0,1,1,0,0],[0,1,1,1,0],[1,1,1,1,0],[0,1,1,0,0]],
    'tree':    [[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,0,1,0,0],[0,0,1,0,0]],
    'bolt':    [[0,0,1,0,0],[0,1,1,0,0],[1,1,1,1,0],[0,0,1,1,0],[0,0,1,0,0]],
    'halo':    [[0,1,1,1,0],[1,0,0,0,1],[1,0,0,0,1],[1,0,0,0,1],[0,1,1,1,0]],
    'eraser':  [[1,1,1,0,0],[1,0,1,0,0],[1,1,1,1,0],[0,0,1,0,1],[0,0,0,1,1]],
    'flag':    [[1,1,1,0,0],[1,0,1,0,0],[1,1,1,0,0],[1,0,0,0,0],[1,0,0,0,0]],
    'hammer':  [[1,1,1,0,0],[1,1,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0]],
    'sword':   [[0,0,0,0,1],[0,0,0,1,0],[0,0,1,0,0],[0,1,1,0,0],[1,0,0,0,0]],
    'cloud':   [[0,1,1,1,0],[1,1,1,1,1],[1,1,1,1,1],[0,0,0,0,0],[0,0,0,0,0]],
}


def _render_icon(icon_key, color, size=20):
    grid = _ICONS.get(icon_key)
    if not grid:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, color, (2, 2, size - 4, size - 4))
        return s
    rows, cols = len(grid), len(grid[0])
    ps = max(1, size // cols)
    surf = pygame.Surface((cols * ps, rows * ps), pygame.SRCALPHA)
    for ry, row in enumerate(grid):
        for rx, v in enumerate(row):
            if v:
                pygame.draw.rect(surf, color, (rx * ps, ry * ps, ps, ps))
    return surf


class WorldBoxUI:
    """Full WorldBox-style UI system."""

    def __init__(self, tool_state, gods):
        self.ts         = tool_state
        self.gods       = gods
        self._ready     = False
        self.font_lg    = None
        self.font_sm    = None
        self.font_xs    = None
        self.font_title = None

        # panels
        self.show_info_panel  = False
        self.show_tool_panel  = True
        self.info_data        = {}

        # hover state
        self.hover_tile   = None
        self.hover_biome  = ""
        self.hover_god    = None
        self.hover_str    = 0.0
        self.hover_mat    = "none"
        self.hover_elev   = 0.0
        self.hover_moist  = 0.0
        self.hover_temp   = 0.0
        self.hover_weather = None
        self.hover_building = None
        self.hover_units  = 0

        # events
        self.events       = []

        # standings
        self.standings    = []

        # rectangles for click detection
        self._cat_rects   = []
        self._tool_rects  = []
        self._brush_rects = []
        self._god_rects   = []
        self._topbar_btns = {}

        # icon cache
        self._icon_cache  = {}

    # ── lazy font init ─────────────────────────────────────────────────────
    def _init_fonts(self):
        if self._ready:
            return
        pygame.font.init()
        self.font_title = pygame.font.SysFont("consolas", 16, bold=True)
        self.font_lg    = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_sm    = pygame.font.SysFont("consolas", 12)
        self.font_xs    = pygame.font.SysFont("consolas", 10)
        self._ready     = True

    # ── setters ────────────────────────────────────────────────────────────
    def set_hover(self, tx, ty, biome, god_id, strength, mat, elev, moist,
                  temp=0.0, weather=None, building=None, unit_count=0):
        self.hover_tile  = (tx, ty)
        self.hover_biome = biome
        self.hover_god   = god_id
        self.hover_str   = strength
        self.hover_mat   = mat
        self.hover_elev  = elev
        self.hover_moist = moist
        self.hover_temp  = temp
        self.hover_weather = weather
        self.hover_building = building
        self.hover_units = unit_count

    def set_info(self, data):
        self.info_data = data
        self.show_info_panel = True

    def close_info(self):
        self.show_info_panel = False

    def add_event(self, text):
        self.events.append(text)
        if len(self.events) > 100:
            self.events = self.events[-100:]

    def set_standings(self, standings):
        self.standings = standings

    # ── hit testing ────────────────────────────────────────────────────────
    def handle_click(self, mx, my):
        """Returns True if click was consumed by UI, False if it should go to map."""
        # Sidebar categories
        for i, r in enumerate(self._cat_rects):
            if r.collidepoint(mx, my):
                self.ts.set_category(i)
                self.show_tool_panel = True
                return True

        # Tool panel items
        if self.show_tool_panel:
            for i, r in enumerate(self._tool_rects):
                if r.collidepoint(mx, my):
                    self.ts.set_tool(i)
                    return True

        # Brush sizes
        for i, r in enumerate(self._brush_rects):
            if r.collidepoint(mx, my):
                self.ts.brush_idx = i
                return True

        # God selector
        for i, r in enumerate(self._god_rects):
            if r.collidepoint(mx, my):
                self.ts.selected_god = i
                return True

        # Top bar buttons
        for key, r in self._topbar_btns.items():
            if r.collidepoint(mx, my):
                if key == 'pause':
                    self.ts.toggle_pause()
                elif key == 'speed':
                    self.ts.cycle_speed()
                elif key == 'info_toggle':
                    self.show_info_panel = not self.show_info_panel
                return True

        # Info panel area
        if self.show_info_panel:
            ipx = SCR.w - INFO_PANEL_W - 10
            ipy = TOPBAR_H + 10
            ip_rect = pygame.Rect(ipx, ipy, INFO_PANEL_W, INFO_PANEL_H)
            if ip_rect.collidepoint(mx, my):
                return True

        return False

    def is_over_ui(self, mx, my):
        """True if mouse is over any UI element."""
        if mx < SIDEBAR_W:
            return True
        if my < TOPBAR_H:
            return True
        if my >= SCR.h - BOTTOMBAR_H:
            return True
        if self.show_tool_panel and mx < SIDEBAR_W + TOOL_PANEL_W + 4:
            cat = self.ts.category
            tool_count = len(cat['tools'])
            panel_h = 40 + tool_count * 28 + 90 + len(BRUSH_SIZES) * 18 + 20
            if my < TOPBAR_H + panel_h + 10:
                return True
        if self.show_info_panel:
            ipx = SCR.w - INFO_PANEL_W - 10
            ipy = TOPBAR_H + 10
            if mx >= ipx and my >= ipy and my < ipy + INFO_PANEL_H + 80:
                return True
        return False

    # ══════════════════════════════════════════════════════════════════════
    #  RENDER
    # ══════════════════════════════════════════════════════════════════════
    def render(self, screen, fps=0, season='spring', pop=0, unit_count=0,
               building_count=0, weather_zones=0, era='', army_count=0,
               war_count=0):
        self._init_fonts()
        self._season = season
        self._pop = pop
        self._unit_count = unit_count
        self._building_count = building_count
        self._weather_zones = weather_zones
        self._era = era
        self._army_count = army_count
        self._war_count = war_count
        self._draw_topbar(screen, fps)
        self._draw_sidebar(screen)
        if self.show_tool_panel:
            self._draw_tool_panel(screen)
        if self.show_info_panel:
            self._draw_info_panel(screen)
        self._draw_bottom_bar(screen)
        self._draw_brush_cursor(screen)

    # ── top bar ────────────────────────────────────────────────────────────
    def _draw_topbar(self, screen, fps):
        pygame.draw.rect(screen, C_BG_DARK, (0, 0, SCR.w, TOPBAR_H))
        pygame.draw.line(screen, C_BORDER, (0, TOPBAR_H - 1), (SCR.w, TOPBAR_H - 1))

        # Title
        s = self.font_lg.render("AETHERMOOR", True, C_ACCENT)
        screen.blit(s, (SIDEBAR_W + 8, 8))

        # Sim controls
        bx = SIDEBAR_W + 140
        btn_w, btn_h = 60, 22

        # Pause / Play
        paused = self.ts.sim_paused
        pr = pygame.Rect(bx, 5, btn_w, btn_h)
        self._topbar_btns['pause'] = pr
        pc = (200, 80, 80) if paused else (80, 200, 100)
        pygame.draw.rect(screen, C_BG_LIGHT, pr, border_radius=3)
        pygame.draw.rect(screen, pc, pr, 1, border_radius=3)
        lbl = "PLAY" if paused else "PAUSE"
        screen.blit(self.font_xs.render(lbl, True, pc), (bx + 10, 10))

        # Speed
        bx += btn_w + 6
        sr = pygame.Rect(bx, 5, 36, btn_h)
        self._topbar_btns['speed'] = sr
        pygame.draw.rect(screen, C_BG_LIGHT, sr, border_radius=3)
        pygame.draw.rect(screen, C_BORDER, sr, 1, border_radius=3)
        screen.blit(self.font_xs.render(f"{self.ts.sim_speed}x", True, C_TEXT), (bx + 8, 10))

        # Info toggle
        bx += 44
        ir = pygame.Rect(bx, 5, 36, btn_h)
        self._topbar_btns['info_toggle'] = ir
        ic = C_ACCENT if self.show_info_panel else C_TEXT_DIM
        pygame.draw.rect(screen, C_BG_LIGHT, ir, border_radius=3)
        pygame.draw.rect(screen, ic, ir, 1, border_radius=3)
        screen.blit(self.font_xs.render("INFO", True, ic), (bx + 4, 10))

        # FPS
        if fps > 0:
            fs = self.font_xs.render(f"FPS:{int(fps)}", True, C_TEXT_DIM)
            screen.blit(fs, (SCR.w - 56, 10))

        # Season + stats
        season = getattr(self, '_season', 'spring')
        pop = getattr(self, '_pop', 0)
        season_colors = {'spring': (120,200,80), 'summer': (220,180,40),
                         'autumn': (200,120,40), 'winter': (140,180,220)}
        sc = season_colors.get(season, C_TEXT)
        s_season = self.font_xs.render(season.upper(), True, sc)
        screen.blit(s_season, (SCR.w - 120, 10))

        # Current tool name
        tname = self.ts.tool['name']
        tn = self.font_sm.render(tname, True, self.ts.category['color'])
        screen.blit(tn, (SCR.w - 230, 9))

    # ── sidebar ────────────────────────────────────────────────────────────
    def _draw_sidebar(self, screen):
        pygame.draw.rect(screen, C_BG_DARK, (0, TOPBAR_H, SIDEBAR_W, SCR.h - TOPBAR_H))
        pygame.draw.line(screen, C_BORDER, (SIDEBAR_W - 1, TOPBAR_H), (SIDEBAR_W - 1, SCR.h))

        self._cat_rects = []
        cy = TOPBAR_H + 4
        # Adaptive button size: shrink if too many categories
        avail_h = SCR.h - TOPBAR_H - BOTTOMBAR_H - 8
        btn_size = min(40, max(28, (avail_h - len(TOOL_CATEGORIES) * 3) // len(TOOL_CATEGORIES)))
        gap = 3

        for i, cat in enumerate(TOOL_CATEGORIES):
            r = pygame.Rect(6, cy, btn_size, btn_size)
            self._cat_rects.append(r)

            is_sel = (i == self.ts.category_idx)
            bg = C_SELECTED if is_sel else C_BG_MID
            bc = cat['color'] if is_sel else C_BORDER

            pygame.draw.rect(screen, bg, r, border_radius=4)
            pygame.draw.rect(screen, bc, r, 1, border_radius=4)

            # icon
            icon_key = cat['icon']
            icon_sz = max(12, btn_size - 12)
            cache_key = (icon_key, cat['color'], is_sel, icon_sz)
            if cache_key not in self._icon_cache:
                c = cat['color'] if is_sel else tuple(min(255, v + 40) for v in C_TEXT_DIM)
                self._icon_cache[cache_key] = _render_icon(icon_key, c, icon_sz)
            icon_s = self._icon_cache[cache_key]
            screen.blit(icon_s, (r.x + (btn_size - icon_s.get_width()) // 2,
                                  r.y + (btn_size - icon_s.get_height()) // 2))

            cy += btn_size + gap

    # ── tool panel ─────────────────────────────────────────────────────────
    def _draw_tool_panel(self, screen):
        cat   = self.ts.category
        tools = cat['tools']
        px    = SIDEBAR_W + 2
        py    = TOPBAR_H + 4

        panel_h = 36 + len(tools) * 28 + 90 + len(BRUSH_SIZES) * 18 + 20
        if cat['id'] == 'divine':
            panel_h += len(self.gods) * 22 + 24

        # Panel background
        panel_r = pygame.Rect(px, py, TOOL_PANEL_W, panel_h)
        pygame.draw.rect(screen, C_BG_DARK, panel_r, border_radius=6)
        pygame.draw.rect(screen, C_BORDER, panel_r, 1, border_radius=6)

        # Category title
        s = self.font_lg.render(cat['name'].upper(), True, cat['color'])
        screen.blit(s, (px + 10, py + 8))
        ty = py + 32

        # Tools
        self._tool_rects = []
        for i, t in enumerate(tools):
            r = pygame.Rect(px + 6, ty, TOOL_PANEL_W - 12, 24)
            self._tool_rects.append(r)

            is_sel = (i == self.ts.tool_idx)
            bg = C_SELECTED if is_sel else C_BG_MID
            bc = cat['color'] if is_sel else C_BORDER

            pygame.draw.rect(screen, bg, r, border_radius=3)
            if is_sel:
                pygame.draw.rect(screen, bc, r, 1, border_radius=3)

            tc = C_TEXT_BRIGHT if is_sel else C_TEXT
            screen.blit(self.font_sm.render(t['name'], True, tc), (r.x + 8, r.y + 5))
            ty += 28

        # Brush size section
        ty += 8
        screen.blit(self.font_xs.render("BRUSH SIZE", True, C_TEXT_DIM), (px + 10, ty))
        ty += 16

        self._brush_rects = []
        for i, bs in enumerate(BRUSH_SIZES):
            r = pygame.Rect(px + 10, ty, TOOL_PANEL_W - 20, 16)
            self._brush_rects.append(r)

            is_sel = (i == self.ts.brush_idx)
            if is_sel:
                pygame.draw.rect(screen, C_SELECTED, r, border_radius=2)

            # visual bar
            bw = min(int(bs / 32 * (TOOL_PANEL_W - 50)), TOOL_PANEL_W - 50)
            bar_c = cat['color'] if is_sel else C_TEXT_DIM
            pygame.draw.rect(screen, bar_c, (r.x + 28, r.y + 4, bw, 8), border_radius=2)
            screen.blit(self.font_xs.render(str(bs), True, C_TEXT), (r.x + 4, r.y + 2))
            ty += 18

        # Tool description
        ty += 8
        desc = self.ts.tool.get('desc', '')
        if desc:
            words = desc.split()
            line = ""
            for w in words:
                test = line + " " + w if line else w
                if self.font_xs.size(test)[0] > TOOL_PANEL_W - 24:
                    screen.blit(self.font_xs.render(line, True, C_TEXT_DIM), (px + 10, ty))
                    ty += 13
                    line = w
                else:
                    line = test
            if line:
                screen.blit(self.font_xs.render(line, True, C_TEXT_DIM), (px + 10, ty))
                ty += 13

        # God selector (for divine tools)
        if cat['id'] == 'divine' and self.gods:
            ty += 8
            screen.blit(self.font_xs.render("SELECT GOD", True, C_TEXT_DIM), (px + 10, ty))
            ty += 16
            self._god_rects = []
            for i, g in enumerate(self.gods):
                r = pygame.Rect(px + 10, ty, TOOL_PANEL_W - 20, 18)
                self._god_rects.append(r)
                is_sel = (i == self.ts.selected_god)
                gid = g.get('god_id', '')
                gc = GOD_COLORS.get(gid, (128, 128, 128))
                if is_sel:
                    pygame.draw.rect(screen, C_SELECTED, r, border_radius=2)
                    pygame.draw.rect(screen, gc, r, 1, border_radius=2)
                pygame.draw.circle(screen, gc, (r.x + 8, r.y + 9), 5)
                nm = g.get('god_name', gid)
                if len(nm) > 22:
                    nm = nm[:20] + "..."
                screen.blit(self.font_xs.render(nm, True, gc if is_sel else C_TEXT), (r.x + 18, r.y + 3))
                ty += 22
        else:
            self._god_rects = []

    # ── info panel (right side) ────────────────────────────────────────────
    def _draw_info_panel(self, screen):
        px = SCR.w - INFO_PANEL_W - 10
        py = TOPBAR_H + 10
        # Dynamic height based on content
        panel_h = INFO_PANEL_H + 80
        panel_r = pygame.Rect(px, py, INFO_PANEL_W, panel_h)
        pygame.draw.rect(screen, C_BG_DARK, panel_r, border_radius=6)
        pygame.draw.rect(screen, C_BORDER, panel_r, 1, border_radius=6)

        y = py + 10

        # ── Hover info ─────────────────────
        if self.hover_tile:
            tx, ty2 = self.hover_tile
            screen.blit(self.font_lg.render("TILE INFO", True, C_ACCENT), (px + 10, y))
            y += 22

            screen.blit(self.font_sm.render(f"Pos: ({tx}, {ty2})", True, C_TEXT), (px + 10, y))
            y += 16
            bio = self.hover_biome.replace('_', ' ').title()
            screen.blit(self.font_sm.render(f"Biome: {bio}", True, C_TEXT), (px + 10, y))
            y += 16
            screen.blit(self.font_sm.render(f"Elevation: {self.hover_elev:.3f}", True, C_TEXT), (px + 10, y))
            y += 16
            screen.blit(self.font_sm.render(f"Moisture:  {self.hover_moist:.3f}", True, C_TEXT), (px + 10, y))
            y += 16

            # Temperature
            temp = getattr(self, 'hover_temp', 0.0)
            temp_col = (200, 60, 40) if temp > 0.65 else (60, 150, 220) if temp < 0.35 else C_TEXT
            screen.blit(self.font_sm.render(f"Temp: {temp:.3f}", True, temp_col), (px + 10, y))
            y += 16

            # Weather
            weather = getattr(self, 'hover_weather', None)
            if weather:
                wc = (80, 140, 220)
                screen.blit(self.font_sm.render(f"Weather: {weather}", True, wc), (px + 10, y))
                y += 16

            if self.hover_mat and self.hover_mat != 'none':
                mat_info = MATERIALS.get(self.hover_mat, {})
                mat_col  = mat_info.get('color', C_TEXT)
                screen.blit(self.font_sm.render(f"Material: {self.hover_mat}", True, mat_col), (px + 10, y))
                y += 16

            if self.hover_god:
                gc   = GOD_COLORS.get(self.hover_god, (180, 180, 180))
                name = self.hover_god.replace('god_', '').title()
                screen.blit(self.font_sm.render(f"God: {name}", True, gc), (px + 10, y))
                y += 16

                # influence bar
                bx, by2, bw, bh = px + 12, y, INFO_PANEL_W - 24, 10
                pygame.draw.rect(screen, C_BG_LIGHT, (bx, by2, bw, bh), border_radius=2)
                fw = int(bw * min(self.hover_str, 1.0))
                if fw > 0:
                    pygame.draw.rect(screen, gc, (bx, by2, fw, bh), border_radius=2)
                pygame.draw.rect(screen, C_BORDER, (bx, by2, bw, bh), 1, border_radius=2)
                y += 18
            else:
                screen.blit(self.font_sm.render("Neutral territory", True, C_TEXT_DIM), (px + 10, y))
                y += 16

            # Building info
            building = getattr(self, 'hover_building', None)
            if building:
                y += 4
                pygame.draw.line(screen, C_BORDER, (px + 10, y), (px + INFO_PANEL_W - 10, y))
                y += 6
                screen.blit(self.font_lg.render("BUILDING", True, (200, 170, 100)), (px + 10, y))
                y += 18
                screen.blit(self.font_sm.render(building.display_name, True, C_TEXT_BRIGHT), (px + 10, y))
                y += 16
                screen.blit(self.font_xs.render(f"HP: {building.hp}/{building.max_hp}  Pop: {int(building.population)}", True, C_TEXT), (px + 10, y))
                y += 14

            # Units count
            unit_count = getattr(self, 'hover_units', 0)
            if unit_count > 0:
                screen.blit(self.font_xs.render(f"Units here: {unit_count}", True, (200, 100, 100)), (px + 10, y))
                y += 14

        # ── Stronghold info ────────────────
        sh = self.info_data.get('stronghold')
        if sh:
            y += 6
            pygame.draw.line(screen, C_BORDER, (px + 10, y), (px + INFO_PANEL_W - 10, y))
            y += 8
            screen.blit(self.font_lg.render("STRONGHOLD", True, (220, 200, 100)), (px + 10, y))
            y += 20
            screen.blit(self.font_sm.render(sh.get('name', '?'), True, C_TEXT_BRIGHT), (px + 10, y))
            y += 16
            gid = sh.get('god_id', '')
            gc  = GOD_COLORS.get(gid, (180, 180, 180))
            screen.blit(self.font_sm.render(f"Owner: {gid.replace('god_','').title()}", True, gc), (px + 10, y))
            y += 16
            screen.blit(self.font_xs.render(f"Str: {sh.get('strength',0):.2f}  Rad: {sh.get('radius',0)}", True, C_TEXT_DIM), (px + 10, y))
            y += 14
            screen.blit(self.font_xs.render(f"Type: {sh.get('type','?')}", True, C_TEXT_DIM), (px + 10, y))

        # ── God standings ──────────────────
        if not sh and self.standings:
            y += 6
            pygame.draw.line(screen, C_BORDER, (px + 10, y), (px + INFO_PANEL_W - 10, y))
            y += 8
            screen.blit(self.font_lg.render("DOMINION", True, C_ACCENT), (px + 10, y))
            y += 20
            for g in self.standings[:9]:
                gid  = g.get('god_id', '')
                gc   = GOD_COLORS.get(gid, (128, 128, 128))
                terr = g.get('territories', 0)
                nm   = g.get('god_name', gid)
                if len(nm) > 20:
                    nm = nm[:18] + "..."
                pygame.draw.circle(screen, gc, (px + 16, y + 6), 4)
                screen.blit(self.font_xs.render(nm, True, C_TEXT), (px + 26, y))
                screen.blit(self.font_xs.render(str(terr), True, gc), (px + INFO_PANEL_W - 30, y))
                y += 16

    # ── bottom bar (event log) ──────────────────────────────────────────
    def _draw_bottom_bar(self, screen):
        top = SCR.h - BOTTOMBAR_H
        pygame.draw.rect(screen, (10, 10, 16), (0, top, SCR.w, BOTTOMBAR_H))
        pygame.draw.line(screen, C_BORDER, (0, top), (SCR.w, top))

        # Event log
        x = SIDEBAR_W + 10
        screen.blit(self.font_xs.render("EVENT LOG", True, C_TEXT_DIM), (x, top + 4))
        ey = top + 18
        n  = 4
        rec = self.events[-n:] if self.events else ["No events yet"]
        for t in rec:
            if len(t) > 80:
                t = t[:77] + "..."
            screen.blit(self.font_xs.render(t, True, (120, 120, 140)), (x, ey))
            ey += 14

        # World stats (middle section)
        mid_x = SCR.w // 2 - 80
        pop = getattr(self, '_pop', 0)
        uc = getattr(self, '_unit_count', 0)
        bc = getattr(self, '_building_count', 0)
        wz = getattr(self, '_weather_zones', 0)
        season = getattr(self, '_season', 'spring')

        screen.blit(self.font_xs.render("WORLD", True, C_TEXT_DIM), (mid_x, top + 4))
        season_colors = {'spring': (120,200,80), 'summer': (220,180,40),
                         'autumn': (200,120,40), 'winter': (140,180,220)}
        sc = season_colors.get(season, C_TEXT)
        era = getattr(self, '_era', '')
        ac = getattr(self, '_army_count', 0)
        wc = getattr(self, '_war_count', 0)
        era_str = f"  Era: {era}" if era else ""
        screen.blit(self.font_xs.render(f"Season: {season.title()}{era_str}", True, sc), (mid_x, top + 18))
        screen.blit(self.font_xs.render(f"Pop: {pop}  Units: {uc}  Armies: {ac}", True, C_TEXT), (mid_x, top + 32))
        war_col = (220, 80, 80) if wc > 0 else C_TEXT
        screen.blit(self.font_xs.render(f"Buildings: {bc}  Weather: {wz}  Wars: {wc}", True, war_col), (mid_x, top + 46))

        # Mini standings on right side
        sx = SCR.w - 300
        screen.blit(self.font_xs.render("DOMINION", True, C_TEXT_DIM), (sx, top + 4))
        col_x = sx
        for i, g in enumerate(self.standings[:9]):
            gid  = g.get('god_id', '')
            gc   = GOD_COLORS.get(gid, (128, 128, 128))
            terr = g.get('territories', 0)
            nm   = gid.replace('god_', '')[:5].title()
            row_y = top + 18 + (i % 5) * 12
            col_off = (i // 5) * 140
            pygame.draw.circle(screen, gc, (col_x + col_off + 5, row_y + 5), 3)
            screen.blit(self.font_xs.render(f"{nm}: {terr}", True, C_TEXT_DIM), (col_x + col_off + 12, row_y))

    # ── brush cursor ────────────────────────────────────────────────────
    def _draw_brush_cursor(self, screen):
        mx, my = pygame.mouse.get_pos()
        if self.is_over_ui(mx, my):
            return
        r = self.ts.brush_radius
        cat_color = self.ts.category['color']

        # Draw a circle outline for brush size indicator
        radius_px = max(r * 2, 4)
        cs = pygame.Surface((radius_px * 2 + 2, radius_px * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(cs, (*cat_color, 100), (radius_px + 1, radius_px + 1), radius_px, 1)
        screen.blit(cs, (mx - radius_px - 1, my - radius_px - 1))

        # Center dot
        pygame.draw.circle(screen, cat_color, (mx, my), 2)
