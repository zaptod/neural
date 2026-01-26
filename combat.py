# combat.py
import math
import random
from config import *
from skills import get_skill_data

class Projetil:
    """Projétil genérico que carrega dados do SKILL_DB"""
    def __init__(self, nome_skill, x, y, angulo, dono):
        self.nome = nome_skill
        data = get_skill_data(nome_skill)
        
        self.x = x
        self.y = y
        self.angulo = angulo
        self.dono = dono
        
        # Atributos carregados
        self.tipo_efeito = data.get("efeito", "NORMAL")
        self.vel = data.get("velocidade", 10.0)
        self.raio = data.get("raio", 0.3)
        self.dano = data.get("dano", 10.0)
        self.cor = data.get("cor", BRANCO)
        self.vida = data.get("vida", 2.0)
        
        # Multi-shot support
        self.multi_shot = data.get("multi_shot", 1)
        
        self.ativo = True
        self.trail = []  # Rastro visual

    def atualizar(self, dt):
        rad = math.radians(self.angulo)
        self.x += math.cos(rad) * self.vel * dt
        self.y += math.sin(rad) * self.vel * dt
        
        # Salva posição para trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
        
        self.vida -= dt
        if self.vida <= 0:
            self.ativo = False


class AreaEffect:
    """Efeito de área (explosões, nuvens, etc)"""
    def __init__(self, nome_skill, x, y, dono):
        self.nome = nome_skill
        data = get_skill_data(nome_skill)
        
        self.x = x
        self.y = y
        self.dono = dono
        
        self.raio = data.get("raio_area", 2.0)
        self.dano = data.get("dano", 10.0)
        self.cor = data.get("cor", BRANCO)
        self.duracao = data.get("duracao", 0.5)
        self.tipo_efeito = data.get("efeito", "NORMAL")
        
        self.vida = self.duracao
        self.ativo = True
        self.alvos_atingidos = set()  # Evita hit múltiplo
        
        # Animação
        self.raio_atual = 0.0
        self.alpha = 255

    def atualizar(self, dt):
        self.vida -= dt
        
        # Expansão do raio
        if self.raio_atual < self.raio:
            self.raio_atual += self.raio * 3 * dt
        
        # Fade out
        self.alpha = int(255 * (self.vida / self.duracao))
        
        if self.vida <= 0:
            self.ativo = False


class Beam:
    """Raio instantâneo (relâmpagos, lasers)"""
    def __init__(self, nome_skill, x_origem, y_origem, x_destino, y_destino, dono):
        self.nome = nome_skill
        data = get_skill_data(nome_skill)
        
        self.x1, self.y1 = x_origem, y_origem
        self.x2, self.y2 = x_destino, y_destino
        self.dono = dono
        
        self.dano = data.get("dano", 15.0)
        self.cor = data.get("cor", (255, 255, 100))
        self.tipo_efeito = data.get("efeito", "ATORDOAR")
        
        self.vida = 0.15  # Curta duração visual
        self.ativo = True
        self.hit_aplicado = False
        
        # Efeito visual
        self.largura = 8
        self.segments = self._gerar_zigzag()

    def _gerar_zigzag(self):
        """Gera pontos de zigzag para efeito de raio"""
        segments = [(self.x1, self.y1)]
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        dist = math.hypot(dx, dy)
        
        if dist == 0:
            return segments
        
        num_segs = int(dist / 0.5) + 1
        for i in range(1, num_segs):
            t = i / num_segs
            px = self.x1 + dx * t + random.uniform(-0.3, 0.3)
            py = self.y1 + dy * t + random.uniform(-0.3, 0.3)
            segments.append((px, py))
        
        segments.append((self.x2, self.y2))
        return segments

    def atualizar(self, dt):
        self.vida -= dt
        self.largura = max(1, int(8 * (self.vida / 0.15)))
        if self.vida <= 0:
            self.ativo = False


class Buff:
    """Efeito de buff/debuff em um lutador"""
    def __init__(self, nome_skill, alvo):
        self.nome = nome_skill
        data = get_skill_data(nome_skill)
        
        self.alvo = alvo
        self.duracao = data.get("duracao", 5.0)
        self.vida = self.duracao
        self.cor = data.get("cor", BRANCO)
        
        # Efeitos possíveis
        self.escudo = data.get("escudo", 0)
        self.escudo_atual = self.escudo
        self.buff_dano = data.get("buff_dano", 1.0)
        self.buff_velocidade = data.get("buff_velocidade", 1.0)
        self.refletir = data.get("refletir", 0)
        self.cura_por_segundo = data.get("regen", 0)
        
        self.ativo = True

    def atualizar(self, dt):
        self.vida -= dt
        
        # Cura contínua
        if self.cura_por_segundo > 0:
            self.alvo.vida = min(self.alvo.vida_max, self.alvo.vida + self.cura_por_segundo * dt)
        
        if self.vida <= 0:
            self.ativo = False
    
    def absorver_dano(self, dano):
        """Tenta absorver dano com escudo, retorna dano restante"""
        if self.escudo_atual <= 0:
            return dano
        
        if dano <= self.escudo_atual:
            self.escudo_atual -= dano
            return 0
        else:
            restante = dano - self.escudo_atual
            self.escudo_atual = 0
            return restante


class DotEffect:
    """Damage over Time (veneno, sangramento, queimadura)"""
    def __init__(self, tipo, alvo, dano_por_tick, duracao, cor):
        self.tipo = tipo
        self.alvo = alvo
        self.dano_por_tick = dano_por_tick
        self.duracao = duracao
        self.vida = duracao
        self.cor = cor
        
        self.tick_timer = 0.0
        self.tick_interval = 0.5
        self.ativo = True

    def atualizar(self, dt):
        self.vida -= dt
        self.tick_timer += dt
        
        if self.tick_timer >= self.tick_interval:
            self.tick_timer = 0
            # Aplica dano
            if not self.alvo.morto:
                self.alvo.vida -= self.dano_por_tick
                if self.alvo.vida <= 0:
                    self.alvo.morrer()
        
        if self.vida <= 0:
            self.ativo = False