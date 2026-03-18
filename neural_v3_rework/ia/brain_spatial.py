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


class SpatialMixin(_AIBrainMixinBase):
    """Mixin de consciÃªncia espacial, paredes, obstÃ¡culos e tÃ¡ticas de posicionamento."""

    def _distancia_borda_arena(self, arena, x, y):
        """Retorna a distÃ¢ncia atÃ© a borda mais prÃ³xima respeitando o formato da arena."""
        if getattr(getattr(arena, "config", None), "formato", "retangular") == "circular" and getattr(arena, "raio", None) is not None:
            return max(0.0, float(arena.raio) - math.hypot(x - arena.centro_x, y - arena.centro_y))
        return min(
            x - arena.min_x,
            arena.max_x - x,
            y - arena.min_y,
            arena.max_y - y,
        )

    def _parede_dominante_arena(self, arena, x, y):
        """Estima qual lado da arena estÃ¡ pressionando mais o lutador."""
        if getattr(getattr(arena, "config", None), "formato", "retangular") == "circular":
            dx = x - arena.centro_x
            dy = y - arena.centro_y
            if abs(dx) >= abs(dy):
                return "leste" if dx >= 0 else "oeste"
            return "sul" if dy >= 0 else "norte"

        paredes = [
            ("norte", y - arena.min_y),
            ("sul", arena.max_y - y),
            ("oeste", x - arena.min_x),
            ("leste", arena.max_x - x),
        ]
        return min(paredes, key=lambda item: item[1])[0]

    def _caminho_esta_livre(self, arena, x, y, raio):
        """Combina colisÃ£o de obstÃ¡culo com validade dentro da arena."""
        if hasattr(arena, "esta_dentro") and not arena.esta_dentro(x, y, raio):
            return False
        return not arena.colide_obstaculo(x, y, raio)

    def _analisar_zona_perigo(self, arena, x, y):
        """Retorna (tipo_zona, distancia_aprox) para fogo/lava prÃ³ximos."""
        tipo_atual = arena.esta_em_zona_perigo(x, y) if hasattr(arena, "esta_em_zona_perigo") else None
        dist_min = 999.0
        tipo_proximo = None
        for obs in getattr(arena, "obstaculos", []) or []:
            if getattr(obs, "tipo", None) not in {"lava", "fogo"}:
                continue
            dx = abs(x - obs.x) - obs.largura / 2
            dy = abs(y - obs.y) - obs.altura / 2
            dist = math.hypot(max(0.0, dx), max(0.0, dy))
            if dist < dist_min:
                dist_min = dist
                tipo_proximo = obs.tipo
        return tipo_atual, tipo_proximo, dist_min

    
    # =========================================================================
    # SISTEMA DE RECONHECIMENTO ESPACIAL v9.0
    # =========================================================================
    
    def _atualizar_consciencia_espacial(self, dt, distancia, inimigo):
        """
        Atualiza awareness de paredes, obstÃ¡culos e posicionamento tÃ¡tico.
        Chamado no processar() principal.
        """
        tatica = self.tatica_espacial
        
        # OtimizaÃ§Ã£o: sÃ³ checa a cada 0.2s
        tatica["last_check_time"] += dt
        if tatica["last_check_time"] < AI_INTERVALO_ESPACIAL:
            return
        tatica["last_check_time"] = 0.0
        
        p = self.parent
        esp = self.consciencia_espacial
        
        # Importa arena (QC-04: _get_arena jÃ¡ importado no mÃ³dulo)
        try:
            if _get_arena is None:
                return
            arena = _get_arena()
        except Exception:
            return  # Se arena nÃ£o disponÃ­vel, ignora
        
        # === DETECÃ‡ÃƒO DE PAREDES ===
        esp["parede_proxima"] = self._parede_dominante_arena(arena, p.pos[0], p.pos[1])
        esp["distancia_parede"] = self._distancia_borda_arena(arena, p.pos[0], p.pos[1])
        esp["distancia_centro"] = math.hypot(p.pos[0] - arena.centro_x, p.pos[1] - arena.centro_y)
        
        # === DETECÃ‡ÃƒO DE OBSTÃCULOS ===
        obs_mais_proximo = None
        dist_obs_min = 999.0
        
        if hasattr(arena, 'obstaculos'):
            for obs in arena.obstaculos:
                if not obs.solido:
                    continue
                
                dx = p.pos[0] - obs.x
                dy = p.pos[1] - obs.y
                dist = math.hypot(dx, dy) - (obs.largura + obs.altura) / 4
                
                if dist < dist_obs_min:
                    dist_obs_min = dist
                    obs_mais_proximo = obs
        
        esp["obstaculo_proxima"] = obs_mais_proximo
        esp["distancia_obstaculo"] = dist_obs_min
        esp["zona_perigo_atual"], esp["zona_perigo_proxima"], esp["distancia_zona_perigo"] = self._analisar_zona_perigo(arena, p.pos[0], p.pos[1])
        esp["zona_perigo_inimigo"], _, _ = self._analisar_zona_perigo(arena, inimigo.pos[0], inimigo.pos[1])
        
        # === ANÃLISE DE CAMINHOS LIVRES ===
        # Verifica se hÃ¡ obstÃ¡culos bloqueando cada direÃ§Ã£o
        check_dist = 2.0  # DistÃ¢ncia de checagem
        
        # Frente (em direÃ§Ã£o ao inimigo)
        ang_inimigo = math.atan2(inimigo.pos[1] - p.pos[1], inimigo.pos[0] - p.pos[0])
        check_x_frente = p.pos[0] + math.cos(ang_inimigo) * check_dist
        check_y_frente = p.pos[1] + math.sin(ang_inimigo) * check_dist
        esp["caminho_livre"]["frente"] = self._caminho_esta_livre(arena, check_x_frente, check_y_frente, p.raio_fisico)
        
        # TrÃ¡s (oposto ao inimigo)
        check_x_tras = p.pos[0] - math.cos(ang_inimigo) * check_dist
        check_y_tras = p.pos[1] - math.sin(ang_inimigo) * check_dist
        esp["caminho_livre"]["tras"] = self._caminho_esta_livre(arena, check_x_tras, check_y_tras, p.raio_fisico)
        
        # Esquerda (perpendicular)
        ang_esq = ang_inimigo + math.pi / 2
        check_x_esq = p.pos[0] + math.cos(ang_esq) * check_dist
        check_y_esq = p.pos[1] + math.sin(ang_esq) * check_dist
        esp["caminho_livre"]["esquerda"] = self._caminho_esta_livre(arena, check_x_esq, check_y_esq, p.raio_fisico)
        
        # Direita
        ang_dir = ang_inimigo - math.pi / 2
        check_x_dir = p.pos[0] + math.cos(ang_dir) * check_dist
        check_y_dir = p.pos[1] + math.sin(ang_dir) * check_dist
        esp["caminho_livre"]["direita"] = self._caminho_esta_livre(arena, check_x_dir, check_y_dir, p.raio_fisico)
        
        # === AVALIAÃ‡ÃƒO DE POSIÃ‡ÃƒO TÃTICA ===
        # Encurralado = parede atrÃ¡s E sem caminhos laterais
        parede_atras = (
            (esp["parede_proxima"] == "norte" and p.pos[1] < inimigo.pos[1]) or
            (esp["parede_proxima"] == "sul" and p.pos[1] > inimigo.pos[1]) or
            (esp["parede_proxima"] == "oeste" and p.pos[0] < inimigo.pos[0]) or
            (esp["parede_proxima"] == "leste" and p.pos[0] > inimigo.pos[0])
        )
        
        sem_saidas = (
            not esp["caminho_livre"]["esquerda"] and 
            not esp["caminho_livre"]["direita"] and
            not esp["caminho_livre"]["tras"]
        )
        
        esp["encurralado"] = (
            parede_atras and sem_saidas and 
            esp["distancia_parede"] < AI_DIST_PAREDE_CRITICA
        )
        
        # Oponente contra parede
        dist_ini_parede = self._distancia_borda_arena(arena, inimigo.pos[0], inimigo.pos[1])
        esp["distancia_parede_inimigo"] = dist_ini_parede
        esp["oponente_contra_parede"] = dist_ini_parede < 2.5
        esp["dominando_centro"] = esp["distancia_centro"] + 1.0 < math.hypot(inimigo.pos[0] - arena.centro_x, inimigo.pos[1] - arena.centro_y)

        dist_obs_inimigo = 999.0
        if hasattr(arena, 'obstaculos'):
            for obs in arena.obstaculos:
                if not obs.solido:
                    continue
                dx_ini = inimigo.pos[0] - obs.x
                dy_ini = inimigo.pos[1] - obs.y
                dist_obs_inimigo = min(dist_obs_inimigo, math.hypot(dx_ini, dy_ini) - (obs.largura + obs.altura) / 4)
        esp["oponente_perto_obstaculo"] = dist_obs_inimigo < 2.0
        esp["inimigo_vulneravel_zona"] = esp["zona_perigo_inimigo"] is not None
        esp["pressao_borda"] = max(0.0, min(1.0, (AI_DIST_PAREDE_AVISO - dist_ini_parede) / max(0.1, AI_DIST_PAREDE_AVISO)))
        
        # PosiÃ§Ã£o geral
        if esp["encurralado"]:
            esp["posicao_tatica"] = "encurralado"
        elif esp["distancia_parede"] < 2.0:
            esp["posicao_tatica"] = "perto_parede"
        elif esp["oponente_contra_parede"]:
            esp["posicao_tatica"] = "vantagem"
        else:
            esp["posicao_tatica"] = "centro"
        
        # === ANÃLISE TÃTICA ===
        self._avaliar_taticas_espaciais(distancia, inimigo)

    
    def _avaliar_taticas_espaciais(self, distancia, inimigo):
        """
        Avalia e define tÃ¡ticas espaciais baseadas na situaÃ§Ã£o.
        VERSÃƒO MELHORADA v10.0 - mais inteligente e baseada em traÃ§os.
        """
        esp = self.consciencia_espacial
        tatica = self.tatica_espacial
        p = self.parent
        hp_pct = p.vida / max(p.vida_max, 1)
        
        # Reset tÃ¡ticas
        tatica["usando_cobertura"] = False
        tatica["forcar_canto"] = False
        tatica["retomar_centro"] = False
        tatica["escapar_zona_perigo"] = False
        tatica["pressionar_em_zona"] = False
        tatica["recuar_para_obstaculo"] = False
        tatica["flanquear_obstaculo"] = False
        
        # === SE ENCURRALADO ===
        if esp["encurralado"]:
            # ReaÃ§Ã£o depende da personalidade
            if "BERSERKER" in self.tracos or "KAMIKAZE" in self.tracos:
                # Berserkers ficam mais perigosos quando encurralados
                self.raiva = min(1.0, self.raiva + 0.4)
                self.medo = max(0, self.medo - 0.2)
                self.hesitacao = 0
            elif "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
                # Covardes entram em pÃ¢nico
                self.medo = min(1.0, self.medo + 0.4)
                self.hesitacao = min(0.8, self.hesitacao + 0.3)
            elif "FRIO" in self.tracos or "CALCULISTA" in self.tracos:
                # Calculistas mantÃªm a calma e planejam escape
                self.hesitacao = max(0.0, self.hesitacao - 0.2)
            else:
                # PadrÃ£o: stress moderado
                self.medo = min(1.0, self.medo + 0.2)
                self.hesitacao = max(0.0, self.hesitacao - 0.1)
            
            # Determina melhor rota de escape baseado em traÃ§os
            if esp["caminho_livre"]["esquerda"] and esp["caminho_livre"]["direita"]:
                # Escolhe baseado em tendÃªncia ou aleatoriedade
                if "ERRATICO" in self.tracos or "CAOTICO" in self.tracos:
                    self.dir_circular = random.choice([-1, 1])
                else:
                    # Vai pro lado oposto do oponente
                    ang_inimigo = math.atan2(inimigo.pos[1] - p.pos[1], inimigo.pos[0] - p.pos[0])
                    self.dir_circular = 1 if math.sin(ang_inimigo) > 0 else -1
            elif esp["caminho_livre"]["esquerda"]:
                self.dir_circular = 1
            elif esp["caminho_livre"]["direita"]:
                self.dir_circular = -1
        
        # === OPONENTE CONTRA PAREDE/OBSTÃCULO ===
        oponente_vulneravel = esp.get("oponente_contra_parede", False) or esp.get("oponente_perto_obstaculo", False)
        if oponente_vulneravel and distancia < 6.0:
            tatica["forcar_canto"] = True
            self.confianca = min(1.0, self.confianca + 0.15)
            
            # BUG-AI-05 fix: pressÃ£o extra via modificador temporÃ¡rio (nÃ£o corrompe a personalidade base)
            if "PREDADOR" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.25)
            if "SANGUINARIO" in self.tracos or "IMPLACAVEL" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.20)
            if "OPORTUNISTA" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.15)

        if esp.get("zona_perigo_inimigo"):
            tatica["pressionar_em_zona"] = True
            self.confianca = min(1.0, self.confianca + 0.10)
            if "PREDADOR" in self.tracos or "OPORTUNISTA" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.18)

        if esp.get("zona_perigo_atual"):
            tatica["escapar_zona_perigo"] = True
            self.medo = min(1.0, self.medo + 0.08)
            self.hesitacao = max(0.0, self.hesitacao - 0.08)

        # === RETOMADA DE CENTRO ===
        if (
            esp["distancia_parede"] < AI_DIST_PAREDE_AVISO
            and not oponente_vulneravel
            and esp.get("distancia_centro", 0.0) > 2.5
            and not tatica["usando_cobertura"]
        ):
            tatica["retomar_centro"] = True
            if "CALCULISTA" in self.tracos or "TATICO" in self.tracos or "FOCADO" in self.tracos:
                self.confianca = min(1.0, self.confianca + 0.08)
                self.hesitacao = max(0.0, self.hesitacao - 0.05)
            elif "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
                self.medo = min(1.0, self.medo + 0.05)
            else:
                self._agressividade_temp_mod = min(0.35, self._agressividade_temp_mod + 0.06)
        
        # === USO DE COBERTURA ===
        # BUG-AI-06 fix: padronizado para "obstaculo_proxima" (chave definida em __init__ e _atualizar_consciencia_espacial)
        obs_proximo = esp.get("obstaculo_proxima")
        dist_obs = esp.get("distancia_obstaculo", 999)
        
        if obs_proximo and dist_obs < 2.5:
            # Decide se usa cobertura baseado em personalidade
            usa_cobertura = False
            
            if "CAUTELOSO" in self.tracos or "TATICO" in self.tracos:
                usa_cobertura = True
            elif hp_pct < 0.35:
                usa_cobertura = True
            elif self.medo > 0.6:
                usa_cobertura = True
            elif "COVARDE" in self.tracos and distancia > 4.0:
                usa_cobertura = True
            
            # Berserkers e kamikazes nÃ£o usam cobertura
            if "BERSERKER" in self.tracos or "KAMIKAZE" in self.tracos or "IMPLACAVEL" in self.tracos:
                usa_cobertura = False
            
            if usa_cobertura:
                tatica["usando_cobertura"] = True
                tatica["tipo_cobertura"] = getattr(obs_proximo, 'tipo', 'obstaculo')
        
        # === FLANQUEAMENTO COM OBSTÃCULOS ===
        if obs_proximo and 3.0 < distancia < 8.0 and dist_obs < 4.0:
            # Flanqueio Ã© mais provÃ¡vel com certos traÃ§os
            flanqueia = False
            
            if "FLANQUEADOR" in self.tracos:
                flanqueia = random.random() < 0.6
            elif "TATICO" in self.tracos or "CALCULISTA" in self.tracos:
                flanqueia = random.random() < 0.4
            elif "ASSASSINO_NATO" in self.tracos or self.arquetipo == "NINJA":  # FP-N02: era substring
                flanqueia = random.random() < 0.5
            else:
                flanqueia = random.random() < 0.2
            
            if flanqueia:
                tatica["flanquear_obstaculo"] = True
        
        # === EVITA RECUAR PARA OBSTÃCULO ===
        if not esp["caminho_livre"]["tras"] and distancia < 4.0:
            tatica["recuar_para_obstaculo"] = True
            
            # Ajusta aÃ§Ã£o se estava tentando recuar
            if self.acao_atual in ["RECUAR", "FUGIR"]:
                if "BERSERKER" in self.tracos:
                    self.acao_atual = "MATAR"  # NÃ£o foge, ataca!
                elif random.random() < 0.7:
                    self.acao_atual = "CIRCULAR"
                else:
                    self.acao_atual = "FLANQUEAR"

        # ================================================================
        # v13.0: TEAM SPATIAL AWARENESS â€” posicionamento relativo ao time
        # ================================================================
        orders = getattr(self, 'team_orders', {})
        team_role = orders.get("role", "")
        has_team = orders.get("alive_count", 1) > 1

        if has_team and team_role:
            team_center = orders.get("team_center", (0, 0))
            team_spread = orders.get("team_spread", 0)
            dist_to_center = math.hypot(
                p.pos[0] - team_center[0], p.pos[1] - team_center[1]
            ) if team_center != (0, 0) else 999

            # â”€â”€ RETREAT TO ALLY (quando HP baixo, recua para suporte/tank) â”€â”€
            if hp_pct < 0.35 and team_role not in ("VANGUARD",):
                from ia.team_ai import TeamCoordinatorManager
                coord = TeamCoordinatorManager.get().get_fighter_coordinator(p)
                if coord:
                    retreat_pos = coord.should_retreat_to_ally(p)
                    if retreat_pos:
                        # Ajusta aÃ§Ã£o para recuar em direÃ§Ã£o ao aliado
                        dx = retreat_pos[0] - p.pos[0]
                        dy = retreat_pos[1] - p.pos[1]
                        dist_retreat = math.hypot(dx, dy)
                        if dist_retreat > 2.0:
                            self.acao_atual = "RECUAR"
                            # Seta direÃ§Ã£o de movimento para o aliado (nÃ£o para longe do inimigo)
                            ang_aliado = math.atan2(dy, dx)
                            p.movimento_x = math.cos(ang_aliado) * 0.3

            # â”€â”€ VANGUARD: posiciona-se entre aliados e inimigos â”€â”€
            if team_role == "VANGUARD":
                ma = getattr(self, 'multi_awareness', {})
                inimigos = ma.get("inimigos", [])
                if inimigos and team_center != (0, 0):
                    # Centro dos inimigos
                    cx_ini = sum(e["lutador"].pos[0] for e in inimigos) / len(inimigos)
                    cy_ini = sum(e["lutador"].pos[1] for e in inimigos) / len(inimigos)
                    # PosiÃ§Ã£o ideal: entre aliados e inimigos
                    ideal_x = (team_center[0] + cx_ini) / 2
                    ideal_y = (team_center[1] + cy_ini) / 2
                    dist_to_ideal = math.hypot(p.pos[0] - ideal_x, p.pos[1] - ideal_y)
                    if dist_to_ideal > 4.0:
                        # Muito longe da posiÃ§Ã£o ideal, vai para lÃ¡
                        self._agressividade_temp_mod = max(
                            -0.1, self._agressividade_temp_mod - 0.05
                        )

            # â”€â”€ ARTILLERY: recua se muito perto do centro do time (fica atrÃ¡s) â”€â”€
            if team_role == "ARTILLERY":
                if dist_to_center < 2.0:
                    # Muito colado no time, se afasta para trÃ¡s
                    self._agressividade_temp_mod = max(
                        -0.3, self._agressividade_temp_mod - 0.05
                    )

            # â”€â”€ FLANKER: tenta ficar em Ã¢ngulo diferente dos aliados â”€â”€
            if team_role == "FLANKER":
                ma = getattr(self, 'multi_awareness', {})
                aliados = ma.get("aliados", [])
                if aliados and inimigo:
                    # Ã‚ngulo do inimigo em relaÃ§Ã£o a mim
                    ang_meu = math.atan2(
                        inimigo.pos[1] - p.pos[1],
                        inimigo.pos[0] - p.pos[0]
                    )
                    # Ã‚ngulo do aliado mais perto em relaÃ§Ã£o ao inimigo
                    for aliado in aliados:
                        ang_aliado = math.atan2(
                            inimigo.pos[1] - aliado["lutador"].pos[1],
                            inimigo.pos[0] - aliado["lutador"].pos[0]
                        )
                        diff = abs(math.degrees(ang_meu - ang_aliado))
                        if diff > 180:
                            diff = 360 - diff
                        # Se estou no mesmo Ã¢ngulo que o aliado, flanqueia mais
                        if diff < 45:
                            self.dir_circular = 1 if random.random() < 0.5 else -1
                        break  # sÃ³ checa o mais perto

    
    def _aplicar_modificadores_espaciais(self, distancia, inimigo):
        """
        Aplica modificadores de comportamento baseados no ambiente.
        VERSÃƒO MELHORADA v10.0 - decisÃµes mais inteligentes.
        """
        esp = self.consciencia_espacial
        tatica = self.tatica_espacial
        p = self.parent
        
        # === MODIFICADORES POR SITUAÃ‡ÃƒO ===
        
        # Se encurralado
        if esp["encurralado"]:
            # Escolha depende do balanÃ§o medo/raiva e traÃ§os
            escape_roll = random.random()
            
            if "BERSERKER" in self.tracos or self.raiva > self.medo * 1.5:
                # Ataca com tudo
                if escape_roll < 0.7:
                    self.acao_atual = random.choice(["MATAR", "ESMAGAR", "CONTRA_ATAQUE"])
            elif "EVASIVO" in self.tracos or "ACROBATA" in self.tracos:
                # Tenta escapar com estilo
                if escape_roll < 0.5:
                    self.acao_atual = "FLANQUEAR"
                else:
                    self.acao_atual = "CIRCULAR"
            else:
                # PadrÃ£o: mistura de escape e contra-ataque
                if self.medo > self.raiva:
                    if escape_roll < 0.5:
                        self.acao_atual = "CIRCULAR"
                    elif escape_roll < 0.8:
                        self.acao_atual = "FLANQUEAR"
                    else:
                        self.acao_atual = "CONTRA_ATAQUE"
                else:
                    if escape_roll < 0.4:
                        self.acao_atual = random.choice(["MATAR", "CONTRA_ATAQUE"])
                    else:
                        self.acao_atual = "CIRCULAR"
        
        # Se oponente contra parede
        if tatica["forcar_canto"]:
            if random.random() < 0.35 + esp.get("pressao_borda", 0.0) * 0.25:
                self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "ESMAGAR"])

        if tatica["pressionar_em_zona"]:
            if self.acao_atual in ["NEUTRO", "RECUAR", "BLOQUEAR", "POKE"]:
                self.acao_atual = random.choice(["PRESSIONAR", "COMBATE", "MATAR"])

        if tatica["escapar_zona_perigo"]:
            if self.acao_atual in ["RECUAR", "FUGIR", "BLOQUEAR", "NEUTRO", "POKE"]:
                if esp["caminho_livre"]["esquerda"] or esp["caminho_livre"]["direita"]:
                    self.acao_atual = "CIRCULAR"
                else:
                    self.acao_atual = "APROXIMAR"

        # Se precisa retomar o centro da arena
        if tatica["retomar_centro"]:
            if self.acao_atual in ["RECUAR", "FUGIR", "NEUTRO", "BLOQUEAR", "POKE"]:
                self.acao_atual = random.choice(["CIRCULAR", "FLANQUEAR", "APROXIMAR"])
            elif self.acao_atual == "COMBATE" and distancia > 2.3:
                self.acao_atual = random.choice(["CIRCULAR", "APROXIMAR"])
        
        # Se usando cobertura
        if tatica["usando_cobertura"]:
            if random.random() < 0.25:
                # Fica atrÃ¡s do obstÃ¡culo
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "BLOQUEAR"])
        
        # Se flanqueando com obstÃ¡culo
        if tatica["flanquear_obstaculo"]:
            if random.random() < 0.2:
                self.acao_atual = "FLANQUEAR"
        
        # Se recuando pra obstÃ¡culo
        if tatica["recuar_para_obstaculo"]:
            # NUNCA recua
            if self.acao_atual in ["RECUAR", "FUGIR"]:
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "FLANQUEAR"])
        
        # === MODIFICADORES POR DIREÃ‡ÃƒO ===
        
        # Se caminho da frente bloqueado
        if not esp["caminho_livre"]["frente"]:
            if self.acao_atual in ["APROXIMAR", "MATAR", "PRESSIONAR"]:
                # Circula ao invÃ©s de ir direto
                if random.random() < 0.4:
                    self.acao_atual = "FLANQUEAR"
        
        # Se perto de parede
        if esp["distancia_parede"] < 2.0:
            # Ajusta direÃ§Ã£o circular pra nÃ£o bater na parede
            if esp["parede_proxima"] in ["oeste", "leste"]:
                # Parede lateral - ajusta se necessÃ¡rio
                if esp["parede_proxima"] == "oeste" and self.dir_circular < 0:
                    self.dir_circular = 1
                elif esp["parede_proxima"] == "leste" and self.dir_circular > 0:
                    self.dir_circular = -1

    
    def _ajustar_direcao_por_ambiente(self, direcao_alvo):
        """
        Ajusta uma direÃ§Ã£o de movimento para evitar obstÃ¡culos.
        Retorna nova direÃ§Ã£o segura.
        """
        esp = self.consciencia_espacial
        p = self.parent
        
        # Converte direÃ§Ã£o pra radianos
        ang_rad = math.radians(direcao_alvo)
        
        # Verifica se a direÃ§Ã£o estÃ¡ bloqueada
        try:
            if _get_arena is None:
                raise ImportError("arena nÃ£o disponÃ­vel")
            arena = _get_arena()  # QC-04: usa _get_arena de nÃ­vel de mÃ³dulo
            
            # Testa ponto Ã  frente
            test_dist = 1.5
            test_x = p.pos[0] + math.cos(ang_rad) * test_dist
            test_y = p.pos[1] + math.sin(ang_rad) * test_dist
            
            if arena.colide_obstaculo(test_x, test_y, p.raio_fisico):
                # Bloqueado! Tenta alternativas
                alternativas = [
                    direcao_alvo + 45,
                    direcao_alvo - 45,
                    direcao_alvo + 90,
                    direcao_alvo - 90,
                    direcao_alvo + 135,
                    direcao_alvo - 135,
                ]
                
                for alt_ang in alternativas:
                    alt_rad = math.radians(alt_ang)
                    alt_x = p.pos[0] + math.cos(alt_rad) * test_dist
                    alt_y = p.pos[1] + math.sin(alt_rad) * test_dist
                    
                    if not arena.colide_obstaculo(alt_x, alt_y, p.raio_fisico):
                        return alt_ang
                
                # Se tudo bloqueado, fica parado (retorna direÃ§Ã£o atual)
                return direcao_alvo
        except (AttributeError, TypeError, Exception):
            pass
        
        return direcao_alvo

