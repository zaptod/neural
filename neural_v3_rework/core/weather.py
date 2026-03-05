"""
NEURAL FIGHTS — Sistema de Clima v1.0
======================================
Clima dinâmico que afeta o combate.
Muda periodicamente durante a luta e aplica efeitos globais.
Integra com simulacao.py (update + render) e entities.py (movement mods).
"""

import random
import math
from typing import Dict, List, Optional, Any, Tuple


# ============================================================================
# TIPOS DE CLIMA
# ============================================================================

CLIMAS = {
    "limpo": {
        "nome": "Céu Limpo",
        "descricao": "Sem efeitos climáticos",
        "icone": "☀️",
        "mod_velocidade": 1.0,
        "mod_visao": 1.0,
        "cor_overlay": None,
        "particulas": None,
        "peso_chance": 35,
    },
    "chuva": {
        "nome": "Chuva Torrencial",
        "descricao": "Reduz velocidade e visão. Chance de escorregar.",
        "icone": "🌧️",
        "mod_velocidade": 0.92,
        "mod_visao": 0.8,
        "cor_overlay": (30, 40, 80, 40),  # RGBA
        "particulas": {"tipo": "chuva", "quantidade": 80, "cor": (150, 180, 220), "velocidade": 15},
        "efeito": "escorregar",
        "chance_escorregar": 0.015,
        "peso_chance": 20,
    },
    "tempestade": {
        "nome": "Tempestade Elétrica",
        "descricao": "Raios caem aleatoriamente causando dano.",
        "icone": "⛈️",
        "mod_velocidade": 0.88,
        "mod_visao": 0.65,
        "cor_overlay": (20, 20, 50, 50),
        "particulas": {"tipo": "chuva", "quantidade": 120, "cor": (130, 150, 200), "velocidade": 18},
        "efeito": "raio_aleatorio",
        "raio_intervalo": 5.0,
        "raio_dano": 15.0,
        "raio_area": 2.0,
        "peso_chance": 10,
    },
    "neblina": {
        "nome": "Neblina Densa",
        "descricao": "Reduz drasticamente o alcance de percepção da IA.",
        "icone": "🌫️",
        "mod_velocidade": 1.0,
        "mod_visao": 0.4,
        "cor_overlay": (120, 120, 130, 80),
        "particulas": {"tipo": "neblina", "quantidade": 30, "cor": (180, 180, 190), "velocidade": 0.5},
        "efeito": "reducao_percepcao",
        "peso_chance": 15,
    },
    "neve": {
        "nome": "Nevasca Congelante",
        "descricao": "Velocidade reduzida. Chance de slow adicional.",
        "icone": "🌨️",
        "mod_velocidade": 0.85,
        "mod_visao": 0.7,
        "cor_overlay": (180, 200, 230, 35),
        "particulas": {"tipo": "neve", "quantidade": 60, "cor": (220, 230, 245), "velocidade": 3},
        "efeito": "gelo_chao",
        "chance_slow": 0.02,
        "slow_duracao": 1.5,
        "peso_chance": 12,
    },
    "eclipse": {
        "nome": "Eclipse Sombrio",
        "descricao": "Trevas fortalecidas, Luz enfraquecida.",
        "icone": "🌑",
        "mod_velocidade": 1.0,
        "mod_visao": 0.5,
        "cor_overlay": (10, 5, 20, 70),
        "particulas": {"tipo": "sombra", "quantidade": 20, "cor": (50, 30, 70), "velocidade": 1},
        "efeito": "trevas_buff",
        "buff_trevas": 1.25,
        "nerf_luz": 0.75,
        "peso_chance": 8,
    },
}


class WeatherParticle:
    """Partícula de clima individual"""
    
    def __init__(self, tipo: str, screen_w: int, screen_h: int, cor: Tuple[int, int, int], vel: float):
        self.tipo = tipo
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.cor = cor
        self.vel = vel
        self.reset()
    
    def reset(self):
        """Reposiciona a partícula"""
        if self.tipo == "chuva":
            self.x = random.randint(0, self.screen_w)
            self.y = random.randint(-50, 0)
            self.comprimento = random.randint(5, 15)
            self.vel_x = random.uniform(-1, 1)
        elif self.tipo == "neve":
            self.x = random.randint(0, self.screen_w)
            self.y = random.randint(-20, 0)
            self.tamanho = random.randint(2, 5)
            self.vel_x = random.uniform(-1.5, 1.5)
            self.oscilacao = random.uniform(0, math.pi * 2)
        elif self.tipo == "neblina":
            self.x = random.randint(0, self.screen_w)
            self.y = random.randint(0, self.screen_h)
            self.tamanho = random.randint(40, 100)
            self.alpha = random.randint(20, 60)
            self.vel_x = random.uniform(-0.3, 0.3)
        elif self.tipo == "sombra":
            self.x = random.randint(0, self.screen_w)
            self.y = random.randint(0, self.screen_h)
            self.tamanho = random.randint(20, 60)
            self.alpha = random.randint(30, 80)
            self.vel_x = random.uniform(-0.5, 0.5)
            self.vel_y = random.uniform(-0.5, 0.5)
    
    def update(self, dt: float):
        """Atualiza posição"""
        if self.tipo == "chuva":
            self.y += self.vel * dt * 50
            self.x += self.vel_x * dt * 50
            if self.y > self.screen_h:
                self.reset()
        elif self.tipo == "neve":
            self.y += self.vel * dt * 50
            self.oscilacao += dt * 2
            self.x += (self.vel_x + math.sin(self.oscilacao) * 0.5) * dt * 50
            if self.y > self.screen_h:
                self.reset()
        elif self.tipo == "neblina":
            self.x += self.vel_x * dt * 50
            if self.x < -self.tamanho:
                self.x = self.screen_w + self.tamanho
            elif self.x > self.screen_w + self.tamanho:
                self.x = -self.tamanho
        elif self.tipo == "sombra":
            self.x += self.vel_x * dt * 50
            self.y += self.vel_y * dt * 50
            if self.x < -self.tamanho: self.x = self.screen_w + self.tamanho
            if self.y < -self.tamanho: self.y = self.screen_h + self.tamanho


class WeatherSystem:
    """
    Sistema de clima dinâmico.
    Singleton pattern consistente com o resto do projeto.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        cls._instance = None
    
    def __init__(self):
        self.clima_atual: str = "limpo"
        self.clima_anterior: str = "limpo"
        self.timer_clima = 0.0
        self.duracao_clima = 30.0
        self.transicao_timer = 0.0
        self.transicao_duracao = 3.0
        self.em_transicao = False
        self.proximo_clima: Optional[str] = None
        
        self.particulas: List[WeatherParticle] = []
        self.screen_w = 1200
        self.screen_h = 800
        
        # Raio (para tempestade)
        self.raio_timer = 0.0
        self.raio_flash_timer = 0.0
        self.raio_pos = None  # (x_metros, y_metros) do último raio
        
        # Estado de arena para verificar se clima é compatível
        self._arena_tema = "neutro"
    
    def set_screen_size(self, w: int, h: int):
        self.screen_w = w
        self.screen_h = h
    
    def set_arena_tema(self, tema: str):
        """Ajusta pesos de clima baseado na arena"""
        self._arena_tema = tema
    
    def iniciar(self, clima_inicial: Optional[str] = None):
        """Inicia o sistema com um clima"""
        if clima_inicial and clima_inicial in CLIMAS:
            self.clima_atual = clima_inicial
        else:
            self.clima_atual = self._sortear_clima()
        
        self.duracao_clima = random.uniform(20.0, 45.0)
        self.timer_clima = 0.0
        self._criar_particulas()
    
    def _sortear_clima(self) -> str:
        """Sorteia um novo clima baseado nos pesos"""
        opcoes = []
        pesos = []
        for nome, dados in CLIMAS.items():
            # Ajusta peso baseado na arena
            peso = dados["peso_chance"]
            if self._arena_tema == "vulcao" and nome == "neve":
                peso = 0  # Sem neve no vulcão
            elif self._arena_tema == "vulcao" and nome == "eclipse":
                peso *= 2  # Mais eclipse no vulcão
            elif self._arena_tema == "floresta" and nome == "neblina":
                peso *= 2  # Mais neblina na floresta
            elif self._arena_tema == "gotico" and nome == "eclipse":
                peso *= 2
            opcoes.append(nome)
            pesos.append(max(0, peso))
        
        total = sum(pesos)
        if total == 0:
            return "limpo"
        
        r = random.uniform(0, total)
        acumulado = 0
        for nome, peso in zip(opcoes, pesos):
            acumulado += peso
            if r <= acumulado:
                return nome
        return "limpo"
    
    def _criar_particulas(self):
        """Cria partículas para o clima atual"""
        self.particulas.clear()
        dados = CLIMAS.get(self.clima_atual, {})
        part_config = dados.get("particulas")
        if not part_config:
            return
        
        for _ in range(part_config["quantidade"]):
            p = WeatherParticle(
                part_config["tipo"],
                self.screen_w, self.screen_h,
                part_config["cor"],
                part_config["velocidade"]
            )
            # Distribui posições inicialmente
            p.y = random.randint(0, self.screen_h)
            self.particulas.append(p)
    
    def update(self, dt: float, lutadores: list, arena=None) -> List[Dict]:
        """
        Atualiza clima e aplica efeitos.
        Retorna lista de eventos (raios, escorregões, etc.) para VFX.
        """
        eventos = []
        
        # Timer de troca de clima
        self.timer_clima += dt
        if self.timer_clima >= self.duracao_clima and not self.em_transicao:
            self._iniciar_transicao()
        
        # Processa transição
        if self.em_transicao:
            self.transicao_timer += dt
            if self.transicao_timer >= self.transicao_duracao:
                self.clima_atual = self.proximo_clima or "limpo"
                self.em_transicao = False
                self.timer_clima = 0.0
                self.duracao_clima = random.uniform(20.0, 45.0)
                self._criar_particulas()
        
        # Atualiza partículas
        for p in self.particulas:
            p.update(dt)
        
        # Flash de raio
        if self.raio_flash_timer > 0:
            self.raio_flash_timer -= dt
        
        # Aplica efeitos do clima atual
        dados = CLIMAS.get(self.clima_atual, {})
        efeito = dados.get("efeito")
        
        if efeito == "escorregar" and not self.em_transicao:
            chance = dados.get("chance_escorregar", 0.015)
            for lut in lutadores:
                if lut.morto or lut.z > 0:
                    continue
                vel_mag = math.hypot(lut.vel[0], lut.vel[1])
                if vel_mag > 3.0 and random.random() < chance * dt:
                    # Escorrega: impulso lateral aleatório
                    ang = random.uniform(0, math.pi * 2)
                    force = random.uniform(3.0, 6.0)
                    lut.vel[0] += math.cos(ang) * force
                    lut.vel[1] += math.sin(ang) * force
                    lut.stun_timer = max(lut.stun_timer, 0.3)
                    eventos.append({
                        "tipo": "escorregar",
                        "x": lut.pos[0], "y": lut.pos[1],
                        "lutador": lut
                    })
        
        elif efeito == "raio_aleatorio" and not self.em_transicao:
            intervalo = dados.get("raio_intervalo", 5.0)
            self.raio_timer += dt
            if self.raio_timer >= intervalo:
                self.raio_timer = 0.0
                # Raio cai em posição aleatória (preferencialmente perto de lutadores)
                if lutadores and random.random() < 0.6:
                    alvo = random.choice([l for l in lutadores if not l.morto] or lutadores)
                    rx = alvo.pos[0] + random.uniform(-3, 3)
                    ry = alvo.pos[1] + random.uniform(-3, 3)
                else:
                    # Arena bounds
                    if arena:
                        rx = random.uniform(1, arena.largura - 1)
                        ry = random.uniform(1, arena.altura - 1)
                    else:
                        rx = random.uniform(2, 28)
                        ry = random.uniform(2, 18)
                
                self.raio_pos = (rx, ry)
                self.raio_flash_timer = 0.3
                
                # Emite evento — dano é aplicado pela simulação para
                # garantir kill-registration, narrador, ELO e VFX.
                dano = dados.get("raio_dano", 15.0)
                area = dados.get("raio_area", 2.0)
                
                eventos.append({
                    "tipo": "raio",
                    "x": rx, "y": ry,
                    "raio": area,
                    "dano": dano
                })
        
        elif efeito == "gelo_chao" and not self.em_transicao:
            chance = dados.get("chance_slow", 0.02)
            for lut in lutadores:
                if lut.morto or lut.z > 0:
                    continue
                if random.random() < chance * dt:
                    dur = dados.get("slow_duracao", 1.5)
                    lut.slow_timer = max(lut.slow_timer, dur)
                    lut.slow_fator = min(lut.slow_fator, 0.6)
                    eventos.append({
                        "tipo": "gelo",
                        "x": lut.pos[0], "y": lut.pos[1],
                        "lutador": lut
                    })
        
        return eventos
    
    def get_mod_velocidade(self) -> float:
        """Retorna modificador de velocidade global do clima"""
        dados = CLIMAS.get(self.clima_atual, {})
        if self.em_transicao:
            dados_ant = CLIMAS.get(self.clima_anterior, {})
            t = self.transicao_timer / max(self.transicao_duracao, 0.01)
            v1 = dados_ant.get("mod_velocidade", 1.0)
            v2 = dados.get("mod_velocidade", 1.0) if self.proximo_clima else v1
            return v1 + (v2 - v1) * t
        return dados.get("mod_velocidade", 1.0)
    
    def get_mod_visao(self) -> float:
        """Retorna modificador de visão (para AI)"""
        dados = CLIMAS.get(self.clima_atual, {})
        return dados.get("mod_visao", 1.0)
    
    def get_element_mods(self) -> Dict[str, float]:
        """Retorna modificadores elementais (eclipse: trevas buff, luz nerf)"""
        dados = CLIMAS.get(self.clima_atual, {})
        mods = {}
        if dados.get("efeito") == "trevas_buff":
            mods["TREVAS"] = dados.get("buff_trevas", 1.25)
            mods["LUZ"] = dados.get("nerf_luz", 0.75)
        return mods
    
    def get_overlay_cor(self) -> Optional[Tuple]:
        """Retorna cor de overlay para renderização (RGBA)"""
        dados = CLIMAS.get(self.clima_atual, {})
        if self.em_transicao and self.proximo_clima:
            # Fade entre overlays
            t = self.transicao_timer / max(self.transicao_duracao, 0.01)
            cor_ant = CLIMAS.get(self.clima_anterior, {}).get("cor_overlay")
            cor_prox = CLIMAS.get(self.proximo_clima, {}).get("cor_overlay")
            if not cor_ant and not cor_prox:
                return None
            c1 = cor_ant or (0, 0, 0, 0)
            c2 = cor_prox or (0, 0, 0, 0)
            return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))
        return dados.get("cor_overlay")
    
    def get_display_info(self) -> Dict:
        """Retorna info para HUD"""
        dados = CLIMAS.get(self.clima_atual, CLIMAS["limpo"])
        tempo_restante = max(0, self.duracao_clima - self.timer_clima)
        return {
            "nome": dados["nome"],
            "icone": dados.get("icone", ""),
            "descricao": dados["descricao"],
            "tempo_restante": tempo_restante,
            "em_transicao": self.em_transicao,
        }
    
    def _iniciar_transicao(self):
        """Inicia transição para novo clima"""
        self.clima_anterior = self.clima_atual
        self.proximo_clima = self._sortear_clima()
        # Evita repetir o mesmo clima
        tentativas = 0
        while self.proximo_clima == self.clima_atual and tentativas < 5:
            self.proximo_clima = self._sortear_clima()
            tentativas += 1
        self.em_transicao = True
        self.transicao_timer = 0.0
