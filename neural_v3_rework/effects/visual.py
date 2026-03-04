"""
NEURAL FIGHTS - Efeitos Visuais (UI) v15.0 POLISHED
Texto flutuante e manchas (decals) com animações melhoradas
"""

import pygame
import math
from utils.config import PRETO


class FloatingText:
    """Texto flutuante para dano e notificações — v15.0 com scale + bounce"""
    def __init__(self, x, y, texto, cor, tamanho=20):
        self.x = x
        self.y = y
        self.texto = str(int(texto)) if isinstance(texto, (int, float)) else texto
        self.cor = cor
        self.tamanho_base = tamanho
        self.tamanho = tamanho
        self._fontes = {}  # Cache de fontes por tamanho
        self.vel_y = -1.5  # Sobe mais rápido
        self.vel_x = 0      # Drift lateral sutil
        self.vida = 1.2
        self.max_vida = 1.2
        self.alpha = 255
        self.scale = 0.3    # Começa pequeno (pop-in)
        
        # Texto grande (dano alto, CRITICAL, FATAL) = efeito maior
        self._is_special = tamanho >= 28 or any(w in str(texto) for w in ["!", "FATAL", "CRÍTICO", "CLASH", "PARRY"])
        if self._is_special:
            self.vel_y = -2.0

    def _get_fonte(self, size):
        """Cache de fontes para evitar criar toda frame"""
        size = max(8, int(size))
        if size not in self._fontes:
            self._fontes[size] = pygame.font.SysFont("Impact", size)
        return self._fontes[size]

    def update(self, dt):
        self.y += self.vel_y * dt * 60
        self.x += self.vel_x * dt * 60
        self.vel_y += 0.03  # Gravidade menor (flutua mais)
        self.vida -= dt
        
        # Scale animation: pop-in rápido, depois estabiliza
        prog = 1.0 - (self.vida / self.max_vida)
        if prog < 0.1:
            # Pop-in: 0.3 -> 1.15 (overshoot)
            t = prog / 0.1
            self.scale = 0.3 + 0.85 * t
            if self._is_special:
                self.scale = 0.3 + 1.0 * t  # Textos especiais ficam maiores
        elif prog < 0.2:
            # Settle: 1.15 -> 1.0
            t = (prog - 0.1) / 0.1
            self.scale = 1.15 - 0.15 * t
            if self._is_special:
                self.scale = 1.3 - 0.3 * t
        else:
            self.scale = 1.0
        
        # Fade out nos últimos 40%
        if self.vida < self.max_vida * 0.4:
            self.alpha = int(255 * (self.vida / (self.max_vida * 0.4)))
        
        # Shrink no final
        if self.vida < self.max_vida * 0.2:
            shrink = self.vida / (self.max_vida * 0.2)
            self.scale *= (0.5 + 0.5 * shrink)

    def draw(self, tela, cam):
        if self.vida <= 0 or self.alpha < 5:
            return
        sx, sy = cam.converter(self.x, self.y)
        
        # Tamanho com escala
        tam_atual = max(8, int(self.tamanho_base * self.scale))
        fonte = self._get_fonte(tam_atual)
        
        # Renderiza texto
        surf = fonte.render(self.texto, True, self.cor)
        surf.set_alpha(max(0, min(255, self.alpha)))
        
        # Sombra (offset 2px, mais escura)
        sombra = fonte.render(self.texto, True, PRETO)
        sombra.set_alpha(max(0, min(255, int(self.alpha * 0.6))))
        
        # Glow para textos especiais
        if self._is_special and self.alpha > 100:
            glow_fonte = self._get_fonte(tam_atual + 2)
            glow = glow_fonte.render(self.texto, True, self.cor)
            glow_alpha = max(0, min(255, int(self.alpha * 0.3)))
            glow.set_alpha(glow_alpha)
            gw = glow.get_width()
            gh = glow.get_height()
            tela.blit(glow, (sx - gw // 2, sy - gh // 2))
        
        # Desenha sombra + texto
        tw = surf.get_width()
        th = surf.get_height()
        tela.blit(sombra, (sx - tw // 2 + 2, sy - th // 2 + 2))
        tela.blit(surf, (sx - tw // 2, sy - th // 2))


class Decal:
    """Manchas no chão (sangue, queimaduras, etc)"""
    def __init__(self, x, y, raio, cor):
        self.x = x
        self.y = y
        self.raio = raio
        self.cor = cor
        self.alpha = 200

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        r = cam.converter_tam(self.raio)
        if r < 1:
            return
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.cor, self.alpha), (r, r), r)
        tela.blit(s, (sx-r, sy-r))
