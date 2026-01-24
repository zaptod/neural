import random
import math
from config import *
from physics import normalizar_angulo
# Importação necessária para ler os dados da skill
from skills import get_skill_data

class AIBrain:
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

    def definir_arquetipo(self):
        p = self.parent
        # Prioriza classe
        if "Mago" in p.classe_nome: self.arquetipo = "MAGO"; p.alcance_ideal = 8.0; return
        
        arma = p.dados.arma_obj
        if not arma: self.arquetipo = "MONGE"; p.alcance_ideal = 1.0; return

        if "Orbital" in arma.tipo:
            self.arquetipo = "SENTINELA"
            p.alcance_ideal = (arma.distancia / 100.0 * p.fator_escala) + p.raio_fisico + 0.5
        elif "Reta" in arma.tipo:
            comp_total = (arma.comp_cabo + arma.comp_lamina)
            if arma.peso > 8.0: self.arquetipo = "COLOSSO"
            elif arma.peso < 3.0: self.arquetipo = "ASSASSINO"
            elif comp_total > 80.0: self.arquetipo = "LANCEIRO"
            else: self.arquetipo = "GUERREIRO"
            p.alcance_ideal = (comp_total / 100.0 * 0.9 * p.fator_escala) + p.raio_fisico

    def definir_tracos(self):
        possibilidades = ["COVARDE", "VINGATIVO", "IMPRUDENTE", "ANALITICO", "SALTADOR", "SPAMMER", "PACIENTE"]
        self.tracos = random.sample(possibilidades, 2)
        if "IMPRUDENTE" in self.tracos: self.parent.alcance_ideal *= 0.8
        if "COVARDE" in self.tracos: self.parent.alcance_ideal *= 1.2

    def processar(self, dt, distancia, inimigo):
        self.raiva = max(0, self.raiva - 0.005)
        self.medo = max(0, self.medo - 0.005)
        self.timer_decisao -= dt
        
        p = self.parent

        # --- 1. DECISÃO DE USO DE HABILIDADE (IA Genérica) ---
        # Verifica se tem skill, se não está em cooldown e se tem mana
        if p.skill_arma_nome != "Nenhuma" and p.cd_skill_arma <= 0 and p.mana >= p.custo_skill_arma:
            
            # Busca os dados da skill para saber o TIPO
            dados_skill = get_skill_data(p.skill_arma_nome)
            tipo_skill = dados_skill.get("tipo", "NADA")
            
            usar = False
            
            # Lógica baseada no TIPO da skill (Funciona para qualquer nome!)
            if tipo_skill == "PROJETIL":
                # Projéteis são bons de média distância
                # Mas se for "Sônico" (vida curta), tem que ser de perto
                alcance_skill = dados_skill.get("vida", 1.0) * dados_skill.get("velocidade", 10.0)
                
                # Só atira se o inimigo estiver dentro do alcance teórico do projétil
                if distancia < alcance_skill and distancia > 2.0:
                    usar = True
                    # Se for Mago ou Spammer, é mais agressivo no gatilho
                    if self.arquetipo == "MAGO" or "SPAMMER" in self.tracos: 
                        usar = True
            
            elif tipo_skill == "AREA" or tipo_skill == "BUFF":
                # Skills de área/buff geralmente são defensivas ou curto alcance
                if distancia < 3.5:
                    usar = True

            # Sobrescrita de Arquétipo (Magos tentam usar tudo sempre)
            if self.arquetipo == "MAGO":
                usar = True 

            # Execução
            if usar:
                if p.usar_skill_arma():
                    # Reação pós-uso
                    if self.arquetipo == "MAGO" or "COVARDE" in self.tracos:
                        self.acao_atual = "RECUAR"
                    return

        # 2. Tomada de Decisão de Movimento
        if self.timer_decisao <= 0:
            self.timer_decisao = random.uniform(0.2, 0.6)
            self.decidir_movimento(distancia, inimigo)

    def decidir_movimento(self, distancia, inimigo):
        p = self.parent
        roll = random.random()

        if p.modo_adrenalina:
            self.acao_atual = "MATAR"
            return

        if p.estamina < 15:
            self.acao_atual = "RECUAR"
            return

        # Arquétipos
        if self.arquetipo == "MAGO":
            if distancia < 6.0: self.acao_atual = "FUGIR"
            else: self.acao_atual = "BLOQUEAR" # Fica parado mirando
            
        elif self.arquetipo == "SENTINELA":
            self.acao_atual = "BLOQUEAR" if distancia < p.alcance_ideal + 1.5 else "APROXIMAR_LENTO"
            
        elif self.arquetipo == "ASSASSINO":
            if roll < 0.4: self.acao_atual = "CIRCULAR"
            elif roll < 0.7: self.acao_atual = "FLANQUEAR"
            else: self.acao_atual = "ATAQUE_RAPIDO"
            
        elif self.arquetipo == "COLOSSO":
            self.acao_atual = "ESMAGAR"
            
        else: # GUERREIRO / LANCEIRO
            if distancia > p.alcance_ideal + 1.5: self.acao_atual = "APROXIMAR"
            elif distancia < p.alcance_ideal - 1.0: self.acao_atual = "RECUAR"
            else:
                self.acao_atual = "COMBATE" if roll < 0.6 else "CIRCULAR"