import pygame
import random
from config import *

class FloatingText:
    def __init__(self, x, y, texto, cor, tamanho=20):
        self.x = x
        self.y = y
        self.texto = str(int(texto)) if isinstance(texto, (int, float)) else texto
        self.cor = cor
        self.fonte = pygame.font.SysFont("Impact", tamanho)
        self.vel_y = -1.0
        self.vida = 1.0
        self.alpha = 255

    def update(self, dt):
        self.y += self.vel_y * dt * 60
        self.vel_y += 0.05 
        self.vida -= dt
        if self.vida < 0.5:
            self.alpha = int(255 * (self.vida / 0.5))

    def draw(self, tela, cam):
        if self.vida <= 0: return
        sx, sy = cam.converter(self.x, self.y)
        surf = self.fonte.render(self.texto, True, self.cor)
        surf.set_alpha(self.alpha)
        sombra = self.fonte.render(self.texto, True, PRETO)
        sombra.set_alpha(self.alpha)
        tela.blit(sombra, (sx+2, sy+2))
        tela.blit(surf, (sx, sy))

class Decal:
    """Manchas no chão"""
    def __init__(self, x, y, raio, cor):
        self.x = x
        self.y = y
        self.raio = raio
        self.cor = cor
        self.alpha = 200

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        r = cam.converter_tam(self.raio)
        if r < 1: return
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.cor, self.alpha), (r, r), r)
        tela.blit(s, (sx-r, sy-r))

class Shockwave:
    """Onda de choque"""
    def __init__(self, x, y, cor):
        self.x = x
        self.y = y
        self.raio = 10.0
        self.cor = cor
        self.vida = 0.3
        self.max_vida = 0.3

    def update(self, dt):
        self.vida -= dt
        self.raio += 500 * dt

    def draw(self, tela, cam):
        if self.vida <= 0: return
        sx, sy = cam.converter(self.x, self.y)
        r = cam.converter_tam(self.raio)
        width = int(5 * (self.vida / self.max_vida))
        if width < 1: width = 1
        pygame.draw.circle(tela, self.cor, (sx, sy), r, width)

class Particula:
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

class Câmera:
    def __init__(self):
        self.x = 12.0 * PPM 
        self.y = 8.0 * PPM
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.modo = "AUTO" 
        self.shake_timer = 0.0
        self.shake_magnitude = 0.0
        self.offset_x = 0
        self.offset_y = 0

    def aplicar_shake(self, forca, duracao=0.2):
        self.shake_magnitude = forca
        self.shake_timer = duracao

    def converter(self, world_x, world_y):
        screen_x = (world_x - self.x) * self.zoom + LARGURA / 2 + self.offset_x
        screen_y = (world_y - self.y) * self.zoom + ALTURA / 2 + self.offset_y
        return int(screen_x), int(screen_y)

    def converter_tam(self, tamanho):
        return int(tamanho * self.zoom)

    def atualizar(self, dt, p1, p2):
        self.zoom += (self.target_zoom - self.zoom) * 5 * dt
        
        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.offset_x = random.uniform(-self.shake_magnitude, self.shake_magnitude)
            self.offset_y = random.uniform(-self.shake_magnitude, self.shake_magnitude)
        else:
            self.offset_x = 0; self.offset_y = 0
        
        if self.modo == "P1":
            tx, ty = p1.pos[0] * PPM, p1.pos[1] * PPM
            self.lerp_pos(tx, ty, dt)
        elif self.modo == "P2":
            tx, ty = p2.pos[0] * PPM, p2.pos[1] * PPM
            self.lerp_pos(tx, ty, dt)
        elif self.modo == "AUTO":
            mx = (p1.pos[0] + p2.pos[0]) / 2 * PPM
            my = (p1.pos[1] + p2.pos[1]) / 2 * PPM
            self.lerp_pos(mx, my, dt)

    def lerp_pos(self, tx, ty, dt):
        self.x += (tx - self.x) * 5 * dt
        self.y += (ty - self.y) * 5 * dt