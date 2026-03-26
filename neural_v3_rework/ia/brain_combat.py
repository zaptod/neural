"""Auto-generated mixin â€” see scripts/split_brain.py"""
from dataclasses import dataclass
import random
import math
import logging
from typing import Any

_log = logging.getLogger("neural_ai")

from utilitarios.config import (
    AI_HP_CRITICO, AI_HP_BAIXO, AI_HP_EXECUTE,
    AI_DIST_ATAQUE_IMINENTE, AI_DIST_PAREDE_CRITICA, AI_DIST_PAREDE_AVISO,
    AI_INTERVALO_ESPACIAL, AI_INTERVALO_ARMAS,
    AI_PREVISIBILIDADE_ALTA, AI_AGRESSIVIDADE_ALTA,
    AI_MOMENTUM_POSITIVO, AI_MOMENTUM_NEGATIVO, AI_PRESSAO_ALTA,
    AI_RAND_POOL_SIZE,
)
from ia.personalities import (
    ESTILOS_LUTA, FILOSOFIAS, HUMORES,
)
from ia.behavior_profiles import get_behavior_profile, get_trait_effects, FALLBACK_PROFILE
from ia.weapon_ai import (
    FAMILIAS_CURTA_DISTANCIA,
    FAMILIAS_PRESSAO_MELEE,
    arma_eh_ranged,
    obter_metricas_arma,
    resolver_familia_arma,
)
from nucleo.armas import resolver_subtipo_orbital

try:
    from nucleo.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
except ImportError:
    pass

try:
    from ia.skill_strategy import SkillStrategySystem, CombatSituation, SkillPriority
except ImportError:
    pass

try:
    from nucleo.hitbox import HITBOX_PROFILES
except ImportError:
    HITBOX_PROFILES = {}

from ia._brain_mixin_base import _AIBrainMixinBase


@dataclass(frozen=True)
class CombatDecisionContext:
    """Snapshot do frame usado pelo caminho generico de movimento."""

    distancia: float
    roll: float
    hp_pct: float
    inimigo_hp_pct: float
    alcance_efetivo: float
    alcance_ideal: float
    parent: Any
    inimigo: Any
    minha_arma: Any
    minha_familia: str
    sou_ranged: bool
    arma_inimigo: Any
    familia_inimigo: str
    no_alcance: bool
    quase_no_alcance: bool
    longe: bool
    muito_longe: bool
    stall_approaching: bool
    pressao_ritmo: float


class CombatMixin(_AIBrainMixinBase):
    """Mixin de decisÃ£o de ataque, combos, baiting, momentum e movimento tÃ¡tico."""

    # MEL-AI-04: janela de observaÃ§Ã£o pÃ³s-bait
    BAIT_JANELA_OBSERVACAO = 0.2  # segundos de observaÃ§Ã£o apÃ³s o bait terminar

    def _obter_pacote_composto_id(self):
        perfil = getattr(self, "arquetipo_composto", None)
        if not isinstance(perfil, dict):
            return ""
        pacote = perfil.get("pacote_referencia") or {}
        if isinstance(pacote, dict):
            return str(pacote.get("id", "") or "").strip().lower()
        return ""

    def _aplicar_janela_padrao_oponente(self, inimigo, distancia):
        """Cria janelas especiais para punir habitos detectados do oponente."""
        if not hasattr(self, "_obter_padrao_dominante_oponente"):
            return None
        padrao = self._obter_padrao_dominante_oponente(inimigo)
        if not padrao:
            return None

        acao_inimiga = getattr(getattr(inimigo, "brain", None), "acao_atual", "")
        burst_orbital_pronto = getattr(inimigo, "orbital_burst_cd", 999.0) <= 0.0
        bonus_hibrido = getattr(inimigo, "transform_bonus_timer", 0.0) > 0.0

        if padrao == "entrada_agressiva" and acao_inimiga in {"APROXIMAR", "MATAR", "ESMAGAR", "PRESSIONAR"} and distancia < 4.4:
            return ("punir_entrada", 0.88, 0.45)
        if padrao == "recuo_pos_ataque" and acao_inimiga in {"RECUAR", "FUGIR", "CIRCULAR"} and distancia < 5.8:
            return ("punir_recuo", 0.82, 0.65)
        if padrao == "guarda_reativa" and acao_inimiga == "BLOQUEAR" and distancia < 4.0:
            return ("quebrar_guarda_lida", 0.78, 0.55)
        if padrao == "prepara_burst_orbital" and burst_orbital_pronto and distancia < 4.2:
            return ("punir_burst_orbital", 0.86, 0.40)
        if padrao == "troca_forma_burst" and bonus_hibrido and distancia < 4.4:
            return ("punir_troca_burst", 0.84, 0.50)
        return None

    def _resolver_plano_punish(self, tipo, distancia, inimigo):
        """Resolve opener e follow-up para janelas especiais de punish."""
        arma = getattr(getattr(self.parent, "dados", None), "arma_obj", None)
        familia = resolver_familia_arma(arma)
        forma_hibrida = int(getattr(self.parent, "transform_forma", getattr(arma, "forma_atual", 0)) or 0)

        if tipo == "punir_entrada":
            if familia == "corrente":
                return self._modular_plano_punish_por_personalidade("CONTRA_ATAQUE", "ESMAGAR", familia)
            if familia == "foco":
                return self._modular_plano_punish_por_personalidade("COMBATE", "POKE", familia)
            if familia == "orbital":
                return self._modular_plano_punish_por_personalidade("ATAQUE_RAPIDO", "COMBATE", familia)
            if familia == "hibrida":
                opener, followup = ("POKE", "MATAR") if forma_hibrida == 1 else ("CONTRA_ATAQUE", "POKE")
                return self._modular_plano_punish_por_personalidade(opener, followup, familia)
            if "CALCULISTA" in self.tracos or "REATIVO" in self.tracos:
                return self._modular_plano_punish_por_personalidade("CONTRA_ATAQUE", "PRESSIONAR", familia)
            if "BERSERKER" in self.tracos or "FURIOSO" in self.tracos:
                return self._modular_plano_punish_por_personalidade("MATAR", "ESMAGAR", familia)
            return self._modular_plano_punish_por_personalidade("CONTRA_ATAQUE", "MATAR", familia)

        if tipo == "punir_recuo":
            if familia in {"foco", "disparo", "arremesso", "orbital"}:
                return self._modular_plano_punish_por_personalidade("POKE", "COMBATE", familia)
            if familia == "corrente":
                return self._modular_plano_punish_por_personalidade("PRESSIONAR", "MATAR", familia)
            return self._modular_plano_punish_por_personalidade("APROXIMAR", "MATAR", familia)

        if tipo == "quebrar_guarda_lida":
            if familia == "corrente":
                return self._modular_plano_punish_por_personalidade("FLANQUEAR", "ESMAGAR", familia)
            if familia == "foco":
                return self._modular_plano_punish_por_personalidade("CIRCULAR", "POKE", familia)
            if "CALCULISTA" in self.tracos or "OPORTUNISTA" in self.tracos:
                return self._modular_plano_punish_por_personalidade("FLANQUEAR", "ATAQUE_RAPIDO", familia)
            return self._modular_plano_punish_por_personalidade("MATAR", "PRESSIONAR", familia)

        if tipo == "punir_burst_orbital":
            if familia in {"foco", "orbital"}:
                return self._modular_plano_punish_por_personalidade("CIRCULAR", "POKE", familia)
            return self._modular_plano_punish_por_personalidade("ATAQUE_RAPIDO", "COMBATE", familia)

        if tipo == "punir_troca_burst":
            if familia == "hibrida":
                opener, followup = ("POKE", "COMBATE") if forma_hibrida == 1 else ("PRESSIONAR", "MATAR")
                return self._modular_plano_punish_por_personalidade(opener, followup, familia)
            if familia == "foco":
                return self._modular_plano_punish_por_personalidade("POKE", "COMBATE", familia)
            if "PACIENTE" in self.tracos or "CALCULISTA" in self.tracos:
                return self._modular_plano_punish_por_personalidade("POKE", "PRESSIONAR", familia)
            return self._modular_plano_punish_por_personalidade("PRESSIONAR", "MATAR", familia)

        return self._modular_plano_punish_por_personalidade(None, None, familia)

    def _modular_plano_punish_por_personalidade(self, opener, followup, familia):
        """Dá assinatura dramatica ao punish a partir do arquétipo, humor e tracos."""
        arquetipo = (self.arquetipo or "").upper()
        humor = (self.humor or "").upper()
        timer = 0.45
        boost_excitacao = 0.08
        boost_adrenalina = 0.04
        assinatura_agil = arquetipo in {"ASSASSINO", "NINJA", "SOMBRA", "DUELISTA"} or "FLANQUEADOR" in self.tracos or "ACROBATA" in self.tracos
        assinatura_guardia = arquetipo in {"GUARDIAO", "PALADINO", "CAVALEIRO", "SAMURAI"} or "DETERMINADO" in self.tracos or "FOCADO" in self.tracos
        assinatura_furia = arquetipo in {"BERSERKER", "VIKING"} or "BERSERKER" in self.tracos or "FURIOSO" in self.tracos or humor in {"FURIOSO", "EUFORICO", "EXTASE", "BERSERK"}
        assinatura_fria = "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos or humor in {"CALMO", "FOCADO", "GLACIAL"}

        if assinatura_furia:
            if opener in {"POKE", "FLANQUEAR", "CIRCULAR", "CONTRA_ATAQUE"}:
                opener = "MATAR"
            if followup in {None, "POKE", "COMBATE", "FLANQUEAR", "MATAR"}:
                followup = "ESMAGAR" if familia in {"corrente", "lamina", "hibrida"} else "PRESSIONAR"
            timer = 0.30
            boost_excitacao = 0.16
            boost_adrenalina = 0.12

        elif assinatura_agil:
            if opener in {"MATAR", "CONTRA_ATAQUE"}:
                opener = "ATAQUE_RAPIDO"
            if followup in {"MATAR", "ESMAGAR", "COMBATE"}:
                followup = "FLANQUEAR"
            timer = 0.34
            boost_excitacao = 0.12

        elif assinatura_guardia:
            if opener == "MATAR":
                opener = "CONTRA_ATAQUE"
            if followup in {"FLANQUEAR", "POKE"}:
                followup = "COMBATE"
            timer = 0.50
            boost_adrenalina = 0.06

        elif assinatura_fria:
            if opener == "MATAR":
                opener = "CONTRA_ATAQUE"
            if followup in {"ESMAGAR", "MATAR"} and familia not in {"corrente"}:
                followup = "POKE" if familia in {"foco", "orbital", "disparo", "arremesso"} else "COMBATE"
            timer = 0.56
            boost_excitacao = 0.05

        return self._modular_plano_punish_por_estado_emocional(
            opener, followup, timer, boost_excitacao, boost_adrenalina, familia
        )

    def _modular_plano_punish_por_estado_emocional(self, opener, followup, timer, boost_excitacao, boost_adrenalina, familia):
        """Ajusta o tom do punish conforme emoção e momentum do momento."""
        hp_pct = self.parent.vida / max(self.parent.vida_max, 1)
        confianca = getattr(self, "confianca", 0.5)
        medo = getattr(self, "medo", 0.0)
        raiva = getattr(self, "raiva", 0.0)
        excitacao = getattr(self, "excitacao", 0.0)
        momentum = getattr(self, "momentum", 0.0)
        humor = (self.humor or "").upper()
        arquetipo = (self.arquetipo or "").upper()
        assinatura_agil = arquetipo in {"ASSASSINO", "NINJA", "SOMBRA", "DUELISTA"} or "FLANQUEADOR" in self.tracos or "ACROBATA" in self.tracos

        if medo > 0.62 and confianca < 0.48:
            if opener in {"MATAR", "ESMAGAR", "ATAQUE_RAPIDO"}:
                opener = "CONTRA_ATAQUE" if familia not in {"foco", "orbital", "disparo", "arremesso"} else "POKE"
            if followup in {"ESMAGAR", "MATAR", "PRESSIONAR", "FLANQUEAR"}:
                followup = "COMBATE" if familia not in {"foco", "orbital"} else "POKE"
            timer = max(timer, 0.52)
            boost_excitacao = min(boost_excitacao, 0.06)

        if (raiva > 0.72 or excitacao > 0.78 or momentum > 0.45 or humor in {"EUFORICO", "EXTASE", "FURIOSO", "BERSERK"}) and hp_pct > 0.22:
            if assinatura_agil:
                # Se a fúria já promoveu o opener para MATAR, não desfaça esse pico dramático.
                if opener in {"APROXIMAR", "CONTRA_ATAQUE", "COMBATE", "POKE", "CIRCULAR"}:
                    opener = "ATAQUE_RAPIDO"
                if followup in {None, "COMBATE", "POKE", "MATAR", "ESMAGAR", "PRESSIONAR"}:
                    followup = "FLANQUEAR"
            else:
                if opener in {"APROXIMAR", "CONTRA_ATAQUE", "COMBATE", "POKE", "CIRCULAR"}:
                    opener = "MATAR" if familia not in {"foco", "orbital"} else "COMBATE"
                if followup in {None, "COMBATE", "POKE", "FLANQUEAR"}:
                    followup = "ESMAGAR" if familia in {"corrente", "lamina", "hibrida"} else "PRESSIONAR"
            timer = min(timer, 0.32)
            boost_excitacao = max(boost_excitacao, 0.14)
            boost_adrenalina = max(boost_adrenalina, 0.10)

        if confianca > 0.78 and momentum > 0.20 and medo < 0.35:
            if followup in {"COMBATE", "POKE"} and familia not in {"foco", "orbital"}:
                followup = "PRESSIONAR"
            timer = min(timer, 0.40)
            boost_excitacao = max(boost_excitacao, 0.10)

        memoria_cena = getattr(self, "memoria_cena", {})
        tipo_cena = memoria_cena.get("tipo") if isinstance(memoria_cena, dict) else None
        intensidade_cena = memoria_cena.get("intensidade", 0.0) if isinstance(memoria_cena, dict) else 0.0

        if tipo_cena == "clash":
            if opener in {"CONTRA_ATAQUE", "COMBATE", "CIRCULAR"}:
                opener = "ESMAGAR" if familia in {"corrente", "lamina", "hibrida"} else "MATAR"
            if followup in {None, "POKE", "COMBATE"}:
                followup = "MATAR"
            timer = min(timer, 0.30)
            boost_excitacao = max(boost_excitacao, 0.16 + intensidade_cena * 0.06)

        elif tipo_cena == "final_showdown":
            if opener in {"APROXIMAR", "CONTRA_ATAQUE", "POKE"}:
                opener = "MATAR" if familia not in {"foco", "orbital"} else "COMBATE"
            if followup in {None, "COMBATE", "POKE", "FLANQUEAR"}:
                followup = "ESMAGAR" if familia in {"corrente", "lamina", "hibrida"} else "PRESSIONAR"
            timer = min(timer, 0.28)
            boost_adrenalina = max(boost_adrenalina, 0.14)

        elif tipo_cena == "sequencia_perfeita":
            if followup in {"COMBATE", "POKE"}:
                followup = "PRESSIONAR"
            timer = min(timer, 0.33)
            boost_excitacao = max(boost_excitacao, 0.14)

        elif tipo_cena == "dominando":
            if followup in {"COMBATE", "POKE"} and familia not in {"foco", "orbital"}:
                followup = "PRESSIONAR"
            boost_excitacao = max(boost_excitacao, 0.12)

        elif tipo_cena in {"leitura_perfeita", "virada"}:
            if opener == "MATAR":
                opener = "CONTRA_ATAQUE" if familia not in {"foco", "orbital"} else "POKE"
            if followup in {"MATAR", "ESMAGAR"} and familia not in {"corrente"}:
                followup = "COMBATE" if familia not in {"foco", "orbital"} else "POKE"
            timer = max(timer, 0.48)

        elif tipo_cena in {"humilhado", "quase_morte"}:
            if opener in {"MATAR", "ESMAGAR"}:
                opener = "CONTRA_ATAQUE" if familia not in {"foco", "orbital"} else "POKE"
            if followup in {"MATAR", "ESMAGAR", "PRESSIONAR"}:
                followup = "COMBATE" if familia not in {"foco", "orbital"} else "POKE"
            timer = max(timer, 0.54)
            boost_excitacao = min(boost_excitacao, 0.07)

        return self._modular_plano_punish_por_rivalidade(
            opener, followup, timer, boost_excitacao, boost_adrenalina, familia
        )

    def _modular_plano_punish_por_rivalidade(self, opener, followup, timer, boost_excitacao, boost_adrenalina, familia):
        """Dá um tom mais pessoal ao punish quando existe vínculo forte com o rival."""
        alvo = getattr(self, "_alvo_atual", None)
        if alvo is None:
            return opener, followup, timer, boost_excitacao, boost_adrenalina

        rivalidade = self._calcular_pressao_rivalidade(alvo) if hasattr(self, "_calcular_pressao_rivalidade") else {}
        dominante = rivalidade.get("dominante")
        intensidade = rivalidade.get("intensidade", 0.0)
        if not dominante or intensidade < 0.18:
            return opener, followup, timer, boost_excitacao, boost_adrenalina

        if dominante == "respeito":
            if opener in {"MATAR", "ESMAGAR"}:
                opener = "CONTRA_ATAQUE" if familia not in {"foco", "orbital"} else "POKE"
            if followup in {"MATAR", "ESMAGAR", "PRESSIONAR"}:
                followup = "COMBATE" if familia not in {"foco", "orbital"} else "POKE"
            timer = max(timer, 0.48 + intensidade * 0.08)
            boost_excitacao = max(boost_excitacao, 0.06)

        elif dominante == "vinganca":
            if opener in {"COMBATE", "POKE", "APROXIMAR", "CONTRA_ATAQUE"}:
                opener = "MATAR" if familia not in {"foco", "orbital"} else "PRESSIONAR"
            if followup in {None, "COMBATE", "POKE", "FLANQUEAR"}:
                followup = "ESMAGAR" if familia in {"corrente", "lamina", "hibrida"} else "PRESSIONAR"
            timer = min(timer, 0.34)
            boost_excitacao = max(boost_excitacao, 0.15 + intensidade * 0.05)
            boost_adrenalina = max(boost_adrenalina, 0.10)

        elif dominante == "obsessao":
            if opener in {"APROXIMAR", "COMBATE"}:
                opener = "FLANQUEAR" if familia not in {"corrente"} else "PRESSIONAR"
            if followup in {"COMBATE", "POKE", None}:
                followup = "PRESSIONAR"
            timer = min(timer, 0.38)
            boost_excitacao = max(boost_excitacao, 0.12)

        elif dominante == "caca":
            if opener in {"POKE", "CIRCULAR", "COMBATE"}:
                opener = "APROXIMAR" if familia in {"disparo", "arremesso", "foco", "orbital"} else "PRESSIONAR"
            if followup in {"POKE", "COMBATE", None}:
                followup = "MATAR" if familia not in {"foco", "orbital"} else "PRESSIONAR"
            timer = min(timer, 0.36)
            boost_excitacao = max(boost_excitacao, 0.11)

        return opener, followup, timer, boost_excitacao, boost_adrenalina

    def _agendar_followup_forcado(self, opener, followup, origem, timer_followup=0.45, boost_excitacao=0.0, boost_adrenalina=0.0):
        if not followup:
            return
        combo = self.combo_state
        combo["em_combo"] = True
        combo["pode_followup"] = True
        combo["timer_followup"] = timer_followup
        combo["ultimo_tipo_ataque"] = opener
        combo["followup_forcado"] = followup
        combo["origem_followup"] = origem
        self.excitacao = min(1.0, self.excitacao + boost_excitacao)
        self.adrenalina = min(1.0, self.adrenalina + boost_adrenalina)

    
    # =========================================================================
    # SISTEMA DE ATAQUE INTELIGENTE v8.0
    # =========================================================================
    
    def _avaliar_e_executar_ataque(self, dt, distancia, inimigo):
        """Avalia se deve atacar e como - v12.2 MELHORADO"""
        p = self.parent
        janela = self.janela_ataque
        combo = self.combo_state
        
        # Calcula alcance efetivo baseado na arma
        alcance_efetivo = self._calcular_alcance_efetivo()
        no_alcance = distancia <= alcance_efetivo * 1.1  # 10% de margem
        
        # FIX: Stall detection â€” se estÃ¡ em aÃ§Ã£o ofensiva hÃ¡ muito tempo sem
        # realmente atacar (p.atacando=False), libera o loop para _decidir_movimento
        acoes_ofensivas_stall = {"MATAR", "ESMAGAR", "COMBATE", "PRESSIONAR", "ATAQUE_RAPIDO"}
        if p.atacando:
            self._tempo_sem_ataque_efetivo = 0.0
        elif self.acao_atual in acoes_ofensivas_stall:
            self._tempo_sem_ataque_efetivo += dt
        else:
            self._tempo_sem_ataque_efetivo = 0.0
        
        if self._tempo_sem_ataque_efetivo > 1.5:
            # Stall: aÃ§Ã£o ofensiva mas sem golpe efetivo hÃ¡ 1.5s â€” forÃ§a aproximaÃ§Ã£o
            self._tempo_sem_ataque_efetivo = 0.0
            self.acao_atual = "APROXIMAR"
            return False  # Libera para _decidir_movimento no prÃ³ximo frame
        
        # Se estÃ¡ em combo, tenta continuar
        if combo["em_combo"] and combo["pode_followup"]:
            if self._tentar_followup(distancia, inimigo):
                return True
        
        # === ATAQUE DIRETO SE NO ALCANCE E NÃƒO ATACANDO ===
        if no_alcance and not p.atacando:
            # Behavior profile drive attack chance
            bp = getattr(self, '_behavior_profile', FALLBACK_PROFILE)
            chance_base = bp.get("ataque_min_chance", 0.5) + bp.get("ataque_bonus_chance", 0.0)
            memoria = getattr(self, "memoria_adaptativa", {})
            chance_base += memoria.get("vies_agressao", 0.0) * 0.16
            chance_base += memoria.get("vies_pressao", 0.0) * 0.10
            chance_base += memoria.get("vies_contra_ataque", 0.0) * 0.06
            chance_base -= max(0.0, memoria.get("vies_cautela", 0.0)) * 0.18
            
            # Aumenta chance se inimigo com pouca vida (execute zone)
            inimigo_hp_r = inimigo.vida / max(inimigo.vida_max, 1)
            if inimigo_hp_r < bp.get("execute_threshold", 0.25):
                chance_base = min(0.95, chance_base + 0.30)
            
            # Momentum
            chance_base += self.momentum * 0.15
            
            # Emotion modifiers amplified by profile
            if self.raiva > 0.5:
                chance_base += self.raiva * 0.2 * bp.get("raiva_ganho_mult", 1.0)
            if self.medo > 0.5:
                chance_base -= self.medo * 0.15 * bp.get("medo_ganho_mult", 1.0)
            
            chance_base = max(0.05, min(0.95, chance_base))
            
            if random.random() < chance_base:
                self._executar_ataque(distancia, inimigo)
                return True
        
        # Verifica se tem janela de oportunidade
        if janela["aberta"]:
            # Calcula se vale a pena atacar
            chance_ataque = janela["qualidade"]
            memoria = getattr(self, "memoria_adaptativa", {})
            chance_ataque += memoria.get("vies_contra_ataque", 0.0) * 0.12
            chance_ataque += memoria.get("vies_pressao", 0.0) * 0.08
            chance_ataque -= max(0.0, memoria.get("vies_cautela", 0.0)) * 0.10
            
            # Modificadores de distÃ¢ncia
            if distancia > alcance_efetivo * 1.5:
                chance_ataque *= 0.3  # Longe demais
            elif distancia > alcance_efetivo:
                chance_ataque *= 0.7  # Um pouco longe
            elif distancia < p.alcance_ideal * 0.5:
                chance_ataque *= 1.3  # Muito perto, aproveita
            
            # Personalidade
            if "OPORTUNISTA" in self.tracos:
                chance_ataque *= 1.3
            if "CALCULISTA" in self.tracos:
                chance_ataque *= 1.2 if janela["qualidade"] > 0.7 else 0.8
            if "PACIENTE" in self.tracos:
                chance_ataque *= 0.9 if janela["qualidade"] < 0.8 else 1.1
            
            # Momentum
            chance_ataque += self.momentum * 0.2
            
            # EmoÃ§Ãµes
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
        
        # Escolhe aÃ§Ã£o baseado no tipo de janela
        if tipo == "pos_ataque":
            # Contra-ataque rÃ¡pido
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
        
        elif tipo == "pos_bloqueio":
            # CB-02: contra-ataque imediato apÃ³s bloqueio/parry bem-sucedido
            self.acao_atual = "CONTRA_ATAQUE"
            self.confianca = min(1.0, self.confianca + 0.12)
            return True

        elif tipo == "punir_entrada":
            opener, followup, timer_followup, boost_excitacao, boost_adrenalina = self._resolver_plano_punish(tipo, distancia, inimigo)
            self.acao_atual = opener or "CONTRA_ATAQUE"
            self._agendar_followup_forcado(self.acao_atual, followup, tipo, timer_followup, boost_excitacao, boost_adrenalina)
            self.excitacao = min(1.0, self.excitacao + 0.12)
            return True

        elif tipo == "punir_recuo":
            opener, followup, timer_followup, boost_excitacao, boost_adrenalina = self._resolver_plano_punish(tipo, distancia, inimigo)
            self.acao_atual = opener or ("PRESSIONAR" if distancia > self.parent.alcance_ideal else "APROXIMAR")
            self._agendar_followup_forcado(self.acao_atual, followup, tipo, timer_followup, boost_excitacao, boost_adrenalina)
            return True

        elif tipo == "quebrar_guarda_lida":
            opener, followup, timer_followup, boost_excitacao, boost_adrenalina = self._resolver_plano_punish(tipo, distancia, inimigo)
            self.acao_atual = opener or ("FLANQUEAR" if "CALCULISTA" in self.tracos else "MATAR")
            self._agendar_followup_forcado(self.acao_atual, followup, tipo, timer_followup, boost_excitacao, boost_adrenalina)
            return True

        elif tipo == "punir_burst_orbital":
            opener, followup, timer_followup, boost_excitacao, boost_adrenalina = self._resolver_plano_punish(tipo, distancia, inimigo)
            self.acao_atual = opener or ("CIRCULAR" if self.cd_pulo > 0 else "ATAQUE_RAPIDO")
            self._agendar_followup_forcado(self.acao_atual, followup, tipo, timer_followup, boost_excitacao, boost_adrenalina)
            return True

        elif tipo == "punir_troca_burst":
            opener, followup, timer_followup, boost_excitacao, boost_adrenalina = self._resolver_plano_punish(tipo, distancia, inimigo)
            self.acao_atual = opener or ("POKE" if "PACIENTE" in self.tracos or "CALCULISTA" in self.tracos else "PRESSIONAR")
            self._agendar_followup_forcado(self.acao_atual, followup, tipo, timer_followup, boost_excitacao, boost_adrenalina)
            self.adrenalina = min(1.0, self.adrenalina + 0.08)
            return True
        
        return False

    
    def _executar_ataque(self, distancia, inimigo):
        """Executa um ataque baseado na distÃ¢ncia e situaÃ§Ã£o - v12.2"""
        p = self.parent
        
        # Usa alcance efetivo calculado
        alcance_efetivo = self._calcular_alcance_efetivo()
        
        # Escolhe tipo de ataque baseado na distÃ¢ncia relativa ao alcance
        if distancia <= alcance_efetivo * 0.5:
            # Muito perto - ataque rÃ¡pido
            self.acao_atual = "ATAQUE_RAPIDO"
        elif distancia <= alcance_efetivo:
            # Dentro do alcance - ataque normal
            if random.random() < 0.6:
                self.acao_atual = "MATAR"
            else:
                self.acao_atual = "ATAQUE_RAPIDO"
        elif distancia <= alcance_efetivo * 1.3:
            # Quase no alcance - pressiona
            if random.random() < 0.5:
                self.acao_atual = "PRESSIONAR"
            else:
                self.acao_atual = "APROXIMAR"
        else:
            # Longe - aproxima
            self.acao_atual = "APROXIMAR"
        
        # Seta flag de ataque diretamente (nÃ£o existe mÃ©todo iniciar_ataque)
        if distancia <= alcance_efetivo * 1.1:
            # O ataque Ã© executado via executar_ataques() em entities.py
            # Basta garantir que a aÃ§Ã£o seja ofensiva
            if self.acao_atual not in ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "PRESSIONAR", "CONTRA_ATAQUE", "POKE"]:
                self.acao_atual = "MATAR"

    
    def _tentar_followup(self, distancia, inimigo):
        """Tenta continuar combo"""
        combo = self.combo_state

        if combo["timer_followup"] <= 0:
            combo["em_combo"] = False
            combo["pode_followup"] = False
            self._proximo_skill_combo = None  # limpa payload pendente
            return False

        # BUG-C1 fix: consome o payload estratÃ©gico do combo (sk2) antes de
        # cair na lÃ³gica genÃ©rica de movimento.  _proximo_skill_combo Ã© gravado
        # em _processar_skills_estrategico (Prioridade 4) quando a IA executa
        # o setup do combo (sk1).  Aqui entregamos o payload (sk2).
        sk2_pendente = getattr(self, '_proximo_skill_combo', None)
        if sk2_pendente and combo.get("pode_followup"):
            if distancia <= self.parent.alcance_ideal + 2.0:
                if self._executar_skill_por_nome(sk2_pendente):
                    _log.debug(
                        "[COMBO] %s entregou payload '%s'",
                        self.parent.dados.nome, sk2_pendente
                    )
                    self._proximo_skill_combo = None
                    combo["em_combo"] = False
                    combo["pode_followup"] = False
                    combo["hits_combo"] += 1
                    return True
            # Fora de alcance ou skill falhou â€” cancela o combo sem punir
            self._proximo_skill_combo = None
            combo["em_combo"] = False
            combo["pode_followup"] = False
            return False

        followup_forcado = combo.get("followup_forcado")
        if followup_forcado and combo.get("pode_followup"):
            alcance_combo = max(self.parent.alcance_ideal * 1.35, self._calcular_alcance_efetivo() * 1.15)
            if followup_forcado not in {"APROXIMAR", "CIRCULAR", "RECUAR", "POKE", "COMBATE"} and distancia > alcance_combo:
                self.acao_atual = "APROXIMAR"
            else:
                self.acao_atual = followup_forcado
            combo["followup_forcado"] = None
            combo["origem_followup"] = None
            combo["hits_combo"] += 1
            combo["ultimo_tipo_ataque"] = self.acao_atual
            combo["timer_followup"] = 0.35
            self.excitacao = min(1.0, self.excitacao + 0.06)
            return True

        # Determina prÃ³ximo ataque do combo (caminho genÃ©rico â€” sem payload estratÃ©gico)
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
        
        # Verifica distÃ¢ncia
        if distancia > self.parent.alcance_ideal + 1.5:
            combo["em_combo"] = False
            return False
        
        self.acao_atual = proximo
        combo["hits_combo"] += 1
        combo["ultimo_tipo_ataque"] = proximo
        combo["timer_followup"] = 0.4  # Janela para prÃ³ximo hit
        
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
            combo["followup_forcado"] = None
            combo["origem_followup"] = None


    def _processar_baiting(self, dt, distancia, inimigo):
        """Processa sistema de baiting/fintas"""
        bait = self.bait_state

        # --- FASE DE OBSERVAÃ‡ÃƒO PÃ“S-BAIT (MEL-AI-04) ---
        # ApÃ³s a finta terminar, aguarda uma janela curta (0.2s) para capturar
        # somente reaÃ§Ãµes imediatas do oponente â€” nÃ£o comportamento agressivo padrÃ£o.
        if bait["fase_obs"]:
            bait["timer_obs"] -= dt
            if bait["timer_obs"] <= 0:
                bait["fase_obs"] = False
                return self._executar_contra_bait(distancia, inimigo)
            return True  # MantÃ©m controle durante a janela de observaÃ§Ã£o

        # Atualiza timer principal do bait
        if bait["ativo"]:
            bait["timer"] -= dt
            # FP-04 fix: registra aÃ§Ã£o do inimigo no inÃ­cio do bait para comparar depois
            if bait.get("acao_inimigo_antes") is None and hasattr(inimigo, 'brain') and inimigo.brain:
                bait["acao_inimigo_antes"] = inimigo.brain.acao_atual
            if bait["timer"] <= 0:
                # MEL-AI-04: nÃ£o avalia imediatamente â€” inicia janela de observaÃ§Ã£o
                bait["ativo"] = False
                bait["fase_obs"] = True
                bait["timer_obs"] = self.BAIT_JANELA_OBSERVACAO
                return True
        
        # Decide se inicia bait
        if not bait["ativo"]:
            chance_bait = 0.0
            padrao_dominante = self._obter_padrao_dominante_oponente(inimigo) if hasattr(self, "_obter_padrao_dominante_oponente") else None
            
            # Fatores que aumentam chance de bait
            if "TRICKSTER" in self.tracos:
                chance_bait += 0.15
            if "CALCULISTA" in self.tracos:
                chance_bait += 0.08
            if "OPORTUNISTA" in self.tracos:
                chance_bait += 0.05
            
            # Situacionais
            if self.momentum < AI_MOMENTUM_NEGATIVO:  # Perdendo, tenta enganar
                chance_bait += 0.1
            if self.leitura_oponente["agressividade_percebida"] > 0.7:
                chance_bait += 0.1  # Oponente agressivo, fÃ¡cil de baitar
            if padrao_dominante in {"entrada_agressiva", "guarda_reativa", "recuo_pos_ataque"}:
                chance_bait += 0.12
            
            if 3.0 < distancia < 6.0 and random.random() < chance_bait:
                if padrao_dominante == "entrada_agressiva":
                    tipo_bait = random.choice(["abertura_falsa", "hesitacao_falsa", "abertura_falsa"])
                elif padrao_dominante == "guarda_reativa":
                    tipo_bait = random.choice(["abertura_falsa", "recuo_falso"])
                elif padrao_dominante == "recuo_pos_ataque":
                    tipo_bait = random.choice(["recuo_falso", "hesitacao_falsa"])
                else:
                    tipo_bait = random.choice(["recuo_falso", "abertura_falsa", "hesitacao_falsa"])
                bait["ativo"] = True
                bait["tipo"] = tipo_bait
                bait["timer"] = random.uniform(0.3, 0.6)
                # FP-04 fix: salva aÃ§Ã£o atual do inimigo para detectar mudanÃ§a real
                bait["acao_inimigo_antes"] = (
                    inimigo.brain.acao_atual
                    if hasattr(inimigo, 'brain') and inimigo.brain else None
                )
                
                # Executa inÃ­cio do bait
                if tipo_bait == "recuo_falso":
                    self.acao_atual = "RECUAR"
                elif tipo_bait == "abertura_falsa":
                    self.acao_atual = "BLOQUEAR"
                elif tipo_bait == "hesitacao_falsa":
                    self.acao_atual = "CIRCULAR"
                
                return True
        
        return False

    
    def _executar_contra_bait(self, distancia, inimigo):
        """Executa contra-ataque apÃ³s bait bem sucedido"""
        bait = self.bait_state
        bait["ativo"] = False
        
        # FP-04 fix: verifica mudanÃ§a REAL de comportamento do oponente.
        # Antes: contava como sucesso qualquer comportamento agressivo (incluindo o padrÃ£o).
        # Agora: sÃ³ conta se o inimigo mudou de uma aÃ§Ã£o neutra/defensiva para agressiva
        # dentro da janela do bait.
        oponente_caiu = False
        if hasattr(inimigo, 'brain') and inimigo.brain:
            acao_antes = bait.get("acao_inimigo_antes")
            acao_agora = inimigo.brain.acao_atual
            acoes_agressivas = {"APROXIMAR", "MATAR", "ESMAGAR", "PRESSIONAR"}
            acoes_neutras_defensivas = {
                "CIRCULAR", "BLOQUEAR", "RECUAR", "FUGIR", "COMBATE",
                "FLANQUEAR", "NEUTRO", None
            }
            # Sucesso = estava neutro/defensivo E agora estÃ¡ agressivo (mudou por causa do bait)
            if acao_antes in acoes_neutras_defensivas and acao_agora in acoes_agressivas:
                oponente_caiu = True
        bait["acao_inimigo_antes"] = None  # Limpa para o prÃ³ximo bait
        
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
    # SISTEMA DE MOMENTUM E PRESSÃƒO v8.0
    # =========================================================================
    
    def _atualizar_momentum(self, dt, distancia, inimigo):
        """Atualiza momentum da luta"""
        # Momentum aumenta quando:
        # - DÃ¡ hits
        # - Oponente recua
        # - HP do oponente cai
        # Momentum diminui quando:
        # - Recebe hits
        # - VocÃª recua
        # - Seu HP cai
        
        # Decay natural para o neutro (frame-rate independent)
        self.momentum *= 0.995 ** (dt * 60)
        
        # Baseado em hits recentes
        diff_hits = self.hits_dados_recente - self.hits_recebidos_recente
        self.momentum += diff_hits * 0.05
        
        # Baseado em HP
        p = self.parent
        meu_hp = p.vida / max(p.vida_max, 1)
        ini_hp = inimigo.vida / max(inimigo.vida_max, 1)
        hp_diff = meu_hp - ini_hp
        self.momentum += hp_diff * 0.02
        
        # Baseado em pressÃ£o
        if distancia < 3.0:
            if self.acao_atual in ["MATAR", "PRESSIONAR", "ESMAGAR"]:
                self.pressao_aplicada = min(1.0, self.pressao_aplicada + dt * 0.5)
            else:
                self.pressao_aplicada = max(0.0, self.pressao_aplicada - dt * 0.3)
        else:
            self.pressao_aplicada = max(0.0, self.pressao_aplicada - dt * 0.5)
        
        # PressÃ£o recebida
        if hasattr(inimigo, 'brain') and inimigo.brain:
            ai_ini = inimigo.brain
            if distancia < 3.0 and ai_ini.acao_atual in ["MATAR", "PRESSIONAR", "ESMAGAR"]:
                self.pressao_recebida = min(1.0, self.pressao_recebida + dt * 0.5)
            else:
                self.pressao_recebida = max(0.0, self.pressao_recebida - dt * 0.3)
        
        # Clamp momentum
        self.momentum = max(-1.0, min(1.0, self.momentum))

    
    # =========================================================================
    # SISTEMA DE JANELAS DE OPORTUNIDADE v8.0
    # =========================================================================
    
    def _atualizar_janelas_oportunidade(self, dt, distancia, inimigo):
        """Detecta janelas de oportunidade para atacar"""
        janela = self.janela_ataque
        
        # Decrementa duraÃ§Ã£o da janela atual
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
        
        # 1. PÃ³s-ataque do oponente (recovery)
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
        if hasattr(inimigo, 'brain') and inimigo.brain:
            if inimigo.brain.acao_atual in ["RECUAR", "FUGIR"]:
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

        janela_padrao = self._aplicar_janela_padrao_oponente(inimigo, distancia)
        if janela_padrao:
            tipo_padrao, qualidade_padrao, duracao_padrao = janela_padrao
            if qualidade_padrao > qualidade:
                nova_janela = True
                tipo_janela = tipo_padrao
                qualidade = qualidade_padrao
                duracao = duracao_padrao
        
        # Atualiza janela se encontrou uma melhor
        if nova_janela and qualidade > janela.get("qualidade", 0):
            janela["aberta"] = True
            janela["tipo"] = tipo_janela
            janela["qualidade"] = qualidade
            janela["duracao"] = duracao

    def _criar_contexto_combate_generico(self, distancia, roll, hp_pct, inimigo_hp_pct, alcance_efetivo, alcance_ideal, inimigo):
        """Agrupa o estado usado pelo caminho generico de movimento."""
        p = self.parent
        minha_arma = getattr(getattr(p, "dados", None), "arma_obj", None)
        arma_inimigo = getattr(getattr(inimigo, "dados", None), "arma_obj", None)
        return CombatDecisionContext(
            distancia=distancia,
            roll=roll,
            hp_pct=hp_pct,
            inimigo_hp_pct=inimigo_hp_pct,
            alcance_efetivo=alcance_efetivo,
            alcance_ideal=alcance_ideal,
            parent=p,
            inimigo=inimigo,
            minha_arma=minha_arma,
            minha_familia=resolver_familia_arma(minha_arma),
            sou_ranged=arma_eh_ranged(minha_arma),
            arma_inimigo=arma_inimigo,
            familia_inimigo=resolver_familia_arma(arma_inimigo),
            no_alcance=distancia <= alcance_efetivo,
            quase_no_alcance=distancia <= alcance_efetivo * 1.3,
            longe=distancia > alcance_efetivo * 1.5,
            muito_longe=distancia > alcance_efetivo * 2.5,
            stall_approaching=self.tempo_desde_hit > 3.0 and not p.atacando,
            pressao_ritmo=max(0.0, min(1.0, float(getattr(self, "pressao_ritmo", 0.0) or 0.0))),
        )

    def _votar_movimento(self, pesos, acao, peso):
        pesos[acao] = pesos.get(acao, 0.0) + peso

    def _votar_base_generica(self, ctx, pesos):
        if ctx.inimigo_hp_pct < 0.25 and ctx.no_alcance:
            self._votar_movimento(pesos, "MATAR", 1.5)
            self._votar_movimento(pesos, "ESMAGAR", 1.0)
            if ctx.stall_approaching:
                self._votar_movimento(pesos, "APROXIMAR", 1.0)
        elif ctx.no_alcance:
            if ctx.inimigo_hp_pct < 0.3:
                self._votar_movimento(pesos, "MATAR", 1.2)
                self._votar_movimento(pesos, "ESMAGAR", 0.8)
            else:
                for acao, peso in (
                    ("MATAR", 0.6),
                    ("ATAQUE_RAPIDO", 0.5),
                    ("COMBATE", 0.4),
                    ("FLANQUEAR", 0.4),
                    ("CIRCULAR", 0.3),
                    ("PRESSIONAR", 0.3),
                    ("CONTRA_ATAQUE", 0.2),
                ):
                    self._votar_movimento(pesos, acao, peso)
            if ctx.stall_approaching:
                self._votar_movimento(pesos, "APROXIMAR", 0.8)
                self._votar_movimento(pesos, "PRESSIONAR", 0.6)
        elif ctx.quase_no_alcance:
            for acao, peso in (
                ("APROXIMAR", 0.7),
                ("PRESSIONAR", 0.5),
                ("FLANQUEAR", 0.4),
                ("COMBATE", 0.3),
                ("POKE", 0.2),
                ("CIRCULAR", 0.2),
            ):
                self._votar_movimento(pesos, acao, peso)
        elif ctx.longe or ctx.muito_longe:
            self._votar_movimento(pesos, "APROXIMAR", 1.0)
            self._votar_movimento(pesos, "PRESSIONAR", 0.4)

        if ctx.familia_inimigo == "disparo" and not ctx.sou_ranged:
            if ctx.distancia > ctx.alcance_efetivo * 0.9:
                self._votar_movimento(pesos, "APROXIMAR", 1.3)
                self._votar_movimento(pesos, "FLANQUEAR", 0.9)
                self._votar_movimento(pesos, "PRESSIONAR", 0.8)
            else:
                self._votar_movimento(pesos, "MATAR", 0.7)
                self._votar_movimento(pesos, "PRESSIONAR", 0.5)
            if ctx.hp_pct > 0.25:
                pesos["RECUAR"] = pesos.get("RECUAR", 0.0) * 0.55
                pesos["FUGIR"] = pesos.get("FUGIR", 0.0) * 0.45

    def _votar_profile_traits_generico(self, ctx, pesos):
        bp = getattr(self, "_behavior_profile", FALLBACK_PROFILE)

        if ctx.hp_pct < bp.get("recuar_threshold", 0.30):
            if bp.get("nunca_recua", False):
                self._votar_movimento(pesos, "MATAR", 2.5)
                self._votar_movimento(pesos, "ESMAGAR", 1.5)
            else:
                self._votar_movimento(pesos, "RECUAR", 1.5 * bp.get("retreat_weight", 1.0))
                self._votar_movimento(pesos, "FUGIR", 0.8 * bp.get("retreat_weight", 1.0))
        elif ctx.hp_pct < 0.50 and bp.get("nunca_recua", False):
            self._votar_movimento(pesos, "MATAR", 1.5)

        if ctx.inimigo_hp_pct < bp.get("execute_threshold", 0.25):
            self._votar_movimento(pesos, "MATAR", 2.0 * bp.get("pressao_mult", 1.0))
            self._votar_movimento(pesos, "ESMAGAR", 1.0 * bp.get("pressao_mult", 1.0))
        elif ctx.inimigo_hp_pct < 0.50:
            self._votar_movimento(pesos, "PRESSIONAR", 1.0 * bp.get("pressao_mult", 1.0))

        if bp.get("perseguir_sempre", False) and ctx.distancia > ctx.alcance_efetivo * 1.2:
            self._votar_movimento(pesos, "APROXIMAR", 1.5 * bp.get("approach_weight", 1.0))
            self._votar_movimento(pesos, "PRESSIONAR", 0.8 * bp.get("approach_weight", 1.0))

        for trait in self.tracos:
            effects = get_trait_effects(trait)
            for acao, peso in effects.items():
                self._votar_movimento(pesos, acao, peso)

        if "COVARDE" in self.tracos and ctx.hp_pct < bp.get("recuar_threshold", 0.30) + 0.10:
            if self.vezes_que_fugiu > 4:
                self._votar_movimento(pesos, "MATAR", 2.0)
                self.raiva = 0.9
            else:
                self._votar_movimento(pesos, "FUGIR", 2.0 * bp.get("retreat_weight", 1.0))
        if "BERSERKER" in self.tracos and ctx.hp_pct < 0.45:
            self._votar_movimento(pesos, "MATAR", (1.0 - ctx.hp_pct) * 3.0)
        if "FINALIZADOR_NATO" in self.tracos and ctx.inimigo_hp_pct < 0.25:
            self._votar_movimento(pesos, "MATAR", 2.0)
        if "CLUTCH_PLAYER" in self.tracos and ctx.hp_pct < 0.30:
            self._votar_movimento(pesos, "MATAR", 1.5)
            self._votar_movimento(pesos, "CONTRA_ATAQUE", 1.0)
        if "TILTER" in self.tracos and ctx.hp_pct < 0.30:
            self._votar_movimento(pesos, "FUGIR", 0.8)
            self._votar_movimento(pesos, "RECUAR", 0.5)
        if "PHOENIX" in self.tracos and ctx.hp_pct < 0.20:
            self._votar_movimento(pesos, "MATAR", 2.5)
        if "ULTIMO_SUSPIRO" in self.tracos and ctx.hp_pct < 0.10:
            self._votar_movimento(pesos, "MATAR", 3.0)
            self._votar_movimento(pesos, "ESMAGAR", 2.0)
        if "UNDERDOG" in self.tracos and ctx.hp_pct < ctx.inimigo_hp_pct - 0.2:
            self._votar_movimento(pesos, "MATAR", 1.2)
            self._votar_movimento(pesos, "PRESSIONAR", 0.8)
        if "MOMENTUM_RIDER" in self.tracos and self.momentum > 0.3:
            self._votar_movimento(pesos, "MATAR", 1.0)
            self._votar_movimento(pesos, "PRESSIONAR", 0.8)
        if "MASOQUISTA" in self.tracos:
            dano_bonus = (1.0 - ctx.hp_pct) * 2.0
            self._votar_movimento(pesos, "MATAR", dano_bonus * 0.5)
            self._votar_movimento(pesos, "PRESSIONAR", dano_bonus * 0.3)
        if "KAMIKAZE" in self.tracos:
            self._votar_movimento(pesos, "MATAR", 3.0)
        if "EMOTIVO" in self.tracos:
            self._votar_movimento(pesos, "MATAR", self.raiva * 0.6)
            self._votar_movimento(pesos, "FUGIR", self.medo * 0.6)

        return bp

    def _votar_estilo_emocao_generico(self, ctx, pesos, bp):
        estilo_ativo = getattr(self, "_estilo_override", None) or self.estilo_luta
        estilo_data = ESTILOS_LUTA.get(estilo_ativo, ESTILOS_LUTA["BALANCED"])
        agressividade = estilo_data.get("agressividade_base", 0.6)
        agressividade = min(1.0, agressividade + min(0.2, self.tempo_combate / 60.0))
        if ctx.inimigo_hp_pct < 0.3:
            agressividade = min(1.0, agressividade + 0.25)
        if ctx.hp_pct < 0.25 and "BERSERKER" not in self.tracos:
            agressividade = max(0.3, agressividade - 0.1)

        if ctx.distancia < ctx.alcance_ideal * 0.7:
            self._votar_movimento(pesos, estilo_data["acao_perto"], agressividade * 0.8)
        elif ctx.distancia > ctx.alcance_efetivo * 1.3:
            self._votar_movimento(pesos, estilo_data["acao_longe"], agressividade * 0.8)
        else:
            self._votar_movimento(pesos, estilo_data["acao_medio"], agressividade * 0.8)

        for acao_key, mult_key in [
            ("APROXIMAR", "approach_weight"),
            ("RECUAR", "retreat_weight"),
            ("FUGIR", "retreat_weight"),
            ("FLANQUEAR", "flank_weight"),
            ("POKE", "poke_weight"),
        ]:
            if acao_key in pesos:
                pesos[acao_key] = pesos[acao_key] * bp.get(mult_key, 1.0)

        if "FRIO" not in self.tracos and self.raiva > 0.4:
            self._votar_movimento(pesos, "MATAR", self.raiva * 0.6 * bp.get("raiva_ganho_mult", 1.0))
            self._votar_movimento(pesos, "ESMAGAR", self.raiva * 0.4 * bp.get("raiva_ganho_mult", 1.0))
        if "FRIO" not in self.tracos and self.medo > 0.4:
            self._votar_movimento(pesos, "RECUAR", self.medo * 0.5 * bp.get("medo_ganho_mult", 1.0))
            self._votar_movimento(pesos, "FUGIR", self.medo * 0.3 * bp.get("medo_ganho_mult", 1.0))

        humor_data = HUMORES.get(self.humor, HUMORES["CALMO"])
        mod_humor = humor_data.get("mod_agressividade", 0.0)
        if mod_humor > 0.15:
            self._votar_movimento(pesos, "MATAR", mod_humor * 0.5)
            self._votar_movimento(pesos, "APROXIMAR", mod_humor * 0.3)
        elif mod_humor < -0.25:
            self._votar_movimento(pesos, "COMBATE", abs(mod_humor) * 0.4)
            self._votar_movimento(pesos, "RECUAR", abs(mod_humor) * 0.2)

        if self._rand() < 0.2:
            filosofia_data = FILOSOFIAS.get(self.filosofia, FILOSOFIAS["EQUILIBRIO"])
            for acao in filosofia_data["preferencia_acao"]:
                self._votar_movimento(pesos, acao, 0.3)

        if self.momentum > AI_MOMENTUM_POSITIVO:
            self._votar_movimento(pesos, "MATAR", 0.3)
            self._votar_movimento(pesos, "PRESSIONAR", 0.2)
        elif self.momentum < AI_MOMENTUM_NEGATIVO:
            self._votar_movimento(pesos, "RECUAR", 0.2)
            self._votar_movimento(pesos, "COMBATE", 0.2)
            self._votar_movimento(pesos, "CIRCULAR", 0.1)

        if ctx.pressao_ritmo > 0.05:
            self._votar_movimento(pesos, "APROXIMAR", 0.22 + ctx.pressao_ritmo * 0.32)
            self._votar_movimento(pesos, "PRESSIONAR", 0.16 + ctx.pressao_ritmo * 0.28)
            if ctx.distancia <= ctx.alcance_efetivo * 1.15:
                self._votar_movimento(pesos, "MATAR", 0.08 + ctx.pressao_ritmo * 0.18)
            pesos["RECUAR"] = pesos.get("RECUAR", 0.0) * max(0.18, 1.0 - ctx.pressao_ritmo * 0.7)
            pesos["FUGIR"] = pesos.get("FUGIR", 0.0) * max(0.12, 1.0 - ctx.pressao_ritmo * 0.8)

    def _votar_leitura_oponente_generico(self, ctx, pesos):
        leitura = self.leitura_oponente
        if leitura["previsibilidade"] > AI_PREVISIBILIDADE_ALTA:
            tend_esq = leitura.get("tendencia_esquerda", 0.5)
            if self._dir_circular_cd <= 0:
                if tend_esq > 0.60:
                    self.dir_circular = 1
                    self._dir_circular_cd = 0.4
                elif tend_esq < 0.40:
                    self.dir_circular = -1
                    self._dir_circular_cd = 0.4

            tempo_reacao = getattr(self, "timer_decisao", 0.2)
            vel_in = getattr(ctx.inimigo, "vel", (0.0, 0.0))
            pos_in = getattr(ctx.inimigo, "pos", (0.0, 0.0))
            self._pos_interceptacao = (
                pos_in[0] + vel_in[0] * tempo_reacao,
                pos_in[1] + vel_in[1] * tempo_reacao,
            )

            if leitura["agressividade_percebida"] > 0.6:
                self._votar_movimento(pesos, "CONTRA_ATAQUE", 0.6)
            elif leitura.get("frequencia_pulo", 0) > 0.35 and ctx.distancia < 5.0:
                self._votar_movimento(pesos, "COMBATE", 0.5)
            else:
                self._votar_movimento(pesos, "PRESSIONAR", 0.4)
        else:
            self._pos_interceptacao = None

        if leitura["agressividade_percebida"] > AI_AGRESSIVIDADE_ALTA and ("REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos):
            self._votar_movimento(pesos, "CONTRA_ATAQUE", 0.4)
        if leitura.get("frequencia_pulo", 0) > 0.4:
            self._votar_movimento(pesos, "COMBATE", 0.25)
        if ctx.distancia < 4.0:
            tend = leitura.get("tendencia_esquerda", 0.5)
            if self._dir_circular_cd <= 0:
                if tend > 0.65:
                    self.dir_circular = 1
                    self._dir_circular_cd = 0.4
                elif tend < 0.35:
                    self.dir_circular = -1
                    self._dir_circular_cd = 0.4

        padrao_dominante = self._obter_padrao_dominante_oponente(ctx.inimigo) if hasattr(self, "_obter_padrao_dominante_oponente") else None
        if padrao_dominante == "entrada_agressiva":
            self._votar_movimento(pesos, "CONTRA_ATAQUE", 0.45)
            self._votar_movimento(pesos, "CIRCULAR", 0.22)
        elif padrao_dominante == "recuo_pos_ataque":
            self._votar_movimento(pesos, "PRESSIONAR", 0.35)
            self._votar_movimento(pesos, "APROXIMAR", 0.24)
        elif padrao_dominante == "guarda_reativa":
            self._votar_movimento(pesos, "FLANQUEAR", 0.30)
            self._votar_movimento(pesos, "CIRCULAR", 0.18)
        elif padrao_dominante == "prepara_burst_orbital":
            self._votar_movimento(pesos, "CIRCULAR", 0.38)
            self._votar_movimento(pesos, "RECUAR", 0.24)
        elif padrao_dominante == "troca_forma_burst":
            self._votar_movimento(pesos, "CIRCULAR", 0.22)
            self._votar_movimento(pesos, "POKE", 0.18)

    def _votar_modificadores_externos_generico(self, ctx, pesos):
        acao_anterior = self.acao_atual
        self._aplicar_modificadores_espaciais(ctx.distancia, ctx.inimigo)
        sugestao_espacial = self.acao_atual
        self.acao_atual = acao_anterior
        if sugestao_espacial not in ("NEUTRO",) and sugestao_espacial != acao_anterior:
            self._votar_movimento(pesos, sugestao_espacial, 0.5)

        self._aplicar_modificadores_armas(ctx.distancia, ctx.inimigo)
        sugestao_arma = self.acao_atual
        self.acao_atual = acao_anterior
        if sugestao_arma not in ("NEUTRO",) and sugestao_arma != acao_anterior:
            self._votar_movimento(pesos, sugestao_arma, 0.45)

    def _votar_time_generico(self, ctx, pesos):
        orders = getattr(self, "team_orders", {})
        team_role = orders.get("role", "")
        team_tactic = orders.get("tactic", "")
        team_center = orders.get("team_center", (0, 0))
        has_team = orders.get("alive_count", 1) > 1

        if has_team and team_role:
            if team_role == "VANGUARD":
                self._votar_movimento(pesos, "APROXIMAR", 0.5)
                self._votar_movimento(pesos, "PRESSIONAR", 0.5)
                self._votar_movimento(pesos, "MATAR", 0.3)
                self._votar_movimento(pesos, "BLOQUEAR", 0.2)
                pesos["RECUAR"] = pesos.get("RECUAR", 0.0) * 0.4
                pesos["FUGIR"] = pesos.get("FUGIR", 0.0) * 0.2
            elif team_role == "FLANKER":
                self._votar_movimento(pesos, "FLANQUEAR", 0.8)
                self._votar_movimento(pesos, "CIRCULAR", 0.4)
                if ctx.no_alcance:
                    self._votar_movimento(pesos, "ATAQUE_RAPIDO", 0.5)
                else:
                    self._votar_movimento(pesos, "APROXIMAR", 0.3)
                pesos["PRESSIONAR"] = pesos.get("PRESSIONAR", 0.0) * 0.5
            elif team_role == "ARTILLERY":
                if ctx.distancia < ctx.alcance_efetivo * 0.6:
                    self._votar_movimento(pesos, "RECUAR", 1.2)
                    self._votar_movimento(pesos, "FUGIR", 0.6)
                elif ctx.distancia < ctx.alcance_efetivo:
                    self._votar_movimento(pesos, "RECUAR", 0.5)
                    self._votar_movimento(pesos, "CIRCULAR", 0.4)
                else:
                    self._votar_movimento(pesos, "COMBATE", 0.5)
                pesos["APROXIMAR"] = pesos.get("APROXIMAR", 0.0) * 0.3
                pesos["MATAR"] = pesos.get("MATAR", 0.0) * 0.5
            elif team_role == "SUPPORT":
                dist_to_center = math.hypot(
                    ctx.parent.pos[0] - team_center[0], ctx.parent.pos[1] - team_center[1]
                ) if team_center != (0, 0) else 999
                if dist_to_center > 6.0:
                    self._votar_movimento(pesos, "RECUAR", 0.6)
                    self._votar_movimento(pesos, "CIRCULAR", 0.4)
                else:
                    self._votar_movimento(pesos, "COMBATE", 0.5)
                    self._votar_movimento(pesos, "CIRCULAR", 0.3)
                pesos["MATAR"] = pesos.get("MATAR", 0.0) * 0.4
                pesos["ESMAGAR"] = pesos.get("ESMAGAR", 0.0) * 0.3
            elif team_role == "CONTROLLER":
                if ctx.distancia < ctx.alcance_ideal * 0.6:
                    self._votar_movimento(pesos, "RECUAR", 0.6)
                    self._votar_movimento(pesos, "CIRCULAR", 0.5)
                elif ctx.distancia < ctx.alcance_efetivo:
                    self._votar_movimento(pesos, "COMBATE", 0.5)
                    self._votar_movimento(pesos, "CIRCULAR", 0.4)
                    self._votar_movimento(pesos, "FLANQUEAR", 0.3)
                else:
                    self._votar_movimento(pesos, "APROXIMAR", 0.3)
                    self._votar_movimento(pesos, "CIRCULAR", 0.3)
            elif team_role == "STRIKER":
                if ctx.no_alcance:
                    self._votar_movimento(pesos, "MATAR", 0.4)
                    self._votar_movimento(pesos, "ESMAGAR", 0.3)
                else:
                    self._votar_movimento(pesos, "APROXIMAR", 0.4)
                    self._votar_movimento(pesos, "PRESSIONAR", 0.3)

            pacote_id = self._obter_pacote_composto_id()
            if pacote_id == "vanguarda_brutal":
                pesos["MATAR"] = pesos.get("MATAR", 0.0) * 0.74
                pesos["ESMAGAR"] = pesos.get("ESMAGAR", 0.0) * 0.80
                self._votar_movimento(pesos, "COMBATE", 0.28)
                self._votar_movimento(pesos, "CIRCULAR", 0.18)
                if ctx.distancia > ctx.alcance_efetivo * 0.92:
                    pesos["PRESSIONAR"] = pesos.get("PRESSIONAR", 0.0) * 0.82
                else:
                    pesos["PRESSIONAR"] = pesos.get("PRESSIONAR", 0.0) * 0.76

            if team_tactic == "RETREAT_REGROUP":
                self._votar_movimento(pesos, "RECUAR", 1.0)
                self._votar_movimento(pesos, "CIRCULAR", 0.5)
                pesos["MATAR"] = pesos.get("MATAR", 0.0) * 0.3
                pesos["APROXIMAR"] = pesos.get("APROXIMAR", 0.0) * 0.3
            elif team_tactic == "FULL_AGGRO":
                self._votar_movimento(pesos, "MATAR", 0.5)
                self._votar_movimento(pesos, "APROXIMAR", 0.4)
                self._votar_movimento(pesos, "PRESSIONAR", 0.3)
            elif team_tactic == "KITE_AND_POKE":
                if ctx.distancia < ctx.alcance_efetivo * 0.8:
                    self._votar_movimento(pesos, "RECUAR", 0.5)
                self._votar_movimento(pesos, "CIRCULAR", 0.3)
                self._votar_movimento(pesos, "POKE", 0.3)
            elif team_tactic == "PINCER_ATTACK":
                if team_role == "FLANKER":
                    self._votar_movimento(pesos, "FLANQUEAR", 0.8)
                else:
                    self._votar_movimento(pesos, "PRESSIONAR", 0.4)
                    self._votar_movimento(pesos, "APROXIMAR", 0.3)
            elif team_tactic == "PROTECT_CARRY":
                if orders.get("is_carry", False):
                    self._votar_movimento(pesos, "MATAR", 0.4)
                    self._votar_movimento(pesos, "PRESSIONAR", 0.3)
                elif team_role in ("VANGUARD", "SUPPORT"):
                    self._votar_movimento(pesos, "COMBATE", 0.3)
                    self._votar_movimento(pesos, "CIRCULAR", 0.3)
            elif team_tactic == "BAIT_AND_PUNISH":
                if team_role in ("CONTROLLER", "FLANKER"):
                    self._votar_movimento(pesos, "CIRCULAR", 0.4)
                    self._votar_movimento(pesos, "RECUAR", 0.3)
                else:
                    self._votar_movimento(pesos, "COMBATE", 0.3)

    def _compensar_matchup_generico(self, ctx, pesos, bp):
        perfil_agressivo = (
            bp.get("approach_weight", 1.0)
            + bp.get("pressao_mult", 1.0)
            + bp.get("combo_tendencia", 1.0)
        )
        perfil_defensivo = (
            bp.get("retreat_weight", 1.0)
            + bp.get("bloqueio_mult", 1.0)
            + bp.get("paciencia_mult", 1.0)
        )

        if ctx.minha_familia in (FAMILIAS_CURTA_DISTANCIA | {"haste"}) and perfil_defensivo > perfil_agressivo * 1.12:
            pesos["RECUAR"] = pesos.get("RECUAR", 0.0) * 0.62
            pesos["FUGIR"] = pesos.get("FUGIR", 0.0) * 0.52
            self._votar_movimento(pesos, "APROXIMAR", 0.35)
            self._votar_movimento(pesos, "PRESSIONAR", 0.28)
            if ctx.minha_familia == "orbital":
                self._votar_movimento(pesos, "COMBATE", 0.42)
                votos_anti_passivo = 0.24 if ctx.distancia > ctx.alcance_efetivo * 1.1 else 0.0
                if votos_anti_passivo > 0:
                    self._votar_movimento(pesos, "APROXIMAR", votos_anti_passivo)

        if ctx.minha_familia in {"disparo", "arremesso", "foco"} and perfil_agressivo > perfil_defensivo * 1.20:
            pesos["MATAR"] = pesos.get("MATAR", 0.0) * 0.84
            pesos["ESMAGAR"] = pesos.get("ESMAGAR", 0.0) * 0.78
            self._votar_movimento(pesos, "COMBATE", 0.25)
            self._votar_movimento(pesos, "CIRCULAR", 0.20)
            if ctx.distancia < ctx.alcance_ideal * 0.75:
                self._votar_movimento(pesos, "RECUAR", 0.28)
            elif ctx.distancia > ctx.alcance_efetivo * 1.05:
                self._votar_movimento(pesos, "APROXIMAR", 0.18)

        if ctx.familia_inimigo == "disparo" and not ctx.sou_ranged and ctx.minha_familia in FAMILIAS_PRESSAO_MELEE:
            if perfil_agressivo < perfil_defensivo:
                self._votar_movimento(pesos, "FLANQUEAR", 0.24)
                self._votar_movimento(pesos, "CIRCULAR", 0.12)
                pesos["APROXIMAR"] = pesos.get("APROXIMAR", 0.0) * 0.92

    def _aplicar_anti_repeticao_generico(self, ctx, pesos):
        if len(self.historico_acoes) >= 3:
            ultimas_3 = self.historico_acoes[-3:]
            acao_rep = self.acao_atual
            if ultimas_3.count(acao_rep) >= 2:
                pesos[acao_rep] = pesos.get(acao_rep, 0.0) * 0.5

        if self.circular_consecutivo >= 3:
            pesos["CIRCULAR"] = pesos.get("CIRCULAR", 0.0) * 0.1
            if ctx.no_alcance:
                self._votar_movimento(pesos, "COMBATE", 0.8)
                self._votar_movimento(pesos, "PRESSIONAR", 0.5)
            else:
                self._votar_movimento(pesos, "APROXIMAR", 0.7)
                self._votar_movimento(pesos, "FLANQUEAR", 0.5)

    def _escolher_acao_generica(self, ctx, pesos, debug=False):
        if not pesos:
            return None

        acao_escolhida = max(pesos, key=pesos.__getitem__)
        top_items = sorted(pesos.items(), key=lambda item: item[1], reverse=True)
        if len(top_items) > 1:
            max_w = max(0.01, top_items[0][1])
            contenders = [(acao, peso) for acao, peso in top_items[:4] if peso >= max_w * 0.72]

            variancia_base = 0.14
            if "Caótico" in self.tracos or "IMPRUDENTE" in self.tracos:
                variancia_base += 0.08
            if "Contemplativo" in self.tracos or "PRUDENTE" in self.tracos:
                variancia_base -= 0.06
            variancia_base = max(0.05, min(0.30, variancia_base))

            if len(contenders) >= 2 and random.random() < variancia_base:
                total = sum(max(0.01, peso) for _, peso in contenders)
                cursor = random.random() * total
                acumulado = 0.0
                for action_name, weight in contenders:
                    acumulado += max(0.01, weight)
                    if cursor <= acumulado:
                        acao_escolhida = action_name
                        break

        if debug:
            top3 = sorted(pesos.items(), key=lambda item: item[1], reverse=True)[:3]
            _log.debug("[DECISAO] %s â†’ genÃ©rico | top3=%s", ctx.parent.dados.nome, top3)
        return acao_escolhida


    # =========================================================================
    # MOVIMENTO v8.0 COM INTELIGÃŠNCIA HUMANA
    # =========================================================================
    
    # =========================================================================
    # MEL-AI-02 â€” SISTEMA DE DECISÃƒO DE MOVIMENTO v13.0 (STRATEGY PATTERN)
    # =========================================================================
    # `_decidir_movimento` agora Ã© um dispatcher puro: aplica overrides globais,
    # delega para o mÃ©todo correto de acordo com o tipo de arma e, para o caminho
    # genÃ©rico, aplica o sistema de pesos acumulativos (MEL-AI-03).
    #
    # Cada tipo de arma tem seu prÃ³prio mÃ©todo `_estrategia_*`, facilitando:
    #   - Adicionar novos tipos sem inflar o mÃ©todo principal
    #   - Testar e ajustar balanÃ§o por arma de forma isolada
    #   - Rastrear qual estratÃ©gia tomou controle (DEBUG_AI_DECISIONS)

    def _decidir_movimento(self, distancia, inimigo):
        """Dispatcher de decisÃ£o de movimento â€” v13.0 Strategy Pattern"""
        p = self.parent
        roll = random.random()
        hp_pct = p.vida / max(p.vida_max, 1)
        inimigo_hp_pct = inimigo.vida / max(inimigo.vida_max, 1)

        alcance_efetivo = self._calcular_alcance_efetivo()
        alcance_ideal   = p.alcance_ideal
        no_alcance      = distancia <= alcance_efetivo
        muito_perto     = distancia < alcance_ideal * 0.5

        debug = getattr(self, 'DEBUG_AI_DECISIONS', False)

        # Tipo da arma atual (usado por overrides tÃ¡ticos e estratÃ©gia por arma).
        arma = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None

        # Anti-kite hard override: melee contra arco deve fechar distÃ¢ncia.
        # Reduz o risco de passividade causada por blocos defensivos/eventos reativos.
        minha_familia = resolver_familia_arma(arma)
        sou_ranged = arma_eh_ranged(arma)
        inimigo_arma = getattr(getattr(inimigo, 'dados', None), 'arma_obj', None)
        familia_inimigo = resolver_familia_arma(inimigo_arma)
        pressao_ritmo = max(0.0, min(1.0, float(getattr(self, "pressao_ritmo", 0.0) or 0.0)))
        if familia_inimigo == "disparo" and not sou_ranged and hp_pct > 0.22 and distancia > alcance_efetivo * 0.85:
            self.acao_atual = "APROXIMAR" if roll < 0.65 else ("FLANQUEAR" if roll < 0.9 else "PRESSIONAR")
            if debug:
                _log.debug("[DECISAO] %s â†’ override ANTI_KITE_BOW â†’ %s", p.dados.nome, self.acao_atual)
            return

        # â”€â”€ OVERRIDES GLOBAIS DE ALTA PRIORIDADE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if hasattr(p, 'modo_adrenalina') and p.modo_adrenalina:
            self.acao_atual = "MATAR"
            if debug: _log.debug("[DECISAO] %s â†’ override ADRENALINA â†’ MATAR", p.dados.nome)
            return

        if hasattr(p, 'estamina') and p.estamina < 15:
            self.acao_atual = "ATAQUE_RAPIDO" if (no_alcance and roll < 0.4) else "RECUAR"
            if debug: _log.debug("[DECISAO] %s â†’ override ESTAMINA_BAIXA â†’ %s", p.dados.nome, self.acao_atual)
            return

        if self.modo_berserk:
            self.acao_atual = "MATAR"
            if debug: _log.debug("[DECISAO] %s â†’ override BERSERK â†’ MATAR", p.dados.nome)
            return

        if self.modo_defensivo:
            self.acao_atual = "CONTRA_ATAQUE" if (no_alcance and roll < 0.3) else ("RECUAR" if muito_perto else "COMBATE")
            if debug: _log.debug("[DECISAO] %s â†’ override DEFENSIVO â†’ %s", p.dados.nome, self.acao_atual)
            return

        if self.medo > 0.75 and "DETERMINADO" not in self.tracos and "FRIO" not in self.tracos:
            if pressao_ritmo >= 0.55:
                self.acao_atual = "COMBATE" if no_alcance else ("PRESSIONAR" if distancia <= alcance_efetivo * 1.25 else "APROXIMAR")
                if debug:
                    _log.debug("[DECISAO] %s â†’ override MEDO QUEBRADO PELA PRESSAO â†’ %s", p.dados.nome, self.acao_atual)
            else:
                self.acao_atual = "ATAQUE_RAPIDO" if (no_alcance and roll < 0.25) else "FUGIR"
                if debug:
                    _log.debug("[DECISAO] %s â†’ override MEDO â†’ %s", p.dados.nome, self.acao_atual)
            return

        # â”€â”€ DELEGAÃ‡ÃƒO POR TIPO DE ARMA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        arma      = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        if minha_familia in {"disparo", "arremesso", "foco"}:
            self._estrategia_ranged(distancia, roll, alcance_efetivo, alcance_ideal, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s â†’ estratÃ©gia RANGED â†’ %s", p.dados.nome, self.acao_atual)
            return

        if minha_familia == "corrente":
            self._estrategia_corrente(distancia, roll, alcance_efetivo, alcance_ideal, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s â†’ estratÃ©gia CORRENTE â†’ %s", p.dados.nome, self.acao_atual)
            return

        if minha_familia == "dupla":
            self._estrategia_dupla(distancia, roll, alcance_efetivo, alcance_ideal, hp_pct, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s â†’ estratÃ©gia DUPLA â†’ %s", p.dados.nome, self.acao_atual)
            return

        if minha_familia == "orbital":
            self._estrategia_orbital(distancia, roll, alcance_efetivo, alcance_ideal, hp_pct, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s â†’ estratÃ©gia ORBITAL â†’ %s", p.dados.nome, self.acao_atual)
            return

        if minha_familia == "hibrida":
            self._estrategia_hibrida(distancia, roll, alcance_efetivo, alcance_ideal, hp_pct, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s â†’ estratÃ©gia HIBRIDA â†’ %s", p.dados.nome, self.acao_atual)
            return

        # â”€â”€ CAMINHO GENÃ‰RICO (MEL-AI-03: pesos acumulativos) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._estrategia_generica(distancia, roll, hp_pct, inimigo_hp_pct,
                                  alcance_efetivo, alcance_ideal, inimigo, debug)


    # â”€â”€ ESTRATÃ‰GIAS POR TIPO DE ARMA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _estrategia_ranged(self, distancia, roll, alcance_efetivo, alcance_ideal, inimigo_hp_pct, arma):
        """Estratégia de posicionamento para famílias ranged com ritmo próprio."""
        familia = resolver_familia_arma(arma)
        perigosamente_perto = distancia < alcance_ideal * 0.42
        perto_demais = distancia < alcance_ideal * 0.72
        distancia_boa = alcance_ideal * 0.72 <= distancia <= alcance_efetivo
        longe_demais = distancia > alcance_efetivo

        if familia == "disparo":
            carregando = bool(getattr(self.parent, "bow_charging", False))
            if perigosamente_perto:
                self.acao_atual = random.choice(["FUGIR", "RECUAR", "CIRCULAR"])
            elif perto_demais:
                self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "FLANQUEAR"])
            elif distancia_boa:
                self.acao_atual = random.choice(["COMBATE", "POKE", "MATAR"] if carregando else ["COMBATE", "POKE", "PRESSIONAR"])
            elif longe_demais:
                self.acao_atual = random.choice(["APROXIMAR", "POKE"])
            else:
                self.acao_atual = random.choice(["COMBATE", "POKE", "MATAR"])
            return

        if familia == "arremesso":
            consec = float(getattr(self.parent, "throw_consecutive", 0.0))
            ritmo_rajada = consec >= 2.0
            if perigosamente_perto:
                self.acao_atual = random.choice(["RECUAR", "ATAQUE_RAPIDO", "CIRCULAR"])
            elif perto_demais:
                self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR", "RECUAR"] if ritmo_rajada else ["PRESSIONAR", "ATAQUE_RAPIDO", "FLANQUEAR"])
            elif distancia_boa:
                self.acao_atual = random.choice(["PRESSIONAR", "COMBATE", "FLANQUEAR"] if ritmo_rajada else ["MATAR", "PRESSIONAR", "COMBATE"])
            elif longe_demais:
                self.acao_atual = "APROXIMAR"
            else:
                self.acao_atual = random.choice(["PRESSIONAR", "COMBATE", "FLANQUEAR"])
            return

        # foco
        orbes_orbitando = len([o for o in getattr(self.parent, "buffer_orbes", []) if getattr(o, "ativo", False) and getattr(o, "estado", "") == "orbitando"])
        if perigosamente_perto and orbes_orbitando == 0:
            self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "FLANQUEAR"])
        elif perto_demais:
            self.acao_atual = random.choice(["COMBATE", "CIRCULAR", "RECUAR"] if orbes_orbitando >= 2 else ["CIRCULAR", "FLANQUEAR", "RECUAR"])
        elif distancia_boa:
            if inimigo_hp_pct < 0.28:
                self.acao_atual = random.choice(["MATAR", "COMBATE", "PRESSIONAR"])
            else:
                self.acao_atual = random.choice(["COMBATE", "POKE", "PRESSIONAR"] if orbes_orbitando >= 2 else ["COMBATE", "FLANQUEAR", "POKE"])
        elif longe_demais:
            self.acao_atual = random.choice(["APROXIMAR", "POKE"])
        else:
            self.acao_atual = random.choice(["COMBATE", "PRESSIONAR", "POKE"])


    def _estrategia_corrente(self, distancia, roll, alcance_efetivo, alcance_ideal,
                              inimigo_hp_pct, arma):
        """EstratÃ©gia para armas de corrente (Mangual v3.1 + genÃ©rico)."""
        arma_estilo = getattr(arma, 'estilo', '') if arma else ''
        try:
            perfil_hb       = HITBOX_PROFILES.get("Corrente", {})
            zona_morta_ratio = perfil_hb.get("min_range_ratio", 0.25)
        except (KeyError, AttributeError):
            zona_morta_ratio = 0.25
        zona_morta = alcance_efetivo * zona_morta_ratio

        if arma_estilo == "Mangual":
            zona_ideal_max = alcance_efetivo * 0.75
            zona_longa_max = alcance_efetivo * 1.10
            zona_morta     = alcance_efetivo * 0.30   # sobrescreve ratio para mangual

            em_zona_morta = distancia < zona_morta
            em_zona_ideal = zona_morta <= distancia <= zona_ideal_max
            em_zona_longa = zona_ideal_max < distancia <= zona_longa_max

            slam_combo = getattr(self.parent, 'mangual_slam_combo', 0)
            em_combo   = slam_combo >= 2

            if em_zona_morta:
                urgencia = 1.0 - (distancia / max(zona_morta, 0.01))
                self.acao_atual = "RECUAR" if (urgencia > 0.4 or roll < 0.88) else random.choice(["RECUAR", "COMBATE", "RECUAR"])
                if hasattr(self.parent, 'mangual_slam_combo'):
                    self.parent.mangual_slam_combo = 0
            elif em_zona_ideal:
                if inimigo_hp_pct < AI_HP_EXECUTE:
                    self.acao_atual = random.choice(["MATAR", "ESMAGAR", "MATAR"])
                elif em_combo:
                    self.acao_atual = random.choice(["ESMAGAR", "MATAR"]) if roll < 0.70 else random.choice(["FLANQUEAR", "CIRCULAR"])
                    if hasattr(self.parent, 'mangual_slam_combo'):
                        self.parent.mangual_slam_combo = min(5, slam_combo + 1)
                else:
                    if roll < 0.55:
                        self.acao_atual = random.choice(["ESMAGAR", "MATAR", "ESMAGAR"])
                    elif roll < 0.80:
                        self.acao_atual = random.choice(["FLANQUEAR", "ESMAGAR"])
                    else:
                        self.acao_atual = random.choice(["PRESSIONAR", "ESMAGAR"])
                    if hasattr(self.parent, 'mangual_slam_combo'):
                        self.parent.mangual_slam_combo = 1
            elif em_zona_longa:
                self.acao_atual = random.choice(["MATAR", "ESMAGAR"]) if roll < 0.55 else (
                    random.choice(["PRESSIONAR", "MATAR"]) if roll < 0.80 else random.choice(["CIRCULAR", "FLANQUEAR"]))
            else:  # fora do alcance
                # MEL-AI-06 fix: reseta combo ao sair do alcance
                if hasattr(self.parent, 'mangual_slam_combo'):
                    self.parent.mangual_slam_combo = 0
                self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "APROXIMAR"]) if roll < 0.60 else random.choice(["FLANQUEAR", "CIRCULAR", "APROXIMAR"])
        else:
            # Outras correntes (Chicote, Meteor Hammer, etc.)
            no_alcance = distancia <= alcance_efetivo
            if distancia < zona_morta:
                self.acao_atual = "RECUAR"
            elif distancia < alcance_ideal:
                self.acao_atual = random.choice(["MATAR", "ESMAGAR", "FLANQUEAR"])
            elif no_alcance:
                self.acao_atual = random.choice(["MATAR", "CIRCULAR", "COMBATE"])
            else:
                self.acao_atual = "APROXIMAR"


    def _estrategia_dupla(self, distancia, roll, alcance_efetivo, alcance_ideal,
                           hp_pct, inimigo_hp_pct, arma):
        """EstratÃ©gia para armas duplas (Adagas GÃªmeas v3.1 + genÃ©rico)."""
        arma_estilo   = getattr(arma, 'estilo', '') if arma else ''
        no_alcance    = distancia <= alcance_efetivo
        longe         = distancia > alcance_efetivo * 1.5
        muito_longe   = distancia > alcance_efetivo * 2.5

        if arma_estilo == "Adagas GÃªmeas":
            engajamento = alcance_ideal
            pressao     = alcance_ideal * 1.30
            dash_curto  = alcance_ideal * 2.20

            em_engajamento = distancia <= engajamento
            em_pressao     = engajamento < distancia <= pressao
            em_dash        = pressao < distancia <= dash_curto

            combo_hits   = self.combo_atual  # CB-05: atributo pertence ao AIBrain (self), nÃ£o ao parent
            combo_ativo  = combo_hits > 2
            combo_frenzy = combo_hits > 5

            if em_engajamento:
                if hp_pct < 0.20 and roll < 0.50:
                    self.acao_atual = random.choice(["FLANQUEAR", "RECUAR", "FLANQUEAR"])
                elif inimigo_hp_pct < 0.25:
                    self.acao_atual = random.choice(["MATAR", "MATAR", "ATAQUE_RAPIDO"])
                elif combo_frenzy:
                    self.acao_atual = random.choice(["MATAR", "ATAQUE_RAPIDO", "ATAQUE_RAPIDO", "MATAR", "COMBATE"])
                elif combo_ativo:
                    self.acao_atual = random.choice(["MATAR", "ATAQUE_RAPIDO", "ESMAGAR"]) if roll < 0.65 else random.choice(["FLANQUEAR", "CIRCULAR"])
                else:
                    self.acao_atual = random.choice(["MATAR", "ESMAGAR", "COMBATE"]) if roll < 0.60 else random.choice(["ATAQUE_RAPIDO", "FLANQUEAR"])
            elif em_pressao:
                if inimigo_hp_pct < 0.30:
                    self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "PRESSIONAR"])
                elif roll < 0.55:
                    self.acao_atual = random.choice(["PRESSIONAR", "ATAQUE_RAPIDO"])
                elif roll < 0.80:
                    self.acao_atual = random.choice(["FLANQUEAR", "PRESSIONAR"])
                else:
                    self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR"])
            elif em_dash:
                self.acao_atual = random.choice(["FLANQUEAR", "PRESSIONAR"]) if roll < 0.45 else (
                    random.choice(["APROXIMAR", "PRESSIONAR"]) if roll < 0.75 else random.choice(["CIRCULAR", "APROXIMAR"]))
            else:
                self.acao_atual = random.choice(["FLANQUEAR", "CIRCULAR"]) if roll < 0.40 else random.choice(["APROXIMAR", "FLANQUEAR"])
        else:
            # Outras armas duplas (Garras, Tonfas, etc.)
            if muito_longe:
                self.acao_atual = "APROXIMAR"
            elif longe:
                self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR", "PRESSIONAR"])
            elif no_alcance:
                self.acao_atual = "MATAR" if inimigo_hp_pct < 0.3 else (
                    random.choice(["MATAR", "ATAQUE_RAPIDO", "MATAR"]) if roll < 0.7 else random.choice(["FLANQUEAR", "CIRCULAR"]))
            else:
                self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR"])

    def _estrategia_orbital(self, distancia, roll, alcance_efetivo, alcance_ideal, hp_pct, inimigo_hp_pct, arma):
        """Estratégia para armas orbitais: controlar espaço e explodir janelas de burst."""
        burst_pronto = getattr(self.parent, "orbital_burst_cd", 0.0) <= 0.0
        subtipo_orbital = resolver_subtipo_orbital(arma)
        pacote_id = self._obter_pacote_composto_id()
        alcance_burst = max(3.2, alcance_efetivo * (1.18 if subtipo_orbital == "escudo" else 1.35 if subtipo_orbital == "laminas" else 1.48))
        muito_perto = distancia < max(1.15, alcance_ideal * (0.62 if subtipo_orbital == "escudo" else 0.50))
        zona_orbita = distancia <= max(2.25, alcance_efetivo * (0.92 if subtipo_orbital == "escudo" else 1.08))

        if subtipo_orbital == "escudo":
            if pacote_id == "bastiao_prismatico":
                if muito_perto and hp_pct < 0.42:
                    self.acao_atual = random.choice(["COMBATE", "CONTRA_ATAQUE", "RECUAR"])
                elif burst_pronto and distancia < alcance_burst * 0.84 and inimigo_hp_pct < 0.48:
                    self.acao_atual = random.choice(["CONTRA_ATAQUE", "COMBATE"])
                elif zona_orbita:
                    self.acao_atual = random.choice(["COMBATE", "CONTRA_ATAQUE", "CIRCULAR"])
                elif distancia > alcance_burst:
                    self.acao_atual = random.choice(["APROXIMAR", "COMBATE"])
                else:
                    self.acao_atual = random.choice(["COMBATE", "CIRCULAR", "CONTRA_ATAQUE"])
                return
            if muito_perto and hp_pct < 0.38:
                self.acao_atual = random.choice(["COMBATE", "CIRCULAR", "RECUAR"])
            elif burst_pronto and distancia < alcance_burst * 0.88 and inimigo_hp_pct < 0.55:
                self.acao_atual = random.choice(["COMBATE", "PRESSIONAR", "CONTRA_ATAQUE"])
            elif zona_orbita:
                self.acao_atual = random.choice(["COMBATE", "CIRCULAR", "CONTRA_ATAQUE"])
            elif distancia > alcance_burst:
                self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR"])
            else:
                self.acao_atual = random.choice(["APROXIMAR", "COMBATE", "CIRCULAR"])
            return

        if subtipo_orbital == "drone":
            if pacote_id == "artilheiro_de_orbita":
                if muito_perto and hp_pct < 0.36:
                    self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "POKE"])
                elif burst_pronto and zona_orbita:
                    self.acao_atual = random.choice(["POKE", "COMBATE", "PRESSIONAR"] if inimigo_hp_pct < 0.40 else ["POKE", "CIRCULAR", "COMBATE"])
                elif distancia > alcance_burst:
                    self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR", "POKE"])
                else:
                    self.acao_atual = random.choice(["POKE", "CIRCULAR", "COMBATE"])
                return
            if muito_perto and hp_pct < 0.30:
                self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "POKE"])
            elif burst_pronto and zona_orbita:
                self.acao_atual = random.choice(["PRESSIONAR", "POKE", "MATAR"] if inimigo_hp_pct < 0.45 else ["PRESSIONAR", "COMBATE", "POKE"])
            elif distancia > alcance_burst:
                self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR", "PRESSIONAR"])
            else:
                self.acao_atual = random.choice(["POKE", "COMBATE", "CIRCULAR"])
            return

        if subtipo_orbital == "laminas":
            if muito_perto and hp_pct < 0.28:
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "RECUAR"])
            elif burst_pronto and zona_orbita:
                self.acao_atual = random.choice(["MATAR", "PRESSIONAR", "FLANQUEAR"] if inimigo_hp_pct < 0.5 else ["COMBATE", "FLANQUEAR", "PRESSIONAR"])
            elif distancia > alcance_burst:
                self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR"])
            else:
                self.acao_atual = random.choice(["COMBATE", "MATAR", "FLANQUEAR"])
            return

        if muito_perto and hp_pct < 0.32:
            self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "COMBATE"])
        elif burst_pronto and zona_orbita:
            self.acao_atual = random.choice(["PRESSIONAR", "COMBATE", "MATAR"] if inimigo_hp_pct < 0.4 else ["PRESSIONAR", "COMBATE", "FLANQUEAR"])
        elif distancia > alcance_burst:
            self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR", "PRESSIONAR"])
        elif zona_orbita:
            self.acao_atual = random.choice(["COMBATE", "CIRCULAR", "FLANQUEAR"])
        else:
            self.acao_atual = random.choice(["APROXIMAR", "COMBATE", "CIRCULAR"])

    def _estrategia_hibrida(self, distancia, roll, alcance_efetivo, alcance_ideal, hp_pct, inimigo_hp_pct, arma):
        """Estratégia para armas híbridas: alternar envelope curto/longo sem perder pressão."""
        forma_atual = int(getattr(self.parent, "transform_forma", getattr(arma, "forma_atual", 0)) or 0)
        bonus_troca = getattr(self.parent, "transform_bonus_timer", 0.0) > 0.0
        cutoff_curto = max(1.4, alcance_ideal * 0.62)
        cutoff_longo = max(3.0, alcance_efetivo * 1.08)

        if forma_atual == 0:
            if distancia > cutoff_longo:
                self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "FLANQUEAR"])
            elif distancia < cutoff_curto and hp_pct < 0.35:
                self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "COMBATE"])
            elif bonus_troca and inimigo_hp_pct < 0.45:
                self.acao_atual = random.choice(["MATAR", "ESMAGAR", "PRESSIONAR"])
            else:
                self.acao_atual = random.choice(["MATAR", "COMBATE", "PRESSIONAR"])
            return

        if distancia < cutoff_curto:
            self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "POKE"])
        elif bonus_troca and inimigo_hp_pct < 0.5:
            self.acao_atual = random.choice(["MATAR", "POKE", "PRESSIONAR"])
        elif distancia <= alcance_efetivo:
            self.acao_atual = random.choice(["POKE", "COMBATE", "PRESSIONAR"])
        else:
            self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR", "POKE"])


    # â”€â”€ CAMINHO GENÃ‰RICO COM PESOS ACUMULATIVOS (MEL-AI-03) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _estrategia_generica(self, distancia, roll, hp_pct, inimigo_hp_pct,
                              alcance_efetivo, alcance_ideal, inimigo, debug=False):
        ctx = self._criar_contexto_combate_generico(
            distancia,
            roll,
            hp_pct,
            inimigo_hp_pct,
            alcance_efetivo,
            alcance_ideal,
            inimigo,
        )
        pesos: dict[str, float] = {}
        self._votar_base_generica(ctx, pesos)
        bp = self._votar_profile_traits_generico(ctx, pesos)
        self._votar_estilo_emocao_generico(ctx, pesos, bp)
        self._votar_leitura_oponente_generico(ctx, pesos)
        self._votar_modificadores_externos_generico(ctx, pesos)
        self._votar_time_generico(ctx, pesos)
        self._compensar_matchup_generico(ctx, pesos, bp)
        self._aplicar_anti_repeticao_generico(ctx, pesos)

        acao_escolhida = self._escolher_acao_generica(ctx, pesos, debug=debug)
        if acao_escolhida:
            self.acao_atual = acao_escolhida
        return

    # L-N02: mÃ©todos [DEPRECIADO] removidos (Sprint 4) â€” lÃ³gica jÃ¡ absorvida em _estrategia_generica

    def _calcular_alcance_efetivo(self):
        """Calcula alcance real de ataque baseado na arma e hitbox profile v12.2
        CRIT-03 fix: incorpora o alcance_tatico_offset da percepÃ§Ã£o de armas
        sem sobrescrever p.alcance_ideal (que pertence Ã  personalidade).
        """
        p = self.parent
        
        arma = p.dados.arma_obj if p.dados else None
        if not arma:
            return 2.0  # Fallback sem arma
        
        metricas = obter_metricas_arma(arma, p)
        alcance_calc = metricas["alcance_tatico"]

        # CRIT-03 fix: aplica offset tÃ¡tico da percepÃ§Ã£o de armas sem alterar alcance_ideal
        offset = getattr(self, 'percepcao_arma', {}).get("alcance_tatico_offset", 0.0)
        if offset != 0.0:
            alcance_calc = max(0.8, alcance_calc + offset)

        return alcance_calc


    def _calcular_timer_decisao(self):
        """Calcula timer para prÃ³xima decisÃ£o"""
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

