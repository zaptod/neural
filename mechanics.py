import math
import random
import database

# --- CONSTANTES FÍSICAS ---
PPM = 50 
GRAVIDADE_Z = 35.0 
ATRITO = 8.0 
ALTURA_PADRAO = 1.70

# --- FUNÇÕES MATEMÁTICAS ---
def normalizar_angulo(ang):
    return (ang + 180) % 360 - 180

def distancia_pontos(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def colisao_linha_circulo(pt1, pt2, centro_circulo, raio_circulo):
    x1, y1 = pt1; x2, y2 = pt2; cx, cy = centro_circulo
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0: return False
    t = ((cx - x1) * dx + (cy - y1) * dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    closest_x = x1 + t * dx; closest_y = y1 + t * dy
    dist_sq = (cx - closest_x)**2 + (cy - closest_y)**2
    return dist_sq <= raio_circulo**2

def intersect_line_circle(pt1, pt2, circle_center, radius):
    x1, y1 = pt1; x2, y2 = pt2; cx, cy = circle_center
    dx, dy = x2 - x1, y2 - y1; fx, fy = x1 - cx, y1 - cy
    a = dx*dx + dy*dy; b = 2*(fx*dx + fy*dy)
    c = (fx*fx + fy*fy) - radius*radius
    delta = b*b - 4*a*c
    if delta < 0 or a == 0: return [] 
    delta_sqrt = math.sqrt(delta)
    t1 = (-b - delta_sqrt) / (2*a); t2 = (-b + delta_sqrt) / (2*a)
    points = []
    if 0 <= t1 <= 1: points.append((x1 + t1*dx, y1 + t1*dy))
    if 0 <= t2 <= 1: points.append((x1 + t2*dx, y1 + t2*dy))
    return points

def colisao_linha_linha(p1, p2, p3, p4):
    def ccw(A,B,C): return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    return ccw(p1,p3,p4) != ccw(p2,p3,p4) and ccw(p1,p2,p3) != ccw(p1,p2,p4)

# --- CLASSES LÓGICAS ---
class Particula:
    def __init__(self, x, y, cor, vel_x, vel_y, tamanho, vida_util=1.0):
        self.x, self.y = x, y; self.cor = cor
        self.vel_x, self.vel_y = vel_x, vel_y
        self.tamanho = tamanho; self.vida = vida_util

    def atualizar(self, dt):
        self.x += self.vel_x * dt; self.y += self.vel_y * dt
        self.vida -= dt; self.tamanho *= 0.92

class Projetil:
    def __init__(self, tipo, x, y, angulo, dono):
        self.tipo = tipo
        self.x = x
        self.y = y
        self.angulo = angulo
        self.dono = dono # Quem atirou (para não se acertar)
        self.vida = 2.0
        self.ativo = True
        
        # Configs por tipo
        if "Sônico" in tipo:
            self.vel = 15.0 # Muito rápido
            self.raio = 0.5
            self.dano = 15.0
            self.cor = (200, 200, 255)
            self.vida = 0.4 # Curto alcance
        elif "Disparo" in tipo:
            self.vel = 8.0
            self.raio = 0.2
            self.dano = 8.0
            self.cor = (50, 150, 255)
            self.vida = 3.0
        else: # Padrão
            self.vel = 5.0
            self.raio = 0.2
            self.dano = 5.0
            self.cor = (255, 255, 255)

    def atualizar(self, dt):
        rad = math.radians(self.angulo)
        self.x += math.cos(rad) * self.vel * dt
        self.y += math.sin(rad) * self.vel * dt
        self.vida -= dt
        if self.vida <= 0: self.ativo = False

class LutadorAuto:
    def __init__(self, dados_char, pos_x, pos_y):
        self.dados = dados_char
        self.pos = [pos_x, pos_y]
        self.vel = [0.0, 0.0]
        self.z = 0.0; self.vel_z = 0.0
        self.raio_fisico = (self.dados.tamanho / 4.0)
        
        # Status
        self.vida_max = 100.0 + (self.dados.resistencia * 10)
        self.vida = self.vida_max
        self.estamina = 100.0
        self.estamina_max = 100.0
        self.mana_max = 50.0 + (getattr(self.dados, 'mana', 0) * 10.0)
        self.mana = self.mana_max
        
        # Skills
        self.classe_nome = getattr(self.dados, 'classe', "Guerreiro")
        self.skill_arma_nome = "Nenhuma"
        self.custo_skill_arma = 0
        if self.dados.arma_obj:
            self.skill_arma_nome = getattr(self.dados.arma_obj, 'habilidade', "Nenhuma")
            self.custo_skill_arma = getattr(self.dados.arma_obj, 'custo_mana', 0)

        self.cd_skill_arma = 0.0
        
        # Buffer de Projéteis (Para o simulador pegar)
        self.buffer_projeteis = []

        # Estados e Controle
        self.morto = False
        self.invencivel_timer = 0.0
        self.flash_timer = 0.0
        self.stun_timer = 0.0 
        self.modo_adrenalina = False
        self.angulo_olhar = 0.0 
        self.angulo_arma_visual = 0.0 
        self.cooldown_ataque = 0.0
        self.timer_animacao = 0.0
        self.atacando = False
        self.modo_ataque_aereo = False 
        self.arma_droppada_pos = None; self.arma_droppada_ang = 0
        self.fator_escala = self.dados.tamanho / ALTURA_PADRAO
        
        self.definir_arquetipo()
        self.definir_tracos()
        
        # IA Variáveis
        self.medo = 0.0; self.raiva = 0.0
        self.timer_decisao = 0.0
        self.acao_atual = "NEUTRO"
        self.dir_circular = random.choice([-1, 1])

    def definir_arquetipo(self):
        if "Mago" in self.classe_nome: self.arquetipo = "MAGO"; self.alcance_ideal = 8.0; return
        arma = self.dados.arma_obj
        if not arma: self.arquetipo = "MONGE"; self.alcance_ideal = 1.0; return

        if "Orbital" in arma.tipo:
            self.arquetipo = "SENTINELA"
            self.alcance_ideal = (arma.distancia / 100.0 * self.fator_escala) + self.raio_fisico + 0.5
        elif "Reta" in arma.tipo:
            comp_total = (arma.comp_cabo + arma.comp_lamina)
            if arma.peso > 8.0: self.arquetipo = "COLOSSO"
            elif arma.peso < 3.0: self.arquetipo = "ASSASSINO"
            elif comp_total > 80.0: self.arquetipo = "LANCEIRO"
            else: self.arquetipo = "GUERREIRO"
            self.alcance_ideal = (comp_total / 100.0 * 0.9 * self.fator_escala) + self.raio_fisico

    def definir_tracos(self):
        possibilidades = ["COVARDE", "VINGATIVO", "IMPRUDENTE", "ANALITICO", "SALTADOR", "SPAMMER", "PACIENTE"]
        self.tracos = random.sample(possibilidades, 2)
        if "IMPRUDENTE" in self.tracos: self.alcance_ideal *= 0.8
        if "COVARDE" in self.tracos: self.alcance_ideal *= 1.2

    def tomar_dano(self, dano, empurrao_x, empurrao_y):
        if self.morto or self.invencivel_timer > 0: return False
        
        fator = 0.9 if self.estamina > 30 else 1.0
        self.vida -= dano * fator
        self.invencivel_timer = 0.3; self.flash_timer = 0.1
        self.raiva += 0.2
        if "COVARDE" in self.tracos: self.medo += 0.3
        
        fator_kb = 15.0 + (1.0 - (self.vida/self.vida_max)) * 10.0
        self.vel[0] += empurrao_x * fator_kb; self.vel[1] += empurrao_y * fator_kb
        
        if not self.modo_adrenalina and self.vida < (self.vida_max * 0.3):
            self.modo_adrenalina = True
            self.estamina = 100; self.mana = self.mana_max
            self.raiva = 1.0
        
        if self.vida <= 0: self.morrer(); return True 
        return False

    def tomar_clash(self, empurrao_x, empurrao_y):
        self.stun_timer = 0.6; self.atacando = False; self.timer_animacao = 0 
        self.estamina -= 15 
        self.vel[0] += empurrao_x * 22.0; self.vel[1] += empurrao_y * 22.0
        self.flash_timer = 0.1 

    def morrer(self):
        self.morto = True; self.vida = 0
        self.arma_droppada_pos = list(self.pos)
        self.arma_droppada_ang = self.angulo_arma_visual

    def tentar_usar_skill(self):
        # Verifica Skill da Arma
        if self.skill_arma_nome != "Nenhuma" and self.cd_skill_arma <= 0:
            if self.mana >= self.custo_skill_arma:
                self.mana -= self.custo_skill_arma
                self.cd_skill_arma = 4.0 # Cooldown base
                
                # CRIA O PROJÉTIL/EFEITO
                # Posição de saída (na frente do personagem)
                rad = math.radians(self.angulo_olhar)
                spawn_x = self.pos[0] + math.cos(rad) * 0.5
                spawn_y = self.pos[1] + math.sin(rad) * 0.5
                
                p = Projetil(self.skill_arma_nome, spawn_x, spawn_y, self.angulo_olhar, self)
                self.buffer_projeteis.append(p)
                
                # Se for ataque de curta distância, avança um pouco (dash)
                if "Sônico" in self.skill_arma_nome:
                    self.vel[0] += math.cos(rad) * 10.0
                    self.vel[1] += math.sin(rad) * 10.0
                
                return True
        return False

    def processar_cerebro(self, distancia, inimigo):
        self.raiva = max(0, self.raiva - 0.005); self.medo = max(0, self.medo - 0.005)
        self.timer_decisao -= 0.016
        if self.timer_decisao > 0: return

        self.timer_decisao = random.uniform(0.3, 0.8)
        
        # --- Lógica de Uso de Skill para TODOS ---
        # Se tiver mana, tenta usar em momentos agressivos
        if self.mana > 20 and self.skill_arma_nome != "Nenhuma":
            # "Impacto Sônico" é curto alcance, usa quando perto
            if "Sônico" in self.skill_arma_nome and distancia < 4.0:
                self.tentar_usar_skill()
            # "Disparo" é longo alcance, usa quando longe
            elif "Disparo" in self.skill_arma_nome and distancia > 5.0:
                self.tentar_usar_skill()

        if self.arquetipo == "MAGO":
            self.tentar_usar_skill() # Mago spamma sempre que pode
            if distancia < 6.0: self.acao_atual = "FUGIR"
            else: self.acao_atual = "BLOQUEAR" # Fica parado mirando
            return

        if self.estamina < 15: self.acao_atual = "RECUAR"; return
        
        # Lógica padrão simplificada
        roll = random.random()
        if self.arquetipo == "SENTINELA":
            self.acao_atual = "BLOQUEAR" if distancia < self.alcance_ideal + 2.0 else "APROXIMAR_LENTO"
        elif self.arquetipo == "ASSASSINO":
            self.acao_atual = "CIRCULAR" if roll < 0.4 else ("FLANQUEAR" if roll < 0.7 else "ATAQUE_RAPIDO")
        elif self.arquetipo == "LANCEIRO":
            if distancia < self.alcance_ideal - 1.0: self.acao_atual = "RECUAR"
            elif distancia > self.alcance_ideal + 1.0: self.acao_atual = "APROXIMAR"
            else: self.acao_atual = "POKE"
        elif self.arquetipo == "COLOSSO":
            self.acao_atual = "ESMAGAR"
        else: # Guerreiro
            self.acao_atual = "COMBATE" if roll < 0.5 else "CIRCULAR"

    def atualizar_ia(self, dt, inimigo):
        if self.morto or self.stun_timer > 0: 
            if self.stun_timer > 0: self.stun_timer -= dt
            return

        if self.cd_skill_arma > 0: self.cd_skill_arma -= dt
        
        mana_regen = 5.0 if "Mago" in self.classe_nome else 2.0
        self.mana = min(self.mana_max, self.mana + mana_regen * dt)
        
        recup = 15.0 if "RECUAR" in self.acao_atual else 5.0
        self.estamina = min(self.estamina_max, self.estamina + recup * dt)

        dx = inimigo.pos[0] - self.pos[0]; dy = inimigo.pos[1] - self.pos[1]
        distancia = math.hypot(dx, dy)
        
        # Mira
        angulo_alvo = math.degrees(math.atan2(dy, dx))
        erro = random.uniform(-10, 10) if "NERVOSO" in self.tracos else 0
        diff = normalizar_angulo((angulo_alvo + erro) - self.angulo_olhar)
        vel_giro = 20.0 if self.arquetipo == "ASSASSINO" else 10.0
        self.angulo_olhar += diff * vel_giro * dt 
        
        if inimigo.morto: return

        self.processar_cerebro(distancia, inimigo)

        # Movimento
        acc = 60.0 if self.modo_adrenalina else 40.0
        move_x, move_y = 0, 0
        rad = math.radians(self.angulo_olhar)
        
        if self.acao_atual in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"]:
            move_x = math.cos(rad); move_y = math.sin(rad)
        elif self.acao_atual in ["RECUAR", "FUGIR"]:
            move_x = -math.cos(rad); move_y = -math.sin(rad)
        elif self.acao_atual == "CIRCULAR":
            rad_lat = math.radians(self.angulo_olhar + (90 * self.dir_circular))
            move_x = math.cos(rad_lat); move_y = math.sin(rad_lat)
            if random.random() < 0.02: self.dir_circular *= -1
        elif self.acao_atual == "FLANQUEAR":
            rad_f = math.radians(self.angulo_olhar + (60 * self.dir_circular))
            move_x = math.cos(rad_f); move_y = math.sin(rad_f)
        elif self.acao_atual == "APROXIMAR" or self.acao_atual == "APROXIMAR_LENTO":
            move_x = math.cos(rad); move_y = math.sin(rad)
            if self.acao_atual == "APROXIMAR_LENTO": acc *= 0.5

        # Pulo de Ataque (Colosso/Guerreiro)
        if self.z == 0 and distancia > 4.0 and distancia < 7.0 and random.random() < 0.02 and self.estamina > 30:
             if self.arquetipo in ["COLOSSO", "GUERREIRO"]:
                 self.vel_z = 12.0; self.modo_ataque_aereo = True
                 self.estamina -= 20

        # Aplicação Movimento
        if self.modo_ataque_aereo:
            self.vel[0] += math.cos(rad) * acc * 1.5 * dt
            self.vel[1] += math.sin(rad) * acc * 1.5 * dt
            if self.z <= 0: self.modo_ataque_aereo = False
        else:
            self.vel[0] += move_x * acc * dt
            self.vel[1] += move_y * acc * dt

        # Ataque Físico
        self.cooldown_ataque -= dt
        pode_atacar = False
        if self.acao_atual in ["MATAR", "ESMAGAR"] and distancia < self.alcance_ideal + 1.0: pode_atacar = True
        if self.acao_atual == "POKE" and abs(distancia - self.alcance_ideal) < 0.8: pode_atacar = True
        
        is_orbital = self.dados.arma_obj and "Orbital" in self.dados.arma_obj.tipo
        if is_orbital:
            spd = 200
            if self.acao_atual in ["MATAR", "BLOQUEAR"]: spd = 1000
            self.angulo_arma_visual += spd * dt
        else:
            if pode_atacar and self.cooldown_ataque <= 0 and self.estamina > 10:
                if abs(self.z - inimigo.z) < 1.5: self.iniciar_ataque()

        if not is_orbital: self.processar_animacao_ataque(dt)

    def iniciar_ataque(self):
        self.atacando = True; self.timer_animacao = 0.25 
        custo = 15; cd = 0.5 + random.random() * 0.5
        if self.arquetipo == "COLOSSO": cd *= 1.5; custo = 30
        if self.arquetipo == "ASSASSINO": cd *= 0.7; custo = 10
        self.estamina -= custo; self.cooldown_ataque = cd
        
    def processar_animacao_ataque(self, dt):
        if self.timer_animacao > 0:
            self.timer_animacao -= dt
            prog = 1.0 - (self.timer_animacao / 0.25)
            arco = math.sin(prog * math.pi) * 120 
            self.angulo_arma_visual = self.angulo_olhar - 60 + arco
        else:
            self.atacando = False
            self.angulo_arma_visual = self.angulo_olhar

    def atualizar_fisica(self, dt):
        if self.invencivel_timer > 0: self.invencivel_timer -= dt
        if self.flash_timer > 0: self.flash_timer -= dt
        friccao = ATRITO if not self.morto else ATRITO * 2
        if self.z > 0: friccao *= 0.2 
        self.vel[0] -= self.vel[0] * friccao * dt; self.vel[1] -= self.vel[1] * friccao * dt
        self.pos[0] += self.vel[0] * dt; self.pos[1] += self.vel[1] * dt
        if self.z > 0 or self.vel_z > 0:
            self.vel_z -= GRAVIDADE_Z * dt; self.z += self.vel_z * dt
            if self.z < 0: self.z = 0; self.vel_z = 0

    # --- HELPERS ---
    def get_pos_ponteira_arma(self):
        arma = self.dados.arma_obj
        if not arma or "Orbital" in arma.tipo: return None 
        rad = math.radians(self.angulo_arma_visual)
        ax, ay = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        cabo_px = int(((arma.comp_cabo/100)*PPM) * self.fator_escala)
        lamina_px = int(((arma.comp_lamina/100)*PPM) * self.fator_escala)
        xi = ax + math.cos(rad) * cabo_px; yi = ay + math.sin(rad) * cabo_px
        xf = ax + math.cos(rad) * (cabo_px + lamina_px); yf = ay + math.sin(rad) * (cabo_px + lamina_px)
        return (xi, yi), (xf, yf)

    def get_escudo_info(self):
        arma = self.dados.arma_obj
        if not arma or "Orbital" not in arma.tipo: return None
        cx, cy = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        dist_base_px = int(((arma.distancia/100)*PPM)*self.fator_escala)
        raio_char_px = int((self.dados.tamanho/2)*PPM)
        return (cx, cy), dist_base_px + raio_char_px, self.angulo_arma_visual, arma.largura