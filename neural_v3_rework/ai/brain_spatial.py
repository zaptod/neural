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


class SpatialMixin(_AIBrainMixinBase):
    """Mixin de consciência espacial, paredes, obstáculos e táticas de posicionamento."""

    
    # =========================================================================
    # SISTEMA DE RECONHECIMENTO ESPACIAL v9.0
    # =========================================================================
    
    def _atualizar_consciencia_espacial(self, dt, distancia, inimigo):
        """
        Atualiza awareness de paredes, obstáculos e posicionamento tático.
        Chamado no processar() principal.
        """
        tatica = self.tatica_espacial
        
        # Otimização: só checa a cada 0.2s
        tatica["last_check_time"] += dt
        if tatica["last_check_time"] < AI_INTERVALO_ESPACIAL:
            return
        tatica["last_check_time"] = 0.0
        
        p = self.parent
        esp = self.consciencia_espacial
        
        # Importa arena (QC-04: _get_arena já importado no módulo)
        try:
            if _get_arena is None:
                return
            arena = _get_arena()
        except Exception:
            return  # Se arena não disponível, ignora
        
        # === DETECÇÃO DE PAREDES ===
        margem_detecao = AI_DIST_PAREDE_AVISO  # Começa a detectar parede a 3m
        
        dist_norte = p.pos[1] - arena.min_y
        dist_sul = arena.max_y - p.pos[1]
        dist_oeste = p.pos[0] - arena.min_x
        dist_leste = arena.max_x - p.pos[0]
        
        # Encontra parede mais próxima
        paredes = [
            ("norte", dist_norte),
            ("sul", dist_sul),
            ("oeste", dist_oeste),
            ("leste", dist_leste),
        ]
        parede_mais_proxima = min(paredes, key=lambda x: x[1])
        
        esp["parede_proxima"] = parede_mais_proxima[0]
        esp["distancia_parede"] = parede_mais_proxima[1]
        
        # === DETECÇÃO DE OBSTÁCULOS ===
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
        
        # === ANÁLISE DE CAMINHOS LIVRES ===
        # Verifica se há obstáculos bloqueando cada direção
        check_dist = 2.0  # Distância de checagem
        
        # Frente (em direção ao inimigo)
        ang_inimigo = math.atan2(inimigo.pos[1] - p.pos[1], inimigo.pos[0] - p.pos[0])
        check_x_frente = p.pos[0] + math.cos(ang_inimigo) * check_dist
        check_y_frente = p.pos[1] + math.sin(ang_inimigo) * check_dist
        esp["caminho_livre"]["frente"] = not arena.colide_obstaculo(
            check_x_frente, check_y_frente, p.raio_fisico
        )
        
        # Trás (oposto ao inimigo)
        check_x_tras = p.pos[0] - math.cos(ang_inimigo) * check_dist
        check_y_tras = p.pos[1] - math.sin(ang_inimigo) * check_dist
        esp["caminho_livre"]["tras"] = not arena.colide_obstaculo(
            check_x_tras, check_y_tras, p.raio_fisico
        )
        
        # Esquerda (perpendicular)
        ang_esq = ang_inimigo + math.pi / 2
        check_x_esq = p.pos[0] + math.cos(ang_esq) * check_dist
        check_y_esq = p.pos[1] + math.sin(ang_esq) * check_dist
        esp["caminho_livre"]["esquerda"] = not arena.colide_obstaculo(
            check_x_esq, check_y_esq, p.raio_fisico
        )
        
        # Direita
        ang_dir = ang_inimigo - math.pi / 2
        check_x_dir = p.pos[0] + math.cos(ang_dir) * check_dist
        check_y_dir = p.pos[1] + math.sin(ang_dir) * check_dist
        esp["caminho_livre"]["direita"] = not arena.colide_obstaculo(
            check_x_dir, check_y_dir, p.raio_fisico
        )
        
        # === AVALIAÇÃO DE POSIÇÃO TÁTICA ===
        # Encurralado = parede atrás E sem caminhos laterais
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
        dist_ini_parede = min(
            inimigo.pos[1] - arena.min_y,
            arena.max_y - inimigo.pos[1],
            inimigo.pos[0] - arena.min_x,
            arena.max_x - inimigo.pos[0]
        )
        esp["oponente_contra_parede"] = dist_ini_parede < 2.5
        
        # Posição geral
        if esp["encurralado"]:
            esp["posicao_tatica"] = "encurralado"
        elif esp["distancia_parede"] < 2.0:
            esp["posicao_tatica"] = "perto_parede"
        elif esp["oponente_contra_parede"]:
            esp["posicao_tatica"] = "vantagem"
        else:
            esp["posicao_tatica"] = "centro"
        
        # === ANÁLISE TÁTICA ===
        self._avaliar_taticas_espaciais(distancia, inimigo)

    
    def _avaliar_taticas_espaciais(self, distancia, inimigo):
        """
        Avalia e define táticas espaciais baseadas na situação.
        VERSÃO MELHORADA v10.0 - mais inteligente e baseada em traços.
        """
        esp = self.consciencia_espacial
        tatica = self.tatica_espacial
        p = self.parent
        hp_pct = p.vida / p.vida_max
        
        # Reset táticas
        tatica["usando_cobertura"] = False
        tatica["forcar_canto"] = False
        tatica["recuar_para_obstaculo"] = False
        tatica["flanquear_obstaculo"] = False
        
        # === SE ENCURRALADO ===
        if esp["encurralado"]:
            # Reação depende da personalidade
            if "BERSERKER" in self.tracos or "KAMIKAZE" in self.tracos:
                # Berserkers ficam mais perigosos quando encurralados
                self.raiva = min(1.0, self.raiva + 0.4)
                self.medo = max(0, self.medo - 0.2)
                self.hesitacao = 0
            elif "COVARDE" in self.tracos or "MEDROSO" in self.tracos:
                # Covardes entram em pânico
                self.medo = min(1.0, self.medo + 0.4)
                self.hesitacao = min(0.8, self.hesitacao + 0.3)
            elif "FRIO" in self.tracos or "CALCULISTA" in self.tracos:
                # Calculistas mantêm a calma e planejam escape
                self.hesitacao = max(0.0, self.hesitacao - 0.2)
            else:
                # Padrão: stress moderado
                self.medo = min(1.0, self.medo + 0.2)
                self.hesitacao = max(0.0, self.hesitacao - 0.1)
            
            # Determina melhor rota de escape baseado em traços
            if esp["caminho_livre"]["esquerda"] and esp["caminho_livre"]["direita"]:
                # Escolhe baseado em tendência ou aleatoriedade
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
        
        # === OPONENTE CONTRA PAREDE/OBSTÁCULO ===
        oponente_vulneravel = esp.get("oponente_contra_parede", False) or esp.get("oponente_perto_obstaculo", False)
        if oponente_vulneravel and distancia < 6.0:
            tatica["forcar_canto"] = True
            self.confianca = min(1.0, self.confianca + 0.15)
            
            # BUG-AI-05 fix: pressão extra via modificador temporário (não corrompe a personalidade base)
            if "PREDADOR" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.25)
            if "SANGUINARIO" in self.tracos or "IMPLACAVEL" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.20)
            if "OPORTUNISTA" in self.tracos:
                self._agressividade_temp_mod = min(0.5, self._agressividade_temp_mod + 0.15)
        
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
            
            # Berserkers e kamikazes não usam cobertura
            if "BERSERKER" in self.tracos or "KAMIKAZE" in self.tracos or "IMPLACAVEL" in self.tracos:
                usa_cobertura = False
            
            if usa_cobertura:
                tatica["usando_cobertura"] = True
                tatica["tipo_cobertura"] = getattr(obs_proximo, 'tipo', 'obstaculo')
        
        # === FLANQUEAMENTO COM OBSTÁCULOS ===
        if obs_proximo and 3.0 < distancia < 8.0 and dist_obs < 4.0:
            # Flanqueio é mais provável com certos traços
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
        
        # === EVITA RECUAR PARA OBSTÁCULO ===
        if not esp["caminho_livre"]["tras"] and distancia < 4.0:
            tatica["recuar_para_obstaculo"] = True
            
            # Ajusta ação se estava tentando recuar
            if self.acao_atual in ["RECUAR", "FUGIR"]:
                if "BERSERKER" in self.tracos:
                    self.acao_atual = "MATAR"  # Não foge, ataca!
                elif random.random() < 0.7:
                    self.acao_atual = "CIRCULAR"
                else:
                    self.acao_atual = "FLANQUEAR"

    
    def _aplicar_modificadores_espaciais(self, distancia, inimigo):
        """
        Aplica modificadores de comportamento baseados no ambiente.
        VERSÃO MELHORADA v10.0 - decisões mais inteligentes.
        """
        esp = self.consciencia_espacial
        tatica = self.tatica_espacial
        p = self.parent
        
        # === MODIFICADORES POR SITUAÇÃO ===
        
        # Se encurralado
        if esp["encurralado"]:
            # Escolha depende do balanço medo/raiva e traços
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
                # Padrão: mistura de escape e contra-ataque
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
            if random.random() < 0.35:
                self.acao_atual = random.choice(["PRESSIONAR", "MATAR", "ESMAGAR"])
        
        # Se usando cobertura
        if tatica["usando_cobertura"]:
            if random.random() < 0.25:
                # Fica atrás do obstáculo
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "BLOQUEAR"])
        
        # Se flanqueando com obstáculo
        if tatica["flanquear_obstaculo"]:
            if random.random() < 0.2:
                self.acao_atual = "FLANQUEAR"
        
        # Se recuando pra obstáculo
        if tatica["recuar_para_obstaculo"]:
            # NUNCA recua
            if self.acao_atual in ["RECUAR", "FUGIR"]:
                self.acao_atual = random.choice(["CIRCULAR", "COMBATE", "FLANQUEAR"])
        
        # === MODIFICADORES POR DIREÇÃO ===
        
        # Se caminho da frente bloqueado
        if not esp["caminho_livre"]["frente"]:
            if self.acao_atual in ["APROXIMAR", "MATAR", "PRESSIONAR"]:
                # Circula ao invés de ir direto
                if random.random() < 0.4:
                    self.acao_atual = "FLANQUEAR"
        
        # Se perto de parede
        if esp["distancia_parede"] < 2.0:
            # Ajusta direção circular pra não bater na parede
            if esp["parede_proxima"] in ["oeste", "leste"]:
                # Parede lateral - ajusta se necessário
                if esp["parede_proxima"] == "oeste" and self.dir_circular < 0:
                    self.dir_circular = 1
                elif esp["parede_proxima"] == "leste" and self.dir_circular > 0:
                    self.dir_circular = -1

    
    def _ajustar_direcao_por_ambiente(self, direcao_alvo):
        """
        Ajusta uma direção de movimento para evitar obstáculos.
        Retorna nova direção segura.
        """
        esp = self.consciencia_espacial
        p = self.parent
        
        # Converte direção pra radianos
        ang_rad = math.radians(direcao_alvo)
        
        # Verifica se a direção está bloqueada
        try:
            if _get_arena is None:
                raise ImportError("arena não disponível")
            arena = _get_arena()  # QC-04: usa _get_arena de nível de módulo
            
            # Testa ponto à frente
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
                
                # Se tudo bloqueado, fica parado (retorna direção atual)
                return direcao_alvo
        except (AttributeError, TypeError, Exception):
            pass
        
        return direcao_alvo
