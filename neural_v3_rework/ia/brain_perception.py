"""Auto-generated mixin â€” see scripts/split_brain.py"""
import random
import math
import logging
from typing import TYPE_CHECKING

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
from ia.weapon_ai import arma_eh_ranged, obter_metricas_arma, resolver_familia_arma

try:
    from nucleo.weapon_analysis import (
        analisador_armas, get_weapon_profile, compare_weapons,
        get_safe_distance, evaluate_combat_position, ThreatLevel, WeaponStyle
    )
    WEAPON_ANALYSIS_AVAILABLE = True
except ImportError:
    WEAPON_ANALYSIS_AVAILABLE = False

if TYPE_CHECKING:
    from nucleo.weapon_analysis import (  # noqa: F811
        get_weapon_profile as get_weapon_profile,
        compare_weapons as compare_weapons,
        get_safe_distance as get_safe_distance,
        evaluate_combat_position as evaluate_combat_position,
    )

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


class PerceptionMixin(_AIBrainMixinBase):
    """Mixin de leitura de oponente e percepÃ§Ã£o de armas."""

    def _registrar_padrao_oponente(self, oponente, padrao, peso=1.0):
        """Registra um habito recorrente do oponente atual."""
        if not padrao or oponente is None or not hasattr(self, "_garantir_memoria_curta_oponente"):
            return
        bucket = self._garantir_memoria_curta_oponente(oponente)
        if bucket is None:
            return

        padroes = bucket.setdefault("padroes", {})
        padroes[padrao] = padroes.get(padrao, 0.0) + max(0.1, peso)

        dominante = max(padroes.items(), key=lambda item: item[1])
        dominante_nome, dominante_score = dominante
        segundo_score = max((v for k, v in padroes.items() if k != dominante_nome), default=0.0)

        if dominante_score >= 0.55 and dominante_score >= segundo_score + 0.30:
            self.memoria_oponente["padrao_dominante"] = dominante_nome
            self.memoria_oponente["padrao_detectado"] = dominante_nome

    def _obter_padrao_dominante_oponente(self, oponente):
        if oponente is None or not hasattr(self, "_obter_vies_oponente"):
            return self.memoria_oponente.get("padrao_dominante")
        bucket = self._obter_vies_oponente(oponente)
        padroes = bucket.get("padroes", {}) if isinstance(bucket, dict) else {}
        if not padroes:
            return self.memoria_oponente.get("padrao_dominante")
        return max(padroes.items(), key=lambda item: item[1])[0]


    # =========================================================================
    # SISTEMA DE LEITURA DO OPONENTE v8.0
    # =========================================================================
    
    def _atualizar_leitura_oponente(self, dt, distancia, inimigo):
        """LÃª e antecipa os movimentos do oponente como um humano faria"""
        leitura = self.leitura_oponente
        
        # Detecta se oponente estÃ¡ preparando ataque
        # FP-03 fix: `acao_atual` Ã© intenÃ§Ã£o de movimento, nÃ£o execuÃ§Ã£o real.
        # SÃ³ considera ataque iminente baseado em `acao_atual` se o inimigo estÃ¡
        # dentro do alcance efetivo de ameaÃ§a (1.5Ã— o alcance estimado do inimigo).
        alcance_inimigo_estimado = getattr(inimigo, 'alcance_ideal', 2.5)
        distancia_ameaca = alcance_inimigo_estimado * 1.5

        ataque_prep = False
        if hasattr(inimigo, 'atacando') and inimigo.atacando:
            ataque_prep = True
        if hasattr(inimigo, 'cooldown_ataque') and inimigo.cooldown_ataque < 0.2:
            # Cooldown baixo = recÃ©m atacou ou prestes a atacar; sÃ³ relevante se perto
            if distancia < distancia_ameaca * 1.2:
                ataque_prep = True
        if hasattr(inimigo, 'brain') and inimigo.brain:
            ai_ini = inimigo.brain
            if ai_ini.acao_atual in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "CONTRA_ATAQUE"]:
                # FP-03 fix: intenÃ§Ã£o de ataque sÃ³ Ã© iminente se o inimigo estÃ¡ prÃ³ximo o suficiente
                if distancia < distancia_ameaca:
                    ataque_prep = True
        
        leitura["ataque_iminente"] = ataque_prep
        
        # Calcula direÃ§Ã£o provÃ¡vel do ataque
        if hasattr(inimigo, 'vel') and (inimigo.vel[0] != 0 or inimigo.vel[1] != 0):
            leitura["direcao_provavel"] = math.degrees(math.atan2(inimigo.vel[1], inimigo.vel[0]))
        
        # Registra padrÃ£o de movimento
        vel_x = inimigo.vel[0] if hasattr(inimigo, 'vel') else 0
        vel_y = inimigo.vel[1] if hasattr(inimigo, 'vel') else 0
        z_val = inimigo.z if hasattr(inimigo, 'z') else 0
        mov_atual = (vel_x, vel_y, z_val)
        leitura["padrao_movimento"].append(mov_atual)
        if len(leitura["padrao_movimento"]) > 15:
            leitura["padrao_movimento"].pop(0)
        
        # Analisa tendÃªncia lateral (com dead zone para evitar oscilaÃ§Ã£o com vel â‰ˆ 0)
        if len(leitura["padrao_movimento"]) >= 5:
            lateral_sum = sum(m[0] for m in leitura["padrao_movimento"][-5:])
            if abs(lateral_sum) > 0.5:
                if lateral_sum > 0:
                    leitura["tendencia_esquerda"] = max(0.2, leitura["tendencia_esquerda"] - 0.02)
                else:
                    leitura["tendencia_esquerda"] = min(0.8, leitura["tendencia_esquerda"] + 0.02)
        
        # Detecta frequÃªncia de pulos
        pulos_recentes = sum(1 for m in leitura["padrao_movimento"] if m[2] > 0)
        leitura["frequencia_pulo"] = pulos_recentes / max(1, len(leitura["padrao_movimento"]))
        
        # Calcula previsibilidade do oponente
        if len(leitura["padrao_movimento"]) >= 8:
            # Compara movimentos consecutivos - mais similares = mais previsÃ­vel
            variacoes = []
            for i in range(1, min(8, len(leitura["padrao_movimento"]))):
                m1 = leitura["padrao_movimento"][-i]
                m2 = leitura["padrao_movimento"][-i-1]
                var = abs(m1[0] - m2[0]) + abs(m1[1] - m2[1])
                variacoes.append(var)
            media_var = sum(variacoes) / len(variacoes) if variacoes else 1.0
            leitura["previsibilidade"] = max(0.1, min(0.9, 1.0 - (media_var / 20.0)))
        
        # Percebe agressividade do oponente
        if hasattr(inimigo, 'brain') and inimigo.brain:
            ai_ini = inimigo.brain
            if ai_ini.acao_atual in ["MATAR", "ESMAGAR", "PRESSIONAR", "APROXIMAR"]:
                leitura["agressividade_percebida"] = min(1.0, leitura["agressividade_percebida"] + 0.03)
            elif ai_ini.acao_atual in ["RECUAR", "FUGIR", "BLOQUEAR"]:
                leitura["agressividade_percebida"] = max(0.0, leitura["agressividade_percebida"] - 0.02)

        # === BUG-AI-01 fix: detecta se inimigo estÃ¡ reposicionando ===
        # Reposicionando = movimentaÃ§Ã£o lateral/recuo sem intenÃ§Ã£o de ataque imediato
        inimigo_reposiciona = False
        if hasattr(inimigo, 'brain') and inimigo.brain:
            acao_ini = inimigo.brain.acao_atual
            inimigo_reposiciona = acao_ini in ["CIRCULAR", "FLANQUEAR", "APROXIMAR", "RECUAR"]
            # SÃ³ conta como reposicionamento se NÃƒO estÃ¡ em iminÃªncia de ataque
            if leitura["ataque_iminente"]:
                inimigo_reposiciona = False
        leitura["reposicionando"] = inimigo_reposiciona

        # === BUG-AI-02 fix: detecta whiff (ataque do inimigo que nÃ£o acertou) ===
        inimigo_atacando_agora = (
            (hasattr(inimigo, 'atacando') and inimigo.atacando) or
            (hasattr(inimigo, 'brain') and inimigo.brain and
             inimigo.brain.acao_atual in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO"])
        )
        if self._inimigo_estava_atacando and not inimigo_atacando_agora:
            # Inimigo parou de atacar â€” verifica se nÃ£o acertou (hits_recebidos nÃ£o aumentou)
            if self.hits_recebidos_total == self._hits_recebidos_antes_ataque_ini:
                # Whiff confirmado! Abre janela de puniÃ§Ã£o
                self.janela_ataque["aberta"] = True
                self.janela_ataque["tipo"] = "whiff"
                self.janela_ataque["qualidade"] = 0.90
                self.janela_ataque["duracao"] = 0.6
        # Salva estado atual para prÃ³ximo frame
        if not self._inimigo_estava_atacando and inimigo_atacando_agora:
            self._hits_recebidos_antes_ataque_ini = self.hits_recebidos_total
        self._inimigo_estava_atacando = inimigo_atacando_agora

        # === BUG-AI-04 fix: atualiza padrao_detectado a partir da previsibilidade calculada ===
        leitura["padrao_detectado"] = leitura["previsibilidade"] > AI_PREVISIBILIDADE_ALTA

    
    # =========================================================================
    # SISTEMA DE PERCEPÃ‡ÃƒO DE ARMAS v10.0
    # =========================================================================
    
    def _atualizar_percepcao_armas(self, dt, distancia, inimigo):
        """
        Atualiza percepÃ§Ã£o da arma inimiga e calcula estratÃ©gias.
        Chamado no processar() principal.
        """
        perc = self.percepcao_arma
        p = self.parent
        
        # OtimizaÃ§Ã£o: sÃ³ analisa a cada 0.5s ou quando mudou
        perc["last_analysis_time"] += dt
        if perc["last_analysis_time"] < 0.5:
            return
        perc["last_analysis_time"] = 0.0
        
        # === ANÃLISE DA MINHA ARMA ===
        minha_arma = p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None
        minhas_metricas = obter_metricas_arma(minha_arma, p)
        meu_perfil = get_weapon_profile(minha_arma) if WEAPON_ANALYSIS_AVAILABLE else None
        
        if meu_perfil:
            perc["minha_arma_perfil"] = meu_perfil
            perc["meu_alcance_efetivo"] = meu_perfil.alcance_maximo
            perc["minha_velocidade_ataque"] = meu_perfil.velocidade_rating
            perc["meu_arco_cobertura"] = meu_perfil.arco_ataque
        else:
            perc["minha_arma_perfil"] = None
            perc["meu_alcance_efetivo"] = minhas_metricas["alcance_max"]
            perc["minha_velocidade_ataque"] = minhas_metricas["cadencia"]
            perc["meu_arco_cobertura"] = max(45.0, float(getattr(minha_arma, "arco_ataque", 90.0) or 90.0))
        
        # === ANÃLISE DA ARMA INIMIGA ===
        arma_inimigo = None
        if hasattr(inimigo, 'dados') and hasattr(inimigo.dados, 'arma_obj'):
            arma_inimigo = inimigo.dados.arma_obj
        
        metricas_inimigo = obter_metricas_arma(arma_inimigo, inimigo)
        familia_inimigo = resolver_familia_arma(arma_inimigo)
        perfil_inimigo = get_weapon_profile(arma_inimigo) if WEAPON_ANALYSIS_AVAILABLE else None
        
        # Verifica se arma do inimigo mudou
        tipo_atual = familia_inimigo if arma_inimigo else None
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
                        perc["ponto_cego_inimigo"] = 180  # AtrÃ¡s
                        break
        else:
            perc["arma_inimigo_perfil"] = None
            perc["alcance_inimigo"] = metricas_inimigo["alcance_max"]
            perc["zona_perigo_inimigo"] = metricas_inimigo["alcance_max"] * 1.2
            perc["velocidade_inimigo"] = metricas_inimigo["cadencia"]
            perc["ponto_cego_inimigo"] = 180 if familia_inimigo in {"corrente", "disparo", "foco"} else None
        
        # === ANÃLISE DE MATCHUP ===
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
            
            # Calcula distÃ¢ncias tÃ¡ticas
            perc["distancia_segura"] = get_safe_distance(minha_arma, arma_inimigo)
            if meu_perfil.alcance_ideal:
                perc["distancia_ataque"] = meu_perfil.alcance_ideal
            
            # Define estratÃ©gia recomendada
            self._calcular_estrategia_armas(distancia, inimigo)
        else:
            perc["vantagem_alcance"] = minhas_metricas["alcance_max"] - metricas_inimigo["alcance_max"]
            perc["vantagem_velocidade"] = minhas_metricas["cadencia"] - metricas_inimigo["cadencia"]
            perc["vantagem_cobertura"] = 0.0
            perc["matchup_favoravel"] = max(
                -1.0,
                min(1.0, perc["vantagem_alcance"] * 0.12 + perc["vantagem_velocidade"] * 0.18),
            )
            perc["distancia_segura"] = max(metricas_inimigo["alcance_min"] + 0.2, metricas_inimigo["alcance_tatico"] * 0.95)
            perc["distancia_ataque"] = minhas_metricas["alcance_tatico"]
            self._calcular_estrategia_armas(distancia, inimigo)

    
    def _calcular_estrategia_armas(self, distancia, inimigo):
        """
        Calcula estratÃ©gia recomendada baseada no matchup de armas.
        """
        perc = self.percepcao_arma
        p = self.parent
        
        # Avalia posiÃ§Ã£o de combate
        ang_relativo = 0.0
        if hasattr(inimigo, 'angulo_olhar'):
            # Calcula Ã¢ngulo entre direÃ§Ã£o que inimigo olha e minha posiÃ§Ã£o
            dx = p.pos[0] - inimigo.pos[0]
            dy = p.pos[1] - inimigo.pos[1]
            ang_para_mim = math.degrees(math.atan2(dy, dx))
            ang_relativo = ang_para_mim - inimigo.angulo_olhar
        
        # Usa o sistema de avaliaÃ§Ã£o de posiÃ§Ã£o
        avaliacao = evaluate_combat_position(
            p.dados.arma_obj if hasattr(p.dados, 'arma_obj') else None,
            inimigo.dados.arma_obj if hasattr(inimigo.dados, 'arma_obj') else None,
            distancia,
            ang_relativo
        )
        
        perc["estrategia_recomendada"] = avaliacao["recomendacao"]
        
        # CRIT-03 fix: antes, este mÃ©todo sobrescrevia p.alcance_ideal diretamente a
        # cada 0.5s, criando uma race condition com os ajustes de personalidade de
        # _definir_arquetipo_por_arma() e _aplicar_modificadores_iniciais().
        # Ex.: um Assassino COVARDE (alcance_ideal aumentado em 30%) tinha o ajuste
        # revertido pelo matchup de armas, lutando na distÃ¢ncia errada.
        #
        # SoluÃ§Ã£o: armazena o alcance tÃ¡tico como um OFFSET no percepcao_arma,
        # sem tocar p.alcance_ideal diretamente.  O offset Ã© somado em
        # _calcular_alcance_efetivo() apenas para decisÃ£o de posicionamento.
        perc["alcance_tatico_offset"] = 0.0  # reset

        if perc["matchup_favoravel"] > 0.3:
            # Matchup favorÃ¡vel â€” fica na distÃ¢ncia ideal da prÃ³pria arma (sem offset)
            perc["alcance_tatico_offset"] = 0.0
        elif perc["matchup_favoravel"] < -0.3:
            perfil_ini = perc.get("arma_inimigo_perfil")
            if perfil_ini:
                if perc["vantagem_alcance"] < -0.5:
                    # Inimigo tem mais alcance: aproximo atÃ© a zona morta dele
                    alvo = max(1.0, perfil_ini.zona_morta * 0.8)
                    perc["alcance_tatico_offset"] = alvo - p.alcance_ideal
                elif perc["vantagem_alcance"] > 0.5:
                    # Tenho mais alcance: fico na distÃ¢ncia segura
                    alvo = perc["distancia_segura"] * 0.9
                    perc["alcance_tatico_offset"] = alvo - p.alcance_ideal

    
    def _aplicar_modificadores_armas(self, distancia, inimigo):
        """
        Aplica modificadores de comportamento baseados na percepÃ§Ã£o de armas.
        Chamado em _decidir_movimento().
        """
        perc = self.percepcao_arma
        p = self.parent
        minha_arma = getattr(getattr(p, 'dados', None), 'arma_obj', None)
        minha_familia = resolver_familia_arma(minha_arma)
        sou_ranged = arma_eh_ranged(minha_arma)
        
        # VariÃ¡veis locais necessÃ¡rias para cÃ¡lculos baseados em arma
        alcance_efetivo = self._calcular_alcance_efetivo()
        roll = random.random()
        arma_inimigo = None
        if hasattr(inimigo, 'dados') and hasattr(inimigo.dados, 'arma_obj'):
            arma_inimigo = inimigo.dados.arma_obj
        familia_inimigo = resolver_familia_arma(arma_inimigo)
        
        estrategia = perc.get("estrategia_recomendada", "neutro")
        matchup = perc.get("matchup_favoravel", 0.0)
        tipo_ini = perc.get("arma_inimigo_tipo", "")

        # Melee vs Arco: recuar normalmente Ã© uma mÃ¡ escolha tÃ¡tica, porque o arqueiro
        # ganha tempo de kite e amplia vantagem de distÃ¢ncia. MantÃ©m recuo sÃ³ em HP crÃ­tico.
        if familia_inimigo == "disparo" and not sou_ranged:
            hp_pct = p.vida / max(p.vida_max, 1)
            if estrategia == "recuar" and hp_pct > 0.22:
                estrategia = "aproximar"
        
        # Ajustes de confianÃ§a baseados no matchup
        if matchup > 0.3:
            self.confianca = min(1.0, self.confianca + 0.1)
        elif matchup < -0.3:
            self.confianca = max(0.0, self.confianca - 0.1)
        
        # Aplica estratÃ©gia recomendada (com chance de ignorar baseado em personalidade)
        segue_estrategia = random.random() < 0.7  # 70% de chance base
        
        if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
            segue_estrategia = random.random() < 0.3
        elif "CALCULISTA" in self.tracos or "TATICO" in self.tracos:
            segue_estrategia = random.random() < 0.9
        elif "BERSERKER" in self.tracos:
            segue_estrategia = False  # Ignora estratÃ©gia, sÃ³ ataca
        
        if not segue_estrategia:
            return
        
        # Aplica estratÃ©gia
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
        
        # === COMPORTAMENTOS ESPECÃFICOS POR TIPO DE ARMA INIMIGA ===
        # v2.0: inclui lÃ³gica contra Mangual e Adagas GÃªmeas reformulados
        arma_inimigo_estilo = ""
        if arma_inimigo and hasattr(arma_inimigo, 'estilo'):
            arma_inimigo_estilo = arma_inimigo.estilo
        
        # Contra Adagas GÃªmeas: sÃ£o muito rÃ¡pidas, nÃ£o deixar entrar no combo
        if familia_inimigo == "dupla" and arma_inimigo_estilo == "Adagas GÃªmeas":
            # Adagas GÃªmeas sÃ£o letais de perto mas frÃ¡geis
            # Manter distÃ¢ncia e punir a aproximaÃ§Ã£o
            dist_segura = alcance_efetivo * 1.2  # Fica alÃ©m do alcance das adagas
            if distancia < dist_segura and roll < 0.45:
                self.acao_atual = random.choice(["RECUAR", "FLANQUEAR", "RECUAR"])
        
        if familia_inimigo == "corrente":
            arma_ini_estilo = arma_inimigo.estilo if arma_inimigo and hasattr(arma_inimigo, 'estilo') else ''
            
            if arma_ini_estilo == "Mangual":
                # v2.0 CONTRA MANGUAL: o Mangual tem zona morta enorme
                # EstratÃ©gia: entrar NA ZONA MORTA (muito perto) para anular o spin
                # OU ficar MUITO LONGE fora do alcance total
                alcance_mangual = perc.get("alcance_inimigo", 4.0)
                zona_morta_estimada = alcance_mangual * 0.40  # v3.0: zona morta 40%
                
                if distancia > alcance_mangual * 0.9:
                    pass  # Fora do alcance: mantÃ©m distÃ¢ncia segura
                elif distancia > zona_morta_estimada * 2:
                    # Na zona de perigo: tenta entrar na zona morta para anular
                    self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "FLANQUEAR"])
                # Se dentro da zona morta: o Mangual Ã© ineficaz â†’ ataca!

            elif arma_ini_estilo == "Kusarigama":
                # v5.0 CONTRA KUSARIGAMA: Troca de modo Ã© vulnerÃ¡vel
                # Manter distÃ¢ncia mÃ©dia (fora do foice, dentro do peso)
                # para forÃ§ar troca de modos constante
                chain_mode_ini = getattr(inimigo, 'chain_mode', 0)
                if chain_mode_ini == 0:
                    # Modo foice (perto): manter distÃ¢ncia
                    if distancia < 3.0 and roll < 0.55:
                        self.acao_atual = random.choice(["RECUAR", "FLANQUEAR"])
                else:
                    # Modo peso (longe): aproximar para forÃ§ar troca
                    if distancia > 4.0 and roll < 0.55:
                        self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR"])

            elif arma_ini_estilo == "Chicote":
                # v5.0 CONTRA CHICOTE: Sweet spot na ponta = 2x dano
                # EstratÃ©gia: ficar BEM PERTO (dentro da zona fraca) ou LONGE demais
                alcance_chicote = perc.get("alcance_inimigo", 5.0)
                zona_fraca = alcance_chicote * 0.5  # Dentro de 50% = dano fraco
                if distancia > zona_fraca and distancia < alcance_chicote:
                    # Na zona do CRACK: perigosÃ­ssimo, sai ou entra mais
                    if roll < 0.6:
                        self.acao_atual = random.choice(["APROXIMAR", "APROXIMAR", "RECUAR"])
                elif distancia < zona_fraca:
                    # Dentro da zona fraca: vantagem! Chicote fraco de perto
                    if roll < 0.65:
                        self.acao_atual = random.choice(["MATAR", "PRESSIONAR", "COMBATE"])

            elif arma_ini_estilo == "Meteor Hammer":
                # v5.0 CONTRA METEOR HAMMER: Spin contÃ­nuo cria zona 360Â°
                # EstratÃ©gia: ficar FORA quando estÃ¡ girando, punir quando NÃƒO gira
                is_spinning = getattr(inimigo, 'chain_spinning', False)
                if is_spinning:
                    alcance_meteor = perc.get("alcance_inimigo", 5.0)
                    if distancia < alcance_meteor * 1.1:
                        # Dentro da zona de spin: sair URGENTE
                        self.acao_atual = random.choice(["RECUAR", "RECUAR", "FLANQUEAR"])
                    # Fora da zona: esperar ele parar
                else:
                    # NÃ£o estÃ¡ girando: momento de atacar
                    if distancia < 4.0 and roll < 0.6:
                        self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "COMBATE"])

            elif "Corrente com Peso" in arma_ini_estilo:
                # v5.0 CONTRA CORRENTE COM PESO: Pull + Slow Ã© letal
                # EstratÃ©gia: manter distÃ¢ncia mÃ¡xima, nunca deixar puxar
                # CRIT-01 fix: self.lutador nÃ£o existe â€” atributo correto Ã© self.parent
                is_slowed = getattr(self.parent, 'slow_timer', 0) > 0
                if is_slowed:
                    # Estou lento: foge desesperadamente
                    self.acao_atual = random.choice(["RECUAR", "RECUAR", "FLANQUEAR"])
                elif distancia < 3.5 and roll < 0.5:
                    # Perto demais: risco de pull
                    self.acao_atual = random.choice(["RECUAR", "FLANQUEAR"])
                elif distancia > 5.0 and roll < 0.4:
                    # Seguro: mantÃ©m distÃ¢ncia ou aproveita para poke
                    self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR"])

            else:
                # Contra correntes genÃ©ricas (fallback)
                if distancia < perc.get("distancia_segura", 3.0) * 0.5:
                    if random.random() < 0.6:
                        self.acao_atual = random.choice(["MATAR", "PRESSIONAR"])
                elif distancia < perc.get("zona_perigo_inimigo", 4.0):
                    if random.random() < 0.5:
                        self.acao_atual = random.choice(["APROXIMAR", "RECUAR"])
        
        elif familia_inimigo == "disparo":
            # Contra arcos: melee precisa colar e cortar linha de tiro.
            # Antes sÃ³ reagia bem quando distancia > 5.0, gerando passividade entre 2.5-5.0m.
            if not sou_ranged:
                if distancia > alcance_efetivo * 1.0:
                    if random.random() < 0.85:
                        self.acao_atual = random.choice(["APROXIMAR", "APROXIMAR", "FLANQUEAR", "PRESSIONAR"])
                elif distancia > alcance_efetivo * 0.65:
                    if random.random() < 0.70:
                        self.acao_atual = random.choice(["PRESSIONAR", "FLANQUEAR", "MATAR"])
            else:
                # Espelho ranged vs ranged: ainda pode manter distÃ¢ncia e flanquear
                if distancia > 5.0 and random.random() < 0.6:
                    self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR"])
        
        elif familia_inimigo == "foco":
            # Contra foco: pressiona e corta espaço antes da trama de orbes crescer.
            orbes_ativas = len([o for o in getattr(inimigo, "buffer_orbes", []) if getattr(o, "ativo", False)])
            if not sou_ranged and distancia > max(2.1, alcance_efetivo * 0.75):
                self.acao_atual = random.choice(["PRESSIONAR", "APROXIMAR", "FLANQUEAR"])
            elif orbes_ativas >= 2 and roll < 0.65:
                self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR", "RECUAR"])

        elif familia_inimigo == "orbital":
            burst_pronto = getattr(inimigo, "orbital_burst_cd", 0.0) <= 0.0
            alcance_orbital = max(2.2, perc.get("alcance_inimigo", 2.0) + 0.4)
            if burst_pronto and distancia < alcance_orbital * 1.1:
                self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR", "RECUAR"])
            elif distancia > alcance_orbital * 1.6 and roll < 0.5:
                self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR"])

        elif familia_inimigo == "hibrida":
            forma_inimiga = int(getattr(inimigo, "transform_forma", getattr(arma_inimigo, "forma_atual", 0)) or 0)
            if forma_inimiga == 1:
                if distancia < perc.get("alcance_inimigo", 3.0) * 0.55 and roll < 0.55:
                    self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "FLANQUEAR"])
            else:
                if distancia > alcance_efetivo * 1.05 and roll < 0.55:
                    self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "FLANQUEAR"])

        # Ajustes para o ritmo da minha própria família
        if minha_familia == "foco":
            orbes_orbitando = len([o for o in getattr(p, "buffer_orbes", []) if getattr(o, "ativo", False) and getattr(o, "estado", "") == "orbitando"])
            if distancia < 2.4 and orbes_orbitando == 0:
                self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "FLANQUEAR"])
            elif orbes_orbitando >= 2 and distancia <= alcance_efetivo:
                self.acao_atual = random.choice(["COMBATE", "POKE", "PRESSIONAR"])

        elif minha_familia == "orbital":
            burst_pronto = getattr(p, "orbital_burst_cd", 0.0) <= 0.0
            if burst_pronto and distancia < max(3.2, alcance_efetivo * 1.15):
                self.acao_atual = random.choice(["PRESSIONAR", "COMBATE", "MATAR"])
            elif distancia > max(4.2, alcance_efetivo * 1.4):
                self.acao_atual = random.choice(["APROXIMAR", "FLANQUEAR"])

        elif minha_familia == "hibrida":
            forma_atual = int(getattr(p, "transform_forma", getattr(minha_arma, "forma_atual", 0)) or 0)
            if forma_atual == 0 and distancia > alcance_efetivo * 1.08:
                self.acao_atual = random.choice(["APROXIMAR", "PRESSIONAR", "FLANQUEAR"])
            elif forma_atual == 1 and distancia < max(1.5, alcance_efetivo * 0.58):
                self.acao_atual = random.choice(["RECUAR", "CIRCULAR", "POKE"])

        elif minha_familia == "corrente":
            if familia_inimigo in {"disparo", "foco"} and distancia > alcance_efetivo * 0.9 and roll < 0.55:
                self.acao_atual = random.choice(["FLANQUEAR", "APROXIMAR", "PRESSIONAR"])


    # =========================================================================
    # SISTEMA DE COREOGRAFIA
    # =========================================================================
    
    def _observar_oponente(self, inimigo, distancia):
        """Observa o que o oponente estÃ¡ fazendo"""
        if not hasattr(inimigo, 'brain') or not inimigo.brain:
            return

        ai_ini = inimigo.brain
        mem = self.memoria_oponente
        if hasattr(self, "_garantir_memoria_curta_oponente"):
            self._garantir_memoria_curta_oponente(inimigo)
        
        acao_oponente = ai_ini.acao_atual
        acao_anterior = mem.get("ultima_acao")
        familia_inimiga = ""
        if hasattr(inimigo, "dados"):
            familia_inimiga = resolver_familia_arma(getattr(inimigo.dados, "arma_obj", None))
        
        if acao_oponente != mem["ultima_acao"]:
            mem["ultima_acao"] = acao_oponente
            
            if acao_oponente in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "APROXIMAR"]:
                mem["vezes_atacou"] += 1
            elif acao_oponente in ["FUGIR", "RECUAR"]:
                mem["vezes_fugiu"] += 1
                # Sprint2: on_inimigo_fugiu nunca era chamado â€” momentum e janela de
                # perseguiÃ§Ã£o nunca abriam. Dispara apenas em transiÃ§Ãµes reais para fuga.
                if hasattr(self, 'on_inimigo_fugiu'):
                    self.on_inimigo_fugiu()

            if acao_anterior in ["APROXIMAR", "FLANQUEAR", "CIRCULAR"] and acao_oponente in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "CONTRA_ATAQUE"]:
                self._registrar_padrao_oponente(inimigo, "entrada_agressiva", 0.6)
            if acao_anterior in ["MATAR", "ESMAGAR", "ATAQUE_RAPIDO", "CONTRA_ATAQUE"] and acao_oponente in ["RECUAR", "FUGIR", "CIRCULAR", "BLOQUEAR"]:
                self._registrar_padrao_oponente(inimigo, "recuo_pos_ataque", 0.6)
            if acao_anterior in ["RECUAR", "CIRCULAR"] and acao_oponente == "BLOQUEAR":
                self._registrar_padrao_oponente(inimigo, "guarda_reativa", 0.55)
            if acao_oponente in ["FUGIR", "RECUAR"] and mem["vezes_fugiu"] >= 2:
                self._registrar_padrao_oponente(inimigo, "fuga_sob_pressao", 0.45)

        if familia_inimiga == "hibrida":
            forma_atual = int(getattr(inimigo, "transform_forma", getattr(getattr(inimigo, "dados", None), "arma_obj", None) and getattr(inimigo.dados.arma_obj, "forma_atual", 0) or 0) or 0)
            forma_anterior = mem.get("ultima_forma_hibrida")
            bonus_troca = getattr(inimigo, "transform_bonus_timer", 0.0) > 0.0
            if forma_anterior is not None and forma_atual != forma_anterior and bonus_troca:
                self._registrar_padrao_oponente(inimigo, "troca_forma_burst", 0.8)
            mem["ultima_forma_hibrida"] = forma_atual
        else:
            mem["ultima_forma_hibrida"] = None

        if familia_inimiga == "orbital":
            burst_pronto = getattr(inimigo, "orbital_burst_cd", 999.0) <= 0.0 and distancia <= max(3.4, getattr(inimigo, "alcance_ideal", 2.5) * 1.05)
            if burst_pronto and not mem.get("ultimo_burst_orbital_pronto", False):
                self._registrar_padrao_oponente(inimigo, "prepara_burst_orbital", 0.7)
            mem["ultimo_burst_orbital_pronto"] = burst_pronto
        else:
            mem["ultimo_burst_orbital_pronto"] = False
        
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
        """Gera uma reaÃ§Ã£o inteligente ao oponente"""
        mem = self.memoria_oponente
        padrao_dominante = self._obter_padrao_dominante_oponente(inimigo)

        if padrao_dominante == "prepara_burst_orbital" and distancia < 4.0:
            self.reacao_pendente = "ESQUIVAR" if self.cd_pulo <= 0 else "RECUAR"
            return

        if padrao_dominante == "troca_forma_burst" and distancia < 4.3:
            if "CALCULISTA" in self.tracos or "PACIENTE" in self.tracos:
                self.reacao_pendente = "CIRCULAR"
            else:
                self.reacao_pendente = "RECUAR"
            return
        
        if acao_oponente == "MATAR" and distancia < 4.0:
            if padrao_dominante == "entrada_agressiva":
                if "CALCULISTA" in self.tracos or "REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos:
                    self.reacao_pendente = "CONTRA_ATAQUE"
                    return
                if "COVARDE" in self.tracos or self.medo > 0.6:
                    self.reacao_pendente = "RECUAR"
                    return
            if "REATIVO" in self.tracos or "OPORTUNISTA" in self.tracos:
                self.reacao_pendente = "CONTRA_ATAQUE"
            elif "COVARDE" in self.tracos or self.medo > 0.6:
                self.reacao_pendente = "RECUAR"
            elif "BERSERKER" in self.tracos or self.raiva > 0.7:
                self.reacao_pendente = "CONTRA_MATAR"
            elif random.random() < 0.3:
                self.reacao_pendente = "ESQUIVAR"
        
        elif acao_oponente == "FUGIR":
            if padrao_dominante == "recuo_pos_ataque":
                self.reacao_pendente = "PERSEGUIR" if distancia < 5.5 else "PRESSIONAR"
                return
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
            if padrao_dominante == "guarda_reativa":
                if "CALCULISTA" in self.tracos or "OPORTUNISTA" in self.tracos:
                    self.reacao_pendente = "ESPERAR_ABERTURA"
                else:
                    self.reacao_pendente = "FLANQUEAR"
                return
            if "CALCULISTA" in self.tracos:
                self.reacao_pendente = "ESPERAR_ABERTURA"
            elif "IMPRUDENTE" in self.tracos or "AGRESSIVO" in self.tracos:
                self.reacao_pendente = "FURAR_GUARDA"
            elif self.filosofia == "PACIENCIA":
                self.reacao_pendente = "ESPERAR"

    @staticmethod
    def _id_oponente(oponente) -> str:
        """Gera uma chave Ãºnica para identificar o oponente entre lutas."""
        nome = getattr(getattr(oponente, 'dados', None), 'nome', None) or str(id(oponente))
        classe = getattr(oponente, 'classe_nome', '') or ''
        return f"{nome}::{classe}"


    def carregar_memoria_rival(self, oponente) -> None:
        """
        Carrega o histÃ³rico de confrontos anteriores contra o oponente e ajusta
        parÃ¢metros iniciais de personalidade para refletir o aprendizado acumulado.
        Chamado logo apÃ³s gerar personalidade, antes do primeiro frame de combate.
        """
        chave = self._id_oponente(oponente)
        hist = type(self)._historico_combates.get(chave)
        if not hist:
            return  # Primeiro encontro â€” sem ajuste

        lutas = hist.get("lutas", 0)
        if lutas == 0:
            return

        taxa_vitoria = hist.get("vitorias", 0) / lutas
        avg_hits_sofridos = hist.get("hits_sofridos_total", 0) / lutas
        avg_max_combo = hist.get("max_combo_total", 0) / lutas
        fugas = hist.get("fugas_total", 0) / lutas

        _log.debug(
            "[IA] %s: carregando rival '%s' â€” %d luta(s), %.0f%% vitÃ³rias",
            self.parent.dados.nome, chave, lutas, taxa_vitoria * 100,
        )

        # Adapta agressividade: venceu muito â†’ mais ousado; perdeu muito â†’ mais cauteloso
        delta_agg = (taxa_vitoria - 0.5) * 0.2
        self.agressividade_base = max(0.05, min(1.0, self.agressividade_base + delta_agg))

        # Muitos hits sofridos â†’ aumenta medo inicial (mais defensivo)
        if avg_hits_sofridos > 5:
            self.medo = min(0.4, avg_hits_sofridos * 0.03)

        # Rival tem combo alto â†’ mais cauteloso, adiciona traÃ§o REATIVO se ausente
        if avg_max_combo > 4 and "REATIVO" not in self.tracos:
            self.tracos.append("REATIVO")

        # Fugiu muito nas Ãºltimas lutas â†’ inibe fuga repetida
        if fugas > 3 and "TEIMOSO" not in self.tracos:
            self.tracos.append("TEIMOSO")

        bucket = self._garantir_memoria_curta_oponente(oponente) if hasattr(self, "_garantir_memoria_curta_oponente") else None
        if bucket is not None:
            bucket["vies_agressao"] = max(bucket.get("vies_agressao", 0.0), max(0.0, (taxa_vitoria - 0.5) * 0.6))
            bucket["vies_cautela"] = max(bucket.get("vies_cautela", 0.0), max(0.0, (0.5 - taxa_vitoria) * 0.7))
            respeito = min(1.0, avg_max_combo * 0.10 + avg_hits_sofridos * 0.03 + max(0.0, (0.45 - taxa_vitoria) * 0.9))
            vinganca = min(1.0, max(0.0, 0.5 - taxa_vitoria) * 1.35)
            obsessao = min(1.0, lutas * 0.12 + abs(taxa_vitoria - 0.5) * 0.20)
            caca = min(1.0, max(0.0, taxa_vitoria - 0.52) * 1.10 + min(0.35, fugas * 0.06))
            bucket["relacao_respeito"] = max(bucket.get("relacao_respeito", 0.0), respeito)
            bucket["relacao_vinganca"] = max(bucket.get("relacao_vinganca", 0.0), vinganca)
            bucket["relacao_obsessao"] = max(bucket.get("relacao_obsessao", 0.0), obsessao)
            bucket["relacao_caca"] = max(bucket.get("relacao_caca", 0.0), caca)
            if hasattr(self, "_atualizar_relacao_dominante_bucket"):
                self._atualizar_relacao_dominante_bucket(bucket)
            if avg_max_combo > 4:
                self._registrar_padrao_oponente(oponente, "entrada_agressiva", min(2.0, avg_max_combo * 0.25))
            if fugas > 3:
                self._registrar_padrao_oponente(oponente, "fuga_sob_pressao", min(2.0, fugas * 0.25))


    def salvar_memoria_rival(self, oponente, venceu: bool) -> None:
        """
        Persiste as estatÃ­sticas desta luta para uso em confrontos futuros.
        Chamado ao fim de cada combate (ex: em on_luta_encerrada ou similar).
        """
        chave = self._id_oponente(oponente)
        hist = type(self)._historico_combates.setdefault(chave, {
            "lutas": 0,
            "vitorias": 0,
            "hits_sofridos_total": 0,
            "max_combo_total": 0,
            "fugas_total": 0,
            "rivalidade_total": 0.0,
        })
        hist["lutas"] += 1
        if venceu:
            hist["vitorias"] += 1
        hist["hits_sofridos_total"] += self.hits_recebidos_total
        hist["max_combo_total"] += self.max_combo
        hist["fugas_total"] += self.vezes_que_fugiu
        bucket = self._obter_vies_oponente(oponente) if hasattr(self, "_obter_vies_oponente") else {}
        if isinstance(bucket, dict):
            rivalidade = (
                max(0.0, bucket.get("relacao_respeito", 0.0))
                + max(0.0, bucket.get("relacao_vinganca", 0.0))
                + max(0.0, bucket.get("relacao_obsessao", 0.0))
                + max(0.0, bucket.get("relacao_caca", 0.0))
            ) / 4.0
            hist["rivalidade_total"] += rivalidade

        _log.debug(
            "[IA] %s: salvou memÃ³ria rival '%s' â€” %d luta(s) registradas",
            self.parent.dados.nome, chave, hist["lutas"],
        )

