import random
import math
from config import *
from physics import normalizar_angulo
from skills import get_skill_data
from models import get_class_data

class AIBrain:
    """
    Cérebro da IA com sistema de arquétipos, traços e decisões táticas.
    Agora com suporte completo aos novos tipos de skills e classes.
    """
    def __init__(self, parent):
        self.parent = parent
        self.timer_decisao = 0.0
        self.acao_atual = "NEUTRO"
        self.dir_circular = random.choice([-1, 1])
        
        # Emoções
        self.medo = 0.0
        self.raiva = 0.0
        
        # Personalidade
        self.arquetipo = "GUERREIRO"
        self.tracos = []
        self.definir_arquetipo()
        self.definir_tracos()
        
        # Cache de skills disponíveis
        self.skills_ofensivas = []
        self.skills_defensivas = []
        self.skills_mobilidade = []
        self.categorizar_skills()

    def categorizar_skills(self):
        """Categoriza skills do personagem para decisões táticas"""
        p = self.parent
        
        # Skill da arma
        if p.skill_arma_nome != "Nenhuma":
            data = get_skill_data(p.skill_arma_nome)
            self._categorizar_skill(p.skill_arma_nome, data)
        
        # Skills de classe (afinidade)
        class_data = get_class_data(p.classe_nome)
        for skill_nome in class_data.get("skills_afinidade", []):
            data = get_skill_data(skill_nome)
            self._categorizar_skill(skill_nome, data)
    
    def _categorizar_skill(self, nome, data):
        """Categoriza uma skill individual"""
        tipo = data.get("tipo", "NADA")
        
        if tipo in ["PROJETIL", "BEAM", "AREA"]:
            if data.get("efeito") in ["DRENAR", "SANGRAMENTO", "VENENO", "EXPLOSAO"]:
                self.skills_ofensivas.append(nome)
            elif data.get("dano", 0) > 15:
                self.skills_ofensivas.append(nome)
            else:
                self.skills_ofensivas.append(nome)
                
        elif tipo == "BUFF":
            if data.get("cura") or data.get("escudo"):
                self.skills_defensivas.append(nome)
            else:
                self.skills_ofensivas.append(nome)
                
        elif tipo == "DASH":
            self.skills_mobilidade.append(nome)

    def definir_arquetipo(self):
        """Define arquétipo baseado na classe e arma"""
        p = self.parent
        classe = p.classe_nome
        
        # Mapeamento de classe para arquétipo
        if "Mago" in classe or "Piromante" in classe or "Criomante" in classe or "Necromante" in classe or "Feiticeiro" in classe:
            self.arquetipo = "MAGO"
            p.alcance_ideal = 8.0
            return
        
        if "Assassino" in classe or "Ninja" in classe:
            self.arquetipo = "ASSASSINO"
            p.alcance_ideal = 2.0
            return
        
        if "Berserker" in classe:
            self.arquetipo = "BERSERKER"
            p.alcance_ideal = 1.5
            return
        
        if "Cavaleiro" in classe or "Paladino" in classe:
            self.arquetipo = "SENTINELA"
            p.alcance_ideal = 2.0
            return
        
        if "Ladino" in classe:
            self.arquetipo = "ASSASSINO"
            p.alcance_ideal = 3.0
            return
        
        if "Druida" in classe:
            self.arquetipo = "DRUIDA"
            p.alcance_ideal = 5.0
            return
        
        if "Monge" in classe:
            self.arquetipo = "MONGE"
            p.alcance_ideal = 1.5
            return
        
        # Fallback: baseado na arma
        arma = p.dados.arma_obj
        if not arma:
            self.arquetipo = "MONGE"
            p.alcance_ideal = 1.0
            return

        if "Orbital" in arma.tipo:
            self.arquetipo = "SENTINELA"
            p.alcance_ideal = (arma.distancia / 100.0 * p.fator_escala) + p.raio_fisico + 0.5
        elif "Reta" in arma.tipo:
            comp_total = (arma.comp_cabo + arma.comp_lamina)
            if arma.peso > 8.0:
                self.arquetipo = "COLOSSO"
            elif arma.peso < 3.0:
                self.arquetipo = "ASSASSINO"
            elif comp_total > 80.0:
                self.arquetipo = "LANCEIRO"
            else:
                self.arquetipo = "GUERREIRO"
            p.alcance_ideal = (comp_total / 100.0 * 0.9 * p.fator_escala) + p.raio_fisico

    def definir_tracos(self):
        """Define traços de personalidade aleatórios"""
        possibilidades = [
            "COVARDE", "VINGATIVO", "IMPRUDENTE", "ANALITICO", 
            "SALTADOR", "SPAMMER", "PACIENTE", "AGRESSIVO",
            "CALCULISTA", "BERSERKER"
        ]
        self.tracos = random.sample(possibilidades, 2)
        
        if "IMPRUDENTE" in self.tracos:
            self.parent.alcance_ideal *= 0.8
        if "COVARDE" in self.tracos:
            self.parent.alcance_ideal *= 1.2
        if "AGRESSIVO" in self.tracos:
            self.parent.alcance_ideal *= 0.9

    def processar(self, dt, distancia, inimigo):
        """Processa decisões da IA a cada frame"""
        self.raiva = max(0, self.raiva - 0.005)
        self.medo = max(0, self.medo - 0.005)
        self.timer_decisao -= dt
        
        p = self.parent

        # === DECISÃO DE SKILLS ===
        skill_usada = self.processar_skills(distancia, inimigo)
        if skill_usada:
            return

        # === DECISÃO DE MOVIMENTO ===
        if self.timer_decisao <= 0:
            self.timer_decisao = random.uniform(0.2, 0.6)
            self.decidir_movimento(distancia, inimigo)

    def processar_skills(self, distancia, inimigo):
        """Lógica de uso de skills baseada no contexto"""
        p = self.parent
        
        # Verifica se pode usar skill da arma
        if p.skill_arma_nome == "Nenhuma" or p.cd_skill_arma > 0 or p.mana < p.custo_skill_arma:
            return False
        
        dados_skill = get_skill_data(p.skill_arma_nome)
        tipo_skill = dados_skill.get("tipo", "NADA")
        efeito = dados_skill.get("efeito", "NORMAL")
        
        usar = False
        
        # === PROJÉTEIS ===
        if tipo_skill == "PROJETIL":
            alcance_skill = dados_skill.get("vida", 1.0) * dados_skill.get("velocidade", 10.0)
            
            # Magos disparam à distância
            if self.arquetipo == "MAGO":
                if distancia > 3.0:
                    usar = True
            # Assassinos usam em close range
            elif self.arquetipo == "ASSASSINO":
                if distancia < 4.0:
                    usar = True
            # Outros usam quando em alcance
            elif distancia < alcance_skill and distancia > 2.0:
                usar = True
            
            # Spammers sempre tentam
            if "SPAMMER" in self.tracos and random.random() < 0.3:
                usar = True
        
        # === BEAMS (instantâneos) ===
        elif tipo_skill == "BEAM":
            alcance = dados_skill.get("alcance", 5.0)
            if distancia < alcance:
                usar = True
        
        # === ÁREA ===
        elif tipo_skill == "AREA":
            raio = dados_skill.get("raio_area", 2.0)
            # Usa quando inimigo está no raio
            if distancia < raio + 1.0:
                usar = True
            # Berserkers usam mais agressivamente
            if self.arquetipo == "BERSERKER" and distancia < raio + 2.0:
                usar = True
        
        # === DASH ===
        elif tipo_skill == "DASH":
            dist_dash = dados_skill.get("distancia", 3.0)
            # Fuga
            if self.medo > 0.5 or (p.vida < p.vida_max * 0.3):
                usar = True
            # Aproximação agressiva
            elif self.arquetipo in ["ASSASSINO", "BERSERKER"] and distancia > 4.0 and distancia < dist_dash + 2.0:
                usar = True
        
        # === BUFF ===
        elif tipo_skill == "BUFF":
            # Cura quando HP baixo
            if dados_skill.get("cura") and p.vida < p.vida_max * 0.5:
                usar = True
            # Escudo quando entrando em combate
            elif dados_skill.get("escudo") and distancia < 5.0 and p.vida == p.vida_max:
                usar = True
            # Buff de dano quando perto
            elif dados_skill.get("buff_dano") and distancia < 3.0:
                usar = True
            # Buff de velocidade para aproximar/fugir
            elif dados_skill.get("buff_velocidade"):
                if distancia > 6.0 or p.vida < p.vida_max * 0.4:
                    usar = True
        
        # === EXECUÇÃO ===
        if usar:
            if p.usar_skill_arma():
                # Reação pós-uso
                if self.arquetipo == "MAGO" or "COVARDE" in self.tracos:
                    if tipo_skill != "DASH":
                        self.acao_atual = "RECUAR"
                elif self.arquetipo in ["ASSASSINO", "BERSERKER"]:
                    self.acao_atual = "MATAR"
                return True
        
        return False

    def decidir_movimento(self, distancia, inimigo):
        """Decide ação de movimento baseada no contexto"""
        p = self.parent
        roll = random.random()

        # Modo adrenalina = full agressivo
        if p.modo_adrenalina:
            self.acao_atual = "MATAR"
            return

        # Sem estamina = recuar
        if p.estamina < 15:
            self.acao_atual = "RECUAR"
            return
        
        # Medo alto = fugir
        if self.medo > 0.7:
            self.acao_atual = "FUGIR"
            return

        # === COMPORTAMENTO POR ARQUÉTIPO ===
        
        if self.arquetipo == "MAGO":
            if distancia < 5.0:
                self.acao_atual = "FUGIR"
            elif distancia < 8.0:
                self.acao_atual = "CIRCULAR"
            else:
                self.acao_atual = "BLOQUEAR"
        
        elif self.arquetipo == "BERSERKER":
            # Quanto menos vida, mais agressivo
            hp_pct = p.vida / p.vida_max
            if hp_pct < 0.5:
                self.acao_atual = "MATAR"
            else:
                self.acao_atual = "ESMAGAR" if roll < 0.7 else "APROXIMAR"
        
        elif self.arquetipo == "SENTINELA":
            if distancia < p.alcance_ideal + 1.5:
                self.acao_atual = "BLOQUEAR"
            else:
                self.acao_atual = "APROXIMAR_LENTO"
        
        elif self.arquetipo == "ASSASSINO":
            if roll < 0.35:
                self.acao_atual = "CIRCULAR"
            elif roll < 0.6:
                self.acao_atual = "FLANQUEAR"
            elif roll < 0.8:
                self.acao_atual = "ATAQUE_RAPIDO"
            else:
                self.acao_atual = "RECUAR"
        
        elif self.arquetipo == "COLOSSO":
            self.acao_atual = "ESMAGAR"
        
        elif self.arquetipo == "LANCEIRO":
            if distancia > p.alcance_ideal + 1.5:
                self.acao_atual = "APROXIMAR"
            elif distancia < p.alcance_ideal - 1.0:
                self.acao_atual = "RECUAR"
            else:
                self.acao_atual = "POKE" if roll < 0.6 else "CIRCULAR"
        
        elif self.arquetipo == "DRUIDA":
            if distancia < 4.0:
                self.acao_atual = "RECUAR" if roll < 0.6 else "CIRCULAR"
            else:
                self.acao_atual = "BLOQUEAR"
        
        elif self.arquetipo == "MONGE":
            if roll < 0.4:
                self.acao_atual = "CIRCULAR"
            elif roll < 0.7:
                self.acao_atual = "ATAQUE_RAPIDO"
            else:
                self.acao_atual = "FLANQUEAR"
        
        else:  # GUERREIRO padrão
            if distancia > p.alcance_ideal + 1.5:
                self.acao_atual = "APROXIMAR"
            elif distancia < p.alcance_ideal - 1.0:
                self.acao_atual = "RECUAR"
            else:
                self.acao_atual = "COMBATE" if roll < 0.6 else "CIRCULAR"
        
        # === MODIFICADORES DE TRAÇO ===
        if "AGRESSIVO" in self.tracos and self.acao_atual in ["CIRCULAR", "BLOQUEAR"]:
            if random.random() < 0.3:
                self.acao_atual = "APROXIMAR"
        
        if "CALCULISTA" in self.tracos and self.acao_atual == "MATAR":
            if random.random() < 0.4:
                self.acao_atual = "CIRCULAR"