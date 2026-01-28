"""
=============================================================================
NEURAL FIGHTS - Cérebro da IA v9.0 SPATIAL AWARENESS EDITION
=============================================================================
Sistema de inteligência artificial com comportamento humano realista
e consciência espacial avançada.

NOVIDADES v9.0:
- Sistema de reconhecimento de paredes e obstáculos
- Consciência espacial tática (encurralado, vantagem, cobertura)
- Uso inteligente de obstáculos (cobertura, flanqueamento)
- Detecção de quando oponente está contra parede
- Evita recuar para obstáculos
- Ajuste automático de trajetória para evitar colisões
- Análise de caminhos livres em todas direções
- Comportamentos especiais quando encurralado

SISTEMAS v8.0 (mantidos):
- Sistema de antecipação de ataques (lê o oponente)
- Desvios inteligentes com timing humano
- Baiting e fintas (engana o oponente)
- Janelas de oportunidade (ataca nos momentos certos)
- Pressão psicológica e momentum
- Hesitação realista e impulsos
- Leitura de padrões do oponente
- Combos e follow-ups inteligentes

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
    Cérebro da IA v8.0 HUMAN EDITION - Sistema de personalidade procedural com
    comportamento humano realista e inteligência de combate avançada.
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
        
        # === SISTEMA HUMANO v8.0 - NOVIDADES ===
        
        # Antecipação e leitura do oponente
        self.leitura_oponente = {
            "ataque_iminente": False,
            "direcao_provavel": 0.0,
            "tempo_para_ataque": 0.0,
            "padrao_movimento": [],  # Últimos 10 movimentos
            "padrao_ataque": [],     # Últimos 10 ataques
            "tendencia_esquerda": 0.5,
            "frequencia_pulo": 0.0,
            "agressividade_percebida": 0.5,
            "previsibilidade": 0.5,  # Quão previsível é o oponente
        }
        
        # Sistema de janelas de oportunidade
        self.janela_ataque = {
            "aberta": False,
            "tipo": None,  # "pos_ataque", "recuperando", "fora_alcance", "pulo"
            "duracao": 0.0,
            "qualidade": 0.0,  # 0-1, quão boa é a janela
        }
        
        # Sistema de baiting (isca/finta)
        self.bait_state = {
            "ativo": False,
            "tipo": None,  # "recuo_falso", "abertura_falsa", "skill_falsa"
            "timer": 0.0,
            "sucesso_count": 0,
            "falha_count": 0,
        }
        
        # Momentum e pressão
        self.momentum = 0.0  # -1 (perdendo) a 1 (ganhando)
        self.pressao_aplicada = 0.0  # Quanto está pressionando
        self.pressao_recebida = 0.0  # Quanto está sendo pressionado
        
        # Hesitação e impulso humano
        self.hesitacao = 0.0  # Probabilidade de hesitar
        self.impulso = 0.0    # Probabilidade de agir impulsivamente
        self.congelamento = 0.0  # "Freeze" sob pressão
        
        # Timing humano
        self.tempo_reacao_base = random.uniform(0.12, 0.25)  # Varia por personalidade
        self.variacao_timing = random.uniform(0.05, 0.15)    # Inconsistência humana
        self.micro_ajustes = 0  # Pequenos ajustes de posição
        
        # Sistema de combos e follow-ups
        self.combo_state = {
            "em_combo": False,
            "hits_combo": 0,
            "ultimo_tipo_ataque": None,
            "pode_followup": False,
            "timer_followup": 0.0,
        }
        
        # Respiração e ritmo
        self.ritmo_combate = random.uniform(0.8, 1.2)  # Personalidade do ritmo
        self.burst_counter = 0  # Conta explosões de ação
        self.descanso_timer = 0.0  # Micro-pausas naturais
        
        # Histórico de ações para não repetir muito
        self.historico_acoes = []
        self.repeticao_contador = {}
        
        # === SISTEMA DE RECONHECIMENTO ESPACIAL v9.0 ===
        # Awareness de paredes e obstáculos
        self.consciencia_espacial = {
            "parede_proxima": None,  # None, "norte", "sul", "leste", "oeste"
            "distancia_parede": 999.0,
            "obstaculo_proxima": None,  # Obstáculo mais próximo
            "distancia_obstaculo": 999.0,
            "encurralado": False,
            "oponente_contra_parede": False,
            "caminho_livre": {"frente": True, "tras": True, "esquerda": True, "direita": True},
            "posicao_tatica": "centro",  # "centro", "perto_parede", "encurralado", "vantagem"
        }
        
        # Uso tático de obstáculos
        self.tatica_espacial = {
            "usando_cobertura": False,
            "tipo_cobertura": None,  # "pilar", "obstaculo", "parede"
            "forcar_canto": False,  # Tentando encurralar oponente
            "recuar_para_obstaculo": False,  # Recuando de costas pra obstáculo (perigoso)
            "flanquear_obstaculo": False,  # Usando obstáculo pra flanquear
            "last_check_time": 0.0,  # Otimização - não checa todo frame
        }
        
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
    # PROCESSAMENTO PRINCIPAL v8.0
    # =========================================================================
    
    def processar(self, dt, distancia, inimigo):
        """Processa decisões da IA a cada frame com comportamento humano"""
        p = self.parent
        self.tempo_combate += dt
        
        self._atualizar_cooldowns(dt)
        self._detectar_dano()
        self._atualizar_emocoes(dt, distancia, inimigo)
        self._atualizar_humor(dt)
        self._processar_modos_especiais(dt, distancia, inimigo)
        
        # === NOVOS SISTEMAS v8.0 ===
        self._atualizar_leitura_oponente(dt, distancia, inimigo)
        self._atualizar_janelas_oportunidade(dt, distancia, inimigo)
        self._atualizar_momentum(dt, distancia, inimigo)
        self._atualizar_estados_humanos(dt, distancia, inimigo)
        self._atualizar_combo_state(dt)
        
        # === SISTEMA ESPACIAL v9.0 ===
        self._atualizar_consciencia_espacial(dt, distancia, inimigo)
        
        # Hesitação humana - às vezes congela brevemente
        if self._verificar_hesitacao(distancia, inimigo):
            return
        
        # Sistema de Coreografia
        self._observar_oponente(inimigo, distancia)
        
        choreographer = CombatChoreographer.get_instance()
        acao_sync = choreographer.get_acao_sincronizada(p)
        
        if acao_sync:
            if self._executar_acao_sincronizada(acao_sync, distancia, inimigo):
                return
        
        # Processa baiting (fintas)
        if self._processar_baiting(dt, distancia, inimigo):
            return
        
        if self._processar_reacao_oponente(dt, distancia, inimigo):
            return
        
        # === SISTEMA DE DESVIO INTELIGENTE v8.0 ===
        if self._processar_desvio_inteligente(dt, distancia, inimigo):
            return
        
        if self._processar_quirks(dt, distancia, inimigo):
            return
        
        if self._processar_reacoes(dt, distancia, inimigo):
            return
        
        # === SISTEMA DE ATAQUE INTELIGENTE v8.0 ===
        if self._avaliar_e_executar_ataque(dt, distancia, inimigo):
            return
        
        if self._processar_skills(distancia, inimigo):
            return
        
        self.timer_decisao -= dt
        if self.timer_decisao <= 0:
            self._decidir_movimento(distancia, inimigo)
            self._calcular_timer_decisao()
            self._registrar_acao()

    # =========================================================================
    # SISTEMA DE LEITURA DO OPONENTE v8.0
    # =========================================================================
    
    def _atualizar_leitura_oponente(self, dt, distancia, inimigo):
        """Lê e antecipa os movimentos do oponente como um humano faria"""
        leitura = self.leitura_oponente
        
        # Detecta se oponente está preparando ataque
        ataque_prep = False
        if hasattr(inimigo, 'atacando') and inimigo.atacando:
            ataque_prep = True
        if hasattr(inimigo, 'cooldown_ataque') and inimigo.cooldown_ataque < 0.2:
            ataque_prep = True
        if hasattr(inimigo, 'ai') and inimigo.ai:
            ai_ini = inimigo.ai
            if ai_ini.acao_atual in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "CONTRA_ATAQUE"]:
                ataque_prep = True
        
        leitura["ataque_iminente"] = ataque_prep
        
        # Calcula direção provável do ataque
        if inimigo.vel[0] != 0 or inimigo.vel[1] != 0:
            leitura["direcao_provavel"] = math.degrees(math.atan2(inimigo.vel[1], inimigo.vel[0]))
        
        # Registra padrão de movimento
        mov_atual = (inimigo.vel[0], inimigo.vel[1], inimigo.z)
        leitura["padrao_movimento"].append(mov_atual)
        if len(leitura["padrao_movimento"]) > 15:
            leitura["padrao_movimento"].pop(0)
        
        # Analisa tendência lateral
        if len(leitura["padrao_movimento"]) >= 5:
            lateral_sum = sum(m[0] for m in leitura["padrao_movimento"][-5:])
            if lateral_sum > 0:
                leitura["tendencia_esquerda"] = max(0.2, leitura["tendencia_esquerda"] - 0.02)
            else:
                leitura["tendencia_esquerda"] = min(0.8, leitura["tendencia_esquerda"] + 0.02)
        
        # Detecta frequência de pulos
        pulos_recentes = sum(1 for m in leitura["padrao_movimento"] if m[2] > 0)
        leitura["frequencia_pulo"] = pulos_recentes / max(1, len(leitura["padrao_movimento"]))
        
        # Calcula previsibilidade do oponente
        if len(leitura["padrao_movimento"]) >= 8:
            # Compara movimentos consecutivos - mais similares = mais previsível
            variacoes = []
            for i in range(1, min(8, len(leitura["padrao_movimento"]))):
                m1 = leitura["padrao_movimento"][-i]
                m2 = leitura["padrao_movimento"][-i-1]
                var = abs(m1[0] - m2[0]) + abs(m1[1] - m2[1])
                variacoes.append(var)
            media_var = sum(variacoes) / len(variacoes) if variacoes else 1.0
            leitura["previsibilidade"] = max(0.1, min(0.9, 1.0 - (media_var / 20.0)))
        
        # Percebe agressividade do oponente
        if hasattr(inimigo, 'ai') and inimigo.ai:
            ai_ini = inimigo.ai
            if ai_ini.acao_atual in ["MATAR", "ESMAGAR", "PRESSIONAR", "APROXIMAR"]:
                leitura["agressividade_percebida"] = min(1.0, leitura["agressividade_percebida"] + 0.03)
            elif ai_ini.acao_atual in ["RECUAR", "FUGIR", "BLOQUEAR"]:
                leitura["agressividade_percebida"] = max(0.0, leitura["agressividade_percebida"] - 0.02)
    
    # =========================================================================
    # SISTEMA DE DESVIO INTELIGENTE v8.0
    # =========================================================================
    
    def _processar_desvio_inteligente(self, dt, distancia, inimigo):
        """Sistema de desvio avançado com antecipação e timing humano"""
        p = self.parent
        leitura = self.leitura_oponente
        
        # Não desvia se estiver em berserk ou muito confiante
        if self.modo_berserk:
            return False
        if self.confianca > 0.85 and "IMPRUDENTE" in self.tracos:
            return False
        
        # Detecta necessidade de desvio
        desvio_necessario = False
        tipo_desvio = None
        urgencia = 0.0
        
        # 1. Ataque físico iminente
        if leitura["ataque_iminente"] and distancia < 3.5:
            desvio_necessario = True
            tipo_desvio = "ATAQUE_FISICO"
            urgencia = 1.0 - (distancia / 3.5)
        
        # 2. Projétil vindo
        projetil_info = self._analisar_projeteis_vindo(inimigo)
        if projetil_info["vindo"]:
            desvio_necessario = True
            tipo_desvio = "PROJETIL"
            urgencia = max(urgencia, projetil_info["urgencia"])
        
        # 3. Área de dano
        area_info = self._analisar_areas_perigo(inimigo)
        if area_info["perigo"]:
            desvio_necessario = True
            tipo_desvio = "AREA"
            urgencia = max(urgencia, area_info["urgencia"])
        
        if not desvio_necessario:
            return False
        
        # Aplica timing humano (não reage instantaneamente)
        tempo_reacao = self.tempo_reacao_base + random.uniform(-self.variacao_timing, self.variacao_timing)
        
        # Traços afetam tempo de reação
        if "REATIVO" in self.tracos or "EVASIVO" in self.tracos:
            tempo_reacao *= 0.7
        if "ESTATICO" in self.tracos:
            tempo_reacao *= 1.5
        if self.adrenalina > 0.6:
            tempo_reacao *= 0.8
        if self.medo > 0.5:
            tempo_reacao *= 0.85  # Medo aumenta reflexos
        if self.congelamento > 0.3:
            tempo_reacao *= 1.5  # Congela sob pressão
        
        # Chance de reagir baseado na urgência vs tempo de reação
        chance_reagir = urgencia * (1.0 - tempo_reacao)
        
        # Personalidade afeta chance
        if "ACROBATA" in self.tracos:
            chance_reagir += 0.2
        if "PACIENTE" in self.tracos:
            chance_reagir += 0.1
        if "IMPRUDENTE" in self.tracos:
            chance_reagir -= 0.15
        
        if random.random() > chance_reagir:
            return False
        
        # Decide direção do desvio
        direcao_desvio = self._calcular_direcao_desvio(tipo_desvio, distancia, inimigo, projetil_info)
        
        # Executa o desvio
        return self._executar_desvio(tipo_desvio, direcao_desvio, urgencia, distancia, inimigo)
    
    def _analisar_projeteis_vindo(self, inimigo):
        """Analisa projéteis vindo em direção ao lutador"""
        p = self.parent
        resultado = {"vindo": False, "urgencia": 0.0, "direcao": 0.0, "tempo_impacto": 999.0}
        
        # Verifica projéteis
        if hasattr(inimigo, 'buffer_projeteis'):
            for proj in inimigo.buffer_projeteis:
                if not proj.ativo:
                    continue
                
                dx = p.pos[0] - proj.x
                dy = p.pos[1] - proj.y
                dist = math.hypot(dx, dy)
                
                if dist > 8.0:
                    continue
                
                # Calcula se está vindo na minha direção
                ang_para_mim = math.degrees(math.atan2(dy, dx))
                ang_proj = getattr(proj, 'angulo', 0)
                diff_ang = abs(normalizar_angulo(ang_para_mim - ang_proj))
                
                if diff_ang < 45:  # Vindo na minha direção
                    vel_proj = getattr(proj, 'vel', 10.0)
                    tempo_impacto = dist / vel_proj
                    
                    if tempo_impacto < resultado["tempo_impacto"]:
                        resultado["vindo"] = True
                        resultado["tempo_impacto"] = tempo_impacto
                        resultado["urgencia"] = max(0.3, 1.0 - tempo_impacto / 1.0)
                        resultado["direcao"] = ang_proj
        
        # Verifica orbes
        if hasattr(inimigo, 'buffer_orbes'):
            for orbe in inimigo.buffer_orbes:
                if not orbe.ativo or orbe.estado != "disparando":
                    continue
                
                dx = p.pos[0] - orbe.x
                dy = p.pos[1] - orbe.y
                dist = math.hypot(dx, dy)
                
                if dist < 5.0:
                    resultado["vindo"] = True
                    resultado["urgencia"] = max(resultado["urgencia"], 0.8)
                    resultado["direcao"] = math.degrees(math.atan2(-dy, -dx))
        
        # Verifica beams
        if hasattr(inimigo, 'buffer_beams'):
            for beam in inimigo.buffer_beams:
                if not beam.ativo:
                    continue
                # Simplificação: se beam está ativo e perto, é perigo
                dist = math.hypot(p.pos[0] - beam.x1, p.pos[1] - beam.y1)
                alcance = math.hypot(beam.x2 - beam.x1, beam.y2 - beam.y1)
                if dist < alcance + 1.0:
                    resultado["vindo"] = True
                    resultado["urgencia"] = max(resultado["urgencia"], 0.9)
        
        return resultado
    
    def _analisar_areas_perigo(self, inimigo):
        """Analisa áreas de dano próximas"""
        p = self.parent
        resultado = {"perigo": False, "urgencia": 0.0}
        
        if hasattr(inimigo, 'buffer_areas'):
            for area in inimigo.buffer_areas:
                if not area.ativo:
                    continue
                
                dist = math.hypot(p.pos[0] - area.x, p.pos[1] - area.y)
                raio = getattr(area, 'raio', 2.0)
                
                if dist < raio + 1.5:  # Dentro ou perto da área
                    resultado["perigo"] = True
                    resultado["urgencia"] = max(resultado["urgencia"], 1.0 - dist / (raio + 1.5))
        
        return resultado
    
    def _calcular_direcao_desvio(self, tipo_desvio, distancia, inimigo, projetil_info):
        """Calcula a melhor direção para desviar"""
        p = self.parent
        leitura = self.leitura_oponente
        
        # Direção base: perpendicular ao ataque
        if tipo_desvio == "PROJETIL" and projetil_info.get("direcao"):
            ang_ataque = projetil_info["direcao"]
        else:
            ang_ataque = math.degrees(math.atan2(
                p.pos[1] - inimigo.pos[1], 
                p.pos[0] - inimigo.pos[0]
            )) + 180
        
        # Perpendicular: +90 ou -90
        opcao1 = ang_ataque + 90
        opcao2 = ang_ataque - 90
        
        # Escolhe direção baseado em fatores
        escolha = opcao1 if random.random() < 0.5 else opcao2
        
        # Leitura do oponente influencia
        if leitura["tendencia_esquerda"] > 0.6:
            escolha = opcao2  # Oponente tende a ir pra esquerda, vou pra direita
        elif leitura["tendencia_esquerda"] < 0.4:
            escolha = opcao1
        
        # Usa direção circular estabelecida
        if self.dir_circular > 0:
            escolha = opcao1
        else:
            escolha = opcao2
        
        # Adiciona variação humana
        escolha += random.uniform(-20, 20)
        
        # Se HP baixo, prioriza recuar
        hp_pct = p.vida / p.vida_max
        if hp_pct < 0.3:
            # Mistura desvio com recuo
            ang_recuo = math.degrees(math.atan2(
                p.pos[1] - inimigo.pos[1], 
                p.pos[0] - inimigo.pos[0]
            ))
            escolha = (escolha + ang_recuo) / 2
        
        return escolha
    
    def _executar_desvio(self, tipo_desvio, direcao, urgencia, distancia, inimigo):
        """Executa o desvio escolhido"""
        p = self.parent
        
        # Tipo de desvio baseado na urgência e situação
        if urgencia > 0.8 or tipo_desvio == "AREA":
            # Desvio urgente - dash se disponível
            if self.cd_dash <= 0:
                dash_skills = self.skills_por_tipo.get("DASH", [])
                for skill in dash_skills:
                    # Ajusta ângulo de olhar temporariamente para dash
                    ang_original = p.angulo_olhar
                    p.angulo_olhar = direcao
                    if self._usar_skill(skill):
                        p.angulo_olhar = ang_original
                        self.cd_dash = 2.0
                        self.acao_atual = "DESVIO"
                        return True
                    p.angulo_olhar = ang_original
            
            # Sem dash, tenta pulo
            if p.z == 0 and self.cd_pulo <= 0:
                p.vel_z = random.uniform(10.0, 14.0)
                self.cd_pulo = 1.0
                # Move lateralmente também
                rad = math.radians(direcao)
                p.vel[0] += math.cos(rad) * 15.0
                p.vel[1] += math.sin(rad) * 15.0
                self.acao_atual = "DESVIO"
                return True
        
        # Desvio normal - movimento lateral
        if urgencia > 0.4:
            rad = math.radians(direcao)
            impulso = 20.0 * urgencia
            p.vel[0] += math.cos(rad) * impulso
            p.vel[1] += math.sin(rad) * impulso
            
            # Define ação
            if distancia > 4.0:
                self.acao_atual = "CIRCULAR"
            else:
                self.acao_atual = "FLANQUEAR"
            
            return True
        
        # Desvio sutil - apenas ajuste de posição
        if random.random() < urgencia:
            self.acao_atual = "CIRCULAR"
            return True
        
        return False
    
    # =========================================================================
    # SISTEMA DE JANELAS DE OPORTUNIDADE v8.0
    # =========================================================================
    
    def _atualizar_janelas_oportunidade(self, dt, distancia, inimigo):
        """Detecta janelas de oportunidade para atacar"""
        janela = self.janela_ataque
        
        # Decrementa duração da janela atual
        if janela["aberta"]:
            janela["duracao"] -= dt
            if janela["duracao"] <= 0:
                janela["aberta"] = False
                janela["tipo"] = None
        
        # Detecta novas janelas
        nova_janela = False
        tipo_janela = None
        qualidade = 0.0
        duracao = 0.0
        
        # 1. Pós-ataque do oponente (recovery)
        if hasattr(inimigo, 'atacando') and not inimigo.atacando:
            if hasattr(inimigo, 'cooldown_ataque') and 0.1 < inimigo.cooldown_ataque < 0.6:
                nova_janela = True
                tipo_janela = "pos_ataque"
                qualidade = 0.8
                duracao = inimigo.cooldown_ataque
        
        # 2. Oponente usando skill (channeling)
        if hasattr(inimigo, 'canalizando') and inimigo.canalizando:
            nova_janela = True
            tipo_janela = "canalizando"
            qualidade = 0.9
            duracao = 1.0
        
        # 3. Oponente no ar (menos mobilidade)
        if hasattr(inimigo, 'z') and inimigo.z > 0.5:
            nova_janela = True
            tipo_janela = "aereo"
            qualidade = 0.6
            duracao = 0.5
        
        # 4. Oponente stunado ou lento
        if hasattr(inimigo, 'stun_timer') and inimigo.stun_timer > 0:
            nova_janela = True
            tipo_janela = "stunado"
            qualidade = 1.0
            duracao = inimigo.stun_timer
        
        # 5. Oponente com estamina baixa
        if hasattr(inimigo, 'estamina') and inimigo.estamina < 20:
            nova_janela = True
            tipo_janela = "exausto"
            qualidade = 0.7
            duracao = 1.5
        
        # 6. Oponente recuando (costas viradas parcialmente)
        if hasattr(inimigo, 'ai') and inimigo.ai:
            if inimigo.ai.acao_atual in ["RECUAR", "FUGIR"]:
                nova_janela = True
                tipo_janela = "recuando"
                qualidade = 0.75
                duracao = 0.8
        
        # 7. Oponente usou skill de mana alta (esperando cooldown)
        if hasattr(inimigo, 'cd_skill_arma') and inimigo.cd_skill_arma > 2.0:
            nova_janela = True
            tipo_janela = "skill_cd"
            qualidade = 0.65
            duracao = min(2.0, inimigo.cd_skill_arma)
        
        # Atualiza janela se encontrou uma melhor
        if nova_janela and qualidade > janela.get("qualidade", 0):
            janela["aberta"] = True
            janela["tipo"] = tipo_janela
            janela["qualidade"] = qualidade
            janela["duracao"] = duracao
    
    # =========================================================================
    # SISTEMA DE ATAQUE INTELIGENTE v8.0
    # =========================================================================
    
    def _avaliar_e_executar_ataque(self, dt, distancia, inimigo):
        """Avalia se deve atacar e como"""
        p = self.parent
        janela = self.janela_ataque
        combo = self.combo_state
        
        # Se está em combo, tenta continuar
        if combo["em_combo"] and combo["pode_followup"]:
            if self._tentar_followup(distancia, inimigo):
                return True
        
        # Verifica se tem janela de oportunidade
        if janela["aberta"]:
            # Calcula se vale a pena atacar
            chance_ataque = janela["qualidade"]
            
            # Modificadores
            if distancia > p.alcance_ideal + 2.0:
                chance_ataque *= 0.5  # Longe demais
            if distancia < p.alcance_ideal * 0.5:
                chance_ataque *= 1.2  # Muito perto, aproveita
            
            # Personalidade
            if "OPORTUNISTA" in self.tracos:
                chance_ataque *= 1.3
            if "CALCULISTA" in self.tracos:
                chance_ataque *= 1.2 if janela["qualidade"] > 0.7 else 0.8
            if "PACIENTE" in self.tracos:
                chance_ataque *= 0.9 if janela["qualidade"] < 0.8 else 1.1
            
            # Momentum
            chance_ataque += self.momentum * 0.2
            
            # Emoções
            if self.raiva > 0.5:
                chance_ataque *= 1.2
            if self.medo > 0.6:
                chance_ataque *= 0.7
            
            if random.random() < chance_ataque:
                # Decide tipo de ataque baseado na janela
                return self._executar_ataque_oportunidade(janela, distancia, inimigo)
        
        return False
    
    def _executar_ataque_oportunidade(self, janela, distancia, inimigo):
        """Executa ataque aproveitando janela de oportunidade"""
        tipo = janela["tipo"]
        qualidade = janela["qualidade"]
        
        # Escolhe ação baseado no tipo de janela
        if tipo == "pos_ataque":
            # Contra-ataque rápido
            self.acao_atual = "CONTRA_ATAQUE"
            self.excitacao = min(1.0, self.excitacao + 0.2)
            return True
        
        elif tipo == "canalizando":
            # Interrompe com ataque pesado
            self.acao_atual = "ESMAGAR"
            return True
        
        elif tipo == "aereo":
            # Anti-air
            self.acao_atual = "ATAQUE_RAPIDO"
            return True
        
        elif tipo == "stunado":
            # Combo pesado
            self.acao_atual = "MATAR"
            self.modo_burst = True
            return True
        
        elif tipo == "exausto":
            # Pressiona
            self.acao_atual = "PRESSIONAR"
            return True
        
        elif tipo == "recuando":
            # Persegue
            self.acao_atual = "APROXIMAR"
            self.confianca = min(1.0, self.confianca + 0.1)
            return True
        
        elif tipo == "skill_cd":
            # Aproveita cooldown
            self.acao_atual = "MATAR"
            return True
        
        return False
    
    def _tentar_followup(self, distancia, inimigo):
        """Tenta continuar combo"""
        combo = self.combo_state
        
        if combo["timer_followup"] <= 0:
            combo["em_combo"] = False
            combo["pode_followup"] = False
            return False
        
        # Determina próximo ataque do combo
        ultimo = combo["ultimo_tipo_ataque"]
        proximo = None
        
        if ultimo == "ATAQUE_RAPIDO":
            proximo = random.choice(["ATAQUE_RAPIDO", "MATAR"])
        elif ultimo == "MATAR":
            proximo = random.choice(["ESMAGAR", "ATAQUE_RAPIDO"])
        elif ultimo == "ESMAGAR":
            proximo = random.choice(["MATAR", "FLANQUEAR"])
        else:
            proximo = "ATAQUE_RAPIDO"
        
        # Verifica distância
        if distancia > self.parent.alcance_ideal + 1.5:
            combo["em_combo"] = False
            return False
        
        self.acao_atual = proximo
        combo["hits_combo"] += 1
        combo["ultimo_tipo_ataque"] = proximo
        combo["timer_followup"] = 0.4  # Janela para próximo hit
        
        return True
    
    def _atualizar_combo_state(self, dt):
        """Atualiza estado do combo"""
        combo = self.combo_state
        if combo["timer_followup"] > 0:
            combo["timer_followup"] -= dt
        if combo["timer_followup"] <= 0 and combo["em_combo"]:
            combo["em_combo"] = False
            combo["hits_combo"] = 0
            combo["pode_followup"] = False
    
    # =========================================================================
    # SISTEMA DE BAITING (FINTAS) v8.0
    # =========================================================================
    
    def _processar_baiting(self, dt, distancia, inimigo):
        """Processa sistema de baiting/fintas"""
        bait = self.bait_state
        
        # Atualiza timer
        if bait["ativo"]:
            bait["timer"] -= dt
            if bait["timer"] <= 0:
                return self._executar_contra_bait(distancia, inimigo)
        
        # Decide se inicia bait
        if not bait["ativo"]:
            chance_bait = 0.0
            
            # Fatores que aumentam chance de bait
            if "TRICKSTER" in self.tracos:
                chance_bait += 0.15
            if "CALCULISTA" in self.tracos:
                chance_bait += 0.08
            if "OPORTUNISTA" in self.tracos:
                chance_bait += 0.05
            
            # Situacionais
            if self.momentum < -0.3:  # Perdendo, tenta enganar
                chance_bait += 0.1
            if self.leitura_oponente["agressividade_percebida"] > 0.7:
                chance_bait += 0.1  # Oponente agressivo, fácil de baitar
            
            if 3.0 < distancia < 6.0 and random.random() < chance_bait:
                tipo_bait = random.choice(["recuo_falso", "abertura_falsa", "hesitacao_falsa"])
                bait["ativo"] = True
                bait["tipo"] = tipo_bait
                bait["timer"] = random.uniform(0.3, 0.6)
                
                # Executa início do bait
                if tipo_bait == "recuo_falso":
                    self.acao_atual = "RECUAR"
                elif tipo_bait == "abertura_falsa":
                    self.acao_atual = "BLOQUEAR"
                elif tipo_bait == "hesitacao_falsa":
                    self.acao_atual = "CIRCULAR"
                
                return True
        
        return False
    
    def _executar_contra_bait(self, distancia, inimigo):
        """Executa contra-ataque após bait bem sucedido"""
        bait = self.bait_state
        bait["ativo"] = False
        
        # Verifica se oponente caiu no bait
        oponente_caiu = False
        if hasattr(inimigo, 'ai') and inimigo.ai:
            ai_ini = inimigo.ai
            if ai_ini.acao_atual in ["APROXIMAR", "MATAR", "ESMAGAR", "PRESSIONAR"]:
                oponente_caiu = True
        
        if oponente_caiu and distancia < 5.0:
            bait["sucesso_count"] += 1
            self.confianca = min(1.0, self.confianca + 0.15)
            self.excitacao = min(1.0, self.excitacao + 0.2)
            
            # Contra-ataque devastador
            if bait["tipo"] == "recuo_falso":
                self.acao_atual = "CONTRA_ATAQUE"
            elif bait["tipo"] == "abertura_falsa":
                self.acao_atual = "MATAR"
            else:
                self.acao_atual = "FLANQUEAR"
            
            return True
        else:
            bait["falha_count"] += 1
            return False
    
    # =========================================================================
    # SISTEMA DE MOMENTUM E PRESSÃO v8.0
    # =========================================================================
    
    def _atualizar_momentum(self, dt, distancia, inimigo):
        """Atualiza momentum da luta"""
        # Momentum aumenta quando:
        # - Dá hits
        # - Oponente recua
        # - HP do oponente cai
        # Momentum diminui quando:
        # - Recebe hits
        # - Você recua
        # - Seu HP cai
        
        # Decay natural para o neutro
        self.momentum *= 0.995
        
        # Baseado em hits recentes
        diff_hits = self.hits_dados_recente - self.hits_recebidos_recente
        self.momentum += diff_hits * 0.05
        
        # Baseado em HP
        p = self.parent
        meu_hp = p.vida / p.vida_max
        ini_hp = inimigo.vida / inimigo.vida_max
        hp_diff = meu_hp - ini_hp
        self.momentum += hp_diff * 0.02
        
        # Baseado em pressão
        if distancia < 3.0:
            if self.acao_atual in ["MATAR", "PRESSIONAR", "ESMAGAR"]:
                self.pressao_aplicada = min(1.0, self.pressao_aplicada + dt * 0.5)
            else:
                self.pressao_aplicada = max(0.0, self.pressao_aplicada - dt * 0.3)
        else:
            self.pressao_aplicada = max(0.0, self.pressao_aplicada - dt * 0.5)
        
        # Pressão recebida
        if hasattr(inimigo, 'ai') and inimigo.ai:
            ai_ini = inimigo.ai
            if distancia < 3.0 and ai_ini.acao_atual in ["MATAR", "PRESSIONAR", "ESMAGAR"]:
                self.pressao_recebida = min(1.0, self.pressao_recebida + dt * 0.5)
            else:
                self.pressao_recebida = max(0.0, self.pressao_recebida - dt * 0.3)
        
        # Clamp momentum
        self.momentum = max(-1.0, min(1.0, self.momentum))
    
    # =========================================================================
    # SISTEMA DE RECONHECIMENTO ESPACIAL v9.0
    # =========================================================================
    
    def _atualizar_consciencia_espacial(self, dt, distancia, inimigo):
        """
        Atualiza awareness de paredes, obstáculos e posicionamento tático.
        Chamado no processar() principal.
        """
        tatica = self.tatica_espacial
        
        # Otimização: só checa a cada 0.2s
        tatica["last_check_time"] += dt
        if tatica["last_check_time"] < 0.2:
            return
        tatica["last_check_time"] = 0.0
        
        p = self.parent
        esp = self.consciencia_espacial
        
        # Importa arena
        try:
            from arena import get_arena
            arena = get_arena()
        except:
            return  # Se arena não disponível, ignora
        
        # === DETECÇÃO DE PAREDES ===
        margem_detecao = 3.0  # Começa a detectar parede a 3m
        
        dist_norte = p.pos[1] - arena.min_y
        dist_sul = arena.max_y - p.pos[1]
        dist_oeste = p.pos[0] - arena.min_x
        dist_leste = arena.max_x - p.pos[0]
        
        # Encontra parede mais próxima
        paredes = [
            ("norte", dist_norte),
            ("sul", dist_sul),
            ("oeste", dist_oeste),
            ("leste", dist_leste),
        ]
        parede_mais_proxima = min(paredes, key=lambda x: x[1])
        
        esp["parede_proxima"] = parede_mais_proxima[0]
        esp["distancia_parede"] = parede_mais_proxima[1]
        
        # === DETECÇÃO DE OBSTÁCULOS ===
        obs_mais_proximo = None
        dist_obs_min = 999.0
        
        if hasattr(arena, 'obstaculos'):
            for obs in arena.obstaculos:
                if not obs.solido:
                    continue
                
                dx = p.pos[0] - obs.x
                dy = p.pos[1] - obs.y
                dist = math.hypot(dx, dy) - (obs.largura + obs.altura) / 4
                
                if dist < dist_obs_min:
                    dist_obs_min = dist
                    obs_mais_proximo = obs
        
        esp["obstaculo_proxima"] = obs_mais_proximo
        esp["distancia_obstaculo"] = dist_obs_min
        
        # === ANÁLISE DE CAMINHOS LIVRES ===
        # Verifica se há obstáculos bloqueando cada direção
        check_dist = 2.0  # Distância de checagem
        
        # Frente (em direção ao inimigo)
        ang_inimigo = math.atan2(inimigo.pos[1] - p.pos[1], inimigo.pos[0] - p.pos[0])
        check_x_frente = p.pos[0] + math.cos(ang_inimigo) * check_dist
        check_y_frente = p.pos[1] + math.sin(ang_inimigo) * check_dist
        esp["caminho_livre"]["frente"] = not arena.colide_obstaculo(
            check_x_frente, check_y_frente, p.raio_fisico
        )
        
        # Trás (oposto ao inimigo)
        check_x_tras = p.pos[0] - math.cos(ang_inimigo) * check_dist
        check_y_tras = p.pos[1] - math.sin(ang_inimigo) * check_dist
        esp["caminho_livre"]["tras"] = not arena.colide_obstaculo(
            check_x_tras, check_y_tras, p.raio_fisico
        )
        
        # Esquerda (perpendicular)
        ang_esq = ang_inimigo + math.pi / 2
        check_x_esq = p.pos[0] + math.cos(ang_esq) * check_dist
        check_y_esq = p.pos[1] + math.sin(ang_esq) * check_dist
        esp["caminho_livre"]["esquerda"] = not arena.colide_obstaculo(
            check_x_esq, check_y_esq, p.raio_fisico
        )
        
        # Direita
        ang_dir = ang_inimigo - math.pi / 2
        check_x_dir = p.pos[0] + math.cos(ang_dir) * check_dist
        check_y_dir = p.pos[1] + math.sin(ang_dir) * check_dist
        esp["caminho_livre"]["direita"] = not arena.colide_obstaculo(
            check_x_dir, check_y_dir, p.raio_fisico
        )
        
        # === AVALIAÇÃO DE POSIÇÃO TÁTICA ===
        # Encurralado = parede atrás E sem caminhos laterais
        parede_atras = (
            (esp["parede_proxima"] == "norte" and p.pos[1] < inimigo.pos[1]) or
            (esp["parede_proxima"] == "sul" and p.pos[1] > inimigo.pos[1]) or
            (esp["parede_proxima"] == "oeste" and p.pos[0] < inimigo.pos[0]) or
            (esp["parede_proxima"] == "leste" and p.pos[0] > inimigo.pos[0])
        )
        
        sem_saidas = (
            not esp["caminho_livre"]["esquerda"] and 
            not esp["caminho_livre"]["direita"] and
            not esp["caminho_livre"]["tras"]
        )
        
        esp["encurralado"] = (
            parede_atras and sem_saidas and 
            esp["distancia_parede"] < 2.0
        )
        
        # Oponente contra parede
        dist_ini_parede = min(
            inimigo.pos[1] - arena.min_y,
            arena.max_y - inimigo.pos[1],
            inimigo.pos[0] - arena.min_x,
            arena.max_x - inimigo.pos[0]
        )
        esp["oponente_contra_parede"] = dist_ini_parede < 2.5
        
        # Posição geral
        if esp["encurralado"]:
            esp["posicao_tatica"] = "encurralado"
        elif esp["distancia_parede"] < 2.0:
            esp["posicao_tatica"] = "perto_parede"
        elif esp["oponente_contra_parede"]:
            esp["posicao_tatica"] = "vantagem"
        else:
            esp["posicao_tatica"] = "centro"
        
        # === ANÁLISE TÁTICA ===
        self._avaliar_taticas_espaciais(distancia, inimigo)
    
    def _avaliar_taticas_espaciais(self, distancia, inimigo):
        """Avalia e define táticas espaciais baseadas na situação"""
        esp = self.consciencia_espacial
        tatica = self.tatica_espacial
        p = self.parent
        
        # Reset táticas
        tatica["usando_cobertura"] = False
        tatica["forcar_canto"] = False
        tatica["recuar_para_obstaculo"] = False
        tatica["flanquear_obstaculo"] = False
        
        # === SE ENCURRALADO ===
        if esp["encurralado"]:
            # Pânico ou contra-ataque desesperado
            self.medo = min(1.0, self.medo + 0.2)
            self.hesitacao = max(0.0, self.hesitacao - 0.3)  # Menos hesitação, ação urgente
            
            # Tenta escapar pelos lados
            if esp["caminho_livre"]["esquerda"]:
                self.dir_circular = 1
            elif esp["caminho_livre"]["direita"]:
                self.dir_circular = -1
            
            # Ou luta com tudo
            if "BERSERKER" in self.tracos or "KAMIKAZE" in self.tracos:
                self.raiva = 1.0
        
        # === OPONENTE CONTRA PAREDE ===
        if esp["oponente_contra_parede"] and distancia < 6.0:
            tatica["forcar_canto"] = True
            self.confianca = min(1.0, self.confianca + 0.1)
            
            # Pressiona mais
            if "PREDADOR" in self.tracos or "OPORTUNISTA" in self.tracos:
                self.agressividade_base = min(1.0, self.agressividade_base + 0.2)
        
        # === USO DE COBERTURA ===
        if esp["obstaculo_proxima"] and esp["distancia_obstaculo"] < 2.0:
            # Usa obstáculo como cobertura se:
            # - HP baixo
            # - Oponente tem projéteis
            # - É cauteloso
            
            hp_pct = p.vida / p.vida_max
            usa_cobertura = (
                hp_pct < 0.4 or
                "CAUTELOSO" in self.tracos or
                "TATICO" in self.tracos or
                self.medo > 0.5
            )
            
            if usa_cobertura and distancia > 4.0:
                tatica["usando_cobertura"] = True
                tatica["tipo_cobertura"] = esp["obstaculo_proxima"].tipo
        
        # === FLANQUEAMENTO COM OBSTÁCULOS ===
        if (esp["obstaculo_proxima"] and 
            3.0 < distancia < 8.0 and
            esp["distancia_obstaculo"] < 4.0):
            
            # Usa obstáculo pra flanquear
            if "TATICO" in self.tracos or "INTELIGENTE" in self.tracos:
                tatica["flanquear_obstaculo"] = True
        
        # === EVITA RECUAR PARA OBSTÁCULO ===
        if not esp["caminho_livre"]["tras"] and distancia < 4.0:
            tatica["recuar_para_obstaculo"] = True
            # Aviso mental: não pode recuar!
            if self.acao_atual in ["RECUAR", "FUGIR"]:
                # Muda pra movimento lateral
                self.acao_atual = "CIRCULAR"
    
    def _aplicar_modificadores_espaciais(self, distancia, inimigo):
        """
        Aplica modificadores de comportamento baseados no ambiente.
        Chamado durante a escolha de ação.
        """
        esp = self.consciencia_espacial
        tatica = self.tatica_espacial
        
        # === MODIFICADORES POR SITUAÇÃO ===
        
        # Se encurralado
        if esp["encurralado"]:
            # Força ações de escape ou contra-ataque desesperado
            if self.medo > self.raiva:
                if random.random() < 0.4:
                    self.acao_atual = "CIRCULAR"  # Tenta escapar pelos lados
            else:
                if random.random() < 0.3:
                    self.acao_atual = random.choice(["MATAR", "CONTRA_ATAQUE"])
        
        # Se oponente contra parede
        if tatica["forcar_canto"]:
            if random.random() < 0.3:
                self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "ESMAGAR"])
        
        # Se usando cobertura
        if tatica["usando_cobertura"]:
            if random.random() < 0.25:
                # Fica atrás do obstáculo
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "BLOQUEAR"])
        
        # Se flanqueando com obstáculo
        if tatica["flanquear_obstaculo"]:
            if random.random() < 0.2:
                self.acao_atual = "FLANQUEAR"
        
        # Se recuando pra obstáculo
        if tatica["recuar_para_obstaculo"]:
            # NUNCA recua
            if self.acao_atual in ["RECUAR", "FUGIR"]:
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "FLANQUEAR"])
        
        # === MODIFICADORES POR DIREÇÃO ===
        
        # Se caminho da frente bloqueado
        if not esp["caminho_livre"]["frente"]:
            if self.acao_atual in ["APROXIMAR", "MATAR", "PRESSIONAR"]:
                # Circula ao invés de ir direto
                if random.random() < 0.4:
                    self.acao_atual = "FLANQUEAR"
        
        # Se perto de parede
        if esp["distancia_parede"] < 2.0:
            # Ajusta direção circular pra não bater na parede
            if esp["parede_proxima"] in ["oeste", "leste"]:
                # Parede lateral - ajusta se necessário
                if esp["parede_proxima"] == "oeste" and self.dir_circular < 0:
                    self.dir_circular = 1
                elif esp["parede_proxima"] == "leste" and self.dir_circular > 0:
                    self.dir_circular = -1
    
    def _ajustar_direcao_por_ambiente(self, direcao_alvo):
        """
        Ajusta uma direção de movimento para evitar obstáculos.
        Retorna nova direção segura.
        """
        esp = self.consciencia_espacial
        p = self.parent
        
        # Converte direção pra radianos
        ang_rad = math.radians(direcao_alvo)
        
        # Verifica se a direção está bloqueada
        try:
            from arena import get_arena
            arena = get_arena()
            
            # Testa ponto à frente
            test_dist = 1.5
            test_x = p.pos[0] + math.cos(ang_rad) * test_dist
            test_y = p.pos[1] + math.sin(ang_rad) * test_dist
            
            if arena.colide_obstaculo(test_x, test_y, p.raio_fisico):
                # Bloqueado! Tenta alternativas
                alternativas = [
                    direcao_alvo + 45,
                    direcao_alvo - 45,
                    direcao_alvo + 90,
                    direcao_alvo - 90,
                    direcao_alvo + 135,
                    direcao_alvo - 135,
                ]
                
                for alt_ang in alternativas:
                    alt_rad = math.radians(alt_ang)
                    alt_x = p.pos[0] + math.cos(alt_rad) * test_dist
                    alt_y = p.pos[1] + math.sin(alt_rad) * test_dist
                    
                    if not arena.colide_obstaculo(alt_x, alt_y, p.raio_fisico):
                        return alt_ang
                
                # Se tudo bloqueado, fica parado (retorna direção atual)
                return direcao_alvo
        except:
            pass
        
        return direcao_alvo
    
    # =========================================================================
    # SISTEMA DE ESTADOS HUMANOS v8.0
    # =========================================================================
    
    def _atualizar_estados_humanos(self, dt, distancia, inimigo):
        """Atualiza hesitação, impulso e outros estados humanos"""
        p = self.parent
        hp_pct = p.vida / p.vida_max
        
        # === HESITAÇÃO ===
        # Aumenta quando: 
        # - Situação desfavorável
        # - Oponente muito agressivo
        # - Tomou muito dano recentemente
        
        base_hesitacao = 0.1
        if hp_pct < 0.3:
            base_hesitacao += 0.2
        if self.momentum < -0.5:
            base_hesitacao += 0.15
        if self.hits_recebidos_recente >= 3:
            base_hesitacao += 0.2
        if self.pressao_recebida > 0.7:
            base_hesitacao += 0.15
        
        # Personalidade
        if "DETERMINADO" in self.tracos:
            base_hesitacao *= 0.5
        if "FRIO" in self.tracos:
            base_hesitacao *= 0.6
        if "COVARDE" in self.tracos:
            base_hesitacao *= 1.5
        if "BERSERKER" in self.tracos:
            base_hesitacao *= 0.3
        
        self.hesitacao = max(0.0, min(0.8, base_hesitacao))
        
        # === IMPULSO ===
        # Aumenta quando:
        # - Raiva alta
        # - Oponente com HP baixo
        # - Momento favorável
        
        base_impulso = 0.1
        if self.raiva > 0.6:
            base_impulso += 0.3
        if inimigo.vida / inimigo.vida_max < 0.25:
            base_impulso += 0.25
        if self.momentum > 0.5:
            base_impulso += 0.2
        if self.excitacao > 0.7:
            base_impulso += 0.15
        
        # Personalidade
        if "IMPRUDENTE" in self.tracos:
            base_impulso *= 1.5
        if "CALCULISTA" in self.tracos:
            base_impulso *= 0.5
        if "PACIENTE" in self.tracos:
            base_impulso *= 0.6
        
        self.impulso = max(0.0, min(0.9, base_impulso))
        
        # === CONGELAMENTO ===
        # Ocorre sob pressão extrema
        
        base_congela = 0.0
        if self.pressao_recebida > 0.8:
            base_congela = 0.3
        if self.hits_recebidos_recente >= 4 and self.tempo_desde_dano < 1.0:
            base_congela += 0.4
        
        if "FRIO" in self.tracos:
            base_congela *= 0.2
        if "MEDROSO" in self.tracos:
            base_congela *= 1.5
        
        self.congelamento = max(0.0, min(0.6, base_congela))
        
        # === DESCANSO ===
        # Micro-pausas após bursts de ação
        self.burst_counter = max(0, self.burst_counter - dt * 2)
        if self.burst_counter > 5:
            self.descanso_timer = random.uniform(0.3, 0.8)
            self.burst_counter = 0
    
    def _verificar_hesitacao(self, distancia, inimigo):
        """Verifica se a IA hesita neste frame"""
        # Descanso forçado
        if self.descanso_timer > 0:
            self.descanso_timer -= 0.016
            self.acao_atual = "CIRCULAR"
            return True
        
        # Congelamento sob pressão
        if random.random() < self.congelamento * 0.1:
            self.acao_atual = "BLOQUEAR"
            return True
        
        # Hesitação
        if random.random() < self.hesitacao * 0.05:
            # Hesita - faz algo defensivo
            self.acao_atual = random.choice(["CIRCULAR", "BLOQUEAR", "RECUAR"])
            return True
        
        # Impulso pode cancelar hesitação
        if random.random() < self.impulso * 0.1:
            self.acao_atual = random.choice(["MATAR", "APROXIMAR", "PRESSIONAR"])
            self.burst_counter += 1
            return True
        
        return False
    
    def _registrar_acao(self):
        """Registra ação para evitar repetição excessiva"""
        self.historico_acoes.append(self.acao_atual)
        if len(self.historico_acoes) > 10:
            self.historico_acoes.pop(0)
        
        # Conta repetições
        if self.acao_atual in self.repeticao_contador:
            self.repeticao_contador[self.acao_atual] += 1
        else:
            self.repeticao_contador[self.acao_atual] = 1
        
        # Decay das contagens
        for key in list(self.repeticao_contador.keys()):
            if key != self.acao_atual:
                self.repeticao_contador[key] = max(0, self.repeticao_contador[key] - 0.5)

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
        """Executa ação sincronizada de momento cinematográfico v8.0"""
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
        
        # === NOVAS AÇÕES v8.0 ===
        if acao == "TROCAR_RAPIDO":
            # Troca rápida de golpes - alterna entre ataque e defesa
            if random.random() < 0.6:
                self.acao_atual = random.choice(["ATAQUE_RAPIDO", "MATAR"])
            else:
                self.acao_atual = random.choice(["CONTRA_ATAQUE", "FLANQUEAR"])
            self.excitacao = min(1.0, self.excitacao + 0.15)
            return True
        
        if acao == "REAGIR_ESQUIVA":
            # Reage a uma esquiva próxima
            if random.random() < 0.5:
                self.acao_atual = "CONTRA_ATAQUE"
            else:
                self.acao_atual = "CIRCULAR"
            return True
        
        if acao == "PRESSIONAR_CONTINUO":
            # Mantém pressão sobre o oponente
            self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "APROXIMAR"])
            self.pressao_aplicada = min(1.0, self.pressao_aplicada + 0.1)
            return True
        
        if acao == "RESISTIR_PRESSAO":
            # Resiste à pressão do oponente
            if self.raiva > 0.6 or random.random() < 0.3:
                self.acao_atual = "CONTRA_ATAQUE"
            else:
                self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR", "COMBATE"])
            return True
        
        if acao == "SEPARAR":
            # Ambos se afastam brevemente
            self.acao_atual = "RECUAR"
            self.timer_decisao = 0.5
            return True
        
        if acao == "FINTA":
            # Executa uma finta
            if not self.bait_state["ativo"]:
                self.bait_state["ativo"] = True
                self.bait_state["tipo"] = "finta_coreografada"
                self.bait_state["timer"] = 0.4
            self.acao_atual = random.choice(["APROXIMAR_LENTO", "CIRCULAR", "COMBATE"])
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
    # MOVIMENTO v8.0 COM INTELIGÊNCIA HUMANA
    # =========================================================================
    
    def _decidir_movimento(self, distancia, inimigo):
        """Decide ação de movimento com inteligência humana avançada"""
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
        
        # === NOVOS MODIFICADORES v8.0 ===
        self._aplicar_modificadores_momentum(distancia, inimigo_hp_pct)
        self._aplicar_modificadores_leitura(distancia, inimigo)
        self._evitar_repeticao_excessiva()
        
        # === MODIFICADORES ESPACIAIS v9.0 ===
        self._aplicar_modificadores_espaciais(distancia, inimigo)
    
    def _aplicar_modificadores_momentum(self, distancia, inimigo_hp_pct):
        """Aplica modificadores baseados no momentum da luta"""
        # Momentum positivo = mais agressivo
        if self.momentum > 0.3:
            if self.acao_atual in ["CIRCULAR", "RECUAR", "BLOQUEAR"]:
                if random.random() < self.momentum * 0.5:
                    self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "APROXIMAR"])
        
        # Momentum negativo = mais cauteloso (mas não covarde)
        elif self.momentum < -0.3:
            if self.acao_atual in ["MATAR", "ESMAGAR"]:
                if random.random() < abs(self.momentum) * 0.3:
                    self.acao_atual = random.choice(["COMBATE", "FLANQUEAR", "CIRCULAR"])
        
        # Pressão alta = decisões mais extremas
        if self.pressao_aplicada > 0.7:
            if random.random() < 0.3:
                self.acao_atual = random.choice(["MATAR", "ESMAGAR", "PRESSIONAR"])
        
        if self.pressao_recebida > 0.7:
            if random.random() < 0.25:
                # Ou contra-ataca ou recua - decisão de momento
                if self.raiva > self.medo:
                    self.acao_atual = random.choice(["CONTRA_ATAQUE", "MATAR"])
                else:
                    self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "FLANQUEAR"])
    
    def _aplicar_modificadores_leitura(self, distancia, inimigo):
        """Aplica modificadores baseados na leitura do oponente"""
        leitura = self.leitura_oponente
        
        # Se oponente é previsível, aproveita
        if leitura["previsibilidade"] > 0.7:
            if random.random() < 0.2:
                # Antecipa e contra
                if leitura["agressividade_percebida"] > 0.6:
                    self.acao_atual = "CONTRA_ATAQUE"
                else:
                    self.acao_atual = "PRESSIONAR"
        
        # Se oponente é muito agressivo
        if leitura["agressividade_percebida"] > 0.8:
            if "REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos:
                if random.random() < 0.3:
                    self.acao_atual = "CONTRA_ATAQUE"
        
        # Se oponente pula muito, posiciona melhor
        if leitura["frequencia_pulo"] > 0.4:
            if random.random() < 0.2:
                self.acao_atual = "COMBATE"  # Espera ele cair
        
        # Adapta à tendência lateral do oponente
        if distancia < 4.0:
            if leitura["tendencia_esquerda"] > 0.65:
                if random.random() < 0.15:
                    self.dir_circular = 1  # Vai pro outro lado
            elif leitura["tendencia_esquerda"] < 0.35:
                if random.random() < 0.15:
                    self.dir_circular = -1
    
    def _evitar_repeticao_excessiva(self):
        """Evita repetir a mesma ação muitas vezes seguidas"""
        if len(self.historico_acoes) < 3:
            return
        
        # Verifica repetição
        ultimas_3 = self.historico_acoes[-3:]
        if ultimas_3.count(self.acao_atual) >= 2:
            # Está repetindo muito, varia
            if random.random() < 0.4:
                acoes_alternativas = [
                    "MATAR", "CIRCULAR", "FLANQUEAR", "COMBATE", 
                    "APROXIMAR", "ATAQUE_RAPIDO", "PRESSIONAR"
                ]
                # Remove a ação atual das alternativas
                acoes_alternativas = [a for a in acoes_alternativas if a != self.acao_atual]
                self.acao_atual = random.choice(acoes_alternativas)
    
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
    # CALLBACKS v8.0
    # =========================================================================
    
    def on_hit_dado(self):
        """Quando acerta um golpe - integrado com sistema de combos"""
        self.hits_dados_total += 1
        self.hits_dados_recente += 1
        self.tempo_desde_hit = 0.0
        self.combo_atual += 1
        self.max_combo = max(self.max_combo, self.combo_atual)
        
        self.confianca = min(1.0, self.confianca + 0.05)
        self.frustracao = max(0, self.frustracao - 0.1)
        self.excitacao = min(1.0, self.excitacao + 0.1)
        
        # Sistema de combo
        combo = self.combo_state
        combo["em_combo"] = True
        combo["hits_combo"] += 1
        combo["ultimo_tipo_ataque"] = self.acao_atual
        combo["pode_followup"] = True
        combo["timer_followup"] = 0.5  # Janela para continuar combo
        
        # Momentum positivo
        self.momentum = min(1.0, self.momentum + 0.15)
        self.burst_counter += 1
        
        if "SEDE_SANGUE" in self.quirks:
            self.adrenalina = min(1.0, self.adrenalina + 0.2)
        
        # Combo master continua pressionando
        if "COMBO_MASTER" in self.tracos or "MESTRE_COMBO" in self.quirks:
            combo["timer_followup"] = 0.7
    
    def on_hit_recebido(self, dano):
        """Quando recebe dano"""
        # Momentum negativo
        self.momentum = max(-1.0, self.momentum - 0.1)
        
        # Quebra combo
        self.combo_state["em_combo"] = False
        self.combo_state["hits_combo"] = 0
    
    def on_skill_usada(self, skill_nome, sucesso):
        """Quando usa skill"""
        if not sucesso:
            self.frustracao = min(1.0, self.frustracao + 0.1)
        else:
            self.burst_counter += 2  # Skills contam mais pro burst
    
    def on_inimigo_fugiu(self):
        """Quando inimigo foge"""
        # Ganha momentum
        self.momentum = min(1.0, self.momentum + 0.1)
        
        if "PERSEGUIDOR" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.2)
            self.acao_atual = "APROXIMAR"
        if "PREDADOR" in self.tracos:
            self.excitacao = min(1.0, self.excitacao + 0.2)
        
        # Marca como oportunidade
        self.janela_ataque["aberta"] = True
        self.janela_ataque["tipo"] = "fugindo"
        self.janela_ataque["qualidade"] = 0.6
        self.janela_ataque["duracao"] = 1.0
    
    def on_esquiva_sucesso(self):
        """Quando desvia com sucesso de um ataque"""
        self.confianca = min(1.0, self.confianca + 0.1)
        self.excitacao = min(1.0, self.excitacao + 0.15)
        
        # Abre janela de contra-ataque
        self.janela_ataque["aberta"] = True
        self.janela_ataque["tipo"] = "pos_esquiva"
        self.janela_ataque["qualidade"] = 0.85
        self.janela_ataque["duracao"] = 0.5
        
        if "CONTRA_ATAQUE_PERFEITO" in self.quirks:
            self.reacao_pendente = "CONTRA_MATAR"
