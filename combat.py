# combat.py
import math
import random
from config import *
from skills import get_skill_data


class ArmaProjetil:
    """Projétil de arma física (facas, flechas, etc) - diferente de skills"""
    def __init__(self, tipo, x, y, angulo, dono, dano, velocidade=15.0, tamanho=0.3, cor=(200, 200, 200)):
        self.tipo = tipo  # "faca", "flecha", "chakram", "shuriken"
        self.x = x
        self.y = y
        self.angulo = angulo
        self.angulo_visual = angulo  # Para rotação visual
        self.dono = dono
        
        self.dano = dano
        self.vel = velocidade
        self.raio = tamanho  # Raio de colisão em metros
        self.cor = cor
        
        self.vida = 3.0  # Segundos até desaparecer
        self.ativo = True
        self.trail = []
        
        # Rotação visual (shurikens giram rápido)
        self.rotacao_vel = 0
        if tipo in ["shuriken", "chakram"]:
            self.rotacao_vel = 720  # graus/segundo
        elif tipo == "faca":
            self.rotacao_vel = 360
    
    def atualizar(self, dt):
        # Movimento
        rad = math.radians(self.angulo)
        self.x += math.cos(rad) * self.vel * dt
        self.y += math.sin(rad) * self.vel * dt
        
        # Rotação visual
        self.angulo_visual += self.rotacao_vel * dt
        
        # Trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        
        # Vida
        self.vida -= dt
        if self.vida <= 0:
            self.ativo = False
    
    def colidir(self, alvo):
        """Verifica colisão com um lutador"""
        if alvo == self.dono:
            return False
        if alvo.morto:
            return False
        
        dist = math.hypot(alvo.pos[0] - self.x, alvo.pos[1] - self.y)
        raio_alvo = alvo.dados.tamanho / 2
        
        return dist < (self.raio + raio_alvo)


class FlechaProjetil(ArmaProjetil):
    """Flecha com gravidade opcional"""
    def __init__(self, x, y, angulo, dono, dano, forca=1.0, cor=(139, 90, 43)):
        super().__init__("flecha", x, y, angulo, dono, dano, 
                        velocidade=12.0 + forca * 8.0,  # Mais força = mais rápido
                        tamanho=0.2, cor=cor)
        self.forca = forca
        self.gravidade = 3.0  # Queda suave
        self.vel_y_extra = 0  # Velocidade vertical adicional pela gravidade
        self.perfurante = forca > 0.8  # Flechas fortes perfuram
    
    def atualizar(self, dt):
        # Movimento base
        rad = math.radians(self.angulo)
        self.x += math.cos(rad) * self.vel * dt
        
        # Gravidade afeta Y
        self.vel_y_extra += self.gravidade * dt
        self.y += math.sin(rad) * self.vel * dt + self.vel_y_extra * dt
        
        # Ajusta ângulo visual para acompanhar trajetória
        vel_x = math.cos(rad) * self.vel
        vel_y = math.sin(rad) * self.vel + self.vel_y_extra
        self.angulo_visual = math.degrees(math.atan2(vel_y, vel_x))
        
        # Trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        
        self.vida -= dt
        if self.vida <= 0:
            self.ativo = False


class OrbeMagico:
    """Orbe mágico que flutua ao redor do mago e depois dispara no inimigo"""
    def __init__(self, x, y, dono, dano, indice=0, total=1, cor=(100, 100, 255)):
        self.x = x
        self.y = y
        self.dono = dono
        self.dano = dano
        self.cor = cor
        self.raio = 0.25  # Raio de colisão
        self.raio_visual = 0.15  # Tamanho visual inicial
        
        # Índice para posicionamento orbital
        self.indice = indice
        self.total = total
        
        # Estados: "orbitando", "carregando", "disparando"
        self.estado = "orbitando"
        
        # Órbita
        self.angulo_orbital = (360.0 / total) * indice
        self.vel_orbital = 180.0  # graus/segundo
        self.dist_orbital = 0.8  # distância do dono
        
        # Carregamento
        self.tempo_carga = 0.0
        self.carga_max = 0.6  # tempo para carregar
        
        # Disparo
        self.angulo_disparo = 0
        self.vel_disparo = 0
        self.vel_max = 18.0
        self.alvo = None
        
        # Visual
        self.pulso = 0.0
        self.particulas = []
        self.trail = []
        
        self.vida = 8.0  # Tempo máximo de existência
        self.ativo = True
    
    def iniciar_carga(self, alvo):
        """Começa a carregar para disparar"""
        if self.estado == "orbitando":
            self.estado = "carregando"
            self.tempo_carga = 0.0
            self.alvo = alvo
    
    def atualizar(self, dt):
        self.vida -= dt
        self.pulso += dt * 5.0
        
        if self.vida <= 0:
            self.ativo = False
            return
        
        if self.estado == "orbitando":
            self._atualizar_orbita(dt)
        elif self.estado == "carregando":
            self._atualizar_carga(dt)
        elif self.estado == "disparando":
            self._atualizar_disparo(dt)
        
        # Partículas mágicas
        if random.random() < 0.3:
            self.particulas.append({
                'x': self.x + random.uniform(-0.1, 0.1),
                'y': self.y + random.uniform(-0.1, 0.1),
                'vida': 0.3,
                'cor': self.cor
            })
        
        # Atualiza partículas
        for p in self.particulas:
            p['vida'] -= dt
            p['y'] -= dt * 0.5  # Sobe levemente
        self.particulas = [p for p in self.particulas if p['vida'] > 0]
    
    def _atualizar_orbita(self, dt):
        """Orbita ao redor do dono"""
        self.angulo_orbital += self.vel_orbital * dt
        rad = math.radians(self.angulo_orbital)
        
        # Flutua suavemente
        offset_y = math.sin(self.pulso) * 0.1
        
        self.x = self.dono.pos[0] + math.cos(rad) * self.dist_orbital
        self.y = self.dono.pos[1] + math.sin(rad) * self.dist_orbital + offset_y
    
    def _atualizar_carga(self, dt):
        """Carrega energia antes de disparar"""
        self.tempo_carga += dt
        
        # Cresce durante carga
        self.raio_visual = 0.15 + (self.tempo_carga / self.carga_max) * 0.15
        
        # Move-se para posição de disparo (entre dono e alvo)
        if self.alvo:
            dir_x = self.alvo.pos[0] - self.dono.pos[0]
            dir_y = self.alvo.pos[1] - self.dono.pos[1]
            dist = math.hypot(dir_x, dir_y)
            if dist > 0:
                dir_x /= dist
                dir_y /= dist
            
            # Move para frente do dono na direção do alvo
            target_x = self.dono.pos[0] + dir_x * 0.6
            target_y = self.dono.pos[1] + dir_y * 0.6
            
            self.x += (target_x - self.x) * dt * 5.0
            self.y += (target_y - self.y) * dt * 5.0
            
            # Calcula ângulo de disparo
            self.angulo_disparo = math.degrees(math.atan2(dir_y, dir_x))
        
        # Pronto para disparar
        if self.tempo_carga >= self.carga_max:
            self.estado = "disparando"
            self.vel_disparo = self.vel_max
    
    def _atualizar_disparo(self, dt):
        """Voa em direção ao alvo"""
        # Se tem alvo, persegue levemente
        if self.alvo and not self.alvo.morto:
            dir_x = self.alvo.pos[0] - self.x
            dir_y = self.alvo.pos[1] - self.y
            ang_alvo = math.degrees(math.atan2(dir_y, dir_x))
            
            # Ajuste suave de direção (homing leve)
            diff = ang_alvo - self.angulo_disparo
            while diff > 180: diff -= 360
            while diff < -180: diff += 360
            self.angulo_disparo += diff * dt * 2.0  # Homing suave
        
        # Movimento
        rad = math.radians(self.angulo_disparo)
        self.x += math.cos(rad) * self.vel_disparo * dt
        self.y += math.sin(rad) * self.vel_disparo * dt
        
        # Trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)
    
    def colidir(self, alvo):
        """Verifica colisão - só colide quando disparando"""
        if self.estado != "disparando":
            return False
        if alvo == self.dono:
            return False
        if alvo.morto:
            return False
        
        dist = math.hypot(alvo.pos[0] - self.x, alvo.pos[1] - self.y)
        raio_alvo = alvo.dados.tamanho / 2
        
        return dist < (self.raio + raio_alvo)


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