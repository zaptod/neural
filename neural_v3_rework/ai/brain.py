"""
=============================================================================
NEURAL FIGHTS - Cérebro da IA v11.0 WEAPON REWORK EDITION
=============================================================================
CHANGELOG v11.0:
- Reformulação da IA para Mangual: spin acumulativo, distância de zona de spin,
  detecção de zona morta expandida, arquétipo BERSERKER
- Reformulação da IA para Adagas Gêmeas: alcance ideal reduzido (0.50x),
  modo combo colado, dash agressivo para manter combo ativo
- Percepção de armas inimigas: lógica contra Mangual (entrar na zona morta)
  e contra Adagas Gêmeas (manter distância, punir aproximação)
- Bugfix: lógica de fallback para estilo de arma None/vazio
- Bugfix: detecção de alcance_agressao para Adagas Gêmeas
- Compatível com novos campos anim_* em armas.json
=============================================================================
Sistema de inteligência artificial com comportamento humano realista,
consciência espacial avançada e percepção de armas.

NOVIDADES v10.0:
- Percepção de armas inimigas (tipo, alcance, perigo)
- Cálculo de zonas de ameaça baseado na arma do oponente
- Adaptação de distância ideal baseado em matchup de armas
- Análise de vantagens/desvantagens de arma
- Comportamentos específicos contra cada tipo de arma
- Sweet spots e zonas mortas de armas

SISTEMAS v9.0 (mantidos):
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
import re as _re_arquetipo
import logging

_log = logging.getLogger("neural_ai")

from utils.config import PPM
from utils.config import (
    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,
    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,
    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,
    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,
    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,
    AI_RAND_POOL_SIZE,
)
from core.physics import normalizar_angulo
from core.skills import get_skill_data
from models import get_class_data
from ai.choreographer import CombatChoreographer
from ai.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,
    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES
)

try:
    from core.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
    WEAPON_ANALYSIS_AVAILABLE = True
except ImportError:
    WEAPON_ANALYSIS_AVAILABLE = False

try:
    from ai.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority
    SKILL_STRATEGY_AVAILABLE = True
except ImportError:
    SKILL_STRATEGY_AVAILABLE = False

try:
    from core.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

try:
    from core.arena import get_arena as _get_arena
except ImportError:
    _get_arena = None

# ── Mixin imports ──
from ai.brain_personality import PersonalityMixin
from ai.brain_perception import PerceptionMixin
from ai.brain_evasion import EvasionMixin
from ai.brain_combat import CombatMixin
from ai.brain_skills import SkillsMixin
from ai.brain_spatial import SpatialMixin
from ai.brain_emotions import EmotionsMixin
from ai.brain_choreography import ChoreographyMixin


class AIBrain(PersonalityMixin, PerceptionMixin, EvasionMixin, CombatMixin, SkillsMixin, SpatialMixin, EmotionsMixin, ChoreographyMixin):
    """
    Cérebro da IA v10.0 WEAPON PERCEPTION EDITION - Sistema de personalidade procedural com
    comportamento humano realista, inteligência de combate avançada e percepção de armas.
    """

    # MEL-AI-07: Memória de rivalidade entre lutas (modo torneio).
    # Mapeamento: id_oponente → dict com estatísticas acumuladas de confrontos anteriores.
    # Persiste durante toda a sessão do torneio (instâncias de AIBrain são recriadas a cada luta,
    # mas este dicionário de classe sobrevive).
    _historico_combates: dict = {}


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
        self.ultimo_dano_recebido = 0.0  # Valor do último dano recebido
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
        # BUG-AI-05 fix: modificador temporário de agressividade — não altera a personalidade base.
        # Situações táticas (oponente contra parede, instintos, execute_mode) ajustam aqui.
        # Decai ao longo do tempo de volta a 0 em _atualizar_emocoes.
        self._agressividade_temp_mod = 0.0
        
        # === NOVOS SISTEMAS v11.0 ===
        self.instintos = []  # Lista de instintos ativos
        self.ritmo = None    # Ritmo de batalha atual
        self.ritmo_fase_atual = 0  # Índice da fase atual
        self.ritmo_timer = 0.0     # Timer para mudança de fase
        self.ritmo_modificadores = {"agressividade": 0, "defesa": 0, "mobilidade": 0}

        # MEL-ARQ-06: flag de debug de decisão de movimento.
        # Quando True, cada frame que chamar _decidir_movimento emite um log DEBUG
        # indicando qual etapa (override, estratégia de arma ou genérica) controlou
        # a decisão e qual ação resultou.  Útil para depurar comportamentos inesperados.
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
        
        # === SISTEMA DE ESTRATÉGIA DE SKILLS v1.0 ===
        self.skill_strategy = None  # Inicializado após gerar personalidade
        
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
            # BUG-AI-01 fix: chave faltante — usada em _processar_skills_estrategico (Prioridade 3)
            "reposicionando": False,
            # BUG-AI-04 fix: chave faltante — usada em _processar_instintos
            "padrao_detectado": False,
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
            # FP-04 fix: registra ação do inimigo antes do bait para detectar mudança real
            "acao_inimigo_antes": None,
            # MEL-AI-04 fix: fase de observação pós-bait separada do tempo de execução.
            # Após o bait terminar, aguarda BAIT_JANELA_OBSERVACAO segundos observando
            # se o oponente mudou de comportamento antes de declarar sucesso/falha.
            "fase_obs": False,      # True durante a janela de observação
            "timer_obs": 0.0,       # Contador decrescente da janela de observação
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
        # BUG-AI-03 fix: atributo faltante — usado em trigger "bloqueio_sucesso" dos instintos
        self.ultimo_bloqueio = 999.0  # Segundos desde o último bloqueio bem-sucedido
        # BUG-AI-02 fix: variáveis para detecção de whiff (ataque que errou)
        self._inimigo_estava_atacando = False
        self._hits_recebidos_antes_ataque_ini = 0
        
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
        
        # === SISTEMA DE PERCEPÇÃO DE ARMAS v10.0 ===
        self.percepcao_arma = {
            # Análise da minha arma
            "minha_arma_perfil": None,          # WeaponProfile da minha arma
            "meu_alcance_efetivo": 2.0,         # Alcance real da minha arma
            "minha_velocidade_ataque": 0.5,    # Velocidade de ataque
            "meu_arco_cobertura": 90.0,         # Arco que minha arma cobre
            
            # Análise da arma inimiga
            "arma_inimigo_tipo": None,          # Tipo da arma do inimigo
            "arma_inimigo_perfil": None,        # WeaponProfile da arma inimiga
            "alcance_inimigo": 2.0,             # Alcance do inimigo
            "zona_perigo_inimigo": 2.5,         # Distância perigosa
            "ponto_cego_inimigo": None,         # Ângulo do ponto cego
            "velocidade_inimigo": 0.5,          # Velocidade de ataque
            
            # Análise de matchup
            "vantagem_alcance": 0.0,            # >0 = meu alcance maior
            "vantagem_velocidade": 0.0,         # >0 = sou mais rápido
            "vantagem_cobertura": 0.0,          # >0 = cubro mais área
            "matchup_favoravel": 0.0,           # -1 a 1, geral
            
            # Estado tático baseado em armas
            "distancia_segura": 3.0,            # Distância segura contra inimigo
            "distancia_ataque": 1.5,            # Distância ideal para atacar
            "estrategia_recomendada": "neutro", # "aproximar", "afastar", "flanquear", "trocar"
            
            # Timing
            "last_analysis_time": 0.0,          # Quando última análise foi feita
            "enemy_weapon_changed": False,      # Se arma do inimigo mudou
        }
        
        # Gera personalidade única
        self._gerar_personalidade()


    # =========================================================================
    # PROCESSAMENTO PRINCIPAL v10.0
    # =========================================================================
    
    def processar(self, dt, distancia, inimigo):
        """Processa decisões da IA a cada frame com comportamento humano"""
        p = self.parent
        self.tempo_combate += dt
        
        # QC-03: gera um pool de valores aleatórios uma vez por frame.
        # As funções do cascade (_aplicar_modificadores_*, _comportamento_estilo, etc.)
        # consomem esses valores em sequência em vez de chamar random.random() cada uma.
        # Isso reduz de ~15-25 chamadas/frame para 1, tornando o comportamento
        # mais fácil de reproduzir em debug e mais eficiente em batalhas multi-combatente.
        self._rand_pool = [random.random() for _ in range(AI_RAND_POOL_SIZE)]
        self._rand_idx = 0
        
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
        
        # === SISTEMA DE PERCEPÇÃO DE ARMAS v10.0 ===
        self._atualizar_percepcao_armas(dt, distancia, inimigo)
        
        # === NOVOS SISTEMAS v11.0 ===
        self._atualizar_ritmo(dt)
        if self._processar_instintos(dt, distancia, inimigo):
            return  # Instinto tomou controle
        
        # Hesitação humana - às vezes congela brevemente
        if self._verificar_hesitacao(dt, distancia, inimigo):
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
        
        # === PRIORIZAÇÃO DE SKILLS PARA MAGOS ===
        # Se o personagem é um caster (role de mago), prioriza skills sobre ataques básicos
        usa_skills_primeiro = False
        if self.skill_strategy is not None:
            role = self.skill_strategy.role_principal.value
            if role in ["artillery", "burst_mage", "control_mage", "summoner", "buffer", "channeler"]:
                usa_skills_primeiro = True
        
        if usa_skills_primeiro:
            # Magos: Skills primeiro, depois ataque básico
            if self._processar_skills(dt, distancia, inimigo):
                return
            if self._avaliar_e_executar_ataque(dt, distancia, inimigo):
                return
        else:
            # Melee: Ataque primeiro, skills como suporte
            if self._avaliar_e_executar_ataque(dt, distancia, inimigo):
                return
            if self._processar_skills(dt, distancia, inimigo):
                return
        
        self.timer_decisao -= dt
        if self.timer_decisao <= 0:
            self._decidir_movimento(distancia, inimigo)
            self._calcular_timer_decisao()
            self._registrar_acao()
