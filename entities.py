# entities.py
import math
import random
from config import *
from physics import normalizar_angulo
from combat import Projetil
from ai import AIBrain
from skills import get_skill_data # Importa o catálogo

class Lutador:
    def __init__(self, dados_char, pos_x, pos_y):
        self.dados = dados_char
        self.pos = [pos_x, pos_y]
        self.vel = [0.0, 0.0]
        self.z = 0.0; self.vel_z = 0.0
        self.raio_fisico = (self.dados.tamanho / 4.0)
        
        self.vida_max = 100.0 + (self.dados.resistencia * 10)
        self.vida = self.vida_max
        self.estamina = 100.0; self.estamina_max = 100.0
        self.mana_max = 50.0 + (getattr(self.dados, 'mana', 0) * 10.0)
        self.mana = self.mana_max
        
        self.classe_nome = getattr(self.dados, 'classe', "Guerreiro")
        
        # --- CARREGA DADOS DA SKILL DO ARQUIVO skills.py ---
        self.skill_arma_nome = "Nenhuma"
        if self.dados.arma_obj:
            nome_raw = getattr(self.dados.arma_obj, 'habilidade', "Nenhuma")
            # Verifica se a skill existe no DB, senão usa Nenhuma
            skill_data = get_skill_data(nome_raw)
            if skill_data["tipo"] != "NADA":
                self.skill_arma_nome = nome_raw
                # O custo vem do DB agora, ignorando o json antigo da arma se quiser
                self.custo_skill_arma = skill_data["custo"]
            else:
                self.custo_skill_arma = 0
        else:
            self.custo_skill_arma = 0
        
        self.cd_skill_arma = 0.0
        self.buffer_projeteis = []

        # Estado
        self.morto = False
        self.invencivel_timer = 0.0
        self.flash_timer = 0.0
        self.stun_timer = 0.0 
        self.modo_adrenalina = False
        self.angulo_olhar = 0.0; self.angulo_arma_visual = 0.0
        self.cooldown_ataque = 0.0; self.timer_animacao = 0.0; self.atacando = False
        self.modo_ataque_aereo = False
        self.arma_droppada_pos = None; self.arma_droppada_ang = 0
        self.fator_escala = self.dados.tamanho / ALTURA_PADRAO
        self.alcance_ideal = 1.5

        self.brain = AIBrain(self)

    def usar_skill_arma(self):
        # Busca dados atualizados (para cooldown)
        data = get_skill_data(self.skill_arma_nome)
        
        self.mana -= self.custo_skill_arma
        self.cd_skill_arma = data["cooldown"] # Cooldown vindo do DB
        
        rad = math.radians(self.angulo_olhar)
        spawn_x = self.pos[0] + math.cos(rad) * 0.6
        spawn_y = self.pos[1] + math.sin(rad) * 0.6
        
        # Cria o projétil genérico que se auto-configura
        p = Projetil(self.skill_arma_nome, spawn_x, spawn_y, self.angulo_olhar, self)
        self.buffer_projeteis.append(p)
        
        # Efeito de recuo para disparos fortes
        if data["dano"] > 20:
            self.vel[0] -= math.cos(rad) * 5.0
            self.vel[1] -= math.sin(rad) * 5.0
            
        return True

    def update(self, dt, inimigo):
        if self.invencivel_timer > 0: self.invencivel_timer -= dt
        if self.flash_timer > 0: self.flash_timer -= dt 
        if self.stun_timer > 0: self.stun_timer -= dt   
        if self.cd_skill_arma > 0: self.cd_skill_arma -= dt

        if self.morto:
            self.aplicar_fisica(dt)
            return

        mana_regen = 8.0 if "Mago" in self.classe_nome else 3.0
        self.mana = min(self.mana_max, self.mana + mana_regen * dt)
        
        dx = inimigo.pos[0] - self.pos[0]; dy = inimigo.pos[1] - self.pos[1]
        distancia = math.hypot(dx, dy)
        angulo_alvo = math.degrees(math.atan2(dy, dx))
        diff = normalizar_angulo(angulo_alvo - self.angulo_olhar)
        
        vel_giro = 20.0 if self.brain.arquetipo == "ASSASSINO" else 10.0
        self.angulo_olhar += diff * vel_giro * dt 

        if self.stun_timer <= 0 and not inimigo.morto:
            self.brain.processar(dt, distancia, inimigo)
            self.executar_movimento(dt, distancia)
            self.executar_ataques(dt, distancia, inimigo)

        self.aplicar_fisica(dt)

    def aplicar_fisica(self, dt):
        if self.z > 0 or self.vel_z > 0:
            self.vel_z -= GRAVIDADE_Z * dt
            self.z += self.vel_z * dt
            if self.z < 0: self.z = 0; self.vel_z = 0
        
        fr = ATRITO if self.z == 0 else ATRITO * 0.2
        self.vel[0] -= self.vel[0] * fr * dt
        self.vel[1] -= self.vel[1] * fr * dt
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

    def executar_movimento(self, dt, distancia):
        acao = self.brain.acao_atual
        acc = 40.0
        if self.modo_adrenalina: acc = 65.0
        
        mx, my = 0, 0
        rad = math.radians(self.angulo_olhar)
        
        if acao in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "APROXIMAR"]:
            mx = math.cos(rad); my = math.sin(rad)
        elif acao in ["RECUAR", "FUGIR"]:
            mx = -math.cos(rad); my = -math.sin(rad)
        elif acao == "CIRCULAR":
            rad_lat = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
            mx = math.cos(rad_lat); my = math.sin(rad_lat)
        elif acao == "FLANQUEAR":
            rad_f = math.radians(self.angulo_olhar + (60 * self.brain.dir_circular))
            mx = math.cos(rad_f); my = math.sin(rad_f)
            
        if "SALTADOR" in self.brain.tracos and self.z == 0 and random.random() < 0.01:
            self.vel_z = 12.0
        if acao in ["RECUAR", "FUGIR"] and self.z == 0 and random.random() < 0.02:
            self.vel_z = 10.0
        ofensivos = ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"]
        if acao in ofensivos and 4.0 < distancia < 8.0 and self.z == 0 and random.random() < 0.015:
            self.vel_z = 13.0; self.modo_ataque_aereo = True

        self.vel[0] += mx * acc * dt
        self.vel[1] += my * acc * dt

    def executar_ataques(self, dt, distancia, inimigo):
        self.cooldown_ataque -= dt
        
        is_orbital = self.dados.arma_obj and "Orbital" in self.dados.arma_obj.tipo
        if is_orbital:
            spd = 200
            if self.brain.acao_atual in ["MATAR", "BLOQUEAR", "COMBATE"] or distancia < 2.5: spd = 1000
            self.angulo_arma_visual += spd * dt
        elif self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0: self.atacando = False
            else:
                prog = 1.0 - (self.timer_animacao / 0.25)
                self.angulo_arma_visual = self.angulo_olhar - 60 + (math.sin(prog * math.pi) * 120)
        else:
            self.angulo_arma_visual = self.angulo_olhar

        if not self.atacando and not is_orbital and self.cooldown_ataque <= 0:
            acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR"]
            deve_atacar = False
            
            if self.brain.acao_atual in acoes_ofensivas and distancia < self.alcance_ideal + 1.0: deve_atacar = True
            if self.brain.acao_atual == "POKE" and abs(distancia - self.alcance_ideal) < 1.0: deve_atacar = True
            if self.modo_ataque_aereo and distancia < 2.0: deve_atacar = True

            if deve_atacar and abs(self.z - inimigo.z) < 1.5:
                self.atacando = True
                self.timer_animacao = 0.25
                self.cooldown_ataque = 0.5 + random.random() * 0.5

    def tomar_dano(self, dano, empurrao_x, empurrao_y):
        if self.morto or self.invencivel_timer > 0: return False
        
        self.vida -= dano
        self.invencivel_timer = 0.3
        self.flash_timer = 0.1 
        self.brain.raiva += 0.2
        
        kb = 15.0 + (1.0 - (self.vida/self.vida_max)) * 10.0
        self.vel[0] += empurrao_x * kb; self.vel[1] += empurrao_y * kb
        
        if self.vida < self.vida_max * 0.3: self.modo_adrenalina = True
        if self.vida <= 0: self.morrer(); return True
        return False

    def tomar_clash(self, ex, ey):
        self.stun_timer = 0.5
        self.atacando = False
        self.vel[0] += ex * 25
        self.vel[1] += ey * 25

    def morrer(self):
        self.morto = True; self.vida = 0
        self.arma_droppada_pos = list(self.pos)
        self.arma_droppada_ang = self.angulo_arma_visual

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