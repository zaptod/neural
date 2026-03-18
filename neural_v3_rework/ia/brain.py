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
        self.timer_decisao = 0.0
        self.acao_atual = "NEUTRO"
        self._tempo_sem_decisao = 0.0
        self.dir_circular = random.choice([-1, 1])
        self._dir_circular_cd = 0.0  # Cooldown antes de permitir nova mudanÃ§a de dir_circular
        self.circular_consecutivo = 0  # Conta decisÃµes CIRCULAR seguidas
        
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

        # Gera personalidade Ãºnica
        self._gerar_personalidade()


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
        memoria = getattr(self, "memoria_oponente", None)
        if not isinstance(memoria, dict):
            return
        buckets = memoria.get("adaptacao_por_oponente", {})
        if not isinstance(buckets, dict):
            return

        _, decaimento, _ = self._modificadores_personalidade_adaptativa()
        taxa_base = max(0.02, dt * 0.28 * decaimento)
        remover = []
        for chave, bucket in buckets.items():
            if not isinstance(bucket, dict):
                remover.append(chave)
                continue
            for campo, valor in list(bucket.items()):
                if campo == "ultimo_evento":
                    continue
                if campo == "padroes":
                    if not isinstance(valor, dict):
                        bucket[campo] = {}
                        continue
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
                    continue
                if not isinstance(valor, (int, float)):
                    continue
                taxa_campo = taxa_base
                if campo.startswith("relacao_"):
                    taxa_campo = taxa_base * 0.45
                if abs(valor) <= taxa_campo:
                    bucket[campo] = 0.0
                elif valor > 0:
                    bucket[campo] = valor - taxa_campo
                else:
                    bucket[campo] = valor + taxa_campo
            padroes_bucket = bucket.get("padroes", {})
            if isinstance(padroes_bucket, dict) and padroes_bucket:
                bucket["padrao_dominante"] = max(padroes_bucket.items(), key=lambda item: item[1])[0]
            else:
                bucket["padrao_dominante"] = None
            self._atualizar_relacao_dominante_bucket(bucket)
            if all(abs(bucket.get(campo, 0.0)) < 0.04 for campo in (
                "vies_skill", "vies_agressao", "vies_cautela", "vies_pressao", "vies_contra_ataque"
            )) and all(bucket.get(campo, 0.0) < 0.05 for campo in (
                "relacao_respeito", "relacao_vinganca", "relacao_obsessao", "relacao_caca"
            )):
                bucket["ultimo_evento"] = None
            bucket_inerte = all(abs(bucket.get(campo, 0.0)) < 0.01 for campo in (
                "vies_skill", "vies_agressao", "vies_cautela", "vies_pressao", "vies_contra_ataque"
            )) and all(bucket.get(campo, 0.0) < 0.03 for campo in (
                "relacao_respeito", "relacao_vinganca", "relacao_obsessao", "relacao_caca"
            )) and not bucket.get("padroes")
            if bucket_inerte and memoria.get("id_atual") != chave:
                remover.append(chave)
        for chave in remover:
            buckets.pop(chave, None)

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

        dominante = relacao.get("dominante")
        intensidade = max(
            relacao.get("respeito", 0.0),
            relacao.get("vinganca", 0.0),
            relacao.get("obsessao", 0.0),
            relacao.get("caca", 0.0),
        )
        if intensidade < 0.16:
            dominante = None

        perfil = "neutro"
        if dominante == "respeito":
            perfil = "duelo"
        elif dominante == "vinganca":
            perfil = "revanche"
        elif dominante == "obsessao":
            perfil = "rival"
        elif dominante == "caca":
            perfil = "predacao"

        return {
            "dominante": dominante,
            "intensidade": max(0.0, min(1.0, intensidade)),
            "perfil": perfil,
            "respeito": relacao.get("respeito", 0.0),
            "vinganca": relacao.get("vinganca", 0.0),
            "obsessao": relacao.get("obsessao", 0.0),
            "caca": relacao.get("caca", 0.0),
        }

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
        p = self.parent
        arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        familia = resolver_familia_arma(arma)
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

        prefer_skills = False
        if self.skill_strategy is not None:
            role = self.skill_strategy.role_principal.value
            if role in ["artillery", "burst_mage", "control_mage", "summoner", "buffer", "channeler"]:
                prefer_skills = True

        if team_role in {"ARTILLERY", "CONTROLLER", "SUPPORT"}:
            prefer_skills = True

        if mana_pct < 0.16 and team_role not in {"SUPPORT", "CONTROLLER"}:
            prefer_skills = False

        if familia == "foco":
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

        elif familia == "orbital":
            burst_pronto = getattr(p, 'orbital_burst_cd', 999.0) <= 0.0
            if burst_pronto and distancia <= max(3.2, alcance_ideal * 1.12):
                prefer_skills = False
            elif "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos:
                prefer_skills = True

        elif familia == "hibrida":
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

        elif familia == "corrente":
            metricas = obter_metricas_arma(arma, p)
            alcance_max = metricas["alcance_max"]
            alcance_min = metricas["alcance_min"]
            centro_sweet_spot = max(alcance_min + 0.4, (alcance_max + alcance_min) / 2.0)
            em_sweet_spot = abs(distancia - centro_sweet_spot) <= max(0.55, alcance_max * 0.20)
            if em_sweet_spot:
                prefer_skills = False
            elif "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos:
                prefer_skills = True

        if team_tactic == "FULL_AGGRO" and familia in {"corrente", "orbital", "hibrida"} and hp_pct > 0.35:
            prefer_skills = False
        elif team_tactic == "KITE_AND_POKE" and familia in {"foco", "disparo", "arremesso"}:
            prefer_skills = True

        if self.janela_ataque.get("aberta", False) and self.janela_ataque.get("qualidade", 0.0) > 0.75:
            if familia in {"corrente", "orbital", "hibrida"}:
                prefer_skills = False

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
        p = self.parent
        self.tempo_combate += dt
        self._tempo_sem_decisao += dt
        # BUG-C2 fix: registra o inimigo principal como alvo atual logo no inÃ­cio
        # do frame para que _score_alvo (priorizaÃ§Ã£o de times) possa lÃª-lo.
        self._alvo_atual = inimigo
        self._garantir_memoria_curta_oponente(inimigo)

        # Anti-indecisÃ£o: se a IA ficar muito tempo sem recalcular estratÃ©gia
        # e estiver em aÃ§Ã£o passiva, forÃ§a uma nova decisÃ£o para quebrar stalls.
        if (
            self._tempo_sem_decisao > 0.9
            and not p.atacando
            and self.acao_atual in {"NEUTRO", "BLOQUEAR", "CIRCULAR", "COMBATE", "RECUAR", "FUGIR"}
        ):
            self._decidir_movimento(distancia, inimigo)
            self._calcular_timer_decisao()
            self._registrar_acao()
            self._tempo_sem_decisao = 0.0
        
        # QC-03: gera um pool de valores aleatÃ³rios uma vez por frame.
        # As funÃ§Ãµes do cascade (_aplicar_modificadores_*, _comportamento_estilo, etc.)
        # consomem esses valores em sequÃªncia em vez de chamar random.random() cada uma.
        # Isso reduz de ~15-25 chamadas/frame para 1, tornando o comportamento
        # mais fÃ¡cil de reproduzir em debug e mais eficiente em batalhas multi-combatente.
        self._rand_pool = [random.random() for _ in range(AI_RAND_POOL_SIZE)]
        self._rand_idx = 0

        # F01 Sprint 9: modo debug da IA â€” ligar em utilitarios/config.py: DEBUG_AI = True
        # Filtrar por nome: DEBUG_AI_FIGHTER = "NomeDoLutador"
        if DEBUG_AI:
            _nome = p.dados.nome if hasattr(p, 'dados') and hasattr(p.dados, 'nome') else '?'
            if DEBUG_AI_FIGHTER is None or _nome == DEBUG_AI_FIGHTER:
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

        # v13.0: Atualiza consciÃªncia multi-combatente
        if todos_lutadores is not None:
            self._atualizar_multi_awareness(dt, inimigo, todos_lutadores)
        
        # v13.0: Aplica ordens do TeamCoordinator ao comportamento
        self._aplicar_team_orders(dt, distancia, inimigo, todos_lutadores)
        
        # A02: mÃ©todos de atualizaÃ§Ã£o divididos em 3 grupos de throttle.
        # _atualizar_cooldowns e _detectar_dano sÃ£o baratos e frame-critical â€” sempre rodam.
        self._atualizar_cooldowns(dt)
        self._detectar_dano()

        # GRUPO EMOCIONAL â€” 4hz (a cada 0.25s): emoÃ§Ãµes, humor, modos especiais
        self._t_emocional += dt
        if self._t_emocional >= self._I_EMOCIONAL:
            self._t_emocional = 0.0
            self._atualizar_emocoes(dt, distancia, inimigo)
            self._atualizar_humor(dt)
            self._processar_modos_especiais(dt, distancia, inimigo)

        # GRUPO TÃTICO â€” 10hz (a cada 0.10s): leitura, janelas, momentum, estados, combo
        self._t_tatico += dt
        if self._t_tatico >= self._I_TATICO:
            self._t_tatico = 0.0
            # === NOVOS SISTEMAS v8.0 ===
            self._atualizar_leitura_oponente(dt, distancia, inimigo)
            self._atualizar_janelas_oportunidade(dt, distancia, inimigo)
            self._atualizar_momentum(dt, distancia, inimigo)
            self._atualizar_estados_humanos(dt, distancia, inimigo)
            self._atualizar_combo_state(dt)

        # GRUPO ESTRATÃ‰GICO â€” 2hz (a cada 0.50s): ritmo
        # (consciÃªncia espacial e percepÃ§Ã£o de armas tÃªm throttle prÃ³prio interno)
        self._t_estrategico += dt
        if self._t_estrategico >= self._I_ESTRATEGICO:
            self._t_estrategico = 0.0
            # === NOVOS SISTEMAS v11.0 ===
            self._atualizar_ritmo(dt)

        # === SISTEMA ESPACIAL v9.0 === (throttle interno: AI_INTERVALO_ESPACIAL=0.20s)
        self._atualizar_consciencia_espacial(dt, distancia, inimigo)

        # === SISTEMA DE PERCEPÃ‡ÃƒO DE ARMAS v10.0 === (throttle interno: 0.50s)
        self._atualizar_percepcao_armas(dt, distancia, inimigo)
        if self._processar_instintos(dt, distancia, inimigo):
            return  # Instinto tomou controle
        
        # HesitaÃ§Ã£o humana - Ã s vezes congela brevemente
        if self._verificar_hesitacao(dt, distancia, inimigo):
            return
        
        # Sistema de Coreografia
        self._observar_oponente(inimigo, distancia)
        
        choreographer = CombatChoreographer.get_instance()
        acao_sync = choreographer.get_acao_sincronizada(p) if choreographer else None
        
        # Sprint1: O choreographer fazia early-return ANTES de _processar_desvio_inteligente
        # e _processar_reacao_oponente. Durante momentos como STANDOFF ou BREATHER,
        # a IA ficava "congelada" na aÃ§Ã£o coreografada mesmo com o inimigo atacando.
        # Fix: se hÃ¡ ataque iminente, o choreographer perde prioridade.
        ataque_iminente = self.leitura_oponente.get("ataque_iminente", False)
        if acao_sync and not ataque_iminente:
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
        
        # === PRIORIZAÃ‡ÃƒO DE SKILLS PARA MAGOS ===
        # Se o personagem Ã© um caster (role de mago), prioriza skills sobre ataques bÃ¡sicos
        usa_skills_primeiro = self._preferir_skills_neste_frame(distancia, inimigo)
        team_role = self.team_orders.get("role", "STRIKER")
        
        # v13.0: TEAM TACTICAL OVERRIDE â€” certas tÃ¡ticas de time alteram comportamento
        team_tactic = self.team_orders.get("tactic", "FOCUS_FIRE")
        if team_tactic == "RETREAT_REGROUP" and self.team_orders.get("is_weakest", False):
            # Sou o mais fraco e time estÃ¡ recuando: prioriza sobrevivÃªncia
            if self._processar_skills(dt, distancia, inimigo):
                return  # Tenta usar skill defensiva/cura
            self.acao_atual = "RECUAR"
            return
        
        # v13.0: Se friendly fire risk alto, suprime apenas ataques em linha.
        ff_suppressed = False
        arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        if self.multi_awareness.get("aliado_no_caminho", False) and arma_dispara_em_linha(arma):
            if random.random() < 0.7:
                ff_suppressed = True
        
        if usa_skills_primeiro:
            # Magos: Skills primeiro, depois ataque bÃ¡sico
            if self._processar_skills(dt, distancia, inimigo):
                self._broadcast_team_intent(inimigo)
                return
            if not ff_suppressed and self._avaliar_e_executar_ataque(dt, distancia, inimigo):
                self._broadcast_team_intent(inimigo)
                return
        else:
            # Melee: Ataque primeiro, skills como suporte
            if not ff_suppressed and self._avaliar_e_executar_ataque(dt, distancia, inimigo):
                self._broadcast_team_intent(inimigo)
                return
            if self._processar_skills(dt, distancia, inimigo):
                self._broadcast_team_intent(inimigo)
                return
        
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
        p = self.parent
        ma = self.multi_awareness
        
        ma["inimigos"] = []
        ma["aliados"] = []
        
        for f in todos_lutadores:
            if f is p or f.morto:
                continue
            
            dx = f.pos[0] - p.pos[0]
            dy = f.pos[1] - p.pos[1]
            dist = math.hypot(dx, dy)
            angulo = math.degrees(math.atan2(dy, dx))
            
            if f.team_id != p.team_id:
                # Inimigo
                vida_pct = f.vida / max(f.vida_max, 1)
                ameaca = self._calcular_ameaca_lutador(f, dist, vida_pct)
                ma["inimigos"].append({
                    "lutador": f,
                    "distancia": dist,
                    "angulo": angulo,
                    "ameaca": ameaca,
                    "vida_pct": vida_pct,
                })
            else:
                # Aliado
                vida_pct = f.vida / max(f.vida_max, 1)
                ma["aliados"].append({
                    "lutador": f,
                    "distancia": dist,
                    "angulo": angulo,
                    "vida_pct": vida_pct,
                })
        
        num_ini = len(ma["inimigos"])
        num_ali = len(ma["aliados"])
        ma["num_inimigos_vivos"] = max(num_ini, 1)
        ma["num_aliados_vivos"] = num_ali
        ma["modo_multialvo"] = num_ini > 1
        ma["em_desvantagem_numerica"] = num_ini > (num_ali + 1)
        
        # --- AmeaÃ§a de flanqueio ---
        if num_ini >= 2:
            angulos = sorted([e["angulo"] for e in ma["inimigos"]])
            max_spread = 0
            for i in range(len(angulos)):
                for j in range(i + 1, len(angulos)):
                    diff = abs(angulos[j] - angulos[i])
                    if diff > 180:
                        diff = 360 - diff
                    max_spread = max(max_spread, diff)
            # Se inimigos estÃ£o em Ã¢ngulos opostos (>120Â°), flanqueio alto
            ma["ameaca_flanqueio"] = min(1.0, max_spread / 180.0)
        else:
            ma["ameaca_flanqueio"] = 0.0
        
        # --- ConcentraÃ§Ã£o inimiga (quÃ£o agrupados estÃ£o) ---
        if num_ini >= 2:
            posicoes = [(e["lutador"].pos[0], e["lutador"].pos[1]) for e in ma["inimigos"]]
            cx = sum(x for x, y in posicoes) / num_ini
            cy = sum(y for x, y in posicoes) / num_ini
            spread = sum(math.hypot(x - cx, y - cy) for x, y in posicoes) / num_ini
            # Menor spread = mais concentrados. Normaliza para 0-1 (0=espalhados, 1=juntos)
            ma["concentracao_inimiga"] = max(0.0, 1.0 - spread / 10.0)
        else:
            ma["concentracao_inimiga"] = 0.0
        
        # --- Aliado perto do alvo principal ---
        if ma["aliados"] and inimigo_principal:
            for aliado in ma["aliados"]:
                dist_aliado_alvo = math.hypot(
                    aliado["lutador"].pos[0] - inimigo_principal.pos[0],
                    aliado["lutador"].pos[1] - inimigo_principal.pos[1]
                )
                if dist_aliado_alvo < 3.0:
                    ma["aliado_perto_alvo"] = True
                    break
            else:
                ma["aliado_perto_alvo"] = False
        else:
            ma["aliado_perto_alvo"] = False
        
        # --- Aliado no caminho (risco de friendly fire) ---
        ma["aliado_no_caminho"] = False
        if ma["aliados"] and inimigo_principal:
            dir_alvo = math.atan2(
                inimigo_principal.pos[1] - p.pos[1],
                inimigo_principal.pos[0] - p.pos[0]
            )
            dist_alvo = math.hypot(
                inimigo_principal.pos[0] - p.pos[0],
                inimigo_principal.pos[1] - p.pos[1]
            )
            for aliado in ma["aliados"]:
                if aliado["distancia"] > dist_alvo:
                    continue  # Aliado atrÃ¡s do alvo, sem risco
                dir_aliado = math.atan2(
                    aliado["lutador"].pos[1] - p.pos[1],
                    aliado["lutador"].pos[0] - p.pos[0]
                )
                diff_ang = abs(math.degrees(dir_alvo - dir_aliado))
                if diff_ang > 180:
                    diff_ang = 360 - diff_ang
                if diff_ang < 25:  # Aliado dentro de cone de 25Â° da direÃ§Ã£o do ataque
                    ma["aliado_no_caminho"] = True
                    break
        
        # --- Melhor alvo estratÃ©gico ---
        if ma["inimigos"]:
            melhor = max(ma["inimigos"], key=lambda e: self._score_alvo(e))
            ma["melhor_alvo"] = melhor["lutador"]
        else:
            ma["melhor_alvo"] = inimigo_principal

    def _calcular_ameaca_lutador(self, lutador, distancia, vida_pct):
        """Calcula nÃ­vel de ameaÃ§a de um lutador (0-1).
        
        Considera: distÃ¢ncia, vida, se estÃ¡ atacando, tipo de arma.
        """
        ameaca = 0.5
        
        # Mais perto = mais perigoso
        if distancia < 3.0:
            ameaca += 0.3 * (1.0 - distancia / 3.0)
        elif distancia > 8.0:
            ameaca -= 0.2
        
        # Mais vida = mais perigoso
        ameaca += vida_pct * 0.2
        
        # Se estÃ¡ atacando = mais perigoso
        if getattr(lutador, 'atacando', False):
            ameaca += 0.15
        
        # Se tem arma de longo alcance
        arma = getattr(getattr(lutador, 'dados', None), 'arma_obj', None)
        alcance = 0.0
        if arma:
            if WEAPON_ANALYSIS_AVAILABLE:
                try:
                    perfil = get_weapon_profile(arma)
                except Exception:
                    perfil = None
                if perfil:
                    alcance = getattr(perfil, 'alcance_maximo', 0.0)
            if alcance <= 0:
                alcance = obter_metricas_arma(arma, self.parent)["alcance_max"]
            if alcance > 3.0:
                ameaca += 0.1 if alcance < 6.0 else 0.15
        
        return max(0.0, min(1.0, ameaca))

    def _score_alvo(self, info_inimigo):
        """Calcula score de prioridade para um alvo.
        
        Prioriza: inimigos com pouca vida, perto, e atacando aliados.
        Integra com team_orders para coordenaÃ§Ã£o de foco.
        """
        score = 0.0
        
        # Prioridade 1: Inimigos com pouca vida (execute)
        if info_inimigo["vida_pct"] < 0.25:
            score += 3.0
        elif info_inimigo["vida_pct"] < 0.5:
            score += 1.5
        
        # Prioridade 2: Proximidade (preferir alvos perto)
        if info_inimigo["distancia"] < 4.0:
            score += 2.0 * (1.0 - info_inimigo["distancia"] / 4.0)
        
        # Prioridade 3: AmeaÃ§a alta
        score += info_inimigo["ameaca"] * 1.5
        vies_oponente = self._obter_vies_oponente(info_inimigo["lutador"])
        score += vies_oponente.get("vies_pressao", 0.0) * 0.7
        score += vies_oponente.get("vies_agressao", 0.0) * 0.5
        score -= max(0.0, vies_oponente.get("vies_cautela", 0.0)) * 0.25
        relacao = self._obter_relacao_oponente(info_inimigo["lutador"])
        score += relacao.get("obsessao", 0.0) * 1.10
        score += relacao.get("vinganca", 0.0) * 0.80
        score += relacao.get("caca", 0.0) * 0.65
        score += relacao.get("respeito", 0.0) * 0.25

        # Prioridade 4: Se estÃ¡ atacando um aliado nosso
        f = info_inimigo["lutador"]
        if getattr(f, 'brain', None):
            brain = f.brain
            # BUG-C2 fix: _alvo_atual agora Ã© sempre atribuÃ­do em processar().
            # Verifica se o inimigo estÃ¡ focando um aliado nosso â€” bÃ´nus de score
            # para incentivar interceptaÃ§Ã£o e proteÃ§Ã£o de aliados.
            alvo_do_inimigo = getattr(brain, '_alvo_atual', None)
            if alvo_do_inimigo and getattr(alvo_do_inimigo, 'team_id', -1) == self.parent.team_id:
                score += 1.0
        
        # v13.0: Prioridade 5 â€” Alvo designado pelo TeamCoordinator
        primary_id = self.team_orders.get("primary_target_id", 0)
        if primary_id and id(f) == primary_id:
            score += 2.5  # Big bonus para o alvo do time
        
        # v13.0: Prioridade 6 â€” Role-based targeting
        team_role = self.team_orders.get("role", "STRIKER")
        if team_role == "FLANKER":
            # Flankers preferem alvos que jÃ¡ estÃ£o sendo pressionados por aliados
            ally_intents = self.team_orders.get("ally_intents", {})
            for intent in ally_intents.values():
                if intent.target_id == id(f):
                    score += 1.0  # Aliado jÃ¡ estÃ¡ nesse, posso flanquear
                    break
        elif team_role == "SUPPORT":
            # MED-3 fix: f.alvo nÃ£o existe em Lutador â€” substituÃ­do por
            # f.brain._alvo_atual que Ã© atribuÃ­do em processar() (BUG-C2 fix).
            # Suporte prefere alvos que ameaÃ§am aliados frÃ¡geis.
            aliado_alvo = getattr(getattr(f, 'brain', None), '_alvo_atual', None)
            if aliado_alvo and getattr(aliado_alvo, 'team_id', -1) == self.parent.team_id:
                hp_aliado = aliado_alvo.vida / max(aliado_alvo.vida_max, 1)
                if hp_aliado < 0.4:
                    score += 2.0  # Proteger aliado ferido
        
        # v13.0: Penalidade se muitos aliados jÃ¡ focam esse alvo (evita overkill)
        ally_intents = self.team_orders.get("ally_intents", {})
        allies_on_target = sum(1 for i in ally_intents.values()
                               if getattr(i, 'target_id', 0) == id(f))
        if allies_on_target >= 2:
            score -= 0.5 * (allies_on_target - 1)  # Penaliza overkill
        
        return score

    # =========================================================================
    # SISTEMA DE COORDENAÃ‡ÃƒO DE TIME v13.0
    # =========================================================================
    
    def _aplicar_team_orders(self, dt, distancia, inimigo, todos_lutadores):
        """Aplica ordens do TeamCoordinator ao comportamento individual.
        
        Modifica: agressividade, alvo, posicionamento, urgÃªncia de skills.
        Integra com: personalidade, classe, emoÃ§Ãµes, spatial.
        """
        orders = self.team_orders
        if not orders or orders.get("alive_count", 1) <= 1:
            return  # Solo ou sem ordens
        
        p = self.parent
        role = orders.get("role", "STRIKER")
        tactic = orders.get("tactic", "FOCUS_FIRE")
        
        # â”€â”€ ROLE-BASED AGGRESSION MODIFIERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        
        # â”€â”€ TACTIC-BASED EMOTIONAL ADJUSTMENTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        
        # â”€â”€ DESVANTAGEM NUMÃ‰RICA AWARENESS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if orders.get("em_desvantagem", False):
            # Time em desvantagem: aumenta cautela de todos exceto berserkers
            if "BERSERKER" not in self.tracos and "DETERMINADO" not in self.tracos:
                self.hesitacao = min(0.3, self.hesitacao + 0.01 * dt * 60)
            # Mas se eu sou o carry, pressiona mais (Ã© a Ãºltima esperanÃ§a)
            if orders.get("is_carry", False):
                self.adrenalina = min(1.0, self.adrenalina + 0.03 * dt * 60)
        
        # â”€â”€ RESPOND TO CALLOUTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        for callout in orders.get("callouts", []):
            if callout.get("type") == "HELP":
                # Aliado pediu ajuda â€” se sou vanguard/support, priorizo
                if role in ("VANGUARD", "SUPPORT"):
                    self.impulso = min(0.6, self.impulso + 0.1)
            elif callout.get("type") == "TARGET":
                # Aliado marcou alvo â€” aumento prioridade mental
                pass  # JÃ¡ handled pelo scoring do _score_alvo
        
        # â”€â”€ SYNERGY AWARENESS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        
        # â”€â”€ POSITION RELATIVE TO TEAM â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

