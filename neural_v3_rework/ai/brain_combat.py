"""Auto-generated mixin — see scripts/split_brain.py"""
import random
import math
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

from ai._brain_mixin_base import _AIBrainMixinBase


class CombatMixin(_AIBrainMixinBase):
    """Mixin de decisão de ataque, combos, baiting, momentum e movimento tático."""

    # MEL-AI-04: janela de observação pós-bait
    BAIT_JANELA_OBSERVACAO = 0.2  # segundos de observação após o bait terminar

    
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
        
        # Se está em combo, tenta continuar
        if combo["em_combo"] and combo["pode_followup"]:
            if self._tentar_followup(distancia, inimigo):
                return True
        
        # === ATAQUE DIRETO SE NO ALCANCE E NÃO ATACANDO ===
        if no_alcance and not p.atacando:
            # Chance base de atacar quando no alcance
            chance_base = 0.6
            
            # Aumenta chance se inimigo com pouca vida
            if inimigo.vida / inimigo.vida_max < 0.3:
                chance_base = 0.85
            
            # Modificadores de personalidade
            if "AGRESSIVO" in self.tracos or "BERSERKER" in self.tracos:
                chance_base += 0.2
            if "CAUTELOSO" in self.tracos:
                chance_base -= 0.15
            if "OPORTUNISTA" in self.tracos:
                chance_base += 0.1
            
            # Momentum
            chance_base += self.momentum * 0.15
            
            if random.random() < chance_base:
                self._executar_ataque(distancia, inimigo)
                return True
        
        # Verifica se tem janela de oportunidade
        if janela["aberta"]:
            # Calcula se vale a pena atacar
            chance_ataque = janela["qualidade"]
            
            # Modificadores de distância
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
        
        elif tipo == "pos_bloqueio":
            # CB-02: contra-ataque imediato após bloqueio/parry bem-sucedido
            self.acao_atual = "CONTRA_ATAQUE"
            self.confianca = min(1.0, self.confianca + 0.12)
            return True
        
        return False

    
    def _executar_ataque(self, distancia, inimigo):
        """Executa um ataque baseado na distância e situação - v12.2"""
        p = self.parent
        
        # Usa alcance efetivo calculado
        alcance_efetivo = self._calcular_alcance_efetivo()
        
        # Escolhe tipo de ataque baseado na distância relativa ao alcance
        if distancia <= alcance_efetivo * 0.5:
            # Muito perto - ataque rápido
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
        
        # Seta flag de ataque diretamente (não existe método iniciar_ataque)
        if distancia <= alcance_efetivo * 1.1:
            # O ataque é executado via executar_ataques() em entities.py
            # Basta garantir que a ação seja ofensiva
            if self.acao_atual not in ["MATAR", "ESMAGAR", "COMBATE", "ATAQUE_RAPIDO", "PRESSIONAR", "CONTRA_ATAQUE", "POKE"]:
                self.acao_atual = "MATAR"

    
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


    def _processar_baiting(self, dt, distancia, inimigo):
        """Processa sistema de baiting/fintas"""
        bait = self.bait_state

        # --- FASE DE OBSERVAÇÃO PÓS-BAIT (MEL-AI-04) ---
        # Após a finta terminar, aguarda uma janela curta (0.2s) para capturar
        # somente reações imediatas do oponente — não comportamento agressivo padrão.
        if bait["fase_obs"]:
            bait["timer_obs"] -= dt
            if bait["timer_obs"] <= 0:
                bait["fase_obs"] = False
                return self._executar_contra_bait(distancia, inimigo)
            return True  # Mantém controle durante a janela de observação

        # Atualiza timer principal do bait
        if bait["ativo"]:
            bait["timer"] -= dt
            # FP-04 fix: registra ação do inimigo no início do bait para comparar depois
            if bait.get("acao_inimigo_antes") is None and hasattr(inimigo, 'ai') and inimigo.ai:
                bait["acao_inimigo_antes"] = inimigo.ai.acao_atual
            if bait["timer"] <= 0:
                # MEL-AI-04: não avalia imediatamente — inicia janela de observação
                bait["ativo"] = False
                bait["fase_obs"] = True
                bait["timer_obs"] = self.BAIT_JANELA_OBSERVACAO
                return True
        
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
            if self.momentum < AI_MOMENTUM_NEGATIVO:  # Perdendo, tenta enganar
                chance_bait += 0.1
            if self.leitura_oponente["agressividade_percebida"] > 0.7:
                chance_bait += 0.1  # Oponente agressivo, fácil de baitar
            
            if 3.0 < distancia < 6.0 and random.random() < chance_bait:
                tipo_bait = random.choice(["recuo_falso", "abertura_falsa", "hesitacao_falsa"])
                bait["ativo"] = True
                bait["tipo"] = tipo_bait
                bait["timer"] = random.uniform(0.3, 0.6)
                # FP-04 fix: salva ação atual do inimigo para detectar mudança real
                bait["acao_inimigo_antes"] = (
                    inimigo.ai.acao_atual
                    if hasattr(inimigo, 'ai') and inimigo.ai else None
                )
                
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
        
        # FP-04 fix: verifica mudança REAL de comportamento do oponente.
        # Antes: contava como sucesso qualquer comportamento agressivo (incluindo o padrão).
        # Agora: só conta se o inimigo mudou de uma ação neutra/defensiva para agressiva
        # dentro da janela do bait.
        oponente_caiu = False
        if hasattr(inimigo, 'ai') and inimigo.ai:
            acao_antes = bait.get("acao_inimigo_antes")
            acao_agora = inimigo.ai.acao_atual
            acoes_agressivas = {"APROXIMAR", "MATAR", "ESMAGAR", "PRESSIONAR"}
            acoes_neutras_defensivas = {
                "CIRCULAR", "BLOQUEAR", "RECUAR", "FUGIR", "COMBATE",
                "FLANQUEAR", "NEUTRO", None
            }
            # Sucesso = estava neutro/defensivo E agora está agressivo (mudou por causa do bait)
            if acao_antes in acoes_neutras_defensivas and acao_agora in acoes_agressivas:
                oponente_caiu = True
        bait["acao_inimigo_antes"] = None  # Limpa para o próximo bait
        
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
    # MOVIMENTO v8.0 COM INTELIGÊNCIA HUMANA
    # =========================================================================
    
    # =========================================================================
    # MEL-AI-02 — SISTEMA DE DECISÃO DE MOVIMENTO v13.0 (STRATEGY PATTERN)
    # =========================================================================
    # `_decidir_movimento` agora é um dispatcher puro: aplica overrides globais,
    # delega para o método correto de acordo com o tipo de arma e, para o caminho
    # genérico, aplica o sistema de pesos acumulativos (MEL-AI-03).
    #
    # Cada tipo de arma tem seu próprio método `_estrategia_*`, facilitando:
    #   - Adicionar novos tipos sem inflar o método principal
    #   - Testar e ajustar balanço por arma de forma isolada
    #   - Rastrear qual estratégia tomou controle (DEBUG_AI_DECISIONS)

    def _decidir_movimento(self, distancia, inimigo):
        """Dispatcher de decisão de movimento — v13.0 Strategy Pattern"""
        p = self.parent
        roll = random.random()
        hp_pct = p.vida / p.vida_max
        inimigo_hp_pct = inimigo.vida / inimigo.vida_max if inimigo.vida_max > 0 else 1.0

        alcance_efetivo = self._calcular_alcance_efetivo()
        alcance_ideal   = p.alcance_ideal
        no_alcance      = distancia <= alcance_efetivo
        muito_perto     = distancia < alcance_ideal * 0.5

        debug = getattr(self, 'DEBUG_AI_DECISIONS', False)

        # ── OVERRIDES GLOBAIS DE ALTA PRIORIDADE ──────────────────────────────
        if hasattr(p, 'modo_adrenalina') and p.modo_adrenalina:
            self.acao_atual = "MATAR"
            if debug: _log.debug("[DECISAO] %s → override ADRENALINA → MATAR", p.dados.nome)
            return

        if hasattr(p, 'estamina') and p.estamina < 15:
            self.acao_atual = "ATAQUE_RAPIDO" if (no_alcance and roll < 0.4) else "RECUAR"
            if debug: _log.debug("[DECISAO] %s → override ESTAMINA_BAIXA → %s", p.dados.nome, self.acao_atual)
            return

        if self.modo_berserk:
            self.acao_atual = "MATAR"
            if debug: _log.debug("[DECISAO] %s → override BERSERK → MATAR", p.dados.nome)
            return

        if self.modo_defensivo:
            self.acao_atual = "CONTRA_ATAQUE" if (no_alcance and roll < 0.3) else ("RECUAR" if muito_perto else "COMBATE")
            if debug: _log.debug("[DECISAO] %s → override DEFENSIVO → %s", p.dados.nome, self.acao_atual)
            return

        if self.medo > 0.75 and "DETERMINADO" not in self.tracos and "FRIO" not in self.tracos:
            self.acao_atual = "ATAQUE_RAPIDO" if (no_alcance and roll < 0.25) else "FUGIR"
            if debug: _log.debug("[DECISAO] %s → override MEDO → %s", p.dados.nome, self.acao_atual)
            return

        # ── DELEGAÇÃO POR TIPO DE ARMA ─────────────────────────────────────────
        arma      = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        arma_tipo = arma.tipo if arma else ""

        if arma_tipo in ("Arco", "Arremesso"):
            self._estrategia_ranged(distancia, roll, alcance_efetivo, alcance_ideal, inimigo_hp_pct)
            if debug: _log.debug("[DECISAO] %s → estratégia RANGED → %s", p.dados.nome, self.acao_atual)
            return

        if arma_tipo == "Corrente":
            self._estrategia_corrente(distancia, roll, alcance_efetivo, alcance_ideal, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s → estratégia CORRENTE → %s", p.dados.nome, self.acao_atual)
            return

        if arma_tipo == "Dupla":
            self._estrategia_dupla(distancia, roll, alcance_efetivo, alcance_ideal, hp_pct, inimigo_hp_pct, arma)
            if debug: _log.debug("[DECISAO] %s → estratégia DUPLA → %s", p.dados.nome, self.acao_atual)
            return

        # ── CAMINHO GENÉRICO (MEL-AI-03: pesos acumulativos) ──────────────────
        self._estrategia_generica(distancia, roll, hp_pct, inimigo_hp_pct,
                                  alcance_efetivo, alcance_ideal, inimigo, debug)


    # ── ESTRATÉGIAS POR TIPO DE ARMA ──────────────────────────────────────────

    def _estrategia_ranged(self, distancia, roll, alcance_efetivo, alcance_ideal, inimigo_hp_pct):
        """Estratégia de posicionamento para armas de longa distância (Arco / Arremesso)."""
        perigosamente_perto = distancia < alcance_ideal * 0.4
        perto_demais        = distancia < alcance_ideal * 0.7
        distancia_boa       = alcance_ideal * 0.7 <= distancia <= alcance_efetivo
        longe_demais        = distancia > alcance_efetivo

        if perigosamente_perto:
            self.acao_atual = "FUGIR"
        elif perto_demais:
            self.acao_atual = "ATAQUE_RAPIDO" if roll < 0.3 else "RECUAR"
        elif distancia_boa:
            self.acao_atual = random.choice(["MATAR", "MATAR", "PRESSIONAR", "ATAQUE_RAPIDO"])
        elif longe_demais:
            self.acao_atual = "APROXIMAR"
        else:
            self.acao_atual = "MATAR"


    def _estrategia_corrente(self, distancia, roll, alcance_efetivo, alcance_ideal,
                              inimigo_hp_pct, arma):
        """Estratégia para armas de corrente (Mangual v3.1 + genérico)."""
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
                urgencia = 1.0 - (distancia / zona_morta)
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
        """Estratégia para armas duplas (Adagas Gêmeas v3.1 + genérico)."""
        arma_estilo   = getattr(arma, 'estilo', '') if arma else ''
        no_alcance    = distancia <= alcance_efetivo
        longe         = distancia > alcance_efetivo * 1.5
        muito_longe   = distancia > alcance_efetivo * 2.5

        if arma_estilo == "Adagas Gêmeas":
            engajamento = alcance_ideal
            pressao     = alcance_ideal * 1.30
            dash_curto  = alcance_ideal * 2.20

            em_engajamento = distancia <= engajamento
            em_pressao     = engajamento < distancia <= pressao
            em_dash        = pressao < distancia <= dash_curto

            combo_hits   = self.combo_atual  # CB-05: atributo pertence ao AIBrain (self), não ao parent
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


    # ── CAMINHO GENÉRICO COM PESOS ACUMULATIVOS (MEL-AI-03) ──────────────────

    def _estrategia_generica(self, distancia, roll, hp_pct, inimigo_hp_pct,
                              alcance_efetivo, alcance_ideal, inimigo, debug=False):
        """
        Caminho genérico de decisão usando sistema de pesos acumulativos.

        MEL-AI-03: em vez de 7 camadas de modificadores que sobrescrevem a ação
        anterior em cascata (podendo inverter completamente a decisão base), cada
        fonte de influência deposita pesos num dict {acao: peso}. A ação final é
        a de maior peso acumulado. Isso mantém todas as influências visíveis e
        proporciona decisões mais coerentes com a intenção principal da IA.
        """
        p = self.parent
        no_alcance       = distancia <= alcance_efetivo
        quase_no_alcance = distancia <= alcance_efetivo * 1.3
        longe            = distancia > alcance_efetivo * 1.5
        muito_longe      = distancia > alcance_efetivo * 2.5

        pesos: dict[str, float] = {}

        def votar(acao: str, peso: float) -> None:
            pesos[acao] = pesos.get(acao, 0.0) + peso

        # ── 1. BASE: posição e HP ──────────────────────────────────────────────
        if inimigo_hp_pct < 0.25 and no_alcance:
            votar("MATAR",  1.5); votar("ESMAGAR", 1.0)
        elif no_alcance:
            if inimigo_hp_pct < 0.3:
                votar("MATAR", 1.2); votar("ESMAGAR", 0.8)
            else:
                votar("MATAR", 0.6); votar("ATAQUE_RAPIDO", 0.5); votar("COMBATE", 0.4)
                votar("FLANQUEAR", 0.4); votar("CIRCULAR", 0.3); votar("PRESSIONAR", 0.3)
                votar("CONTRA_ATAQUE", 0.2)
        elif quase_no_alcance:
            votar("APROXIMAR", 0.7); votar("PRESSIONAR", 0.5); votar("FLANQUEAR", 0.4)
            votar("COMBATE", 0.3); votar("POKE", 0.2); votar("CIRCULAR", 0.2)
        elif longe or muito_longe:
            votar("APROXIMAR", 1.0); votar("PRESSIONAR", 0.4)

        # ── 2. TRAÇOS DE PERSONALIDADE ─────────────────────────────────────────
        if "COVARDE" in self.tracos and hp_pct < 0.35:
            # CB-07: vezes_que_fugiu é incrementado apenas em _tentar_dash_emergencia (execução real)
            if self.vezes_que_fugiu > 4:
                votar("MATAR", 2.0); self.raiva = 0.9
            else:
                votar("FUGIR", 2.0)
        if "BERSERKER" in self.tracos and hp_pct < 0.45:
            votar("MATAR", 2.0)
        if "SANGUINARIO" in self.tracos and inimigo_hp_pct < 0.3:
            votar("MATAR", 1.8)
        if "PREDADOR" in self.tracos and inimigo_hp_pct < 0.4:
            votar("APROXIMAR", 1.5)
        if "PERSEGUIDOR" in self.tracos and distancia > 5.0:
            votar("APROXIMAR", 1.5)
        if "KAMIKAZE" in self.tracos:
            votar("MATAR", 3.0)

        # ── 3. ESTILO DE LUTA ──────────────────────────────────────────────────
        estilo_data   = ESTILOS_LUTA.get(self.estilo_luta, ESTILOS_LUTA["BALANCED"])
        agressividade = estilo_data.get("agressividade_base", 0.6)
        agressividade = min(1.0, agressividade + min(0.2, self.tempo_combate / 60.0))
        if inimigo_hp_pct < 0.3: agressividade = min(1.0, agressividade + 0.25)
        if hp_pct < 0.25 and "BERSERKER" not in self.tracos: agressividade = max(0.3, agressividade - 0.1)

        if distancia < alcance_ideal * 0.7:
            votar(estilo_data["acao_perto"], agressividade * 0.8)
        elif distancia > alcance_efetivo * 1.3:
            votar(estilo_data["acao_longe"], agressividade * 0.8)
        else:
            votar(estilo_data["acao_medio"], agressividade * 0.8)

        # ── 4. TRAÇOS MODIFICADORES ────────────────────────────────────────────
        if "AGRESSIVO" in self.tracos:
            votar("MATAR", 0.4); votar("APROXIMAR", 0.3); votar("PRESSIONAR", 0.3)
        if "CALCULISTA" in self.tracos and distancia > 4.0:
            votar("FLANQUEAR", 0.4)
        if "PACIENTE" in self.tracos:
            votar("COMBATE", 0.3)
        if "IMPRUDENTE" in self.tracos:
            votar("MATAR", 0.5); votar("ESMAGAR", 0.4)
        if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
            for a in ["FLANQUEAR", "APROXIMAR", "ATAQUE_RAPIDO", "MATAR", "ESMAGAR", "POKE"]:
                votar(a, 0.15)
        if "FLANQUEADOR" in self.tracos:
            votar("FLANQUEAR", 0.5)
        if "VELOZ" in self.tracos:
            votar("FLANQUEAR", 0.3); votar("ATAQUE_RAPIDO", 0.3)
        if "SELVAGEM" in self.tracos:
            votar("MATAR", 0.3); votar("ESMAGAR", 0.2); votar("ATAQUE_RAPIDO", 0.2)
        if "TEIMOSO" in self.tracos:
            votar("MATAR", 0.3)
        if "FRIO" not in self.tracos and self.raiva > 0.6:
            votar("MATAR", self.raiva * 0.4); votar("ESMAGAR", self.raiva * 0.3)

        # ── 5. HUMOR ───────────────────────────────────────────────────────────
        humor_data = HUMORES.get(self.humor, HUMORES["CALMO"])
        mod_humor  = humor_data.get("mod_agressividade", 0.0)
        if mod_humor > 0.15:
            votar("MATAR", mod_humor * 0.5); votar("APROXIMAR", mod_humor * 0.3)
        elif mod_humor < -0.25:
            votar("COMBATE", abs(mod_humor) * 0.4); votar("RECUAR", abs(mod_humor) * 0.2)

        # ── 6. FILOSOFIA ───────────────────────────────────────────────────────
        if self._rand() < 0.2:
            filosofia_data = FILOSOFIAS.get(self.filosofia, FILOSOFIAS["EQUILIBRIO"])
            for a in filosofia_data["preferencia_acao"]:
                votar(a, 0.3)

        # ── 7. MOMENTUM ────────────────────────────────────────────────────────
        if self.momentum > AI_MOMENTUM_POSITIVO:
            votar("MATAR", 0.3); votar("PRESSIONAR", 0.2)
        elif self.momentum < AI_MOMENTUM_NEGATIVO:
            votar("RECUAR", 0.2); votar("COMBATE", 0.2); votar("CIRCULAR", 0.1)

        # ── 8. LEITURA DO OPONENTE (intercepção) ───────────────────────────────
        leitura = self.leitura_oponente
        if leitura["previsibilidade"] > AI_PREVISIBILIDADE_ALTA:
            tend_esq = leitura.get("tendencia_esquerda", 0.5)
            if tend_esq > 0.60: self.dir_circular = 1
            elif tend_esq < 0.40: self.dir_circular = -1

            # M-N01: calcula posição futura real do oponente e armazena como alvo de intercepção
            tempo_reacao = getattr(self, 'timer_decisao', 0.2)
            vel_in = getattr(inimigo, 'vel', (0.0, 0.0))
            pos_in = getattr(inimigo, 'pos', (0.0, 0.0))
            self._pos_interceptacao = (
                pos_in[0] + vel_in[0] * tempo_reacao,
                pos_in[1] + vel_in[1] * tempo_reacao,
            )

            if leitura["agressividade_percebida"] > 0.6:
                votar("CONTRA_ATAQUE", 0.6)
            elif leitura.get("frequencia_pulo", 0) > 0.35 and distancia < 5.0:
                votar("COMBATE", 0.5)
            else:
                votar("PRESSIONAR", 0.4)
        else:
            self._pos_interceptacao = None  # sem previsão suficiente — não interceptar
        if leitura["agressividade_percebida"] > AI_AGRESSIVIDADE_ALTA:
            if "REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos:
                votar("CONTRA_ATAQUE", 0.4)
        if leitura.get("frequencia_pulo", 0) > 0.4:
            votar("COMBATE", 0.25)
        if distancia < 4.0:
            tend = leitura.get("tendencia_esquerda", 0.5)
            if tend > 0.65: self.dir_circular = 1
            elif tend < 0.35: self.dir_circular = -1

        # ── 9. MODIFICADORES ESPACIAIS ─────────────────────────────────────────
        self._aplicar_modificadores_espaciais(distancia, inimigo)    # ainda seta acao_atual diretamente
        if self.acao_atual not in ("NEUTRO",):
            votar(self.acao_atual, 0.6)   # reincorpora decisão espacial como voto extra

        # ── 10. MODIFICADORES DE ARMAS ─────────────────────────────────────────
        self._aplicar_modificadores_armas(distancia, inimigo)        # idem
        if self.acao_atual not in ("NEUTRO",):
            votar(self.acao_atual, 0.5)

        # ── ANTI-REPETIÇÃO ─────────────────────────────────────────────────────
        if len(self.historico_acoes) >= 3:
            ultimas_3 = self.historico_acoes[-3:]
            acao_rep = self.acao_atual
            if ultimas_3.count(acao_rep) >= 2:
                pesos[acao_rep] = pesos.get(acao_rep, 0.0) * 0.5   # penaliza repetição

        # ── DECISÃO FINAL ──────────────────────────────────────────────────────
        if pesos:
            acao_escolhida = max(pesos, key=pesos.__getitem__)
            if debug:
                top3 = sorted(pesos.items(), key=lambda x: x[1], reverse=True)[:3]
                _log.debug("[DECISAO] %s → genérico | top3=%s", p.dados.nome, top3)
            self.acao_atual = acao_escolhida

    
    # L-N02: métodos [DEPRECIADO] removidos (Sprint 4) — lógica já absorvida em _estrategia_generica

    def _calcular_alcance_efetivo(self):
        """Calcula alcance real de ataque baseado na arma e hitbox profile v12.2"""
        p = self.parent
        
        arma = p.dados.arma_obj if p.dados else None
        if not arma:
            return 2.0  # Fallback sem arma
        
        tipo = arma.tipo
        raio = p.raio_fisico if hasattr(p, 'raio_fisico') else 0.4
        
        # Importa perfis de hitbox para cálculo preciso (QC-04: HITBOX_PROFILES no módulo)
        try:
            profile = HITBOX_PROFILES.get(tipo, HITBOX_PROFILES.get("Reta", {}))
            range_mult = profile.get("range_mult", 2.0)
        except (KeyError, AttributeError):
            range_mult = 2.0
        
        # Alcance base = raio do personagem * multiplicador do tipo de arma
        alcance_base = raio * range_mult
        
        # Ajustes específicos por tipo
        # Alcance = raio × range_mult (geometria removida)
        if tipo == "Reta":
            return alcance_base
        
        elif tipo == "Dupla":
            return alcance_base
        
        elif tipo == "Corrente":
            zona_morta = alcance_base * profile.get("min_range_ratio", 0.25)
            return (alcance_base + zona_morta) / 2
        
        elif tipo == "Arremesso":
            # Projéteis: mantém distância média
            return alcance_base * 0.7
        
        elif tipo == "Arco":
            # Arco: ALCANCE TOTAL - flechas voam longe!
            return alcance_base * 1.0
        
        elif tipo == "Mágica":
            # Magia: distância média
            return alcance_base * 0.7
        
        elif tipo == "Orbital":
            # Orbitais: fica perto
            dist_orbe = getattr(arma, 'distancia', 50) / PPM
            return raio + dist_orbe * 0.8
        
        elif tipo == "Transformável":
            return alcance_base
        
        return alcance_base


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
