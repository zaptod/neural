"""Auto-generated mixin — see scripts/split_simulacao.py"""
import pygame
import logging
_log = logging.getLogger("simulacao")  # QC-02
import json
import math
import random
import sys
import os

# Adiciona o diretório pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import database
from utils.config import (
    PPM, LARGURA, ALTURA, LARGURA_PORTRAIT, ALTURA_PORTRAIT, FPS,
    BRANCO, VERMELHO_SANGUE, SANGUE_ESCURO, AMARELO_FAISCA,
    AZUL_MANA, COR_CORPO, COR_P1, COR_P2, COR_FUNDO, COR_GRID,
    COR_UI_BG, COR_TEXTO_TITULO, COR_TEXTO_INFO,
)
from effects import (Particula, FloatingText, Decal, Shockwave, Câmera, EncantamentoEffect,
                     ImpactFlash, MagicClash, BlockEffect, DashTrail, HitSpark,
                     MovementAnimationManager, MovementType,  # v8.0 Movement Animations
                     AttackAnimationManager, calcular_knockback_com_forca, get_impact_tier,  # v8.0 Attack Animations
                     MagicVFXManager, get_element_from_skill)  # v11.0 Magic VFX
from effects.audio import AudioManager  # v10.0 Sistema de Áudio
from core.entities import Lutador
from core.physics import colisao_linha_circulo, intersect_line_circle, colisao_linha_linha, normalizar_angulo
from core.hitbox import sistema_hitbox, verificar_hit, get_debug_visual, atualizar_debug, DEBUG_VISUAL
from core.arena import Arena, ARENAS, get_arena, set_arena  # v9.0 Sistema de Arena
from ai import CombatChoreographer  # Sistema de Coreografia v5.0
from core.game_feel import GameFeelManager, HitStopManager  # Sistema de Game Feel v8.0


class SimuladorRenderer:
    """Mixin de renderização: desenho de lutadores, armas, UI e debug."""


    def desenhar(self):
        self.tela.fill(COR_FUNDO)
        
        # === DESENHA ARENA v9.0 (ANTES DE TUDO) ===
        if self.arena:
            self.arena.desenhar(self.tela, self.cam)
        else:
            # Fallback: grid antigo se não houver arena
            self.desenhar_grid()
        
        for d in self.decals: d.draw(self.tela, self.cam)
        
        # === DESENHA ÁREAS COM EFEITOS DRAMÁTICOS v11.0 ===
        if hasattr(self, 'areas'):
            for area in self.areas:
                if area.ativo:
                    ax, ay = self.cam.converter(area.x * PPM, area.y * PPM)
                    ar = self.cam.converter_tam(area.raio_atual * PPM)
                    if ar > 0:
                        # Pulso baseado no tempo
                        pulse_time = pygame.time.get_ticks() / 1000.0
                        pulse = 0.85 + 0.15 * math.sin(pulse_time * 6)
                        ar_pulsing = int(ar * pulse)
                        
                        # Múltiplas camadas para glow dramático
                        # Camada externa (glow)
                        s_glow = pygame.Surface((ar*4, ar*4), pygame.SRCALPHA)
                        glow_alpha = int(30 + 20 * math.sin(pulse_time * 4))
                        pygame.draw.circle(s_glow, (*area.cor[:3], glow_alpha), (ar*2, ar*2), ar*2)
                        self.tela.blit(s_glow, (ax - ar*2, ay - ar*2))
                        
                        # Camada média
                        s = pygame.Surface((ar*2, ar*2), pygame.SRCALPHA)
                        cor_com_alpha = (*area.cor[:3], min(255, area.alpha // 3))
                        pygame.draw.circle(s, cor_com_alpha, (ar, ar), ar_pulsing)
                        self.tela.blit(s, (ax - ar, ay - ar))
                        
                        # Anéis pulsantes (2-3 anéis)
                        for i in range(3):
                            ring_phase = pulse_time * (3 + i) + i * 0.5
                            ring_pulse = 0.5 + 0.5 * ((ring_phase % 1.0))
                            ring_r = int(ar * ring_pulse)
                            if ring_r > 2 and ring_r < ar:
                                ring_alpha = int(150 * (1 - ring_pulse))
                                s_ring = pygame.Surface((ring_r*2+4, ring_r*2+4), pygame.SRCALPHA)
                                pygame.draw.circle(s_ring, (*area.cor[:3], ring_alpha), (ring_r+2, ring_r+2), ring_r, 2)
                                self.tela.blit(s_ring, (ax - ring_r - 2, ay - ring_r - 2))
                        
                        # Borda principal (brilhante)
                        pygame.draw.circle(self.tela, area.cor, (ax, ay), ar_pulsing, 3)
                        # Core brilhante
                        inner_r = int(ar * 0.3)
                        if inner_r > 2:
                            s_core = pygame.Surface((inner_r*2+4, inner_r*2+4), pygame.SRCALPHA)
                            pygame.draw.circle(s_core, (255, 255, 255, 80), (inner_r+2, inner_r+2), inner_r)
                            self.tela.blit(s_core, (ax - inner_r - 2, ay - inner_r - 2))
        
        # === DESENHA BEAMS COM EFEITOS DRAMÁTICOS v11.0 ===
        if hasattr(self, 'beams'):
            pulse_time = pygame.time.get_ticks() / 1000.0
            for beam in self.beams:
                if beam.ativo:
                    # Desenha segmentos zigzag
                    pts_screen = []
                    for bx, by in beam.segments:
                        sx, sy = self.cam.converter(bx * PPM, by * PPM)
                        pts_screen.append((sx, sy))
                    if len(pts_screen) >= 2:
                        pulse = 0.8 + 0.4 * abs(math.sin(pulse_time * 12))
                        largura_efetiva = int(beam.largura * pulse)
                        
                        # Calcula bounding box para surface
                        min_x = min(p[0] for p in pts_screen) - largura_efetiva - 10
                        min_y = min(p[1] for p in pts_screen) - largura_efetiva - 10
                        max_x = max(p[0] for p in pts_screen) + largura_efetiva + 10
                        max_y = max(p[1] for p in pts_screen) + largura_efetiva + 10
                        
                        w = int(max_x - min_x + 1)
                        h = int(max_y - min_y + 1)
                        
                        if w > 0 and h > 0:
                            s = pygame.Surface((w, h), pygame.SRCALPHA)
                            local_pts = [(int(p[0] - min_x), int(p[1] - min_y)) for p in pts_screen]
                            
                            # Glow externo (muito largo, semi-transparente)
                            glow_alpha = int(60 + 30 * math.sin(pulse_time * 8))
                            pygame.draw.lines(s, (*beam.cor[:3], glow_alpha), False, local_pts, largura_efetiva + 12)
                            
                            # Glow médio
                            pygame.draw.lines(s, (*beam.cor[:3], 150), False, local_pts, largura_efetiva + 6)
                            
                            # Beam principal colorido
                            pygame.draw.lines(s, beam.cor, False, local_pts, largura_efetiva)
                            
                            # Core brilhante branco
                            core_largura = max(2, largura_efetiva // 2)
                            pygame.draw.lines(s, (255, 255, 255), False, local_pts, core_largura)
                            
                            self.tela.blit(s, (min_x, min_y))
                        
                        # Partículas ao longo do beam
                        if random.random() < 0.3:
                            idx = random.randint(0, len(pts_screen) - 1)
                            px, py = pts_screen[idx]
                            # Particula(x, y, cor, vel_x, vel_y, tamanho, vida_util)
                            self.particulas.append(Particula(
                                px + random.uniform(-10, 10),
                                py + random.uniform(-10, 10),
                                beam.cor,
                                random.uniform(-30, 30),  # vel_x
                                random.uniform(-30, 30),  # vel_y
                                random.uniform(3, 6),     # tamanho
                                0.3                       # vida_util
                            ))
        
        for p in self.particulas:
            sx, sy = self.cam.converter(p.x, p.y); tam = self.cam.converter_tam(p.tamanho)
            # Desenha partícula com glow
            if tam > 2:
                s = pygame.Surface((int(tam*2)+4, int(tam*2)+4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*p.cor, 100), (int(tam)+2, int(tam)+2), int(tam))
                pygame.draw.circle(s, p.cor, (int(tam)+2, int(tam)+2), max(1, int(tam*0.6)))
                self.tela.blit(s, (sx - int(tam) - 2, sy - int(tam) - 2))
            else:
                pygame.draw.rect(self.tela, p.cor, (sx, sy, max(1, int(tam)), max(1, int(tam))))
        
        # === DESENHA SUMMONS (Invocações) v11.0 DRAMATIC ===
        if hasattr(self, 'summons') and self.summons:
            pulse_time = pygame.time.get_ticks() / 1000.0
            for summon in self.summons:
                if summon.ativo:
                    sx, sy = self.cam.converter(summon.x * PPM, summon.y * PPM)
                    raio = self.cam.converter_tam(0.8 * PPM)  # Tamanho visual do summon
                    
                    # Círculo mágico no chão (rotacionando)
                    rotacao = pulse_time * 2
                    circle_r = int(raio * 1.5)
                    s_circle = pygame.Surface((circle_r*2+4, circle_r*2+4), pygame.SRCALPHA)
                    pygame.draw.circle(s_circle, (*summon.cor, 60), (circle_r+2, circle_r+2), circle_r, 2)
                    # Runas (linhas radiais)
                    for i in range(8):
                        ang = rotacao + i * (math.pi / 4)
                        inner = circle_r * 0.6
                        outer = circle_r
                        x1 = circle_r + 2 + math.cos(ang) * inner
                        y1 = circle_r + 2 + math.sin(ang) * inner
                        x2 = circle_r + 2 + math.cos(ang) * outer
                        y2 = circle_r + 2 + math.sin(ang) * outer
                        pygame.draw.line(s_circle, (*summon.cor, 100), (int(x1), int(y1)), (int(x2), int(y2)), 2)
                    self.tela.blit(s_circle, (sx - circle_r - 2, sy - circle_r - 2))
                    
                    # Sombra
                    pygame.draw.ellipse(self.tela, (30, 30, 30), (sx - raio, sy + raio//2, raio*2, raio//2))
                    
                    # Glow exterior pulsante
                    glow_pulse = 0.8 + 0.4 * math.sin(pulse_time * 5 + summon.vida_timer)
                    s = pygame.Surface((int(raio*4), int(raio*4)), pygame.SRCALPHA)
                    glow_alpha = int((60 + 40 * math.sin(summon.vida_timer * 3)) * glow_pulse)
                    pygame.draw.circle(s, (*summon.cor, glow_alpha), (int(raio*2), int(raio*2)), int(raio * 1.8 * glow_pulse))
                    self.tela.blit(s, (sx - raio*2, sy - raio*2))
                    
                    # Corpo do summon (baseado na cor da skill) com gradiente
                    pygame.draw.circle(self.tela, summon.cor, (int(sx), int(sy)), int(raio))
                    pygame.draw.circle(self.tela, tuple(min(255, c + 50) for c in summon.cor), (int(sx), int(sy)), int(raio * 0.7))
                    
                    # Core brilhante
                    pygame.draw.circle(self.tela, BRANCO, (int(sx), int(sy)), max(1, int(raio * 0.35)))
                    
                    # Barra de vida do summon
                    vida_pct = summon.vida / summon.vida_max
                    barra_w = raio * 2
                    pygame.draw.rect(self.tela, (50, 50, 50), (sx - raio, sy - raio - 10, barra_w, 5))
                    pygame.draw.rect(self.tela, summon.cor, (sx - raio, sy - raio - 10, barra_w * vida_pct, 5))
                    
                    # Nome do summon
                    font = pygame.font.Font(None, 16)
                    nome_txt = font.render(summon.nome, True, summon.cor)
                    self.tela.blit(nome_txt, (sx - nome_txt.get_width()//2, sy - raio - 22))
        
        # === DESENHA TRAPS (Armadilhas) v2.0 ===
        if hasattr(self, 'traps'):
            for trap in self.traps:
                if trap.ativo:
                    tx, ty = self.cam.converter(trap.x * PPM, trap.y * PPM)
                    traio = self.cam.converter_tam(trap.raio * PPM)
                    
                    # Desenha armadilha como hexágono ou círculo
                    if trap.bloqueia_movimento:
                        # Estrutura sólida - hexágono
                        pts = []
                        for i in range(6):
                            ang = i * (math.pi / 3) + trap.angulo
                            pts.append((tx + math.cos(ang) * traio, ty + math.sin(ang) * traio))
                        pygame.draw.polygon(self.tela, trap.cor, pts)
                        pygame.draw.polygon(self.tela, BRANCO, pts, 2)
                    else:
                        # Armadilha no chão - círculo com padrão
                        s = pygame.Surface((traio*2, traio*2), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*trap.cor, 150), (traio, traio), traio)
                        self.tela.blit(s, (tx - traio, ty - traio))
                        # Marcas de perigo
                        pygame.draw.circle(self.tela, trap.cor, (int(tx), int(ty)), int(traio), 2)
                        pygame.draw.circle(self.tela, trap.cor, (int(tx), int(ty)), int(traio * 0.5), 1)
        
        # === DESENHA MARCAS NO CHÃO (CRATERAS, RACHADURAS) - v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_ground(self.tela, self.cam)
        
        lutadores = [self.p1, self.p2]
        lutadores.sort(key=lambda p: 0 if p.morto else 1)
        for l in lutadores: self.desenhar_lutador(l)
        
        # === DESENHA PROJÉTEIS COM TRAIL ELEMENTAL v4.0 ===
        pulse_time = pygame.time.get_ticks() / 1000.0
        
        # (trail update movido para update())
        
        for proj in self.projeteis:
            # Trail legado como fallback (projéteis físicos não mágicos)
            if hasattr(proj, 'trail') and len(proj.trail) > 1 and not any(
                    w in str(getattr(proj, 'nome', '')).lower()
                    for w in ["fogo","gelo","raio","trevas","luz","arcano","sangue","veneno","void"]):
                cor_trail = proj.cor if hasattr(proj, 'cor') else BRANCO
                for i in range(1, len(proj.trail)):
                    t = i / len(proj.trail)
                    alpha = int(255 * t * 0.7)
                    largura = max(1, int(proj.raio * PPM * self.cam.zoom * t))
                    p1 = self.cam.converter(proj.trail[i-1][0] * PPM, proj.trail[i-1][1] * PPM)
                    p2 = self.cam.converter(proj.trail[i][0] * PPM, proj.trail[i][1] * PPM)
                    if largura > 2:
                        s = pygame.Surface((abs(int(p2[0]-p1[0]))+largura*4, abs(int(p2[1]-p1[1]))+largura*4), pygame.SRCALPHA)
                        offset_x = min(p1[0], p2[0]) - largura*2
                        offset_y = min(p1[1], p2[1]) - largura*2
                        local_p1 = (p1[0] - offset_x, p1[1] - offset_y)
                        local_p2 = (p2[0] - offset_x, p2[1] - offset_y)
                        pygame.draw.line(s, (*cor_trail[:3], alpha // 2), local_p1, local_p2, largura * 2)
                        pygame.draw.line(s, (*cor_trail[:3], alpha), local_p1, local_p2, largura)
                        self.tela.blit(s, (offset_x, offset_y))
                    else:
                        pygame.draw.line(self.tela, cor_trail, p1, p2, largura)
            
            # Projétil principal - desenho baseado no tipo
            px, py = self.cam.converter(proj.x * PPM, proj.y * PPM)
            pr = self.cam.converter_tam(proj.raio * PPM)
            cor = proj.cor if hasattr(proj, 'cor') else BRANCO
            
            # Glow do projétil
            glow_pulse = 0.8 + 0.4 * math.sin(pulse_time * 10 + id(proj) % 100)
            glow_r = int(pr * 2 * glow_pulse)
            if glow_r > 3:
                s = pygame.Surface((glow_r*2+4, glow_r*2+4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*cor[:3], 60), (glow_r+2, glow_r+2), glow_r)
                self.tela.blit(s, (px - glow_r - 2, py - glow_r - 2))
            
            tipo_proj = getattr(proj, 'tipo', 'skill')
            ang_visual = getattr(proj, 'angulo_visual', proj.angulo) if hasattr(proj, 'angulo') else 0
            rad = math.radians(ang_visual)
            
            if tipo_proj == "faca":
                # Desenha faca (triângulo alongado)
                tam = max(pr * 2, 8)
                pts = [
                    (px + math.cos(rad) * tam, py + math.sin(rad) * tam),  # Ponta
                    (px + math.cos(rad + 2.5) * tam * 0.4, py + math.sin(rad + 2.5) * tam * 0.4),
                    (px - math.cos(rad) * tam * 0.3, py - math.sin(rad) * tam * 0.3),  # Base
                    (px + math.cos(rad - 2.5) * tam * 0.4, py + math.sin(rad - 2.5) * tam * 0.4),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, BRANCO, pts, 1)
                
            elif tipo_proj == "shuriken":
                # Desenha shuriken (estrela de 4 pontas girando)
                tam = max(pr * 2, 10)
                pts = []
                for i in range(8):
                    ang_pt = rad + i * (math.pi / 4)
                    dist = tam if i % 2 == 0 else tam * 0.3
                    pts.append((px + math.cos(ang_pt) * dist, py + math.sin(ang_pt) * dist))
                pygame.draw.polygon(self.tela, cor, pts)
                pygame.draw.polygon(self.tela, (50, 50, 50), pts, 1)
                
            elif tipo_proj == "chakram":
                # Desenha chakram (anel girando)
                tam = max(pr * 2, 12)
                pygame.draw.circle(self.tela, cor, (int(px), int(py)), int(tam), 3)
                pygame.draw.circle(self.tela, BRANCO, (int(px), int(py)), int(tam * 0.5), 2)
                # Lâminas
                for i in range(6):
                    ang_blade = rad + i * (math.pi / 3)
                    bx = px + math.cos(ang_blade) * tam
                    by = py + math.sin(ang_blade) * tam
                    pygame.draw.line(self.tela, cor, (px, py), (int(bx), int(by)), 2)
                
            elif tipo_proj == "flecha":
                # Desenha flecha
                tam = max(pr * 3, 15)
                # Corpo da flecha
                x1 = px - math.cos(rad) * tam * 0.7
                y1 = py - math.sin(rad) * tam * 0.7
                x2 = px + math.cos(rad) * tam * 0.3
                y2 = py + math.sin(rad) * tam * 0.3
                pygame.draw.line(self.tela, (139, 90, 43), (int(x1), int(y1)), (int(x2), int(y2)), 2)
                # Ponta da flecha (triângulo)
                pts = [
                    (px + math.cos(rad) * tam * 0.6, py + math.sin(rad) * tam * 0.6),
                    (px + math.cos(rad + 2.7) * tam * 0.2, py + math.sin(rad + 2.7) * tam * 0.2),
                    (px + math.cos(rad - 2.7) * tam * 0.2, py + math.sin(rad - 2.7) * tam * 0.2),
                ]
                pygame.draw.polygon(self.tela, cor, pts)
                # Penas (traseira)
                for offset in [-0.3, 0.3]:
                    fx = x1 + math.cos(rad + offset) * tam * 0.15
                    fy = y1 + math.sin(rad + offset) * tam * 0.15
                    pygame.draw.line(self.tela, (200, 200, 200), (int(x1), int(y1)), (int(fx), int(fy)), 1)
                
            else:
                # Projétil de skill — visual por elemento (v4.0)
                # Detecta elemento pelo nome/tipo do projétil
                _nome_el = str(getattr(proj, 'nome', '')).lower() + str(getattr(proj, 'tipo', '')).lower()
                if any(w in _nome_el for w in ["fogo","fire","chama","meteoro"]):
                    _el_proj = "FOGO"
                elif any(w in _nome_el for w in ["gelo","ice","glacial"]):
                    _el_proj = "GELO"
                elif any(w in _nome_el for w in ["raio","lightning","thunder"]):
                    _el_proj = "RAIO"
                elif any(w in _nome_el for w in ["trevas","shadow","dark","sombra"]):
                    _el_proj = "TREVAS"
                elif any(w in _nome_el for w in ["luz","light","holy","sagrado"]):
                    _el_proj = "LUZ"
                elif any(w in _nome_el for w in ["arcano","arcane","mana"]):
                    _el_proj = "ARCANO"
                elif any(w in _nome_el for w in ["sangue","blood"]):
                    _el_proj = "SANGUE"
                elif any(w in _nome_el for w in ["void","vazio"]):
                    _el_proj = "VOID"
                else:
                    _el_proj = "DEFAULT"

                _pkt = pulse_time + id(proj) % 100 * 0.1

                if _el_proj == "FOGO":
                    # Orbe de fogo: esfera central + chama acima
                    pygame.draw.circle(self.tela, (255, 140, 0), (int(px), int(py)), int(pr))
                    pygame.draw.circle(self.tela, (255, 220, 80), (int(px), int(py)), max(1, int(pr*0.6)))
                    # Chama pulsante no topo
                    flame_h = int(pr * 1.4 * (0.85 + 0.15 * math.sin(_pkt * 12)))
                    try:
                        _fs = pygame.Surface((int(pr*2)+4, flame_h+4), pygame.SRCALPHA)
                        _flame_pts = [
                            (int(pr)+2, 4),
                            (int(pr*0.4)+2, flame_h+2),
                            (int(pr*1.6)+2, flame_h+2),
                        ]
                        pygame.draw.polygon(_fs, (255, 80, 0, 160), _flame_pts)
                        self.tela.blit(_fs, (int(px)-int(pr)-2, int(py)-flame_h-2))
                    except Exception: pass

                elif _el_proj == "GELO":
                    # Cristal hexagonal
                    hex_pts = []
                    for _hi in range(6):
                        _ha = ang_visual + math.radians(30) + _hi * (math.pi/3)
                        hex_pts.append((px + math.cos(_ha)*pr, py + math.sin(_ha)*pr))
                    try:
                        pygame.draw.polygon(self.tela, (150, 220, 255), [(int(h[0]),int(h[1])) for h in hex_pts])
                        pygame.draw.polygon(self.tela, (220, 250, 255), [(int(h[0]),int(h[1])) for h in hex_pts], 2)
                    except Exception: pass
                    pygame.draw.circle(self.tela, (255, 255, 255), (int(px), int(py)), max(1, int(pr*0.35)))

                elif _el_proj == "RAIO":
                    # Losango pulsante branco-azul elétrico
                    _lr = pr * (0.9 + 0.1 * math.sin(_pkt * 25))
                    _lpts = [(px, py - _lr), (px + _lr*0.6, py),
                             (px, py + _lr), (px - _lr*0.6, py)]
                    try:
                        pygame.draw.polygon(self.tela, (200, 200, 255), [(int(p[0]),int(p[1])) for p in _lpts])
                        pygame.draw.polygon(self.tela, (255,255,255), [(int(p[0]),int(p[1])) for p in _lpts], 1)
                    except Exception: pass
                    # Arcos secundários pulsantes
                    if pr > 5:
                        for _li in range(4):
                            _la = _li * (math.pi/2) + _pkt * 5
                            _lx = px + math.cos(_la) * pr * 1.3
                            _ly = py + math.sin(_la) * pr * 1.3
                            try:
                                _ls = pygame.Surface((int(abs(_lx-px))+10, int(abs(_ly-py))+10), pygame.SRCALPHA)
                                _lox, _loy = min(px, _lx)-4, min(py, _ly)-4
                                pygame.draw.line(_ls, (255,255,150,160),
                                                 (int(px-_lox),int(py-_loy)),
                                                 (int(_lx-_lox),int(_ly-_loy)), 1)
                                self.tela.blit(_ls, (int(_lox),int(_loy)))
                            except Exception: pass

                elif _el_proj == "TREVAS":
                    # Esfera escura com halo roxo
                    pygame.draw.circle(self.tela, (20, 0, 40), (int(px), int(py)), int(pr))
                    pygame.draw.circle(self.tela, (100, 0, 150), (int(px), int(py)), int(pr), 2)
                    # Wisps orbitando
                    for _wi in range(3):
                        _wa = _pkt * 3 + _wi * (math.pi * 2 / 3)
                        _wx = int(px + math.cos(_wa) * pr * 1.4)
                        _wy = int(py + math.sin(_wa) * pr * 1.4)
                        pygame.draw.circle(self.tela, (150, 50, 200), (_wx, _wy), max(1, int(pr*0.3)))

                elif _el_proj == "LUZ":
                    # Estrela de 8 pontas brilhante
                    pygame.draw.circle(self.tela, (255, 255, 255), (int(px), int(py)), int(pr))
                    _star_pts = []
                    for _si in range(16):
                        _sa = ang_visual + _si * (math.pi/8)
                        _sr = pr * (1.8 if _si % 2 == 0 else 0.8)
                        _star_pts.append((px + math.cos(_sa)*_sr, py + math.sin(_sa)*_sr))
                    try:
                        pygame.draw.polygon(self.tela, (255, 255, 200), [(int(p[0]),int(p[1])) for p in _star_pts])
                        pygame.draw.polygon(self.tela, (255,255,255), [(int(p[0]),int(p[1])) for p in _star_pts], 1)
                    except Exception: pass

                elif _el_proj == "ARCANO":
                    # Orbe arcano: círculo com 3 anéis giratórios
                    pygame.draw.circle(self.tela, (200, 100, 255), (int(px), int(py)), int(pr))
                    pygame.draw.circle(self.tela, (255, 200, 255), (int(px), int(py)), max(1, int(pr*0.5)))
                    for _ai in range(3):
                        _aa = _pkt * (4 + _ai) + _ai * (math.pi * 2 / 3)
                        _ar = pr * (1.2 + _ai * 0.15)
                        _ax = int(px + math.cos(_aa) * _ar * 0.5)
                        _ay = int(py + math.sin(_aa) * _ar * 0.5)
                        pygame.draw.circle(self.tela, (255, 150, 255), (_ax, _ay), max(1, int(pr*0.25)))

                elif _el_proj == "SANGUE":
                    # Gota de sangue
                    pygame.draw.circle(self.tela, (180, 0, 30), (int(px), int(py)), int(pr))
                    pygame.draw.circle(self.tela, (255, 100, 100), (int(px-pr*0.25), int(py-pr*0.25)), max(1, int(pr*0.35)))
                    try:
                        _dtail = [(int(px-pr*0.3), int(py)),
                                   (int(px+pr*0.3), int(py)),
                                   (int(px), int(py+pr*1.8))]
                        pygame.draw.polygon(self.tela, (180, 0, 30), _dtail)
                    except Exception: pass

                elif _el_proj == "VOID":
                    # Buraco negro: preto com anel branco-roxo
                    pygame.draw.circle(self.tela, (5, 0, 15), (int(px), int(py)), int(pr))
                    pygame.draw.circle(self.tela, (80, 0, 120), (int(px), int(py)), int(pr), 3)
                    # Distorção — pequenos arcos girando no exterior
                    for _vi in range(4):
                        _va = _pkt * (-2) + _vi * (math.pi/2)
                        _vr = pr * 1.5
                        try:
                            _vx1 = int(px + math.cos(_va)*_vr)
                            _vy1 = int(py + math.sin(_va)*_vr)
                            _vx2 = int(px + math.cos(_va + 0.5)*_vr)
                            _vy2 = int(py + math.sin(_va + 0.5)*_vr)
                            pygame.draw.line(self.tela, (120, 50, 180), (_vx1, _vy1), (_vx2, _vy2), 2)
                        except Exception: pass

                else:
                    # Padrão genérico mas com glow
                    pygame.draw.circle(self.tela, cor, (int(px), int(py)), int(pr))
                    pygame.draw.circle(self.tela, BRANCO, (int(px), int(py)), max(1, int(pr)-2))

        # === DESENHA ORBES MÁGICOS ===
        for p in [self.p1, self.p2]:
            if hasattr(p, 'buffer_orbes'):
                for orbe in p.buffer_orbes:
                    if not orbe.ativo:
                        continue
                    
                    ox, oy = self.cam.converter(orbe.x * PPM, orbe.y * PPM)
                    or_visual = self.cam.converter_tam(orbe.raio_visual * PPM)
                    
                    # Trail quando disparando
                    if orbe.estado == "disparando" and len(orbe.trail) > 1:
                        for i in range(1, len(orbe.trail)):
                            alpha = int(255 * (i / len(orbe.trail)) * 0.6)
                            p1 = self.cam.converter(orbe.trail[i-1][0] * PPM, orbe.trail[i-1][1] * PPM)
                            p2 = self.cam.converter(orbe.trail[i][0] * PPM, orbe.trail[i][1] * PPM)
                            cor_trail = tuple(min(255, c + 50) for c in orbe.cor)
                            pygame.draw.line(self.tela, cor_trail, p1, p2, max(2, int(or_visual * 0.5)))
                    
                    # Partículas mágicas
                    for part in orbe.particulas:
                        ppx, ppy = self.cam.converter(part['x'] * PPM, part['y'] * PPM)
                        palpha = int(255 * (part['vida'] / 0.3))
                        s = pygame.Surface((6, 6), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*part['cor'], palpha), (3, 3), 3)
                        self.tela.blit(s, (ppx - 3, ppy - 3))
                    
                    # Glow externo
                    glow_size = int(or_visual * 2.5)
                    if glow_size > 2:
                        s = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                        # Pulso de brilho
                        pulso = 0.7 + 0.3 * math.sin(orbe.pulso)
                        glow_alpha = int(100 * pulso)
                        cor_glow = (*orbe.cor[:3], glow_alpha)
                        pygame.draw.circle(s, cor_glow, (glow_size, glow_size), glow_size)
                        self.tela.blit(s, (ox - glow_size, oy - glow_size))
                    
                    # Orbe principal (núcleo brilhante)
                    if or_visual > 1:
                        # Borda colorida
                        pygame.draw.circle(self.tela, orbe.cor, (int(ox), int(oy)), int(or_visual))
                        # Core branco
                        pygame.draw.circle(self.tela, BRANCO, (int(ox), int(oy)), max(1, int(or_visual * 0.5)))
                    
                    # Estado visual extra
                    if orbe.estado == "carregando":
                        # Anéis de carga
                        carga_pct = orbe.tempo_carga / orbe.carga_max
                        ring_r = int(or_visual * (1.5 + carga_pct))
                        pygame.draw.circle(self.tela, orbe.cor, (int(ox), int(oy)), ring_r, 1)

        # === EFEITOS v7.0 IMPACT EDITION ===
        for ef in self.dash_trails: ef.draw(self.tela, self.cam)
        for ef in self.hit_sparks: ef.draw(self.tela, self.cam)
        for ef in self.magic_clashes: ef.draw(self.tela, self.cam)
        for ef in self.impact_flashes: ef.draw(self.tela, self.cam)
        for ef in self.block_effects: ef.draw(self.tela, self.cam)
        
        # === MAGIC VFX v11.0 DRAMATIC EDITION ===
        if hasattr(self, 'magic_vfx') and self.magic_vfx:
            self.magic_vfx.draw(self.tela, self.cam)

        # === ANIMAÇÕES DE MOVIMENTO v8.0 CINEMATIC EDITION ===
        if self.movement_anims:
            self.movement_anims.draw(self.tela, self.cam)

        # === ANIMAÇÕES DE ATAQUE v8.0 IMPACT EDITION ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_effects(self.tela, self.cam)

        for s in self.shockwaves: s.draw(self.tela, self.cam)
        for t in self.textos: t.draw(self.tela, self.cam)

        # === SCREEN EFFECTS (FLASH) v8.0 IMPACT ===
        if hasattr(self, 'attack_anims') and self.attack_anims:
            self.attack_anims.draw_screen_effects(self.tela, self.screen_width, self.screen_height)

        # === DEBUG VISUAL DE HITBOX ===
        if self.show_hitbox_debug:
            self.desenhar_hitbox_debug()

        if self.show_hud:
            if not self.vencedor:
                self.desenhar_barras(self.p1, 20, 20, COR_P1, self.vida_visual_p1)
                # Ajusta posição P2 baseado no modo (220 em portrait, 320 em normal)
                p2_offset = 220 if self.portrait_mode else 320
                self.desenhar_barras(self.p2, self.screen_width - p2_offset, 20, COR_P2, self.vida_visual_p2)
                # DES-4: Timer de luta no centro do HUD
                tempo_restante = max(0, self.TEMPO_MAX_LUTA - self.tempo_luta)
                cor_timer = (255, 80, 80) if tempo_restante < 15 else (255, 255, 255)
                font_timer = pygame.font.SysFont("Impact", 28)
                txt_timer = font_timer.render(f"{int(tempo_restante)}", True, cor_timer)
                self.tela.blit(txt_timer, (self.screen_width // 2 - txt_timer.get_width() // 2, 24))
                if not self.portrait_mode:  # Esconde controles em portrait para mais espaço
                    self.desenhar_controles() 
            else: self.desenhar_vitoria()
            if self.paused: self.desenhar_pause()
        if self.show_analysis: self.desenhar_analise()


    def desenhar_grid(self):
        start_x = int((-self.cam.x * self.cam.zoom) % (50 * self.cam.zoom))
        start_y = int((-self.cam.y * self.cam.zoom) % (50 * self.cam.zoom))
        step = int(50 * self.cam.zoom)
        for x in range(start_x, self.screen_width, step): pygame.draw.line(self.tela, COR_GRID, (x, 0), (x, self.screen_height))
        for y in range(start_y, self.screen_height, step): pygame.draw.line(self.tela, COR_GRID, (0, y), (self.screen_width, y))


    def desenhar_lutador(self, l):
        px = l.pos[0] * PPM; py = l.pos[1] * PPM
        sx, sy = self.cam.converter(px, py); off_y = self.cam.converter_tam(l.z * PPM); raio = self.cam.converter_tam((l.dados.tamanho / 2) * PPM)
        if l in self.rastros and len(self.rastros[l]) > 2:
            pts_rastro = []
            for ponta, cabo in self.rastros[l]:
                p_conv = self.cam.converter(ponta[0], ponta[1]); c_conv = self.cam.converter(cabo[0], cabo[1])
                p_conv = (p_conv[0], p_conv[1] - off_y); c_conv = (c_conv[0], c_conv[1] - off_y)
                pts_rastro.append(p_conv); pts_rastro.insert(0, c_conv)
            s = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            cor_rastro = (l.dados.arma_obj.r, l.dados.arma_obj.g, l.dados.arma_obj.b, 80)
            if len(pts_rastro) > 2: pygame.draw.polygon(s, cor_rastro, pts_rastro); self.tela.blit(s, (0,0))
        if l.morto:
            pygame.draw.ellipse(self.tela, COR_CORPO, (sx-raio, sy-raio, raio*2, raio*2))
            if l.dados.arma_obj:
                ax = l.arma_droppada_pos[0]*PPM; ay = l.arma_droppada_pos[1]*PPM
                asx, asy = self.cam.converter(ax, ay)
                self.desenhar_arma(l.dados.arma_obj, (asx, asy), l.arma_droppada_ang, l.dados.tamanho, raio)
            return
        sombra = pygame.Surface((raio*2, raio*2), pygame.SRCALPHA); pygame.draw.ellipse(sombra, (0,0,0,80), (0,0,raio*2, raio*2))
        tam_s = int(raio * 2 * max(0.4, 1.0 - (l.z/4.0)))
        if tam_s > 0:
            sombra_scaled = pygame.transform.scale(sombra, (tam_s, tam_s)); self.tela.blit(sombra_scaled, (sx-tam_s//2, sy-tam_s//2))
        centro = (sx, sy - off_y)
        
        # === COR DO CORPO COM FLASH DE DANO MELHORADO ===
        if l.flash_timer > 0:
            # Usa cor de flash personalizada se disponível
            flash_cor = getattr(l, 'flash_cor', (255, 255, 255))
            # Intensidade do flash diminui com o tempo
            flash_intensity = l.flash_timer / 0.25
            # Mistura cor original com cor de flash
            cor_r = getattr(l.dados, 'cor_r', 200) or 200
            cor_g = getattr(l.dados, 'cor_g', 50) or 50
            cor_b = getattr(l.dados, 'cor_b', 50) or 50
            cor_original = (cor_r, cor_g, cor_b)
            cor = tuple(int(max(0, min(255, flash_cor[i] * flash_intensity + cor_original[i] * (1 - flash_intensity)))) for i in range(3))
        else:
            cor_r = getattr(l.dados, 'cor_r', 200) or 200
            cor_g = getattr(l.dados, 'cor_g', 50) or 50
            cor_b = getattr(l.dados, 'cor_b', 50) or 50
            cor = (int(cor_r), int(cor_g), int(cor_b))
        
        pygame.draw.circle(self.tela, cor, centro, raio)
        
        # === CONTORNO APRIMORADO ===
        if l.stun_timer > 0:
            contorno = AMARELO_FAISCA
            largura = max(2, self.cam.converter_tam(5))
        elif l.atacando:
            contorno = (255, 255, 255)
            largura = max(2, self.cam.converter_tam(4))
        elif l.flash_timer > 0:
            # Contorno vermelho durante dano
            contorno = (255, 100, 100)
            largura = max(2, self.cam.converter_tam(4))
        else:
            contorno = (50, 50, 50)
            largura = max(1, self.cam.converter_tam(2))
        
        pygame.draw.circle(self.tela, contorno, centro, raio, largura)
        
        # === EFEITO DE GLOW EM VIDA BAIXA (ADRENALINA) ===
        if l.modo_adrenalina and not l.morto:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150)
            glow_size = int(raio * 1.3)
            s = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            glow_alpha = int(60 * pulso)
            pygame.draw.circle(s, (255, 50, 50, glow_alpha), (glow_size, glow_size), glow_size)
            self.tela.blit(s, (centro[0] - glow_size, centro[1] - glow_size))
        
        # === RENDERIZA ARMA COM ANIMAÇÕES APRIMORADAS ===
        if l.dados.arma_obj:
            # Aplica shake da animação
            shake = getattr(l, 'weapon_anim_shake', (0, 0))
            centro_ajustado = (centro[0] + shake[0], centro[1] + shake[1])
            
            # Escala da animação
            anim_scale = getattr(l, 'weapon_anim_scale', 1.0)
            
            # Desenha slash arc se estiver atacando (para armas melee)
            if l.atacando and l.dados.arma_obj.tipo in ["Reta", "Dupla", "Corrente", "Transformável"]:
                self._desenhar_slash_arc(l, centro, raio, anim_scale)
            
            # Desenha trail antes da arma
            self._desenhar_weapon_trail(l)
            
            # Desenha arma com escala
            self.desenhar_arma(l.dados.arma_obj, centro_ajustado, l.angulo_arma_visual, 
                             l.dados.tamanho, raio, anim_scale)

        # === TAG DE NOME (estilo Minecraft) — sempre acima da cabeça ===
        self._desenhar_nome_tag(l, centro, raio)


    def _desenhar_nome_tag(self, l, centro, raio):
        """Desenha o nome do personagem flutuando acima da cabeça, estilo Minecraft."""
        nome = l.dados.nome
        hp_pct = l.vida / l.vida_max if l.vida_max > 0 else 0.0

        # Posição: acima do topo do círculo (centro já desconta o Z via off_y em desenhar_lutador)
        OFFSET_Y = 14   # pixels acima do topo do círculo

        # === FONTE ===
        if not hasattr(self, '_fonte_nametag'):
            self._fonte_nametag = pygame.font.SysFont("Arial", 13, bold=True)
        font = self._fonte_nametag
        texto = font.render(nome, True, (255, 255, 255))
        tw = texto.get_width()
        th = texto.get_height()

        tag_x = centro[0]
        tag_y = centro[1] - raio - OFFSET_Y - th

        # === FUNDO SEMI-TRANSPARENTE (placa preta) ===
        padding_x, padding_y = 6, 3
        bg_w = tw + padding_x * 2
        bg_h = th + padding_y * 2
        bg_x = tag_x - bg_w // 2
        bg_y = tag_y - padding_y

        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.tela.blit(bg, (bg_x, bg_y))

        # === TEXTO DO NOME ===
        self.tela.blit(texto, (tag_x - tw // 2, tag_y))

        # === BARRA DE VIDA MINÚSCULA ABAIXO DO NOME ===
        bar_w = bg_w
        bar_h = 4
        bar_x = bg_x
        bar_y = bg_y + bg_h + 2

        # Fundo da barra
        pygame.draw.rect(self.tela, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))

        # Cor da barra: verde → amarelo → vermelho
        if hp_pct > 0.5:
            t = (hp_pct - 0.5) / 0.5
            cor_hp = (int(255 * (1 - t)), 200, 0)
        else:
            t = hp_pct / 0.5
            cor_hp = (220, int(200 * t), 0)

        vida_w = int(bar_w * max(0, hp_pct))
        if vida_w > 0:
            pygame.draw.rect(self.tela, cor_hp, (bar_x, bar_y, vida_w, bar_h))

        # Borda da barra
        pygame.draw.rect(self.tela, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h), 1)


    def _desenhar_slash_arc(self, lutador, centro, raio, anim_scale):
        """Desenha arco de corte visível durante ataques melee"""
        arma = lutador.dados.arma_obj
        if not arma:
            return
        
        # Cor do arco baseada na arma
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (255, 255, 255)
        cor_brilho = tuple(min(255, c + 80) for c in cor)
        
        # Progresso da animação
        timer = lutador.timer_animacao
        
        # Perfil da arma para saber a duração total
        from effects.weapon_animations import WEAPON_PROFILES
        profile = WEAPON_PROFILES.get(arma.tipo, WEAPON_PROFILES["Reta"])
        total_time = profile.total_time
        
        # Progresso normalizado (0-1)
        prog = 1.0 - (timer / total_time) if total_time > 0 else 0
        
        # Só desenha durante a fase de ataque principal (não na anticipation ou recovery)
        antecipation_end = profile.anticipation_time / total_time
        attack_end = (profile.anticipation_time + profile.attack_time + profile.impact_time) / total_time
        
        if prog < antecipation_end or prog > attack_end + 0.2:
            return
        
        # Calcula fase dentro do ataque
        attack_prog = (prog - antecipation_end) / max(attack_end - antecipation_end, 0.01)
        attack_prog = max(0, min(1, attack_prog))
        
        # Parâmetros do arco
        angulo_base = lutador.angulo_olhar
        arc_start = angulo_base + profile.anticipation_angle
        arc_end = angulo_base + profile.attack_angle
        
        # Ângulo atual do arco (expande ao longo do ataque)
        current_arc = arc_start + (arc_end - arc_start) * attack_prog
        
        # Raio do arco
        arc_radius = raio * 2.5 * anim_scale
        
        # Alpha diminui conforme avança
        alpha = int(180 * (1 - attack_prog * 0.7))
        
        # Largura do arco
        arc_width = max(3, int(8 * (1 - attack_prog * 0.5)))
        
        # Desenha o arco de corte
        s = pygame.Surface((int(arc_radius * 3), int(arc_radius * 3)), pygame.SRCALPHA)
        arc_center = (int(arc_radius * 1.5), int(arc_radius * 1.5))
        
        # Calcula pontos do arco
        num_points = 15
        points_outer = []
        points_inner = []
        
        for i in range(num_points + 1):
            t = i / num_points
            angle = math.radians(arc_start + (current_arc - arc_start) * t)
            
            # Ponto externo
            ox = arc_center[0] + math.cos(angle) * arc_radius
            oy = arc_center[1] + math.sin(angle) * arc_radius
            points_outer.append((ox, oy))
            
            # Ponto interno (para criar espessura)
            inner_radius = arc_radius * 0.7
            ix = arc_center[0] + math.cos(angle) * inner_radius
            iy = arc_center[1] + math.sin(angle) * inner_radius
            points_inner.append((ix, iy))
        
        # Cria polígono do arco
        if len(points_outer) > 2:
            arc_polygon = points_outer + points_inner[::-1]
            
            # Cor com alpha
            arc_color = (*cor_brilho, alpha)
            pygame.draw.polygon(s, arc_color, arc_polygon)
            
            # Contorno mais brilhante
            pygame.draw.lines(s, (*cor, min(255, alpha + 50)), False, points_outer, 2)
        
        # Blit na posição do lutador
        blit_pos = (centro[0] - arc_center[0], centro[1] - arc_center[1])
        self.tela.blit(s, blit_pos)

    
    def _desenhar_weapon_trail(self, lutador):
        """Desenha o trail da arma durante ataques"""
        trail = getattr(lutador, 'weapon_trail_positions', [])
        if len(trail) < 2:
            return
        
        arma = lutador.dados.arma_obj
        if not arma:
            return
        
        cor = (arma.r, arma.g, arma.b) if hasattr(arma, 'r') else (200, 200, 200)
        tipo = arma.tipo
        
        # Diferentes estilos de trail por tipo
        for i in range(len(trail) - 1):
            x1, y1, a1 = trail[i]
            x2, y2, a2 = trail[i + 1]
            
            # Converte para tela (coordenadas mundo -> pixels)
            from utils.config import PPM
            p1 = self.cam.converter(x1 * PPM, y1 * PPM)
            p2 = self.cam.converter(x2 * PPM, y2 * PPM)
            
            alpha = min(a1, a2)
            if alpha < 0.1:
                continue
            
            # Largura e cor com fade
            width = max(1, int(5 * (i / len(trail)) * alpha))
            
            if tipo == "Mágica":
                # Trail brilhante para magia
                bright = tuple(min(255, int(c + 80 * alpha)) for c in cor)
                pygame.draw.line(self.tela, bright, p1, p2, width + 2)
                
                # Partícula no final
                if i == len(trail) - 2 and alpha > 0.5:
                    glow_size = int(8 * alpha)
                    s = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                    glow_alpha = int(100 * alpha)
                    pygame.draw.circle(s, (*cor, glow_alpha), (glow_size, glow_size), glow_size)
                    self.tela.blit(s, (p2[0] - glow_size, p2[1] - glow_size))
            else:
                # Trail padrão de corte
                blend = alpha * 0.8
                trail_color = tuple(min(255, int(c * 0.5 + 127 * blend)) for c in cor)
                pygame.draw.line(self.tela, trail_color, p1, p2, width)


    def desenhar_arma(self, arma, centro, angulo, tam_char, raio_char, anim_scale=1.0):
        """
        Renderiza a arma do lutador - VERSÃO APRIMORADA v3.0
        Visual muito mais bonito com gradientes, brilhos e detalhes.
        """
        cx, cy = centro
        rad = math.radians(angulo)
        
        # Cores da arma com validação
        cor_r = getattr(arma, 'r', 180) or 180
        cor_g = getattr(arma, 'g', 180) or 180
        cor_b = getattr(arma, 'b', 180) or 180
        cor = (int(cor_r), int(cor_g), int(cor_b))
        
        # Cor mais clara para highlights
        cor_clara = tuple(min(255, c + 60) for c in cor)
        # Cor mais escura para sombras
        cor_escura = tuple(max(0, c - 40) for c in cor)
        
        # Cor de raridade para efeitos especiais
        raridade = getattr(arma, 'raridade', 'Comum')
        cores_raridade = {
            'Comum': (180, 180, 180),
            'Incomum': (30, 255, 30),
            'Raro': (30, 144, 255),
            'Épico': (148, 0, 211),
            'Lendário': (255, 165, 0),
            'Mítico': (255, 20, 147)
        }
        cor_raridade = cores_raridade.get(raridade, (180, 180, 180))
        
        tipo = getattr(arma, 'tipo', 'Reta')
        
        # Escala base da arma
        base_scale = raio_char * 0.025  # Escala relativa ao personagem
        
        # Largura da arma proporcional
        larg_base = max(3, int(raio_char * 0.12 * anim_scale))
        
        # Flag de ataque ativo (para efeitos especiais)
        atacando = anim_scale > 1.05
        tempo = pygame.time.get_ticks()
        
        # Helper para estilos Dupla: polígono cônico (base larga → ponta)
        def _dupla_blade_poly(bx, by, tx, ty, ang, w_base, w_tip):
            px = math.cos(ang + math.pi/2)
            py = math.sin(ang + math.pi/2)
            return [
                (int(bx - px*w_base), int(by - py*w_base)),
                (int(bx + px*w_base), int(by + py*w_base)),
                (int(tx + px*w_tip),  int(ty + py*w_tip)),
                (int(tx),             int(ty)),
                (int(tx - px*w_tip),  int(ty - py*w_tip)),
            ]

        # === RETA (Espadas, Lanças, Machados) ===
        if tipo == "Reta":
            estilo_arma = getattr(arma, 'estilo', '')
            # Geometria fixa por estilo (baseada em raio_char)
            if 'Lança' in estilo_arma or 'Estocada' in estilo_arma:
                cabo_len   = raio_char * 1.00
                lamina_len = raio_char * 1.80 * anim_scale
            elif 'Maça' in estilo_arma or 'Contusão' in estilo_arma:
                cabo_len   = raio_char * 0.90
                lamina_len = raio_char * 0.70 * anim_scale
            else:  # Espada / Misto
                cabo_len   = raio_char * 0.55
                lamina_len = raio_char * 1.30 * anim_scale
            larg = max(4, int(larg_base * 1.2))

            cabo_end_x = cx + math.cos(rad) * cabo_len
            cabo_end_y = cy + math.sin(rad) * cabo_len
            lamina_end_x = cx + math.cos(rad) * (cabo_len + lamina_len)
            lamina_end_y = cy + math.sin(rad) * (cabo_len + lamina_len)

            perp_x = math.cos(rad + math.pi/2)
            perp_y = math.sin(rad + math.pi/2)

            # ── ESTOCADA (Lança) — haste longa, ponta de metal estreita ──
            if "Lança" in estilo_arma or "Estocada" in estilo_arma:
                # Haste de madeira (mais fina)
                for i in range(2):
                    shade = (90 - i*20, 55 - i*15, 22 - i*8)
                    pygame.draw.line(self.tela, shade,
                                     (int(cx), int(cy)), (int(cabo_end_x), int(cabo_end_y)),
                                     max(2, larg - i*2))
                # Ponteira metálica — triângulo estreito e longo
                tip_w = max(2, larg - 2)
                lance_pts = [
                    (int(cabo_end_x - perp_x * tip_w), int(cabo_end_y - perp_y * tip_w)),
                    (int(cabo_end_x + perp_x * tip_w), int(cabo_end_y + perp_y * tip_w)),
                    (int(lamina_end_x + perp_x), int(lamina_end_y + perp_y)),
                    (int(lamina_end_x), int(lamina_end_y)),
                    (int(lamina_end_x - perp_x), int(lamina_end_y - perp_y)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor_escura, lance_pts)
                    pygame.draw.polygon(self.tela, cor, lance_pts, 1)
                except Exception: pass  # QC-01
                # Anel metálico na virola
                pygame.draw.circle(self.tela, (160,165,175), (int(cabo_end_x), int(cabo_end_y)), larg//2 + 1, 2)
                # Fio central da ponta
                pygame.draw.line(self.tela, cor_clara,
                                 (int(cabo_end_x), int(cabo_end_y)),
                                 (int(lamina_end_x), int(lamina_end_y)), 1)

            # ── CONTUSÃO (Maça) — cabo + cabeça larga com espigões ───────
            elif "Maça" in estilo_arma or "Contusão" in estilo_arma:
                # Cabo
                pygame.draw.line(self.tela, (30, 18, 8),
                                 (int(cx)+1, int(cy)+1), (int(cabo_end_x)+1, int(cabo_end_y)+1), larg+2)
                pygame.draw.line(self.tela, (90, 55, 25),
                                 (int(cx), int(cy)), (int(cabo_end_x), int(cabo_end_y)), larg)
                # Cabeça — cilindro largo
                head_half = larg * 1.8
                head_pts = [
                    (int(cabo_end_x - perp_x*head_half), int(cabo_end_y - perp_y*head_half)),
                    (int(cabo_end_x + perp_x*head_half), int(cabo_end_y + perp_y*head_half)),
                    (int(lamina_end_x + perp_x*head_half), int(lamina_end_y + perp_y*head_half)),
                    (int(lamina_end_x - perp_x*head_half), int(lamina_end_y - perp_y*head_half)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor_escura, head_pts)
                    pygame.draw.polygon(self.tela, cor, head_pts, 2)
                except Exception: pass  # QC-01
                # Espigões nas 4 faces
                mid_x = (cabo_end_x + lamina_end_x) / 2
                mid_y = (cabo_end_y + lamina_end_y) / 2
                for s_sign in [-1, 1]:
                    sx1 = int(mid_x + perp_x * head_half * s_sign)
                    sy1 = int(mid_y + perp_y * head_half * s_sign)
                    sx2 = int(mid_x + perp_x * (head_half + 6) * s_sign)
                    sy2 = int(mid_y + perp_y * (head_half + 6) * s_sign)
                    pygame.draw.line(self.tela, cor_clara, (sx1, sy1), (sx2, sy2), max(2, larg//2))
                # Highlight
                pygame.draw.circle(self.tela, cor_clara, (int(cabo_end_x), int(cabo_end_y)), max(2, larg//3))
                if raridade not in ['Comum', 'Incomum']:
                    pulso = 0.5 + 0.5 * math.sin(tempo/200)
                    pygame.draw.circle(self.tela, cor_raridade,
                                       (int(lamina_end_x), int(lamina_end_y)), max(3, int(larg*0.8*(1+pulso*0.3))))

            # ── CORTE (Espada) — lâmina larga, guarda, fio ───────────────
            else:  # "Espada" in estilo ou "Misto" ou fallback
                # Guarda (oval perpendicular)
                guarda_x = cabo_end_x + math.cos(rad) * 2
                guarda_y = cabo_end_y + math.sin(rad) * 2
                pygame.draw.ellipse(self.tela, (80, 60, 40),
                                    (int(guarda_x - larg*1.5), int(guarda_y - larg*0.8), larg*3, larg*1.6))
                # Cabo com faixas de couro
                for i in range(3):
                    shade = (90 - i*15, 50 - i*10, 20 - i*5)
                    pygame.draw.line(self.tela, shade,
                                     (int(cx)+i-1, int(cy)+i-1),
                                     (int(cabo_end_x)+i-1, int(cabo_end_y)+i-1), max(2, larg - i))
                # Lâmina (polígono)
                lamina_pts = [
                    (int(cabo_end_x - perp_x*larg*0.6), int(cabo_end_y - perp_y*larg*0.6)),
                    (int(cabo_end_x + perp_x*larg*0.6), int(cabo_end_y + perp_y*larg*0.6)),
                    (int(lamina_end_x - perp_x*larg*0.3), int(lamina_end_y - perp_y*larg*0.3)),
                    (int(lamina_end_x), int(lamina_end_y)),
                    (int(lamina_end_x + perp_x*larg*0.3), int(lamina_end_y + perp_y*larg*0.3)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor, lamina_pts)
                    pygame.draw.polygon(self.tela, cor_escura, lamina_pts, 1)
                except Exception: pass  # QC-01
                # Fio (highlight)
                mid_x = (cabo_end_x + lamina_end_x) / 2
                mid_y = (cabo_end_y + lamina_end_y) / 2
                pygame.draw.line(self.tela, cor_clara,
                                 (int(cabo_end_x), int(cabo_end_y)), (int(mid_x), int(mid_y)),
                                 max(1, larg//3))
                # Glow de raridade
                if raridade not in ['Comum', 'Incomum']:
                    pulso = 0.5 + 0.5 * math.sin(tempo/200)
                    pygame.draw.circle(self.tela, cor_raridade,
                                       (int(lamina_end_x), int(lamina_end_y)),
                                       max(3, int(larg*0.8*(1+pulso*0.3))))
                # Glow de ataque
                if atacando:
                    try:
                        gl = pygame.Surface((int(lamina_len*2), int(lamina_len*2)), pygame.SRCALPHA)
                        for r2 in range(3, 0, -1):
                            pygame.draw.line(gl, (*cor_clara, 50//r2),
                                             (int(lamina_len), int(lamina_len)),
                                             (int(lamina_len + math.cos(rad)*lamina_len*0.8),
                                              int(lamina_len + math.sin(rad)*lamina_len*0.8)), larg+r2*2)
                        self.tela.blit(gl, (int(cabo_end_x-lamina_len), int(cabo_end_y-lamina_len)))
                    except Exception: pass  # QC-01
        
        # === DUPLA - ADAGAS GÊMEAS v3.0 (Karambit Reverse-Grip) ===
        elif tipo == "Dupla":
            estilo_arma = getattr(arma, 'estilo', '')
            sep = raio_char * 0.55  # separação fixa
            larg = max(4, int(larg_base * 1.1))

            if estilo_arma == "Adagas Gêmeas":
                # ── ADAGAS GÊMEAS v3.1: Laterais do corpo, empunhadura normal apontando à frente ──
                # Cada daga fica na mão do personagem (lateral), lâmina apontando na direção do ataque
                cabo_len   = raio_char * 0.35
                lamina_len = raio_char * 1.05 * anim_scale
                pulso = 0.5 + 0.5 * math.sin(tempo / 180)
                glow_alpha_base = int(100 + 70 * pulso) if atacando else int(35 + 20 * pulso)

                for i, lado_sinal in enumerate([-1, 1]):
                    # ── Posição da mão: lateral ao corpo, fora do centro ──
                    # sep já dá a separação lateral adequada
                    hand_x = cx + math.cos(rad + math.pi/2) * sep * lado_sinal * 0.85
                    hand_y = cy + math.sin(rad + math.pi/2) * sep * lado_sinal * 0.85

                    # Ângulo da daga: aponta para frente com leve abertura lateral
                    spread_deg = 18 * lado_sinal  # abertura: esquerda vai -18°, direita vai +18°
                    daga_ang = rad + math.radians(spread_deg)

                    # ── Cabo (handle) ──
                    cabo_ex = hand_x + math.cos(daga_ang) * cabo_len
                    cabo_ey = hand_y + math.sin(daga_ang) * cabo_len
                    # Sombra
                    pygame.draw.line(self.tela, (30, 18, 8),
                                     (int(hand_x)+1, int(hand_y)+1),
                                     (int(cabo_ex)+1, int(cabo_ey)+1), larg + 3)
                    # Madeira/grip
                    pygame.draw.line(self.tela, (60, 38, 18),
                                     (int(hand_x), int(hand_y)),
                                     (int(cabo_ex), int(cabo_ey)), larg + 2)
                    pygame.draw.line(self.tela, (100, 65, 30),
                                     (int(hand_x), int(hand_y)),
                                     (int(cabo_ex), int(cabo_ey)), max(1, larg))
                    # Faixas de grip
                    for gi in range(1, 4):
                        gt = gi / 4
                        gx = int(hand_x + (cabo_ex - hand_x) * gt)
                        gy = int(hand_y + (cabo_ey - hand_y) * gt)
                        gp_x = math.cos(daga_ang + math.pi/2) * (larg + 1)
                        gp_y = math.sin(daga_ang + math.pi/2) * (larg + 1)
                        pygame.draw.line(self.tela, (45, 28, 10),
                                         (int(gx-gp_x), int(gy-gp_y)),
                                         (int(gx+gp_x), int(gy+gp_y)), 1)

                    # ── Guarda cruzada (finger guard) ──
                    grd_x = math.cos(daga_ang + math.pi/2) * (larg + 3)
                    grd_y = math.sin(daga_ang + math.pi/2) * (larg + 3)
                    pygame.draw.line(self.tela, (150, 155, 165),
                                     (int(cabo_ex - grd_x), int(cabo_ey - grd_y)),
                                     (int(cabo_ex + grd_x), int(cabo_ey + grd_y)), max(2, larg))

                    # ── Lâmina: reta com ponta levemente curvada para dentro ──
                    # Divide em dois segmentos: corpo reto + curva terminal
                    corpo_pct = 0.72  # 72% da lâmina é reta
                    curva_pct = 0.28  # 28% final curva levemente

                    corpo_end_x = cabo_ex + math.cos(daga_ang) * lamina_len * corpo_pct
                    corpo_end_y = cabo_ey + math.sin(daga_ang) * lamina_len * corpo_pct

                    # Curva da ponta (gira ligeiramente para o centro)
                    curva_deg = -12 * lado_sinal  # curva para dentro
                    curva_ang = daga_ang + math.radians(curva_deg)
                    tip_x = corpo_end_x + math.cos(curva_ang) * lamina_len * curva_pct
                    tip_y = corpo_end_y + math.sin(curva_ang) * lamina_len * curva_pct

                    # Largura da lâmina (afunila até a ponta)
                    lam_w_base = max(3, larg - 1)
                    lam_w_tip  = max(1, larg // 3)

                    # Sombra da lâmina
                    pygame.draw.line(self.tela, (20, 20, 25),
                                     (int(cabo_ex)+1, int(cabo_ey)+1),
                                     (int(tip_x)+1,   int(tip_y)+1), lam_w_base + 2)

                    # Corpo da lâmina (parte reta)
                    perp_bx = math.cos(daga_ang + math.pi/2)
                    perp_by = math.sin(daga_ang + math.pi/2)
                    lam_poly = [
                        (int(cabo_ex - perp_bx * lam_w_base), int(cabo_ey - perp_by * lam_w_base)),
                        (int(cabo_ex + perp_bx * lam_w_base), int(cabo_ey + perp_by * lam_w_base)),
                        (int(corpo_end_x + perp_bx * lam_w_tip), int(corpo_end_y + perp_by * lam_w_tip)),
                        (int(tip_x), int(tip_y)),
                        (int(corpo_end_x - perp_bx * lam_w_tip), int(corpo_end_y - perp_by * lam_w_tip)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, lam_poly)
                        pygame.draw.polygon(self.tela, cor, lam_poly, 1)
                    except Exception: pass  # QC-01
                    # Fio da lâmina (highlight central)
                    pygame.draw.line(self.tela, cor_clara,
                                     (int(cabo_ex), int(cabo_ey)),
                                     (int(corpo_end_x), int(corpo_end_y)), 1)

                    # ── Glow de energia durante ataque ──
                    if atacando or glow_alpha_base > 50:
                        try:
                            sz = max(8, int(lamina_len * 2))
                            gs = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                            mid_x = int((cabo_ex + tip_x) / 2) - sz
                            mid_y = int((cabo_ey + tip_y) / 2) - sz
                            local_s = (sz - int(cabo_ex - mid_x - sz), sz - int(cabo_ey - mid_y - sz))
                            local_e = (sz - int(cabo_ex - mid_x - sz) + int(tip_x - cabo_ex),
                                       sz - int(cabo_ey - mid_y - sz) + int(tip_y - cabo_ey))
                            pygame.draw.line(gs, (*cor, glow_alpha_base),
                                             (max(0,min(sz*2-1,local_s[0])), max(0,min(sz*2-1,local_s[1]))),
                                             (max(0,min(sz*2-1,local_e[0])), max(0,min(sz*2-1,local_e[1]))),
                                             max(4, lam_w_base + 3))
                            self.tela.blit(gs, (mid_x, mid_y))
                        except Exception: pass  # QC-01

                    # ── Runa na lâmina (raridade) ──
                    if raridade not in ['Comum', 'Incomum']:
                        rune_x = int((cabo_ex + corpo_end_x) / 2)
                        rune_y = int((cabo_ey + corpo_end_y) / 2)
                        rune_a = int(160 + 80 * math.sin(tempo / 120 + i * math.pi))
                        try:
                            rs = pygame.Surface((8, 8), pygame.SRCALPHA)
                            pygame.draw.circle(rs, (*cor_raridade, rune_a), (4, 4), 3)
                            self.tela.blit(rs, (rune_x - 4, rune_y - 4))
                        except Exception: pass  # QC-01

                    # ── Ponta brilhante ──
                    tip_r = max(2, larg - 1)
                    tip_a = int(160 + 80 * math.sin(tempo / 90 + i))
                    try:
                        ts = pygame.Surface((tip_r * 5, tip_r * 5), pygame.SRCALPHA)
                        pygame.draw.circle(ts, (*cor_clara, tip_a), (tip_r*2, tip_r*2), tip_r * 2)
                        self.tela.blit(ts, (int(tip_x) - tip_r*2, int(tip_y) - tip_r*2))
                    except Exception: pass  # QC-01
                    tip_cor = cor_raridade if raridade not in ['Comum'] else cor_clara
                    pygame.draw.circle(self.tela, tip_cor, (int(tip_x), int(tip_y)), tip_r)

            else:
                # ── PER-STYLE RENDERERS para os demais estilos Dupla ──
                # Kamas, Sai, Garras, Tonfas, Facas Táticas — cada um com visual único
                cabo_len   = raio_char * 0.40
                lamina_len = raio_char * 0.90 * anim_scale
                lw         = max(3, larg)
                pulso      = 0.5 + 0.5 * math.sin(tempo / 180)

                for i, lado_sinal in enumerate([-1, 1]):
                    # Posição da mão
                    hand_x = cx + math.cos(rad + math.pi/2) * sep * lado_sinal * 0.8
                    hand_y = cy + math.sin(rad + math.pi/2) * sep * lado_sinal * 0.8
                    # Ângulo com leve abertura lateral
                    spread = math.radians(20 * lado_sinal)
                    ang    = rad + spread

                    # Ponta do cabo
                    cabo_ex = hand_x + math.cos(ang) * cabo_len
                    cabo_ey = hand_y + math.sin(ang) * cabo_len

                    # Ponto final da lâmina
                    tip_x = cabo_ex + math.cos(ang) * lamina_len
                    tip_y = cabo_ey + math.sin(ang) * lamina_len

                    # ── KAMAS: foice — cabo + lâmina curva perpendicular ──
                    if estilo_arma == "Kamas":
                        # Cabo
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(hand_x)+1, int(hand_y)+1), (int(cabo_ex)+1, int(cabo_ey)+1), lw+2)
                        pygame.draw.line(self.tela, (90, 55, 25),
                                         (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw)
                        # Guarda (crossguard)
                        g_perp_x = math.cos(ang + math.pi/2) * (lw + 4)
                        g_perp_y = math.sin(ang + math.pi/2) * (lw + 4)
                        pygame.draw.line(self.tela, (160, 165, 175),
                                         (int(cabo_ex - g_perp_x), int(cabo_ey - g_perp_y)),
                                         (int(cabo_ex + g_perp_x), int(cabo_ey + g_perp_y)), max(2, lw-1))
                        # Lâmina curva (arco): gira 90° para o interior
                        curve_ang  = ang + math.pi/2 * lado_sinal
                        ctrl_x = cabo_ex + math.cos(curve_ang) * lamina_len * 0.5
                        ctrl_y = cabo_ey + math.sin(curve_ang) * lamina_len * 0.5
                        hook_x = cabo_ex + math.cos(curve_ang) * lamina_len
                        hook_y = cabo_ey + math.sin(curve_ang) * lamina_len
                        # Bézier aproximado: dividir em 8 segmentos
                        prev = (int(cabo_ex), int(cabo_ey))
                        for seg in range(1, 9):
                            t = seg / 8
                            bx = (1-t)**2*cabo_ex + 2*(1-t)*t*ctrl_x + t**2*hook_x
                            by = (1-t)**2*cabo_ey + 2*(1-t)*t*ctrl_y + t**2*hook_y
                            pygame.draw.line(self.tela, cor, prev, (int(bx), int(by)), lw)
                            prev = (int(bx), int(by))
                        # Glow na ponta
                        glow_r = max(3, lw)
                        try:
                            gs = pygame.Surface((glow_r*4, glow_r*4), pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor_clara, int(150+80*pulso)), (glow_r*2, glow_r*2), glow_r*2)
                            self.tela.blit(gs, (int(hook_x)-glow_r*2, int(hook_y)-glow_r*2))
                        except Exception: pass  # QC-01
                        pygame.draw.circle(self.tela, cor_raridade, (int(hook_x), int(hook_y)), glow_r)

                    # ── SAI: tridente — lâmina central + duas guardas diagonais ──
                    elif estilo_arma == "Sai":
                        # Cabo
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(hand_x)+1, int(hand_y)+1), (int(cabo_ex)+1, int(cabo_ey)+1), lw+2)
                        pygame.draw.line(self.tela, (90, 55, 25),
                                         (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw)
                        # Lâmina central
                        lam_poly_c = _dupla_blade_poly(hand_x, hand_y, tip_x, tip_y, ang, lw, lw//2)
                        try:
                            pygame.draw.polygon(self.tela, cor_escura, lam_poly_c)
                            pygame.draw.polygon(self.tela, cor, lam_poly_c, 1)
                        except Exception: pass  # QC-01
                        pygame.draw.line(self.tela, cor_clara, (int(cabo_ex), int(cabo_ey)), (int(tip_x), int(tip_y)), 1)
                        # Guardas (asas do Sai) — partem do final do cabo em diagonal
                        asa_len = lamina_len * 0.4
                        for asa_sinal in [-1, 1]:
                            asa_ang = ang + math.pi/2 * asa_sinal * 0.7
                            ax = cabo_ex + math.cos(asa_ang) * asa_len
                            ay = cabo_ey + math.sin(asa_ang) * asa_len
                            pygame.draw.line(self.tela, (180, 185, 195),
                                             (int(cabo_ex), int(cabo_ey)), (int(ax), int(ay)), max(1, lw-1))
                            pygame.draw.circle(self.tela, (200, 205, 215), (int(ax), int(ay)), max(2, lw-2))
                        # Ponta central
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip_x), int(tip_y)), max(2, lw-1))

                    # ── GARRAS: 3 lâminas curtas em leque de uma base knuckle ──
                    elif estilo_arma == "Garras":
                        # Base (knuckle duster)
                        perp_x = math.cos(ang + math.pi/2) * (lw + 3)
                        perp_y = math.sin(ang + math.pi/2) * (lw + 3)
                        base_pts = [
                            (int(hand_x - perp_x), int(hand_y - perp_y)),
                            (int(hand_x + perp_x), int(hand_y + perp_y)),
                            (int(cabo_ex + perp_x), int(cabo_ey + perp_y)),
                            (int(cabo_ex - perp_x), int(cabo_ey - perp_y)),
                        ]
                        try:
                            pygame.draw.polygon(self.tela, (55, 30, 12), base_pts)
                            pygame.draw.polygon(self.tela, (100, 65, 30), base_pts, 1)
                        except Exception: pass  # QC-01
                        # 3 garras em leque: -25°, 0°, +25°
                        garra_len = lamina_len * 0.7
                        for ga_deg in [-25 * lado_sinal, 0, 25 * lado_sinal]:
                            ga = ang + math.radians(ga_deg)
                            gx = cabo_ex + math.cos(ga) * garra_len
                            gy = cabo_ey + math.sin(ga) * garra_len
                            pygame.draw.line(self.tela, cor_escura, (int(cabo_ex)+1, int(cabo_ey)+1), (int(gx)+1, int(gy)+1), max(1, lw-1)+1)
                            pygame.draw.line(self.tela, cor,         (int(cabo_ex),   int(cabo_ey)),   (int(gx),   int(gy)),   max(1, lw-1))
                            pygame.draw.line(self.tela, cor_clara,   (int(cabo_ex),   int(cabo_ey)),   (int(gx),   int(gy)),   1)
                            pygame.draw.circle(self.tela, cor_raridade, (int(gx), int(gy)), max(2, lw-2))
                        # Glow de ataque nas garras
                        if atacando:
                            try:
                                sz = int(garra_len * 2.5)
                                gs = pygame.Surface((sz, sz), pygame.SRCALPHA)
                                pygame.draw.circle(gs, (*cor, int(80*pulso)), (sz//2, sz//2), sz//2)
                                self.tela.blit(gs, (int(cabo_ex)-sz//2, int(cabo_ey)-sz//2))
                            except Exception: pass  # QC-01

                    # ── TONFAS: bastão-L — braço longo + cabo perpendicular curto ──
                    elif estilo_arma == "Tonfas":
                        # Braço principal (lâmina = comprimento do bastão)
                        pygame.draw.line(self.tela, (20, 18, 20),
                                         (int(hand_x)+1, int(hand_y)+1), (int(tip_x)+1, int(tip_y)+1), lw+3)
                        pygame.draw.line(self.tela, cor, (int(hand_x), int(hand_y)), (int(tip_x), int(tip_y)), lw+1)
                        pygame.draw.line(self.tela, cor_clara, (int(hand_x), int(hand_y)), (int(tip_x), int(tip_y)), 1)
                        # Cabo perpendicular (pega) — 1/4 do braço a partir da mão
                        pivot_x = hand_x + math.cos(ang) * lamina_len * 0.28
                        pivot_y = hand_y + math.sin(ang) * lamina_len * 0.28
                        handle_ang = ang + math.pi/2 * lado_sinal
                        grip_x = pivot_x + math.cos(handle_ang) * cabo_len
                        grip_y = pivot_y + math.sin(handle_ang) * cabo_len
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(pivot_x)+1, int(pivot_y)+1), (int(grip_x)+1, int(grip_y)+1), lw+2)
                        pygame.draw.line(self.tela, (90, 55, 25),
                                         (int(pivot_x), int(pivot_y)), (int(grip_x), int(grip_y)), lw)
                        # Pontas brilhantes
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip_x),  int(tip_y)),  max(2, lw-1))
                        pygame.draw.circle(self.tela, (180, 185, 195), (int(grip_x), int(grip_y)), max(2, lw-2))
                        # Faixas de grip no cabo perpendicular
                        for fi in [0.35, 0.65]:
                            fx = int(pivot_x + (grip_x - pivot_x) * fi)
                            fy = int(pivot_y + (grip_y - pivot_y) * fi)
                            pygame.draw.circle(self.tela, (50, 28, 10), (fx, fy), max(2, lw-1))

                    # ── FACAS TÁTICAS (e fallback genérico): lâmina militar reta com fio ──
                    else:
                        # Cabo com serrilha
                        pygame.draw.line(self.tela, (30, 18, 8),
                                         (int(hand_x)+1, int(hand_y)+1), (int(cabo_ex)+1, int(cabo_ey)+1), lw+2)
                        pygame.draw.line(self.tela, (80, 48, 20),
                                         (int(hand_x), int(hand_y)), (int(cabo_ex), int(cabo_ey)), lw+1)
                        # Faixas de grip no cabo
                        for gi in range(1, 4):
                            gt = gi / 4
                            gx = int(hand_x + (cabo_ex - hand_x) * gt)
                            gy = int(hand_y + (cabo_ey - hand_y) * gt)
                            gp_x = math.cos(ang + math.pi/2) * (lw + 1)
                            gp_y = math.sin(ang + math.pi/2) * (lw + 1)
                            pygame.draw.line(self.tela, (45, 26, 8),
                                             (int(gx-gp_x), int(gy-gp_y)), (int(gx+gp_x), int(gy+gp_y)), 1)
                        # Guarda (crossguard)
                        g_perp_x = math.cos(ang + math.pi/2) * (lw + 4)
                        g_perp_y = math.sin(ang + math.pi/2) * (lw + 4)
                        pygame.draw.line(self.tela, (160, 165, 175),
                                         (int(cabo_ex - g_perp_x), int(cabo_ey - g_perp_y)),
                                         (int(cabo_ex + g_perp_x), int(cabo_ey + g_perp_y)), max(2, lw-1))
                        # Lâmina: polígono cônico
                        lam_poly = _dupla_blade_poly(hand_x, hand_y, tip_x, tip_y, ang, lw, max(1, lw//2))
                        try:
                            pygame.draw.polygon(self.tela, cor_escura, lam_poly)
                            pygame.draw.polygon(self.tela, cor,        lam_poly, 1)
                        except Exception: pass  # QC-01
                        # Fio central
                        pygame.draw.line(self.tela, cor_clara, (int(cabo_ex), int(cabo_ey)), (int(tip_x), int(tip_y)), 1)
                        # Serrilha no dorso (4 dentes)
                        perp_x = math.cos(ang + math.pi/2) * (lw + 1)
                        perp_y = math.sin(ang + math.pi/2) * (lw + 1)
                        for si in range(1, 5):
                            st  = si / 5
                            sx  = cabo_ex + (tip_x - cabo_ex) * st
                            sy  = cabo_ey + (tip_y - cabo_ey) * st
                            ts  = 0.04
                            tsx = cabo_ex + (tip_x - cabo_ex) * (st - ts)
                            tsy = cabo_ey + (tip_y - cabo_ey) * (st - ts)
                            pygame.draw.line(self.tela, cor_clara,
                                             (int(sx + perp_x), int(sy + perp_y)),
                                             (int(tsx + perp_x*2.5), int(tsy + perp_y*2.5)), 1)
                        # Glow de ataque
                        glow_a = int(100 + 70 * pulso) if atacando else int(30 + 15 * pulso)
                        try:
                            sz = max(8, int(lamina_len * 2))
                            gs = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
                            mid_x = int((cabo_ex + tip_x) / 2) - sz
                            mid_y = int((cabo_ey + tip_y) / 2) - sz
                            ls = (sz - int(cabo_ex - mid_x - sz), sz - int(cabo_ey - mid_y - sz))
                            le = (sz - int(cabo_ex - mid_x - sz) + int(tip_x - cabo_ex),
                                  sz - int(cabo_ey - mid_y - sz) + int(tip_y - cabo_ey))
                            pygame.draw.line(gs, (*cor, glow_a),
                                             (max(0,min(sz*2-1,ls[0])), max(0,min(sz*2-1,ls[1]))),
                                             (max(0,min(sz*2-1,le[0])), max(0,min(sz*2-1,le[1]))),
                                             max(4, lw+2))
                            self.tela.blit(gs, (mid_x, mid_y))
                        except Exception: pass  # QC-01
                        # Ponta brilhante
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip_x), int(tip_y)), max(2, lw-1))

        
        # === CORRENTE - MANGUAL v3.0 (Heavy Flail com Física de Elos) ===
        elif tipo == "Corrente":
            estilo_arma = getattr(arma, 'estilo', '')

            if estilo_arma == "Mangual":
                # ── MANGUAL v3.0: Cabo pesado + Elos de ferro fundido + Bola espigada ──
                cabo_tam      = raio_char * 0.70
                corrente_comp = raio_char * 1.55 * anim_scale
                ponta_tam = max(6, int(raio_char * 0.20 * anim_scale))
                num_elos = 6
                pulso = 0.5 + 0.5 * math.sin(tempo / 200)

                # ── Cabo de madeira grossa ──
                cabo_ex = cx + math.cos(rad) * cabo_tam
                cabo_ey = cy + math.sin(rad) * cabo_tam
                # Sombra do cabo
                pygame.draw.line(self.tela, (30, 20, 10),
                                 (int(cx)+2, int(cy)+2), (int(cabo_ex)+2, int(cabo_ey)+2), max(6, larg_base + 4))
                # Madeira do cabo
                pygame.draw.line(self.tela, (90, 55, 25),
                                 (int(cx), int(cy)), (int(cabo_ex), int(cabo_ey)), max(6, larg_base + 4))
                pygame.draw.line(self.tela, (130, 85, 40),
                                 (int(cx), int(cy)), (int(cabo_ex), int(cabo_ey)), max(3, larg_base))
                # Faixas de couro no cabo
                for fi in range(1, 5):
                    ft = fi / 5
                    fx = int(cx + (cabo_ex - cx) * ft)
                    fy = int(cy + (cabo_ey - cy) * ft)
                    fperp_x = math.cos(rad + math.pi/2) * (larg_base + 2)
                    fperp_y = math.sin(rad + math.pi/2) * (larg_base + 2)
                    pygame.draw.line(self.tela, (55, 30, 10),
                                     (int(fx - fperp_x), int(fy - fperp_y)),
                                     (int(fx + fperp_x), int(fy + fperp_y)), 2)

                # ── Argola de conexão ──
                anel_r = max(4, larg_base + 1)
                pygame.draw.circle(self.tela, (80, 80, 90), (int(cabo_ex), int(cabo_ey)), anel_r + 2)
                pygame.draw.circle(self.tela, (160, 165, 175), (int(cabo_ex), int(cabo_ey)), anel_r, 3)
                pygame.draw.circle(self.tela, (200, 205, 215), (int(cabo_ex), int(cabo_ey)), max(2, anel_r - 2), 1)

                # ── Corrente com elos fundidos (pendular arc) ──
                chain_pts = []
                sag = corrente_comp * 0.08 * (1 + 0.08 * math.sin(tempo / 200))  # Sag gravitacional (reduzido v3.1)
                for ei in range(num_elos + 1):
                    t = ei / num_elos
                    # Catenary approximation: arco para baixo
                    base_px = cabo_ex + math.cos(rad) * corrente_comp * t
                    base_py = cabo_ey + math.sin(rad) * corrente_comp * t
                    # Curvatura gravitacional + ondulação de momentum
                    gravity_y = sag * math.sin(t * math.pi) * math.sin(rad + math.pi/2) * -1
                    wave = math.sin(t * math.pi * 2 + tempo / 200) * raio_char * 0.03 * (1 - t * 0.4)
                    wave_x = math.cos(rad + math.pi/2) * wave
                    wave_y = math.sin(rad + math.pi/2) * wave + gravity_y
                    chain_pts.append((base_px + wave_x, base_py + wave_y))

                # Sombra da corrente
                shadow_chain = [(int(p[0]+3), int(p[1]+3)) for p in chain_pts]
                if len(shadow_chain) > 1:
                    try: pygame.draw.lines(self.tela, (20, 20, 22), False, shadow_chain, max(4, larg_base + 2))
                    except Exception: pass  # QC-01

                # Elos individuais (alternando horizontal/vertical)
                elo_w = max(5, larg_base + 2)
                elo_h = max(3, larg_base - 1)
                for ei in range(len(chain_pts)):
                    ex, ey = chain_pts[ei]
                    elo_ang = rad + math.pi/2 if ei % 2 == 0 else rad
                    # Elo como elipse/retângulo rotacionado
                    elo_perp_x = math.cos(elo_ang) * elo_w
                    elo_perp_y = math.sin(elo_ang) * elo_w
                    elo_fwd_x = math.cos(elo_ang + math.pi/2) * elo_h
                    elo_fwd_y = math.sin(elo_ang + math.pi/2) * elo_h
                    elo_pts = [
                        (int(ex - elo_perp_x - elo_fwd_x), int(ey - elo_perp_y - elo_fwd_y)),
                        (int(ex + elo_perp_x - elo_fwd_x), int(ey + elo_perp_y - elo_fwd_y)),
                        (int(ex + elo_perp_x + elo_fwd_x), int(ey + elo_perp_y + elo_fwd_y)),
                        (int(ex - elo_perp_x + elo_fwd_x), int(ey - elo_perp_y + elo_fwd_y)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, (90, 92, 100), elo_pts)
                        pygame.draw.polygon(self.tela, (145, 148, 160), elo_pts, 1)
                    except Exception: pass  # QC-01

                # ── Bola espigada (iron flail head) ──
                if chain_pts:
                    end_x, end_y = chain_pts[-1]
                    ball_r = ponta_tam

                    # Glow de impacto (quando atacando)
                    if atacando:
                        glow_r = int(ball_r * 2.2)
                        try:
                            gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                            glow_a = int(120 * anim_scale)
                            pygame.draw.circle(gs, (*cor, min(255, glow_a)), (glow_r, glow_r), glow_r)
                            self.tela.blit(gs, (int(end_x) - glow_r, int(end_y) - glow_r))
                        except Exception: pass  # QC-01

                    # Sombra da bola
                    pygame.draw.circle(self.tela, (15, 15, 18), (int(end_x) + 3, int(end_y) + 3), ball_r + 1)

                    # Bola principal (esfera fundida)
                    pygame.draw.circle(self.tela, cor_escura, (int(end_x), int(end_y)), ball_r)
                    pygame.draw.circle(self.tela, cor, (int(end_x), int(end_y)), ball_r - 1)
                    # Highlight da esfera
                    hl_x = int(end_x - ball_r * 0.3)
                    hl_y = int(end_y - ball_r * 0.3)
                    pygame.draw.circle(self.tela, cor_clara, (hl_x, hl_y), max(2, ball_r // 3))

                    # Spikes (6 espinhos fundidos)
                    num_spikes = 6
                    spike_len = ball_r * 0.7
                    spike_base_w = max(2, ball_r // 4)
                    spike_rot = tempo / 80  # Lenta rotação visual
                    for si in range(num_spikes):
                        s_ang = spike_rot + (si * math.pi * 2 / num_spikes)
                        # Base do spike na superfície da bola
                        s_base_x = end_x + math.cos(s_ang) * (ball_r - 1)
                        s_base_y = end_y + math.sin(s_ang) * (ball_r - 1)
                        # Ponta do spike
                        s_tip_x = end_x + math.cos(s_ang) * (ball_r + spike_len)
                        s_tip_y = end_y + math.sin(s_ang) * (ball_r + spike_len)
                        # Spike como triângulo
                        perp_sx = math.cos(s_ang + math.pi/2) * spike_base_w
                        perp_sy = math.sin(s_ang + math.pi/2) * spike_base_w
                        spike_pts = [
                            (int(s_base_x - perp_sx), int(s_base_y - perp_sy)),
                            (int(s_base_x + perp_sx), int(s_base_y + perp_sy)),
                            (int(s_tip_x), int(s_tip_y)),
                        ]
                        try:
                            pygame.draw.polygon(self.tela, cor, spike_pts)
                            pygame.draw.polygon(self.tela, cor_clara, spike_pts, 1)
                        except Exception: pass  # QC-01

                    # Anel de reforço na bola
                    pygame.draw.circle(self.tela, (70, 72, 80), (int(end_x), int(end_y)), ball_r, 2)

                    # Glow de raridade
                    if raridade not in ['Comum']:
                        rar_alpha = int(100 + 80 * pulso)
                        try:
                            rs = pygame.Surface((ball_r * 4, ball_r * 4), pygame.SRCALPHA)
                            pygame.draw.circle(rs, (*cor_raridade, rar_alpha),
                                               (ball_r * 2, ball_r * 2), ball_r + 4)
                            self.tela.blit(rs, (int(end_x) - ball_r * 2, int(end_y) - ball_r * 2))
                        except Exception: pass  # QC-01

            else:
                # ── PER-STYLE RENDERERS: Kusarigama, Chicote, Corrente com Peso ──
                comp_total = raio_char * 2.10 * anim_scale
                cabo_len   = raio_char * 0.60
                ponta_tam  = max(6, int(raio_char * 0.25))
                pulso      = 0.5 + 0.5 * math.sin(tempo / 180)

                # ── KUSARIGAMA — foice small + corrente + peso ──────────────
                if estilo_arma == "Kusarigama":
                    # Cabo pequeno da foice
                    kama_cabo_x = cx + math.cos(rad) * cabo_len
                    kama_cabo_y = cy + math.sin(rad) * cabo_len
                    pygame.draw.line(self.tela, (30,18,8), (int(cx)+1,int(cy)+1), (int(kama_cabo_x)+1,int(kama_cabo_y)+1), max(3,larg_base)+1)
                    pygame.draw.line(self.tela, (90,55,25), (int(cx),int(cy)), (int(kama_cabo_x),int(kama_cabo_y)), max(3,larg_base))
                    # Lâmina da foice (arco rápido usando Bézier)
                    kama_len = ponta_tam * 2.5
                    curve_ang = rad - math.pi/2
                    ctrl_x = kama_cabo_x + math.cos(curve_ang) * kama_len * 0.5
                    ctrl_y = kama_cabo_y + math.sin(curve_ang) * kama_len * 0.5
                    hook_x = kama_cabo_x + math.cos(curve_ang) * kama_len
                    hook_y = kama_cabo_y + math.sin(curve_ang) * kama_len
                    prev = (int(kama_cabo_x), int(kama_cabo_y))
                    for seg in range(1, 9):
                        t = seg / 8
                        bx2 = (1-t)**2*kama_cabo_x + 2*(1-t)*t*ctrl_x + t**2*hook_x
                        by2 = (1-t)**2*kama_cabo_y + 2*(1-t)*t*ctrl_y + t**2*hook_y
                        pygame.draw.line(self.tela, cor, prev, (int(bx2),int(by2)), max(2,larg_base))
                        prev = (int(bx2),int(by2))
                    pygame.draw.circle(self.tela, cor_raridade, (int(hook_x),int(hook_y)), max(2,larg_base-1))
                    # Corrente ondulada saindo do cabo
                    chain_pts = []
                    for i in range(14):
                        t = i / 13
                        wave = math.sin(t * math.pi * 3 + tempo/120) * raio_char * 0.12
                        px2 = kama_cabo_x + math.cos(rad) * comp_total * t
                        py2 = kama_cabo_y + math.sin(rad) * comp_total * t + wave
                        chain_pts.append((int(px2),int(py2)))
                    if len(chain_pts) > 1:
                        try: pygame.draw.lines(self.tela, (80,82,90), False, chain_pts, max(2,larg_base-1))
                        except Exception: pass  # QC-01
                        for j in range(0,len(chain_pts)-1,2):
                            pygame.draw.circle(self.tela,(60,62,72),chain_pts[j],max(2,larg_base//2))
                    # Peso (bola pequena no final)
                    if chain_pts:
                        ex,ey = chain_pts[-1]
                        pygame.draw.circle(self.tela, cor_escura, (ex,ey), ponta_tam+1)
                        pygame.draw.circle(self.tela, cor, (ex,ey), ponta_tam-1)
                        pygame.draw.circle(self.tela, cor_clara, (ex-ponta_tam//3,ey-ponta_tam//3), max(1,ponta_tam//3))

                # ── CHICOTE — longo, sinuoso, afunilando ───────────────────
                elif estilo_arma == "Chicote":
                    # Cabo de couro
                    cabo_ex = cx + math.cos(rad) * cabo_len
                    cabo_ey = cy + math.sin(rad) * cabo_len
                    pygame.draw.line(self.tela, (20,10,4),  (int(cx)+1,int(cy)+1), (int(cabo_ex)+1,int(cabo_ey)+1), max(4,larg_base)+2)
                    pygame.draw.line(self.tela, (60,30,10), (int(cx),int(cy)), (int(cabo_ex),int(cabo_ey)), max(4,larg_base))
                    # Tira de couro com faixas
                    for fi in range(1,4):
                        ft = fi/4
                        fx = int(cx + (cabo_ex-cx)*ft)
                        fy = int(cy + (cabo_ey-cy)*ft)
                        perp_x2 = math.cos(rad+math.pi/2)*(larg_base+2)
                        perp_y2 = math.sin(rad+math.pi/2)*(larg_base+2)
                        pygame.draw.line(self.tela,(35,16,4),(int(fx-perp_x2),int(fy-perp_y2)),(int(fx+perp_x2),int(fy+perp_y2)),1)
                    # Chicote ondulado (20 segmentos, afunilando)
                    num_seg = 20
                    pts = []
                    for i in range(num_seg+1):
                        t = i / num_seg
                        amp = raio_char * 0.25 * (1 - t*0.75)
                        wave = math.sin(t*math.pi*3.5 + tempo/100) * amp
                        px2 = cabo_ex + math.cos(rad) * comp_total * t
                        py2 = cabo_ey + math.sin(rad) * comp_total * t
                        perp_x2 = math.cos(rad+math.pi/2)*wave
                        perp_y2 = math.sin(rad+math.pi/2)*wave
                        pts.append((int(px2+perp_x2), int(py2+perp_y2)))
                    for j in range(len(pts)-1):
                        thick = max(1, int(larg_base * (1 - j/num_seg) + 0.5))
                        alpha_t = 80 + int(80 * (1 - j/num_seg))
                        try: pygame.draw.line(self.tela, cor, pts[j], pts[j+1], thick)
                        except Exception: pass  # QC-01
                    # Nó da ponta
                    if pts:
                        pygame.draw.circle(self.tela, cor_raridade, pts[-1], max(2,larg_base-1))

                # ── CORRENTE COM PESO — elos quadrados + bloco metálico ────
                else:
                    # Argola de pulso
                    pygame.draw.circle(self.tela, (80,82,90), (int(cx),int(cy)), larg_base+2, 2)
                    # Elos robustos (retângulos grandes)
                    num_elos = 8
                    pts = []
                    for i in range(num_elos+1):
                        t = i / num_elos
                        wave = math.sin(t*math.pi*2+tempo/200)*raio_char*0.1
                        px2 = cx + math.cos(rad)*comp_total*t
                        py2 = cy + math.sin(rad)*comp_total*t + wave
                        pts.append((int(px2),int(py2)))
                    for j in range(len(pts)-1):
                        pygame.draw.line(self.tela,(30,30,38),pts[j],pts[j+1],larg_base+3)
                        pygame.draw.line(self.tela,(90,92,105),pts[j],pts[j+1],larg_base)
                        if j%2==0:
                            perp_x2 = math.cos(rad+math.pi/2)*(larg_base+3)
                            perp_y2 = math.sin(rad+math.pi/2)*(larg_base+3)
                            mx=(pts[j][0]+pts[j+1][0])//2; my=(pts[j][1]+pts[j+1][1])//2
                            pygame.draw.line(self.tela,(55,56,65),(int(mx-perp_x2),int(my-perp_y2)),(int(mx+perp_x2),int(my+perp_y2)),2)
                    # Peso — bloco metálico pesado
                    if pts:
                        ex,ey = pts[-1]
                        hw = ponta_tam+2; hh = int(ponta_tam*1.4)
                        pygame.draw.rect(self.tela,(20,22,28),(ex-hw,ey-hh,hw*2,hh*2))
                        pygame.draw.rect(self.tela, cor, (ex-hw+1,ey-hh+1,hw*2-2,hh*2-2), 2)
                        pygame.draw.line(self.tela, cor_clara, (ex-hw+2,ey-hh+2),(ex-hw//2,ey-hh//2), 2)
                        if raridade not in ['Comum']:
                            pygame.draw.rect(self.tela,cor_raridade,(ex-hw,ey-hh,hw*2,hh*2),2)

        
        # === ARREMESSO (Machado, Faca Rápida, Chakram, Bumerangue) ===
        elif tipo == "Arremesso":
            estilo_arma = getattr(arma, 'estilo', '')
            tam_proj = max(8, int(raio_char * 0.35))
            qtd = min(5, int(getattr(arma, 'quantidade', 3)))
            pulso = 0.5 + 0.5 * math.sin(tempo / 180)

            for i in range(qtd):
                offset_ang = (i - (qtd-1)/2) * 20
                r_proj = rad + math.radians(offset_ang)
                dist = raio_char * 1.15 + tam_proj * 0.6
                px = cx + math.cos(r_proj) * dist
                py = cy + math.sin(r_proj) * dist
                rot = tempo / 90 + i * (math.pi * 2 / max(1, qtd))

                # ── MACHADO (Não Retorna) ─────────────────────────────────
                if "Machado" in estilo_arma:
                    # Cabo giratório
                    cabo_ax = px + math.cos(rot) * tam_proj * 0.5
                    cabo_ay = py + math.sin(rot) * tam_proj * 0.5
                    pygame.draw.line(self.tela, (60,35,12), (int(px), int(py)), (int(cabo_ax), int(cabo_ay)), max(2,larg_base-1))
                    # Cabeça assimétrica
                    perp_ax = math.cos(rot + math.pi/2)
                    perp_ay = math.sin(rot + math.pi/2)
                    ax_pts = [
                        (int(cabo_ax - perp_ax*tam_proj*0.9), int(cabo_ay - perp_ay*tam_proj*0.9)),
                        (int(cabo_ax + perp_ax*tam_proj*0.3), int(cabo_ay + perp_ay*tam_proj*0.3)),
                        (int(cabo_ax + math.cos(rot)*tam_proj*0.8 + perp_ax*tam_proj*0.25),
                         int(cabo_ay + math.sin(rot)*tam_proj*0.8 + perp_ay*tam_proj*0.25)),
                        (int(cabo_ax + math.cos(rot)*tam_proj*0.9), int(cabo_ay + math.sin(rot)*tam_proj*0.9)),
                        (int(cabo_ax + math.cos(rot)*tam_proj*0.8 - perp_ax*tam_proj*0.9),
                         int(cabo_ay + math.sin(rot)*tam_proj*0.8 - perp_ay*tam_proj*0.9)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, ax_pts)
                        pygame.draw.polygon(self.tela, cor, ax_pts, 1)
                    except Exception: pass  # QC-01
                    pygame.draw.circle(self.tela, cor_raridade, (int(cabo_ax+math.cos(rot)*tam_proj*0.9),int(cabo_ay+math.sin(rot)*tam_proj*0.9)), max(2,larg_base-2))

                # ── CHAKRAM (Retorna) — anel com fio ─────────────────────
                elif "Chakram" in estilo_arma:
                    r2 = max(7, tam_proj - 1)
                    # Anel com espessura
                    pygame.draw.circle(self.tela, cor_escura, (int(px), int(py)), r2+1)
                    pygame.draw.circle(self.tela, cor, (int(px), int(py)), r2, max(3,larg_base-1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(px), int(py)), r2, 1)
                    # Raios internos girando
                    for rj in range(3):
                        ra = rot + rj * math.pi / 3 * 2
                        pygame.draw.line(self.tela, cor_clara,
                                         (int(px + math.cos(ra)*r2*0.5), int(py + math.sin(ra)*r2*0.5)),
                                         (int(px - math.cos(ra)*r2*0.5), int(py - math.sin(ra)*r2*0.5)), 1)
                    pygame.draw.circle(self.tela, cor_raridade, (int(px),int(py)), max(2,r2//3))
                    # Glow de ataque
                    if atacando:
                        try:
                            gs = pygame.Surface((r2*4, r2*4), pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor, int(80*pulso)), (r2*2,r2*2), r2*2)
                            self.tela.blit(gs, (int(px)-r2*2, int(py)-r2*2))
                        except Exception: pass  # QC-01

                # ── BUMERANGUE ─────────────────────────────────────────────
                elif "Bumerangue" in estilo_arma:
                    t2 = tam_proj
                    bum_pts = [
                        (int(px + math.cos(rot)*t2*1.1),         int(py + math.sin(rot)*t2*1.1)),
                        (int(px + math.cos(rot+2.3)*t2*0.5),     int(py + math.sin(rot+2.3)*t2*0.5)),
                        (int(px),                                  int(py)),
                        (int(px + math.cos(rot-2.3)*t2*0.5),     int(py + math.sin(rot-2.3)*t2*0.5)),
                        (int(px + math.cos(rot+math.pi)*t2*0.9), int(py + math.sin(rot+math.pi)*t2*0.9)),
                        (int(px + math.cos(rot+math.pi+0.5)*t2*0.4), int(py + math.sin(rot+math.pi+0.5)*t2*0.4)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, bum_pts)
                        pygame.draw.polygon(self.tela, cor, bum_pts, 1)
                    except Exception: pass  # QC-01
                    pygame.draw.circle(self.tela, cor_raridade, (int(px), int(py)), max(2,larg_base-2))

                # ── FACA (Rápida) e fallback ─────────────────────────────
                else:
                    # Throwing knife — estreita e rápida
                    blade = tam_proj * 1.2
                    perp_f = math.cos(rot + math.pi/2) * max(2, larg_base//2)
                    perp_fy = math.sin(rot + math.pi/2) * max(2, larg_base//2)
                    tip_fx = px + math.cos(rot) * blade
                    tip_fy = py + math.sin(rot) * blade
                    faca_pts = [
                        (int(px - perp_f), int(py - perp_fy)),
                        (int(px + perp_f), int(py + perp_fy)),
                        (int(tip_fx + perp_f*0.3), int(tip_fy + perp_fy*0.3)),
                        (int(tip_fx), int(tip_fy)),
                        (int(tip_fx - perp_f*0.3), int(tip_fy - perp_fy*0.3)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, faca_pts)
                        pygame.draw.polygon(self.tela, cor, faca_pts, 1)
                    except Exception: pass  # QC-01
                    pygame.draw.line(self.tela, cor_clara, (int(px),int(py)), (int(tip_fx),int(tip_fy)), 1)
                    pygame.draw.circle(self.tela, cor_raridade, (int(tip_fx),int(tip_fy)), max(2,larg_base-2))

        # === ARCO (Arco Curto, Arco Longo, Besta, Besta de Repetição) ===
        elif tipo == "Arco":
            estilo_arma = getattr(arma, 'estilo', '')
            tam_arco   = raio_char * 1.30
            tam_flecha = raio_char * 1.20 * anim_scale
            pulso = 0.5 + 0.5 * math.sin(tempo / 200)

            # ── BESTA / BESTA DE REPETIÇÃO ────────────────────────────────
            if "Besta" in estilo_arma:
                # Coronha (stock) — paralela ao rad
                stock_len = tam_arco * 0.6
                stock_ex = cx + math.cos(rad) * stock_len
                stock_ey = cy + math.sin(rad) * stock_len
                perp_x = math.cos(rad + math.pi/2)
                perp_y = math.sin(rad + math.pi/2)
                # Madeira da coronha
                pygame.draw.line(self.tela, (30,18,8), (int(cx)+1,int(cy)+1),(int(stock_ex)+1,int(stock_ey)+1), larg_base+3)
                pygame.draw.line(self.tela, (90,55,25),(int(cx),int(cy)),(int(stock_ex),int(stock_ey)),larg_base+1)
                pygame.draw.line(self.tela, (130,85,40),(int(cx),int(cy)),(int(stock_ex),int(stock_ey)),max(1,larg_base-1))
                # Limbo horizontal (os "braços")
                limbo_len = tam_arco * 0.45
                mid_x = cx + math.cos(rad) * stock_len * 0.75
                mid_y = cy + math.sin(rad) * stock_len * 0.75
                limbo_p1 = (int(mid_x + perp_x*limbo_len), int(mid_y + perp_y*limbo_len))
                limbo_p2 = (int(mid_x - perp_x*limbo_len), int(mid_y - perp_y*limbo_len))
                pygame.draw.line(self.tela, (20,18,20), (int(limbo_p1[0])+1,int(limbo_p1[1])+1),(int(limbo_p2[0])+1,int(limbo_p2[1])+1), max(3,larg_base)+1)
                pygame.draw.line(self.tela, cor, limbo_p1, limbo_p2, max(3,larg_base))
                pygame.draw.line(self.tela, cor_clara, limbo_p1, limbo_p2, 1)
                # Corda (de ponta a ponta do limbo, passando pelo trilho)
                trilho_x = cx + math.cos(rad) * stock_len * 0.95
                trilho_y = cy + math.sin(rad) * stock_len * 0.95
                pygame.draw.line(self.tela, (200,185,140), limbo_p1, (int(trilho_x),int(trilho_y)), 2)
                pygame.draw.line(self.tela, (200,185,140), limbo_p2, (int(trilho_x),int(trilho_y)), 2)
                # Virote (bolto) no trilho
                pygame.draw.line(self.tela, (139,90,43), (int(trilho_x),int(trilho_y)),(int(trilho_x+math.cos(rad)*tam_flecha*0.6),int(trilho_y+math.sin(rad)*tam_flecha*0.6)), max(2,larg_base//2))
                tip_bx = int(trilho_x + math.cos(rad)*tam_flecha*0.6)
                tip_by = int(trilho_y + math.sin(rad)*tam_flecha*0.6)
                pts_tip = [(tip_bx,tip_by),
                           (int(tip_bx-math.cos(rad)*8+perp_x*4),int(tip_by-math.sin(rad)*8+perp_y*4)),
                           (int(tip_bx-math.cos(rad)*8-perp_x*4),int(tip_by-math.sin(rad)*8-perp_y*4))]
                try: pygame.draw.polygon(self.tela, cor_raridade, pts_tip)
                except Exception: pass  # QC-01
                # Pente de repetição (caixinha em cima do trilho)
                if "Repetição" in estilo_arma:
                    px2 = int(mid_x + math.cos(rad)*stock_len*0.05)
                    py2 = int(mid_y + math.sin(rad)*stock_len*0.05)
                    pygame.draw.rect(self.tela, (55,30,10), (px2-6, py2-18, 12, 16))
                    pygame.draw.rect(self.tela, cor_raridade, (px2-6, py2-18, 12, 16), 1)
                # Glow de raridade
                if raridade not in ['Comum','Incomum']:
                    pygame.draw.circle(self.tela, cor_raridade, (tip_bx,tip_by), max(3,larg_base))

            # ── ARCO LONGO ────────────────────────────────────────────────
            elif "Longo" in estilo_arma:
                arco_pts = []
                span = tam_arco * 0.9
                for i in range(15):
                    ang = rad + math.radians(-60 + i * (120/14))
                    curva = math.sin((i/14)*math.pi) * span * 0.12
                    r2 = span*0.55 + curva
                    arco_pts.append((int(cx+math.cos(ang)*r2), int(cy+math.sin(ang)*r2)))
                if len(arco_pts) > 1:
                    pygame.draw.lines(self.tela, cor_escura, False, [(p[0]+1,p[1]+1) for p in arco_pts], larg_base+2)
                    pygame.draw.lines(self.tela, cor, False, arco_pts, larg_base+1)
                    pygame.draw.lines(self.tela, cor_clara, False, arco_pts, 1)
                    pygame.draw.line(self.tela, (200,185,140), arco_pts[0], arco_pts[-1], 2)
                # Flecha longa
                flecha_end_x = cx + math.cos(rad)*tam_flecha
                flecha_end_y = cy + math.sin(rad)*tam_flecha
                pygame.draw.line(self.tela, (100,65,25),(int(cx),int(cy)),(int(flecha_end_x),int(flecha_end_y)),max(2,larg_base//2))
                plen = tam_flecha*0.14; perp_f = math.pi/2
                tip_pts = [(int(flecha_end_x),int(flecha_end_y)),
                           (int(flecha_end_x-math.cos(rad)*plen+math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen+math.sin(rad+perp_f)*plen*0.4)),
                           (int(flecha_end_x-math.cos(rad)*plen-math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen-math.sin(rad+perp_f)*plen*0.4))]
                try: pygame.draw.polygon(self.tela, cor_raridade, tip_pts)
                except Exception: pass  # QC-01
                # Penas
                for poff in [-1,1]:
                    pex = cx+math.cos(rad)*tam_flecha*0.12
                    pey = cy+math.sin(rad)*tam_flecha*0.12
                    pygame.draw.line(self.tela,(200,50,50),(int(pex),int(pey)),(int(pex+math.cos(rad+poff*0.6)*tam_flecha*0.12),int(pey+math.sin(rad+poff*0.6)*tam_flecha*0.12)),2)

            # ── ARCO CURTO (default) ──────────────────────────────────────
            else:
                arco_pts = []
                for i in range(13):
                    ang = rad + math.radians(-50 + i*(100/12))
                    curva = math.sin((i/12)*math.pi) * tam_arco * 0.15
                    r2 = tam_arco*0.5 + curva
                    arco_pts.append((int(cx+math.cos(ang)*r2), int(cy+math.sin(ang)*r2)))
                if len(arco_pts) > 1:
                    pygame.draw.lines(self.tela, cor, False, arco_pts, max(4,larg_base))
                    pygame.draw.lines(self.tela, cor_escura, False, arco_pts, 1)
                    pygame.draw.line(self.tela, (200,180,140), arco_pts[0], arco_pts[-1], 2)
                flecha_end_x = cx+math.cos(rad)*tam_flecha
                flecha_end_y = cy+math.sin(rad)*tam_flecha
                pygame.draw.line(self.tela,(139,90,43),(int(cx),int(cy)),(int(flecha_end_x),int(flecha_end_y)),max(2,larg_base//2))
                plen = tam_flecha*0.15; perp_f = math.pi/2
                tip_pts = [(int(flecha_end_x),int(flecha_end_y)),
                           (int(flecha_end_x-math.cos(rad)*plen+math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen+math.sin(rad+perp_f)*plen*0.4)),
                           (int(flecha_end_x-math.cos(rad)*plen-math.cos(rad+perp_f)*plen*0.4),int(flecha_end_y-math.sin(rad)*plen-math.sin(rad+perp_f)*plen*0.4))]
                try: pygame.draw.polygon(self.tela, cor_raridade, tip_pts)
                except Exception: pass  # QC-01
                for poff in [-1,1]:
                    pex = cx+math.cos(rad)*tam_flecha*0.15
                    pey = cy+math.sin(rad)*tam_flecha*0.15
                    pygame.draw.line(self.tela,(200,50,50),(int(pex),int(pey)),(int(pex+math.cos(rad+poff*0.5)*tam_flecha*0.1),int(pey+math.sin(rad+poff*0.5)*tam_flecha*0.1)),2)

        # === ORBITAL (Escudo, Drone, Orbes, Lâminas Orbitais) ===
        elif tipo == "Orbital":
            estilo_arma = getattr(arma, 'estilo', '')
            dist_orbit = raio_char * 1.6
            qtd  = max(1, min(5, int(getattr(arma, 'quantidade_orbitais', 2))))
            tam_orbe = max(8, int(raio_char * 0.32))
            rot_speed = tempo / 800
            pulso = 0.5 + 0.5 * math.sin(tempo / 200)

            for i in range(qtd):
                ang = rot_speed + (2 * math.pi / qtd) * i
                ox = cx + math.cos(ang) * dist_orbit
                oy = cy + math.sin(ang) * dist_orbit

                # Linha conectora sutil
                pygame.draw.line(self.tela, (50,50,70), (int(cx),int(cy)), (int(ox),int(oy)), 1)

                # ── ESCUDO ────────────────────────────────────────────────
                if "Escudo" in estilo_arma or "Defensivo" in estilo_arma:
                    arc_r = tam_orbe * 1.6
                    # Arco sólido como escudo curvo
                    start_ang = math.degrees(ang) + 60
                    try:
                        pygame.draw.arc(self.tela, cor_escura,
                                        (int(ox-arc_r), int(oy-arc_r), int(arc_r*2), int(arc_r*2)),
                                        math.radians(start_ang), math.radians(start_ang+120), tam_orbe//2+2)
                        pygame.draw.arc(self.tela, cor,
                                        (int(ox-arc_r), int(oy-arc_r), int(arc_r*2), int(arc_r*2)),
                                        math.radians(start_ang), math.radians(start_ang+120), tam_orbe//2)
                        pygame.draw.arc(self.tela, cor_clara,
                                        (int(ox-arc_r+2), int(oy-arc_r+2), int(arc_r*2-4), int(arc_r*2-4)),
                                        math.radians(start_ang+10), math.radians(start_ang+50), 1)
                    except Exception: pass  # QC-01
                    if raridade not in ['Comum']:
                        try:
                            gs = pygame.Surface((tam_orbe*4, tam_orbe*4), pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor_raridade, int(60*pulso)), (tam_orbe*2,tam_orbe*2), tam_orbe*2)
                            self.tela.blit(gs, (int(ox)-tam_orbe*2, int(oy)-tam_orbe*2))
                        except Exception: pass  # QC-01

                # ── DRONE ─────────────────────────────────────────────────
                elif "Drone" in estilo_arma or "Ofensivo" in estilo_arma:
                    # Hexágono metálico
                    hex_pts = []
                    for j in range(6):
                        ha = ang*30 + j*math.pi/3
                        hex_pts.append((int(ox+math.cos(ha)*tam_orbe), int(oy+math.sin(ha)*tam_orbe)))
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, hex_pts)
                        pygame.draw.polygon(self.tela, cor, hex_pts, 2)
                    except Exception: pass  # QC-01
                    pygame.draw.circle(self.tela, cor_raridade, (int(ox),int(oy)), max(3,tam_orbe//3))
                    # Propulsor
                    thrust_x = int(ox + math.cos(ang+math.pi)*tam_orbe*1.4)
                    thrust_y = int(oy + math.sin(ang+math.pi)*tam_orbe*1.4)
                    pygame.draw.line(self.tela, (100,180,255), (int(ox),int(oy)), (thrust_x,thrust_y), max(2,larg_base-1))
                    try:
                        gs = pygame.Surface((8,8), pygame.SRCALPHA)
                        pygame.draw.circle(gs, (100,180,255,int(120*pulso)), (4,4), 4)
                        self.tela.blit(gs, (thrust_x-4, thrust_y-4))
                    except Exception: pass  # QC-01

                # ── LÂMINAS ORBITAIS ──────────────────────────────────────
                elif "Lâmina" in estilo_arma:
                    blade_len = tam_orbe * 1.5
                    ba = ang + tempo/600
                    perp_bx = math.cos(ba + math.pi/2)
                    perp_by = math.sin(ba + math.pi/2)
                    tip1x = ox + math.cos(ba)*blade_len; tip1y = oy + math.sin(ba)*blade_len
                    tip2x = ox - math.cos(ba)*blade_len; tip2y = oy - math.sin(ba)*blade_len
                    w = max(2, larg_base-2)
                    blade_pts = [
                        (int(tip1x),int(tip1y)),
                        (int(ox+perp_bx*w),int(oy+perp_by*w)),
                        (int(tip2x),int(tip2y)),
                        (int(ox-perp_bx*w),int(oy-perp_by*w)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, blade_pts)
                        pygame.draw.polygon(self.tela, cor, blade_pts, 1)
                    except Exception: pass  # QC-01
                    pygame.draw.line(self.tela, cor_clara, (int(tip1x),int(tip1y)), (int(tip2x),int(tip2y)), 1)
                    if raridade not in ['Comum']:
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip1x),int(tip1y)), max(2,larg_base-2))
                        pygame.draw.circle(self.tela, cor_raridade, (int(tip2x),int(tip2y)), max(2,larg_base-2))

                # ── ORBE MÁGICO (default) ─────────────────────────────────
                else:
                    for glow_r in range(3,0,-1):
                        alpha_cor = tuple(min(255, c+glow_r*18) for c in cor)
                        pygame.draw.circle(self.tela, alpha_cor, (int(ox),int(oy)), tam_orbe+glow_r)
                    pygame.draw.circle(self.tela, cor, (int(ox),int(oy)), tam_orbe)
                    pygame.draw.circle(self.tela, cor_clara, (int(ox),int(oy)), tam_orbe//2)
                    pygame.draw.circle(self.tela, cor_raridade, (int(ox),int(oy)), tam_orbe, 2)
                    # Highlight
                    pygame.draw.circle(self.tela, (255,255,255), (int(ox-tam_orbe//3),int(oy-tam_orbe//3)), max(2,tam_orbe//4))

        # === MÁGICA (Espadas Espectrais, Runas, Tentáculos, Cristais) ===
        elif tipo == "Mágica":
            estilo_arma = getattr(arma, 'estilo', '')
            qtd       = min(5, int(getattr(arma, 'quantidade', 3)))
            tam_base  = max(12, int(raio_char * 0.65))
            dist_base = raio_char * 1.4
            float_off = math.sin(tempo/250) * raio_char * 0.1
            rot_off   = tempo / 1500
            pulso     = 0.5 + 0.5 * math.sin(tempo/200)

            for i in range(qtd):
                offset_ang = (i-(qtd-1)/2)*22 + math.degrees(rot_off)
                r_m = rad + math.radians(offset_ang)
                dist = dist_base + float_off*(1 + i*0.2)
                px = cx + math.cos(r_m)*dist
                py = cy + math.sin(r_m)*dist

                # ── ESPADAS ESPECTRAIS ────────────────────────────────────
                if "Espada" in estilo_arma or "Espectral" in estilo_arma:
                    sword_ex = px + math.cos(r_m)*tam_base
                    sword_ey = py + math.sin(r_m)*tam_base
                    perp_mx = math.cos(r_m+math.pi/2)*max(2,larg_base//2)
                    perp_my = math.sin(r_m+math.pi/2)*max(2,larg_base//2)
                    blade_pts = [
                        (int(px-perp_mx),int(py-perp_my)),
                        (int(px+perp_mx),int(py+perp_my)),
                        (int(sword_ex+perp_mx*0.3),int(sword_ey+perp_my*0.3)),
                        (int(sword_ex),int(sword_ey)),
                        (int(sword_ex-perp_mx*0.3),int(sword_ey-perp_my*0.3)),
                    ]
                    try:
                        gs = pygame.Surface((int(tam_base*4), int(tam_base*4)), pygame.SRCALPHA)
                        local_pts = [(p[0]-int(px)+int(tam_base*2), p[1]-int(py)+int(tam_base*2)) for p in blade_pts]
                        pygame.draw.polygon(gs, (*cor, 160), local_pts)
                        self.tela.blit(gs, (int(px)-int(tam_base*2), int(py)-int(tam_base*2)))
                        pygame.draw.polygon(self.tela, cor, blade_pts, 1)
                    except Exception: pass  # QC-01
                    pygame.draw.line(self.tela, cor_clara, (int(px),int(py)), (int(sword_ex),int(sword_ey)), 1)
                    # Guarda
                    pygame.draw.line(self.tela, cor_raridade,
                                     (int(px-perp_mx*2.5),int(py-perp_my*2.5)),
                                     (int(px+perp_mx*2.5),int(py+perp_my*2.5)), max(2,larg_base-1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(sword_ex),int(sword_ey)), 3)

                # ── RUNAS FLUTUANTES ──────────────────────────────────────
                elif "Runa" in estilo_arma:
                    r2 = max(8, int(tam_base*0.65))
                    pygame.draw.circle(self.tela, cor_escura, (int(px),int(py)), r2+2)
                    pygame.draw.circle(self.tela, cor, (int(px),int(py)), r2, max(2,larg_base-1))
                    pygame.draw.circle(self.tela, cor_raridade, (int(px),int(py)), r2, 1)
                    # Cruz + diagonais rúnicas
                    ang_r = rot_off + i * math.pi / qtd
                    for ra in [ang_r, ang_r+math.pi/4, ang_r+math.pi/2, ang_r+3*math.pi/4]:
                        pygame.draw.line(self.tela, cor_clara,
                                         (int(px+math.cos(ra)*(r2-3)),int(py+math.sin(ra)*(r2-3))),
                                         (int(px-math.cos(ra)*(r2-3)),int(py-math.sin(ra)*(r2-3))), 1)
                    pygame.draw.circle(self.tela, cor_raridade, (int(px),int(py)), max(2,r2//3))
                    if raridade not in ['Comum']:
                        try:
                            gs = pygame.Surface((r2*4,r2*4), pygame.SRCALPHA)
                            pygame.draw.circle(gs, (*cor_raridade, int(80*pulso)), (r2*2,r2*2), r2*2)
                            self.tela.blit(gs, (int(px)-r2*2, int(py)-r2*2))
                        except Exception: pass  # QC-01

                # ── TENTÁCULOS SOMBRIOS ───────────────────────────────────
                elif "Tentáculo" in estilo_arma:
                    tent_len = tam_base * 2.0
                    t_pts = []
                    for s in range(9):
                        t = s / 8
                        wave = math.sin(t*math.pi*2.5 + tempo/100 + i) * tam_base*0.4*(1-t*0.3)
                        tx2 = px + math.cos(r_m)*tent_len*t + math.cos(r_m+math.pi/2)*wave
                        ty2 = py + math.sin(r_m)*tent_len*t + math.sin(r_m+math.pi/2)*wave
                        t_pts.append((int(tx2),int(ty2)))
                    if len(t_pts) > 1:
                        try: pygame.draw.lines(self.tela, cor, False, t_pts, max(2,larg_base-1))
                        except Exception: pass  # QC-01
                        try: pygame.draw.lines(self.tela, cor_clara, False, t_pts, 1)
                        except Exception: pass  # QC-01
                    # Ventosas
                    for si in range(1,4):
                        sv = t_pts[si*2] if si*2 < len(t_pts) else t_pts[-1]
                        pygame.draw.circle(self.tela, cor_raridade, sv, max(2,larg_base-2))

                # ── CRISTAIS ARCANOS ──────────────────────────────────────
                else:
                    r2 = max(7, int(tam_base*0.6))
                    crystal_pts = [
                        (int(px+math.cos(rot_off+i)*r2*1.4), int(py+math.sin(rot_off+i)*r2*1.4)),
                        (int(px+math.cos(rot_off+i+2.1)*r2), int(py+math.sin(rot_off+i+2.1)*r2)),
                        (int(px+math.cos(rot_off+i+2.5)*r2*0.6), int(py+math.sin(rot_off+i+2.5)*r2*0.6)),
                        (int(px+math.cos(rot_off+i+3.8)*r2), int(py+math.sin(rot_off+i+3.8)*r2)),
                        (int(px+math.cos(rot_off+i-2.1)*r2), int(py+math.sin(rot_off+i-2.1)*r2)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor_escura, crystal_pts)
                        pygame.draw.polygon(self.tela, cor, crystal_pts, 1)
                    except Exception: pass  # QC-01
                    pygame.draw.circle(self.tela, cor_clara, (int(px),int(py)), max(2,r2//3))
                    if raridade not in ['Comum']:
                        pygame.draw.circle(self.tela, cor_raridade, crystal_pts[0], 3)

        # === TRANSFORMÁVEL (Espada↔Lança, Compacta↔Estendida, Chicote↔Espada, Arco↔Lâminas) ===
        elif tipo == "Transformável":
            estilo_arma = getattr(arma, 'estilo', '')
            forma = getattr(arma, 'forma_atual', 1)
            larg = max(4, int(larg_base * 1.1))
            pulso = 0.5 + 0.5 * math.sin(tempo / 200)

            if forma == 1:
                cabo_len   = raio_char * 0.50
                lamina_len = raio_char * 1.20 * anim_scale
            else:
                cabo_len   = raio_char * 0.85
                lamina_len = raio_char * 1.55 * anim_scale

            cabo_end_x = cx + math.cos(rad)*cabo_len
            cabo_end_y = cy + math.sin(rad)*cabo_len
            lamina_end_x = cx + math.cos(rad)*(cabo_len+lamina_len)
            lamina_end_y = cy + math.sin(rad)*(cabo_len+lamina_len)
            perp_x = math.cos(rad+math.pi/2)
            perp_y = math.sin(rad+math.pi/2)

            # Mecanismo de transformação (engrenagem/pivot) — igual para todos
            mec_col = (int(120+80*pulso), int(100+60*pulso), int(90+50*pulso))
            pygame.draw.circle(self.tela, (40,40,50), (int(cabo_end_x),int(cabo_end_y)), larg+2)
            pygame.draw.circle(self.tela, mec_col, (int(cabo_end_x),int(cabo_end_y)), larg, 2)
            # Cabo com faixas
            pygame.draw.line(self.tela, (30,18,8), (int(cx)+1,int(cy)+1),(int(cabo_end_x)+1,int(cabo_end_y)+1), larg+2)
            pygame.draw.line(self.tela, (90,55,25), (int(cx),int(cy)),(int(cabo_end_x),int(cabo_end_y)), larg)

            # ── ESPADA ↔ LANÇA ────────────────────────────────────────────
            if "Lança" in estilo_arma and "Espada" in estilo_arma:
                if forma == 1:  # Espada
                    blade_pts = [
                        (int(cabo_end_x-perp_x*larg*0.7),int(cabo_end_y-perp_y*larg*0.7)),
                        (int(cabo_end_x+perp_x*larg*0.7),int(cabo_end_y+perp_y*larg*0.7)),
                        (int(lamina_end_x-perp_x*larg*0.3),int(lamina_end_y-perp_y*larg*0.3)),
                        (int(lamina_end_x),int(lamina_end_y)),
                        (int(lamina_end_x+perp_x*larg*0.3),int(lamina_end_y+perp_y*larg*0.3)),
                    ]
                    # Guarda
                    pygame.draw.line(self.tela, (160,165,175),
                                     (int(cabo_end_x-perp_x*(larg+4)),int(cabo_end_y-perp_y*(larg+4))),
                                     (int(cabo_end_x+perp_x*(larg+4)),int(cabo_end_y+perp_y*(larg+4))), max(2,larg-1))
                else:  # Lança
                    blade_pts = [
                        (int(cabo_end_x-perp_x*larg*0.5),int(cabo_end_y-perp_y*larg*0.5)),
                        (int(cabo_end_x+perp_x*larg*0.5),int(cabo_end_y+perp_y*larg*0.5)),
                        (int(lamina_end_x+perp_x),int(lamina_end_y+perp_y)),
                        (int(lamina_end_x),int(lamina_end_y)),
                        (int(lamina_end_x-perp_x),int(lamina_end_y-perp_y)),
                    ]
                try:
                    pygame.draw.polygon(self.tela, cor, blade_pts)
                    pygame.draw.polygon(self.tela, cor_escura, blade_pts, 1)
                except Exception: pass  # QC-01
                pygame.draw.line(self.tela, cor_clara, (int(cabo_end_x),int(cabo_end_y)),(int(lamina_end_x),int(lamina_end_y)), 1)

            # ── CHICOTE ↔ ESPADA ──────────────────────────────────────────
            elif "Chicote" in estilo_arma:
                if forma == 1:  # Espada
                    blade_pts = [
                        (int(cabo_end_x-perp_x*larg*0.7),int(cabo_end_y-perp_y*larg*0.7)),
                        (int(cabo_end_x+perp_x*larg*0.7),int(cabo_end_y+perp_y*larg*0.7)),
                        (int(lamina_end_x-perp_x*larg*0.3),int(lamina_end_y-perp_y*larg*0.3)),
                        (int(lamina_end_x),int(lamina_end_y)),
                        (int(lamina_end_x+perp_x*larg*0.3),int(lamina_end_y+perp_y*larg*0.3)),
                    ]
                    try:
                        pygame.draw.polygon(self.tela, cor, blade_pts)
                        pygame.draw.polygon(self.tela, cor_escura, blade_pts, 1)
                    except Exception: pass  # QC-01
                else:  # Chicote
                    num_seg = 14
                    wpts = []
                    for s in range(num_seg+1):
                        t = s/num_seg
                        amp = raio_char*0.2*(1-t*0.7)
                        wave = math.sin(t*math.pi*3+tempo/100)*amp
                        wx2 = cabo_end_x + math.cos(rad)*lamina_len*t
                        wy2 = cabo_end_y + math.sin(rad)*lamina_len*t + math.cos(rad+math.pi/2)*wave
                        wpts.append((int(wx2),int(wy2)))
                    for j in range(len(wpts)-1):
                        thick = max(1, int(larg*(1-j/num_seg)+0.5))
                        try: pygame.draw.line(self.tela, cor, wpts[j], wpts[j+1], thick)
                        except Exception: pass  # QC-01
                    if wpts: pygame.draw.circle(self.tela, cor_raridade, wpts[-1], max(2,larg-2))

            # ── ARCo ↔ LÂMINAS / COMPACTA ↔ ESTENDIDA (default) ─────────
            else:
                blade_pts = [
                    (int(cabo_end_x-perp_x*larg*0.6),int(cabo_end_y-perp_y*larg*0.6)),
                    (int(cabo_end_x+perp_x*larg*0.6),int(cabo_end_y+perp_y*larg*0.6)),
                    (int(lamina_end_x-perp_x*larg*0.3),int(lamina_end_y-perp_y*larg*0.3)),
                    (int(lamina_end_x),int(lamina_end_y)),
                    (int(lamina_end_x+perp_x*larg*0.3),int(lamina_end_y+perp_y*larg*0.3)),
                ]
                try:
                    pygame.draw.polygon(self.tela, cor, blade_pts)
                    pygame.draw.polygon(self.tela, cor_escura, blade_pts, 1)
                except Exception: pass  # QC-01
                pygame.draw.line(self.tela, cor_clara,(int(cabo_end_x),int(cabo_end_y)),(int(lamina_end_x),int(lamina_end_y)),1)

            # Glow de raridade comum
            if raridade not in ['Comum','Incomum']:
                pygame.draw.circle(self.tela, cor_raridade, (int(lamina_end_x),int(lamina_end_y)), max(4,larg//2))


        
        # === FALLBACK ===
        else:
            cabo_len   = raio_char * 0.55
            lamina_len = raio_char * 1.20 * anim_scale
            
            cabo_end_x = cx + math.cos(rad) * cabo_len
            cabo_end_y = cy + math.sin(rad) * cabo_len
            lamina_end_x = cx + math.cos(rad) * (cabo_len + lamina_len)
            lamina_end_y = cy + math.sin(rad) * (cabo_len + lamina_len)
            
            pygame.draw.line(self.tela, (80, 50, 30), (int(cx), int(cy)), (int(cabo_end_x), int(cabo_end_y)), larg_base)
            pygame.draw.line(self.tela, cor, (int(cabo_end_x), int(cabo_end_y)), (int(lamina_end_x), int(lamina_end_y)), larg_base)


    def desenhar_hitbox_debug(self):
        """Desenha visualização de debug das hitboxes"""
        debug_info = get_debug_visual()
        fonte = pygame.font.SysFont("Arial", 10)
        
        # Desenha hitboxes em tempo real para cada lutador
        for p in [self.p1, self.p2]:
            if p.morto:
                continue
            
            cor_debug = (0, 255, 0, 128) if p == self.p1 else (255, 255, 0, 128)
            
            # Calcula hitbox atual
            hitbox = sistema_hitbox.calcular_hitbox_arma(p)
            if not hitbox:
                continue
            
            # Posição na tela
            cx_screen, cy_screen = self.cam.converter(hitbox.centro[0], hitbox.centro[1])
            off_y = self.cam.converter_tam(p.z * PPM)
            cy_screen -= off_y
            
            # Surface transparente para desenho
            s = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            
            # Desenha raio de alcance
            alcance_screen = self.cam.converter_tam(hitbox.alcance)
            pygame.draw.circle(s, (*cor_debug[:3], 30), (cx_screen, cy_screen), alcance_screen, 2)
            
            # Se tem pontos (arma de lâmina ou corrente)
            if hitbox.pontos:
                # Corrente: desenha como arco
                if hitbox.tipo == "Corrente":
                    # Desenha os segmentos do arco
                    cor_arco = (255, 128, 0, 200) if hitbox.ativo else (100, 100, 100, 100)
                    pontos_screen = []
                    for ponto in hitbox.pontos:
                        ps = self.cam.converter(ponto[0], ponto[1])
                        pontos_screen.append((ps[0], ps[1] - off_y))
                    
                    # Desenha linhas conectando os pontos do arco
                    if len(pontos_screen) > 1:
                        for i in range(len(pontos_screen) - 1):
                            pygame.draw.line(s, cor_arco, pontos_screen[i], pontos_screen[i+1], 3)
                    
                    # Desenha círculo na posição real da bola (centro do arco, no ângulo da arma)
                    rad_bola = math.radians(hitbox.angulo)
                    bola_x = hitbox.centro[0] + math.cos(rad_bola) * hitbox.alcance
                    bola_y = hitbox.centro[1] + math.sin(rad_bola) * hitbox.alcance
                    bola_screen = self.cam.converter(bola_x, bola_y)
                    bola_screen = (bola_screen[0], bola_screen[1] - off_y)
                    pygame.draw.circle(s, (255, 50, 50, 255), bola_screen, 10, 3)  # Círculo vermelho na bola
                    
                    # Linha do centro até a bola
                    pygame.draw.line(s, (255, 128, 0, 100), (cx_screen, cy_screen), bola_screen, 1)
                    
                    # Desenha raio mínimo da corrente (onde ela NÃO acerta)
                    alcance_min = hitbox.alcance * 0.4
                    alcance_min_screen = self.cam.converter_tam(alcance_min)
                    pygame.draw.circle(s, (100, 100, 100, 50), (cx_screen, cy_screen), alcance_min_screen, 1)
                    
                    # Label
                    label = f"{p.dados.nome}: Corrente"
                    if hitbox.ativo:
                        label += f" [GIRANDO t={p.timer_animacao:.2f}]"
                    txt = fonte.render(label, True, BRANCO)
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
                
                # Armas Ranged: desenha linhas de trajetória
                elif hitbox.tipo in ["Arremesso", "Arco"]:
                    cor_traj = (0, 200, 255, 150) if hitbox.ativo else (100, 100, 100, 80)
                    
                    # Múltiplos projéteis ou linha única
                    if len(hitbox.pontos) > 2:
                        # Múltiplos pontos = múltiplos projéteis
                        for ponto in hitbox.pontos:
                            ps = self.cam.converter(ponto[0], ponto[1])
                            ps = (ps[0], ps[1] - off_y)
                            # Linha tracejada do centro até destino
                            pygame.draw.line(s, cor_traj, (cx_screen, cy_screen), ps, 1)
                            pygame.draw.circle(s, cor_traj, ps, 5)
                    else:
                        # Linha única
                        if len(hitbox.pontos) == 2:
                            p1_screen = self.cam.converter(hitbox.pontos[0][0], hitbox.pontos[0][1])
                            p2_screen = self.cam.converter(hitbox.pontos[1][0], hitbox.pontos[1][1])
                            p1_screen = (p1_screen[0], p1_screen[1] - off_y)
                            p2_screen = (p2_screen[0], p2_screen[1] - off_y)
                            pygame.draw.line(s, cor_traj, p1_screen, p2_screen, 2)
                            pygame.draw.circle(s, (255, 100, 100), p2_screen, 6)
                    
                    # Label
                    label = f"{p.dados.nome}: {hitbox.tipo} [RANGED]"
                    if hitbox.ativo:
                        label += " DISPARANDO!"
                    txt = fonte.render(label, True, (0, 200, 255))
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
                    
                else:
                    # Arma de lâmina normal
                    p1_screen = self.cam.converter(hitbox.pontos[0][0], hitbox.pontos[0][1])
                    p2_screen = self.cam.converter(hitbox.pontos[1][0], hitbox.pontos[1][1])
                    p1_screen = (p1_screen[0], p1_screen[1] - off_y)
                    p2_screen = (p2_screen[0], p2_screen[1] - off_y)
                    
                    # Linha da lâmina
                    cor_linha = (255, 0, 0, 200) if hitbox.ativo else (100, 100, 100, 100)
                    pygame.draw.line(s, cor_linha, p1_screen, p2_screen, 4)
                    
                    # Pontos nas extremidades
                    pygame.draw.circle(s, (255, 255, 0), p1_screen, 5)
                    pygame.draw.circle(s, (255, 0, 0), p2_screen, 5)
                    
                    # Label
                    label = f"{p.dados.nome}: {hitbox.tipo}"
                    if hitbox.ativo:
                        label += f" [ATACANDO t={p.timer_animacao:.2f}]"
                    txt = fonte.render(label, True, BRANCO)
                    s.blit(txt, (cx_screen - 50, cy_screen - alcance_screen - 20))
            
            # Arma de área
            else:
                # Desenha arco de ângulo
                rad = math.radians(hitbox.angulo)
                rad_min = rad - math.radians(hitbox.largura_angular / 2)
                rad_max = rad + math.radians(hitbox.largura_angular / 2)
                
                # Linha central
                fx = cx_screen + math.cos(rad) * alcance_screen
                fy = cy_screen + math.sin(rad) * alcance_screen
                pygame.draw.line(s, (*cor_debug[:3], 150), (cx_screen, cy_screen), (int(fx), int(fy)), 2)
                
                # Limites do arco
                fx_min = cx_screen + math.cos(rad_min) * alcance_screen
                fy_min = cy_screen + math.sin(rad_min) * alcance_screen
                fx_max = cx_screen + math.cos(rad_max) * alcance_screen
                fy_max = cy_screen + math.sin(rad_max) * alcance_screen
                pygame.draw.line(s, (*cor_debug[:3], 100), (cx_screen, cy_screen), (int(fx_min), int(fy_min)), 1)
                pygame.draw.line(s, (*cor_debug[:3], 100), (cx_screen, cy_screen), (int(fx_max), int(fy_max)), 1)
            
            self.tela.blit(s, (0, 0))
        
        # Desenha painel de debug no canto
        self.desenhar_painel_debug()

    
    def desenhar_painel_debug(self):
        """Desenha painel com info de debug"""
        x, y = self.screen_width - 300, 80
        w, h = 280, 250
        
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (255, 100, 100), (x, y, w, h), 2)
        
        fonte = pygame.font.SysFont("Arial", 10)
        fonte_bold = pygame.font.SysFont("Arial", 11, bold=True)
        
        self.tela.blit(fonte_bold.render("DEBUG HITBOX [H para toggle]", True, (255, 100, 100)), (x + 10, y + 5))
        
        # Distância entre lutadores
        dist = math.hypot(self.p2.pos[0] - self.p1.pos[0], self.p2.pos[1] - self.p1.pos[1])
        self.tela.blit(fonte_bold.render(f"Distância: {dist:.2f}m", True, (200, 200, 255)), (x + 10, y + 22))
        
        off = 40
        for p in [self.p1, self.p2]:
            cor = (100, 255, 100) if p == self.p1 else (255, 255, 100)
            self.tela.blit(fonte_bold.render(f"=== {p.dados.nome} ===", True, cor), (x + 10, y + off))
            off += 14
            
            arma = p.dados.arma_obj
            if arma:
                self.tela.blit(fonte.render(f"Arma: {arma.nome} ({arma.tipo})", True, BRANCO), (x + 10, y + off))
                off += 11
            
            # Status de ataque
            atk_cor = (0, 255, 0) if p.atacando else (150, 150, 150)
            self.tela.blit(fonte.render(f"Atacando: {p.atacando} Timer: {p.timer_animacao:.3f}", True, atk_cor), (x + 10, y + off))
            off += 11
            self.tela.blit(fonte.render(f"Alcance IA: {p.alcance_ideal:.2f}m CD: {p.cooldown_ataque:.2f}", True, BRANCO), (x + 10, y + off))
            off += 11
            acao_atual = p.brain.acao_atual if p.brain is not None else "MANUAL"
            self.tela.blit(fonte.render(f"Ação: {acao_atual}", True, BRANCO), (x + 10, y + off))
            off += 16


    def desenhar_barras(self, l, x, y, cor, vida_vis):
        # Ajusta largura das barras baseado no modo (menor em portrait)
        w = 200 if self.portrait_mode else 300
        h = 25 if self.portrait_mode else 30
        pygame.draw.rect(self.tela, (20,20,20), (x, y, w, h))
        pct_vis = max(0, vida_vis / l.vida_max); pygame.draw.rect(self.tela, BRANCO, (x, y, int(w * pct_vis), h))
        pct_real = max(0, l.vida / l.vida_max); pygame.draw.rect(self.tela, cor, (x, y, int(w * pct_real), h))
        pygame.draw.rect(self.tela, BRANCO, (x, y, w, h), 2)
        pct_mana = max(0, l.mana / l.mana_max)
        pygame.draw.rect(self.tela, (20, 20, 20), (x, y + h + 5, w, 10))
        pygame.draw.rect(self.tela, AZUL_MANA, (x, y + h + 5, int(w * pct_mana), 10))
        ft_size = 14 if self.portrait_mode else 16
        ft = pygame.font.SysFont("Arial", ft_size, bold=True)
        self.tela.blit(ft.render(f"{l.dados.nome}", True, BRANCO), (x+10, y+5))


    def desenhar_controles(self):
        x, y = 20, 90 
        w, h = 220, 210
        s = pygame.Surface((w, h), pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (x, y))
        pygame.draw.rect(self.tela, (100, 100, 100), (x, y, w, h), 1)
        fonte_tit = pygame.font.SysFont("Arial", 14, bold=True); fonte_txt = pygame.font.SysFont("Arial", 12)
        self.tela.blit(fonte_tit.render("COMANDOS", True, COR_TEXTO_TITULO), (x + 10, y + 10))
        comandos = [("WASD / Setas", "Mover Câmera"), ("Scroll", "Zoom"), ("1/2/3", "Modos Cam"), ("SPACE", "Pause"), ("T/F", "Speed"), ("TAB", "Dados"), ("G", "HUD"), ("H", "Debug Hitbox"), ("R", "Reset"), ("ESC", "Sair")]
        off_y = 35
        for t, a in comandos:
            self.tela.blit(fonte_txt.render(t, True, BRANCO), (x + 10, y + off_y))
            self.tela.blit(fonte_txt.render(a, True, COR_TEXTO_INFO), (x + 110, y + off_y))
            off_y += 16


    def desenhar_analise(self):
        s = pygame.Surface((300, self.screen_height)); s.fill(COR_UI_BG); self.tela.blit(s, (0,0))
        ft = pygame.font.SysFont("Consolas", 14)
        lines = [
            "--- ANÁLISE ---", f"FPS: {int(self.clock.get_fps())}", f"Cam: {self.cam.modo}", "",
            f"--- {self.p1.dados.nome} ---", f"HP: {int(self.p1.vida)}", f"Mana: {int(self.p1.mana)}", f"Estamina: {int(self.p1.estamina)}",
            f"Action: {self.p1.brain.acao_atual}", f"Skill: {self.p1.skill_arma_nome}", "",
            f"--- {self.p2.dados.nome} ---", f"HP: {int(self.p2.vida)}", f"Mana: {int(self.p2.mana)}", f"Estamina: {int(self.p2.estamina)}",
            f"Action: {self.p2.brain.acao_atual}", f"Skill: {self.p2.skill_arma_nome}"
        ]
        for i, l in enumerate(lines):
            c = COR_TEXTO_TITULO if "---" in l else COR_TEXTO_INFO
            self.tela.blit(ft.render(l, True, c), (20, 20 + i*20))


    def desenhar_pause(self):
        ft = pygame.font.SysFont("Impact", 60); txt = ft.render("PAUSE", True, BRANCO)
        self.tela.blit(txt, (self.screen_width//2 - txt.get_width()//2, self.screen_height//2 - 50))


    def desenhar_vitoria(self):
        s = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA); s.fill(COR_UI_BG); self.tela.blit(s, (0,0))
        ft = pygame.font.SysFont("Impact", 80); txt = ft.render(f"{self.vencedor} VENCEU!", True, COR_TEXTO_TITULO)
        self.tela.blit(txt, (self.screen_width//2 - txt.get_width()//2, self.screen_height//2 - 100))
        ft2 = pygame.font.SysFont("Arial", 24); msg = ft2.render("Pressione 'R' para Reiniciar ou 'ESC' para Sair", True, COR_TEXTO_INFO)
        self.tela.blit(msg, (self.screen_width//2 - msg.get_width()//2, self.screen_height//2 + 20))
