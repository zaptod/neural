"""
world_map_pygame/renderer.py
MapRenderer — renderiza o mapa na área (map_x, map_y, map_w, map_h).
Todos os draws são clipados a essa área para não invadir painéis.

[FASE 2] Mudanças:
  - smoothscale substitui scale (elimina pixelado no zoom alto)
  - Labels: visíveis desde zoom 0.30 (era 0.42), fonte serif maior, sombra dupla
  - Hover: borda 5px dourada com glow externo (era 1.5px branca)
  - Ícone de selo antigo: símbolo rúnico procedural no centróide (zoom >= 0.40)
  - Indicador de dono: círculo com iniciais do deus no centróide (zoom 0.35–2.0)
  - Fundo oceano atualizado para paleta sépia
  - Borda pulsante dourada (era cyan)
  - MAP_Y_OFFSET removido completamente
"""
import math
import pygame
import numpy as np
from scipy.ndimage import binary_erosion, binary_dilation
from typing import Dict, Optional, Tuple

from . import config
from .config import (
    WORLD_W, WORLD_H, TEX_W, TEX_H,
    CYAN, GOLD, GOLD_DIM, CRIMSON, TXT, TXT_DIM,
    NATURE_COLOR, SEAL_COLOR, UI_BG, scaled,
)
from .camera import Camera
from .data_loader import Zone, God


class MapRenderer:
    def __init__(self, map_surf, zone_idx, zone_list, zones, gods, cam):
        self.surf      = map_surf
        self.zone_idx  = zone_idx
        self.zone_list = zone_list
        self.zones     = zones
        self.gods      = gods
        self.cam       = cam
        self._compass  = _build_compass(scaled(56))
        self._lfonts:  Dict[tuple, pygame.font.Font] = {}
        self._ownership_surf: Optional[pygame.Surface] = None
        self._ownership_key  = None   # hash do estado de ownership para detectar mudanças
        # Cache de máscaras de erosão/dilation por (zone_i, border_w) — evita recalcular todo frame
        self._mask_cache: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray]] = {}
        # Cache do overlay de filtro por (active_filter, sel_id)
        self._filter_surf: Optional[pygame.Surface] = None
        self._filter_key  = None

    def _lf(self, size: int, serif: bool = False) -> pygame.font.Font:
        """Cache de fontes. serif=True usa Georgia/Times para o estilo pergaminho."""
        k = (size, serif)
        if k not in self._lfonts:
            if serif:
                self._lfonts[k] = pygame.font.SysFont("georgia,times new roman,serif", size)
            else:
                self._lfonts[k] = pygame.font.SysFont("consolas", size)
        return self._lfonts[k]

    def draw(self, screen, ownership, selected_zone, hover_zone,
             ancient_seals, t: float, map_x: int, map_w: int,
             active_filter: str = "all", map_h: int = 0):
        """
        active_filter: "all" ou nome de natureza (ex: "fire").
        map_h: altura visível do mapa (desconta painel inferior se aberto).
        """
        cam   = self.cam
        map_y = cam.map_y
        if map_h <= 0:
            map_h = config.SCREEN_H - map_y
        clip  = pygame.Rect(map_x, map_y, map_w, map_h)

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

        # Fundo oceano sépia
        screen.fill((48, 62, 92), clip)

        # [FASE 2] smoothscale: interpolação bilinear — elimina pixelado no zoom alto
        chunk  = self.surf.subsurface(src)
        scaled_surf = pygame.transform.smoothscale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled_surf, (sx0, sy0))
        screen.set_clip(None)

        # Ownership (fill suave por território)
        if ownership:
            self._draw_ownership(screen, ownership, clip)

        # Hover — borda espessa dourada com glow
        if hover_zone and hover_zone != selected_zone:
            self._draw_zone_overlay_indexed(
                screen, hover_zone, clip,
                (*GOLD, 22), (*GOLD, 200), max(3, int(5 * cam.zoom))
            )

        # Selos — [FASE 2] ícone rúnico substitui círculo simples
        if cam.zoom >= 0.40:
            self._draw_seal_icons(screen, ancient_seals, t, clip)

        # Seleção — borda dourada pulsante via zone_idx
        if selected_zone:
            pa = int(70 + math.sin(t * 3) * 55)
            self._draw_zone_overlay_indexed(
                screen, selected_zone, clip,
                (*GOLD, pa // 2), (*GOLD, 220),
                max(3, int(3.5 * cam.zoom))
            )

        # Indicadores de dono — [FASE 2] círculo com iniciais
        if 0.35 <= cam.zoom <= 2.0:
            self._draw_owner_badges(screen, ownership, clip)

        # Labels — [FASE 2] visíveis desde zoom 0.30, fonte serif maior, sombra dupla
        if cam.zoom >= 0.30:
            self._draw_labels(screen, ownership, clip)

        # [FASE 4] Overlay de filtro — escurece zonas fora do filtro ativo
        if active_filter != "all":
            self._draw_filter_overlay(screen, active_filter, selected_zone, clip)

        # Rosa dos ventos
        cx_ = map_x + map_w - self._compass.get_width() - scaled(12)
        cy_ = map_y + map_h - self._compass.get_height() - scaled(12)
        screen.blit(self._compass, (cx_, cy_))

        # Borda pulsante dourada (era cyan)
        p = int(160 + math.sin(t * 1.8) * 50)
        gold_pulse = (p, int(p * 0.83), int(p * 0.38))
        pygame.draw.rect(screen, gold_pulse, clip, 2)

    # ── Hover espesso dourado ─────────────────────────────────────────────
    def _draw_hover(self, screen, verts_world, clip, t):
        """[FASE 2] Borda 5px dourada com glow externo — era 1.5px branca."""
        cam  = self.cam
        surf = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        verts = [cam.w2s(wx, wy) for wx, wy in verts_world]
        if len(verts) < 3:
            return

        # Fill suave
        pygame.draw.polygon(surf, (*GOLD, 22), verts)

        # Glow externo (borda mais grossa e semi-transparente)
        glow_w = max(8, int(9 * cam.zoom))
        pygame.draw.polygon(surf, (*GOLD, 55), verts, glow_w)

        # Borda principal
        border_w = max(3, int(5 * cam.zoom))
        pygame.draw.polygon(surf, (*GOLD, 200), verts, border_w)

        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    # ── Ownership ─────────────────────────────────────────────────────────
    def _draw_poly_overlay(self, screen, verts_world, clip,
                            fill_col, border_col, border_w):
        """Mantido para compatibilidade — usado só onde zone_idx não se aplica."""
        cam   = self.cam
        surf  = pygame.Surface((config.SCREEN_W, config.SCREEN_H), pygame.SRCALPHA)
        verts = [cam.w2s(wx, wy) for wx, wy in verts_world]
        if len(verts) >= 3:
            pygame.draw.polygon(surf, fill_col,   verts)
            pygame.draw.polygon(surf, border_col, verts, border_w)
        screen.set_clip(clip)
        screen.blit(surf, (0, 0))
        screen.set_clip(None)

    def _draw_zone_overlay_indexed(self, screen, zone, clip,
                                    fill_col, border_col, border_w):
        """
        Overlay de zona via zone_idx — fill e borda seguem o Voronoi real.
        As máscaras de erosão/dilation são cacheadas por (zone_i, border_w)
        para evitar recálculo caro a cada frame.
        """
        try:
            zone_i = self.zone_list.index(zone)
        except ValueError:
            return

        cam   = self.cam
        map_y = cam.map_y
        map_h = clip.height

        # Cache de máscara — erosion/dilation é caro, só roda quando necessário
        cache_key = (zone_i, int(border_w))
        if cache_key not in self._mask_cache:
            mask    = (self.zone_idx == zone_i)          # (H, W) bool
            eroded  = binary_erosion(mask,  iterations=max(1, int(border_w)))
            dilated = binary_dilation(mask, iterations=max(1, int(border_w // 2 + 1)))
            border  = dilated & ~eroded
            # Armazena no espaço (W, H) — surfarray usa (W, H)
            self._mask_cache[cache_key] = (mask.T.copy(), border.T.copy())

        mask_t, border_t = self._mask_cache[cache_key]

        surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        rgb_arr   = pygame.surfarray.pixels3d(surf)
        alpha_arr = pygame.surfarray.pixels_alpha(surf)

        fa = fill_col[3]   if len(fill_col)   > 3 else 40
        ba = border_col[3] if len(border_col) > 3 else 200

        rgb_arr[mask_t, 0]   = fill_col[0]
        rgb_arr[mask_t, 1]   = fill_col[1]
        rgb_arr[mask_t, 2]   = fill_col[2]
        alpha_arr[mask_t]    = fa

        rgb_arr[border_t, 0]  = border_col[0]
        rgb_arr[border_t, 1]  = border_col[1]
        rgb_arr[border_t, 2]  = border_col[2]
        alpha_arr[border_t]   = ba

        del rgb_arr, alpha_arr

        # Viewport → escala e blit
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
        sx0, sy0 = cam.w2s(wl, wt)
        dw = max(1, int((wr - wl) * cam.zoom))
        dh = max(1, int((wb - wt) * cam.zoom))

        chunk    = surf.subsurface(src)
        scaled_s = pygame.transform.smoothscale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled_s, (sx0, sy0))
        screen.set_clip(None)

    # ── Ownership — baseado no zone_idx (Voronoi real) ───────────────────
    def _draw_ownership(self, screen, ownership, clip):
        """
        [FASE 4 patch] Ownership desenhada a partir do zone_idx (bitmap Voronoi),
        não dos zone.vertices (retângulos do JSON).
        Resultado: cores de dono se encaixam perfeitamente nas fronteiras orgânicas.
        A textura é cacheada e só reconstruída quando ownership muda.
        """
        # Detecta mudança no estado de ownership
        key = tuple(sorted(ownership.items()))
        if key != self._ownership_key or self._ownership_surf is None:
            self._ownership_surf = self._build_ownership_texture(ownership)
            self._ownership_key  = key

        # Escala e blit exatamente como o terreno — mesma lógica de viewport
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
        """
        Constrói textura RGBA (TEX_W × TEX_H) de ownership via zone_idx.
        """

        surf = pygame.Surface((TEX_W, TEX_H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Arrays de acesso direto aos pixels
        rgb_arr   = pygame.surfarray.pixels3d(surf)    # (W, H, 3)
        alpha_arr = pygame.surfarray.pixels_alpha(surf) # (W, H)

        # zone_idx é (H, W) — transpõe para (W, H) para alinhar com surfarray
        idx_t = self.zone_idx.T  # (W, H)

        for i, zone in enumerate(self.zone_list):
            gid = ownership.get(zone.zone_id)
            if not gid:
                continue
            god = self.gods.get(gid)
            if not god:
                continue
            r, g, b = god.rgb()
            mask = (idx_t == i)           # (W, H) bool
            rgb_arr[mask, 0] = r
            rgb_arr[mask, 1] = g
            rgb_arr[mask, 2] = b
            alpha_arr[mask]  = 52

        # Fronteiras: pixels onde vizinho horizontal ou vertical tem dono diferente
        # Trabalha no espaço (H, W) original e depois transpõe
        idx = self.zone_idx  # (H, W)
        alpha_t = alpha_arr.T  # view (H, W)

        h_diff = (idx[:, :-1] != idx[:, 1:])   # (H, W-1)
        v_diff = (idx[:-1, :] != idx[1:, :])   # (H-1, W)

        # Marca borda só onde ambos os lados têm dono
        h_both = h_diff & (alpha_t[:, :-1] > 0) & (alpha_t[:, 1:] > 0)
        v_both = v_diff & (alpha_t[:-1, :] > 0) & (alpha_t[1:, :] > 0)

        alpha_t[:, :-1][h_both] = 180
        alpha_t[:, 1:][h_both]  = 180
        alpha_t[:-1, :][v_both] = 180
        alpha_t[1:, :][v_both]  = 180

        # Libera os locks dos pixel arrays antes de retornar
        del rgb_arr, alpha_arr

        return surf

    # ── Ícone de Selo Antigo (rúnico procedural) ──────────────────────────
    def _draw_seal_icons(self, screen, ancient_seals, t, clip):
        """
        [FASE 2] Símbolo rúnico desenhado proceduralmente.
        Usa surface do tamanho do clip (não SCREEN_W×SCREEN_H) para economizar memória/tempo.
        """
        cam  = self.cam
        # Surface do tamanho do clip, não da tela toda
        surf = pygame.Surface((clip.width, clip.height), pygame.SRCALPHA)
        ox, oy = clip.x, clip.y   # offset para converter coords de tela → surf local

        for zone in self.zones.values():
            if not zone.ancient_seal:
                continue
            sd     = ancient_seals.get(zone.zone_id, {})
            status = sd.get("status", "sleeping")
            col    = SEAL_COLOR.get(status, (120, 35, 210))

            sx, sy = cam.w2s(*zone.centroid)
            if not clip.collidepoint(sx, sy):
                continue

            lx, ly = sx - ox, sy - oy  # coords locais na surf

            r = max(7, min(22, int(16 * cam.zoom)))

            pulse_speed = {"sleeping": 1.2, "stirring": 2.2, "awakened": 3.5, "broken": 0.5}
            ps = pulse_speed.get(status, 1.5)
            a_outer = int(60  + math.sin(t * ps) * 40)
            a_inner = int(140 + math.sin(t * ps + 1.0) * 70)
            a_lines = int(100 + math.sin(t * ps + 0.5) * 50)

            pygame.draw.circle(surf, (*col, a_outer), (lx, ly), r)
            pygame.draw.circle(surf, (*col, a_inner), (lx, ly), max(3, r // 2), max(1, r // 5))
            for angle_deg in [45, 135]:
                angle = math.radians(angle_deg)
                dx = math.cos(angle) * r * 0.75
                dy = math.sin(angle) * r * 0.75
                pygame.draw.line(surf, (*col, a_lines),
                                 (int(lx - dx), int(ly - dy)),
                                 (int(lx + dx), int(ly + dy)),
                                 max(1, r // 6))
            pygame.draw.circle(surf, (*col, min(255, a_inner + 40)), (lx, ly), max(2, r // 4))

        screen.set_clip(clip)
        screen.blit(surf, clip.topleft)
        screen.set_clip(None)

    # ── Indicador de dono (círculo com iniciais) ──────────────────────────
    def _draw_owner_badges(self, screen, ownership, clip):
        """
        [FASE 2] Círculo com 1-2 iniciais do nome do deus no centróide da zona.
        Usa surface do tamanho do clip para melhor performance.
        """
        cam  = self.cam
        surf = pygame.Surface((clip.width, clip.height), pygame.SRCALPHA)
        ox, oy = clip.x, clip.y

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

            lx, ly = sx - ox, badge_y - oy  # coords locais
            r, g, b = god.rgb()
            initials = "".join(w[0].upper() for w in god.god_name.split()[:2])

            pygame.draw.circle(surf, (r, g, b, 160), (lx, ly), badge_r)
            pygame.draw.circle(surf, (*GOLD, 200), (lx, ly), badge_r, max(1, badge_r // 5))

            txt_surf = font.render(initials, True, (240, 235, 215))
            txt_rect = txt_surf.get_rect(center=(lx, ly))
            surf.blit(txt_surf, txt_rect)

        screen.set_clip(clip)
        screen.blit(surf, clip.topleft)
        screen.set_clip(None)

    # ── Labels ────────────────────────────────────────────────────────────
    def _draw_labels(self, screen, ownership, clip: pygame.Rect):
        """
        [FASE 2] Labels com fonte serif, maiores, visíveis desde zoom 0.30.
        Sombra dupla (preta + sépia) para legibilidade sobre qualquer terreno.
        Sub-label de natureza em itálico a partir de zoom 0.55.
        """
        cam = self.cam

        # Tamanho da fonte escala com zoom, mas usa UI_SCALE como baseline
        fsz  = max(scaled(9), min(scaled(20), int(scaled(14) * cam.zoom)))
        font = self._lf(fsz, serif=True)

        screen.set_clip(clip)
        for zone in self.zones.values():
            sx, sy = cam.w2s(*zone.centroid)
            if not clip.collidepoint(sx, sy):
                continue

            gid = ownership.get(zone.zone_id)
            col = TXT if gid else (175, 165, 145)

            # Sombra dupla: primeiro preta (offset 2px), depois sépia (offset 1px)
            label = font.render(zone.zone_name, True, col)
            shadow_dark  = font.render(zone.zone_name, True, (0, 0, 0))
            shadow_sepia = font.render(zone.zone_name, True, (40, 30, 15))
            r = label.get_rect(center=(sx, sy))

            # Fundo semi-transparente
            bg = pygame.Surface((r.width + scaled(10), r.height + scaled(4)), pygame.SRCALPHA)
            bg.fill((*UI_BG, 130))
            screen.blit(bg, (r.x - scaled(5), r.y - scaled(2)))

            # Sombras e label
            screen.blit(shadow_dark,  r.move(2, 2))
            screen.blit(shadow_sepia, r.move(1, 1))
            screen.blit(label, r)

            # Nome do deus dono (zoom alto)
            if gid and cam.zoom >= 0.85:
                god = self.gods.get(gid)
                if god:
                    gf  = self._lf(max(scaled(7), fsz - scaled(3)), serif=True)
                    gs  = gf.render(god.god_name, True, god.rgb())
                    gsh = gf.render(god.god_name, True, (0, 0, 0))
                    gr  = gs.get_rect(center=(sx, sy + fsz + scaled(5)))
                    screen.blit(gsh, gr.move(1, 1))
                    screen.blit(gs,  gr)

            # Sub-label de natureza em itálico (zoom médio)
            if cam.zoom >= 0.55:
                nf  = self._lf(max(scaled(7), fsz - scaled(4)), serif=True)
                nc  = NATURE_COLOR.get(zone.base_nature, TXT_DIM)
                ns  = nf.render(zone.base_nature.upper(), True, nc)
                nsh = nf.render(zone.base_nature.upper(), True, (0, 0, 0))
                nr  = ns.get_rect(center=(sx, sy - fsz - scaled(4)))
                screen.blit(nsh, nr.move(1, 1))
                screen.blit(ns,  nr)

        screen.set_clip(None)


    # ── Overlay de filtro ─────────────────────────────────────────────────
    def _draw_filter_overlay(self, screen, active_filter: str,
                              selected_zone, clip: pygame.Rect):
        """
        [FASE 4] Escurece zonas fora do filtro usando zone_idx.
        Cacheado por (active_filter, sel_id) — só reconstrói quando filtro ou seleção mudam.
        """
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
                mask_t = (self.zone_idx == i).T   # (W, H)
                rgb_arr[mask_t, 0] = 12
                rgb_arr[mask_t, 1] = 8
                rgb_arr[mask_t, 2] = 4
                alpha_arr[mask_t]  = 165

            del rgb_arr, alpha_arr
            self._filter_surf = surf
            self._filter_key  = filter_key

        # Escala e blit no viewport atual
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
        sx0, sy0 = cam.w2s(wl, wt)
        dw = max(1, int((wr - wl) * cam.zoom))
        dh = max(1, int((wb - wt) * cam.zoom))

        chunk = self._filter_surf.subsurface(src)
        scaled_f = pygame.transform.smoothscale(chunk, (dw, dh))
        screen.set_clip(clip)
        screen.blit(scaled_f, (sx0, sy0))
        screen.set_clip(None)


# ── Rosa dos Ventos ───────────────────────────────────────────────────────────
def _build_compass(r: int) -> pygame.Surface:
    """Compasso ornamental estilo cartografia antiga, paleta dourada."""
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
