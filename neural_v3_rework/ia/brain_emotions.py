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


class EmotionsMixin(_AIBrainMixinBase):
    """Mixin de emoÃ§Ãµes, humor, estados humanos, quirks, reaÃ§Ãµes, ritmo e instintos."""

    
    # =========================================================================
    # SISTEMA DE ESTADOS HUMANOS v8.0
    # =========================================================================
    
    def _atualizar_estados_humanos(self, dt, distancia, inimigo):
        """Atualiza hesitaÃ§Ã£o, impulso e outros estados humanos"""
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0  # FP-N01
        memoria = getattr(self, "memoria_adaptativa", {})
        vies_agressao = memoria.get("vies_agressao", 0.0)
        vies_cautela = memoria.get("vies_cautela", 0.0)
        vies_pressao = memoria.get("vies_pressao", 0.0)
        vies_contra = memoria.get("vies_contra_ataque", 0.0)
        
        # === HESITAÃ‡ÃƒO ===
        # Aumenta quando: 
        # - SituaÃ§Ã£o desfavorÃ¡vel
        # - Oponente muito agressivo
        # - Tomou muito dano recentemente
        
        base_hesitacao = 0.1
        if hp_pct < 0.3:
            base_hesitacao += 0.2
        if self.momentum < -0.5:
            base_hesitacao += 0.15
        if self.hits_recebidos_recente >= 3:
            base_hesitacao += 0.2
        if self.pressao_recebida > AI_PRESSAO_ALTA:
            base_hesitacao += 0.15
        base_hesitacao += max(0.0, vies_cautela) * 0.25
        base_hesitacao -= max(0.0, vies_agressao) * 0.10
        base_hesitacao -= max(0.0, vies_contra) * 0.06
        
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
        # - Momento favorÃ¡vel
        
        base_impulso = 0.1
        if self.raiva > 0.6:
            base_impulso += 0.3
        if inimigo.vida / max(inimigo.vida_max, 1) < 0.25:
            base_impulso += 0.25
        if self.momentum > 0.5:
            base_impulso += 0.2
        if self.excitacao > 0.7:
            base_impulso += 0.15
        base_impulso += max(0.0, vies_agressao) * 0.22
        base_impulso += max(0.0, vies_pressao) * 0.12
        base_impulso += max(0.0, vies_contra) * 0.08
        base_impulso -= max(0.0, vies_cautela) * 0.16
        
        # Personalidade
        if "IMPRUDENTE" in self.tracos:
            base_impulso *= 1.5
        if "CALCULISTA" in self.tracos:
            base_impulso *= 0.5
        if "PACIENTE" in self.tracos:
            base_impulso *= 0.6
        
        self.impulso = max(0.0, min(0.9, base_impulso))
        
        # === CONGELAMENTO ===
        # Ocorre sob pressÃ£o extrema
        
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
        # Micro-pausas apÃ³s bursts de aÃ§Ã£o
        self.burst_counter = max(0, self.burst_counter - dt * 2)
        if self.burst_counter > 5:
            self.descanso_timer = random.uniform(0.3, 0.8)
            self.burst_counter = 0

    
    def _verificar_hesitacao(self, dt, distancia, inimigo):
        """Verifica se a IA hesita neste frame"""
        # Anti-kite: melee contra arco nÃ£o deve desperdiÃ§ar tempo em hesitaÃ§Ã£o defensiva
        # quando estÃ¡ fora do alcance ideal.
        p = self.parent
        minha_arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        inimigo_arma = getattr(getattr(inimigo, 'dados', None), 'arma_obj', None)
        meu_tipo = getattr(minha_arma, 'tipo', '') if minha_arma else ''
        ini_tipo = getattr(inimigo_arma, 'tipo', '') if inimigo_arma else ''
        sou_ranged = meu_tipo in ("Arco", "Arremesso", "MÃ¡gica")
        if ini_tipo == "Arco" and not sou_ranged and distancia > p.alcance_ideal * 0.9:
            return False

        # Descanso forÃ§ado
        if self.descanso_timer > 0:
            self.descanso_timer -= dt
            self.acao_atual = "CIRCULAR"
            return True
        
        # Congelamento sob pressÃ£o
        if random.random() < self.congelamento * 0.1:
            self.acao_atual = "BLOQUEAR"
            return True
        
        # HesitaÃ§Ã£o
        if random.random() < self.hesitacao * 0.05:
            # Hesita - faz algo defensivo
            self.acao_atual = random.choice(["CIRCULAR", "BLOQUEAR", "RECUAR"])
            return True
        
        # Impulso pode cancelar hesitaÃ§Ã£o
        if random.random() < self.impulso * 0.1:
            self.acao_atual = random.choice(["MATAR", "APROXIMAR", "PRESSIONAR"])
            self.burst_counter += 1
            return True
        
        return False

    
    def _registrar_acao(self):
        """Registra aÃ§Ã£o para evitar repetiÃ§Ã£o excessiva"""
        self.historico_acoes.append(self.acao_atual)
        if len(self.historico_acoes) > 10:
            self.historico_acoes.pop(0)
        
        # Rastreia CIRCULAR consecutivo e inverte direÃ§Ã£o periodicamente
        if self.acao_atual == "CIRCULAR":
            self.circular_consecutivo += 1
            # A cada 2-3 circulares seguidos, inverte a direÃ§Ã£o pra nÃ£o parecer robÃ³tico
            if self.circular_consecutivo >= random.randint(2, 3):
                self.dir_circular *= -1
                self.circular_consecutivo = 0  # BUG-FIX: reset apÃ³s flip para nÃ£o inverter todo frame
        else:
            self.circular_consecutivo = 0
        
        # Conta repetiÃ§Ãµes
        if self.acao_atual in self.repeticao_contador:
            self.repeticao_contador[self.acao_atual] += 1
        else:
            self.repeticao_contador[self.acao_atual] = 1
        
        # Decay das contagens
        for key in list(self.repeticao_contador.keys()):
            if key != self.acao_atual:
                self.repeticao_contador[key] = max(0, self.repeticao_contador[key] - 0.5)


    # =========================================================================
    # ATUALIZAÃ‡ÃƒO DE ESTADOS
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
        self._dir_circular_cd = max(0, self._dir_circular_cd - dt)
        self.tempo_desde_dano += dt
        self.tempo_desde_hit += dt
        if hasattr(self, "_decair_memoria_adaptativa"):
            self._decair_memoria_adaptativa(dt)
        if hasattr(self, "_decair_memoria_curta_oponentes"):
            self._decair_memoria_curta_oponentes(dt)
        if hasattr(self, "_decair_memoria_cena"):
            self._decair_memoria_cena(dt)
        # BUG-AI-03 fix: incrementa contador de bloqueio para o trigger "bloqueio_sucesso"
        self.ultimo_bloqueio = min(999.0, self.ultimo_bloqueio + dt)
        # HIGH-04 fix: decai o timer do estilo temporÃ¡rio (style_switch instinto).
        # Quando expira, restaura o estilo original da personalidade.
        timer_override = getattr(self, '_estilo_override_timer', 0.0)
        if timer_override > 0:
            self._estilo_override_timer = timer_override - dt
            if self._estilo_override_timer <= 0:
                self._estilo_override = None
                _log.debug("[INSTINTO] %s: style_switch expirou, voltando ao estilo base",
                           self.parent.dados.nome if hasattr(self.parent, 'dados') else '?')


    def _detectar_dano(self):
        """Detecta dano recebido"""
        p = self.parent
        
        if p.vida < self.ultimo_hp:
            dano = self.ultimo_hp - p.vida
            self.hits_recebidos_total += 1
            self.hits_recebidos_recente += 1
            self.tempo_desde_dano = 0.0
            self.ultimo_dano_recebido = dano  # Salva o valor do dano
            self.combo_atual = 0
            self._reagir_ao_dano(dano)
        
        self.ultimo_hp = p.vida


    def _reagir_ao_dano(self, dano):
        """ReaÃ§Ãµes emocionais ao dano â€” amplified by behavior profile"""
        from ia.behavior_profiles import FALLBACK_PROFILE
        bp = getattr(self, '_behavior_profile', FALLBACK_PROFILE)
        raiva_mult = bp.get("raiva_ganho_mult", 1.0)
        medo_mult = bp.get("medo_ganho_mult", 1.0)
        dano_reacao = bp.get("dano_recebido_reacao", "neutro")

        if "VINGATIVO" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.25 * raiva_mult)
        if "BERSERKER" in self.tracos or "BERSERKER_RAGE" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.15 * raiva_mult)
            self.adrenalina = min(1.0, self.adrenalina + 0.2)
        if "FURIOSO" in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.2 * raiva_mult)
        if "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
            self.medo = min(1.0, self.medo + 0.2 * medo_mult)
        if "PARANOICO" in self.tracos:
            self.medo = min(1.0, self.medo + 0.15 * medo_mult)
        if "FRIO" not in self.tracos:
            self.raiva = min(1.0, self.raiva + 0.05 * raiva_mult)
        self.frustracao = min(1.0, self.frustracao + 0.1)

        # Profile-driven damage reaction
        if dano_reacao in ("RAIVA", "FURIA"):
            self.raiva = min(1.0, self.raiva + 0.10 * raiva_mult)
        elif dano_reacao == "RECUAR":
            self.medo = min(1.0, self.medo + 0.08 * medo_mult)
        elif dano_reacao == "FOCO":
            # Foco: reduz medo, leve boost de confianÃ§a
            self.medo = max(0.0, self.medo - 0.05)
            self.confianca = min(1.0, self.confianca + 0.05)
        elif dano_reacao == "ADAPTAR":
            # Adaptar: leve raiva + leve cautela simultÃ¢neos
            self.raiva = min(1.0, self.raiva + 0.05 * raiva_mult)
            self.confianca = min(1.0, self.confianca + 0.03)
        # "NADA" = sem reaÃ§Ã£o adicional (por design)


    def _atualizar_emocoes(self, dt, distancia, inimigo):
        """Atualiza estado emocional"""
        p = self.parent
        hp_pct = p.vida / max(p.vida_max, 1)
        inimigo_hp_pct = inimigo.vida / max(inimigo.vida_max, 1)
        
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
        
        # ConfianÃ§a
        hp_diff = hp_pct - inimigo_hp_pct
        target_conf = 0.5 + hp_diff * 0.4
        self.confianca += (target_conf - self.confianca) * 0.05 * dt * 60
        self.confianca = max(0.1, min(1.0, self.confianca))
        
        # ExcitaÃ§Ã£o
        if distancia < 3.0:
            self.excitacao = min(1.0, self.excitacao + 0.02 * dt * 60)
        if self.combo_atual > 2:
            self.excitacao = min(1.0, self.excitacao + 0.05)
        
        # TÃ©dio
        if distancia > 8.0 and self.tempo_combate > 10.0:
            self.tedio = min(1.0, self.tedio + 0.01 * dt * 60)
        
        # Adrenalina
        if hp_pct < 0.2 or (distancia < 2.0 and self.raiva > 0.5):
            self.adrenalina = min(1.0, self.adrenalina + 0.04 * dt * 60)
        
        # ================================================================
        # v13.0: TEAM EMOTIONAL CONTEXT
        # Aliados influenciam estado emocional: moral, coordenaÃ§Ã£o, medo coletivo
        # ================================================================
        orders = getattr(self, 'team_orders', {})
        has_team = orders.get("alive_count", 1) > 1

        if has_team:
            team_hp_pct = orders.get("team_hp_pct", 1.0)
            em_desvantagem = orders.get("em_desvantagem", False)
            alive_count = orders.get("alive_count", 1)
            enemy_alive = orders.get("enemy_alive_count", 1)
            is_carry = orders.get("is_carry", False)

            # â”€â”€ MORAL DO TIME (afeta confianÃ§a e medo de todos) â”€â”€
            if team_hp_pct > 0.7 and alive_count > enemy_alive:
                # Time saudÃ¡vel e em vantagem = moral alto
                self.confianca = min(1.0, self.confianca + 0.01 * dt * 60)
                self.medo = max(0, self.medo - 0.005 * dt * 60)
            elif team_hp_pct < 0.3 or em_desvantagem:
                # Time morrendo ou em desvantagem numÃ©rica
                if "DETERMINADO" not in self.tracos and "FRIO" not in self.tracos:
                    self.medo = min(0.6, self.medo + 0.01 * dt * 60)
                if "VINGATIVO" in self.tracos:
                    self.raiva = min(1.0, self.raiva + 0.02 * dt * 60)

            # â”€â”€ ALLY DEATH DETECTION â”€â”€
            ma = getattr(self, 'multi_awareness', {})
            prev_ally_count = getattr(self, '_prev_ally_alive', alive_count)
            if alive_count < prev_ally_count:
                # Aliado morreu!
                ally_died = True
                if "VINGATIVO" in self.tracos:
                    self.raiva = min(1.0, self.raiva + 0.4)
                    self.adrenalina = min(1.0, self.adrenalina + 0.3)
                if "BERSERKER" in self.tracos or "BERSERKER_RAGE" in self.tracos:
                    self.raiva = min(1.0, self.raiva + 0.3)
                    self.modo_berserk = True
                if "COVARDE" in self.tracos:
                    self.medo = min(1.0, self.medo + 0.3)
                if "PROTETOR" in self.tracos:
                    self.frustracao = min(1.0, self.frustracao + 0.3)
                    self.raiva = min(1.0, self.raiva + 0.2)
                # Emotional impact genÃ©rico
                self.adrenalina = min(1.0, self.adrenalina + 0.15)
            self._prev_ally_alive = alive_count

            # â”€â”€ LAST STAND â€” Ãºltimo sobrevivente do time â”€â”€
            if alive_count == 1 and enemy_alive >= 2:
                self.adrenalina = min(1.0, self.adrenalina + 0.05 * dt * 60)
                if "DETERMINADO" in self.tracos or "KAMIKAZE" in self.tracos:
                    self.raiva = min(1.0, self.raiva + 0.03 * dt * 60)
                    self.confianca = min(0.8, self.confianca + 0.02 * dt * 60)
                    self.medo = max(0, self.medo - 0.02 * dt * 60)
                elif "COVARDE" not in self.tracos:
                    self.medo = min(0.7, self.medo + 0.02 * dt * 60)

            # â”€â”€ COORDINATED AGGRESSION â€” aliados atacando = mais confianÃ§a â”€â”€
            ally_intents = orders.get("ally_intents", {})
            allies_attacking = sum(
                1 for i in ally_intents.values()
                if getattr(i, 'action', '') in ("MATAR", "ESMAGAR", "PRESSIONAR")
            )
            if allies_attacking >= 2:
                self.confianca = min(1.0, self.confianca + 0.01 * dt * 60)
                self.excitacao = min(1.0, self.excitacao + 0.01 * dt * 60)

            # â”€â”€ CARRY PRESSURE â€” carry do time sente pressÃ£o extra â”€â”€
            if is_carry:
                self.excitacao = min(1.0, self.excitacao + 0.005 * dt * 60)

            # â”€â”€ HELP REQUEST URGENCY â€” se aliado pediu ajuda, impulso sobe â”€â”€
            for callout in orders.get("callouts", []):
                if callout.get("type") == "HELP":
                    urgency = callout.get("urgency", 0.5)
                    self.impulso = min(0.7, self.impulso + urgency * 0.1)
                    if "PROTETOR" in self.tracos:
                        self.impulso = min(0.9, self.impulso + 0.15)

        # MudanÃ§a de direÃ§Ã£o
        if self.cd_mudanca_direcao <= 0:
            chance = 0.15 if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos else 0.08
            if random.random() < chance * dt * 60:
                self.dir_circular *= -1
                self.cd_mudanca_direcao = random.uniform(0.5, 2.0)

        # BUG-AI-05 fix: decai o modificador temporÃ¡rio de agressividade de volta a 0.
        # Taxa: ~0.05 por segundo para modificadores positivos, ~0.03 para negativos.
        if self._agressividade_temp_mod > 0:
            self._agressividade_temp_mod = max(0.0, self._agressividade_temp_mod - 0.05 * dt)
        elif self._agressividade_temp_mod < 0:
            self._agressividade_temp_mod = min(0.0, self._agressividade_temp_mod + 0.03 * dt)


    def _atualizar_humor(self, dt):
        """Atualiza humor baseado nas emoÃ§Ãµes"""
        if self.cd_mudanca_humor > 0:
            return
        
        novo_humor = self.humor
        rivalidade = self._calcular_pressao_rivalidade(getattr(self, "_alvo_atual", None)) if hasattr(self, "_calcular_pressao_rivalidade") else {}
        rival_dom = rivalidade.get("dominante")
        rival_int = rivalidade.get("intensidade", 0.0)
        
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

        if rival_int >= 0.28:
            if rival_dom == "respeito" and novo_humor not in {"FURIOSO", "DESESPERADO"}:
                novo_humor = "FOCADO" if self.confianca >= self.medo else "CALMO"
            elif rival_dom == "vinganca":
                novo_humor = "DETERMINADO" if self.confianca > 0.35 else "FURIOSO"
            elif rival_dom == "obsessao" and novo_humor not in {"DESESPERADO", "ASSUSTADO"}:
                novo_humor = "ANIMADO" if self.excitacao > 0.45 else "FOCADO"
            elif rival_dom == "caca" and novo_humor not in {"ASSUSTADO", "NERVOSO"}:
                novo_humor = "CONFIANTE" if self.confianca > 0.45 else "DETERMINADO"
        
        if novo_humor != self.humor:
            self.humor = novo_humor
            self.cd_mudanca_humor = random.uniform(2.0, 5.0)


    def _processar_modos_especiais(self, dt, distancia, inimigo):
        """Processa modos especiais de combate"""
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0  # FP-N01
        
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
            inimigo_hp_pct = inimigo.vida / max(inimigo.vida_max, 1)
            if inimigo_hp_pct < 0.4 or (p.mana > p.mana_max * 0.8 and distancia < 5.0):
                self.modo_burst = True
            elif inimigo_hp_pct > 0.6 or p.mana < p.mana_max * 0.3:
                self.modo_burst = False


    # =========================================================================
    # QUIRKS
    # =========================================================================
    
    def _processar_quirks(self, dt, distancia, inimigo):
        """Processa quirks Ãºnicos"""
        if self.cd_quirk > 0 or not self.quirks:
            return False
        
        p = self.parent
        hp_pct = p.vida / max(p.vida_max, 1)
        inimigo_hp_pct = inimigo.vida / max(inimigo.vida_max, 1)
        
        for quirk in self.quirks:
            if self._executar_quirk(quirk, distancia, hp_pct, inimigo_hp_pct, inimigo):
                self.cd_quirk = random.uniform(3.0, 8.0)
                return True
        
        return False


    def _executar_quirk(self, quirk, distancia, hp_pct, inimigo_hp_pct, inimigo):
        """Executa um quirk especÃ­fico"""
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
    # REAÃ‡Ã•ES
    # =========================================================================
    
    def _processar_reacoes(self, dt, distancia, inimigo):
        """Processa reaÃ§Ãµes imediatas"""
        if self.cd_reagir > 0:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0  # FP-N01
        
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
        """Pulo evasivo de emergÃªncia.
        HIGH-03 fix: mÃ©todo era chamado em _processar_reacoes mas nÃ£o existia
        em nenhum mixin â€” crash silencioso via AttributeError mascarado.
        Ativado quando HP estÃ¡ baixo e inimigo estÃ¡ prÃ³ximo.
        """
        # SÃ³ pula em emergÃªncia real: HP < 35% E inimigo colado
        if hp_pct > 0.35 or distancia > 3.5:
            return False
        if self.cd_pulo > 0:
            return False
        # TraÃ§os que suprimem fuga
        if self.modo_berserk or "KAMIKAZE" in self.tracos:
            return False
        p = self.parent
        if p.z > 0:
            return False  # JÃ¡ estÃ¡ no ar
        # Chance base â€” maior quanto mais desesperado
        chance = (0.35 - hp_pct) * 2.0  # 0% a 70%
        if "EVASIVO" in self.tracos or "ACROBATA" in self.tracos:
            chance += 0.2
        if "ESTATICO" in self.tracos:
            chance *= 0.3
        import random as _r
        if _r.random() < chance:
            p.vel_z = _r.uniform(10.0, 13.5)
            # Impulso lateral para longe do inimigo
            import math as _m
            ang_fuga = _m.atan2(p.pos[1] - inimigo.pos[1], p.pos[0] - inimigo.pos[0])
            p.vel[0] += _m.cos(ang_fuga) * 8.0
            p.vel[1] += _m.sin(ang_fuga) * 8.0
            self.cd_pulo = 1.2
            self.cd_reagir = 0.4
            _log.debug("[REAÃ‡ÃƒO] %s: pulo evasivo (hp=%.0f%%)", p.dados.nome, hp_pct * 100)
            return True
        return False


    def _tentar_dash_emergencia(self, distancia, hp_pct, inimigo):
        """Dash de emergÃªncia quando HP crÃ­tico e inimigo atacando.
        HIGH-03 fix: mÃ©todo era chamado em _processar_reacoes mas nÃ£o existia
        em nenhum mixin â€” crash silencioso via AttributeError mascarado.
        SÃ³ usa uma skill de DASH disponÃ­vel â€” sem criar dash do nada.
        """
        # CondiÃ§Ãµes de emergÃªncia: HP muito baixo E ataque iminente
        if hp_pct > 0.25:
            return False
        if not self.leitura_oponente.get("ataque_iminente", False):
            return False
        if self.cd_dash > 0:
            return False
        if self.modo_berserk:
            return False
        dash_skills = self.skills_por_tipo.get("DASH", [])
        if not dash_skills:
            return False
        import random as _r
        chance = 0.6 + (0.25 - hp_pct) * 2.0  # 60-110% â†’ clampado
        chance = min(0.95, chance)
        if "EVASIVO" in self.tracos:
            chance = min(0.98, chance + 0.15)
        if "ESTATICO" in self.tracos:
            chance *= 0.4
        if _r.random() < chance:
            # Aponta dash para longe do inimigo
            import math as _m
            p = self.parent
            ang_fuga = _m.atan2(p.pos[1] - inimigo.pos[1], p.pos[0] - inimigo.pos[0])
            ang_orig = p.angulo_olhar
            p.angulo_olhar = _m.degrees(ang_fuga)
            usou = self._usar_skill(dash_skills[0])
            p.angulo_olhar = ang_orig
            if usou:
                self.cd_dash = 1.5
                self.cd_reagir = 0.3
                self.acao_atual = "RECUAR"
                _log.debug("[REAÃ‡ÃƒO] %s: dash emergÃªncia (hp=%.0f%%)", p.dados.nome, hp_pct * 100)
                return True
        return False



    def _tentar_cura_emergencia(self, hp_pct):
        """Cura de emergÃªncia"""
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
        
        # FP-01 fix: a condiÃ§Ã£o anterior tinha lÃ³gica invertida.
        # `not inimigo.atacando` era sempre True fora do frame de ataque (inclusive durante
        # movimento, circulaÃ§Ã£o, etc.), gerando falsos "vulnerÃ¡vel". A lÃ³gica correta exige
        # que o inimigo tenha ACABADO de atacar (cooldown > 0) E nÃ£o esteja mais atacando.
        vulneravel = False
        acabou_de_atacar = (
            hasattr(inimigo, 'cooldown_ataque') and
            0.05 < inimigo.cooldown_ataque < 0.70
        )
        nao_esta_atacando = (
            hasattr(inimigo, 'atacando') and not inimigo.atacando
        )
        if acabou_de_atacar and nao_esta_atacando:
            vulneravel = True
        
        if vulneravel and distancia < self.parent.alcance_ideal + 1.5:
            self.acao_atual = "CONTRA_ATAQUE"
            self.raiva = min(1.0, self.raiva + 0.1)
            self.cd_reagir = 0.4
            return True
        
        return False


    # =========================================================================
    # NOVOS SISTEMAS v11.0 - RITMOS E INSTINTOS
    # =========================================================================
    
    def _atualizar_ritmo(self, dt):
        """Atualiza o sistema de ritmo de batalha"""
        if not self.ritmo or self.ritmo not in RITMOS:
            return
        
        ritmo_data = RITMOS[self.ritmo]
        fases = ritmo_data["fases"]
        duracao = ritmo_data["duracao_fase"]
        
        # Atualiza timer
        self.ritmo_timer += dt
        
        # Verifica mudanÃ§a de fase
        if self.ritmo_timer >= duracao:
            self.ritmo_timer = 0.0
            self.ritmo_fase_atual = (self.ritmo_fase_atual + 1) % len(fases)
        
        # Aplica modificadores da fase atual
        fase_atual = fases[self.ritmo_fase_atual]
        
        # Fase ALEATORIO do ritmo caÃ³tico
        if fase_atual == "ALEATORIO":
            # M-N02: salva fase aleatÃ³ria escolhida e reutiliza por toda a duraÃ§Ã£o
            if not hasattr(self, '_fase_aleatorio_atual') or self.ritmo_timer < 0.1:
                self._fase_aleatorio_atual = random.choice(list(RITMO_MODIFICADORES.keys()))
            fase_atual = self._fase_aleatorio_atual
        
        if fase_atual in RITMO_MODIFICADORES:
            mods = RITMO_MODIFICADORES[fase_atual]
            self.ritmo_modificadores = mods.copy()
        else:
            self.ritmo_modificadores = {"agressividade": 0, "defesa": 0, "mobilidade": 0}

    
    def _processar_instintos(self, dt, distancia, inimigo):
        """
        Processa instintos de combate â€” reaÃ§Ãµes automÃ¡ticas de alta prioridade.

        MEL-AI-01 (Sprint 4): todos os trÃªs triggers que estavam inativos foram corrigidos:
          â€¢ 'oponente_whiff'    â€” BUG-AI-02 fix (Sprint 1): janela_ataque["tipo"] = "whiff"
                                  agora Ã© setado em _atualizar_leitura_oponente.
          â€¢ 'bloqueio_sucesso'  â€” BUG-AI-03 fix (Sprint 1): self.ultimo_bloqueio inicializado
                                  em __init__ e resetado em on_bloqueio_sucesso().
          â€¢ 'ataque_previsivel' â€” BUG-AI-04 fix (Sprint 1): leitura["padrao_detectado"]
                                  derivado de leitura["previsibilidade"] > AI_PREVISIBILIDADE_ALTA.
        O sistema de instintos agora estÃ¡ Ã­ntegro â€” todos os triggers sÃ£o funcionais.
        """
        if not self.instintos:
            return False
        
        p = self.parent
        hp_pct = p.vida / p.vida_max if p.vida_max > 0 else 1.0
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0
        
        for instinto_nome in self.instintos:
            if instinto_nome not in INSTINTOS:
                continue
            
            instinto = INSTINTOS[instinto_nome]
            trigger = instinto["trigger"]
            chance = instinto["chance"]
            acao = instinto["acao"]
            
            # Verifica se o trigger estÃ¡ ativo
            triggered = False
            
            if trigger == "hp_critico" and hp_pct < 0.2:
                triggered = True
            elif trigger == "hp_baixo" and hp_pct < 0.4:
                triggered = True
            elif trigger == "oponente_fraco" and inimigo_hp_pct < 0.3:
                triggered = True
            elif trigger == "oponente_whiff" and self.janela_ataque.get("tipo") == "whiff":
                triggered = True
            elif trigger == "oponente_recuando" and hasattr(inimigo, 'brain') and inimigo.brain and inimigo.brain.acao_atual in ["RECUAR", "FUGIR"]:
                triggered = True
            elif trigger == "vantagem_hp" and hp_pct > inimigo_hp_pct + 0.2:
                triggered = True
            elif trigger == "dano_alto" and self.tempo_desde_dano < 0.3 and self.ultimo_dano_recebido > p.vida_max * 0.15:
                triggered = True
            elif trigger == "em_combo" and self.combo_state.get("em_combo", False):
                triggered = True
            elif trigger == "pos_combo" and self.tempo_desde_hit < 0.5 and self.combo_atual > 1:  # CB-06: era tempo_desde_dano (semÃ¢ntica invertida)
                triggered = True
            elif trigger == "bloqueio_sucesso" and hasattr(self, 'ultimo_bloqueio') and self.ultimo_bloqueio < 0.3:
                triggered = True
            elif trigger == "perdendo_trocas" and self.hits_recebidos_recente > self.hits_dados_recente + 2:
                triggered = True
            elif trigger == "ataque_previsivel" and self.leitura_oponente.get("padrao_detectado", False):
                triggered = True
            # Sprint2: triggers definidos em INSTINTOS mas nunca avaliados aqui.
            # ataque_traseiro = inimigo nos flancos traseiros (> 120Â° atrÃ¡s)
            elif trigger == "ataque_traseiro":
                if hasattr(inimigo, 'pos') and hasattr(p, 'angulo_olhar'):
                    import math as _m
                    ang_para_ini = _m.degrees(_m.atan2(
                        inimigo.pos[1] - p.pos[1], inimigo.pos[0] - p.pos[0]
                    ))
                    diff = abs(((ang_para_ini - p.angulo_olhar) + 180) % 360 - 180)
                    if diff > 120 and self.leitura_oponente.get("ataque_iminente", False):
                        triggered = True
            # ataque_baixo = inimigo agachado ou na zona baixa (z muito pequeno vs self.z)
            elif trigger == "ataque_baixo":
                ini_z = getattr(inimigo, 'z', 0)
                self_z = getattr(p, 'z', 0)
                if ini_z < 0.3 and self_z > 0.5 and self.leitura_oponente.get("ataque_iminente", False):
                    triggered = True
            # ataque_alto = inimigo em pulo (z alto) atacando de cima
            elif trigger == "ataque_alto":
                ini_z = getattr(inimigo, 'z', 0)
                if ini_z > 1.0 and self.leitura_oponente.get("ataque_iminente", False):
                    triggered = True
            
            # Executa o instinto se triggado e passar no check de chance
            if triggered and random.random() < chance:
                return self._executar_instinto(acao, distancia, inimigo)
        
        return False

    
    def _executar_instinto(self, acao, distancia, inimigo):
        """Executa uma aÃ§Ã£o instintiva"""
        p = self.parent
        
        if acao == "panic_dash":
            # Dash de pÃ¢nico para longe
            if self.cd_dash <= 0:
                ang = math.atan2(p.pos[1] - inimigo.pos[1], p.pos[0] - inimigo.pos[0])
                p.movimento_x = math.cos(ang) * 0.5
                if hasattr(p, 'iniciar_dash'):
                    p.iniciar_dash()
                self.cd_dash = 0.8
                return True
        
        elif acao == "rage_trigger":
            # Entra em modo de fÃºria
            self.raiva = min(1.0, self.raiva + 0.5)
            self.medo = max(0, self.medo - 0.3)
            # BUG-AI-05 fix: usa modificador temporÃ¡rio â€” a personalidade base nÃ£o Ã© corrompida
            self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.30)
            return False  # NÃ£o consome o turno
        
        elif acao == "auto_chase":
            # Persegue automaticamente
            self.acao_atual = "APROXIMAR"
            return True
        
        elif acao == "defensive_mode":
            # Modo defensivo
            self.acao_atual = "RECUAR"
            # BUG-AI-05 fix: usa modificador temporÃ¡rio negativo
            self._agressividade_temp_mod = max(-0.4, self._agressividade_temp_mod - 0.20)
            return False
        
        elif acao == "punish_attack":
            # Ataque de puniÃ§Ã£o
            self.acao_atual = "MATAR"
            self._executar_ataque(distancia, inimigo)
            return True
        
        elif acao == "execute_mode":
            # Modo execuÃ§Ã£o - all in
            self.acao_atual = "ESMAGAR"
            # BUG-AI-05 fix: usa modificador temporÃ¡rio â€” decai automaticamente apÃ³s a janela
            self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.40)
            self._executar_ataque(distancia, inimigo)
            return True
        
        elif acao == "tactical_retreat":
            # Recuo tÃ¡tico
            self.acao_atual = "RECUAR"
            if self.cd_dash <= 0:
                if hasattr(p, 'iniciar_dash'):
                    p.iniciar_dash()
                self.cd_dash = 0.6
            return True
        
        elif acao == "pressure_increase":
            # Aumenta pressÃ£o
            # BUG-AI-05 fix: usa modificador temporÃ¡rio
            self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.15)
            self.pressao_aplicada = min(1.0, self.pressao_aplicada + 0.2)
            return False
        
        elif acao == "style_switch":
            # HIGH-04 fix: antes, este instinto mudava self.estilo_luta permanentemente
            # sem timer de expiraÃ§Ã£o â€” um MAGO poderia virar "AGGRO" para sempre.
            # Agora usa _estilo_override temporÃ¡rio (3-6s) sem corromper a personalidade base.
            estilos_validos = ["AGGRO", "DEFENSIVE", "MOBILE", "COUNTER", "BURST", "KITE"]
            estilos_alternativos = [e for e in estilos_validos if e != self.estilo_luta]
            self._estilo_override = random.choice(estilos_alternativos)
            self._estilo_override_timer = random.uniform(3.0, 6.0)
            return False
        
        elif acao == "combo_break":
            # Tenta quebrar combo â€” usa dash skill se disponÃ­vel, senÃ£o pulo
            # Sprint2: antes chamava p.iniciar_dash() que nÃ£o existe em Lutador.
            dash_skills = self.skills_por_tipo.get("DASH", [])
            if self.cd_dash <= 0 and dash_skills:
                if self._usar_skill(dash_skills[0]):
                    self.cd_dash = 0.8
                    self.acao_atual = "RECUAR"
                    return True
            elif self.cd_pulo <= 0 and p.z == 0:
                ang_fuga = math.atan2(p.pos[1] - inimigo.pos[1], p.pos[0] - inimigo.pos[0])
                p.vel[0] += math.cos(ang_fuga) * 12.0
                p.vel[1] += math.sin(ang_fuga) * 12.0
                p.vel_z = 10.0
                self.cd_pulo = 1.0
                return True

        # Sprint2: auto_duck, dodge_back, auto_block eram aÃ§Ãµes de instinto
        # definidas em personalities.py mas sem elif em _executar_instinto.
        elif acao == "auto_duck":
            # Agacha / baixa z para evitar ataque alto â€” usa vel_z negativa temporÃ¡ria
            if p.z > 0.3:
                p.vel_z = -p.vel_z * 0.5   # Cancela pulo em andamento
                self.acao_atual = "BLOQUEAR"
                return True
            # No chÃ£o: movimento lateral rÃ¡pido como duck
            rad_lat = math.radians(p.angulo_olhar + 90 * self.dir_circular)
            p.vel[0] += math.cos(rad_lat) * 10.0
            p.vel[1] += math.sin(rad_lat) * 10.0
            self.acao_atual = "CIRCULAR"
            return True

        elif acao == "dodge_back":
            # Dash para trÃ¡s ao detectar ataque traseiro
            ang_fuga = math.atan2(p.pos[1] - inimigo.pos[1], p.pos[0] - inimigo.pos[0])
            impulso = 18.0
            p.vel[0] += math.cos(ang_fuga) * impulso
            p.vel[1] += math.sin(ang_fuga) * impulso
            self.cd_dash = 0.6
            self.acao_atual = "RECUAR"
            return True

        elif acao == "auto_block":
            # Levanta guarda â€” se tiver skill de escudo usa, senÃ£o postura de bloquear
            buff_skills = self.skills_por_tipo.get("BUFF", [])
            for skill in buff_skills:
                if skill.get("data", {}).get("escudo"):
                    if self._usar_skill(skill):
                        return True
            self.acao_atual = "BLOQUEAR"
            return True
        
        elif acao == "instant_counter":
            # Contra-ataque instantÃ¢neo
            self.acao_atual = "CONTRA_ATAQUE"
            self._executar_ataque(distancia, inimigo)
            return True
        
        elif acao == "auto_jump":
            # Pulo automÃ¡tico
            if self.cd_pulo <= 0 and hasattr(p, 'pular'):
                p.pular()
                self.cd_pulo = 0.3
                return True
        
        return False

    
    def get_agressividade_efetiva(self):
        """Retorna agressividade com modificadores de ritmo e situacionais temporÃ¡rios.
        BUG-AI-05 fix: modificadores situacionais vÃ£o em _agressividade_temp_mod (nÃ£o em agressividade_base),
        garantindo que a personalidade original nÃ£o seja corrompida ao longo da luta.
        """
        base = self.agressividade_base
        ritmo_mod = self.ritmo_modificadores.get("agressividade", 0)
        return max(0.0, min(1.0, base + ritmo_mod + self._agressividade_temp_mod))


    def _rand(self):
        """Retorna um float [0,1) do pool prÃ©-gerado por frame.
        QC-03: consome valores do pool criado em processar() em vez de chamar random.random()
        a cada modificador. Se o pool esgotar (mais de 8 consumos/frame), cai de volta
        em random.random() como seguranÃ§a â€” isso nunca deveria acontecer em fluxo normal.
        """
        pool = getattr(self, '_rand_pool', None)
        if pool:
            idx = getattr(self, '_rand_idx', 0)
            if idx < len(pool):
                self._rand_idx = idx + 1
                return pool[idx]
        return random.random()  # fallback de seguranÃ§a

