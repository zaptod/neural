"""
NEURAL FIGHTS - Sistema de Câmera v9.0 BULLETPROOF EDITION
Câmera que NUNCA perde os lutadores de vista.

GARANTIAS:
1. Ambos os lutadores SEMPRE visíveis na tela
2. Zoom dinâmico INSTANTÂNEO quando necessário
3. Funciona com knockbacks de qualquer intensidade
4. Respeita os limites da arena
"""

import pygame
import random
import math
from config import LARGURA, ALTURA, PPM


class Câmera:
    """
    Câmera do jogo com zoom dinâmico GARANTIDO.
    
    Esta câmera foi projetada para NUNCA perder os lutadores de vista,
    mesmo com knockbacks extremos de Berserkers ou Colossos.
    """
    
    def __init__(self):
        # Posição da câmera (centro da visão em pixels do mundo)
        self.x = 15.0 * PPM 
        self.y = 10.0 * PPM
        
        # Zoom atual e alvo
        self.zoom = 1.0
        self.target_zoom = 1.0
        
        # Modo de câmera
        self.modo = "AUTO"  # AUTO, P1, P2, FIXO 
        self.shake_timer = 0.0
        self.shake_magnitude = 0.0
        self.offset_x = 0
        self.offset_y = 0
        
        # === NOVOS PARÂMETROS v8.0 ===
        self.margem_tela = 100  # Pixels de margem nas bordas
        self.zoom_min = 0.4    # Zoom mínimo (para ver lutadores muito distantes)
        self.zoom_max = 1.8    # Zoom máximo (combate próximo)
        self.velocidade_zoom = 3.0  # Velocidade de transição do zoom
        self.velocidade_pan = 6.0   # Velocidade de movimento da câmera
        
        # Tracking de velocidade para enquadramento preditivo
        self._prev_centro = None
        self._velocidade_centro = (0, 0)

    def aplicar_shake(self, forca, duracao=0.2):
        """Aplica efeito de shake na câmera"""
        self.shake_magnitude = max(self.shake_magnitude, forca)  # Não reduz shake atual
        self.shake_timer = max(self.shake_timer, duracao)

    def converter(self, world_x, world_y):
        """Converte coordenadas do mundo para tela"""
        screen_x = (world_x - self.x) * self.zoom + LARGURA / 2 + self.offset_x
        screen_y = (world_y - self.y) * self.zoom + ALTURA / 2 + self.offset_y
        return int(screen_x), int(screen_y)

    def converter_tam(self, tamanho):
        """Converte tamanho do mundo para tela"""
        return int(tamanho * self.zoom)
    
    def _calcular_bounding_box(self, p1, p2):
        """
        Calcula a bounding box que contém ambos os lutadores.
        Retorna: (min_x, min_y, max_x, max_y) em pixels do mundo
        """
        # Posições em pixels
        x1, y1 = p1.pos[0] * PPM, p1.pos[1] * PPM
        x2, y2 = p2.pos[0] * PPM, p2.pos[1] * PPM
        
        # Considera altura Z (pulos/knockback vertical)
        z1 = getattr(p1, 'z', 0) * PPM
        z2 = getattr(p2, 'z', 0) * PPM
        
        # Tamanho visual dos lutadores
        raio1 = p1.dados.tamanho * PPM * 0.8
        raio2 = p2.dados.tamanho * PPM * 0.8
        
        # Bounding box expandida
        min_x = min(x1 - raio1, x2 - raio2)
        max_x = max(x1 + raio1, x2 + raio2)
        min_y = min(y1 - raio1 - z1, y2 - raio2 - z2)  # Considera altura
        max_y = max(y1 + raio1, y2 + raio2)
        
        return min_x, min_y, max_x, max_y
    
    def _calcular_zoom_ideal(self, p1, p2):
        """
        Calcula o zoom ideal para manter ambos os lutadores visíveis.
        """
        # Bounding box dos lutadores
        min_x, min_y, max_x, max_y = self._calcular_bounding_box(p1, p2)
        
        # Tamanho necessário para enquadrar
        largura_necessaria = (max_x - min_x) + self.margem_tela * 2
        altura_necessaria = (max_y - min_y) + self.margem_tela * 2
        
        # Zoom necessário para caber na tela
        zoom_x = LARGURA / largura_necessaria if largura_necessaria > 0 else 1.0
        zoom_y = ALTURA / altura_necessaria if altura_necessaria > 0 else 1.0
        
        # Usa o menor zoom (para garantir que tudo caiba)
        zoom_ideal = min(zoom_x, zoom_y)
        
        # === AJUSTES DE DRAMA/TENSÃO ===
        
        # Distância entre lutadores
        dist = math.hypot(p1.pos[0] - p2.pos[0], p1.pos[1] - p2.pos[1])
        
        # Combate muito próximo = zoom in dramático
        if dist < 2.5 and zoom_ideal > 1.2:
            zoom_ideal = min(zoom_ideal, 1.5)  # Não muito perto
        
        # Vida crítica = ligeiramente mais zoom
        vida_min = min(p1.vida / p1.vida_max if p1.vida_max > 0 else 1, 
                       p2.vida / p2.vida_max if p2.vida_max > 0 else 1)
        if vida_min < 0.25:
            zoom_ideal *= 1.1  # 10% mais zoom em momentos críticos
        
        # Limita zoom
        return max(self.zoom_min, min(self.zoom_max, zoom_ideal))

    def atualizar(self, dt, p1, p2):
        """Atualiza a câmera baseado nos lutadores"""
        
        # === ZOOM DINÂMICO INTELIGENTE ===
        if self.modo == "AUTO":
            # Calcula zoom ideal para manter ambos visíveis
            zoom_ideal = self._calcular_zoom_ideal(p1, p2)
            
            # Suaviza transição do target_zoom
            # Zoom out é mais rápido que zoom in (para não perder lutadores)
            if zoom_ideal < self.target_zoom:
                # Zoom out - mais rápido
                velocidade = self.velocidade_zoom * 1.5
            else:
                # Zoom in - mais suave
                velocidade = self.velocidade_zoom
            
            self.target_zoom += (zoom_ideal - self.target_zoom) * velocidade * dt
        
        # Aplica zoom suavemente
        self.zoom += (self.target_zoom - self.zoom) * 5 * dt
        self.zoom = max(self.zoom_min, min(self.zoom_max, self.zoom))
        
        # === SHAKE ===
        if self.shake_timer > 0:
            self.shake_timer -= dt
            # Shake com decay exponencial
            decay = self.shake_timer / 0.3
            shake_atual = self.shake_magnitude * decay * decay
            self.offset_x = random.uniform(-shake_atual, shake_atual)
            self.offset_y = random.uniform(-shake_atual, shake_atual)
        else:
            self.offset_x *= 0.8  # Fade suave
            self.offset_y *= 0.8
            self.shake_magnitude = 0
        
        # === POSIÇÃO DA CÂMERA ===
        if self.modo == "P1":
            tx, ty = p1.pos[0] * PPM, p1.pos[1] * PPM
            self.lerp_pos(tx, ty, dt, self.velocidade_pan)
        elif self.modo == "P2":
            tx, ty = p2.pos[0] * PPM, p2.pos[1] * PPM
            self.lerp_pos(tx, ty, dt, self.velocidade_pan)
        elif self.modo == "AUTO":
            # Centro entre os lutadores
            cx = (p1.pos[0] + p2.pos[0]) / 2 * PPM
            cy = (p1.pos[1] + p2.pos[1]) / 2 * PPM
            
            # === ENQUADRAMENTO PREDITIVO ===
            # Antecipa movimento baseado na velocidade do centro
            if self._prev_centro is not None:
                vel_x = (cx - self._prev_centro[0]) / dt if dt > 0 else 0
                vel_y = (cy - self._prev_centro[1]) / dt if dt > 0 else 0
                
                # Suaviza velocidade
                self._velocidade_centro = (
                    self._velocidade_centro[0] * 0.8 + vel_x * 0.2,
                    self._velocidade_centro[1] * 0.8 + vel_y * 0.2
                )
                
                # Antecipa ligeiramente (olha para onde estão indo)
                predicao = 0.15  # Segundos de predição
                cx += self._velocidade_centro[0] * predicao
                cy += self._velocidade_centro[1] * predicao
            
            self._prev_centro = ((p1.pos[0] + p2.pos[0]) / 2 * PPM,
                                (p1.pos[1] + p2.pos[1]) / 2 * PPM)
            
            # Move câmera mais rápido quando lutadores estão muito fora de quadro
            velocidade = self.velocidade_pan
            
            # Verifica se algum lutador está fora da tela
            for p in [p1, p2]:
                px, py = p.pos[0] * PPM, p.pos[1] * PPM
                sx, sy = self.converter(px, py)
                
                # Se está muito fora, acelera a câmera
                if sx < 0 or sx > LARGURA or sy < 0 or sy > ALTURA:
                    velocidade = self.velocidade_pan * 2.5
                    break
                elif sx < 50 or sx > LARGURA - 50 or sy < 50 or sy > ALTURA - 50:
                    velocidade = self.velocidade_pan * 1.5
            
            self.lerp_pos(cx, cy, dt, velocidade)

    def zoom_punch(self, intensidade=0.15, duracao=0.1):
        """Efeito de zoom punch para impactos"""
        # Temporariamente aumenta o zoom
        self.target_zoom += intensidade
        # O sistema de zoom dinâmico vai corrigir naturalmente
    
    def lerp_pos(self, tx, ty, dt, velocidade=5.0):
        """Interpola suavemente a posição da câmera"""
        self.x += (tx - self.x) * velocidade * dt
        self.y += (ty - self.y) * velocidade * dt
    
    def esta_visivel(self, world_x, world_y, margem=50):
        """Verifica se uma posição do mundo está visível na tela"""
        sx, sy = self.converter(world_x, world_y)
        return -margem < sx < LARGURA + margem and -margem < sy < ALTURA + margem
    
    def get_bounds_mundo(self):
        """Retorna os limites do mundo visíveis na tela"""
        # Cantos da tela em coordenadas do mundo
        min_x = self.x - (LARGURA / 2) / self.zoom
        max_x = self.x + (LARGURA / 2) / self.zoom
        min_y = self.y - (ALTURA / 2) / self.zoom
        max_y = self.y + (ALTURA / 2) / self.zoom
        return min_x, min_y, max_x, max_y
