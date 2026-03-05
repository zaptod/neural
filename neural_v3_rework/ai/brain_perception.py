"""Auto-generated mixin — see scripts/split_brain.py"""
import random
import math
import logging
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from core.weapon_analysis import (  # noqa: F811
        get_weapon_profile as get_weapon_profile,
        compare_weapons as compare_weapons,
        get_safe_distance as get_safe_distance,
        evaluate_combat_position as evaluate_combat_position,
    )

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


class PerceptionMixin(_AIBrainMixinBase):
    """Mixin de leitura de oponente e percepção de armas."""


    # =========================================================================
    # SISTEMA DE LEITURA DO OPONENTE v8.0
    # =========================================================================
    
    def _atualizar_leitura_oponente(self, dt, distancia, inimigo):
        """Lê e antecipa os movimentos do oponente como um humano faria"""
        leitura = self.leitura_oponente
        
        # Detecta se oponente está preparando ataque
        # FP-03 fix: `acao_atual` é intenção de movimento, não execução real.
        # Só considera ataque iminente baseado em `acao_atual` se o inimigo está
        # dentro do alcance efetivo de ameaça (1.5× o alcance estimado do inimigo).
        alcance_inimigo_estimado = getattr(inimigo, 'alcance_ideal', 2.5)
        distancia_ameaca = alcance_inimigo_estimado * 1.5

        ataque_prep = False
        if hasattr(inimigo, 'atacando') and inimigo.atacando:
            ataque_prep = True
        if hasattr(inimigo, 'cooldown_ataque') and inimigo.cooldown_ataque < 0.2:
            # Cooldown baixo = recém atacou ou prestes a atacar; só relevante se perto
            if distancia < distancia_ameaca * 1.2:
                ataque_prep = True
        if hasattr(inimigo, 'ai') and inimigo.ai:
            ai_ini = inimigo.ai
            if ai_ini.acao_atual in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "CONTRA_ATAQUE"]:
                # FP-03 fix: intenção de ataque só é iminente se o inimigo está próximo o suficiente
                if distancia < distancia_ameaca:
                    ataque_prep = True
        
        leitura["ataque_iminente"] = ataque_prep
        
        # Calcula direção provável do ataque
        if hasattr(inimigo, 'vel') and (inimigo.vel[0] != 0 or inimigo.vel[1] != 0):
            leitura["direcao_provavel"] = math.degrees(math.atan2(inimigo.vel[1], inimigo.vel[0]))
        
        # Registra padrão de movimento
        vel_x = inimigo.vel[0] if hasattr(inimigo, 'vel') else 0
        vel_y = inimigo.vel[1] if hasattr(inimigo, 'vel') else 0
        z_val = inimigo.z if hasattr(inimigo, 'z') else 0
        mov_atual = (vel_x, vel_y, z_val)
        leitura["padrao_movimento"].append(mov_atual)
        if len(leitura["padrao_movimento"]) > 15:
            leitura["padrao_movimento"].pop(0)
        
        # Analisa tendência lateral (com dead zone para evitar oscilação com vel ≈ 0)
        if len(leitura["padrao_movimento"]) >= 5:
            lateral_sum = sum(m[0] for m in leitura["padrao_movimento"][-5:])
            if abs(lateral_sum) > 0.5:
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

        # === BUG-AI-01 fix: detecta se inimigo está reposicionando ===
        # Reposicionando = movimentação lateral/recuo sem intenção de ataque imediato
        inimigo_reposiciona = False
        if hasattr(inimigo, 'ai') and inimigo.ai:
            acao_ini = inimigo.ai.acao_atual
            inimigo_reposiciona = acao_ini in ["CIRCULAR", "FLANQUEAR", "APROXIMAR", "RECUAR"]
            # Só conta como reposicionamento se NÃO está em iminência de ataque
            if leitura["ataque_iminente"]:
                inimigo_reposiciona = False
        leitura["reposicionando"] = inimigo_reposiciona

        # === BUG-AI-02 fix: detecta whiff (ataque do inimigo que não acertou) ===
        inimigo_atacando_agora = (
            (hasattr(inimigo, 'atacando') and inimigo.atacando) or
            (hasattr(inimigo, 'ai') and inimigo.ai and
             inimigo.ai.acao_atual in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"])
        )
        if self._inimigo_estava_atacando and not inimigo_atacando_agora:
            # Inimigo parou de atacar — verifica se não acertou (hits_recebidos não aumentou)
            if self.hits_recebidos_total == self._hits_recebidos_antes_ataque_ini:
                # Whiff confirmado! Abre janela de punição
                self.janela_ataque["aberta"] = True
                self.janela_ataque["tipo"] = "whiff"
                self.janela_ataque["qualidade"] = 0.90
                self.janela_ataque["duracao"] = 0.6
        # Salva estado atual para próximo frame
        if not self._inimigo_estava_atacando and inimigo_atacando_agora:
            self._hits_recebidos_antes_ataque_ini = self.hits_recebidos_total
        self._inimigo_estava_atacando = inimigo_atacando_agora

        # === BUG-AI-04 fix: atualiza padrao_detectado a partir da previsibilidade calculada ===
        leitura["padrao_detectado"] = leitura["previsibilidade"] > AI_PREVISIBILIDADE_ALTA

    
    # =========================================================================
    # SISTEMA DE PERCEPÇÃO DE ARMAS v10.0
    # =========================================================================
    
    def _atualizar_percepcao_armas(self, dt, distancia, inimigo):
        """
        Atualiza percepção da arma inimiga e calcula estratégias.
        Chamado no processar() principal.
        """
        if not WEAPON_ANALYSIS_AVAILABLE:
            return
        
        perc = self.percepcao_arma
        p = self.parent
        
        # Otimização: só analisa a cada 0.5s ou quando mudou
        perc["last_analysis_time"] += dt
        if perc["last_analysis_time"] < 0.5:
            return
        perc["last_analysis_time"] = 0.0
        
        # === ANÁLISE DA MINHA ARMA ===
        minha_arma = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        meu_perfil = get_weapon_profile(minha_arma)
        
        if meu_perfil:
            perc["minha_arma_perfil"] = meu_perfil
            perc["meu_alcance_efetivo"] = meu_perfil.alcance_maximo
            perc["minha_velocidade_ataque"] = meu_perfil.velocidade_rating
            perc["meu_arco_cobertura"] = meu_perfil.arco_ataque
        
        # === ANÁLISE DA ARMA INIMIGA ===
        arma_inimigo = None
        if hasattr(inimigo, 'dados') and hasattr(inimigo.dados, 'arma_obj'):
            arma_inimigo = inimigo.dados.arma_obj
        
        perfil_inimigo = get_weapon_profile(arma_inimigo)
        
        # Verifica se arma do inimigo mudou
        tipo_atual = arma_inimigo.tipo if arma_inimigo else None
        if tipo_atual != perc["arma_inimigo_tipo"]:
            perc["enemy_weapon_changed"] = True
            perc["arma_inimigo_tipo"] = tipo_atual
        else:
            perc["enemy_weapon_changed"] = False
        
        if perfil_inimigo:
            perc["arma_inimigo_perfil"] = perfil_inimigo
            perc["alcance_inimigo"] = perfil_inimigo.alcance_maximo
            perc["zona_perigo_inimigo"] = perfil_inimigo.alcance_maximo * 1.2
            perc["velocidade_inimigo"] = perfil_inimigo.velocidade_rating
            
            # Calcula ponto cego do inimigo
            if perfil_inimigo.pontos_cegos:
                # Pega o primeiro ponto cego significativo
                for _, _, arco_cego in perfil_inimigo.pontos_cegos:
                    if arco_cego >= 90:
                        perc["ponto_cego_inimigo"] = 180  # Atrás
                        break
        
        # === ANÁLISE DE MATCHUP ===
        if meu_perfil and perfil_inimigo:
            # Vantagem de alcance
            perc["vantagem_alcance"] = (meu_perfil.alcance_maximo - perfil_inimigo.alcance_maximo) / 2.0
            
            # Vantagem de velocidade
            perc["vantagem_velocidade"] = meu_perfil.velocidade_rating - perfil_inimigo.velocidade_rating
            
            # Vantagem de cobertura
            perc["vantagem_cobertura"] = (meu_perfil.arco_ataque - perfil_inimigo.arco_ataque) / 90.0
            
            # Matchup geral
            comparacao = compare_weapons(minha_arma, arma_inimigo)
            if comparacao["vencedor"] == 1:
                perc["matchup_favoravel"] = comparacao["diferenca"] * 0.5
            elif comparacao["vencedor"] == 2:
                perc["matchup_favoravel"] = -comparacao["diferenca"] * 0.5
            else:
                perc["matchup_favoravel"] = 0.0
            
            # Limita entre -1 e 1
            perc["matchup_favoravel"] = max(-1.0, min(1.0, perc["matchup_favoravel"]))
            
            # Calcula distâncias táticas
            perc["distancia_segura"] = get_safe_distance(minha_arma, arma_inimigo)
            if meu_perfil.alcance_ideal:
                perc["distancia_ataque"] = meu_perfil.alcance_ideal
            
            # Define estratégia recomendada
            self._calcular_estrategia_armas(distancia, inimigo)

    
    def _calcular_estrategia_armas(self, distancia, inimigo):
        """
        Calcula estratégia recomendada baseada no matchup de armas.
        """
        perc = self.percepcao_arma
        p = self.parent
        
        # Avalia posição de combate
        ang_relativo = 0.0
        if hasattr(inimigo, 'angulo_olhar'):
            # Calcula ângulo entre direção que inimigo olha e minha posição
            dx = p.pos[0] - inimigo.pos[0]
            dy = p.pos[1] - inimigo.pos[1]
            ang_para_mim = math.degrees(math.atan2(dy, dx))
            ang_relativo = ang_para_mim - inimigo.angulo_olhar
        
        # Usa o sistema de avaliação de posição
        avaliacao = evaluate_combat_position(
            p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None,
            inimigo.dados.arma_obj if hasattr(inimigo.dados, 'arma_obj') else None,
            distancia,
            ang_relativo
        )
        
        perc["estrategia_recomendada"] = avaliacao["recomendacao"]
        
        # Ajusta alcance ideal baseado no matchup
        if perc["matchup_favoravel"] > 0.3:
            # Matchup favorável - fico na minha distância ideal
            p.alcance_ideal = perc.get("distancia_ataque", 2.0)
        elif perc["matchup_favoravel"] < -0.3:
            # Matchup desfavorável - ajusto baseado no estilo
            perfil_ini = perc.get("arma_inimigo_perfil")
            if perfil_ini:
                # Se inimigo tem mais alcance, aproximo; se menos, afasto
                if perc["vantagem_alcance"] < -0.5:
                    # Preciso aproximar pra atacar
                    p.alcance_ideal = max(1.0, perfil_ini.zona_morta * 0.8)
                elif perc["vantagem_alcance"] > 0.5:
                    # Mantenho distância segura
                    p.alcance_ideal = perc["distancia_segura"] * 0.9

    
    def _aplicar_modificadores_armas(self, distancia, inimigo):
        """
        Aplica modificadores de comportamento baseados na percepção de armas.
        Chamado em _decidir_movimento().
        """
        if not WEAPON_ANALYSIS_AVAILABLE:
            return
        
        perc = self.percepcao_arma
        p = self.parent
        
        # Variáveis locais necessárias para cálculos baseados em arma
        alcance_efetivo = self._calcular_alcance_efetivo()
        roll = random.random()
        arma_inimigo = None
        if hasattr(inimigo, 'dados') and hasattr(inimigo.dados, 'arma_obj'):
            arma_inimigo = inimigo.dados.arma_obj
        
        estrategia = perc.get("estrategia_recomendada", "neutro")
        matchup = perc.get("matchup_favoravel", 0.0)
        
        # Ajustes de confiança baseados no matchup
        if matchup > 0.3:
            self.confianca = min(1.0, self.confianca + 0.1)
        elif matchup < -0.3:
            self.confianca = max(0.0, self.confianca - 0.1)
        
        # Aplica estratégia recomendada (com chance de ignorar baseado em personalidade)
        segue_estrategia = random.random() < 0.7  # 70% de chance base
        
        if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
            segue_estrategia = random.random() < 0.3
        elif "CALCULISTA" in self.tracos or "TATICO" in self.tracos:
            segue_estrategia = random.random() < 0.9
        elif "BERSERKER" in self.tracos:
            segue_estrategia = False  # Ignora estratégia, só ataca
        
        if not segue_estrategia:
            return
        
        # Aplica estratégia
        if estrategia == "atacar":
            if random.random() < 0.4:
                self.acao_atual = random.choice(["MATAR", "APROXIMAR", "PRESSIONAR"])
        
        elif estrategia == "recuar":
            if random.random() < 0.5:
                self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "FLANQUEAR"])
        
        elif estrategia == "atacar_rapido":
            if random.random() < 0.5:
                self.acao_atual = random.choice(["ATAQUE_RAPIDO", "CONTRA_ATAQUE"])
        
        elif estrategia == "esperar":
            if random.random() < 0.4:
                self.acao_atual = random.choice(["COMBATE", "BLOQUEAR", "COMBATE"])
        
        elif estrategia == "aproximar":
            if random.random() < 0.3:
                self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR"])
        
        # === COMPORTAMENTOS ESPECÍFICOS POR TIPO DE ARMA INIMIGA ===
        # v2.0: inclui lógica contra Mangual e Adagas Gêmeas reformulados
        tipo_ini = perc.get("arma_inimigo_tipo", "")
        arma_inimigo_estilo = ""
        if arma_inimigo and hasattr(arma_inimigo, 'estilo'):
            arma_inimigo_estilo = arma_inimigo.estilo
        
        # Contra Adagas Gêmeas: são muito rápidas, não deixar entrar no combo
        if tipo_ini == "Dupla" and arma_inimigo_estilo == "Adagas Gêmeas":
            # Adagas Gêmeas são letais de perto mas frágeis
            # Manter distância e punir a aproximação
            dist_segura = alcance_efetivo * 1.2  # Fica além do alcance das adagas
            if distancia < dist_segura and roll < 0.45:
                self.acao_atual = random.choice(["RECUAR", "FLANQUEAR", "RECUAR"])
        
        if tipo_ini == "Corrente":
            arma_ini_estilo = arma_inimigo.estilo if arma_inimigo and hasattr(arma_inimigo, 'estilo') else ''
            
            if arma_ini_estilo == "Mangual":
                # v2.0 CONTRA MANGUAL: o Mangual tem zona morta enorme
                # Estratégia: entrar NA ZONA MORTA (muito perto) para anular o spin
                # OU ficar MUITO LONGE fora do alcance total
                alcance_mangual = perc.get("alcance_inimigo", 4.0)
                zona_morta_estimada = alcance_mangual * 0.40  # v3.0: zona morta 40%
                
                if distancia > alcance_mangual * 0.9:
                    pass  # Fora do alcance: mantém distância segura
                elif distancia > zona_morta_estimada * 2:
                    # Na zona de perigo: tenta entrar na zona morta para anular
                    self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "FLANQUEAR"])
                # Se dentro da zona morta: o Mangual é ineficaz → ataca!

            elif arma_ini_estilo == "Kusarigama":
                # v5.0 CONTRA KUSARIGAMA: Troca de modo é vulnerável
                # Manter distância média (fora do foice, dentro do peso)
                # para forçar troca de modos constante
                chain_mode_ini = getattr(inimigo, 'chain_mode', 0)
                if chain_mode_ini == 0:
                    # Modo foice (perto): manter distância
                    if distancia < 3.0 and roll < 0.55:
                        self.acao_atual = random.choice(["RECUAR", "FLANQUEAR"])
                else:
                    # Modo peso (longe): aproximar para forçar troca
                    if distancia > 4.0 and roll < 0.55:
                        self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR"])

            elif arma_ini_estilo == "Chicote":
                # v5.0 CONTRA CHICOTE: Sweet spot na ponta = 2x dano
                # Estratégia: ficar BEM PERTO (dentro da zona fraca) ou LONGE demais
                alcance_chicote = perc.get("alcance_inimigo", 5.0)
                zona_fraca = alcance_chicote * 0.5  # Dentro de 50% = dano fraco
                if distancia > zona_fraca and distancia < alcance_chicote:
                    # Na zona do CRACK: perigosíssimo, sai ou entra mais
                    if roll < 0.6:
                        self.acao_atual = random.choice(["APROXIMAR", "APROXIMAR", "RECUAR"])
                elif distancia < zona_fraca:
                    # Dentro da zona fraca: vantagem! Chicote fraco de perto
                    if roll < 0.65:
                        self.acao_atual = random.choice(["MATAR", "PRESSIONAR", "COMBATE"])

            elif arma_ini_estilo == "Meteor Hammer":
                # v5.0 CONTRA METEOR HAMMER: Spin contínuo cria zona 360°
                # Estratégia: ficar FORA quando está girando, punir quando NÃO gira
                is_spinning = getattr(inimigo, 'chain_spinning', False)
                if is_spinning:
                    alcance_meteor = perc.get("alcance_inimigo", 5.0)
                    if distancia < alcance_meteor * 1.1:
                        # Dentro da zona de spin: sair URGENTE
                        self.acao_atual = random.choice(["RECUAR", "RECUAR", "FLANQUEAR"])
                    # Fora da zona: esperar ele parar
                else:
                    # Não está girando: momento de atacar
                    if distancia < 4.0 and roll < 0.6:
                        self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "COMBATE"])

            elif "Corrente com Peso" in arma_ini_estilo:
                # v5.0 CONTRA CORRENTE COM PESO: Pull + Slow é letal
                # Estratégia: manter distância máxima, nunca deixar puxar
                is_slowed = getattr(self.lutador, 'slow_timer', 0) > 0
                if is_slowed:
                    # Estou lento: foge desesperadamente
                    self.acao_atual = random.choice(["RECUAR", "RECUAR", "FLANQUEAR"])
                elif distancia < 3.5 and roll < 0.5:
                    # Perto demais: risco de pull
                    self.acao_atual = random.choice(["RECUAR", "FLANQUEAR"])
                elif distancia > 5.0 and roll < 0.4:
                    # Seguro: mantém distância ou aproveita para poke
                    self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR"])

            else:
                # Contra correntes genéricas (fallback)
                if distancia < perc.get("distancia_segura", 3.0) * 0.5:
                    if random.random() < 0.6:
                        self.acao_atual = random.choice(["MATAR", "PRESSIONAR"])
                elif distancia < perc.get("zona_perigo_inimigo", 4.0):
                    if random.random() < 0.5:
                        self.acao_atual = random.choice(["APROXIMAR", "RECUAR"])
        
        elif tipo_ini == "Arco":
            # Contra arcos: flanqueia e aproxima
            if distancia > 5.0:
                if random.random() < 0.6:
                    self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR"])
        
        elif tipo_ini == "Mágica":
            # Contra mágica: pressiona para não deixar canalizar
            if random.random() < 0.4:
                self.acao_atual = random.choice(["PRESSIONAR", "APROXIMAR"])
        
        elif tipo_ini == "Orbital":
            # Contra orbital: cuidado com o escudo
            if random.random() < 0.4:
                self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR"])


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

    @staticmethod
    def _id_oponente(oponente) -> str:
        """Gera uma chave única para identificar o oponente entre lutas."""
        nome = getattr(getattr(oponente, 'dados', None), 'nome', None) or str(id(oponente))
        classe = getattr(oponente, 'classe_nome', '') or ''
        return f"{nome}::{classe}"


    def carregar_memoria_rival(self, oponente) -> None:
        """
        Carrega o histórico de confrontos anteriores contra o oponente e ajusta
        parâmetros iniciais de personalidade para refletir o aprendizado acumulado.
        Chamado logo após gerar personalidade, antes do primeiro frame de combate.
        """
        chave = self._id_oponente(oponente)
        hist = type(self)._historico_combates.get(chave)
        if not hist:
            return  # Primeiro encontro — sem ajuste

        lutas = hist.get("lutas", 0)
        if lutas == 0:
            return

        taxa_vitoria = hist.get("vitorias", 0) / lutas
        avg_hits_sofridos = hist.get("hits_sofridos_total", 0) / lutas
        avg_max_combo = hist.get("max_combo_total", 0) / lutas
        fugas = hist.get("fugas_total", 0) / lutas

        _log.debug(
            "[IA] %s: carregando rival '%s' — %d luta(s), %.0f%% vitórias",
            self.parent.dados.nome, chave, lutas, taxa_vitoria * 100,
        )

        # Adapta agressividade: venceu muito → mais ousado; perdeu muito → mais cauteloso
        delta_agg = (taxa_vitoria - 0.5) * 0.2
        self.agressividade_base = max(0.05, min(1.0, self.agressividade_base + delta_agg))

        # Muitos hits sofridos → aumenta medo inicial (mais defensivo)
        if avg_hits_sofridos > 5:
            self.medo = min(0.4, avg_hits_sofridos * 0.03)

        # Rival tem combo alto → mais cauteloso, adiciona traço REATIVO se ausente
        if avg_max_combo > 4 and "REATIVO" not in self.tracos:
            self.tracos.append("REATIVO")

        # Fugiu muito nas últimas lutas → inibe fuga repetida
        if fugas > 3 and "TEIMOSO" not in self.tracos:
            self.tracos.append("TEIMOSO")


    def salvar_memoria_rival(self, oponente, venceu: bool) -> None:
        """
        Persiste as estatísticas desta luta para uso em confrontos futuros.
        Chamado ao fim de cada combate (ex: em on_luta_encerrada ou similar).
        """
        chave = self._id_oponente(oponente)
        hist = type(self)._historico_combates.setdefault(chave, {
            "lutas": 0,
            "vitorias": 0,
            "hits_sofridos_total": 0,
            "max_combo_total": 0,
            "fugas_total": 0,
        })
        hist["lutas"] += 1
        if venceu:
            hist["vitorias"] += 1
        hist["hits_sofridos_total"] += self.hits_recebidos_total
        hist["max_combo_total"] += self.max_combo
        hist["fugas_total"] += self.vezes_que_fugiu

        _log.debug(
            "[IA] %s: salvou memória rival '%s' — %d luta(s) registradas",
            self.parent.dados.nome, chave, hist["lutas"],
        )
