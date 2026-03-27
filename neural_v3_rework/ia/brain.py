"""
=============================================================================
NEURAL FIGHTS - CÃ©rebro da IA v11.0 WEAPON REWORK EDITION
=============================================================================
CHANGELOG v11.0:
- ReformulaÃ§Ã£o da IA para Mangual: spin acumulativo, distÃ¢ncia de zona de spin,
  detecÃ§Ã£o de zona morta expandida, arquÃ©tipo BERSERKER
- ReformulaÃ§Ã£o da IA para Adagas GÃªmeas: alcance ideal reduzido (0.50x),
  modo combo colado, dash agressivo para manter combo ativo
- PercepÃ§Ã£o de armas inimigas: lÃ³gica contra Mangual (entrar na zona morta)
  e contra Adagas GÃªmeas (manter distÃ¢ncia, punir aproximaÃ§Ã£o)
- Bugfix: lÃ³gica de fallback para estilo de arma None/vazio
- Bugfix: detecÃ§Ã£o de alcance_agressao para Adagas GÃªmeas
- CompatÃ­vel com novos campos anim_* em armas.json
=============================================================================
Sistema de inteligÃªncia artificial com comportamento humano realista,
consciÃªncia espacial avanÃ§ada e percepÃ§Ã£o de armas.

NOVIDADES v10.0:
- PercepÃ§Ã£o de armas inimigas (tipo, alcance, perigo)
- CÃ¡lculo de zonas de ameaÃ§a baseado na arma do oponente
- AdaptaÃ§Ã£o de distÃ¢ncia ideal baseado em matchup de armas
- AnÃ¡lise de vantagens/desvantagens de arma
- Comportamentos especÃ­ficos contra cada tipo de arma
- Sweet spots e zonas mortas de armas

SISTEMAS v9.0 (mantidos):
- Sistema de reconhecimento de paredes e obstÃ¡culos
- ConsciÃªncia espacial tÃ¡tica (encurralado, vantagem, cobertura)
- Uso inteligente de obstÃ¡culos (cobertura, flanqueamento)
- DetecÃ§Ã£o de quando oponente estÃ¡ contra parede
- Evita recuar para obstÃ¡culos
- Ajuste automÃ¡tico de trajetÃ³ria para evitar colisÃµes
- AnÃ¡lise de caminhos livres em todas direÃ§Ãµes
- Comportamentos especiais quando encurralado

SISTEMAS v8.0 (mantidos):
- Sistema de antecipaÃ§Ã£o de ataques (lÃª o oponente)
- Desvios inteligentes com timing humano
- Baiting e fintas (engana o oponente)
- Janelas de oportunidade (ataca nos momentos certos)
- PressÃ£o psicolÃ³gica e momentum
- HesitaÃ§Ã£o realista e impulsos
- Leitura de padrÃµes do oponente
- Combos e follow-ups inteligentes

CombinaÃ§Ãµes possÃ­veis:
- 50+ traÃ§os Ã— 5 slots = milhares de combinaÃ§Ãµes de traÃ§os
- 25+ arquÃ©tipos
- 15+ estilos de luta
- 20+ quirks
- 10+ filosofias
- 10 humores dinÃ¢micos

Total: CENTENAS DE MILHARES de personalidades Ãºnicas!
=============================================================================
"""

import random
import math
import re as _re_arquetipo
import logging

_log = logging.getLogger("neural_ai")

from utilitarios.config import PPM
from utilitarios.config import (
    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,
    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,
    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,
    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,
    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,
    AI_RAND_POOL_SIZE,
    DEBUG_AI, DEBUG_AI_FIGHTER,         # F01 Sprint 9: modo debug da IA
)
from nucleo.physics import normalizar_angulo
from nucleo.skills import get_skill_data
from modelos import get_class_data
from ia.choreographer import CombatChoreographer
from ia.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,
    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES
)
from ia.behavior_profiles import FALLBACK_PROFILE
from ia.weapon_ai import arma_dispara_em_linha, obter_metricas_arma, resolver_familia_arma

try:
    from nucleo.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
    WEAPON_ANALYSIS_AVAILABLE = True
except ImportError:
    WEAPON_ANALYSIS_AVAILABLE = False

try:
    from ia.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority
    SKILL_STRATEGY_AVAILABLE = True
except ImportError:
    SKILL_STRATEGY_AVAILABLE = False

try:
    from nucleo.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

try:
    from nucleo.arena import get_arena as _get_arena
except ImportError:
    _get_arena = None

# â”€â”€ Mixin imports â”€â”€
from ia.brain_personality import PersonalityMixin
from ia.brain_perception import PerceptionMixin
from ia.brain_evasion import EvasionMixin
from ia.brain_combat import CombatMixin
from ia.brain_skills import SkillsMixin
from ia.brain_spatial import SpatialMixin
from ia.brain_emotions import EmotionsMixin
from ia.brain_choreography import ChoreographyMixin


class AIBrain(PersonalityMixin, PerceptionMixin, EvasionMixin, CombatMixin, SkillsMixin, SpatialMixin, EmotionsMixin, ChoreographyMixin):
    """
    CÃ©rebro da IA v10.0 WEAPON PERCEPTION EDITION - Sistema de personalidade procedural com
    comportamento humano realista, inteligÃªncia de combate avanÃ§ada e percepÃ§Ã£o de armas.
    """

    # MEL-AI-07: MemÃ³ria de rivalidade entre lutas (modo torneio).
    # Mapeamento: id_oponente â†’ dict com estatÃ­sticas acumuladas de confrontos anteriores.
    # Persiste durante toda a sessÃ£o do torneio (instÃ¢ncias de AIBrain sÃ£o recriadas a cada luta,
    # mas este dicionÃ¡rio de classe sobrevive).
    _historico_combates: dict = {}


    def __init__(self, parent):
        self.parent = parent
        self._initialize_runtime_decision_state()
        self._initialize_emotional_state()
        self._initialize_combat_memory_state(parent)
        self._initialize_personality_state()
        self._initialize_internal_cooldowns_and_skill_state()
        self._initialize_choreography_state()
        self._initialize_human_behavior_state()
        self._initialize_spatial_and_weapon_awareness_state()
        self._initialize_multi_combat_state()
        self._initialize_update_group_timers()

        # Gera personalidade Ãºnica
        self._gerar_personalidade()

    def _initialize_runtime_decision_state(self) -> None:
        self.timer_decisao = 0.0
        self.acao_atual = "NEUTRO"
        self._tempo_sem_decisao = 0.0
        self.dir_circular = random.choice([-1, 1])
        self._dir_circular_cd = 0.0  # Cooldown antes de permitir nova mudanÃ§a de dir_circular
        self.circular_consecutivo = 0  # Conta decisÃµes CIRCULAR seguidas

    def _initialize_emotional_state(self) -> None:
        # === EMOÃ‡Ã•ES (0.0 a 1.0) ===
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

    def _initialize_combat_memory_state(self, parent) -> None:
        # === MEMÃ“RIA DE COMBATE ===
        self.hits_recebidos_total = 0
        self.hits_dados_total = 0
        self.hits_recebidos_recente = 0
        self.hits_dados_recente = 0
        self.tempo_desde_dano = 5.0
        self.tempo_desde_hit = 5.0
        self.ultimo_dano_recebido = 0.0  # Valor do Ãºltimo dano recebido
        self.vezes_que_fugiu = 0
        self.ultimo_hp = parent.vida
        self.combo_atual = 0
        self.max_combo = 0
        self.tempo_combate = 0.0
        self._tempo_sem_ataque_efetivo = 0.0  # Stall detection: tempo em aÃ§Ã£o ofensiva sem p.atacando

    def _initialize_personality_state(self) -> None:
        # === PERSONALIDADE GERADA ===
        self.arquetipo = "GUERREIRO"
        self.estilo_luta = "BALANCED"
        self.filosofia = "EQUILIBRIO"
        self.tracos = []
        self.quirks = []
        self.agressividade_base = 0.5
        # BUG-AI-05 fix: modificador temporÃ¡rio de agressividade â€” nÃ£o altera a personalidade base.
        # SituaÃ§Ãµes tÃ¡ticas (oponente contra parede, instintos, execute_mode) ajustam aqui.
        # Decai ao longo do tempo de volta a 0 em _atualizar_emocoes.
        self._agressividade_temp_mod = 0.0
        self.pressao_ritmo = 0.0
        
        # === NOVOS SISTEMAS v11.0 ===
        self.instintos = []  # Lista de instintos ativos
        self.ritmo = None    # Ritmo de batalha atual
        self.ritmo_fase_atual = 0  # Ãndice da fase atual
        self.ritmo_timer = 0.0     # Timer para mudanÃ§a de fase
        self.ritmo_modificadores = {"agressividade": 0, "defesa": 0, "mobilidade": 0}

        # === BEHAVIOR PROFILE (Phase 1 AI Overhaul) ===
        self._behavior_profile = FALLBACK_PROFILE

        # MEL-ARQ-06: flag de debug de decisÃ£o de movimento.
        # Quando True, cada frame que chamar _decidir_movimento emite um log DEBUG
        # indicando qual etapa (override, estratÃ©gia de arma ou genÃ©rica) controlou
        # a decisÃ£o e qual aÃ§Ã£o resultou.  Ãštil para depurar comportamentos inesperados.
        # Ativar via: ai_instance.DEBUG_AI_DECISIONS = True
        self.DEBUG_AI_DECISIONS = False

    def _initialize_internal_cooldowns_and_skill_state(self) -> None:
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
            "SUMMON": [],
            "TRAP": [],
            "TRANSFORM": [],
            "CHANNEL": []
        }
        
        # === SISTEMA DE ESTRATÃ‰GIA DE SKILLS v1.0 ===
        self.skill_strategy = None  # Inicializado apÃ³s gerar personalidade
        
        # === ESTADO ESPECIAL ===
        self.modo_berserk = False
        self.modo_defensivo = False
        self.modo_burst = False
        self.executando_quirk = False

    def _initialize_choreography_state(self) -> None:
        # === SISTEMA DE COREOGRAFIA v5.0 ===
        self.momento_cinematografico = None
        self.acao_sincronizada = None
        self.respondendo_a_oponente = False
        self.memoria_cena = {
            "tipo": None,
            "intensidade": 0.0,
            "duracao": 0.0,
        }
        self.memoria_oponente = {
            "id_atual": None,
            "ultima_acao": None,
            "padrao_detectado": None,
            "padrao_dominante": None,
            "relacao_dominante": None,
            "vezes_fugiu": 0,
            "vezes_atacou": 0,
            "estilo_percebido": None,
            "ameaca_nivel": 0.5,
            "ultima_forma_hibrida": None,
            "ultimo_burst_orbital_pronto": False,
            "adaptacao_por_oponente": {},
        }
        self.reacao_pendente = None
        self.tempo_reacao = 0.0

    def _initialize_human_behavior_state(self) -> None:
        # === SISTEMA HUMANO v8.0 - NOVIDADES ===

        # AntecipaÃ§Ã£o e leitura do oponente
        self.leitura_oponente = {
            "ataque_iminente": False,
            "direcao_provavel": 0.0,
            "tempo_para_ataque": 0.0,
            "padrao_movimento": [],  # Ãšltimos 10 movimentos
            "padrao_ataque": [],     # Ãšltimos 10 ataques
            "tendencia_esquerda": 0.5,
            "frequencia_pulo": 0.0,
            "agressividade_percebida": 0.5,
            "previsibilidade": 0.5,  # QuÃ£o previsÃ­vel Ã© o oponente
            # BUG-AI-01 fix: chave faltante â€” usada em _processar_skills_estrategico (Prioridade 3)
            "reposicionando": False,
            # BUG-AI-04 fix: chave faltante â€” usada em _processar_instintos
            "padrao_detectado": False,
        }
        
        # Sistema de janelas de oportunidade
        self.janela_ataque = {
            "aberta": False,
            "tipo": None,  # "pos_ataque", "recuperando", "fora_alcance", "pulo"
            "duracao": 0.0,
            "qualidade": 0.0,  # 0-1, quÃ£o boa Ã© a janela
        }
        
        # Sistema de baiting (isca/finta)
        self.bait_state = {
            "ativo": False,
            "tipo": None,  # "recuo_falso", "abertura_falsa", "skill_falsa"
            "timer": 0.0,
            "sucesso_count": 0,
            "falha_count": 0,
            # FP-04 fix: registra aÃ§Ã£o do inimigo antes do bait para detectar mudanÃ§a real
            "acao_inimigo_antes": None,
            # MEL-AI-04 fix: fase de observaÃ§Ã£o pÃ³s-bait separada do tempo de execuÃ§Ã£o.
            # ApÃ³s o bait terminar, aguarda BAIT_JANELA_OBSERVACAO segundos observando
            # se o oponente mudou de comportamento antes de declarar sucesso/falha.
            "fase_obs": False,      # True durante a janela de observaÃ§Ã£o
            "timer_obs": 0.0,       # Contador decrescente da janela de observaÃ§Ã£o
        }
        
        # Momentum e pressÃ£o
        self.momentum = 0.0  # -1 (perdendo) a 1 (ganhando)
        self.pressao_aplicada = 0.0  # Quanto estÃ¡ pressionando
        self.pressao_recebida = 0.0  # Quanto estÃ¡ sendo pressionado
        
        # HesitaÃ§Ã£o e impulso humano
        self.hesitacao = 0.0  # Probabilidade de hesitar
        self.impulso = 0.0    # Probabilidade de agir impulsivamente
        self.congelamento = 0.0  # "Freeze" sob pressÃ£o
        self.memoria_adaptativa = {
            "vies_skill": 0.0,
            "vies_agressao": 0.0,
            "vies_cautela": 0.0,
            "vies_pressao": 0.0,
            "vies_contra_ataque": 0.0,
            "ultimo_evento": None,
        }
        
        # Timing humano
        self.tempo_reacao_base = random.uniform(0.12, 0.25)  # Varia por personalidade
        self.variacao_timing = random.uniform(0.05, 0.15)    # InconsistÃªncia humana
        self.micro_ajustes = 0  # Pequenos ajustes de posiÃ§Ã£o
        # BUG-AI-03 fix: atributo faltante â€” usado em trigger "bloqueio_sucesso" dos instintos
        self.ultimo_bloqueio = 999.0  # Segundos desde o Ãºltimo bloqueio bem-sucedido
        # BUG-AI-02 fix: variÃ¡veis para detecÃ§Ã£o de whiff (ataque que errou)
        self._inimigo_estava_atacando = False
        self._hits_recebidos_antes_ataque_ini = 0
        # BUG-C2 fix: alvo atual â€” usado por _score_alvo para priorizar inimigos
        # que estÃ£o atacando aliados e pelo SUPPORT em _score_alvo.
        self._alvo_atual = None
        
        # Sistema de combos e follow-ups
        self.combo_state = {
            "em_combo": False,
            "hits_combo": 0,
            "ultimo_tipo_ataque": None,
            "pode_followup": False,
            "timer_followup": 0.0,
            "followup_forcado": None,
            "origem_followup": None,
        }
        
        # RespiraÃ§Ã£o e ritmo
        self.ritmo_combate = random.uniform(0.8, 1.2)  # Personalidade do ritmo
        self.burst_counter = 0  # Conta explosÃµes de aÃ§Ã£o
        self.descanso_timer = 0.0  # Micro-pausas naturais
        
        # HistÃ³rico de aÃ§Ãµes para nÃ£o repetir muito
        self.historico_acoes = []
        self.repeticao_contador = {}

    def _initialize_spatial_and_weapon_awareness_state(self) -> None:
        # === SISTEMA DE RECONHECIMENTO ESPACIAL v9.0 ===
        # Awareness de paredes e obstÃ¡culos
        self.consciencia_espacial = {
            "parede_proxima": None,  # None, "norte", "sul", "leste", "oeste"
            "distancia_parede": 999.0,
            "distancia_centro": 0.0,
            "obstaculo_proxima": None,  # ObstÃ¡culo mais prÃ³ximo
            "distancia_obstaculo": 999.0,
            "zona_perigo_atual": None,
            "zona_perigo_inimigo": None,
            "zona_perigo_proxima": None,
            "distancia_zona_perigo": 999.0,
            "encurralado": False,
            "oponente_contra_parede": False,
            "oponente_perto_obstaculo": False,
            "inimigo_vulneravel_zona": False,
            "distancia_parede_inimigo": 999.0,
            "dominando_centro": False,
            "pressao_borda": 0.0,
            "caminho_livre": {"frente": True, "tras": True, "esquerda": True, "direita": True},
            "posicao_tatica": "centro",  # "centro", "perto_parede", "encurralado", "vantagem"
        }
        
        # Uso tÃ¡tico de obstÃ¡culos
        self.tatica_espacial = {
            "usando_cobertura": False,
            "tipo_cobertura": None,  # "pilar", "obstaculo", "parede"
            "forcar_canto": False,  # Tentando encurralar oponente
            "retomar_centro": False,  # Sair da borda e recuperar controle espacial
            "escapar_zona_perigo": False,  # Sair de lava/fogo/zonas letais
            "pressionar_em_zona": False,  # Explorar inimigo preso em zona ruim
            "recuar_para_obstaculo": False,  # Recuando de costas pra obstÃ¡culo (perigoso)
            "flanquear_obstaculo": False,  # Usando obstÃ¡culo pra flanquear
            "last_check_time": 0.0,  # OtimizaÃ§Ã£o - nÃ£o checa todo frame
        }
        
        # === SISTEMA DE PERCEPÃ‡ÃƒO DE ARMAS v10.0 ===
        self.percepcao_arma = {
            # AnÃ¡lise da minha arma
            "minha_arma_perfil": None,          # WeaponProfile da minha arma
            "meu_alcance_efetivo": 2.0,         # Alcance real da minha arma
            "minha_velocidade_ataque": 0.5,    # Velocidade de ataque
            "meu_arco_cobertura": 90.0,         # Arco que minha arma cobre
            
            # AnÃ¡lise da arma inimiga
            "arma_inimigo_tipo": None,          # Tipo da arma do inimigo
            "arma_inimigo_perfil": None,        # WeaponProfile da arma inimiga
            "alcance_inimigo": 2.0,             # Alcance do inimigo
            "zona_perigo_inimigo": 2.5,         # DistÃ¢ncia perigosa
            "ponto_cego_inimigo": None,         # Ã‚ngulo do ponto cego
            "velocidade_inimigo": 0.5,          # Velocidade de ataque
            
            # AnÃ¡lise de matchup
            "vantagem_alcance": 0.0,            # >0 = meu alcance maior
            "vantagem_velocidade": 0.0,         # >0 = sou mais rÃ¡pido
            "vantagem_cobertura": 0.0,          # >0 = cubro mais Ã¡rea
            "matchup_favoravel": 0.0,           # -1 a 1, geral
            
            # Estado tÃ¡tico baseado em armas
            "distancia_segura": 3.0,            # DistÃ¢ncia segura contra inimigo
            "distancia_ataque": 1.5,            # DistÃ¢ncia ideal para atacar
            "estrategia_recomendada": "neutro", # "aproximar", "afastar", "flanquear", "trocar"
            
            # Timing
            "last_analysis_time": 0.0,          # Quando Ãºltima anÃ¡lise foi feita
            "enemy_weapon_changed": False,      # Se arma do inimigo mudou
        }

    def _initialize_multi_combat_state(self) -> None:
        # === SISTEMA MULTI-COMBATENTE v13.0 ===
        self.multi_awareness = {
            "inimigos": [],           # Lista de {lutador, distancia, angulo, ameaca}
            "aliados": [],            # Lista de {lutador, distancia, angulo, vida_pct}
            "num_inimigos_vivos": 1,
            "num_aliados_vivos": 0,
            "ameaca_flanqueio": 0.0,  # 0-1, quÃ£o cercado estÃ¡
            "concentracao_inimiga": 0.0,  # QuÃ£o agrupados estÃ£o os inimigos
            "aliado_perto_alvo": False,    # Aliado estÃ¡ perto do meu alvo?
            "aliado_no_caminho": False,    # Aliado entre mim e o alvo? (friendly fire!)
            "melhor_alvo": None,           # Inimigo mais estratÃ©gico (nÃ£o necessariamente o mais perto)
            "posicao_segura_aliados": None, # DireÃ§Ã£o para evitar friendly fire
            "em_desvantagem_numerica": False,
            "modo_multialvo": False,   # Se hÃ¡ mais de 1 inimigo
        }
        
        # v13.0 TEAM ORDERS â€” preenchido pelo TeamCoordinator
        self.team_orders = {
            "role": "STRIKER",
            "tactic": "FOCUS_FIRE",
            "primary_target_id": 0,
            "em_desvantagem": False,
            "team_hp_pct": 1.0,
            "alive_count": 1,
            "enemy_alive_count": 1,
            "is_carry": False,
            "is_weakest": False,
            "team_center": (0.0, 0.0),
            "team_spread": 0.0,
            "synergies": [],
            "callouts": [],
            "ally_intents": {},
        }

    def _initialize_update_group_timers(self) -> None:
        # A02: throttle timers por grupo de custo
        # Grupo TÃTICO  (10hz): leitura de oponente, janelas, momentum, estados, combo
        # Grupo EMOCIONAL (4hz): emoÃ§Ãµes, humor, modos especiais, baiting
        # Grupo ESTRATÃ‰GICO (2hz): ritmo, multi-awareness, team orders
        self._t_tatico      = 0.0
        self._t_emocional   = 0.0
        self._t_estrategico = 0.0
        # Intervalos (segundos)
        self._I_TATICO      = 0.10   # 10hz
        self._I_EMOCIONAL   = 0.25   # 4hz
        self._I_ESTRATEGICO = 0.50   # 2hz


    # =========================================================================
    # PROCESSAMENTO PRINCIPAL v13.0 MULTI-FIGHTER EDITION
    # =========================================================================

    def _modificadores_personalidade_adaptativa(self):
        """Retorna como a personalidade altera o aprendizado tatico recente."""
        aprendizado = 1.0
        decaimento = 1.0
        risco_base = 0.0

        tracos = set(self.tracos)
        if "CALCULISTA" in tracos:
            aprendizado *= 1.12
            decaimento *= 0.72
        if "PACIENTE" in tracos:
            aprendizado *= 1.05
            decaimento *= 0.80
        if "ADAPTAVEL" in tracos:
            aprendizado *= 1.18
        if "ERRATICO" in tracos or "CAOTICO" in tracos:
            aprendizado *= 0.88
            decaimento *= 1.45
        if "BERSERKER" in tracos or "FURIOSO" in tracos:
            risco_base += 0.18
        if "IMPRUDENTE" in tracos:
            risco_base += 0.12
        if "PRUDENTE" in tracos or "COVARDE" in tracos:
            risco_base -= 0.18
        if "FRIO" in tracos:
            risco_base -= 0.05

        return aprendizado, decaimento, risco_base

    def _registrar_aprendizado_tatico(self, campo, delta, evento=None):
        """Memoria curta de combate usada para adaptar risco e prioridade."""
        memoria = getattr(self, "memoria_adaptativa", None)
        if not isinstance(memoria, dict) or campo not in memoria:
            return

        aprendizado, _, _ = self._modificadores_personalidade_adaptativa()
        valor = memoria.get(campo, 0.0) + (delta * aprendizado)

        tracos = set(self.tracos)
        if campo == "vies_agressao" and ("BERSERKER" in tracos or "FURIOSO" in tracos):
            valor += max(0.0, delta) * 0.08
        elif campo == "vies_cautela" and ("PRUDENTE" in tracos or "COVARDE" in tracos):
            valor += max(0.0, delta) * 0.08
        elif campo == "vies_skill" and "CALCULISTA" in tracos and delta > 0:
            valor += delta * 0.05

        memoria[campo] = max(-1.0, min(1.0, valor))
        if evento:
            memoria["ultimo_evento"] = evento

    def _decair_memoria_adaptativa(self, dt):
        memoria = getattr(self, "memoria_adaptativa", None)
        if not isinstance(memoria, dict):
            return

        _, decaimento, _ = self._modificadores_personalidade_adaptativa()
        taxa_base = max(0.02, dt * 0.34 * decaimento)
        for chave, valor in list(memoria.items()):
            if chave == "ultimo_evento":
                continue
            if abs(valor) <= taxa_base:
                memoria[chave] = 0.0
            elif valor > 0:
                memoria[chave] = valor - taxa_base
            else:
                memoria[chave] = valor + taxa_base

        if all(abs(memoria.get(chave, 0.0)) < 0.05 for chave in (
            "vies_skill", "vies_agressao", "vies_cautela", "vies_pressao", "vies_contra_ataque"
        )):
            memoria["ultimo_evento"] = None

    def _calcular_vies_skill_adaptativo(self):
        memoria = getattr(self, "memoria_adaptativa", {})
        return (
            memoria.get("vies_skill", 0.0) * 0.90
            + memoria.get("vies_cautela", 0.0) * 0.18
            - memoria.get("vies_agressao", 0.0) * 0.22
            - memoria.get("vies_pressao", 0.0) * 0.10
        )

    def _ativar_memoria_cena(self, tipo, intensidade=0.5, duracao=2.0):
        memoria = getattr(self, "memoria_cena", None)
        if not isinstance(memoria, dict):
            return
        intensidade = max(0.0, min(1.0, intensidade))
        duracao = max(0.0, duracao)
        atual_tipo = memoria.get("tipo")
        atual_intensidade = memoria.get("intensidade", 0.0)
        atual_duracao = memoria.get("duracao", 0.0)

        if atual_tipo == tipo:
            memoria["intensidade"] = max(atual_intensidade, intensidade)
            memoria["duracao"] = max(atual_duracao, duracao)
            return

        prioridade = {
            "clash": 5,
            "final_showdown": 5,
            "virada": 4,
            "sequencia_perfeita": 4,
            "leitura_perfeita": 3,
            "dominando": 3,
            "humilhado": 3,
            "quase_morte": 4,
        }
        atual_prioridade = prioridade.get(atual_tipo, 0)
        nova_prioridade = prioridade.get(tipo, 0)
        if atual_duracao > 0.2 and atual_intensidade > intensidade and atual_prioridade > nova_prioridade:
            return

        memoria["tipo"] = tipo
        memoria["intensidade"] = intensidade
        memoria["duracao"] = duracao

    def _decair_memoria_cena(self, dt):
        memoria = getattr(self, "memoria_cena", None)
        if not isinstance(memoria, dict):
            return
        duracao = max(0.0, memoria.get("duracao", 0.0) - dt)
        memoria["duracao"] = duracao
        if duracao <= 0.0:
            memoria["tipo"] = None
            memoria["intensidade"] = 0.0
            return
        intensidade = max(0.0, memoria.get("intensidade", 0.0) - dt * 0.18)
        memoria["intensidade"] = intensidade
        if intensidade <= 0.01:
            memoria["tipo"] = None
            memoria["duracao"] = 0.0

    def _garantir_memoria_curta_oponente(self, oponente):
        if oponente is None:
            return None
        memoria = getattr(self, "memoria_oponente", None)
        if not isinstance(memoria, dict):
            return None
        buckets = memoria.setdefault("adaptacao_por_oponente", {})
        chave = self._id_oponente(oponente) if hasattr(self, "_id_oponente") else str(id(oponente))
        memoria["id_atual"] = chave
        bucket = buckets.get(chave)
        if bucket is None:
            bucket = {
                "vies_skill": 0.0,
                "vies_agressao": 0.0,
                "vies_cautela": 0.0,
                "vies_pressao": 0.0,
                "vies_contra_ataque": 0.0,
                "relacao_respeito": 0.0,
                "relacao_vinganca": 0.0,
                "relacao_obsessao": 0.0,
                "relacao_caca": 0.0,
                "relacao_dominante": None,
                "ultimo_evento": None,
            }
            buckets[chave] = bucket
        return bucket

    def _registrar_aprendizado_oponente(self, oponente, campo, delta, evento=None):
        bucket = self._garantir_memoria_curta_oponente(oponente)
        if bucket is None or campo not in bucket:
            return
        aprendizado, _, _ = self._modificadores_personalidade_adaptativa()
        bucket[campo] = max(-1.0, min(1.0, bucket.get(campo, 0.0) + (delta * aprendizado)))
        if evento:
            bucket["ultimo_evento"] = evento
        self._atualizar_relacao_dominante_bucket(bucket)

    def _atualizar_relacao_dominante_bucket(self, bucket):
        if not isinstance(bucket, dict):
            return None
        candidatos = {
            "respeito": max(0.0, bucket.get("relacao_respeito", 0.0)),
            "vinganca": max(0.0, bucket.get("relacao_vinganca", 0.0)),
            "obsessao": max(0.0, bucket.get("relacao_obsessao", 0.0)),
            "caca": max(0.0, bucket.get("relacao_caca", 0.0)),
        }
        dominante, valor = max(candidatos.items(), key=lambda item: item[1])
        bucket["relacao_dominante"] = dominante if valor >= 0.16 else None
        return bucket["relacao_dominante"]

    def _registrar_relacao_oponente(self, oponente, campo, delta, evento=None):
        bucket = self._garantir_memoria_curta_oponente(oponente)
        if bucket is None:
            return
        chave = f"relacao_{campo}"
        if chave not in bucket:
            return

        aprendizado, decaimento, _ = self._modificadores_personalidade_adaptativa()
        mult = 1.0
        if campo == "vinganca" and ("VINGATIVO" in self.tracos or "TEIMOSO" in self.tracos):
            mult = 1.25
        elif campo == "respeito" and ("CALCULISTA" in self.tracos or "FRIO" in self.tracos):
            mult = 1.18
        elif campo == "obsessao" and ("PREDADOR" in self.tracos or "PERSEGUIDOR" in self.tracos):
            mult = 1.20
        elif campo == "caca" and ("AGRESSIVO" in self.tracos or "BERSERKER" in self.tracos):
            mult = 1.18

        valor = bucket.get(chave, 0.0) + delta * aprendizado * mult
        if delta < 0:
            valor *= max(0.82, 1.0 - decaimento * 0.04)
        bucket[chave] = max(0.0, min(1.0, valor))
        if evento:
            bucket["ultimo_evento"] = evento
        self._atualizar_relacao_dominante_bucket(bucket)

    def _decair_memoria_curta_oponentes(self, dt):
        memoria, buckets = self._obter_buckets_memoria_curta_oponentes()
        if buckets is None:
            return
        taxa_base = self._calcular_taxa_decaimento_memoria_curta(dt)
        remover = []
        for chave, bucket in buckets.items():
            if not self._bucket_memoria_curta_eh_valido(bucket):
                remover.append(chave)
                continue
            self._decair_bucket_memoria_curta_oponente(bucket, taxa_base)
            self._atualizar_resumo_bucket_memoria_curta_oponente(bucket)
            if self._bucket_memoria_curta_deve_limpar_evento(bucket):
                bucket["ultimo_evento"] = None
            if self._bucket_memoria_curta_esta_inerte(bucket) and memoria.get("id_atual") != chave:
                remover.append(chave)
        for chave in remover:
            buckets.pop(chave, None)

    def _obter_buckets_memoria_curta_oponentes(self):
        memoria = getattr(self, "memoria_oponente", None)
        if not isinstance(memoria, dict):
            return None, None
        buckets = memoria.get("adaptacao_por_oponente", {})
        if not isinstance(buckets, dict):
            return memoria, None
        return memoria, buckets

    def _calcular_taxa_decaimento_memoria_curta(self, dt):
        _, decaimento, _ = self._modificadores_personalidade_adaptativa()
        return max(0.02, dt * 0.28 * decaimento)

    def _bucket_memoria_curta_eh_valido(self, bucket) -> bool:
        return isinstance(bucket, dict)

    def _decair_bucket_memoria_curta_oponente(self, bucket, taxa_base) -> None:
        for campo, valor in list(bucket.items()):
            if campo == "ultimo_evento":
                continue
            if campo == "padroes":
                self._decair_padroes_bucket_memoria_curta(valor, bucket, taxa_base)
                continue
            self._decair_campo_bucket_memoria_curta(bucket, campo, valor, taxa_base)

    def _decair_padroes_bucket_memoria_curta(self, valor, bucket, taxa_base) -> None:
        if not isinstance(valor, dict):
            bucket["padroes"] = {}
            return
        remover_padroes = []
        for nome_padrao, score_padrao in list(valor.items()):
            if not isinstance(score_padrao, (int, float)):
                remover_padroes.append(nome_padrao)
                continue
            if abs(score_padrao) <= taxa_base:
                remover_padroes.append(nome_padrao)
            elif score_padrao > 0:
                valor[nome_padrao] = score_padrao - taxa_base
            else:
                valor[nome_padrao] = score_padrao + taxa_base
        for nome_padrao in remover_padroes:
            valor.pop(nome_padrao, None)

    def _decair_campo_bucket_memoria_curta(self, bucket, campo, valor, taxa_base) -> None:
        if not isinstance(valor, (int, float)):
            return
        taxa_campo = taxa_base * 0.45 if campo.startswith("relacao_") else taxa_base
        if abs(valor) <= taxa_campo:
            bucket[campo] = 0.0
        elif valor > 0:
            bucket[campo] = valor - taxa_campo
        else:
            bucket[campo] = valor + taxa_campo

    def _atualizar_resumo_bucket_memoria_curta_oponente(self, bucket) -> None:
        padroes_bucket = bucket.get("padroes", {})
        if isinstance(padroes_bucket, dict) and padroes_bucket:
            bucket["padrao_dominante"] = max(padroes_bucket.items(), key=lambda item: item[1])[0]
        else:
            bucket["padrao_dominante"] = None
        self._atualizar_relacao_dominante_bucket(bucket)

    def _bucket_memoria_curta_deve_limpar_evento(self, bucket) -> bool:
        return all(abs(bucket.get(campo, 0.0)) < 0.04 for campo in (
            "vies_skill", "vies_agressao", "vies_cautela", "vies_pressao", "vies_contra_ataque"
        )) and all(bucket.get(campo, 0.0) < 0.05 for campo in (
            "relacao_respeito", "relacao_vinganca", "relacao_obsessao", "relacao_caca"
        ))

    def _bucket_memoria_curta_esta_inerte(self, bucket) -> bool:
        return all(abs(bucket.get(campo, 0.0)) < 0.01 for campo in (
            "vies_skill", "vies_agressao", "vies_cautela", "vies_pressao", "vies_contra_ataque"
        )) and all(bucket.get(campo, 0.0) < 0.03 for campo in (
            "relacao_respeito", "relacao_vinganca", "relacao_obsessao", "relacao_caca"
        )) and not bucket.get("padroes")

    def _obter_vies_oponente(self, oponente=None):
        memoria = getattr(self, "memoria_oponente", {})
        if not isinstance(memoria, dict):
            return {}
        if oponente is not None:
            chave = self._id_oponente(oponente) if hasattr(self, "_id_oponente") else str(id(oponente))
        else:
            chave = memoria.get("id_atual")
        buckets = memoria.get("adaptacao_por_oponente", {})
        if not chave or not isinstance(buckets, dict):
            return {}
        return buckets.get(chave, {})

    def _obter_relacao_oponente(self, oponente=None):
        bucket = self._obter_vies_oponente(oponente)
        if not isinstance(bucket, dict):
            return {}
        return {
            "respeito": max(0.0, bucket.get("relacao_respeito", 0.0)),
            "vinganca": max(0.0, bucket.get("relacao_vinganca", 0.0)),
            "obsessao": max(0.0, bucket.get("relacao_obsessao", 0.0)),
            "caca": max(0.0, bucket.get("relacao_caca", 0.0)),
            "dominante": bucket.get("relacao_dominante"),
        }

    def _calcular_pressao_rivalidade(self, oponente=None):
        relacao = self._obter_relacao_oponente(oponente)
        if not relacao:
            return {"dominante": None, "intensidade": 0.0, "perfil": "neutro"}
        dominante, intensidade = self._resolver_dominante_e_intensidade_rivalidade(relacao)
        perfil = self._mapear_perfil_rivalidade(dominante)

        return {
            "dominante": dominante,
            "intensidade": max(0.0, min(1.0, intensidade)),
            "perfil": perfil,
            "respeito": relacao.get("respeito", 0.0),
            "vinganca": relacao.get("vinganca", 0.0),
            "obsessao": relacao.get("obsessao", 0.0),
            "caca": relacao.get("caca", 0.0),
        }

    def _resolver_dominante_e_intensidade_rivalidade(self, relacao):
        dominante = relacao.get("dominante")
        intensidade = max(
            relacao.get("respeito", 0.0),
            relacao.get("vinganca", 0.0),
            relacao.get("obsessao", 0.0),
            relacao.get("caca", 0.0),
        )
        if intensidade < 0.16:
            dominante = None
        return dominante, intensidade

    def _mapear_perfil_rivalidade(self, dominante):
        perfis = {
            "respeito": "duelo",
            "vinganca": "revanche",
            "obsessao": "rival",
            "caca": "predacao",
        }
        return perfis.get(dominante, "neutro")

    def _calcular_postura_risco_adaptativa(self, distancia, inimigo=None):
        memoria = getattr(self, "memoria_adaptativa", {})
        memoria_oponente = self._obter_vies_oponente(inimigo)
        _, _, risco_base = self._modificadores_personalidade_adaptativa()

        score = (
            memoria.get("vies_agressao", 0.0) * 0.58
            + memoria.get("vies_pressao", 0.0) * 0.42
            + memoria.get("vies_contra_ataque", 0.0) * 0.28
            - memoria.get("vies_cautela", 0.0) * 0.72
        )
        score += memoria_oponente.get("vies_agressao", 0.0) * 0.34
        score += memoria_oponente.get("vies_pressao", 0.0) * 0.20
        score += memoria_oponente.get("vies_contra_ataque", 0.0) * 0.14
        score -= memoria_oponente.get("vies_cautela", 0.0) * 0.42
        relacao = self._obter_relacao_oponente(inimigo)
        score += relacao.get("vinganca", 0.0) * 0.28
        score += relacao.get("caca", 0.0) * 0.20
        score += relacao.get("obsessao", 0.0) * 0.16
        score -= relacao.get("respeito", 0.0) * 0.18
        score += self.momentum * 0.16
        score += (self.confianca - self.medo) * 0.12
        score += risco_base

        hp_pct = self.parent.vida / max(self.parent.vida_max, 1)
        if hp_pct < 0.28:
            score -= 0.18
        elif hp_pct > 0.72:
            score += 0.06

        if inimigo is not None and inimigo.vida / max(inimigo.vida_max, 1) < 0.24:
            score += 0.08

        alcance_ideal = max(0.8, getattr(self.parent, "alcance_ideal", 2.5))
        if distancia < alcance_ideal * 0.55:
            score -= max(0.0, memoria.get("vies_cautela", 0.0)) * 0.18

        return max(-1.0, min(1.0, score))

    def _preferir_skills_neste_frame(self, distancia, inimigo):
        """Arbitra se skills devem ter prioridade sobre ataque básico neste frame."""
        contexto = self._coletar_contexto_preferencia_skills(distancia, inimigo)
        prefer_skills = self._resolver_baseline_preferencia_skills(contexto)
        prefer_skills = self._aplicar_familia_preferencia_skills(contexto, prefer_skills)
        prefer_skills = self._aplicar_tatica_time_preferencia_skills(contexto, prefer_skills)
        prefer_skills = self._aplicar_janelas_e_pacotes_preferencia_skills(contexto, prefer_skills)
        prefer_skills = self._aplicar_adaptacao_preferencia_skills(contexto, prefer_skills)
        return prefer_skills

    def _coletar_contexto_preferencia_skills(self, distancia, inimigo):
        p = self.parent
        arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        familia = resolver_familia_arma(arma)
        perfil_composto = getattr(self, "arquetipo_composto", None)
        pacote_id = ""
        if isinstance(perfil_composto, dict):
            pacote_ref = perfil_composto.get("pacote_referencia") or {}
            if isinstance(pacote_ref, dict):
                pacote_id = str(pacote_ref.get("id", "") or "").strip().lower()
        mana_pct = p.mana / max(getattr(p, 'mana_max', 1.0), 1.0)
        team_role = self.team_orders.get("role", "STRIKER")
        team_tactic = self.team_orders.get("tactic", "FOCUS_FIRE")
        hp_pct = p.vida / max(p.vida_max, 1)
        alcance_ideal = max(0.8, getattr(p, 'alcance_ideal', 2.5))
        vies_skill_adaptativo = self._calcular_vies_skill_adaptativo()
        vies_oponente = self._obter_vies_oponente(inimigo)
        vies_skill_adaptativo += (
            vies_oponente.get("vies_skill", 0.0) * 0.42
            + vies_oponente.get("vies_cautela", 0.0) * 0.10
            - vies_oponente.get("vies_agressao", 0.0) * 0.12
        )
        postura_risco = self._calcular_postura_risco_adaptativa(distancia, inimigo)
        return {
            "parent": p,
            "arma": arma,
            "familia": familia,
            "pacote_id": pacote_id,
            "mana_pct": mana_pct,
            "team_role": team_role,
            "team_tactic": team_tactic,
            "hp_pct": hp_pct,
            "alcance_ideal": alcance_ideal,
            "vies_skill_adaptativo": vies_skill_adaptativo,
            "postura_risco": postura_risco,
            "distancia": distancia,
            "inimigo": inimigo,
        }

    def _resolver_baseline_preferencia_skills(self, contexto) -> bool:
        prefer_skills = False
        if self.skill_strategy is not None:
            role = self.skill_strategy.role_principal.value
            if role in ["artillery", "burst_mage", "control_mage", "summoner", "buffer", "channeler"]:
                prefer_skills = True

        if contexto["team_role"] in {"ARTILLERY", "CONTROLLER", "SUPPORT"}:
            prefer_skills = True

        if contexto["mana_pct"] < 0.16 and contexto["team_role"] not in {"SUPPORT", "CONTROLLER"}:
            prefer_skills = False
        return prefer_skills

    def _aplicar_familia_preferencia_skills(self, contexto, prefer_skills: bool) -> bool:
        familia = contexto["familia"]
        if familia == "foco":
            return self._resolver_preferencia_skills_foco(contexto, prefer_skills)
        if familia == "orbital":
            return self._resolver_preferencia_skills_orbital(contexto, prefer_skills)
        if familia == "hibrida":
            return self._resolver_preferencia_skills_hibrida(contexto, prefer_skills)
        if familia == "corrente":
            return self._resolver_preferencia_skills_corrente(contexto, prefer_skills)
        return prefer_skills

    def _resolver_preferencia_skills_foco(self, contexto, prefer_skills: bool) -> bool:
        p = contexto["parent"]
        distancia = contexto["distancia"]
        alcance_ideal = contexto["alcance_ideal"]
        orbes_orbitando = len([
            o for o in getattr(p, 'buffer_orbes', [])
            if getattr(o, 'ativo', False) and getattr(o, 'estado', '') == "orbitando"
        ])
        if "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos or "PRUDENTE" in self.tracos:
            prefer_skills = True
        if orbes_orbitando >= 2:
            prefer_skills = True
        if distancia < max(2.1, alcance_ideal * 0.62) and ("BERSERKER" in self.tracos or "FURIOSO" in self.tracos):
            prefer_skills = False
        return prefer_skills

    def _resolver_preferencia_skills_orbital(self, contexto, prefer_skills: bool) -> bool:
        p = contexto["parent"]
        distancia = contexto["distancia"]
        alcance_ideal = contexto["alcance_ideal"]
        pacote_id = contexto["pacote_id"]
        mana_pct = contexto["mana_pct"]
        burst_pronto = getattr(p, 'orbital_burst_cd', 999.0) <= 0.0
        if burst_pronto and distancia <= max(3.2, alcance_ideal * 1.12):
            prefer_skills = False
        elif "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos:
            prefer_skills = True
        if pacote_id == "bastiao_prismatico":
            if mana_pct < 0.44 or burst_pronto:
                prefer_skills = False
        elif pacote_id == "artilheiro_de_orbita":
            if distancia < max(2.9, alcance_ideal * 0.78) or mana_pct < 0.28:
                prefer_skills = False
            else:
                prefer_skills = True
        return prefer_skills

    def _resolver_preferencia_skills_hibrida(self, contexto, prefer_skills: bool) -> bool:
        p = contexto["parent"]
        arma = contexto["arma"]
        distancia = contexto["distancia"]
        alcance_ideal = contexto["alcance_ideal"]
        forma_atual = int(getattr(p, 'transform_forma', getattr(arma, 'forma_atual', 0)) or 0)
        bonus_troca = getattr(p, 'transform_bonus_timer', 0.0) > 0.0
        if forma_atual == 1 and distancia > max(2.2, alcance_ideal * 0.92):
            prefer_skills = True
        elif forma_atual == 0 and distancia <= max(2.0, alcance_ideal * 0.95):
            prefer_skills = False
        if bonus_troca and ("BERSERKER" in self.tracos or "IMPRUDENTE" in self.tracos):
            prefer_skills = False
        elif "CALCULISTA" in self.tracos or "ADAPTAVEL" in self.tracos:
            prefer_skills = True
        return prefer_skills

    def _resolver_preferencia_skills_corrente(self, contexto, prefer_skills: bool) -> bool:
        p = contexto["parent"]
        arma = contexto["arma"]
        distancia = contexto["distancia"]
        metricas = obter_metricas_arma(arma, p)
        alcance_max = metricas["alcance_max"]
        alcance_min = metricas["alcance_min"]
        centro_sweet_spot = max(alcance_min + 0.4, (alcance_max + alcance_min) / 2.0)
        em_sweet_spot = abs(distancia - centro_sweet_spot) <= max(0.55, alcance_max * 0.20)
        if em_sweet_spot:
            prefer_skills = False
        elif "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos:
            prefer_skills = True
        return prefer_skills

    def _aplicar_tatica_time_preferencia_skills(self, contexto, prefer_skills: bool) -> bool:
        team_tactic = contexto["team_tactic"]
        familia = contexto["familia"]
        hp_pct = contexto["hp_pct"]
        mana_pct = contexto["mana_pct"]
        distancia = contexto["distancia"]
        alcance_ideal = contexto["alcance_ideal"]
        pacote_id = contexto["pacote_id"]
        if team_tactic == "FULL_AGGRO" and familia in {"corrente", "orbital", "hibrida"} and hp_pct > 0.35:
            prefer_skills = False
        elif team_tactic == "KITE_AND_POKE" and familia in {"foco", "disparo", "arremesso"}:
            prefer_skills = True
        elif pacote_id == "artilheiro_de_orbita" and team_tactic == "KITE_AND_POKE":
            prefer_skills = mana_pct > 0.24 and distancia >= max(2.9, alcance_ideal * 0.76)
        return prefer_skills

    def _aplicar_janelas_e_pacotes_preferencia_skills(self, contexto, prefer_skills: bool) -> bool:
        familia = contexto["familia"]
        pacote_id = contexto["pacote_id"]
        team_role = contexto["team_role"]
        hp_pct = contexto["hp_pct"]
        distancia = contexto["distancia"]
        alcance_ideal = contexto["alcance_ideal"]
        if self.janela_ataque.get("aberta", False) and self.janela_ataque.get("qualidade", 0.0) > 0.75:
            if familia in {"corrente", "orbital", "hibrida"}:
                prefer_skills = False
        if (
            pacote_id == "vanguarda_brutal"
            and team_role in {"VANGUARD", "STRIKER"}
            and self.team_orders.get("alive_count", 1) > 1
            and familia in {"lamina", "corrente", "haste"}
        ):
            if distancia <= max(2.8, alcance_ideal * 1.02) or hp_pct > 0.45:
                prefer_skills = False
        return prefer_skills

    def _aplicar_adaptacao_preferencia_skills(self, contexto, prefer_skills: bool) -> bool:
        vies_skill_adaptativo = contexto["vies_skill_adaptativo"]
        postura_risco = contexto["postura_risco"]
        familia = contexto["familia"]
        hp_pct = contexto["hp_pct"]
        if vies_skill_adaptativo > 0.18:
            prefer_skills = True
        elif vies_skill_adaptativo < -0.20 and familia in {"lamina", "dupla", "corrente", "orbital", "hibrida"}:
            prefer_skills = False

        if postura_risco > 0.42 and familia in {"lamina", "dupla", "corrente", "orbital", "hibrida"} and hp_pct > 0.30:
            prefer_skills = False
        elif postura_risco < -0.24 and familia in {"foco", "disparo", "orbital"}:
            prefer_skills = True
        return prefer_skills
    
    def processar(self, dt, distancia, inimigo, todos_lutadores=None):
        """Processa decisÃµes da IA a cada frame com comportamento humano.
        
        Args:
            dt: Delta time
            distancia: DistÃ¢ncia ao inimigo principal
            inimigo: Inimigo principal (mais prÃ³ximo)
            todos_lutadores: Lista de TODOS os lutadores (None = modo 1v1 legado)
        """
        self._prepare_processar_frame(dt, distancia, inimigo)
        self._prepare_processar_random_and_debug(distancia)
        self._update_processar_team_and_awareness(dt, distancia, inimigo, todos_lutadores)
        self._update_processar_runtime_groups(dt, distancia, inimigo)
        if self._run_processar_interruptions(dt, distancia, inimigo):
            return
        if self._resolve_processar_combat_priority(dt, distancia, inimigo):
            return
        self._finalize_processar_frame(dt, distancia, inimigo)

    def _prepare_processar_frame(self, dt, distancia, inimigo) -> None:
        self.tempo_combate += dt
        self._tempo_sem_decisao += dt
        self._alvo_atual = inimigo
        self._garantir_memoria_curta_oponente(inimigo)
        self._try_break_processar_indecision(distancia, inimigo)

    def _try_break_processar_indecision(self, distancia, inimigo) -> None:
        p = self.parent
        if (
            self._tempo_sem_decisao > 0.9
            and not p.atacando
            and self.acao_atual in {"NEUTRO", "BLOQUEAR", "CIRCULAR", "COMBATE", "RECUAR", "FUGIR"}
        ):
            self._decidir_movimento(distancia, inimigo)
            self._calcular_timer_decisao()
            self._registrar_acao()
            self._tempo_sem_decisao = 0.0

    def _prepare_processar_random_and_debug(self, distancia) -> None:
        self._rand_pool = [random.random() for _ in range(AI_RAND_POOL_SIZE)]
        self._rand_idx = 0
        self._emit_processar_debug_snapshot(distancia)

    def _emit_processar_debug_snapshot(self, distancia) -> None:
        p = self.parent
        if not DEBUG_AI:
            return
        _nome = p.dados.nome if hasattr(p, 'dados') and hasattr(p.dados, 'nome') else '?'
        if DEBUG_AI_FIGHTER is not None and _nome != DEBUG_AI_FIGHTER:
            return
        _ultima_skill = getattr(self, '_ultima_skill_usada', 'none')
        _log.debug(
            "[AI:%s] dist=%.1f | acao=%-18s | skill=%-20s | humor=%-12s | "
            "hp=%3.0f%% | mana=%3.0f%% | momentum=%+.2f | raiva=%.2f | medo=%.2f",
            _nome, distancia, self.acao_atual,
            _ultima_skill, getattr(self, 'humor', '?'),
            p.vida / max(p.vida_max, 1) * 100,
            p.mana / max(p.mana_max, 1) * 100,
            getattr(self, 'momentum', 0.0),
            getattr(self, 'raiva', 0.0),
            getattr(self, 'medo', 0.0),
        )

    def _update_processar_team_and_awareness(self, dt, distancia, inimigo, todos_lutadores) -> None:
        if todos_lutadores is not None:
            self._atualizar_multi_awareness(dt, inimigo, todos_lutadores)
        self._aplicar_team_orders(dt, distancia, inimigo, todos_lutadores)

    def _update_processar_runtime_groups(self, dt, distancia, inimigo) -> None:
        self._atualizar_cooldowns(dt)
        self._detectar_dano()
        self._run_processar_emotional_group(dt, distancia, inimigo)
        self._run_processar_tactical_group(dt, distancia, inimigo)
        self._run_processar_strategic_group(dt)
        self._atualizar_consciencia_espacial(dt, distancia, inimigo)
        self._atualizar_percepcao_armas(dt, distancia, inimigo)

    def _run_processar_emotional_group(self, dt, distancia, inimigo) -> None:
        self._t_emocional += dt
        if self._t_emocional < self._I_EMOCIONAL:
            return
        self._t_emocional = 0.0
        self._atualizar_emocoes(dt, distancia, inimigo)
        self._atualizar_humor(dt)
        self._processar_modos_especiais(dt, distancia, inimigo)

    def _run_processar_tactical_group(self, dt, distancia, inimigo) -> None:
        self._t_tatico += dt
        if self._t_tatico < self._I_TATICO:
            return
        self._t_tatico = 0.0
        self._atualizar_leitura_oponente(dt, distancia, inimigo)
        self._atualizar_janelas_oportunidade(dt, distancia, inimigo)
        self._atualizar_momentum(dt, distancia, inimigo)
        self._atualizar_estados_humanos(dt, distancia, inimigo)
        self._atualizar_combo_state(dt)

    def _run_processar_strategic_group(self, dt) -> None:
        self._t_estrategico += dt
        if self._t_estrategico < self._I_ESTRATEGICO:
            return
        self._t_estrategico = 0.0
        self._atualizar_ritmo(dt)

    def _run_processar_interruptions(self, dt, distancia, inimigo) -> bool:
        if self._processar_instintos(dt, distancia, inimigo):
            return True
        if self._verificar_hesitacao(dt, distancia, inimigo):
            return True
        self._observar_oponente(inimigo, distancia)
        if self._try_execute_processar_choreography(distancia, inimigo):
            return True
        if self._processar_baiting(dt, distancia, inimigo):
            return True
        if self._processar_reacao_oponente(dt, distancia, inimigo):
            return True
        if self._processar_desvio_inteligente(dt, distancia, inimigo):
            return True
        if self._processar_quirks(dt, distancia, inimigo):
            return True
        if self._processar_reacoes(dt, distancia, inimigo):
            return True
        return False

    def _try_execute_processar_choreography(self, distancia, inimigo) -> bool:
        p = self.parent
        choreographer = CombatChoreographer.get_instance()
        acao_sync = choreographer.get_acao_sincronizada(p) if choreographer else None
        ataque_iminente = self.leitura_oponente.get("ataque_iminente", False)
        if acao_sync and not ataque_iminente:
            if self._executar_acao_sincronizada(acao_sync, distancia, inimigo):
                return True
        return False

    def _resolve_processar_combat_priority(self, dt, distancia, inimigo) -> bool:
        usa_skills_primeiro = self._preferir_skills_neste_frame(distancia, inimigo)
        if self._apply_processar_retreat_regroup_override(dt, distancia, inimigo):
            return True
        ff_suppressed = self._should_suppress_processar_line_attacks()
        if usa_skills_primeiro:
            return self._execute_processar_skill_first_priority(dt, distancia, inimigo, ff_suppressed)
        return self._execute_processar_attack_first_priority(dt, distancia, inimigo, ff_suppressed)

    def _apply_processar_retreat_regroup_override(self, dt, distancia, inimigo) -> bool:
        team_tactic = self.team_orders.get("tactic", "FOCUS_FIRE")
        if team_tactic == "RETREAT_REGROUP" and self.team_orders.get("is_weakest", False):
            if self._processar_skills(dt, distancia, inimigo):
                return True
            self.acao_atual = "RECUAR"
            return True
        return False

    def _should_suppress_processar_line_attacks(self) -> bool:
        p = self.parent
        arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        if self.multi_awareness.get("aliado_no_caminho", False) and arma_dispara_em_linha(arma):
            return random.random() < 0.7
        return False

    def _execute_processar_skill_first_priority(self, dt, distancia, inimigo, ff_suppressed: bool) -> bool:
        if self._processar_skills(dt, distancia, inimigo):
            self._broadcast_team_intent(inimigo)
            return True
        if not ff_suppressed and self._avaliar_e_executar_ataque(dt, distancia, inimigo):
            self._broadcast_team_intent(inimigo)
            return True
        return False

    def _execute_processar_attack_first_priority(self, dt, distancia, inimigo, ff_suppressed: bool) -> bool:
        if not ff_suppressed and self._avaliar_e_executar_ataque(dt, distancia, inimigo):
            self._broadcast_team_intent(inimigo)
            return True
        if self._processar_skills(dt, distancia, inimigo):
            self._broadcast_team_intent(inimigo)
            return True
        return False

    def _finalize_processar_frame(self, dt, distancia, inimigo) -> None:
        self.timer_decisao -= dt
        if self.timer_decisao <= 0:
            self._decidir_movimento(distancia, inimigo)
            self._calcular_timer_decisao()
            self._registrar_acao()
            self._tempo_sem_decisao = 0.0

    # =========================================================================
    # SISTEMA MULTI-COMBATENTE v13.0
    # =========================================================================

    def _atualizar_multi_awareness(self, dt, inimigo_principal, todos_lutadores):
        """Atualiza consciÃªncia de mÃºltiplos combatentes na arena.
        
        Calcula ameaÃ§as de flanqueio, posiÃ§Ã£o de aliados, riscos de friendly fire,
        e seleciona o melhor alvo estratÃ©gico.
        """
        self._limpar_multi_awareness_contatos()
        self._coletar_entidades_multi_awareness(todos_lutadores)
        self._atualizar_resumo_multi_awareness()
        self._calcular_ameaca_flanqueio_multi_awareness()
        self._calcular_concentracao_inimiga_multi_awareness()
        self._detectar_aliado_perto_do_alvo_multi_awareness(inimigo_principal)
        self._detectar_aliado_no_caminho_multi_awareness(inimigo_principal)
        self._selecionar_melhor_alvo_multi_awareness(inimigo_principal)

    def _limpar_multi_awareness_contatos(self) -> None:
        ma = self.multi_awareness
        ma["inimigos"] = []
        ma["aliados"] = []

    def _coletar_entidades_multi_awareness(self, todos_lutadores) -> None:
        p = self.parent
        for lutador in todos_lutadores:
            if lutador is p or lutador.morto:
                continue
            if lutador.team_id != p.team_id:
                self._registrar_inimigo_multi_awareness(lutador)
            else:
                self._registrar_aliado_multi_awareness(lutador)

    def _criar_info_lutador_multi_awareness(self, lutador) -> dict:
        p = self.parent
        dx = lutador.pos[0] - p.pos[0]
        dy = lutador.pos[1] - p.pos[1]
        return {
            "lutador": lutador,
            "distancia": math.hypot(dx, dy),
            "angulo": math.degrees(math.atan2(dy, dx)),
            "vida_pct": lutador.vida / max(lutador.vida_max, 1),
        }

    def _registrar_inimigo_multi_awareness(self, lutador) -> None:
        info = self._criar_info_lutador_multi_awareness(lutador)
        info["ameaca"] = self._calcular_ameaca_lutador(lutador, info["distancia"], info["vida_pct"])
        self.multi_awareness["inimigos"].append(info)

    def _registrar_aliado_multi_awareness(self, lutador) -> None:
        self.multi_awareness["aliados"].append(self._criar_info_lutador_multi_awareness(lutador))

    def _atualizar_resumo_multi_awareness(self) -> None:
        ma = self.multi_awareness
        num_ini = len(ma["inimigos"])
        num_ali = len(ma["aliados"])
        ma["num_inimigos_vivos"] = max(num_ini, 1)
        ma["num_aliados_vivos"] = num_ali
        ma["modo_multialvo"] = num_ini > 1
        ma["em_desvantagem_numerica"] = num_ini > (num_ali + 1)

    def _calcular_ameaca_flanqueio_multi_awareness(self) -> None:
        ma = self.multi_awareness
        if len(ma["inimigos"]) < 2:
            ma["ameaca_flanqueio"] = 0.0
            return
        angulos = sorted(inimigo["angulo"] for inimigo in ma["inimigos"])
        max_spread = 0.0
        for i in range(len(angulos)):
            for j in range(i + 1, len(angulos)):
                diff = abs(angulos[j] - angulos[i])
                if diff > 180:
                    diff = 360 - diff
                max_spread = max(max_spread, diff)
        ma["ameaca_flanqueio"] = min(1.0, max_spread / 180.0)

    def _calcular_concentracao_inimiga_multi_awareness(self) -> None:
        ma = self.multi_awareness
        inimigos = ma["inimigos"]
        if len(inimigos) < 2:
            ma["concentracao_inimiga"] = 0.0
            return
        posicoes = [(info["lutador"].pos[0], info["lutador"].pos[1]) for info in inimigos]
        cx = sum(x for x, _ in posicoes) / len(posicoes)
        cy = sum(y for _, y in posicoes) / len(posicoes)
        spread = sum(math.hypot(x - cx, y - cy) for x, y in posicoes) / len(posicoes)
        ma["concentracao_inimiga"] = max(0.0, 1.0 - spread / 10.0)

    def _detectar_aliado_perto_do_alvo_multi_awareness(self, inimigo_principal) -> None:
        ma = self.multi_awareness
        ma["aliado_perto_alvo"] = False
        if not ma["aliados"] or not inimigo_principal:
            return
        for aliado in ma["aliados"]:
            dist_aliado_alvo = math.hypot(
                aliado["lutador"].pos[0] - inimigo_principal.pos[0],
                aliado["lutador"].pos[1] - inimigo_principal.pos[1],
            )
            if dist_aliado_alvo < 3.0:
                ma["aliado_perto_alvo"] = True
                return

    def _detectar_aliado_no_caminho_multi_awareness(self, inimigo_principal) -> None:
        p = self.parent
        ma = self.multi_awareness
        ma["aliado_no_caminho"] = False
        if not ma["aliados"] or not inimigo_principal:
            return
        dir_alvo = math.atan2(
            inimigo_principal.pos[1] - p.pos[1],
            inimigo_principal.pos[0] - p.pos[0],
        )
        dist_alvo = math.hypot(
            inimigo_principal.pos[0] - p.pos[0],
            inimigo_principal.pos[1] - p.pos[1],
        )
        for aliado in ma["aliados"]:
            if aliado["distancia"] > dist_alvo:
                continue
            dir_aliado = math.atan2(
                aliado["lutador"].pos[1] - p.pos[1],
                aliado["lutador"].pos[0] - p.pos[0],
            )
            diff_ang = abs(math.degrees(dir_alvo - dir_aliado))
            if diff_ang > 180:
                diff_ang = 360 - diff_ang
            if diff_ang < 25:
                ma["aliado_no_caminho"] = True
                return

    def _selecionar_melhor_alvo_multi_awareness(self, inimigo_principal) -> None:
        ma = self.multi_awareness
        if ma["inimigos"]:
            melhor = max(ma["inimigos"], key=self._score_alvo)
            ma["melhor_alvo"] = melhor["lutador"]
            return
        ma["melhor_alvo"] = inimigo_principal

    def _calcular_ameaca_lutador(self, lutador, distancia, vida_pct):
        """Calcula nÃ­vel de ameaÃ§a de um lutador (0-1).
        
        Considera: distÃ¢ncia, vida, se estÃ¡ atacando, tipo de arma.
        """
        ameaca = 0.5
        ameaca += self._calcular_modificador_distancia_ameaca(distancia)
        ameaca += vida_pct * 0.2
        ameaca += self._calcular_modificador_ataque_ameaca(lutador)
        ameaca += self._calcular_modificador_alcance_ameaca(lutador)
        
        return max(0.0, min(1.0, ameaca))

    def _calcular_modificador_distancia_ameaca(self, distancia):
        if distancia < 3.0:
            return 0.3 * (1.0 - distancia / 3.0)
        if distancia > 8.0:
            return -0.2
        return 0.0

    def _calcular_modificador_ataque_ameaca(self, lutador):
        return 0.15 if getattr(lutador, 'atacando', False) else 0.0

    def _calcular_modificador_alcance_ameaca(self, lutador):
        alcance = self._resolver_alcance_ameaca_arma(lutador)
        if alcance > 3.0:
            return 0.1 if alcance < 6.0 else 0.15
        return 0.0

    def _resolver_alcance_ameaca_arma(self, lutador):
        arma = getattr(getattr(lutador, 'dados', None), 'arma_obj', None)
        if not arma:
            return 0.0
        alcance = 0.0
        if WEAPON_ANALYSIS_AVAILABLE:
            try:
                perfil = get_weapon_profile(arma)
            except Exception:
                perfil = None
            if perfil:
                alcance = getattr(perfil, 'alcance_maximo', 0.0)
        if alcance <= 0:
            alcance = obter_metricas_arma(arma, self.parent)["alcance_max"]
        return alcance

    def _score_alvo(self, info_inimigo):
        """Calcula score de prioridade para um alvo.
        
        Prioriza: inimigos com pouca vida, perto, e atacando aliados.
        Integra com team_orders para coordenaÃ§Ã£o de foco.
        """
        f = info_inimigo["lutador"]
        score = 0.0
        score += self._score_execucao_alvo(info_inimigo)
        score += self._score_proximidade_alvo(info_inimigo)
        score += self._score_ameaca_e_memoria_alvo(info_inimigo)
        score += self._score_interceptacao_alvo(f)
        score += self._score_alvo_designado_time(f)
        score += self._score_targeting_por_role_alvo(f)
        score += self._score_penalidade_overkill_alvo(f)
        return score

    def _score_execucao_alvo(self, info_inimigo):
        vida_pct = info_inimigo["vida_pct"]
        if vida_pct < 0.25:
            return 3.0
        if vida_pct < 0.5:
            return 1.5
        return 0.0

    def _score_proximidade_alvo(self, info_inimigo):
        distancia = info_inimigo["distancia"]
        if distancia < 4.0:
            return 2.0 * (1.0 - distancia / 4.0)
        return 0.0

    def _score_ameaca_e_memoria_alvo(self, info_inimigo):
        score = info_inimigo["ameaca"] * 1.5
        alvo = info_inimigo["lutador"]
        vies_oponente = self._obter_vies_oponente(alvo)
        score += vies_oponente.get("vies_pressao", 0.0) * 0.7
        score += vies_oponente.get("vies_agressao", 0.0) * 0.5
        score -= max(0.0, vies_oponente.get("vies_cautela", 0.0)) * 0.25
        relacao = self._obter_relacao_oponente(alvo)
        score += relacao.get("obsessao", 0.0) * 1.10
        score += relacao.get("vinganca", 0.0) * 0.80
        score += relacao.get("caca", 0.0) * 0.65
        score += relacao.get("respeito", 0.0) * 0.25
        return score

    def _score_interceptacao_alvo(self, lutador):
        if not getattr(lutador, 'brain', None):
            return 0.0
        alvo_do_inimigo = getattr(lutador.brain, '_alvo_atual', None)
        if alvo_do_inimigo and getattr(alvo_do_inimigo, 'team_id', -1) == self.parent.team_id:
            return 1.0
        return 0.0

    def _score_alvo_designado_time(self, lutador):
        primary_id = self.team_orders.get("primary_target_id", 0)
        if primary_id and id(lutador) == primary_id:
            return 2.5
        return 0.0

    def _score_targeting_por_role_alvo(self, lutador):
        team_role = self.team_orders.get("role", "STRIKER")
        if team_role == "FLANKER":
            return self._score_flanker_targeting_alvo(lutador)
        if team_role == "SUPPORT":
            return self._score_support_targeting_alvo(lutador)
        return 0.0

    def _score_flanker_targeting_alvo(self, lutador):
        ally_intents = self.team_orders.get("ally_intents", {})
        for intent in ally_intents.values():
            if intent.target_id == id(lutador):
                return 1.0
        return 0.0

    def _score_support_targeting_alvo(self, lutador):
        aliado_alvo = getattr(getattr(lutador, 'brain', None), '_alvo_atual', None)
        if aliado_alvo and getattr(aliado_alvo, 'team_id', -1) == self.parent.team_id:
            hp_aliado = aliado_alvo.vida / max(aliado_alvo.vida_max, 1)
            if hp_aliado < 0.4:
                return 2.0
        return 0.0

    def _score_penalidade_overkill_alvo(self, lutador):
        ally_intents = self.team_orders.get("ally_intents", {})
        allies_on_target = sum(
            1 for intent in ally_intents.values()
            if getattr(intent, 'target_id', 0) == id(lutador)
        )
        if allies_on_target >= 2:
            return -0.5 * (allies_on_target - 1)
        return 0.0

    # =========================================================================
    # SISTEMA DE COORDENAÃ‡ÃƒO DE TIME v13.0
    # =========================================================================
    
    def _aplicar_team_orders(self, dt, distancia, inimigo, todos_lutadores):
        """Aplica ordens do TeamCoordinator ao comportamento individual.
        
        Modifica: agressividade, alvo, posicionamento, urgÃªncia de skills.
        Integra com: personalidade, classe, emoÃ§Ãµes, spatial.
        """
        orders = self.team_orders
        if self._team_orders_estao_inativos(orders):
            return
        role = orders.get("role", "STRIKER")
        tactic = orders.get("tactic", "FOCUS_FIRE")
        package_role = orders.get("package_role", "")
        modo_horda = bool(orders.get("modo_horda", False))

        self._aplicar_agressividade_por_role_team_orders(dt, role)
        self._aplicar_ajustes_emocionais_por_tatica_team_orders(dt, role, tactic, orders)
        self._aplicar_ajustes_modo_horda_team_orders(dt, package_role, modo_horda, orders)
        self._aplicar_ajustes_desvantagem_numerica_team_orders(dt, orders)
        self._aplicar_resposta_a_callouts_team_orders(role, orders)
        self._aplicar_sinergias_team_orders(role, orders)
        self._aplicar_posicionamento_relativo_team_orders(role, orders)

    def _team_orders_estao_inativos(self, orders) -> bool:
        return not orders or orders.get("alive_count", 1) <= 1

    def _aplicar_agressividade_por_role_team_orders(self, dt, role) -> None:
        role_agg_mod = {
            "VANGUARD":   0.10,    # Moderadamente agressivo, engaja
            "STRIKER":    0.15,    # Agressivo, busca dano
            "FLANKER":    0.05,    # Cauteloso atÃ© ter abertura
            "ARTILLERY":  -0.10,   # MantÃ©m distÃ¢ncia
            "SUPPORT":    -0.15,   # Mais defensivo
            "CONTROLLER": -0.05,   # Calculado, espera momento certo
        }
        # BUG-C3 fix: substituÃ­do acumulador (+= mod * dt) por lerp.
        # O acumulador nunca atingia equilÃ­brio porque ganho > decaimento em
        # brain_emotions (ex.: ARTILLERY acumulava -0.1/s mas sÃ³ decaÃ­a +0.03/s,
        # atingindo o piso em ~6s e ficando lÃ¡ para sempre).
        # Com lerp, o modificador converge suavemente ao setpoint do role
        # sem ultrapassÃ¡-lo, independente do dt.
        target_mod = role_agg_mod.get(role, 0.0)
        lerp_rate = min(1.0, 1.5 * dt)  # ~1.5 unidades/s de convergÃªncia
        self._agressividade_temp_mod += (target_mod - self._agressividade_temp_mod) * lerp_rate

    def _aplicar_ajustes_emocionais_por_tatica_team_orders(self, dt, role, tactic, orders) -> None:
        if tactic == "FULL_AGGRO":
            self.confianca = min(1.0, self.confianca + 0.02 * dt * 60)
            self.raiva = min(1.0, self.raiva + 0.01 * dt * 60)
        elif tactic == "RETREAT_REGROUP":
            self.medo = min(0.5, self.medo + 0.02 * dt * 60)  # Cuidado, nÃ£o pÃ¢nico
        elif tactic == "PROTECT_CARRY":
            if orders.get("is_carry", False):
                self.confianca = min(1.0, self.confianca + 0.03 * dt * 60)
            elif role in ("VANGUARD", "SUPPORT"):
                # Protetores mantÃªm calma
                self.medo = max(0, self.medo - 0.01 * dt * 60)

    def _aplicar_ajustes_modo_horda_team_orders(self, dt, package_role, modo_horda, orders) -> None:
        if modo_horda:
            pressure_ratio = min(1.0, max(0.0, (orders.get("enemy_alive_count", 0) - orders.get("alive_count", 1)) / 6.0))
            if package_role == "defensor":
                self._agressividade_temp_mod += 0.04 * dt * 60
                self.medo = max(0.0, self.medo - 0.015 * dt * 60)
            elif package_role in ("curandeiro", "suporte_controle"):
                self._agressividade_temp_mod -= 0.06 * dt * 60
                self.hesitacao = min(0.35, self.hesitacao + 0.008 * dt * 60)
            elif package_role in ("limpador_de_horda", "controlador_de_area", "invocador"):
                self._agressividade_temp_mod += 0.05 * pressure_ratio
                self.excitacao = min(1.0, self.excitacao + 0.012 * dt * 60 * max(0.25, pressure_ratio))
            elif package_role == "assassino":
                self._agressividade_temp_mod -= 0.03 * dt * 60
                self.hesitacao = min(0.30, self.hesitacao + 0.006 * dt * 60)

    def _aplicar_ajustes_desvantagem_numerica_team_orders(self, dt, orders) -> None:
        if orders.get("em_desvantagem", False):
            # Time em desvantagem: aumenta cautela de todos exceto berserkers
            if "BERSERKER" not in self.tracos and "DETERMINADO" not in self.tracos:
                self.hesitacao = min(0.3, self.hesitacao + 0.01 * dt * 60)
            # Mas se eu sou o carry, pressiona mais (Ã© a Ãºltima esperanÃ§a)
            if orders.get("is_carry", False):
                self.adrenalina = min(1.0, self.adrenalina + 0.03 * dt * 60)

    def _aplicar_resposta_a_callouts_team_orders(self, role, orders) -> None:
        for callout in orders.get("callouts", []):
            if callout.get("type") == "HELP":
                # Aliado pediu ajuda â€” se sou vanguard/support, priorizo
                if role in ("VANGUARD", "SUPPORT"):
                    self.impulso = min(0.6, self.impulso + 0.1)
            elif callout.get("type") == "TARGET":
                # Aliado marcou alvo â€” aumento prioridade mental
                pass  # JÃ¡ handled pelo scoring do _score_alvo

    def _aplicar_sinergias_team_orders(self, role, orders) -> None:
        p = self.parent
        synergies = orders.get("synergies", [])
        for syn in synergies:
            if syn.tipo == "cc_burst" and role == "STRIKER":
                # Tenho sinergia CCâ†’Burst com um controlador
                # Espera pelo CC antes de burstar
                ally_intents = orders.get("ally_intents", {})
                partner_id = syn.fighter_a_id if syn.fighter_b_id == id(p) else syn.fighter_b_id
                partner_intent = ally_intents.get(partner_id)
                if partner_intent and partner_intent.skill_name:
                    # Aliado controller estÃ¡ usando skill â€” BURST NOW
                    self._agressividade_temp_mod += 0.3
                    self.modo_burst = True
            elif syn.tipo == "tank_dps" and role == "VANGUARD":
                # Sou o tank â€” mantenho aggro posicionando na frente
                self._agressividade_temp_mod += 0.1
            elif syn.tipo == "heal_support" and role == "SUPPORT":
                # Monitora aliado com pouca vida
                if orders.get("is_weakest", False):
                    pass  # Eu sou o fraco, cuido de mim
                else:
                    # Olho pro mais fraco do time para curar
                    self._agressividade_temp_mod -= 0.1

    def _aplicar_posicionamento_relativo_team_orders(self, role, orders) -> None:
        p = self.parent
        team_center = orders.get("team_center", (0, 0))
        dist_to_center = math.hypot(p.pos[0] - team_center[0], p.pos[1] - team_center[1])
        
        if role == "VANGUARD":
            # Vanguard fica na frente do time (entre aliados e inimigos)
            pass  # Handled na _decidir_movimento via spatial
        elif role == "ARTILLERY":
            # Artillery fica atrÃ¡s do time
            if dist_to_center > 8.0:
                # Muito longe do time, reagrupa
                self._agressividade_temp_mod -= 0.1
        elif role == "SUPPORT":
            # Suporte fica perto do centro do time
            if dist_to_center > 6.0:
                self._agressividade_temp_mod -= 0.15
    
    def _broadcast_team_intent(self, inimigo):
        """Comunica a intenÃ§Ã£o atual ao TeamCoordinator."""
        from ia.team_ai import TeamCoordinatorManager
        coord = TeamCoordinatorManager.get().get_fighter_coordinator(self.parent)
        if coord:
            skill_name = ""
            if hasattr(self.parent, 'skill_atual_nome'):
                skill_name = getattr(self.parent, 'skill_atual_nome', "") or ""
            coord.broadcast_intent(
                self.parent,
                action=self.acao_atual,
                target=inimigo,
                skill=skill_name,
                urgency=self.adrenalina,
            )
    
    def _pedir_ajuda_time(self):
        """Pede ajuda ao time quando em perigo."""
        from ia.team_ai import TeamCoordinatorManager
        coord = TeamCoordinatorManager.get().get_fighter_coordinator(self.parent)
        if coord:
            p = self.parent
            hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1
            urgency = max(0.5, 1.0 - hp_pct)
            coord.request_help(p, urgency)
    
    def _marcar_alvo_time(self, alvo, reason="FOCUS"):
        """Marca um alvo para o time focar."""
        from ia.team_ai import TeamCoordinatorManager
        coord = TeamCoordinatorManager.get().get_fighter_coordinator(self.parent)
        if coord:
            coord.callout_target(self.parent, alvo, reason)

