"""
NEURAL FIGHTS - Efeitos Visuais de Magia v5.0 CINEMATIC EDITION
================================================================================
Reescrito com foco em PRESENÇA VISUAL por elemento.
Cada elemento tem geometria, ritmo e personalidade únicos:

  FOGO    — Explosões de calor em cascata, brasas que sobem, colunas de chamas
  GELO    — Cristais que se formam devagar, explosão de estilhaços, gelo que racha
  RAIO    — Arcos elétricos em galhos, overcharge flash cegante, chain lightning
  TREVAS  — Vórtex que aspira luz, tentáculos de sombra, distorção de espaço
  LUZ     — Raios divinos, halo pulsante, explosão de judgnment com remanência
  NATUREZA — Espinhos que brotam do chão, esporos, raízes que prendem
  ARCANO  — Runas gravitando, ondas arcanas, fragmentos de éter
  CAOS    — Cores impossíveis, geometria quebrada, efeitos misturados
  SANGUE  — Gotas que espirram, névoa carmesim, círculos rituais
  VOID    — Ausência de luz, distorção visual, buraco negro
"""

import pygame
import random
import math
from typing import List, Tuple, Optional, Dict
from utils.config import PPM


ELEMENT_PALETTES = {
    "FOGO": {
        "core":   (255, 255, 220),
        "mid":    [(255, 200, 60), (255, 140, 20), (255, 90, 0)],
        "outer":  [(220, 50, 0),   (160, 25, 0),   (100, 10, 0)],
        "spark":  (255, 255, 150),
        "glow":   (255, 120, 0, 120),
    },
    "GELO": {
        "core":   (240, 255, 255),
        "mid":    [(180, 235, 255), (130, 210, 255), (90, 185, 255)],
        "outer":  [(60, 155, 230), (40, 120, 200), (20, 90, 170)],
        "spark":  (220, 248, 255),
        "glow":   (80, 180, 255, 110),
    },
    "RAIO": {
        "core":   (255, 255, 255),
        "mid":    [(255, 255, 180), (210, 210, 255), (160, 160, 255)],
        "outer":  [(120, 100, 255), (80,  70, 220), (50, 40, 180)],
        "spark":  (255, 255, 255),
        "glow":   (160, 160, 255, 130),
    },
    "TREVAS": {
        "core":   (180, 120, 230),
        "mid":    [(120, 20, 180), (90, 0, 140), (60, 0, 110)],
        "outer":  [(40, 0, 80),   (25, 0, 55),  (10, 0, 35)],
        "spark":  (210, 170, 255),
        "glow":   (100, 0, 160, 90),
    },
    "LUZ": {
        "core":   (255, 255, 255),
        "mid":    [(255, 255, 230), (255, 248, 195), (255, 235, 150)],
        "outer":  [(255, 215, 90), (255, 190, 40), (255, 165, 0)],
        "spark":  (255, 255, 255),
        "glow":   (255, 255, 180, 160),
    },
    "NATUREZA": {
        "core":   (210, 255, 210),
        "mid":    [(120, 255, 120), (80, 220, 80), (50, 190, 50)],
        "outer":  [(35, 160, 35),  (25, 130, 25), (15, 100, 15)],
        "spark":  (200, 255, 200),
        "glow":   (80, 220, 80, 100),
    },
    "ARCANO": {
        "core":   (255, 215, 255),
        "mid":    [(230, 160, 255), (210, 110, 255), (190, 80, 255)],
        "outer":  [(160, 50, 210), (130, 30, 185), (100, 15, 160)],
        "spark":  (255, 210, 255),
        "glow":   (200, 100, 255, 110),
    },
    "CAOS": {
        "core":   (255, 255, 255),
        "mid":    [(255, 90, 90),  (90, 255, 90), (90, 90, 255)],
        "outer":  [(255, 40, 220),(220, 40, 255), (40, 220, 255)],
        "spark":  (255, 255, 255),
        "glow":   (255, 100, 255, 110),
    },
    "SANGUE": {
        "core":   (255, 220, 220),
        "mid":    [(230, 60, 60),  (200, 30, 30), (170, 15, 15)],
        "outer":  [(140, 0,  0),   (110, 0,  0),  (80,  0,  0)],
        "spark":  (255, 160, 160),
        "glow":   (200, 0, 0, 110),
    },
    "VOID": {
        "core":   (120, 70, 180),
        "mid":    [(60, 10, 120),  (40, 0, 90),   (20, 0, 65)],
        "outer":  [(10, 0, 45),   (5, 0, 30),    (0, 0, 15)],
        "spark":  (160, 110, 220),
        "glow":   (50, 0, 100, 90),
    },
    "DEFAULT": {
        "core":   (255, 255, 255),
        "mid":    [(210, 210, 210), (185, 185, 185), (155, 155, 155)],
        "outer":  [(130, 130, 130),(105, 105, 105), (80, 80, 80)],
        "spark":  (255, 255, 255),
        "glow":   (200, 200, 200, 100),
    },
}


def get_element_from_skill(skill_nome: str, skill_data: dict) -> str:
    if "elemento" in skill_data:
        return skill_data["elemento"]
    n = skill_nome.lower()
    if any(w in n for w in ["fogo", "fire", "chama", "meteoro", "inferno", "brasas", "combustao"]):
        return "FOGO"
    if any(w in n for w in ["gelo", "ice", "glacial", "nevasca", "congelar", "cristal"]):
        return "GELO"
    if any(w in n for w in ["raio", "lightning", "thunder", "relampago", "eletric", "tempestade"]):
        return "RAIO"
    if any(w in n for w in ["trevas", "shadow", "dark", "sombr", "necro", "corrupcao"]):
        return "TREVAS"
    if any(w in n for w in ["luz", "light", "holy", "sagrado", "divino", "celestial", "julgamento"]):
        return "LUZ"
    if any(w in n for w in ["natureza", "nature", "veneno", "poison", "planta", "espinho", "raiz"]):
        return "NATUREZA"
    if any(w in n for w in ["arcano", "arcane", "mana", "runa", "eter"]):
        return "ARCANO"
    if any(w in n for w in ["caos", "chaos"]):
        return "CAOS"
    if any(w in n for w in ["sangue", "blood", "vampir", "drenar"]):
        return "SANGUE"
    if any(w in n for w in ["void", "vazio", "singularidade", "abismo"]):
        return "VOID"
    return "DEFAULT"


def _safe_surface(w, h):
    try:
        return pygame.Surface((max(4, int(w)), max(4, int(h))), pygame.SRCALPHA)
    except Exception:
        return None


def _draw_glow_circle(tela, cx, cy, radius, color, alpha, layers=4):
    for i in range(layers, 0, -1):
        r = int(radius * i / layers * 2.0)
        a = int(alpha * (1.0 - i / layers) * 0.55)
        s = _safe_surface(r * 2 + 4, r * 2 + 4)
        if s:
            pygame.draw.circle(s, (*color[:3], a), (r + 2, r + 2), r)
            tela.blit(s, (cx - r - 2, cy - r - 2))


def _draw_lightning_bolt(tela, x1, y1, x2, y2, color, width=2, detail=5):
    """Desenha um raio segmentado irregular entre dois pontos."""
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 4:
        return
    segs = max(3, int(dist / 14))
    px, py = -dy / dist, dx / dist
    pts = [(x1, y1)]
    for i in range(1, segs):
        t = i / segs
        bx = x1 + dx * t + px * random.uniform(-detail * (1 - abs(t - 0.5) * 2), detail * (1 - abs(t - 0.5) * 2))
        by = y1 + dy * t + py * random.uniform(-detail * (1 - abs(t - 0.5) * 2), detail * (1 - abs(t - 0.5) * 2))
        pts.append((bx, by))
    pts.append((x2, y2))
    if len(pts) < 2:
        return
    min_x = min(p[0] for p in pts) - 10
    min_y = min(p[1] for p in pts) - 10
    max_x = max(p[0] for p in pts) + 10
    max_y = max(p[1] for p in pts) + 10
    s = _safe_surface(max_x - min_x + 4, max_y - min_y + 4)
    if not s:
        return
    local = [(p[0] - min_x, p[1] - min_y) for p in pts]
    try:
        pygame.draw.lines(s, (*color[:3], 80),  False, local, width + 4)
        pygame.draw.lines(s, (*color[:3], 200), False, local, width)
        pygame.draw.lines(s, (255, 255, 255, 240), False, local, max(1, width - 1))
    except Exception:
        pass
    tela.blit(s, (int(min_x), int(min_y)))


def _draw_crystal_shard(tela, cx, cy, size, angle, color, alpha):
    pts = []
    for i in range(6):
        a = angle + i * (math.pi * 2 / 6)
        r = size if i % 2 == 0 else size * 0.55
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    s = _safe_surface(size * 3 + 4, size * 3 + 4)
    if s and len(pts) >= 3:
        local = [(p[0] - cx + size * 1.5, p[1] - cy + size * 1.5) for p in pts]
        try:
            pygame.draw.polygon(s, (*color[:3], alpha), local)
            pygame.draw.polygon(s, (255, 255, 255, min(255, alpha + 100)), local, 1)
        except Exception:
            pass
        tela.blit(s, (cx - int(size * 1.5), cy - int(size * 1.5)))


# =============================================================================
# PARTÍCULAS
# =============================================================================

class MagicParticle:
    __slots__ = ["x","y","cor","vel_x","vel_y","tamanho","tamanho_inicial",
                 "vida","vida_max","gravidade","arrasto","rotacao","rot_vel","shape","glow"]

    def __init__(self, x, y, cor, vel_x=0, vel_y=0, tamanho=5.0, vida=1.0,
                 gravidade=0, arrasto=0.97, shape="circle", glow=False):
        self.x, self.y = x, y
        self.cor = cor
        self.vel_x, self.vel_y = vel_x, vel_y
        self.tamanho = self.tamanho_inicial = tamanho
        self.vida = self.vida_max = vida
        self.gravidade = gravidade
        self.arrasto = arrasto
        self.rotacao = random.uniform(0, math.pi * 2)
        self.rot_vel = random.uniform(-7, 7)
        self.shape = shape
        self.glow = glow

    def update(self, dt):
        self.vida -= dt
        if self.vida <= 0:
            return False
        self.vel_y += self.gravidade * dt
        self.vel_x *= self.arrasto
        self.vel_y *= self.arrasto
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        self.tamanho = self.tamanho_inicial * (self.vida / self.vida_max)
        self.rotacao += self.rot_vel * dt
        return True

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        tam = cam.converter_tam(self.tamanho)
        if tam < 1:
            return
        alpha = int(255 * (self.vida / self.vida_max))
        isx, isy = int(sx), int(sy)
        itam = max(1, int(tam))

        if self.shape == "shard":
            _draw_crystal_shard(tela, isx, isy, itam, self.rotacao, self.cor, alpha)
        elif self.shape == "ember":
            s = _safe_surface(itam * 4 + 4, itam * 6 + 4)
            if s:
                cx_, cy_ = itam * 2 + 2, itam * 3 + 2
                try:
                    pygame.draw.ellipse(s, (*self.cor[:3], alpha),
                                        (cx_ - itam, cy_ - itam * 2,
                                         max(2, itam * 2), max(4, itam * 4)))
                    pygame.draw.ellipse(s, (255, 255, 220, min(255, alpha + 80)),
                                        (cx_ - max(1, itam//2), cy_ - itam,
                                         max(1, itam), max(2, itam * 2)))
                except Exception:
                    pass
                tela.blit(s, (isx - itam * 2 - 2, isy - itam * 3 - 2))
        elif self.shape == "drop":
            s = _safe_surface(itam * 3 + 4, itam * 4 + 4)
            if s:
                cx_, cy_ = itam + 2, itam + 2
                try:
                    pygame.draw.circle(s, (*self.cor[:3], alpha), (cx_, cy_), max(1, itam))
                    pts = [(cx_ - max(1, itam//3), cy_),
                           (cx_ + max(1, itam//3), cy_),
                           (cx_, cy_ + max(2, itam * 2))]
                    pygame.draw.polygon(s, (*self.cor[:3], alpha), pts)
                except Exception:
                    pass
                tela.blit(s, (isx - itam - 2, isy - itam - 2))
        elif self.shape == "wisp":
            _draw_glow_circle(tela, isx, isy, max(2, itam), self.cor, alpha, 2)
        elif self.shape == "star":
            s = _safe_surface(itam * 4 + 4, itam * 4 + 4)
            if s:
                cx_, cy_ = itam * 2 + 2, itam * 2 + 2
                star_pts = []
                for si in range(8):
                    a = self.rotacao + si * (math.pi / 4)
                    r = itam * (1.5 if si % 2 == 0 else 0.65)
                    star_pts.append((cx_ + math.cos(a) * r, cy_ + math.sin(a) * r))
                if len(star_pts) >= 3:
                    try:
                        pygame.draw.polygon(s, (*self.cor[:3], alpha), star_pts)
                    except Exception:
                        pass
                tela.blit(s, (isx - itam * 2 - 2, isy - itam * 2 - 2))
        elif self.shape == "rune":
            # Runa quadrada girando
            s = _safe_surface(itam * 3 + 4, itam * 3 + 4)
            if s:
                cx_, cy_ = itam + 2, itam + 2
                try:
                    rect_pts = []
                    for si in range(4):
                        a = self.rotacao + si * (math.pi / 2) + math.pi / 4
                        rect_pts.append((cx_ + math.cos(a) * itam, cy_ + math.sin(a) * itam))
                    if len(rect_pts) >= 3:
                        pygame.draw.polygon(s, (*self.cor[:3], 0), rect_pts)
                        pygame.draw.polygon(s, (*self.cor[:3], alpha), rect_pts, 2)
                except Exception:
                    pass
                tela.blit(s, (isx - itam - 2, isy - itam - 2))
        elif self.shape == "thorn":
            # Espinho triangular
            s = _safe_surface(itam * 3 + 4, itam * 4 + 4)
            if s:
                cx_, cy_ = itam + 2, itam * 2 + 2
                pts = [(cx_, cy_ - max(2, itam * 2)),
                       (cx_ + max(1, itam // 2), cy_),
                       (cx_ - max(1, itam // 2), cy_)]
                try:
                    pygame.draw.polygon(s, (*self.cor[:3], alpha), pts)
                except Exception:
                    pass
                tela.blit(s, (isx - itam - 2, isy - itam * 2 - 2))
        else:  # circle
            if self.glow:
                _draw_glow_circle(tela, isx, isy, max(2, itam), self.cor, alpha, 2)
            else:
                s = _safe_surface(itam * 3 + 4, itam * 3 + 4)
                if s:
                    cx_, cy_ = itam + 2, itam + 2
                    pygame.draw.circle(s, (*self.cor[:3], alpha // 3), (cx_, cy_), max(2, int(itam * 1.5)))
                    pygame.draw.circle(s, (*self.cor[:3], alpha),     (cx_, cy_), max(1, itam))
                    tela.blit(s, (isx - itam - 2, isy - itam - 2))


# =============================================================================
# RASTRO DE PROJÉTIL
# =============================================================================

class DramaticProjectileTrail:
    def __init__(self, elemento="DEFAULT"):
        self.particulas: List[MagicParticle] = []
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.spawn_timer = 0.0
        self.elemento = elemento

    def update(self, dt, x, y, velocidade=1.0):
        self.spawn_timer += dt
        rate = 0.012 / max(0.5, velocidade)
        while self.spawn_timer > rate:
            self.spawn_timer -= rate
            self._spawn(x, y)
        self.particulas = [p for p in self.particulas if p.update(dt)]

    def _spawn(self, x, y):
        el = self.elemento
        pal = self.palette
        if el == "FOGO":
            cor = random.choice(pal["mid"] + pal["outer"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-3, 3), y + random.uniform(-3, 3),
                cor, random.uniform(-25, 25), random.uniform(-90, -30),
                random.uniform(4, 9), random.uniform(0.22, 0.45),
                gravidade=-40, arrasto=0.95, shape="ember"))
            # Faísca extra
            if random.random() < 0.4:
                self.particulas.append(MagicParticle(
                    x, y, pal["spark"],
                    random.uniform(-50, 50), random.uniform(-60, 10),
                    random.uniform(1.5, 3), random.uniform(0.08, 0.18),
                    gravidade=50, arrasto=0.90))
        elif el == "GELO":
            cor = random.choice(pal["mid"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-5, 5), y + random.uniform(-5, 5),
                cor, random.uniform(-45, 45), random.uniform(-45, 45),
                random.uniform(2.5, 6), random.uniform(0.28, 0.55),
                arrasto=0.90, shape="shard"))
        elif el == "RAIO":
            self.particulas.append(MagicParticle(
                x + random.uniform(-9, 9), y + random.uniform(-9, 9),
                pal["spark"], random.uniform(-70, 70), random.uniform(-70, 70),
                random.uniform(1.5, 3.5), random.uniform(0.04, 0.12),
                arrasto=0.82, glow=True))
        elif el == "TREVAS":
            cor = random.choice(pal["mid"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-7, 7), y + random.uniform(-7, 7),
                cor, random.uniform(-18, 18), random.uniform(-18, 18),
                random.uniform(5, 11), random.uniform(0.35, 0.65),
                gravidade=12, arrasto=0.985, shape="wisp"))
        elif el == "ARCANO":
            cor = random.choice(pal["mid"])
            shape = random.choice(["rune", "star", "circle"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-6, 6), y + random.uniform(-6, 6),
                cor, random.uniform(-30, 30), random.uniform(-30, 30),
                random.uniform(3, 7), random.uniform(0.20, 0.40),
                arrasto=0.93, shape=shape, glow=True))
        elif el == "NATUREZA":
            cor = random.choice(pal["mid"])
            shape = random.choice(["thorn", "circle"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-5, 5), y + random.uniform(-5, 5),
                cor, random.uniform(-20, 20), random.uniform(-50, -10),
                random.uniform(3, 7), random.uniform(0.25, 0.50),
                gravidade=-20, arrasto=0.94, shape=shape))
        elif el == "SANGUE":
            cor = random.choice(pal["mid"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-3, 3), y + random.uniform(-3, 3),
                cor, random.uniform(-22, 22), random.uniform(-15, 35),
                random.uniform(3, 7), random.uniform(0.18, 0.38),
                gravidade=90, arrasto=0.93, shape="drop"))
        else:
            cor = random.choice(pal["mid"])
            self.particulas.append(MagicParticle(
                x + random.uniform(-6, 6), y + random.uniform(-6, 6),
                cor, random.uniform(-35, 35), random.uniform(-35, 35),
                random.uniform(3, 7), random.uniform(0.20, 0.42),
                arrasto=0.93))

    def draw(self, tela, cam):
        for p in self.particulas:
            p.draw(tela, cam)


# =============================================================================
# EXPLOSÃO DRAMÁTICA
# =============================================================================

class DramaticExplosion:
    def __init__(self, x, y, elemento="DEFAULT", tamanho=1.0, dano=0):
        self.x, self.y = x, y
        self.tamanho = tamanho
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.elemento = elemento
        self.vida = self.vida_max = 1.2
        self.particulas: List[MagicParticle] = []
        self.shockwaves = []
        self.crystals = []
        self.pillars = []
        self.lightning_bolts = []  # Para RAIO
        self.vortex_rings = []     # Para VOID / TREVAS
        self.flash_alpha = 255
        self.flash_raio = 22 * tamanho
        self.ground_crack_alpha = 0  # Para efeitos de chão
        self._spawn(tamanho, dano)

    def _spawn(self, tam, dano):
        el = self.elemento
        pal = self.palette
        # Ondas de choque base (todas as explosões)
        for i in range(4):
            self.shockwaves.append({
                "raio": 0, "raio_max": (50 + i * 30) * tam,
                "delay": i * 0.045,
                "cor": pal["mid"][i % len(pal["mid"])],
                "largura": max(1, 5 - i),
                "alpha_max": 220 - i * 25,
            })
        n = int(30 * tam + dano * 0.35)

        if el == "FOGO":
            self.vida = self.vida_max = 1.3
            self.flash_raio = 30 * tam
            # Bola de fogo principal
            for _ in range(n):
                ang = random.uniform(-math.pi * 0.8, -math.pi * 0.2) + random.uniform(-0.8, 0.8)
                vel = random.uniform(90, 280) * tam
                cor = random.choice(pal["mid"] + [pal["core"]])
                self.particulas.append(MagicParticle(self.x, self.y, cor,
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(6, 14) * tam, random.uniform(0.4, 0.8),
                    gravidade=45, arrasto=0.94, shape="ember"))
            # Faíscas radiais
            for _ in range(int(n * 0.7)):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(120, 360) * tam
                self.particulas.append(MagicParticle(self.x, self.y, pal["spark"],
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(2, 5), random.uniform(0.15, 0.35),
                    gravidade=120, arrasto=0.91, shape="ember"))
            # Pilares de chama (3)
            for i in range(3):
                ang = (i / 3) * math.pi * 2 + random.uniform(-0.3, 0.3)
                self.pillars.append({
                    "x": self.x + math.cos(ang) * 20 * tam,
                    "y": self.y + math.sin(ang) * 20 * tam,
                    "ang": -math.pi / 2, "length": random.uniform(55, 90) * tam,
                    "vida": 0.9, "vida_max": 0.9,
                    "cor": random.choice(pal["mid"]), "largura": 8,
                    "tem_offset": True,
                })

        elif el == "GELO":
            self.vida = self.vida_max = 1.4
            # Fragmentos de cristal
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(70, 210) * tam
                cor = random.choice(pal["mid"])
                self.particulas.append(MagicParticle(self.x, self.y, cor,
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(4, 11) * tam, random.uniform(0.35, 0.65),
                    gravidade=90, arrasto=0.92, shape="shard"))
            # Cristais que ficam no chão (8 direções)
            for i in range(8):
                ang = i * (math.pi * 2 / 8) + random.uniform(-0.15, 0.15)
                dist = random.uniform(22, 55) * tam
                self.crystals.append({
                    "x": self.x + math.cos(ang) * dist,
                    "y": self.y + math.sin(ang) * dist,
                    "ang": ang, "size": random.uniform(9, 20) * tam,
                    "vida": 0.9, "vida_max": 0.9,
                    "cor": random.choice(pal["mid"]),
                    "grow_speed": random.uniform(80, 140),
                    "current_size": 0,
                })
            # Coluna de gelo no centro
            self.pillars.append({
                "x": self.x, "y": self.y,
                "ang": -math.pi / 2, "length": 70 * tam,
                "vida": 1.0, "vida_max": 1.0,
                "cor": pal["core"], "largura": 12,
            })

        elif el == "RAIO":
            self.vida = self.vida_max = 0.7
            self.flash_raio = 60 * tam
            self.flash_alpha = 255
            # Partículas elétricas rápidas
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(140, 450) * tam
                self.particulas.append(MagicParticle(self.x, self.y, pal["spark"],
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(2, 5), random.uniform(0.08, 0.22),
                    arrasto=0.86, glow=True))
            # Raios em galho (6 direções)
            for i in range(6):
                ang = i * (math.pi / 3) + random.uniform(-0.2, 0.2)
                length = random.uniform(50, 110) * tam
                ex = self.x + math.cos(ang) * length
                ey = self.y + math.sin(ang) * length
                self.lightning_bolts.append({
                    "x1": self.x, "y1": self.y, "x2": ex, "y2": ey,
                    "vida": 0.35, "vida_max": 0.35,
                    "cor": random.choice(pal["mid"] + [pal["spark"]]),
                    "width": random.randint(2, 4),
                    "branches": [],
                })
                # Sub-raios (branching)
                mid_x = (self.x + ex) / 2 + random.uniform(-20, 20)
                mid_y = (self.y + ey) / 2 + random.uniform(-20, 20)
                for _ in range(2):
                    ba = ang + random.uniform(-0.8, 0.8)
                    bl = random.uniform(20, 50) * tam
                    self.lightning_bolts[-1]["branches"].append({
                        "x1": mid_x, "y1": mid_y,
                        "x2": mid_x + math.cos(ba) * bl,
                        "y2": mid_y + math.sin(ba) * bl,
                    })

        elif el == "TREVAS":
            self.vida = self.vida_max = 1.6
            self.flash_alpha = 120
            # Wisps sombrios
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(55, 175) * tam
                cor = random.choice(pal["mid"])
                self.particulas.append(MagicParticle(self.x, self.y, cor,
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(7, 16) * tam, random.uniform(0.55, 1.1),
                    arrasto=0.975, shape="wisp"))
            # Vórtex espirais
            for i in range(3):
                self.vortex_rings.append({
                    "raio": (8 + i * 18) * tam, "raio_max": (40 + i * 30) * tam,
                    "rot": random.uniform(0, math.pi * 2),
                    "vel_rot": random.choice([-1, 1]) * random.uniform(3, 6),
                    "vida": 1.2, "vida_max": 1.2,
                    "cor": pal["mid"][0],
                    "num_dots": 8 + i * 4,
                })

        elif el == "LUZ":
            self.vida = self.vida_max = 0.9
            self.flash_raio = 55 * tam
            self.flash_alpha = 255
            # Raios divinos (12 direções)
            num_rays = int(12 * tam)
            for i in range(num_rays):
                ang = i * (math.pi * 2 / num_rays) + random.uniform(-0.05, 0.05)
                self.pillars.append({
                    "x": self.x, "y": self.y, "ang": ang,
                    "length": random.uniform(50, 100) * tam,
                    "vida": 0.8, "vida_max": 0.8,
                    "cor": random.choice(pal["mid"]), "largura": 5,
                })
            # Estrelas partículas
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(110, 320) * tam
                self.particulas.append(MagicParticle(self.x, self.y, pal["spark"],
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(2, 5), random.uniform(0.18, 0.38),
                    arrasto=0.93, shape="star"))

        elif el == "NATUREZA":
            self.vida = self.vida_max = 1.5
            # Esporos que sobem
            for _ in range(n):
                ang = random.uniform(-math.pi, -math.pi * 0.1)
                vel = random.uniform(60, 200) * tam
                cor = random.choice(pal["mid"])
                self.particulas.append(MagicParticle(self.x, self.y, cor,
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(4, 9) * tam, random.uniform(0.40, 0.80),
                    gravidade=-20, arrasto=0.96, shape="circle"))
            # Espinhos radiais
            for i in range(10):
                ang = i * (math.pi * 2 / 10) + random.uniform(-0.2, 0.2)
                self.pillars.append({
                    "x": self.x, "y": self.y, "ang": ang,
                    "length": random.uniform(30, 65) * tam,
                    "vida": 1.2, "vida_max": 1.2,
                    "cor": pal["outer"][0], "largura": 4,
                })

        elif el == "ARCANO":
            self.vida = self.vida_max = 1.1
            self.flash_raio = 35 * tam
            # Fragmentos de runa
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(80, 250) * tam
                cor = random.choice(pal["mid"])
                shape = random.choice(["rune", "star"])
                self.particulas.append(MagicParticle(self.x, self.y, cor,
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(4, 10) * tam, random.uniform(0.3, 0.6),
                    arrasto=0.93, shape=shape, glow=True))
            # Anel de runas orbitando
            for i in range(6):
                ang = i * (math.pi / 3)
                dist = 35 * tam
                self.crystals.append({
                    "x": self.x + math.cos(ang) * dist,
                    "y": self.y + math.sin(ang) * dist,
                    "ang": ang, "size": 10 * tam,
                    "vida": 0.8, "vida_max": 0.8,
                    "cor": pal["spark"],
                    "grow_speed": 0, "current_size": 10 * tam,
                    "rot": ang, "vel_rot": 2.0,
                })

        elif el == "SANGUE":
            self.vida = self.vida_max = 1.2
            self.flash_alpha = 200
            # Gotas de sangue que caem
            for _ in range(n):
                ang = random.uniform(-math.pi, 0) + random.uniform(-0.5, 0.5)
                vel = random.uniform(90, 270) * tam
                self.particulas.append(MagicParticle(self.x, self.y,
                    random.choice(pal["mid"]),
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(4, 10) * tam, random.uniform(0.3, 0.6),
                    gravidade=230, arrasto=0.93, shape="drop"))
            # Círculo ritual no chão
            for i in range(8):
                ang = i * (math.pi / 4)
                dist = 40 * tam
                self.crystals.append({
                    "x": self.x + math.cos(ang) * dist,
                    "y": self.y + math.sin(ang) * dist,
                    "ang": ang, "size": 6 * tam,
                    "vida": 1.0, "vida_max": 1.0,
                    "cor": pal["outer"][0],
                    "grow_speed": 60, "current_size": 0,
                })

        elif el == "VOID":
            self.vida = self.vida_max = 1.5
            self.flash_alpha = 80
            # Wisps negros que puxam para dentro
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                dist = random.uniform(60, 120) * tam
                px = self.x + math.cos(ang) * dist
                py = self.y + math.sin(ang) * dist
                vel = random.uniform(80, 200) * tam
                cor = random.choice(pal["mid"])
                self.particulas.append(MagicParticle(px, py, cor,
                    -math.cos(ang) * vel, -math.sin(ang) * vel,
                    random.uniform(6, 14) * tam, random.uniform(0.45, 0.9),
                    arrasto=0.96, shape="wisp"))
            # Vórtex singulares
            for i in range(2):
                self.vortex_rings.append({
                    "raio": (15 + i * 20) * tam,
                    "raio_max": (15 + i * 20) * tam,
                    "rot": 0,
                    "vel_rot": (3 + i * 2) * random.choice([-1, 1]),
                    "vida": 1.5, "vida_max": 1.5,
                    "cor": pal["spark"],
                    "num_dots": 12,
                })

        else:  # DEFAULT / CAOS
            for _ in range(n):
                ang = random.uniform(0, math.pi * 2)
                vel = random.uniform(80, 290) * tam
                cor = random.choice(pal["mid"] + pal["outer"])
                self.particulas.append(MagicParticle(self.x, self.y, cor,
                    math.cos(ang) * vel, math.sin(ang) * vel,
                    random.uniform(4, 11) * tam, random.uniform(0.3, 0.65),
                    gravidade=40, arrasto=0.94))

    def update(self, dt):
        self.vida -= dt
        if self.vida <= 0:
            return False
        for w in self.shockwaves:
            if w["delay"] > 0:
                w["delay"] -= dt
            else:
                w["raio"] += 750 * dt
        self.flash_alpha = max(0, self.flash_alpha - 1100 * dt)
        self.flash_raio += 220 * dt
        # Cristais crescem
        for c in self.crystals:
            c["vida"] -= dt
            if c.get("grow_speed", 0) > 0 and c["current_size"] < c["size"]:
                c["current_size"] = min(c["size"], c["current_size"] + c["grow_speed"] * dt)
            if "vel_rot" in c:
                c["ang"] += c["vel_rot"] * dt
        self.crystals = [c for c in self.crystals if c["vida"] > 0]
        for p in self.pillars:
            p["vida"] -= dt
        self.pillars = [p for p in self.pillars if p["vida"] > 0]
        for b in self.lightning_bolts:
            b["vida"] -= dt
        self.lightning_bolts = [b for b in self.lightning_bolts if b["vida"] > 0]
        for v in self.vortex_rings:
            v["vida"] -= dt
            v["rot"] += v["vel_rot"] * dt
        self.vortex_rings = [v for v in self.vortex_rings if v["vida"] > 0]
        self.particulas = [p for p in self.particulas if p.update(dt)]
        return True

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        ratio = self.vida / self.vida_max
        isx, isy = int(sx), int(sy)

        # Flash de impacto
        if self.flash_alpha > 0:
            fr = max(4, int(cam.converter_tam(self.flash_raio)))
            _draw_glow_circle(tela, isx, isy, fr,
                              self.palette["core"], int(self.flash_alpha * ratio), layers=3)

        # Ondas de choque
        for w in self.shockwaves:
            if w["delay"] <= 0 and 0 < w["raio"] < w["raio_max"]:
                r = max(2, int(cam.converter_tam(w["raio"])))
                prog = w["raio"] / w["raio_max"]
                alpha = int(w.get("alpha_max", 200) * (1 - prog) * ratio)
                thick = max(1, int(w["largura"] * (1 - prog * 0.5)))
                s = _safe_surface(r * 2 + 8, r * 2 + 8)
                if s:
                    pygame.draw.circle(s, (*w["cor"], alpha), (r + 4, r + 4), r, thick)
                    tela.blit(s, (isx - r - 4, isy - r - 4))

        # Raios elétricos
        for b in self.lightning_bolts:
            br = b["vida"] / b["vida_max"]
            bx1, by1 = cam.converter(b["x1"], b["y1"])
            bx2, by2 = cam.converter(b["x2"], b["y2"])
            _draw_lightning_bolt(tela, bx1, by1, bx2, by2, b["cor"],
                                 width=b["width"], detail=8)
            for branch in b.get("branches", []):
                brx1, bry1 = cam.converter(branch["x1"], branch["y1"])
                brx2, bry2 = cam.converter(branch["x2"], branch["y2"])
                _draw_lightning_bolt(tela, brx1, bry1, brx2, bry2,
                                     b["cor"], width=max(1, b["width"] - 1), detail=5)

        # Vórtex (Trevas/Void)
        for v in self.vortex_rings:
            vr = v["vida"] / v["vida_max"]
            r_px = max(2, int(cam.converter_tam(v["raio"])))
            for di in range(v["num_dots"]):
                ang = v["rot"] + di * (math.pi * 2 / v["num_dots"])
                dot_x = isx + math.cos(ang) * r_px
                dot_y = isy + math.sin(ang) * r_px
                dot_r = max(2, int(cam.converter_tam(4)))
                _draw_glow_circle(tela, int(dot_x), int(dot_y), dot_r,
                                  v["cor"], int(180 * vr * ratio), 1)

        # Cristais / círculos rituais
        for c in self.crystals:
            csize = c.get("current_size", c["size"])
            if csize < 1:
                continue
            cx, cy = cam.converter(c["x"], c["y"])
            cr = c["vida"] / c["vida_max"]
            size = max(2, int(cam.converter_tam(csize)))
            _draw_crystal_shard(tela, int(cx), int(cy), size,
                                c["ang"], c["cor"], int(200 * cr * ratio))

        # Pilares / raios
        for p in self.pillars:
            pr = p["vida"] / p["vida_max"]
            length = int(cam.converter_tam(p["length"]) * pr)
            if length < 2:
                continue
            if p.get("tem_offset", False):
                # Pilar com origem própria em pixels
                px_s, py_s = cam.converter(p["x"], p["y"])
            else:
                px_s, py_s = sx, sy
            ex = px_s + math.cos(p["ang"]) * length
            ey = py_s + math.sin(p["ang"]) * length
            alpha = int(230 * pr * ratio)
            larg = max(1, int(cam.converter_tam(p["largura"])))
            s = _safe_surface(int(abs(ex - px_s)) + larg * 4 + 10, int(abs(ey - py_s)) + larg * 4 + 10)
            if s:
                ox, oy = min(px_s, ex) - larg * 2 - 4, min(py_s, ey) - larg * 2 - 4
                try:
                    pygame.draw.line(s, (*p["cor"], alpha // 3),
                                     (int(px_s - ox), int(py_s - oy)), (int(ex - ox), int(ey - oy)), larg * 3)
                    pygame.draw.line(s, (*p["cor"], alpha),
                                     (int(px_s - ox), int(py_s - oy)), (int(ex - ox), int(ey - oy)), larg)
                    pygame.draw.line(s, (255, 255, 255, alpha),
                                     (int(px_s - ox), int(py_s - oy)), (int(ex - ox), int(ey - oy)),
                                     max(1, larg - 2))
                except Exception:
                    pass
                tela.blit(s, (int(ox), int(oy)))

        # Partículas
        for p in self.particulas:
            p.draw(tela, cam)


# =============================================================================
# BEAM (FEIXE)
# =============================================================================

class DramaticBeam:
    def __init__(self, x1, y1, x2, y2, elemento="DEFAULT", largura=8):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.elemento = elemento
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.largura = largura
        self.vida = self.vida_max = 0.6
        self.pulse_timer = 0.0
        self.particulas: List[MagicParticle] = []
        self._spawn_particles()

    def _gerar_segments(self):
        segs = [(self.x1, self.y1)]
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        dist = math.hypot(dx, dy)
        if dist < 10:
            segs.append((self.x2, self.y2))
            return segs
        n = max(5, int(dist / 18))
        px, py = -dy / dist, dx / dist
        for i in range(1, n):
            t = i / n
            jitter = 14 * math.sin(t * math.pi)
            bx = self.x1 + dx * t + px * random.uniform(-jitter, jitter)
            by = self.y1 + dy * t + py * random.uniform(-jitter, jitter)
            segs.append((bx, by))
        segs.append((self.x2, self.y2))
        return segs

    def _spawn_particles(self):
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        dist = math.hypot(dx, dy)
        el = self.elemento
        pal = self.palette
        n = max(4, int(dist / 22))
        for _ in range(n):
            t = random.random()
            px = self.x1 + dx * t + random.uniform(-6, 6)
            py = self.y1 + dy * t + random.uniform(-6, 6)
            cor = random.choice(pal["mid"])
            shape = "ember" if el == "FOGO" else "shard" if el == "GELO" else "rune" if el == "ARCANO" else "circle"
            self.particulas.append(MagicParticle(px, py, cor,
                random.uniform(-30, 30), random.uniform(-30, 30),
                random.uniform(3, 7), random.uniform(0.12, 0.30),
                arrasto=0.90, shape=shape))

    def update(self, dt):
        self.vida -= dt
        if self.vida <= 0:
            return False
        self.pulse_timer += dt * 18
        if random.random() < dt * 18:
            self._spawn_particles()
        self.particulas = [p for p in self.particulas if p.update(dt)]
        return True

    def draw(self, tela, cam):
        segs = self._gerar_segments()
        if len(segs) < 2:
            return
        pts = [cam.converter(x, y) for x, y in segs]
        ratio = self.vida / self.vida_max
        pulse = 0.75 + 0.25 * abs(math.sin(self.pulse_timer))
        min_x = min(p[0] for p in pts) - 25
        min_y = min(p[1] for p in pts) - 25
        max_x = max(p[0] for p in pts) + 25
        max_y = max(p[1] for p in pts) + 25
        w, h = max(4, int(max_x - min_x)), max(4, int(max_y - min_y))
        s = _safe_surface(w, h)
        if s:
            local = [(p[0] - min_x, p[1] - min_y) for p in pts]
            gw = max(3, int((self.largura + 12) * pulse))
            try:
                pygame.draw.lines(s, (*self.palette["outer"][0], int(70 * ratio)), False, local, gw)
                pygame.draw.lines(s, (*random.choice(self.palette["mid"]), int(210 * ratio)),
                                  False, local, max(2, int(self.largura * pulse)))
                pygame.draw.lines(s, (255, 255, 255, int(245 * ratio)), False, local,
                                  max(1, int(self.largura * 0.28)))
            except Exception:
                pass
            tela.blit(s, (int(min_x), int(min_y)))
        for p in self.particulas:
            p.draw(tela, cam)


# =============================================================================
# AURA
# =============================================================================

class DramaticAura:
    def __init__(self, x, y, raio, elemento="DEFAULT", intensidade=1.0):
        self.x, self.y = x, y
        self.raio = raio
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.elemento = elemento
        self.vida = self.vida_max = 2.0
        self.timer = 0.0
        self.intensidade = intensidade
        self.aneis = [
            {"raio": raio * (0.45 + i * 0.32), "fase": random.uniform(0, math.pi * 2),
             "vel": random.uniform(1.8, 4.0), "cor": random.choice(self.palette["mid"])}
            for i in range(3)
        ]
        self.orbitantes = [
            {"ang": random.uniform(0, math.pi * 2),
             "dist": random.uniform(raio * 0.45, raio * 1.25),
             "vel": random.uniform(1.2, 3.2) * random.choice([-1, 1]),
             "cor": random.choice(self.palette["mid"]),
             "tam": random.uniform(3.5, 7.0) * intensidade,
             "shape": random.choice(["circle", "star", "rune"])}
            for _ in range(int(12 * intensidade))
        ]
        # Raios de energia periódicos (RAIO / LUZ)
        self.energy_lines = []
        self.energy_timer = 0.0

    def update(self, dt, x=None, y=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        self.vida -= dt
        self.timer += dt
        for a in self.aneis:
            a["fase"] += a["vel"] * dt
        for o in self.orbitantes:
            o["ang"] += o["vel"] * dt
        # Raios elétricos esporádicos
        if self.elemento in ("RAIO", "ARCANO"):
            self.energy_timer += dt
            if self.energy_timer > 0.15:
                self.energy_timer = 0.0
                if random.random() < 0.5:
                    ang = random.uniform(0, math.pi * 2)
                    self.energy_lines.append({
                        "ang": ang, "length": self.raio * 0.8,
                        "vida": 0.1, "vida_max": 0.1,
                        "cor": self.palette["spark"],
                    })
        new_energy_lines = []
        for e in self.energy_lines:
            e["vida"] -= dt
            if e["vida"] > 0:
                new_energy_lines.append(e)
        self.energy_lines = new_energy_lines
        return self.vida > 0

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        ratio = self.vida / self.vida_max
        for a in self.aneis:
            pulse = 0.8 + 0.2 * math.sin(a["fase"])
            r = max(2, int(cam.converter_tam(a["raio"] * pulse)))
            alpha = int(150 * ratio * pulse)
            s = _safe_surface(r * 2 + 8, r * 2 + 8)
            if s:
                pygame.draw.circle(s, (*a["cor"], alpha), (r + 4, r + 4), r, 2)
                tela.blit(s, (int(sx) - r - 4, int(sy) - r - 4))
        for o in self.orbitantes:
            px = self.x + math.cos(o["ang"]) * o["dist"]
            py = self.y + math.sin(o["ang"]) * o["dist"]
            spx, spy = cam.converter(px, py)
            tam = max(1, int(cam.converter_tam(o["tam"])))
            if o["shape"] == "star":
                _draw_crystal_shard(tela, int(spx), int(spy), tam, o["ang"], o["cor"], int(180 * ratio))
            elif o["shape"] == "rune":
                s = _safe_surface(tam * 2 + 4, tam * 2 + 4)
                if s:
                    try:
                        rpts = [(tam + 2 + math.cos(o["ang"] + i * math.pi / 2) * tam,
                                 tam + 2 + math.sin(o["ang"] + i * math.pi / 2) * tam)
                                for i in range(4)]
                        pygame.draw.polygon(s, (*o["cor"], 0), rpts)
                        pygame.draw.polygon(s, (*o["cor"], int(180 * ratio)), rpts, 2)
                    except Exception:
                        pass
                    tela.blit(s, (int(spx) - tam - 2, int(spy) - tam - 2))
            else:
                _draw_glow_circle(tela, int(spx), int(spy), tam, o["cor"], int(180 * ratio), 1)
        for e in self.energy_lines:
            er = e["vida"] / e["vida_max"]
            length = int(cam.converter_tam(e["length"]))
            ex = sx + math.cos(e["ang"]) * length
            ey = sy + math.sin(e["ang"]) * length
            _draw_lightning_bolt(tela, int(sx), int(sy), int(ex), int(ey),
                                 e["cor"], width=2, detail=5)


# =============================================================================
# CHARGEUP (CONCENTRAÇÃO)
# =============================================================================

class MagicCastChargeup:
    def __init__(self, x, y, elemento="DEFAULT", duracao=0.6, intensidade=1.0):
        self.x, self.y = x, y
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.elemento = elemento
        self.vida = self.vida_max = max(0.2, duracao)
        self.intensidade = intensidade
        self.particulas: List[MagicParticle] = []
        self.timer = 0.0
        self.anel_raio = 70 * intensidade
        self.rings = []
        # Pré-gera alguns anéis de carga
        for i in range(3):
            self.rings.append({
                "raio": (70 + i * 25) * intensidade,
                "fase": random.uniform(0, math.pi * 2),
                "vel": (2.5 + i * 1.2) * random.choice([-1, 1]),
                "cor": random.choice(self.palette["mid"]),
            })

    def update(self, dt, x=None, y=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        self.vida -= dt
        if self.vida <= 0:
            return False
        self.timer += dt
        prog = 1 - self.vida / self.vida_max  # 0→1 ao longo do chargeup
        self.anel_raio = max(4, (70 * self.intensidade) * (1 - prog * 0.75))
        for ring in self.rings:
            ring["fase"] += ring["vel"] * dt
        # Partículas aspiradas para o centro (quantidade aumenta com prog)
        spawn_rate = 0.018 / max(0.3, self.intensidade * (0.5 + prog))
        self.timer_spawn = getattr(self, "timer_spawn", 0) + dt
        while self.timer_spawn > spawn_rate:
            self.timer_spawn -= spawn_rate
            self._spawn_particle(prog)
        self.particulas = [p for p in self.particulas if p.update(dt)]
        return True

    def _spawn_particle(self, prog):
        spread = 90 * self.intensidade * (1 - prog * 0.6)
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(20, spread)
        px = self.x + math.cos(ang) * dist
        py = self.y + math.sin(ang) * dist
        # Partícula voa em direção ao centro com velocidade normalizada
        dx = self.x - px
        dy = self.y - py
        d = math.hypot(dx, dy)
        spd = random.uniform(120, 240) * self.intensidade * (0.5 + prog)
        if d > 0:
            vx = (dx / d) * spd
            vy = (dy / d) * spd
        else:
            vx, vy = 0.0, 0.0
        cor = random.choice(self.palette["mid"])
        el = self.elemento
        shape = "ember" if el == "FOGO" else "shard" if el == "GELO" else "rune" if el == "ARCANO" else "circle"
        self.particulas.append(MagicParticle(px, py, cor, vx, vy,
            random.uniform(2.5, 6) * self.intensidade,
            random.uniform(0.08, 0.25), arrasto=0.94, shape=shape, glow=(el in ("RAIO", "LUZ"))))

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        ratio = self.vida / self.vida_max
        prog = 1 - ratio
        isx, isy = int(sx), int(sy)
        # Anéis orbitando que contraem
        for ring in self.rings:
            rr = max(2, int(cam.converter_tam(self.anel_raio * (0.7 + 0.3 * abs(math.sin(ring["fase"]))))))
            alpha = int(120 * ratio * (0.6 + 0.4 * abs(math.sin(ring["fase"]))))
            s = _safe_surface(rr * 2 + 8, rr * 2 + 8)
            if s:
                pygame.draw.circle(s, (*ring["cor"], alpha), (rr + 4, rr + 4), rr, 2)
                tela.blit(s, (isx - rr - 4, isy - rr - 4))
        # Core crescendo no centro
        core_r = max(2, int(cam.converter_tam(10 * prog * self.intensidade)))
        _draw_glow_circle(tela, isx, isy, core_r, self.palette["core"], int(220 * prog), layers=3)
        # Partículas
        for p in self.particulas:
            p.draw(tela, cam)


# =============================================================================
# IMPACTO ELEMENTAL
# =============================================================================

class ElementalImpactBurst:
    def __init__(self, x, y, elemento="DEFAULT", intensidade=1.0):
        self.x, self.y = x, y
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.elemento = elemento
        self.vida = self.vida_max = 0.45
        self.particulas: List[MagicParticle] = []
        self.rings = []
        self.flash = 255
        self._build(elemento, intensidade)

    def _build(self, el, i):
        pal = self.palette
        n = int(18 * i)
        shape = "shard" if el == "GELO" else "ember" if el == "FOGO" else "star" if el == "LUZ" else "circle"
        for _ in range(n):
            ang = random.uniform(0, math.pi * 2)
            vel = random.uniform(110, 320) * i
            cor = random.choice(pal["mid"])
            self.particulas.append(MagicParticle(self.x, self.y, cor,
                math.cos(ang) * vel, math.sin(ang) * vel,
                random.uniform(3, 9) * i, random.uniform(0.14, 0.35),
                gravidade=60 if el == "SANGUE" else 0, arrasto=0.91, shape=shape))
        for ri in range(3):
            self.rings.append({
                "raio": 0, "raio_max": (28 + ri * 22) * i,
                "delay": ri * 0.025,
                "cor": random.choice(pal["mid"]),
                "alpha_max": 200 - ri * 30,
            })

    def update(self, dt):
        self.vida -= dt
        if self.vida <= 0:
            return False
        for r in self.rings:
            if r["delay"] > 0:
                r["delay"] -= dt
            else:
                r["raio"] += 520 * dt
        self.flash = max(0, self.flash - 1200 * dt)
        self.particulas = [p for p in self.particulas if p.update(dt)]
        return True

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        ratio = self.vida / self.vida_max
        if self.flash > 0:
            _draw_glow_circle(tela, int(sx), int(sy), 22,
                              self.palette["core"], int(self.flash * ratio), layers=2)
        for r in self.rings:
            if r["delay"] <= 0 and 0 < r["raio"] < r["raio_max"]:
                rr = max(1, int(cam.converter_tam(r["raio"])))
                prog = r["raio"] / r["raio_max"]
                a = int(r.get("alpha_max", 180) * (1 - prog) * ratio)
                s = _safe_surface(rr * 2 + 6, rr * 2 + 6)
                if s:
                    pygame.draw.circle(s, (*r["cor"], a), (rr + 3, rr + 3), rr, 2)
                    tela.blit(s, (int(sx) - rr - 3, int(sy) - rr - 3))
        for p in self.particulas:
            p.draw(tela, cam)


# =============================================================================
# INVOCAÇÃO
# =============================================================================

class DramaticSummon:
    def __init__(self, x, y, elemento="DEFAULT"):
        self.x, self.y = x, y
        self.palette = ELEMENT_PALETTES.get(elemento, ELEMENT_PALETTES["DEFAULT"])
        self.elemento = elemento
        self.vida = self.vida_max = 1.8
        self.circulo_raio = 0
        self.circulo_raio_max = 60
        self.rot = 0.0
        self.particulas: List[MagicParticle] = []
        self.pilares = [
            {"ang": i * (math.pi / 3), "altura": 0, "max": random.uniform(65, 110),
             "delay": i * 0.09, "cor": random.choice(self.palette["mid"]),
             "largura": random.randint(5, 10)}
            for i in range(6)
        ]
        self.lightning_spawns = []
        self.ln_timer = 0.0

    def update(self, dt):
        self.vida -= dt
        if self.vida <= 0:
            return False
        prog = 1 - self.vida / self.vida_max
        if prog < 0.35:
            self.circulo_raio = self.circulo_raio_max * (prog / 0.35)
        self.rot += dt * 2.8
        for p in self.pilares:
            if p["delay"] > 0:
                p["delay"] -= dt
            elif prog < 0.75:
                p["altura"] = min(p["max"], p["altura"] + 190 * dt)
        if random.random() < dt * 30:
            ang = random.uniform(0, math.pi * 2)
            dist = random.uniform(8, self.circulo_raio)
            cor = random.choice(self.palette["mid"])
            self.particulas.append(MagicParticle(
                self.x + math.cos(ang) * dist,
                self.y + math.sin(ang) * dist,
                cor, random.uniform(-10, 10), random.uniform(-90, -45),
                random.uniform(2, 6), 0.5, arrasto=0.97, glow=True))
        self.particulas = [p for p in self.particulas if p.update(dt)]
        return True

    def draw(self, tela, cam):
        sx, sy = cam.converter(self.x, self.y)
        ratio = self.vida / self.vida_max
        r = max(3, int(cam.converter_tam(self.circulo_raio)))
        if r > 3:
            alpha = int(210 * ratio)
            s = _safe_surface(r * 2 + 10, r * 2 + 10)
            if s:
                pygame.draw.circle(s, (*self.palette["mid"][0], alpha), (r + 5, r + 5), r, 3)
                for i in range(16):
                    a = self.rot + i * (math.pi / 8)
                    ir = r * 0.65
                    x1, y1 = r + 5 + math.cos(a) * ir, r + 5 + math.sin(a) * ir
                    x2, y2 = r + 5 + math.cos(a) * r, r + 5 + math.sin(a) * r
                    try:
                        pygame.draw.line(s, (*self.palette["spark"], alpha),
                                         (int(x1), int(y1)), (int(x2), int(y2)), 2)
                    except Exception:
                        pass
                tela.blit(s, (int(sx) - r - 5, int(sy) - r - 5))
        for p in self.pilares:
            if p["delay"] <= 0 and p["altura"] > 0:
                px = sx + math.cos(p["ang"]) * r * 0.85
                py = sy + math.sin(p["ang"]) * r * 0.85
                h = max(1, int(cam.converter_tam(p["altura"])))
                lw = max(3, int(cam.converter_tam(p["largura"])))
                alpha = int(190 * ratio)
                s = _safe_surface(lw * 4 + 4, h + 6)
                if s:
                    pygame.draw.rect(s, (*p["cor"], alpha), (0, 0, lw * 4, h))
                    pygame.draw.rect(s, (255, 255, 255, alpha // 2), (lw, 0, lw * 2, h))
                    tela.blit(s, (int(px) - lw, int(py) - h))
        for p in self.particulas:
            p.draw(tela, cam)


# =============================================================================
# MANAGER
# =============================================================================

class MagicVFXManager:
    _instance = None

    def __init__(self):
        self.explosions: List[DramaticExplosion] = []
        self.beams: List[DramaticBeam] = []
        self.auras: List[DramaticAura] = []
        self.summons: List[DramaticSummon] = []
        self.chargeups: List[MagicCastChargeup] = []
        self.impact_bursts: List[ElementalImpactBurst] = []
        self.trails: Dict[int, DramaticProjectileTrail] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MagicVFXManager()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def spawn_explosion(self, x, y, elemento="DEFAULT", tamanho=1.0, dano=0):
        self.explosions.append(DramaticExplosion(x, y, elemento, tamanho, dano))

    def spawn_beam(self, x1, y1, x2, y2, elemento="DEFAULT", largura=8):
        self.beams.append(DramaticBeam(x1, y1, x2, y2, elemento, largura))

    def spawn_aura(self, x, y, raio, elemento="DEFAULT", intensidade=1.0):
        self.auras.append(DramaticAura(x, y, raio, elemento, intensidade))

    def spawn_summon(self, x, y, elemento="DEFAULT"):
        self.summons.append(DramaticSummon(x, y, elemento))

    def spawn_chargeup(self, x, y, elemento="DEFAULT", duracao=0.5, intensidade=1.0):
        self.chargeups.append(MagicCastChargeup(x, y, elemento, duracao, intensidade))

    def spawn_impact_burst(self, x, y, elemento="DEFAULT", intensidade=1.0):
        self.impact_bursts.append(ElementalImpactBurst(x, y, elemento, intensidade))

    def get_or_create_trail(self, proj_id, elemento="DEFAULT"):
        if proj_id not in self.trails:
            self.trails[proj_id] = DramaticProjectileTrail(elemento)
        return self.trails[proj_id]

    def remove_trail(self, proj_id):
        if proj_id in self.trails:
            del self.trails[proj_id]

    def update(self, dt):
        self.explosions    = [e for e in self.explosions    if e.update(dt)]
        self.beams         = [b for b in self.beams         if b.update(dt)]
        self.auras         = [a for a in self.auras         if a.update(dt)]
        self.summons       = [s for s in self.summons       if s.update(dt)]
        self.chargeups     = [c for c in self.chargeups     if c.update(dt)]
        self.impact_bursts = [i for i in self.impact_bursts if i.update(dt)]
        # BUG FIX: Avançar partículas residuais nos trails para que desapareçam naturalmente.
        # Trails órfãos (projétil morreu) não recebem update() via simulacao,
        # então suas partículas ficavam congeladas no espaço indefinidamente.
        for trail in self.trails.values():
            trail.particulas = [p for p in trail.particulas if p.update(dt)]

    def draw(self, tela, cam):
        for c in self.chargeups:     c.draw(tela, cam)
        for t in self.trails.values(): t.draw(tela, cam)
        for a in self.auras:         a.draw(tela, cam)
        for s in self.summons:       s.draw(tela, cam)
        for b in self.beams:         b.draw(tela, cam)
        for i in self.impact_bursts: i.draw(tela, cam)
        for e in self.explosions:    e.draw(tela, cam)
