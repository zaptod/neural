"""
=============================================================================
NEURAL FIGHTS - Cérebro da IA v7.0 IMPACT EDITION
=============================================================================
Sistema de inteligência artificial com personalidade procedural.

Combinações possíveis:
- 50+ traços × 5 slots = milhares de combinações de traços
- 25+ arquétipos
- 15+ estilos de luta
- 20+ quirks
- 10+ filosofias
- 10 humores dinâmicos

Total: CENTENAS DE MILHARES de personalidades únicas!
=============================================================================
"""

import random
import math

from config import PPM
from core.physics import normalizar_angulo
from core.skills import get_skill_data
from models import get_class_data
from ai.choreographer import CombatChoreographer
from ai.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES
)


class AIBrain:
    """
    Cérebro da IA v7.0 - Sistema de personalidade procedural com inteligência de alcance.
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.timer_decisao = 0.0
        self.acao_atual = "NEUTRO"
        self.dir_circular = random.choice([-1, 1])
        
        # === EMOÇÕES (0.0 a 1.0) ===
        self.medo = 0.0
        self.raiva = 0.0
        self.confianca = 0.5
        self.frustracao = 0.0
        self.adrenalina = 0.0
        self.excitacao = 0.0
        self.tedio = 0.0
        
        # === HUMOR ATUAL ===
        self.humor = "CALMO"
        self.humor_timer = 0.0
        
        # === MEMÓRIA DE COMBATE ===
        self.hits_recebidos_total = 0
        self.hits_dados_total = 0
        self.hits_recebidos_recente = 0
        self.hits_dados_recente = 0
        self.tempo_desde_dano = 5.0
        self.tempo_desde_hit = 5.0
        self.vezes_que_fugiu = 0
        self.ultimo_hp = parent.vida
        self.combo_atual = 0
        self.max_combo = 0
        self.tempo_combate = 0.0
        
        # === PERSONALIDADE GERADA ===
        self.arquetipo = "GUERREIRO"
        self.estilo_luta = "BALANCED"
        self.filosofia = "EQUILIBRIO"
        self.tracos = []
        self.quirks = []
        self.agressividade_base = 0.5
        
        # === COOLDOWNS INTERNOS ===
        self.cd_dash = 0.0
        self.cd_pulo = 0.0
        self.cd_mudanca_direcao = 0.0
        self.cd_reagir = 0.0
        self.cd_buff = 0.0
        self.cd_quirk = 0.0
        self.cd_mudanca_humor = 0.0
        
        # === CACHE DE SKILLS ===
        self.skills_por_tipo = {
            "PROJETIL": [],
            "BEAM": [],
            "AREA": [],
            "DASH": [],
            "BUFF": [],
            "SUMMON": []
        }
        
        # === ESTADO ESPECIAL ===
        self.modo_berserk = False
        self.modo_defensivo = False
        self.modo_burst = False
        self.executando_quirk = False
        
        # === SISTEMA DE COREOGRAFIA v5.0 ===
        self.momento_cinematografico = None
        self.acao_sincronizada = None
        self.respondendo_a_oponente = False
        self.memoria_oponente = {
            "ultima_acao": None,
            "padrao_detectado": None,
            "vezes_fugiu": 0,
            "vezes_atacou": 0,
            "estilo_percebido": None,
            "ameaca_nivel": 0.5,
        }
        self.reacao_pendente = None
        self.tempo_reacao = 0.0
        
        # Gera personalidade única
        self._gerar_personalidade()

    # =========================================================================
    # GERAÇÃO DE PERSONALIDADE
    # =========================================================================
    
    def _gerar_personalidade(self):
        """Gera uma personalidade completamente única"""
        self._definir_arquetipo()
        self._selecionar_estilo()
        self._selecionar_filosofia()
        self._gerar_tracos()
        self._gerar_quirks()
        self._calcular_agressividade()
        self._categorizar_skills()
        self._aplicar_modificadores_iniciais()

    def _definir_arquetipo(self):
        """Define arquétipo baseado na classe"""
        p = self.parent
        classe = p.classe_nome.lower() if p.classe_nome else ""
        
        arquetipo_map = {
            "mago": "MAGO", "piromante": "PIROMANTE", "criomante": "CRIOMANTE",
            "eletromante": "ELETROMANTE", "necromante": "INVOCADOR", "feiticeiro": "MAGO",
            "bruxo": "MAGO_CONTROLE", "assassino": "ASSASSINO", "ninja": "NINJA",
            "sombra": "SOMBRA", "berserker": "BERSERKER", "bárbaro": "BERSERKER",
            "cavaleiro": "SENTINELA", "paladino": "PALADINO", "ladino": "LADINO",
            "druida": "DRUIDA", "monge": "MONGE", "arqueiro": "ARQUEIRO",
            "caçador": "ARQUEIRO", "guerreiro": "GUERREIRO", "samurai": "SAMURAI",
            "ronin": "RONIN", "espadachim": "DUELISTA", "gladiador": "GLADIADOR",
            "guardião": "GUARDIAO", "templário": "PALADINO",
        }
        
        for key, arq in arquetipo_map.items():
            if key in classe:
                self.arquetipo = arq
                break
        else:
            self._definir_arquetipo_por_arma()
        
        if self.arquetipo in ARQUETIPO_DATA:
            data = ARQUETIPO_DATA[self.arquetipo]
            p.alcance_ideal = data["alcance"]
            self.estilo_luta = data["estilo"]
            self.agressividade_base = data["agressividade"]

    def _definir_arquetipo_por_arma(self):
        """Define arquétipo pela arma se classe não mapeada"""
        p = self.parent
        arma = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        
        if not arma:
            self.arquetipo = "MONGE"
            p.alcance_ideal = 1.5
            return

        tipo = getattr(arma, 'tipo', '')
        peso = getattr(arma, 'peso', 5.0)
        
        if "Orbital" in tipo:
            self.arquetipo = "SENTINELA"
        elif "Arco" in tipo:
            self.arquetipo = "ARQUEIRO"
        elif "Mágica" in tipo or "Cajado" in tipo:
            self.arquetipo = "MAGO"
        elif "Corrente" in tipo:
            self.arquetipo = "ACROBATA"
        elif "Arremesso" in tipo:
            self.arquetipo = "LANCEIRO"
        elif peso > 10.0:
            self.arquetipo = "COLOSSO"
        elif peso < 2.5:
            self.arquetipo = "DUELISTA"
        elif peso > 6.0:
            self.arquetipo = "GUERREIRO_PESADO"
        else:
            self.arquetipo = "GUERREIRO"

    def _selecionar_estilo(self):
        """Seleciona estilo de luta"""
        if random.random() < 0.7:
            return
        
        estilos_alternativos = {
            "MAGO": ["BURST", "CONTROL", "KITE"],
            "ASSASSINO": ["AMBUSH", "COMBO", "OPPORTUNIST"],
            "GUERREIRO": ["AGGRO", "COUNTER", "TANK"],
            "ARQUEIRO": ["RANGED", "MOBILE", "POKE"],
            "BERSERKER": ["AGGRO", "BURST", "BERSERK"],
        }
        
        if self.arquetipo in estilos_alternativos:
            self.estilo_luta = random.choice(estilos_alternativos[self.arquetipo])
        else:
            self.estilo_luta = random.choice(list(ESTILOS_LUTA.keys()))

    def _selecionar_filosofia(self):
        """Seleciona filosofia de combate"""
        filosofias_por_estilo = {
            "BERSERK": ["DOMINACAO", "PRESSAO", "EXECUCAO"],
            "TANK": ["RESISTENCIA", "SOBREVIVENCIA", "EQUILIBRIO"],
            "KITE": ["SOBREVIVENCIA", "PACIENCIA", "OPORTUNISMO"],
            "BURST": ["EXECUCAO", "OPORTUNISMO", "DOMINACAO"],
            "COUNTER": ["PACIENCIA", "OPORTUNISMO", "EQUILIBRIO"],
        }
        
        if self.estilo_luta in filosofias_por_estilo:
            self.filosofia = random.choice(filosofias_por_estilo[self.estilo_luta])
        else:
            self.filosofia = random.choice(list(FILOSOFIAS.keys()))

    def _gerar_tracos(self):
        """Gera combinação única de traços"""
        num_tracos = random.randint(5, 7)
        
        categorias = [
            TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
            TRACOS_SKILLS, TRACOS_MENTAL,
        ]
        
        self.tracos = []
        
        for cat in categorias:
            self.tracos.append(random.choice(cat))
        
        extras_needed = num_tracos - len(self.tracos)
        todos_restantes = [t for t in TODOS_TRACOS if t not in self.tracos]
        
        if random.random() < 0.4:
            especial = random.choice(TRACOS_ESPECIAIS)
            if especial not in self.tracos:
                self.tracos.append(especial)
                extras_needed -= 1
        
        if extras_needed > 0:
            extras = random.sample(todos_restantes, min(extras_needed, len(todos_restantes)))
            self.tracos.extend(extras)
        
        self._resolver_conflitos_tracos()

    def _resolver_conflitos_tracos(self):
        """Remove traços que conflitam"""
        conflitos = [
            ("COVARDE", "BERSERKER"), ("MEDROSO", "IMPLACAVEL"),
            ("ESTATICO", "VELOZ"), ("CALCULISTA", "IMPRUDENTE"),
            ("PACIENTE", "FURIOSO"), ("FRIO", "EMOTIVO"),
            ("TEIMOSO", "ADAPTAVEL"),
        ]
        
        for t1, t2 in conflitos:
            if t1 in self.tracos and t2 in self.tracos:
                self.tracos.remove(random.choice([t1, t2]))

    def _gerar_quirks(self):
        """Gera quirks únicos"""
        num_quirks = random.randint(1, 3)
        
        quirks_por_traco = {
            "BERSERKER": ["FURIA_CEGA", "GRITO_GUERRA"],
            "VINGATIVO": ["OLHO_VERMELHO", "PERSISTENTE"],
            "ASSASSINO_NATO": ["FINALIZADOR", "CONTRA_ATAQUE_PERFEITO"],
            "PHOENIX": ["SEGUNDO_FOLEGO", "EXPLOSAO_FINAL"],
            "VAMPIRO": ["VAMPIRICO", "SEDE_SANGUE"],
            "SHOWMAN": ["PROVOCADOR", "DANCA_MORTE"],
            "EVASIVO": ["ESQUIVA_REFLEXA", "INSTINTO_ANIMAL"],
            "PACIENTE": ["PACIENCIA_INFINITA", "CALCULISTA_FRIO"],
        }
        
        self.quirks = []
        
        for traco in self.tracos:
            if traco in quirks_por_traco and random.random() < 0.5:
                quirk = random.choice(quirks_por_traco[traco])
                if quirk not in self.quirks:
                    self.quirks.append(quirk)
        
        while len(self.quirks) < num_quirks:
            quirk = random.choice(list(QUIRKS.keys()))
            if quirk not in self.quirks:
                self.quirks.append(quirk)

    def _calcular_agressividade(self):
        """Calcula agressividade final"""
        agg = self.agressividade_base
        
        if self.filosofia in FILOSOFIAS:
            agg += FILOSOFIAS[self.filosofia]["mod_agressividade"]
        
        tracos_agressivos = ["IMPRUDENTE", "AGRESSIVO", "BERSERKER", "SANGUINARIO", 
                           "PREDADOR", "SELVAGEM", "IMPLACAVEL", "FURIOSO", "BRUTAL"]
        tracos_defensivos = ["COVARDE", "CAUTELOSO", "PACIENTE", "PARANOICO", 
                           "MEDROSO", "PRUDENTE", "EVASIVO"]
        
        for traco in self.tracos:
            if traco in tracos_agressivos:
                agg += 0.08
            elif traco in tracos_defensivos:
                agg -= 0.06
        
        self.agressividade_base = max(0.1, min(0.95, agg))

    def _categorizar_skills(self):
        """Categoriza todas as skills disponíveis"""
        p = self.parent
        
        if hasattr(p, 'skill_arma_nome') and p.skill_arma_nome and p.skill_arma_nome != "Nenhuma":
            data = get_skill_data(p.skill_arma_nome)
            self._adicionar_skill(p.skill_arma_nome, data, "arma")
        
        if hasattr(p, 'classe_nome') and p.classe_nome:
            class_data = get_class_data(p.classe_nome)
            for skill_nome in class_data.get("skills_afinidade", []):
                data = get_skill_data(skill_nome)
                self._adicionar_skill(skill_nome, data, "classe")

    def _adicionar_skill(self, nome, data, fonte):
        """Adiciona skill à lista categorizada"""
        tipo = data.get("tipo", "NADA")
        if tipo == "NADA" or tipo not in self.skills_por_tipo:
            return
        
        info = {
            "nome": nome, "data": data, "fonte": fonte,
            "tipo": tipo, "custo": data.get("custo", 15),
        }
        self.skills_por_tipo[tipo].append(info)

    def _aplicar_modificadores_iniciais(self):
        """Aplica modificadores baseados na personalidade"""
        p = self.parent
        
        if "IMPRUDENTE" in self.tracos:
            p.alcance_ideal *= 0.7
            self.confianca = 0.8
        if "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
            p.alcance_ideal *= 1.3
            self.medo = 0.2
        if "AGRESSIVO" in self.tracos:
            p.alcance_ideal *= 0.85
        if "CAUTELOSO" in self.tracos or "PRUDENTE" in self.tracos:
            p.alcance_ideal *= 1.2
        if "BERSERKER" in self.tracos:
            self.raiva = 0.3
        if "FURIOSO" in self.tracos:
            self.raiva = 0.4
        if "FRIO" in self.tracos:
            self.medo = 0.0
            self.raiva = 0.0

    # =========================================================================
    # PROCESSAMENTO PRINCIPAL
    # =========================================================================
    
    def processar(self, dt, distancia, inimigo):
        """Processa decisões da IA a cada frame"""
        p = self.parent
        self.tempo_combate += dt
        
        self._atualizar_cooldowns(dt)
        self._detectar_dano()
        self._atualizar_emocoes(dt, distancia, inimigo)
        self._atualizar_humor(dt)
        self._processar_modos_especiais(dt, distancia, inimigo)
        
        # Sistema de Coreografia
        self._observar_oponente(inimigo, distancia)
        
        choreographer = CombatChoreographer.get_instance()
        acao_sync = choreographer.get_acao_sincronizada(p)
        
        if acao_sync:
            if self._executar_acao_sincronizada(acao_sync, distancia, inimigo):
                return
        
        if self._processar_reacao_oponente(dt, distancia, inimigo):
            return
        
        if self._processar_quirks(dt, distancia, inimigo):
            return
        
        if self._processar_reacoes(dt, distancia, inimigo):
            return
        
        if self._processar_skills(distancia, inimigo):
            return
        
        self.timer_decisao -= dt
        if self.timer_decisao <= 0:
            self._decidir_movimento(distancia, inimigo)
            self._calcular_timer_decisao()

    # =========================================================================
    # SISTEMA DE COREOGRAFIA
    # =========================================================================
    
    def _observar_oponente(self, inimigo, distancia):
        """Observa o que o oponente está fazendo"""
        if not hasattr(inimigo, 'ai') or not inimigo.ai:
            return
        
        ai_ini = inimigo.ai
        mem = self.memoria_oponente
        
        acao_oponente = ai_ini.acao_atual
        
        if acao_oponente != mem["ultima_acao"]:
            mem["ultima_acao"] = acao_oponente
            
            if acao_oponente in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "APROXIMAR"]:
                mem["vezes_atacou"] += 1
            elif acao_oponente in ["FUGIR", "RECUAR"]:
                mem["vezes_fugiu"] += 1
        
        if mem["vezes_atacou"] > mem["vezes_fugiu"] * 2:
            mem["estilo_percebido"] = "AGRESSIVO"
            mem["ameaca_nivel"] = min(1.0, mem["ameaca_nivel"] + 0.02)
        elif mem["vezes_fugiu"] > mem["vezes_atacou"] * 2:
            mem["estilo_percebido"] = "DEFENSIVO"
            mem["ameaca_nivel"] = max(0.2, mem["ameaca_nivel"] - 0.01)
        else:
            mem["estilo_percebido"] = "EQUILIBRADO"
        
        self._gerar_reacao_inteligente(acao_oponente, distancia, inimigo)
    
    def _gerar_reacao_inteligente(self, acao_oponente, distancia, inimigo):
        """Gera uma reação inteligente ao oponente"""
        mem = self.memoria_oponente
        
        if acao_oponente == "MATAR" and distancia < 4.0:
            if "REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos:
                self.reacao_pendente = "CONTRA_ATAQUE"
            elif "COVARDE" in self.tracos or self.medo > 0.6:
                self.reacao_pendente = "RECUAR"
            elif "BERSERKER" in self.tracos or self.raiva > 0.7:
                self.reacao_pendente = "CONTRA_MATAR"
            elif random.random() < 0.3:
                self.reacao_pendente = "ESQUIVAR"
        
        elif acao_oponente == "FUGIR":
            if "PERSEGUIDOR" in self.tracos or "PREDADOR" in self.tracos:
                self.reacao_pendente = "PERSEGUIR"
                self.confianca = min(1.0, self.confianca + 0.1)
            elif "PACIENTE" in self.tracos:
                self.reacao_pendente = "ESPERAR"
            elif random.random() < 0.4:
                self.reacao_pendente = "PRESSIONAR"
        
        elif acao_oponente == "CIRCULAR":
            if "FLANQUEADOR" in self.tracos:
                self.reacao_pendente = "CONTRA_CIRCULAR"
            elif random.random() < 0.3:
                self.reacao_pendente = "INTERCEPTAR"
        
        elif acao_oponente == "BLOQUEAR":
            if "CALCULISTA" in self.tracos:
                self.reacao_pendente = "ESPERAR_ABERTURA"
            elif "IMPRUDENTE" in self.tracos or "AGRESSIVO" in self.tracos:
                self.reacao_pendente = "FURAR_GUARDA"
            elif self.filosofia == "PACIENCIA":
                self.reacao_pendente = "ESPERAR"
    
    def _processar_reacao_oponente(self, dt, distancia, inimigo):
        """Processa reação pendente ao oponente"""
        if not self.reacao_pendente:
            return False
        
        reacao = self.reacao_pendente
        self.reacao_pendente = None
        
        chance = 0.6
        if "ADAPTAVEL" in self.tracos:
            chance = 0.8
        if "TEIMOSO" in self.tracos:
            chance = 0.3
        if "FRIO" in self.tracos:
            chance = 0.7
        
        if random.random() > chance:
            return False
        
        acoes = {
            "CONTRA_ATAQUE": ("CONTRA_ATAQUE", lambda: setattr(self, 'excitacao', min(1.0, self.excitacao + 0.2))),
            "CONTRA_MATAR": ("MATAR", lambda: (setattr(self, 'raiva', min(1.0, self.raiva + 0.15)),
                                               setattr(self, 'adrenalina', min(1.0, self.adrenalina + 0.2)))),
            "RECUAR": ("RECUAR", None),
            "PERSEGUIR": ("APROXIMAR", lambda: setattr(self, 'excitacao', min(1.0, self.excitacao + 0.15))),
            "PRESSIONAR": ("APROXIMAR", None),
            "INTERCEPTAR": ("FLANQUEAR", None),
            "ESPERAR": ("BLOQUEAR", None),
            "ESPERAR_ABERTURA": ("CIRCULAR", None),
            "FURAR_GUARDA": ("MATAR", None),
        }
        
        if reacao == "ESQUIVAR":
            if self.parent.z == 0 and self.cd_pulo <= 0:
                self.parent.vel_z = 12.0
                self.cd_pulo = 1.0
            self.acao_atual = "CIRCULAR"
            return True
        
        if reacao == "CONTRA_CIRCULAR":
            if hasattr(inimigo, 'ai') and inimigo.ai:
                self.dir_circular = -inimigo.ai.dir_circular
            self.acao_atual = "CIRCULAR"
            return True
        
        if reacao in acoes:
            self.acao_atual, callback = acoes[reacao]
            if callback:
                callback()
            return True
        
        return False
    
    def _executar_acao_sincronizada(self, acao, distancia, inimigo):
        """Executa ação sincronizada de momento cinematográfico"""
        p = self.parent
        
        acoes = {
            "CIRCULAR_LENTO": lambda: setattr(self, 'timer_decisao', 0.5) or "CIRCULAR",
            "ENCARAR": lambda: "BLOQUEAR",
            "TROCAR_GOLPES": lambda: random.choice(["MATAR", "ATAQUE_RAPIDO", "COMBATE"]),
            "RECUPERAR": lambda: setattr(self, 'timer_decisao', 0.8) or "RECUAR",
            "PERSEGUIR": lambda: "APROXIMAR",
        }
        
        if acao == "PREPARAR_ATAQUE":
            self.modo_burst = True
            self.adrenalina = min(1.0, self.adrenalina + 0.05)
            self.acao_atual = "APROXIMAR_LENTO" if distancia > 4.0 else "BLOQUEAR"
            return True
        
        if acao == "FUGIR_DRAMATICO":
            if self.raiva > 0.7 or random.random() < 0.2:
                self.acao_atual = "MATAR"
            else:
                self.acao_atual = "FUGIR"
            return True
        
        if acao == "CIRCULAR_SINCRONIZADO":
            if hasattr(inimigo, 'ai') and inimigo.ai:
                self.dir_circular = inimigo.ai.dir_circular
            self.acao_atual = "CIRCULAR"
            return True
        
        if acao == "CLASH":
            self.acao_atual = "MATAR"
            self.excitacao = 1.0
            self.adrenalina = min(1.0, self.adrenalina + 0.3)
            return True
        
        if acao == "ATAQUE_FINAL":
            self.modo_burst = True
            self.modo_berserk = True
            self.acao_atual = "MATAR"
            self._usar_tudo()
            return True
        
        if acao in acoes:
            result = acoes[acao]()
            if isinstance(result, str):
                self.acao_atual = result
            return True
        
        return False
    
    def _usar_tudo(self):
        """Usa todas as skills disponíveis"""
        for tipo in ["BUFF", "DASH", "AREA", "BEAM", "PROJETIL"]:
            for skill in self.skills_por_tipo.get(tipo, []):
                self._usar_skill(skill)
    
    def on_momento_cinematografico(self, tipo, iniciando, duracao):
        """Callback quando momento cinematográfico começa/termina"""
        self.momento_cinematografico = tipo if iniciando else None
        
        if iniciando:
            if tipo == "CLASH":
                self.excitacao = 1.0
                self.adrenalina = min(1.0, self.adrenalina + 0.3)
            elif tipo == "STANDOFF":
                self.confianca = 0.5
            elif tipo == "FINAL_SHOWDOWN":
                self.adrenalina = 1.0
                self.excitacao = 1.0
                self.medo = 0.0
            elif tipo == "FACE_OFF":
                self.excitacao = min(1.0, self.excitacao + 0.2)
            elif tipo == "CLIMAX_CHARGE":
                self.modo_burst = True
    
    def on_hit_recebido_de(self, atacante):
        """Callback quando recebe hit de um atacante específico"""
        self.memoria_oponente["ameaca_nivel"] = min(1.0, 
            self.memoria_oponente["ameaca_nivel"] + 0.15)
        
        if "VINGATIVO" in self.tracos:
            self.reacao_pendente = "CONTRA_MATAR"
        elif "COVARDE" in self.tracos and self.medo > 0.4:
            self.reacao_pendente = "FUGIR"
        elif "REATIVO" in self.tracos:
            self.reacao_pendente = "CONTRA_ATAQUE"

    # =========================================================================
    # ATUALIZAÇÃO DE ESTADOS
    # =========================================================================

    def _atualizar_cooldowns(self, dt):
        """Atualiza cooldowns"""
        self.cd_dash = max(0, self.cd_dash - dt)
        self.cd_pulo = max(0, self.cd_pulo - dt)
        self.cd_mudanca_direcao = max(0, self.cd_mudanca_direcao - dt)
        self.cd_reagir = max(0, self.cd_reagir - dt)
        self.cd_buff = max(0, self.cd_buff - dt)
        self.cd_quirk = max(0, self.cd_quirk - dt)
        self.cd_mudanca_humor = max(0, self.cd_mudanca_humor - dt)
        self.tempo_desde_dano += dt
        self.tempo_desde_hit += dt

    def _detectar_dano(self):
        """Detecta dano recebido"""
        p = self.parent
        
        if p.vida < self.ultimo_hp:
            dano = self.ultimo_hp - p.vida
            self.hits_recebidos_total += 1
            self.hits_recebidos_recente += 1
            self.tempo_desde_dano = 0.0
            self.combo_atual = 0
            self._reagir_ao_dano(dano)
        
        self.ultimo_hp = p.vida

    def _reagir_ao_dano(self, dano):
        """Reações emocionais ao dano"""
        if "VINGATIVO" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.25)
        if "BERSERKER" in self.tracos or "BERSERKER_RAGE" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.15)
            self.adrenalina = min(1.0, self.adrenalina + 0.2)
        if "FURIOSO" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.2)
        if "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
            self.medo = min(1.0, self.medo + 0.2)
        if "PARANOICO" in self.tracos:
            self.medo = min(1.0, self.medo + 0.15)
        if "FRIO" not in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.05)
        self.frustracao = min(1.0, self.frustracao + 0.1)

    def _atualizar_emocoes(self, dt, distancia, inimigo):
        """Atualiza estado emocional"""
        p = self.parent
        hp_pct = p.vida / p.vida_max
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0
        
        decay = 0.005 if "FRIO" in self.tracos else 0.015
        if "EMOTIVO" in self.tracos:
            decay *= 0.5
        
        self.raiva = max(0, self.raiva - decay * dt * 60)
        self.medo = max(0, self.medo - decay * dt * 60)
        self.frustracao = max(0, self.frustracao - 0.005 * dt * 60)
        self.adrenalina = max(0, self.adrenalina - 0.01 * dt * 60)
        self.excitacao = max(0, self.excitacao - 0.008 * dt * 60)
        self.tedio = max(0, self.tedio - 0.01 * dt * 60)
        
        if self.tempo_desde_dano > 3.0:
            self.hits_recebidos_recente = max(0, self.hits_recebidos_recente - 1)
        if self.tempo_desde_hit > 3.0:
            self.hits_dados_recente = max(0, self.hits_dados_recente - 1)
        
        # Medo
        if "DETERMINADO" not in self.tracos and "FRIO" not in self.tracos:
            if hp_pct < 0.15:
                self.medo = min(1.0, self.medo + 0.08 * dt * 60)
            elif hp_pct < 0.3:
                self.medo = min(0.8, self.medo + 0.03 * dt * 60)
            if self.hits_recebidos_recente >= 3:
                self.medo = min(1.0, self.medo + 0.15)
        
        # Confiança
        hp_diff = hp_pct - inimigo_hp_pct
        target_conf = 0.5 + hp_diff * 0.4
        self.confianca += (target_conf - self.confianca) * 0.05 * dt * 60
        self.confianca = max(0.1, min(1.0, self.confianca))
        
        # Excitação
        if distancia < 3.0:
            self.excitacao = min(1.0, self.excitacao + 0.02 * dt * 60)
        if self.combo_atual > 2:
            self.excitacao = min(1.0, self.excitacao + 0.05)
        
        # Tédio
        if distancia > 8.0 and self.tempo_combate > 10.0:
            self.tedio = min(1.0, self.tedio + 0.01 * dt * 60)
        
        # Adrenalina
        if hp_pct < 0.2 or (distancia < 2.0 and self.raiva > 0.5):
            self.adrenalina = min(1.0, self.adrenalina + 0.04 * dt * 60)
        
        # Mudança de direção
        if self.cd_mudanca_direcao <= 0:
            chance = 0.15 if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos else 0.08
            if random.random() < chance * dt * 60:
                self.dir_circular *= -1
                self.cd_mudanca_direcao = random.uniform(0.5, 2.0)

    def _atualizar_humor(self, dt):
        """Atualiza humor baseado nas emoções"""
        if self.cd_mudanca_humor > 0:
            return
        
        novo_humor = self.humor
        
        if self.raiva > 0.7:
            novo_humor = "FURIOSO"
        elif self.medo > 0.6:
            novo_humor = "ASSUSTADO"
        elif self.medo > 0.4 and self.confianca < 0.3:
            novo_humor = "NERVOSO"
        elif self.adrenalina > 0.6:
            novo_humor = "DETERMINADO"
        elif self.confianca > 0.7:
            novo_humor = "CONFIANTE"
        elif self.frustracao > 0.5:
            novo_humor = "FURIOSO" if random.random() < 0.5 else "NERVOSO"
        elif self.excitacao > 0.6:
            novo_humor = "ANIMADO"
        elif self.tedio > 0.5:
            novo_humor = "ENTEDIADO"
        elif self.confianca > 0.4 and self.raiva < 0.3 and self.medo < 0.3:
            novo_humor = "CALMO"
        elif self.parent.vida < self.parent.vida_max * 0.2:
            novo_humor = "DESESPERADO"
        else:
            novo_humor = "FOCADO"
        
        if novo_humor != self.humor:
            self.humor = novo_humor
            self.cd_mudanca_humor = random.uniform(2.0, 5.0)

    def _processar_modos_especiais(self, dt, distancia, inimigo):
        """Processa modos especiais de combate"""
        p = self.parent
        hp_pct = p.vida / p.vida_max
        
        if "BERSERKER" in self.tracos or "BERSERKER_RAGE" in self.tracos:
            if hp_pct < 0.4 and self.raiva > 0.5:
                self.modo_berserk = True
            elif hp_pct > 0.6 or self.raiva < 0.2:
                self.modo_berserk = False
        
        if "PRUDENTE" in self.tracos or "CAUTELOSO" in self.tracos:
            if hp_pct < 0.3 or self.medo > 0.6:
                self.modo_defensivo = True
            elif hp_pct > 0.5 and self.medo < 0.3:
                self.modo_defensivo = False
        
        if "EXPLOSIVO" in self.tracos or self.estilo_luta == "BURST":
            inimigo_hp_pct = inimigo.vida / inimigo.vida_max
            if inimigo_hp_pct < 0.4 or (p.mana > p.mana_max * 0.8 and distancia < 5.0):
                self.modo_burst = True
            elif inimigo_hp_pct > 0.6 or p.mana < p.mana_max * 0.3:
                self.modo_burst = False

    # =========================================================================
    # QUIRKS
    # =========================================================================
    
    def _processar_quirks(self, dt, distancia, inimigo):
        """Processa quirks únicos"""
        if self.cd_quirk > 0 or not self.quirks:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max
        
        for quirk in self.quirks:
            if self._executar_quirk(quirk, distancia, hp_pct, inimigo_hp_pct, inimigo):
                self.cd_quirk = random.uniform(3.0, 8.0)
                return True
        
        return False

    def _executar_quirk(self, quirk, distancia, hp_pct, inimigo_hp_pct, inimigo):
        """Executa um quirk específico"""
        p = self.parent
        
        quirk_handlers = {
            "GRITO_GUERRA": lambda: distancia < 5.0 and random.random() < 0.05 and 
                (setattr(self, 'raiva', min(1.0, self.raiva + 0.3)), setattr(self, 'acao_atual', "MATAR")),
            "DANCA_MORTE": lambda: self.tempo_combate > 15.0 and distancia < 4.0 and random.random() < 0.08 and
                (setattr(self, 'acao_atual', "CIRCULAR"), setattr(self, 'dir_circular', self.dir_circular * -1)),
            "SEGUNDO_FOLEGO": lambda: hp_pct < 0.2 and p.estamina < 20 and
                (setattr(p, 'estamina', min(p.estamina + 30, 100)), setattr(self, 'adrenalina', 1.0)),
            "FINALIZADOR": lambda: inimigo_hp_pct < 0.25 and distancia < 4.0 and random.random() < 0.15 and
                (setattr(self, 'modo_burst', True), setattr(self, 'acao_atual', "MATAR")),
            "FURIA_CEGA": lambda: self.raiva > 0.9 and
                (setattr(self, 'modo_berserk', True), setattr(self, 'modo_defensivo', False), setattr(self, 'acao_atual', "MATAR")),
            "PROVOCADOR": lambda: distancia > 3.0 and random.random() < 0.02 and setattr(self, 'acao_atual', "BLOQUEAR"),
            "INSTINTO_ANIMAL": lambda: distancia < 2.0 and self.tempo_desde_dano < 1.0 and setattr(self, 'acao_atual', "RECUAR"),
        }
        
        if quirk == "ESQUIVA_REFLEXA":
            if self.tempo_desde_dano < 0.5 and p.z == 0 and self.cd_pulo <= 0:
                p.vel_z = 12.0
                self.cd_pulo = 1.5
                return True
            return False
        
        if quirk == "EXPLOSAO_FINAL":
            if hp_pct < 0.1 and p.mana > p.mana_max * 0.5:
                self.modo_burst = True
                for tipo in ["AREA", "BEAM", "PROJETIL"]:
                    for skill in self.skills_por_tipo.get(tipo, []):
                        self._usar_skill(skill)
                return True
            return False
        
        if quirk == "REGENERADOR":
            if self.tempo_desde_dano > 5.0 and hp_pct < 0.9:
                p.vida = min(p.vida_max, p.vida + 0.5)
            return False
        
        if quirk in quirk_handlers:
            result = quirk_handlers[quirk]()
            return bool(result)
        
        return False

    # =========================================================================
    # REAÇÕES
    # =========================================================================
    
    def _processar_reacoes(self, dt, distancia, inimigo):
        """Processa reações imediatas"""
        if self.cd_reagir > 0:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max
        
        if self._tentar_pulo_evasivo(distancia, hp_pct):
            return True
        if self._tentar_dash_emergencia(distancia, hp_pct, inimigo):
            return True
        if self._tentar_cura_emergencia(hp_pct):
            return True
        if self._tentar_contra_ataque(distancia, inimigo):
            return True
        
        return False

    def _tentar_pulo_evasivo(self, distancia, hp_pct):
        """Pulo evasivo"""
        p = self.parent
        
        if p.z != 0 or self.cd_pulo > 0:
            return False
        
        chance = 0.03
        if "SALTADOR" in self.tracos:
            chance = 0.12
        if "ACROBATA" in self.tracos:
            chance = 0.10
        if "EVASIVO" in self.tracos:
            chance = 0.08
        if "ESTATICO" in self.tracos:
            chance = 0.01
        
        if distancia < 2.0:
            chance *= 2.5
        if hp_pct < 0.3:
            chance *= 2.0
        if self.medo > 0.5:
            chance *= 1.8
        if self.modo_berserk:
            chance *= 0.3
        
        if random.random() < chance:
            p.vel_z = random.uniform(10.0, 14.0)
            self.cd_pulo = random.uniform(0.8, 2.0)
            
            if self.arquetipo in ["ASSASSINO", "NINJA", "BERSERKER", "ACROBATA"]:
                self.acao_atual = "ATAQUE_AEREO"
            else:
                self.acao_atual = "RECUAR"
            
            self.cd_reagir = 0.3
            return True
        
        return False

    def _tentar_dash_emergencia(self, distancia, hp_pct, inimigo):
        """Dash de emergência v7.0 com detecção de projéteis"""
        if self.cd_dash > 0:
            return False
        
        dash_skills = self.skills_por_tipo.get("DASH", [])
        if not dash_skills:
            return False
        
        emergencia = False
        projetil_vindo = self._detectar_projetil_vindo(inimigo)
        
        if projetil_vindo and random.random() < 0.6:
            emergencia = True
        if hp_pct < 0.2 and distancia < 3.0:
            emergencia = True
        if self.medo > 0.7 and distancia < 4.0:
            emergencia = True
        if self.hits_recebidos_recente >= 4:
            emergencia = True
        
        if "EVASIVO" in self.tracos and projetil_vindo:
            emergencia = True
        if "ACROBATA" in self.tracos and projetil_vindo and random.random() < 0.75:
            emergencia = True
        if "REATIVO" in self.tracos and projetil_vindo and random.random() < 0.5:
            emergencia = True
        if "COVARDE" in self.tracos and hp_pct < 0.4:
            emergencia = True
        if "MEDROSO" in self.tracos and self.medo > 0.5:
            emergencia = True
        
        if "IMPLACAVEL" in self.tracos or "KAMIKAZE" in self.tracos or self.modo_berserk:
            emergencia = False
        
        if emergencia:
            for skill in dash_skills:
                if self._usar_skill(skill):
                    self.acao_atual = "FUGIR"
                    self.cd_dash = 2.5
                    self.cd_reagir = 0.5
                    self.vezes_que_fugiu += 1
                    return True
        
        return False
    
    def _detectar_projetil_vindo(self, inimigo):
        """Detecta se há projéteis vindo na direção do personagem"""
        p = self.parent
        
        if hasattr(inimigo, 'buffer_projeteis'):
            for proj in inimigo.buffer_projeteis:
                if not proj.ativo:
                    continue
                dx = p.pos[0] - proj.x
                dy = p.pos[1] - proj.y
                dist = math.hypot(dx, dy)
                if dist < 4.0:
                    return True
        
        if hasattr(inimigo, 'buffer_orbes'):
            for orbe in inimigo.buffer_orbes:
                if not orbe.ativo or orbe.estado != "disparando":
                    continue
                dx = p.pos[0] - orbe.x
                dy = p.pos[1] - orbe.y
                dist = math.hypot(dx, dy)
                if dist < 5.0:
                    return True
        
        return False

    def _tentar_cura_emergencia(self, hp_pct):
        """Cura de emergência"""
        buff_skills = self.skills_por_tipo.get("BUFF", [])
        
        for skill in buff_skills:
            data = skill["data"]
            if data.get("cura"):
                threshold = 0.5 if "CAUTELOSO" in self.tracos else 0.35
                if "IMPRUDENTE" in self.tracos:
                    threshold = 0.2
                
                if hp_pct < threshold:
                    if self._usar_skill(skill):
                        self.cd_reagir = 0.3
                        return True
        
        return False

    def _tentar_contra_ataque(self, distancia, inimigo):
        """Contra-ataque"""
        pode_contra = False
        if "REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos:
            pode_contra = True
        if self.estilo_luta == "COUNTER" or self.filosofia == "OPORTUNISMO":
            pode_contra = True
        
        if not pode_contra:
            return False
        
        vulneravel = False
        if hasattr(inimigo, 'cooldown_ataque') and inimigo.cooldown_ataque > 0.3:
            vulneravel = True
        if hasattr(inimigo, 'atacando') and not inimigo.atacando:
            vulneravel = True
        
        if vulneravel and distancia < self.parent.alcance_ideal + 1.5:
            self.acao_atual = "CONTRA_ATAQUE"
            self.raiva = min(1.0, self.raiva + 0.1)
            self.cd_reagir = 0.4
            return True
        
        return False

    # =========================================================================
    # SKILLS
    # =========================================================================
    
    def _processar_skills(self, distancia, inimigo):
        """Processa uso de skills"""
        p = self.parent
        
        if hasattr(p, 'cd_skill_arma') and p.cd_skill_arma > 0:
            return False
        
        if "CONSERVADOR" in self.tracos and p.mana < p.mana_max * 0.4:
            if random.random() > 0.2:
                return False
        
        if self._tentar_dash_ofensivo(distancia, inimigo):
            return True
        if self._tentar_usar_buff(distancia, inimigo):
            return True
        if self._tentar_usar_ofensiva(distancia, inimigo):
            return True
        if self._tentar_usar_summon(distancia, inimigo):
            return True
        
        return False

    def _tentar_dash_ofensivo(self, distancia, inimigo):
        """Dash ofensivo"""
        if self.cd_dash > 0:
            return False
        
        dash_skills = self.skills_por_tipo.get("DASH", [])
        if not dash_skills:
            return False
        
        p = self.parent
        
        for skill in dash_skills:
            data = skill["data"]
            dist_dash = data.get("distancia", 3.0)
            
            usar = False
            
            if self.arquetipo in ["ASSASSINO", "NINJA", "ACROBATA", "SOMBRA"]:
                if distancia > 4.0 and distancia < dist_dash + 3.5:
                    if self.confianca > 0.35 or self.raiva > 0.4:
                        usar = True
            
            if self.modo_berserk or "BERSERKER" in self.tracos:
                if distancia > 3.0:
                    usar = True
            
            if "FLANQUEADOR" in self.tracos and random.random() < 0.08:
                if self._usar_skill(skill):
                    self.dir_circular *= -1
                    self.acao_atual = "FLANQUEAR"
                    self.cd_dash = 2.0
                    return True
            
            if "ACROBATA" in self.tracos and random.random() < 0.06:
                usar = True
            
            if usar and self._usar_skill(skill):
                self.acao_atual = "MATAR"
                self.cd_dash = 2.5
                return True
        
        return False

    def _tentar_usar_buff(self, distancia, inimigo):
        """Usa buffs"""
        if self.cd_buff > 0:
            return False
        
        buff_skills = self.skills_por_tipo.get("BUFF", [])
        if not buff_skills:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max
        
        for skill in buff_skills:
            data = skill["data"]
            usar = False
            
            if data.get("cura"):
                threshold = 0.55 if "CAUTELOSO" in self.tracos else 0.40
                if hp_pct < threshold:
                    usar = True
            elif data.get("escudo"):
                if distancia < 5.0 and hp_pct > 0.6 and random.random() < 0.1:
                    usar = True
                if self.hits_recebidos_recente >= 2:
                    usar = True
            elif data.get("buff_dano"):
                if distancia < 4.0 and self.confianca > 0.5:
                    usar = random.random() < 0.15
                if "EXPLOSIVO" in self.tracos and inimigo.vida < inimigo.vida_max * 0.4:
                    usar = True
                if self.modo_burst:
                    usar = True
            elif data.get("buff_velocidade"):
                if distancia > 6.0 and "PERSEGUIDOR" in self.tracos:
                    usar = True
                if hp_pct < 0.35 and distancia < 4.0:
                    usar = True
            
            if usar and self._usar_skill(skill):
                self.cd_buff = 3.0
                return True
        
        return False

    def _tentar_usar_ofensiva(self, distancia, inimigo):
        """Usa skills ofensivas"""
        p = self.parent
        
        chance = self.agressividade_base
        if "SPAMMER" in self.tracos:
            chance += 0.25
        if self.raiva > 0.6:
            chance += 0.15
        if self.modo_burst:
            chance += 0.3
        if "CALCULISTA" in self.tracos:
            chance -= 0.1
        
        if random.random() > chance:
            return False
        
        # Projéteis
        for skill in self.skills_por_tipo.get("PROJETIL", []):
            data = skill["data"]
            alcance = data.get("vida", 1.5) * data.get("velocidade", 8.0) * 0.8
            
            usar = False
            if self.arquetipo in ["MAGO", "MAGO_AGRESSIVO", "ARQUEIRO", "INVOCADOR", "PIROMANTE", "CRIOMANTE"]:
                if distancia > 2.5 and distancia < alcance:
                    usar = True
            elif distancia > 1.5 and distancia < alcance * 0.8:
                usar = True
            
            if "SNIPER" in self.tracos and distancia > 5.0:
                usar = True
            if "CLOSE_RANGE" in self.tracos and distancia > 4.0:
                usar = False
            if "SPAMMER" in self.tracos:
                usar = usar or random.random() < 0.3
            
            if usar and self._usar_skill(skill):
                self._pos_uso_skill_ofensiva(data)
                return True
        
        # Beams
        for skill in self.skills_por_tipo.get("BEAM", []):
            data = skill["data"]
            alcance = data.get("alcance", 5.0)
            if distancia < alcance and self._usar_skill(skill):
                self._pos_uso_skill_ofensiva(data)
                return True
        
        # Área
        for skill in self.skills_por_tipo.get("AREA", []):
            data = skill["data"]
            raio = data.get("raio_area", 2.5)
            
            usar = distancia < raio + 0.5
            if "AREA_DENIAL" in self.tracos and distancia < raio + 2.0:
                usar = True
            if self.modo_berserk and distancia < raio + 2.0:
                usar = True
            
            if usar and self._usar_skill(skill):
                self._pos_uso_skill_ofensiva(data)
                return True
        
        # Skill da arma fallback
        if hasattr(p, 'skill_arma_nome') and p.skill_arma_nome and p.skill_arma_nome != "Nenhuma":
            if hasattr(p, 'usar_skill_arma') and p.mana >= p.custo_skill_arma:
                dados = get_skill_data(p.skill_arma_nome)
                if self._avaliar_uso_skill(dados, distancia, inimigo):
                    if p.usar_skill_arma():
                        self._pos_uso_skill_ofensiva(dados)
                        return True
        
        return False

    def _tentar_usar_summon(self, distancia, inimigo):
        """Usa summons"""
        summon_skills = self.skills_por_tipo.get("SUMMON", [])
        if not summon_skills:
            return False
        
        for skill in summon_skills:
            if distancia > 4.0 or self.medo > 0.4:
                if self._usar_skill(skill):
                    return True
        
        return False

    def _usar_skill(self, skill_info):
        """Usa uma skill"""
        p = self.parent
        data = skill_info["data"]
        custo = skill_info.get("custo", data.get("custo", 15))
        
        if p.mana < custo:
            return False
        
        if skill_info["fonte"] == "arma":
            if hasattr(p, 'usar_skill_arma'):
                return p.usar_skill_arma()
        elif skill_info["fonte"] == "classe":
            if hasattr(p, 'usar_skill_classe'):
                return p.usar_skill_classe(skill_info["nome"])
        
        return False

    def _avaliar_uso_skill(self, dados, distancia, inimigo):
        """Avalia uso de skill"""
        tipo = dados.get("tipo", "NADA")
        p = self.parent
        
        if tipo == "PROJETIL":
            alcance = dados.get("vida", 1.5) * dados.get("velocidade", 8.0) * 0.8
            return distancia < alcance and distancia > 1.0
        elif tipo == "BEAM":
            return distancia < dados.get("alcance", 5.0)
        elif tipo == "AREA":
            return distancia < dados.get("raio_area", 2.5) + 1.0
        elif tipo == "DASH":
            if self.medo > 0.5:
                return True
            dist = dados.get("distancia", 3.0)
            return distancia > 4.0 and distancia < dist + 2.0
        elif tipo == "BUFF":
            if dados.get("cura"):
                return p.vida < p.vida_max * 0.45
            return distancia < 5.0
        
        return False

    def _pos_uso_skill_ofensiva(self, dados):
        """Ação pós-skill ofensiva"""
        tipo = dados.get("tipo", "NADA")
        
        if tipo == "DASH":
            self.acao_atual = "MATAR"
        elif self.estilo_luta in ["KITE", "RANGED", "HIT_RUN"]:
            self.acao_atual = "RECUAR"
        elif self.estilo_luta in ["BERSERK", "AGGRO", "BURST"]:
            self.acao_atual = "MATAR"
        elif "COVARDE" in self.tracos:
            self.acao_atual = "RECUAR"

    # =========================================================================
    # MOVIMENTO v7.0 COM INTELIGÊNCIA DE ALCANCE
    # =========================================================================
    
    def _decidir_movimento(self, distancia, inimigo):
        """Decide ação de movimento com inteligência de alcance"""
        p = self.parent
        roll = random.random()
        hp_pct = p.vida / p.vida_max
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0
        
        # Calcula alcance real
        alcance_efetivo = self._calcular_alcance_efetivo()
        dentro_alcance = distancia <= alcance_efetivo
        quase_no_alcance = distancia <= alcance_efetivo * 1.3
        muito_longe = distancia > alcance_efetivo * 2.0
        
        # Condições especiais
        if hasattr(p, 'modo_adrenalina') and p.modo_adrenalina:
            self.acao_atual = "MATAR"
            return
        
        if hasattr(p, 'estamina') and p.estamina < 15:
            if dentro_alcance and roll < 0.4:
                self.acao_atual = "ATAQUE_RAPIDO"
            else:
                self.acao_atual = "RECUAR"
            return
        
        if self.modo_berserk:
            self.acao_atual = "MATAR"
            return
        
        if self.modo_defensivo:
            if dentro_alcance and roll < 0.3:
                self.acao_atual = "CONTRA_ATAQUE"
            elif distancia < alcance_efetivo * 0.7:
                self.acao_atual = "RECUAR"
            else:
                self.acao_atual = "COMBATE"
            return
        
        if self.medo > 0.75 and "DETERMINADO" not in self.tracos and "FRIO" not in self.tracos:
            if dentro_alcance and roll < 0.25:
                self.acao_atual = "ATAQUE_RAPIDO"
            else:
                self.acao_atual = "FUGIR"
            return
        
        # Inteligência de alcance
        if dentro_alcance:
            if inimigo_hp_pct < 0.3:
                self.acao_atual = random.choice(["MATAR", "ESMAGAR", "MATAR"])
            elif roll < 0.6:
                self.acao_atual = random.choice(["MATAR", "ATAQUE_RAPIDO", "COMBATE"])
            elif roll < 0.85:
                self.acao_atual = random.choice(["FLANQUEAR", "CIRCULAR"])
            else:
                self.acao_atual = "CONTRA_ATAQUE"
            return
        
        if quase_no_alcance:
            if roll < 0.7:
                self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "FLANQUEAR"])
            else:
                self.acao_atual = random.choice(["COMBATE", "POKE"])
            return
        
        if muito_longe:
            self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "MATAR"])
            return
        
        # Traços especiais
        if "COVARDE" in self.tracos and hp_pct < 0.35:
            self.vezes_que_fugiu += 1
            if self.vezes_que_fugiu > 4:
                self.acao_atual = "MATAR"
                self.raiva = 0.9
            else:
                self.acao_atual = "FUGIR"
            return
        
        if "BERSERKER" in self.tracos and hp_pct < 0.45:
            self.acao_atual = "MATAR"
            return
        
        if "SANGUINARIO" in self.tracos and inimigo_hp_pct < 0.3:
            self.acao_atual = "MATAR"
            return
        
        if "PREDADOR" in self.tracos and inimigo_hp_pct < 0.4:
            self.acao_atual = "APROXIMAR"
            return
        
        if "PERSEGUIDOR" in self.tracos and distancia > 5.0:
            self.acao_atual = "APROXIMAR"
            return
        
        if "KAMIKAZE" in self.tracos:
            self.acao_atual = "MATAR"
            return
        
        # Comportamento por estilo
        self._comportamento_estilo(distancia, roll, hp_pct, inimigo_hp_pct)
        self._aplicar_modificadores_movimento(distancia, roll)
        self._aplicar_modificadores_humor()
        self._aplicar_modificadores_filosofia()
    
    def _calcular_alcance_efetivo(self):
        """Calcula alcance real de ataque baseado na arma"""
        p = self.parent
        alcance_base = p.alcance_ideal
        
        arma = p.dados.arma_obj if p.dados else None
        if not arma:
            return alcance_base + 1.0
        
        tipo = arma.tipo
        
        if tipo == "Reta":
            comp_total = (arma.comp_cabo + arma.comp_lamina) / PPM
            return alcance_base + comp_total * 0.5
        elif tipo == "Dupla":
            return alcance_base + 0.5
        elif tipo == "Corrente":
            comp = getattr(arma, 'comp_corrente', 80) / PPM
            return alcance_base + comp * 0.4
        elif tipo == "Arremesso":
            return alcance_base + 6.0
        elif tipo == "Arco":
            return alcance_base + 8.0
        elif tipo == "Mágica":
            return alcance_base + 5.0
        elif tipo == "Orbital":
            return alcance_base + arma.distancia / PPM
        elif tipo == "Transformável":
            return alcance_base + 1.5
        else:
            return alcance_base + 1.0

    def _comportamento_estilo(self, distancia, roll, hp_pct, inimigo_hp_pct):
        """Comportamento baseado no estilo de luta"""
        alcance = self.parent.alcance_ideal
        
        estilo_data = ESTILOS_LUTA.get(self.estilo_luta, ESTILOS_LUTA["BALANCED"])
        agressividade = estilo_data.get("agressividade_base", 0.6)
        
        tempo_boost = min(0.2, self.tempo_combate / 60.0)
        agressividade += tempo_boost
        
        if inimigo_hp_pct < 0.3:
            agressividade += 0.25
        elif inimigo_hp_pct < 0.5:
            agressividade += 0.1
            
        hp_diff = hp_pct - inimigo_hp_pct
        if hp_diff > 0.2:
            agressividade += hp_diff * 0.3
            
        if hp_pct < 0.25 and "BERSERKER" not in self.tracos:
            agressividade -= 0.1
        
        agressividade = max(0.3, min(1.0, agressividade))
        
        margem = 0.5
        if distancia < alcance - margem:
            zona = "perto"
        elif distancia > alcance + 2.0 + margem:
            zona = "longe"
        else:
            zona = "medio"
        
        if zona == "perto":
            self.acao_atual = estilo_data["acao_perto"]
        elif zona == "longe":
            self.acao_atual = estilo_data["acao_longe"]
        else:
            self.acao_atual = estilo_data["acao_medio"]
        
        if roll < agressividade * 0.25:
            acoes_agressivas = ["MATAR", "ATAQUE_RAPIDO", "PRESSIONAR", "ESMAGAR", "FLANQUEAR"]
            self.acao_atual = random.choice(acoes_agressivas)
        elif roll < 0.12:
            acoes_variadas = ["CIRCULAR", "FLANQUEAR", "COMBATE", "POKE"]
            self.acao_atual = random.choice(acoes_variadas)
        
        if distancia > 10.0 and self.acao_atual not in ["APROXIMAR", "MATAR", "PRESSIONAR"]:
            if random.random() < 0.7:
                self.acao_atual = "APROXIMAR"
        
        if distancia < 2.0 and self.acao_atual not in ["MATAR", "ATAQUE_RAPIDO", "ESMAGAR", "CONTRA_ATAQUE"]:
            if random.random() < agressividade * 0.5:
                self.acao_atual = random.choice(["MATAR", "ATAQUE_RAPIDO", "COMBATE"])

    def _aplicar_modificadores_movimento(self, distancia, roll):
        """Modifica ação baseado nos traços"""
        if "AGRESSIVO" in self.tracos:
            if self.acao_atual in ["CIRCULAR", "BLOQUEAR", "RECUAR", "COMBATE"]:
                if random.random() < 0.55:
                    self.acao_atual = random.choice(["MATAR", "APROXIMAR", "PRESSIONAR"])
        
        if "CALCULISTA" in self.tracos:
            if self.acao_atual == "MATAR" and distancia > 4.0:
                if random.random() < 0.25:
                    self.acao_atual = "FLANQUEAR"
        
        if "PACIENTE" in self.tracos:
            if self.acao_atual in ["APROXIMAR", "MATAR"]:
                if random.random() < 0.2:
                    self.acao_atual = "COMBATE"
        
        if "IMPRUDENTE" in self.tracos:
            if self.acao_atual in ["BLOQUEAR", "RECUAR", "FUGIR", "CIRCULAR", "COMBATE"]:
                if random.random() < 0.6:
                    self.acao_atual = random.choice(["MATAR", "ESMAGAR"])
        
        if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
            if random.random() < 0.25:
                acoes = ["FLANQUEAR", "APROXIMAR", "ATAQUE_RAPIDO", "MATAR", "ESMAGAR", "POKE"]
                self.acao_atual = random.choice(acoes)
        
        if "ADAPTAVEL" in self.tracos:
            if self.frustracao > 0.5:
                acoes = ["FLANQUEAR", "MATAR", "ESMAGAR", "PRESSIONAR"]
                self.acao_atual = random.choice(acoes)
                self.frustracao *= 0.5
        
        if "FLANQUEADOR" in self.tracos:
            if self.acao_atual in ["APROXIMAR", "COMBATE", "CIRCULAR", "BLOQUEAR"]:
                if random.random() < 0.5:
                    self.acao_atual = "FLANQUEAR"
        
        if "VELOZ" in self.tracos:
            if self.acao_atual in ["BLOQUEAR", "COMBATE"]:
                if random.random() < 0.6:
                    self.acao_atual = random.choice(["FLANQUEAR", "ATAQUE_RAPIDO"])
        
        if "ESTATICO" in self.tracos:
            if self.acao_atual in ["CIRCULAR", "FLANQUEAR", "RECUAR"]:
                if random.random() < 0.4:
                    self.acao_atual = random.choice(["COMBATE", "MATAR"])
        
        if "SELVAGEM" in self.tracos:
            if random.random() < 0.25:
                self.acao_atual = random.choice(["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"])
        
        if "TEIMOSO" in self.tracos:
            if self.acao_atual not in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"]:
                if random.random() < 0.3:
                    self.acao_atual = "MATAR"
        elif "FRIO" not in self.tracos:
            if self.raiva > 0.6:
                if self.acao_atual in ["RECUAR", "BLOQUEAR", "CIRCULAR", "FUGIR"]:
                    if random.random() < 0.5:
                        self.acao_atual = random.choice(["MATAR", "ESMAGAR"])

    def _aplicar_modificadores_humor(self):
        """Aplica modificadores do humor atual"""
        humor_data = HUMORES.get(self.humor, HUMORES["CALMO"])
        
        if humor_data["mod_agressividade"] > 0.15:
            if self.acao_atual in ["RECUAR", "BLOQUEAR", "CIRCULAR", "FUGIR"]:
                if random.random() < 0.45:
                    self.acao_atual = random.choice(["MATAR", "APROXIMAR", "PRESSIONAR"])
        elif humor_data["mod_agressividade"] < -0.25:
            if self.acao_atual in ["MATAR", "ESMAGAR"]:
                if random.random() < 0.2:
                    self.acao_atual = "COMBATE"

    def _aplicar_modificadores_filosofia(self):
        """Aplica modificadores da filosofia"""
        filosofia_data = FILOSOFIAS.get(self.filosofia, FILOSOFIAS["EQUILIBRIO"])
        preferencias = filosofia_data["preferencia_acao"]
        
        if random.random() < 0.2:
            self.acao_atual = random.choice(preferencias)

    def _calcular_timer_decisao(self):
        """Calcula timer para próxima decisão"""
        base = 0.3
        
        if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
            base = 0.15
        if "PACIENTE" in self.tracos:
            base = 0.45
        if "METODICO" in self.tracos:
            base = 0.4
        if self.modo_berserk:
            base = 0.1
        if self.humor == "ENTEDIADO":
            base = 0.5
        if self.humor == "ANIMADO":
            base = 0.18
        if self.humor == "FURIOSO":
            base = 0.12
        if self.humor == "DESESPERADO":
            base = 0.15
        
        self.timer_decisao = random.uniform(base * 0.5, base * 1.2)

    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def on_hit_dado(self):
        """Quando acerta um golpe"""
        self.hits_dados_total += 1
        self.hits_dados_recente += 1
        self.tempo_desde_hit = 0.0
        self.combo_atual += 1
        self.max_combo = max(self.max_combo, self.combo_atual)
        
        self.confianca = min(1.0, self.confianca + 0.05)
        self.frustracao = max(0, self.frustracao - 0.1)
        self.excitacao = min(1.0, self.excitacao + 0.1)
        
        if "SEDE_SANGUE" in self.quirks:
            self.adrenalina = min(1.0, self.adrenalina + 0.2)
    
    def on_hit_recebido(self, dano):
        """Quando recebe dano"""
        pass
    
    def on_skill_usada(self, skill_nome, sucesso):
        """Quando usa skill"""
        if not sucesso:
            self.frustracao = min(1.0, self.frustracao + 0.1)
    
    def on_inimigo_fugiu(self):
        """Quando inimigo foge"""
        if "PERSEGUIDOR" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.2)
            self.acao_atual = "APROXIMAR"
        if "PREDADOR" in self.tracos:
            self.excitacao = min(1.0, self.excitacao + 0.2)
