"""Auto-generated mixin â€” see scripts/split_brain.py"""
import random
import math
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
)
from ia.personalities import (
    TODOS_TRACOS, TRACOS_AGRESSIVIDADE, TRACOS_DEFENSIVO, TRACOS_MOBILIDADE,
    TRACOS_SKILLS, TRACOS_MENTAL, TRACOS_ESPECIAIS,
    ARQUETIPO_DATA, ESTILOS_LUTA, QUIRKS, FILOSOFIAS, HUMORES,
    PERSONALIDADES_PRESETS, INSTINTOS, RITMOS, RITMO_MODIFICADORES
)

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

from ia._brain_mixin_base import _AIBrainMixinBase


class ChoreographyMixin(_AIBrainMixinBase):
    """Mixin de coreografia de combate, reaÃ§Ãµes ao oponente e callbacks."""

    
    def _processar_reacao_oponente(self, dt, distancia, inimigo):
        """Processa reaÃ§Ã£o pendente ao oponente"""
        if not self.reacao_pendente:
            return False
        
        reacao = self.reacao_pendente
        self.reacao_pendente = None
        
        # HIGH-05 fix: reaÃ§Ãµes de escape com HP crÃ­tico (â‰¤20%) nÃ£o podem falhar â€”
        # o roll de chance anterior (40% de falha base) descartava a reaÃ§Ã£o mesmo
        # em situaÃ§Ã£o de vida-ou-morte sem requeue, perdendo a janela de escape.
        hp_pct = self.parent.vida / max(self.parent.vida_max, 1)
        emergencia = hp_pct <= 0.20 and reacao in ("RECUAR", "ESQUIVAR", "CONTRA_MATAR")

        chance = 0.6
        if emergencia:
            chance = 1.0  # ReaÃ§Ã£o crÃ­tica nunca falha
        elif "ADAPTAVEL" in self.tracos:
            chance = 0.8
        elif "TEIMOSO" in self.tracos:
            chance = 0.3
        elif "FRIO" in self.tracos:
            chance = 0.7

        if random.random() > chance:
            return False
        
        acoes = {
            "CONTRA_ATAQUE": ("CONTRA_ATAQUE", lambda: setattr(self, 'excitacao', min(1.0, self.excitacao + 0.2))),
            "CONTRA_MATAR": ("MATAR", lambda: (setattr(self, 'raiva', min(1.0, self.raiva + 0.15)),
                                               setattr(self, 'adrenalina', min(1.0, self.adrenalina + 0.2)))),
            "RECUAR": ("RECUAR", None),
            "FUGIR": ("FUGIR", None),
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
            if hasattr(inimigo, 'brain') and inimigo.brain:
                self.dir_circular = -inimigo.brain.dir_circular
            self.acao_atual = "CIRCULAR"
            return True
        
        if reacao in acoes:
            self.acao_atual, callback = acoes[reacao]
            if callback:
                callback()
            return True
        
        return False

    
    def _executar_acao_sincronizada(self, acao, distancia, inimigo):
        """Executa aÃ§Ã£o sincronizada de momento cinematogrÃ¡fico v8.0"""
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
            self.acao_atual = "APROXIMAR" if distancia > 4.0 else "BLOQUEAR"
            return True
        
        if acao == "FUGIR_DRAMATICO":
            if self.raiva > 0.7 or random.random() < 0.2:
                self.acao_atual = "MATAR"
            else:
                self.acao_atual = "FUGIR"
            return True
        
        if acao == "CIRCULAR_SINCRONIZADO":
            if hasattr(inimigo, 'brain') and inimigo.brain:
                self.dir_circular = inimigo.brain.dir_circular
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
        
        # === NOVAS AÃ‡Ã•ES v8.0 ===
        if acao == "TROCAR_RAPIDO":
            # Troca rÃ¡pida de golpes - alterna entre ataque e defesa
            if random.random() < 0.6:
                self.acao_atual = random.choice(["ATAQUE_RAPIDO", "MATAR"])
            else:
                self.acao_atual = random.choice(["CONTRA_ATAQUE", "FLANQUEAR"])
            self.excitacao = min(1.0, self.excitacao + 0.15)
            return True
        
        if acao == "REAGIR_ESQUIVA":
            # Reage a uma esquiva prÃ³xima
            if random.random() < 0.5:
                self.acao_atual = "CONTRA_ATAQUE"
            else:
                self.acao_atual = "CIRCULAR"
            return True
        
        if acao == "PRESSIONAR_CONTINUO":
            # MantÃ©m pressÃ£o sobre o oponente
            self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "APROXIMAR"])
            self.pressao_aplicada = min(1.0, self.pressao_aplicada + 0.1)
            return True
        
        if acao == "RESISTIR_PRESSAO":
            # Resiste Ã  pressÃ£o do oponente
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
            self.acao_atual = random.choice(["APROXIMAR", "CIRCULAR", "COMBATE"])
            return True
        
        if acao in acoes:
            result = acoes[acao]()
            if isinstance(result, str):
                self.acao_atual = result
            return True
        
        return False

    
    def on_momento_cinematografico(self, tipo, iniciando, duracao):
        """Callback quando momento cinematogrÃ¡fico comeÃ§a/termina"""
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
        """Callback quando recebe hit de um atacante especÃ­fico"""
        self.memoria_oponente["ameaca_nivel"] = min(1.0, 
            self.memoria_oponente["ameaca_nivel"] + 0.15)
        
        if "VINGATIVO" in self.tracos:
            self.reacao_pendente = "CONTRA_MATAR"
        elif "COVARDE" in self.tracos and self.medo > 0.4:
            self.reacao_pendente = "FUGIR"
        elif "REATIVO" in self.tracos:
            self.reacao_pendente = "CONTRA_ATAQUE"


    def on_bloqueio_sucesso(self):
        """Callback quando bloqueia um ataque com sucesso.
        BUG-AI-03 fix: reseta o timer usado pelo trigger 'bloqueio_sucesso' dos instintos.
        Deve ser chamado pela simulaÃ§Ã£o ao detectar bloqueio bem-sucedido.
        """
        self.ultimo_bloqueio = 0.0
        self.confianca = min(1.0, self.confianca + 0.08)
        # Abre janela de contra-ataque pÃ³s-bloqueio
        self.janela_ataque["aberta"] = True
        self.janela_ataque["tipo"] = "pos_bloqueio"
        self.janela_ataque["qualidade"] = 0.80
        self.janela_ataque["duracao"] = 0.5
        if "CONTRA_ATAQUE_PERFEITO" in self.quirks:
            self.reacao_pendente = "CONTRA_MATAR"


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

