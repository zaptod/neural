"""
NEURAL FIGHTS - Sistema de Consciência Espacial v9.0
Sistema de reconhecimento de paredes, obstáculos e posicionamento tático.
"""

import math
import random


class SpatialAwarenessSystem:
    """
    Sistema de consciência espacial para IA.
    Gerencia awareness de paredes, obstáculos e posicionamento tático.
    """
    
    def __init__(self, parent):
        self.parent = parent
        
        # Estado de consciência espacial
        self.consciencia = {
            "parede_proxima": None,  # None, "norte", "sul", "leste", "oeste"
            "distancia_parede": 999.0,
            "obstaculo_proxima": None,  # Obstáculo mais próximo
            "distancia_obstaculo": 999.0,
            "encurralado": False,
            "oponente_contra_parede": False,
            "caminho_livre": {"frente": True, "tras": True, "esquerda": True, "direita": True},
            "posicao_tatica": "centro",  # "centro", "perto_parede", "encurralado", "vantagem"
        }
        
        # Táticas espaciais
        self.tatica = {
            "usando_cobertura": False,
            "tipo_cobertura": None,  # "pilar", "obstaculo", "parede"
            "forcar_canto": False,  # Tentando encurralar oponente
            "recuar_para_obstaculo": False,  # Recuando de costas pra obstáculo (perigoso)
            "flanquear_obstaculo": False,  # Usando obstáculo pra flanquear
            "last_check_time": 0.0,  # Otimização - não checa todo frame
        }
    
    def atualizar(self, dt, distancia, inimigo):
        """
        Atualiza awareness de paredes, obstáculos e posicionamento tático.
        """
        # Otimização: só checa a cada 0.2s
        self.tatica["last_check_time"] += dt
        if self.tatica["last_check_time"] < 0.2:
            return
        self.tatica["last_check_time"] = 0.0
        
        p = self.parent
        esp = self.consciencia
        
        # Importa arena
        try:
            from arena import get_arena
            arena = get_arena()
        except:
            return  # Se arena não disponível, ignora
        
        # === DETECÇÃO DE PAREDES ===
        self._detectar_paredes(p, arena, esp)
        
        # === DETECÇÃO DE OBSTÁCULOS ===
        self._detectar_obstaculos(p, arena, esp)
        
        # === ANÁLISE DE CAMINHOS LIVRES ===
        self._analisar_caminhos(p, arena, esp, inimigo)
        
        # === VERIFICA ENCURRALAMENTO ===
        self._verificar_encurralamento(esp)
        
        # === VERIFICA OPONENTE CONTRA PAREDE ===
        self._verificar_oponente_contra_parede(arena, inimigo, esp)
        
        # === DEFINE POSIÇÃO TÁTICA ===
        self._definir_posicao_tatica(esp, distancia)
    
    def _detectar_paredes(self, p, arena, esp):
        """Detecta paredes próximas"""
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
    
    def _detectar_obstaculos(self, p, arena, esp):
        """Detecta obstáculos próximos"""
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
    
    def _analisar_caminhos(self, p, arena, esp, inimigo):
        """Verifica se há obstáculos bloqueando cada direção"""
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
    
    def _verificar_encurralamento(self, esp):
        """Verifica se está encurralado"""
        caminhos_bloqueados = sum(
            1 for livre in esp["caminho_livre"].values() if not livre
        )
        
        # Encurralado se:
        # - Parede muito próxima (< 1.5m) E 2+ caminhos bloqueados
        # - OU 3+ caminhos bloqueados
        esp["encurralado"] = (
            (esp["distancia_parede"] < 1.5 and caminhos_bloqueados >= 2) or
            caminhos_bloqueados >= 3
        )
    
    def _verificar_oponente_contra_parede(self, arena, inimigo, esp):
        """Verifica se oponente está contra a parede"""
        dist_norte = inimigo.pos[1] - arena.min_y
        dist_sul = arena.max_y - inimigo.pos[1]
        dist_oeste = inimigo.pos[0] - arena.min_x
        dist_leste = arena.max_x - inimigo.pos[0]
        
        min_dist = min(dist_norte, dist_sul, dist_oeste, dist_leste)
        esp["oponente_contra_parede"] = min_dist < 2.0
    
    def _definir_posicao_tatica(self, esp, distancia):
        """Define a posição tática atual"""
        if esp["encurralado"]:
            esp["posicao_tatica"] = "encurralado"
        elif esp["distancia_parede"] < 2.5:
            esp["posicao_tatica"] = "perto_parede"
        elif esp["oponente_contra_parede"] and distancia < 4.0:
            esp["posicao_tatica"] = "vantagem"
        else:
            esp["posicao_tatica"] = "centro"
    
    def avaliar_taticas(self, distancia, inimigo, tracos):
        """
        Avalia e retorna modificadores táticos baseados na posição espacial.
        Retorna um dict com modificadores de comportamento.
        """
        esp = self.consciencia
        tatica = self.tatica
        
        modificadores = {
            "evitar_recuo": False,
            "forcar_lateral": False,
            "pressao_extra": 0.0,
            "direcao_preferida": None,
            "urgencia_reposicionamento": 0.0,
        }
        
        # === COMPORTAMENTOS QUANDO ENCURRALADO ===
        if esp["encurralado"]:
            modificadores["urgencia_reposicionamento"] = 0.8
            modificadores["evitar_recuo"] = True
            
            # Determina melhor direção de fuga
            for direcao, livre in esp["caminho_livre"].items():
                if livre:
                    modificadores["direcao_preferida"] = direcao
                    break
        
        # === APROVEITAR OPONENTE CONTRA PAREDE ===
        if esp["oponente_contra_parede"]:
            modificadores["pressao_extra"] = 0.3
            
            if "PREDADOR" in tracos or "SANGUINARIO" in tracos:
                modificadores["pressao_extra"] = 0.5
                tatica["forcar_canto"] = True
        
        # === EVITAR RECUAR PARA OBSTÁCULOS ===
        if not esp["caminho_livre"]["tras"]:
            modificadores["evitar_recuo"] = True
            modificadores["forcar_lateral"] = True
        
        # === USAR COBERTURA ===
        if esp["distancia_obstaculo"] < 3.0 and esp["obstaculo_proxima"]:
            obs = esp["obstaculo_proxima"]
            if hasattr(obs, 'bloqueiaProjeteis') and obs.bloqueiaProjeteis:
                tatica["usando_cobertura"] = True
                tatica["tipo_cobertura"] = "obstaculo"
        
        return modificadores
    
    def ajustar_direcao(self, direcao_alvo, tracos):
        """
        Ajusta uma direção de movimento para evitar colisões.
        Retorna a direção ajustada.
        """
        esp = self.consciencia
        p = self.parent
        
        # Se direção alvo leva para obstáculo/parede, ajusta
        try:
            from arena import get_arena
            arena = get_arena()
        except:
            return direcao_alvo
        
        # Calcula posição alvo
        check_dist = 1.5
        rad = math.radians(direcao_alvo)
        check_x = p.pos[0] + math.cos(rad) * check_dist
        check_y = p.pos[1] + math.sin(rad) * check_dist
        
        # Se caminho livre, mantém direção
        if not arena.colide_obstaculo(check_x, check_y, p.raio_fisico):
            # Checa também limites da arena
            if arena.min_x + 1 < check_x < arena.max_x - 1:
                if arena.min_y + 1 < check_y < arena.max_y - 1:
                    return direcao_alvo
        
        # Procura alternativa
        for ajuste in [30, -30, 60, -60, 90, -90, 120, -120]:
            nova_dir = direcao_alvo + ajuste
            rad = math.radians(nova_dir)
            check_x = p.pos[0] + math.cos(rad) * check_dist
            check_y = p.pos[1] + math.sin(rad) * check_dist
            
            if not arena.colide_obstaculo(check_x, check_y, p.raio_fisico):
                if arena.min_x + 1 < check_x < arena.max_x - 1:
                    if arena.min_y + 1 < check_y < arena.max_y - 1:
                        return nova_dir
        
        # Se nada funcionar, mantém original
        return direcao_alvo
    
    def get_estado(self):
        """Retorna o estado atual da consciência espacial"""
        return {
            "consciencia": self.consciencia.copy(),
            "tatica": self.tatica.copy(),
        }
