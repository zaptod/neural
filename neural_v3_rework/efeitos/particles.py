"""
NEURAL FIGHTS - Sistema de PartÃ­culas
PartÃ­culas, faÃ­scas e efeitos de encantamento
"""

import pygame
import random
import math
from utilitarios.config import PPM


# Cores dos encantamentos para partÃ­culas
CORES_ENCANTAMENTOS = {
    "Chamas": [(255, 100, 0), (255, 200, 50), (255, 50, 0)],
    "Gelo": [(100, 200, 255), (200, 230, 255), (150, 220, 255)],
    "RelÃ¢mpago": [(255, 255, 100), (200, 200, 255), (255, 255, 255)],
    "Veneno": [(100, 255, 100), (50, 200, 50), (150, 255, 100)],
    "Trevas": [(100, 0, 150), (50, 0, 100), (150, 50, 200)],
    "Sagrado": [(255, 255, 200), (255, 215, 0), (255, 255, 255)],
    "Velocidade": [(200, 200, 255), (150, 150, 255), (255, 255, 255)],
    "Vampirismo": [(200, 0, 0), (150, 0, 50), (255, 50, 50)],
    "CrÃ­tico": [(255, 50, 50), (255, 100, 100), (255, 0, 0)],
    "PenetraÃ§Ã£o": [(150, 150, 150), (200, 200, 200), (100, 100, 100)],
    "ExecuÃ§Ã£o": [(50, 0, 0), (100, 0, 0), (150, 0, 0)],
    "Espelhamento": [(150, 200, 255), (200, 230, 255), (100, 150, 255)],
}


class Particula:
    """PartÃ­cula bÃ¡sica para efeitos visuais"""
    def __init__(self, x, y, cor, vel_x, vel_y, tamanho, vida_util=1.0):
        self.x, self.y = x, y
        self.cor = cor
        self.vel_x, self.vel_y = vel_x, vel_y
        self.tamanho = tamanho
        self.vida = vida_util

    def atualizar(self, dt):
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        self.vida -= dt
        self.tamanho *= 0.92


class HitSpark:
    """FaÃ­scas estilizadas de impacto â€” v15.0 POLISHED com glow"""
    def __init__(self, x, y, cor, direcao, intensidade=1.0):
        self.x = x
        self.y = y
        self.cor = cor
        self.vida = 0.25
        self.max_vida = 0.25
        self.intensidade = intensidade
        self.sparks = []
        
        # Mais faÃ­scas com variaÃ§Ã£o maior
        num_sparks = int(15 * intensidade)
        for _ in range(num_sparks):
            ang = direcao + random.uniform(-0.9, 0.9)
            vel = random.uniform(90, 250) * intensidade
            vida = random.uniform(0.1, 0.25)
            self.sparks.append({
                'x': x, 'y': y,
                'vx': math.cos(ang) * vel,
                'vy': math.sin(ang) * vel,
                'comprimento': random.uniform(10, 25) * intensidade,
                'vida': vida,
                'max_vida': vida,
                'largura': random.uniform(1.5, 3.5),
            })
    
    def update(self, dt):
        self.vida -= dt
        for s in self.sparks:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['vy'] += 100 * dt  # Gravidade sutil
            s['vida'] -= dt
            s['comprimento'] *= 0.92
        self.sparks = [s for s in self.sparks if s['vida'] > 0]
    
    def draw(self, tela, cam):
        for s in self.sparks:
            if s['vida'] <= 0:
                continue
            sx, sy = cam.converter(s['x'], s['y'])
            life_pct = s['vida'] / s['max_vida']
            alpha = int(255 * life_pct)
            
            ang = math.atan2(s['vy'], s['vx'])
            comp = cam.converter_tam(s['comprimento'])
            ex = sx + math.cos(ang) * comp
            ey = sy + math.sin(ang) * comp
            
            # Surface com glow
            min_x = min(sx, int(ex)) - 6
            min_y = min(sy, int(ey)) - 6
            max_x = max(sx, int(ex)) + 6
            max_y = max(sy, int(ey)) + 6
            w = max(8, max_x - min_x)
            h = max(8, max_y - min_y)
            
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            lp1 = (sx - min_x, sy - min_y)
            lp2 = (int(ex) - min_x, int(ey) - min_y)
            
            # Glow externo colorido
            glow_alpha = max(0, min(255, alpha // 3))
            larg_glow = max(3, int(s['largura'] + 3))
            pygame.draw.line(surf, (*self.cor[:3], glow_alpha), lp1, lp2, larg_glow)
            
            # Core brilhante branco
            core_alpha = max(0, min(255, int(alpha * 0.9)))
            pygame.draw.line(surf, (255, 255, 255, core_alpha), lp1, lp2, max(1, int(s['largura'])))
            
            # Ponta brilhante
            tip_r = max(1, int(2 * life_pct))
            pygame.draw.circle(surf, (255, 255, 200, core_alpha), lp2, tip_r)
            
            tela.blit(surf, (min_x, min_y))


class Shockwave:
    """Onda de choque â€” v15.0 POLISHED com glow e gradiente"""
    def __init__(self, x, y, cor, tamanho=1.0):
        self.x = x
        self.y = y
        self.raio = 10.0 * tamanho
        self.cor = cor
        self.vida = 0.35
        self.max_vida = 0.35
        self.tamanho = tamanho

    def update(self, dt):
        self.vida -= dt
        self.raio += 450 * dt  # Expande um pouco mais rÃ¡pido

    def draw(self, tela, cam):
        if self.vida <= 0:
            return
        sx, sy = cam.converter(self.x, self.y)
        r = cam.converter_tam(self.raio)
        if r < 3:
            return
        
        prog = 1.0 - (self.vida / self.max_vida)
        base_alpha = int(255 * (1.0 - prog ** 1.5))
        
        # Surface pra glow
        surf_size = (r + 10) * 2
        if surf_size < 10 or surf_size > 2000:
            return
        s = pygame.Surface((int(surf_size), int(surf_size)), pygame.SRCALPHA)
        centro = (int(surf_size) // 2, int(surf_size) // 2)
        
        # Camada 1: Glow externo suave
        glow_alpha = max(0, min(255, base_alpha // 5))
        glow_r = min(r + 8, int(surf_size) // 2 - 1)
        if glow_r > 2:
            pygame.draw.circle(s, (*self.cor[:3], glow_alpha), centro, glow_r, max(3, int(8 * (1.0 - prog))))
        
        # Camada 2: Anel principal colorido
        ring_alpha = max(0, min(255, int(base_alpha * 0.7)))
        ring_width = max(2, int(5 * (1.0 - prog)))
        ring_r = min(r, int(surf_size) // 2 - 2)
        if ring_r > 2:
            pygame.draw.circle(s, (*self.cor[:3], ring_alpha), centro, ring_r, ring_width)
        
        # Camada 3: Anel interno branco brilhante
        inner_r = max(2, min(r - 3, int(surf_size) // 2 - 2))
        core_alpha = max(0, min(255, int(base_alpha * 0.5)))
        core_width = max(1, ring_width - 1)
        if inner_r > 2:
            pygame.draw.circle(s, (255, 255, 255, core_alpha), centro, inner_r, core_width)
        
        tela.blit(s, (sx - int(surf_size) // 2, sy - int(surf_size) // 2))


class EncantamentoEffect:
    """Efeito visual de encantamento na arma â€” v15.0 com glow e padrÃµes por elemento"""
    def __init__(self, encantamento, pos_func):
        self.encantamento = encantamento
        self.pos_func = pos_func
        self.particulas = []
        self.cores = CORES_ENCANTAMENTOS.get(encantamento, [(255, 255, 255)])
        self.timer = 0
        self.glow_timer = 0
        
    def update(self, dt):
        self.timer += dt
        self.glow_timer += dt
        
        if self.timer > 0.04:  # Spawn mais frequente
            self.timer = 0
            pos = self.pos_func()
            if pos:
                x, y = pos
                cor = random.choice(self.cores)
                
                # PadrÃµes de velocidade por elemento
                if self.encantamento == "Chamas":
                    vel_x = random.uniform(-40, 40)
                    vel_y = random.uniform(-100, -40)
                    tam = random.uniform(3, 6)
                    vida = random.uniform(0.3, 0.6)
                elif self.encantamento == "Gelo":
                    vel_x = random.uniform(-20, 20)
                    vel_y = random.uniform(5, 30)
                    tam = random.uniform(2, 5)
                    vida = random.uniform(0.4, 0.7)
                elif self.encantamento == "RelÃ¢mpago":
                    vel_x = random.uniform(-120, 120)
                    vel_y = random.uniform(-120, 120)
                    tam = random.uniform(2, 4)
                    vida = random.uniform(0.1, 0.25)
                elif self.encantamento == "Trevas":
                    ang = random.uniform(0, math.pi * 2)
                    dist = random.uniform(5, 15)
                    vel_x = math.cos(ang) * dist
                    vel_y = math.sin(ang) * dist
                    tam = random.uniform(3, 6)
                    vida = random.uniform(0.5, 0.8)
                elif self.encantamento == "Sagrado":
                    ang = random.uniform(0, math.pi * 2)
                    dist = random.uniform(20, 50)
                    vel_x = math.cos(ang) * dist
                    vel_y = math.sin(ang) * dist - 20
                    tam = random.uniform(2, 4)
                    vida = random.uniform(0.4, 0.7)
                elif self.encantamento == "Vampirismo":
                    vel_x = random.uniform(-15, 15)
                    vel_y = random.uniform(-50, -20)
                    tam = random.uniform(2, 5)
                    vida = random.uniform(0.3, 0.5)
                else:
                    vel_x = random.uniform(-30, 30)
                    vel_y = random.uniform(-30, 30)
                    tam = random.uniform(2, 4)
                    vida = random.uniform(0.3, 0.5)
                
                # Offset de spawn aleatÃ³rio
                x += random.uniform(-5, 5)
                y += random.uniform(-5, 5)
                    
                self.particulas.append(Particula(x, y, cor, vel_x, vel_y, tam, vida))
        
        for p in self.particulas:
            p.atualizar(dt)
        self.particulas = [p for p in self.particulas if p.vida > 0]
                
    def draw(self, tela, cam):
        for p in self.particulas:
            sx, sy = cam.converter(p.x, p.y)
            tam = cam.converter_tam(p.tamanho)
            life_pct = max(0, p.vida)
            
            if tam > 2:
                # PartÃ­cula com glow
                surf_size = max(6, int(tam * 3) + 4)
                s = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
                c = surf_size // 2
                alpha = max(0, min(255, int(255 * life_pct)))
                glow_a = max(0, min(255, alpha // 3))
                pygame.draw.circle(s, (*p.cor[:3], glow_a), (c, c), min(c - 1, int(tam * 1.3)))
                pygame.draw.circle(s, (*p.cor[:3], alpha), (c, c), max(1, int(tam * 0.7)))
                # Hotspot branco para efeitos de luz
                if self.encantamento in ["RelÃ¢mpago", "Sagrado", "Chamas"]:
                    hot_a = max(0, min(255, int(alpha * 0.5)))
                    pygame.draw.circle(s, (255, 255, 255, hot_a), (c, c), max(1, int(tam * 0.3)))
                tela.blit(s, (sx - c, sy - c))
            elif tam > 0:
                pygame.draw.circle(tela, p.cor, (sx, sy), max(1, tam))

