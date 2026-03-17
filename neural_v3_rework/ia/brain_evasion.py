"""Auto-generated mixin â€” see scripts/split_brain.py"""
import random
import math
import logging

_log = logging.getLogger("neural_ai")

from nucleo.physics import normalizar_angulo
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

from ia.behavior_profiles import FALLBACK_PROFILE  # MEL-07: esquiva_mult/bloqueio_mult
from ia._brain_mixin_base import _AIBrainMixinBase


class EvasionMixin(_AIBrainMixinBase):
    """Mixin de esquiva inteligente, pulos evasivos e detecÃ§Ã£o de projÃ©teis."""

    
    # =========================================================================
    # SISTEMA DE DESVIO INTELIGENTE v8.0
    # =========================================================================
    
    def _processar_desvio_inteligente(self, dt, distancia, inimigo):
        """Sistema de desvio avanÃ§ado com antecipaÃ§Ã£o e timing humano"""
        p = self.parent
        leitura = self.leitura_oponente
        
        # NÃ£o desvia se estiver em berserk ou muito confiante
        if self.modo_berserk:
            return False
        if self.confianca > 0.85 and "IMPRUDENTE" in self.tracos:
            return False
        
        # Detecta necessidade de desvio
        desvio_necessario = False
        tipo_desvio = None
        urgencia = 0.0
        
        # 1. Ataque fÃ­sico iminente
        if leitura["ataque_iminente"] and distancia < AI_DIST_ATAQUE_IMINENTE:
            desvio_necessario = True
            tipo_desvio = "ATAQUE_FISICO"
            urgencia = 1.0 - (distancia / AI_DIST_ATAQUE_IMINENTE)
        
        # 2. ProjÃ©til vindo
        projetil_info = self._analisar_projeteis_vindo(inimigo)
        if projetil_info["vindo"]:
            desvio_necessario = True
            tipo_desvio = "PROJETIL"
            urgencia = max(urgencia, projetil_info["urgencia"])
        
        # 3. Ãrea de dano
        area_info = self._analisar_areas_perigo(inimigo)
        if area_info["perigo"]:
            desvio_necessario = True
            tipo_desvio = "AREA"
            urgencia = max(urgencia, area_info["urgencia"])
        
        if not desvio_necessario:
            return False
        
        # Aplica timing humano (nÃ£o reage instantaneamente)
        tempo_reacao = self.tempo_reacao_base + random.uniform(-self.variacao_timing, self.variacao_timing)
        
        # TraÃ§os afetam tempo de reaÃ§Ã£o
        if "REATIVO" in self.tracos or "EVASIVO" in self.tracos:
            tempo_reacao *= 0.7
        if "ESTATICO" in self.tracos:
            tempo_reacao *= 1.5
        if self.adrenalina > 0.6:
            tempo_reacao *= 0.8
        if self.medo > 0.5:
            tempo_reacao *= 0.85  # Medo aumenta reflexos
        if self.congelamento > 0.3:
            tempo_reacao *= 1.5  # Congela sob pressÃ£o
        
        # MED-4 fix: clamp em 0.95 antes de calcular chance_reagir.
        # Com mÃºltiplos modificadores de lentidÃ£o acumulados (ESTATICO Ã—1.5
        # + congelamento Ã—1.5 + variaÃ§Ã£o), tempo_reacao podia ultrapassar 1.0
        # tornando chance_reagir negativa â€” o que invertia o sinal e fazia o
        # personagem SEMPRE tentar desviar, ao invÃ©s de nunca.
        tempo_reacao = min(tempo_reacao, 0.95)
        
        # Chance de reagir baseado na urgÃªncia vs tempo de reaÃ§Ã£o
        chance_reagir = max(0.0, urgencia * (1.0 - tempo_reacao))

        # MEL-07 fix: aplica esquiva_mult do behavior profile.
        # Os perfis definem valores entre 0.2 e 1.5 mas nunca eram lidos aqui.
        # Aplicado APÃ“S calcular chance_reagir (fix: era aplicado antes, causando
        # UnboundLocalError porque chance_reagir ainda nÃ£o existia).
        bp = getattr(self, '_behavior_profile', FALLBACK_PROFILE)
        esquiva_mult = bp.get("esquiva_mult", 1.0)
        chance_reagir *= esquiva_mult

        # Sprint3: combo_state do inimigo aumenta urgÃªncia de desviar.
        # Antes: o 8Âº hit consecutivo era tÃ£o fÃ¡cil de desviar quanto o 1Âº.
        # Agora: cada hit em combo adiciona pressÃ£o ao oponente â€” mais acertos
        # = mais adrenalina = reflexos mais afiados.
        if hasattr(inimigo, 'brain') and inimigo.brain:
            combo_hits = inimigo.brain.combo_state.get("hits_combo", 0)
            if combo_hits >= 3:
                bonus_combo = min(0.35, (combo_hits - 2) * 0.07)
                chance_reagir = min(1.0, chance_reagir + bonus_combo)

        # Personalidade afeta chance
        if "ACROBATA" in self.tracos:
            chance_reagir += 0.2
        if "PACIENTE" in self.tracos:
            chance_reagir += 0.1
        if "IMPRUDENTE" in self.tracos:
            chance_reagir -= 0.15
        
        if random.random() > chance_reagir:
            return False
        
        # Decide direÃ§Ã£o do desvio
        direcao_desvio = self._calcular_direcao_desvio(tipo_desvio, distancia, inimigo, projetil_info)
        
        # Executa o desvio
        return self._executar_desvio(tipo_desvio, direcao_desvio, urgencia, distancia, inimigo)

    
    def _calcular_direcao_desvio(self, tipo_desvio, distancia, inimigo, projetil_info):
        """Calcula a melhor direÃ§Ã£o para desviar"""
        p = self.parent
        leitura = self.leitura_oponente
        
        # DireÃ§Ã£o base: perpendicular ao ataque
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
        
        # Escolhe direÃ§Ã£o baseado em fatores (prioridade crescente)
        escolha = opcao1 if random.random() < 0.5 else opcao2
        
        # Usa direÃ§Ã£o circular como base
        if self.dir_circular > 0:
            escolha = opcao1
        else:
            escolha = opcao2
        
        # Leitura do oponente pode sobrescrever (maior prioridade)
        if leitura["tendencia_esquerda"] > 0.6:
            escolha = opcao2  # Oponente tende a ir pra esquerda, vou pra direita
        elif leitura["tendencia_esquerda"] < 0.4:
            escolha = opcao1
        
        # Adiciona variaÃ§Ã£o humana
        escolha += random.uniform(-20, 20)
        
        # Se HP baixo, prioriza recuar
        hp_pct = p.vida / max(p.vida_max, 1)
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
        
        # Tipo de desvio baseado na urgÃªncia e situaÃ§Ã£o
        if urgencia > 0.8 or tipo_desvio == "AREA":
            # Desvio urgente - dash se disponÃ­vel
            if self.cd_dash <= 0:
                dash_skills = self.skills_por_tipo.get("DASH", [])
                for skill in dash_skills:
                    # Ajusta Ã¢ngulo de olhar temporariamente para dash
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
                # Move lateralmente tambÃ©m
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
            
            # Define aÃ§Ã£o
            if distancia > 4.0:
                self.acao_atual = "CIRCULAR"
            else:
                self.acao_atual = "FLANQUEAR"
            
            return True
        
        # Desvio sutil - apenas ajuste de posiÃ§Ã£o
        if random.random() < urgencia:
            self.acao_atual = "CIRCULAR"
            return True
        
        return False

    
    def _analisar_areas_perigo(self, inimigo):
        """Analisa Ã¡reas de dano prÃ³ximas"""
        p = self.parent
        resultado = {"perigo": False, "urgencia": 0.0}
        
        if hasattr(inimigo, 'buffer_areas'):
            for area in inimigo.buffer_areas:
                if not area.ativo:
                    continue
                
                dist = math.hypot(p.pos[0] - area.x, p.pos[1] - area.y)
                raio = getattr(area, 'raio', 2.0)
                
                if dist < raio + 1.5:  # Dentro ou perto da Ã¡rea
                    resultado["perigo"] = True
                    resultado["urgencia"] = max(resultado["urgencia"], 1.0 - dist / (raio + 1.5))
        
        return resultado

    
    def _analisar_projeteis_vindo(self, inimigo):
        """Analisa projÃ©teis vindo em direÃ§Ã£o ao lutador"""
        p = self.parent
        resultado = {"vindo": False, "urgencia": 0.0, "direcao": 0.0, "tempo_impacto": 999.0}
        
        # Verifica projÃ©teis
        if hasattr(inimigo, 'buffer_projeteis'):
            for proj in inimigo.buffer_projeteis:
                if not proj.ativo:
                    continue
                
                dx = p.pos[0] - proj.x
                dy = p.pos[1] - proj.y
                dist = math.hypot(dx, dy)
                
                if dist > 8.0:
                    continue
                
                # Calcula se estÃ¡ vindo na minha direÃ§Ã£o
                ang_para_mim = math.degrees(math.atan2(dy, dx))
                ang_proj = getattr(proj, 'angulo', 0)
                diff_ang = abs(normalizar_angulo(ang_para_mim - ang_proj))
                
                if diff_ang < 45:  # Vindo na minha direÃ§Ã£o
                    vel_proj = getattr(proj, 'vel', 10.0)
                    tempo_impacto = dist / max(vel_proj, 0.01)
                    
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
                # SimplificaÃ§Ã£o: se beam estÃ¡ ativo e perto, Ã© perigo
                dist = math.hypot(p.pos[0] - beam.x1, p.pos[1] - beam.y1)
                alcance = math.hypot(beam.x2 - beam.x1, beam.y2 - beam.y1)
                if dist < alcance + 1.0:
                    resultado["vindo"] = True
                    resultado["urgencia"] = max(resultado["urgencia"], 0.9)
        
        return resultado


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
                self.acao_atual = "ATAQUE_RAPIDO"
            else:
                self.acao_atual = "RECUAR"
            
            self.cd_reagir = 0.3
            return True
        
        return False


    def _tentar_dash_emergencia(self, distancia, hp_pct, inimigo):
        """Dash de emergÃªncia v7.0 com detecÃ§Ã£o de projÃ©teis"""
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
        """Detecta se hÃ¡ projÃ©teis vindo na direÃ§Ã£o do personagem"""
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

