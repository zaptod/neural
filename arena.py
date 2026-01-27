"""
NEURAL FIGHTS - Sistema de Arena v1.0
Define os limites do mapa e colisões com paredes.
"""

import math
import pygame
from config import PPM, LARGURA, ALTURA
from dataclasses import dataclass
from typing import Tuple, List, Optional


@dataclass
class ArenaConfig:
    """Configuração de uma arena"""
    nome: str
    largura: float  # Em metros
    altura: float   # Em metros
    cor_chao: Tuple[int, int, int] = (30, 30, 30)
    cor_parede: Tuple[int, int, int] = (60, 60, 80)
    cor_borda: Tuple[int, int, int] = (100, 100, 140)
    espessura_parede: float = 0.3  # Em metros
    tem_paredes: bool = True
    formato: str = "retangular"  # "retangular", "circular", "octogono"


# Arenas pré-definidas
ARENAS = {
    "Arena": ArenaConfig(
        nome="Arena Clássica",
        largura=30.0,  # 30 metros de largura
        altura=20.0,   # 20 metros de altura
        cor_chao=(25, 25, 35),
        cor_parede=(50, 50, 70),
        cor_borda=(80, 80, 120),
        formato="retangular"
    ),
    "Arena Pequena": ArenaConfig(
        nome="Arena Compacta",
        largura=18.0,
        altura=12.0,
        cor_chao=(35, 25, 25),
        cor_parede=(70, 50, 50),
        cor_borda=(120, 80, 80),
        formato="retangular"
    ),
    "Coliseu": ArenaConfig(
        nome="Coliseu",
        largura=35.0,
        altura=35.0,
        cor_chao=(40, 35, 25),
        cor_parede=(80, 70, 50),
        cor_borda=(140, 120, 80),
        formato="circular"
    ),
    "Dojo": ArenaConfig(
        nome="Dojo",
        largura=20.0,
        altura=20.0,
        cor_chao=(50, 40, 30),
        cor_parede=(90, 75, 55),
        cor_borda=(130, 110, 80),
        formato="octogono"
    ),
}


class Arena:
    """
    Sistema de arena com limites e paredes.
    """
    
    def __init__(self, config: ArenaConfig = None):
        if config is None:
            config = ARENAS["Arena"]
        
        self.config = config
        self.largura = config.largura
        self.altura = config.altura
        
        # Limites em metros
        self.min_x = 0
        self.max_x = config.largura
        self.min_y = 0
        self.max_y = config.altura
        
        # Centro da arena
        self.centro_x = config.largura / 2
        self.centro_y = config.altura / 2
        
        # Para coliseu circular
        if config.formato == "circular":
            self.raio = min(config.largura, config.altura) / 2 - config.espessura_parede
        else:
            self.raio = None
        
        # Histórico de colisões para efeitos
        self.colisoes_recentes: List[Tuple[float, float, float]] = []  # (x, y, intensidade)
    
    def aplicar_limites(self, lutador, dt: float) -> bool:
        """
        Aplica limites da arena ao lutador.
        Retorna True se houve colisão com parede.
        """
        if not self.config.tem_paredes:
            return False
        
        colidiu = False
        margem = lutador.raio_fisico
        bounce = 0.3  # Coeficiente de rebote
        
        if self.config.formato == "circular":
            # Arena circular
            dx = lutador.pos[0] - self.centro_x
            dy = lutador.pos[1] - self.centro_y
            dist = math.hypot(dx, dy)
            
            if dist + margem > self.raio:
                # Colisão com borda circular
                colidiu = True
                
                # Normaliza direção
                if dist > 0:
                    nx, ny = dx / dist, dy / dist
                else:
                    nx, ny = 1, 0
                
                # Empurra de volta
                lutador.pos[0] = self.centro_x + nx * (self.raio - margem - 0.01)
                lutador.pos[1] = self.centro_y + ny * (self.raio - margem - 0.01)
                
                # Rebote
                dot = lutador.vel[0] * nx + lutador.vel[1] * ny
                if dot > 0:  # Só rebote se indo em direção à parede
                    lutador.vel[0] -= (1 + bounce) * dot * nx
                    lutador.vel[1] -= (1 + bounce) * dot * ny
                
                # Registra colisão
                intensidade = abs(dot)
                if intensidade > 2:
                    self.colisoes_recentes.append((lutador.pos[0], lutador.pos[1], intensidade))
        
        elif self.config.formato == "octogono":
            # Arena octogonal (simplificado como retângulo com cantos cortados)
            colidiu = self._aplicar_limites_retangular(lutador, margem, bounce)
            
            # Corta cantos (45 graus)
            corte = min(self.largura, self.altura) * 0.2
            cantos = [
                (self.min_x + corte, self.min_y, 1, 1),      # Superior esquerdo
                (self.max_x - corte, self.min_y, -1, 1),    # Superior direito
                (self.min_x + corte, self.max_y, 1, -1),    # Inferior esquerdo
                (self.max_x - corte, self.max_y, -1, -1),   # Inferior direito
            ]
            
            for cx, cy, dx, dy in cantos:
                # Verifica se está no canto
                px = lutador.pos[0]
                py = lutador.pos[1]
                
                if dx > 0:  # Esquerda
                    in_x = px < cx
                else:  # Direita
                    in_x = px > cx
                    
                if dy > 0:  # Cima
                    in_y = py < cy
                else:  # Baixo
                    in_y = py > cy
                
                if in_x and in_y:
                    # Está no canto - aplica limite diagonal
                    # Linha do canto: dy*x + dx*y = dy*cx + dx*cy
                    linha_val = dy * (px - cx) + dx * (py - cy)
                    if (dx * dy > 0 and linha_val < 0) or (dx * dy < 0 and linha_val > 0):
                        colidiu = True
                        # Projeta de volta
                        norm = math.hypot(dx, dy)
                        nx, ny = dx / norm, dy / norm
                        dist_linha = abs(linha_val) / norm
                        lutador.pos[0] += nx * (dist_linha + margem)
                        lutador.pos[1] += ny * (dist_linha + margem)
        else:
            # Arena retangular padrão
            colidiu = self._aplicar_limites_retangular(lutador, margem, bounce)
        
        return colidiu
    
    def _aplicar_limites_retangular(self, lutador, margem: float, bounce: float) -> bool:
        """Aplica limites retangulares"""
        colidiu = False
        
        # Parede esquerda
        if lutador.pos[0] - margem < self.min_x:
            lutador.pos[0] = self.min_x + margem
            if lutador.vel[0] < 0:
                intensidade = abs(lutador.vel[0])
                lutador.vel[0] *= -bounce
                if intensidade > 2:
                    self.colisoes_recentes.append((lutador.pos[0], lutador.pos[1], intensidade))
            colidiu = True
        
        # Parede direita
        if lutador.pos[0] + margem > self.max_x:
            lutador.pos[0] = self.max_x - margem
            if lutador.vel[0] > 0:
                intensidade = abs(lutador.vel[0])
                lutador.vel[0] *= -bounce
                if intensidade > 2:
                    self.colisoes_recentes.append((lutador.pos[0], lutador.pos[1], intensidade))
            colidiu = True
        
        # Parede superior
        if lutador.pos[1] - margem < self.min_y:
            lutador.pos[1] = self.min_y + margem
            if lutador.vel[1] < 0:
                intensidade = abs(lutador.vel[1])
                lutador.vel[1] *= -bounce
                if intensidade > 2:
                    self.colisoes_recentes.append((lutador.pos[0], lutador.pos[1], intensidade))
            colidiu = True
        
        # Parede inferior
        if lutador.pos[1] + margem > self.max_y:
            lutador.pos[1] = self.max_y - margem
            if lutador.vel[1] > 0:
                intensidade = abs(lutador.vel[1])
                lutador.vel[1] *= -bounce
                if intensidade > 2:
                    self.colisoes_recentes.append((lutador.pos[0], lutador.pos[1], intensidade))
            colidiu = True
        
        return colidiu
    
    def esta_dentro(self, x: float, y: float, margem: float = 0) -> bool:
        """Verifica se um ponto está dentro da arena"""
        if self.config.formato == "circular":
            dx = x - self.centro_x
            dy = y - self.centro_y
            return math.hypot(dx, dy) + margem <= self.raio
        else:
            return (self.min_x + margem <= x <= self.max_x - margem and
                    self.min_y + margem <= y <= self.max_y - margem)
    
    def get_spawn_points(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Retorna pontos de spawn para dois lutadores"""
        # P1 na esquerda, P2 na direita
        margem = 3.0  # Metros da borda
        
        p1_x = self.centro_x - self.largura * 0.3
        p1_y = self.centro_y
        
        p2_x = self.centro_x + self.largura * 0.3
        p2_y = self.centro_y
        
        return (p1_x, p1_y), (p2_x, p2_y)
    
    def limpar_colisoes(self):
        """Limpa histórico de colisões"""
        # Mantém apenas colisões recentes
        self.colisoes_recentes = self.colisoes_recentes[-10:]
    
    def desenhar(self, surface: pygame.Surface, camera):
        """
        Desenha a arena na tela.
        """
        # Desenha chão
        self._desenhar_chao(surface, camera)
        
        # Desenha paredes
        if self.config.tem_paredes:
            self._desenhar_paredes(surface, camera)
        
        # Desenha efeitos de colisão com paredes
        self._desenhar_efeitos_colisao(surface, camera)
    
    def _desenhar_chao(self, surface: pygame.Surface, camera):
        """Desenha o chão da arena"""
        cor = self.config.cor_chao
        
        if self.config.formato == "circular":
            # Chão circular
            cx, cy = camera.converter(self.centro_x * PPM, self.centro_y * PPM)
            raio = camera.converter_tam(self.raio * PPM)
            if raio > 0:
                pygame.draw.circle(surface, cor, (cx, cy), raio)
        else:
            # Chão retangular
            min_px = camera.converter(self.min_x * PPM, self.min_y * PPM)
            max_px = camera.converter(self.max_x * PPM, self.max_y * PPM)
            
            largura = max_px[0] - min_px[0]
            altura = max_px[1] - min_px[1]
            
            if largura > 0 and altura > 0:
                rect = pygame.Rect(min_px[0], min_px[1], largura, altura)
                pygame.draw.rect(surface, cor, rect)
        
        # Grid no chão
        self._desenhar_grid(surface, camera)
    
    def _desenhar_grid(self, surface: pygame.Surface, camera):
        """Desenha grid no chão"""
        grid_size = 2.0  # Metros
        cor_grid = tuple(min(255, c + 10) for c in self.config.cor_chao)
        
        # Linhas verticais
        x = math.ceil(self.min_x / grid_size) * grid_size
        while x < self.max_x:
            p1 = camera.converter(x * PPM, self.min_y * PPM)
            p2 = camera.converter(x * PPM, self.max_y * PPM)
            pygame.draw.line(surface, cor_grid, p1, p2, 1)
            x += grid_size
        
        # Linhas horizontais
        y = math.ceil(self.min_y / grid_size) * grid_size
        while y < self.max_y:
            p1 = camera.converter(self.min_x * PPM, y * PPM)
            p2 = camera.converter(self.max_x * PPM, y * PPM)
            pygame.draw.line(surface, cor_grid, p1, p2, 1)
            y += grid_size
    
    def _desenhar_paredes(self, surface: pygame.Surface, camera):
        """Desenha as paredes da arena"""
        esp = self.config.espessura_parede
        cor = self.config.cor_parede
        cor_borda = self.config.cor_borda
        
        if self.config.formato == "circular":
            # Borda circular
            cx, cy = camera.converter(self.centro_x * PPM, self.centro_y * PPM)
            raio_ext = camera.converter_tam((self.raio + esp) * PPM)
            raio_int = camera.converter_tam(self.raio * PPM)
            
            if raio_ext > 0:
                # Anel da parede
                pygame.draw.circle(surface, cor, (cx, cy), raio_ext)
                pygame.draw.circle(surface, self.config.cor_chao, (cx, cy), raio_int)
                
                # Borda interna
                pygame.draw.circle(surface, cor_borda, (cx, cy), raio_int, max(2, camera.converter_tam(3)))
        
        elif self.config.formato == "octogono":
            # Desenha octógono
            corte = min(self.largura, self.altura) * 0.2
            pontos = [
                (self.min_x + corte, self.min_y),
                (self.max_x - corte, self.min_y),
                (self.max_x, self.min_y + corte),
                (self.max_x, self.max_y - corte),
                (self.max_x - corte, self.max_y),
                (self.min_x + corte, self.max_y),
                (self.min_x, self.max_y - corte),
                (self.min_x, self.min_y + corte),
            ]
            
            pontos_tela = [camera.converter(p[0] * PPM, p[1] * PPM) for p in pontos]
            
            # Desenha parede externa
            pontos_ext = []
            for p in pontos:
                dx = p[0] - self.centro_x
                dy = p[1] - self.centro_y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    nx, ny = dx / dist, dy / dist
                else:
                    nx, ny = 0, 0
                pontos_ext.append(camera.converter((p[0] + nx * esp) * PPM, (p[1] + ny * esp) * PPM))
            
            pygame.draw.polygon(surface, cor, pontos_ext)
            pygame.draw.polygon(surface, self.config.cor_chao, pontos_tela)
            pygame.draw.polygon(surface, cor_borda, pontos_tela, max(3, camera.converter_tam(5)))
        
        else:
            # Paredes retangulares
            esp_px = camera.converter_tam(esp * PPM)
            
            # Parede superior
            p1 = camera.converter((self.min_x - esp) * PPM, (self.min_y - esp) * PPM)
            p2 = camera.converter((self.max_x + esp) * PPM, self.min_y * PPM)
            rect = pygame.Rect(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1])
            pygame.draw.rect(surface, cor, rect)
            
            # Parede inferior
            p1 = camera.converter((self.min_x - esp) * PPM, self.max_y * PPM)
            p2 = camera.converter((self.max_x + esp) * PPM, (self.max_y + esp) * PPM)
            rect = pygame.Rect(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1])
            pygame.draw.rect(surface, cor, rect)
            
            # Parede esquerda
            p1 = camera.converter((self.min_x - esp) * PPM, self.min_y * PPM)
            p2 = camera.converter(self.min_x * PPM, self.max_y * PPM)
            rect = pygame.Rect(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1])
            pygame.draw.rect(surface, cor, rect)
            
            # Parede direita
            p1 = camera.converter(self.max_x * PPM, self.min_y * PPM)
            p2 = camera.converter((self.max_x + esp) * PPM, self.max_y * PPM)
            rect = pygame.Rect(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1])
            pygame.draw.rect(surface, cor, rect)
            
            # Bordas internas
            min_px = camera.converter(self.min_x * PPM, self.min_y * PPM)
            max_px = camera.converter(self.max_x * PPM, self.max_y * PPM)
            largura = max_px[0] - min_px[0]
            altura = max_px[1] - min_px[1]
            if largura > 0 and altura > 0:
                pygame.draw.rect(surface, cor_borda, 
                               pygame.Rect(min_px[0], min_px[1], largura, altura),
                               max(3, camera.converter_tam(5)))
    
    def _desenhar_efeitos_colisao(self, surface: pygame.Surface, camera):
        """Desenha efeitos visuais de colisão com paredes"""
        for i, (x, y, intensidade) in enumerate(self.colisoes_recentes):
            # Fade baseado na posição na lista (mais recente = mais visível)
            alpha = int(200 * (i + 1) / len(self.colisoes_recentes)) if self.colisoes_recentes else 0
            
            cx, cy = camera.converter(x * PPM, y * PPM)
            raio = int(min(30, intensidade * 5))
            
            if raio > 2:
                s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.config.cor_borda, alpha), (raio, raio), raio)
                surface.blit(s, (cx - raio, cy - raio))


# Instância global da arena (pode ser substituída)
_arena_atual: Optional[Arena] = None

def get_arena() -> Arena:
    """Obtém a arena atual"""
    global _arena_atual
    if _arena_atual is None:
        _arena_atual = Arena()
    return _arena_atual

def set_arena(config_nome: str = "Arena") -> Arena:
    """Define a arena atual pelo nome"""
    global _arena_atual
    if config_nome in ARENAS:
        _arena_atual = Arena(ARENAS[config_nome])
    else:
        _arena_atual = Arena()
    return _arena_atual
