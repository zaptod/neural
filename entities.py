# entities.py
import math
import random
from config import *
from physics import normalizar_angulo
from combat import Projetil, AreaEffect, Beam, Buff, DotEffect
from ai import AIBrain
from skills import get_skill_data
from models import get_class_data

class Lutador:
    """
    Classe principal do lutador com suporte completo a:
    - Sistema de classes expandido
    - Novos tipos de skills (DASH, BUFF, AREA, BEAM, SUMMON)
    - Efeitos de status (DoT, buffs, debuffs)
    """
    def __init__(self, dados_char, pos_x, pos_y):
        self.dados = dados_char
        self.pos = [pos_x, pos_y]
        self.vel = [0.0, 0.0]
        self.z = 0.0
        self.vel_z = 0.0
        self.raio_fisico = (self.dados.tamanho / 4.0)
        
        # Carrega dados da classe
        self.classe_nome = getattr(self.dados, 'classe', "Guerreiro (Força Bruta)")
        self.class_data = get_class_data(self.classe_nome)
        
        # Status calculados com modificadores de classe
        self.vida_max = self._calcular_vida_max()
        self.vida = self.vida_max
        self.estamina = 100.0
        self.estamina_max = 100.0
        self.mana_max = self._calcular_mana_max()
        self.mana = self.mana_max
        
        # Regeneração baseada na classe
        self.regen_mana_base = self.class_data.get("regen_mana", 3.0)
        
        # Modificadores de classe
        self.mod_dano = self.class_data.get("mod_forca", 1.0)
        self.mod_velocidade = self.class_data.get("mod_velocidade", 1.0)
        self.mod_defesa = 1.0 / self.class_data.get("mod_vida", 1.0)  # Inverso para redução
        
        # Cor de aura da classe
        self.cor_aura = self.class_data.get("cor_aura", (200, 200, 200))
        
        # === SISTEMA DE SKILLS ===
        self.skill_arma_nome = "Nenhuma"
        self.custo_skill_arma = 0
        self.cd_skill_arma = 0.0
        
        if self.dados.arma_obj:
            nome_raw = getattr(self.dados.arma_obj, 'habilidade', "Nenhuma")
            skill_data = get_skill_data(nome_raw)
            if skill_data["tipo"] != "NADA":
                self.skill_arma_nome = nome_raw
                self.custo_skill_arma = skill_data["custo"]
        
        # Buffers para objetos criados
        self.buffer_projeteis = []
        self.buffer_areas = []
        self.buffer_beams = []
        
        # Efeitos ativos
        self.buffs_ativos = []
        self.dots_ativos = []

        # Estado de combate
        self.morto = False
        self.invencivel_timer = 0.0
        self.flash_timer = 0.0
        self.stun_timer = 0.0
        self.slow_timer = 0.0
        self.slow_fator = 1.0
        self.modo_adrenalina = False
        
        # Animação e visual
        self.angulo_olhar = 0.0
        self.angulo_arma_visual = 0.0
        self.cooldown_ataque = 0.0
        self.timer_animacao = 0.0
        self.atacando = False
        self.modo_ataque_aereo = False
        self.arma_droppada_pos = None
        self.arma_droppada_ang = 0
        self.fator_escala = self.dados.tamanho / ALTURA_PADRAO
        self.alcance_ideal = 1.5
        
        # Efeitos visuais temporários
        self.dash_trail = []
        self.aura_pulso = 0.0

        # IA
        self.brain = AIBrain(self)

    def _calcular_vida_max(self):
        """Calcula vida máxima com modificadores"""
        base = 100.0 + (self.dados.resistencia * 10)
        return base * self.class_data.get("mod_vida", 1.0)
    
    def _calcular_mana_max(self):
        """Calcula mana máxima com modificadores"""
        base = 50.0 + (getattr(self.dados, 'mana', 0) * 10.0)
        return base * self.class_data.get("mod_mana", 1.0)

    def usar_skill_arma(self):
        """Usa a skill equipada na arma"""
        if self.skill_arma_nome == "Nenhuma":
            return False
        
        data = get_skill_data(self.skill_arma_nome)
        tipo = data.get("tipo", "NADA")
        
        # Verifica mana (magos gastam menos)
        custo_real = self.custo_skill_arma
        if "Mago" in self.classe_nome:
            custo_real *= 0.8
        
        if self.mana < custo_real:
            return False
        
        self.mana -= custo_real
        self.cd_skill_arma = data["cooldown"]
        
        # Direção do disparo
        rad = math.radians(self.angulo_olhar)
        spawn_x = self.pos[0] + math.cos(rad) * 0.6
        spawn_y = self.pos[1] + math.sin(rad) * 0.6
        
        # === PROJÉTIL ===
        if tipo == "PROJETIL":
            multi = data.get("multi_shot", 1)
            if multi > 1:
                # Dispara em leque
                spread = 30  # graus total
                for i in range(multi):
                    ang_offset = -spread/2 + (spread / (multi-1)) * i
                    p = Projetil(self.skill_arma_nome, spawn_x, spawn_y, self.angulo_olhar + ang_offset, self)
                    self.buffer_projeteis.append(p)
            else:
                p = Projetil(self.skill_arma_nome, spawn_x, spawn_y, self.angulo_olhar, self)
                self.buffer_projeteis.append(p)
            
            # Recuo para disparos fortes
            if data["dano"] > 20:
                self.vel[0] -= math.cos(rad) * 5.0
                self.vel[1] -= math.sin(rad) * 5.0
        
        # === ÁREA ===
        elif tipo == "AREA":
            area = AreaEffect(self.skill_arma_nome, self.pos[0], self.pos[1], self)
            self.buffer_areas.append(area)
        
        # === DASH ===
        elif tipo == "DASH":
            dist = data.get("distancia", 4.0)
            dano = data.get("dano", 0)
            
            # Move instantaneamente
            self.pos[0] += math.cos(rad) * dist
            self.pos[1] += math.sin(rad) * dist
            
            # Trail visual
            for i in range(5):
                self.dash_trail.append((
                    self.pos[0] - math.cos(rad) * dist * (i/5),
                    self.pos[1] - math.sin(rad) * dist * (i/5),
                    1.0 - i*0.2
                ))
            
            # Se causa dano, cria área no caminho
            if dano > 0:
                area = AreaEffect(self.skill_arma_nome, self.pos[0], self.pos[1], self)
                area.dano = dano
                area.raio = 1.5
                self.buffer_areas.append(area)
            
            # Invencibilidade durante dash?
            if data.get("invencivel"):
                self.invencivel_timer = 0.3
        
        # === BUFF ===
        elif tipo == "BUFF":
            # Cura instantânea
            if data.get("cura"):
                self.vida = min(self.vida_max, self.vida + data["cura"])
            
            # Buff contínuo
            buff = Buff(self.skill_arma_nome, self)
            self.buffs_ativos.append(buff)
        
        # === BEAM ===
        elif tipo == "BEAM":
            alcance = data.get("alcance", 8.0)
            # Endpoint do beam
            end_x = self.pos[0] + math.cos(rad) * alcance
            end_y = self.pos[1] + math.sin(rad) * alcance
            
            beam = Beam(self.skill_arma_nome, self.pos[0], self.pos[1], end_x, end_y, self)
            self.buffer_beams.append(beam)
        
        return True

    def update(self, dt, inimigo):
        """Atualiza estado do lutador"""
        # Timers
        if self.invencivel_timer > 0:
            self.invencivel_timer -= dt
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.stun_timer > 0:
            self.stun_timer -= dt
        if self.cd_skill_arma > 0:
            self.cd_skill_arma -= dt
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_fator = 1.0

        # Atualiza efeitos
        self._atualizar_buffs(dt)
        self._atualizar_dots(dt)
        self._atualizar_dash_trail(dt)
        
        # Aura pulso
        self.aura_pulso += dt * 3
        if self.aura_pulso > math.pi * 2:
            self.aura_pulso = 0

        if self.morto:
            self.aplicar_fisica(dt)
            return

        # Regeneração de mana (classe afeta taxa)
        mana_regen = self.regen_mana_base
        if "Mago" in self.classe_nome:
            mana_regen *= 1.5
        self.mana = min(self.mana_max, self.mana + mana_regen * dt)
        
        # Regeneração de vida (Paladino)
        if "Paladino" in self.classe_nome:
            self.vida = min(self.vida_max, self.vida + self.vida_max * 0.02 * dt)
        
        # Mira no inimigo
        dx = inimigo.pos[0] - self.pos[0]
        dy = inimigo.pos[1] - self.pos[1]
        distancia = math.hypot(dx, dy)
        angulo_alvo = math.degrees(math.atan2(dy, dx))
        diff = normalizar_angulo(angulo_alvo - self.angulo_olhar)
        
        vel_giro = 20.0 if "Assassino" in self.classe_nome or "Ninja" in self.classe_nome else 10.0
        self.angulo_olhar += diff * vel_giro * dt

        if self.stun_timer <= 0 and not inimigo.morto:
            self.brain.processar(dt, distancia, inimigo)
            self.executar_movimento(dt, distancia)
            self.executar_ataques(dt, distancia, inimigo)

        self.aplicar_fisica(dt)

    def _atualizar_buffs(self, dt):
        """Atualiza buffs ativos"""
        for buff in self.buffs_ativos[:]:
            buff.atualizar(dt)
            if not buff.ativo:
                self.buffs_ativos.remove(buff)
    
    def _atualizar_dots(self, dt):
        """Atualiza DoTs ativos"""
        for dot in self.dots_ativos[:]:
            dot.atualizar(dt)
            if not dot.ativo:
                self.dots_ativos.remove(dot)
    
    def _atualizar_dash_trail(self, dt):
        """Fade do trail de dash"""
        for i, (x, y, alpha) in enumerate(self.dash_trail):
            self.dash_trail[i] = (x, y, alpha - dt * 3)
        self.dash_trail = [(x, y, a) for x, y, a in self.dash_trail if a > 0]

    def aplicar_fisica(self, dt):
        """Aplica física de movimento"""
        # Slow afeta velocidade
        vel_mult = self.slow_fator * self.mod_velocidade
        
        if self.z > 0 or self.vel_z > 0:
            self.vel_z -= GRAVIDADE_Z * dt
            self.z += self.vel_z * dt
            if self.z < 0:
                self.z = 0
                self.vel_z = 0
        
        fr = ATRITO if self.z == 0 else ATRITO * 0.2
        self.vel[0] -= self.vel[0] * fr * dt
        self.vel[1] -= self.vel[1] * fr * dt
        self.pos[0] += self.vel[0] * vel_mult * dt
        self.pos[1] += self.vel[1] * vel_mult * dt

    def executar_movimento(self, dt, distancia):
        """Executa movimento baseado na ação da IA"""
        acao = self.brain.acao_atual
        acc = 40.0 * self.mod_velocidade
        if self.modo_adrenalina:
            acc = 65.0 * self.mod_velocidade
        
        # Buff de velocidade
        for buff in self.buffs_ativos:
            acc *= buff.buff_velocidade
        
        mx, my = 0, 0
        rad = math.radians(self.angulo_olhar)
        
        if acao in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "APROXIMAR"]:
            mx = math.cos(rad)
            my = math.sin(rad)
        elif acao in ["RECUAR", "FUGIR"]:
            mx = -math.cos(rad)
            my = -math.sin(rad)
        elif acao == "CIRCULAR":
            rad_lat = math.radians(self.angulo_olhar + (90 * self.brain.dir_circular))
            mx = math.cos(rad_lat)
            my = math.sin(rad_lat)
        elif acao == "FLANQUEAR":
            rad_f = math.radians(self.angulo_olhar + (60 * self.brain.dir_circular))
            mx = math.cos(rad_f)
            my = math.sin(rad_f)
        elif acao == "APROXIMAR_LENTO":
            mx = math.cos(rad) * 0.5
            my = math.sin(rad) * 0.5
        elif acao == "POKE":
            if random.random() < 0.3:
                mx = math.cos(rad)
                my = math.sin(rad)
            
        # Pulos
        if "SALTADOR" in self.brain.tracos and self.z == 0 and random.random() < 0.01:
            self.vel_z = 12.0
        if acao in ["RECUAR", "FUGIR"] and self.z == 0 and random.random() < 0.02:
            self.vel_z = 10.0
        
        # Pulo de ataque
        ofensivos = ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"]
        if acao in ofensivos and 4.0 < distancia < 8.0 and self.z == 0 and random.random() < 0.015:
            self.vel_z = 13.0
            self.modo_ataque_aereo = True

        self.vel[0] += mx * acc * dt
        self.vel[1] += my * acc * dt

    def executar_ataques(self, dt, distancia, inimigo):
        """Executa ataques físicos"""
        self.cooldown_ataque -= dt
        
        is_orbital = self.dados.arma_obj and "Orbital" in self.dados.arma_obj.tipo
        if is_orbital:
            spd = 200
            if self.brain.acao_atual in ["MATAR", "BLOQUEAR", "COMBATE"] or distancia < 2.5:
                spd = 1000
            self.angulo_arma_visual += spd * dt
        elif self.atacando:
            self.timer_animacao -= dt
            if self.timer_animacao <= 0:
                self.atacando = False
            else:
                prog = 1.0 - (self.timer_animacao / 0.25)
                self.angulo_arma_visual = self.angulo_olhar - 60 + (math.sin(prog * math.pi) * 120)
        else:
            self.angulo_arma_visual = self.angulo_olhar

        if not self.atacando and not is_orbital and self.cooldown_ataque <= 0:
            acoes_ofensivas = ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "FLANQUEAR", "POKE"]
            deve_atacar = False
            
            if self.brain.acao_atual in acoes_ofensivas and distancia < self.alcance_ideal + 1.0:
                deve_atacar = True
            if self.brain.acao_atual == "POKE" and abs(distancia - self.alcance_ideal) < 1.0:
                deve_atacar = True
            if self.modo_ataque_aereo and distancia < 2.0:
                deve_atacar = True

            if deve_atacar and abs(self.z - inimigo.z) < 1.5:
                self.atacando = True
                self.timer_animacao = 0.25
                
                # Cooldown varia por classe
                base_cd = 0.5 + random.random() * 0.5
                if "Assassino" in self.classe_nome or "Ninja" in self.classe_nome:
                    base_cd *= 0.7
                elif "Colosso" in self.brain.arquetipo:
                    base_cd *= 1.3
                self.cooldown_ataque = base_cd

    def tomar_dano(self, dano, empurrao_x, empurrao_y, tipo_efeito="NORMAL"):
        """Recebe dano com suporte a efeitos"""
        if self.morto or self.invencivel_timer > 0:
            return False
        
        # Modificador de classe (defesa)
        dano_final = dano
        
        # Cavaleiro recebe menos dano
        if "Cavaleiro" in self.classe_nome:
            dano_final *= 0.75
        
        # Berserker: dano aumenta conforme perde vida
        if "Berserker" in self.classe_nome:
            hp_pct = self.vida / self.vida_max
            bonus_dano = 1.0 + (1.0 - hp_pct) * 0.5
            # Aplica ao próximo ataque do berserker, não ao dano recebido
        
        # Evasão (Ladino)
        if "Ladino" in self.classe_nome and random.random() < 0.2:
            return False  # Esquivou!
        
        # Escudos de buff absorvem primeiro
        for buff in self.buffs_ativos:
            if buff.escudo_atual > 0:
                dano_final = buff.absorver_dano(dano_final)
        
        # Reflexão de dano
        for buff in self.buffs_ativos:
            if buff.refletir > 0:
                # Retorna dano refletido (será tratado pelo simulador)
                pass
        
        self.vida -= dano_final
        self.invencivel_timer = 0.3
        self.flash_timer = 0.1
        self.brain.raiva += 0.2
        
        # Knockback
        kb = 15.0 + (1.0 - (self.vida/self.vida_max)) * 10.0
        self.vel[0] += empurrao_x * kb
        self.vel[1] += empurrao_y * kb
        
        # Aplica efeitos de status
        self._aplicar_efeito_status(tipo_efeito)
        
        # Modo adrenalina
        if self.vida < self.vida_max * 0.3:
            self.modo_adrenalina = True
        
        if self.vida <= 0:
            self.morrer()
            return True
        return False

    def _aplicar_efeito_status(self, efeito):
        """Aplica efeitos de status do dano"""
        if efeito == "VENENO":
            dot = DotEffect("VENENO", self, 3.0, 4.0, (100, 255, 100))
            self.dots_ativos.append(dot)
        elif efeito == "SANGRAMENTO":
            dot = DotEffect("SANGRAMENTO", self, 4.0, 3.0, (180, 0, 30))
            self.dots_ativos.append(dot)
        elif efeito == "QUEIMAR":
            dot = DotEffect("QUEIMAR", self, 5.0, 2.0, (255, 100, 0))
            self.dots_ativos.append(dot)
        elif efeito == "CONGELAR":
            self.slow_timer = 2.0
            self.slow_fator = 0.5
        elif efeito == "ATORDOAR":
            self.stun_timer = 0.8
        elif efeito == "EMPURRAO":
            # Knockback extra já aplicado
            pass
        elif efeito == "DRENAR":
            # Dono recupera vida (tratado no simulador)
            pass

    def tomar_clash(self, ex, ey):
        """Recebe impacto de clash de armas"""
        self.stun_timer = 0.5
        self.atacando = False
        self.vel[0] += ex * 25
        self.vel[1] += ey * 25

    def morrer(self):
        """Processa morte do lutador"""
        self.morto = True
        self.vida = 0
        self.arma_droppada_pos = list(self.pos)
        self.arma_droppada_ang = self.angulo_arma_visual

    def get_pos_ponteira_arma(self):
        """Retorna posição da ponta da arma (para colisão)"""
        arma = self.dados.arma_obj
        if not arma or "Orbital" in arma.tipo:
            return None
        rad = math.radians(self.angulo_arma_visual)
        ax, ay = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        cabo_px = int(((arma.comp_cabo/100)*PPM) * self.fator_escala)
        lamina_px = int(((arma.comp_lamina/100)*PPM) * self.fator_escala)
        xi = ax + math.cos(rad) * cabo_px
        yi = ay + math.sin(rad) * cabo_px
        xf = ax + math.cos(rad) * (cabo_px + lamina_px)
        yf = ay + math.sin(rad) * (cabo_px + lamina_px)
        return (xi, yi), (xf, yf)

    def get_escudo_info(self):
        """Retorna info do escudo orbital"""
        arma = self.dados.arma_obj
        if not arma or "Orbital" not in arma.tipo:
            return None
        cx, cy = int(self.pos[0] * PPM), int(self.pos[1] * PPM)
        dist_base_px = int(((arma.distancia/100)*PPM)*self.fator_escala)
        raio_char_px = int((self.dados.tamanho/2)*PPM)
        return (cx, cy), dist_base_px + raio_char_px, self.angulo_arma_visual, arma.largura
    
    def get_dano_modificado(self, dano_base):
        """Retorna dano com todos os modificadores aplicados"""
        dano = dano_base * self.mod_dano
        
        # Buff de dano
        for buff in self.buffs_ativos:
            dano *= buff.buff_dano
        
        # Berserker bonus
        if "Berserker" in self.classe_nome:
            hp_pct = self.vida / self.vida_max
            dano *= 1.0 + (1.0 - hp_pct) * 0.5
        
        # Crítico (Assassino)
        if "Assassino" in self.classe_nome and random.random() < 0.25:
            dano *= 2.0
        
        return dano