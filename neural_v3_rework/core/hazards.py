"""
NEURAL FIGHTS — Sistema de Hazards de Arena v1.0
=================================================
Hazards dinâmicos que causam dano, aplicam efeitos ou alteram o terreno.
Lidos dos obstáculos da ArenaConfig e processados durante a simulação.
Integra com arena.py (dados), simulacao.py (update) e sim_renderer.py (draw).
"""

import math
import random
from typing import Dict, List, Optional, Any, Tuple


class ArenaHazard:
    """Um hazard ativo na arena"""
    
    def __init__(self, tipo: str, x: float, y: float, largura: float, altura: float, 
                 cor: Tuple[int, int, int] = (255, 0, 0)):
        self.tipo = tipo
        self.x = x
        self.y = y
        self.largura = largura
        self.altura = altura
        self.cor = cor
        self.ativo = True
        self.hp: float = -1  # -1 = indestrutível
        self.cooldown = 0.0
        self.timer_animacao = 0.0
        
        # Configurações por tipo
        self._setup()
    
    def _setup(self):
        """Configura parâmetros baseado no tipo"""
        if self.tipo == "lava":
            self.dano_por_seg = 8.0
            self.slow_fator = 0.6
            self.efeito = "QUEIMANDO"
        elif self.tipo == "espinhos":
            self.dano = 12.0
            self.cooldown_max = 1.5
            self.efeito = "SANGRAMENTO"
        elif self.tipo == "barril_explosivo":
            self.hp = 30
            self.dano_explosao = 35.0
            self.raio_explosao = 3.0
            self.efeito = "EXPLOSAO"
        elif self.tipo == "zona_veneno":
            self.dano_por_seg = 5.0
            self.efeito = "ENVENENADO"
            self.raio_encolhe = 0.0  # Pode encolher ao longo do tempo
        elif self.tipo == "pilar_destrutivel":
            self.hp = 80
        elif self.tipo == "gelo_chao":
            self.chance_escorregar = 0.05
        elif self.tipo == "armadilha_urso":
            self.armada = True
            self.dano = 15.0
            self.enraizar_duracao = 2.0
    
    def contem_ponto(self, px: float, py: float) -> bool:
        """Verifica se um ponto está dentro do hazard"""
        hx = self.x - self.largura / 2
        hy = self.y - self.altura / 2
        return (hx <= px <= hx + self.largura and 
                hy <= py <= hy + self.altura)
    
    def distancia_ao_centro(self, px: float, py: float) -> float:
        """Distância de um ponto ao centro do hazard"""
        return math.hypot(px - self.x, py - self.y)


class HazardSystem:
    """
    Gerencia hazards dinâmicos na arena.
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
        self.hazards: List[ArenaHazard] = []
        self._dano_cooldowns: Dict[int, Dict[int, float]] = {}  # {hazard_idx: {lutador_id: timer}}
    
    def carregar_da_arena(self, arena):
        """Carrega hazards dos obstáculos da arena que têm efeitos"""
        self.hazards.clear()
        self._dano_cooldowns.clear()
        
        if not arena or not hasattr(arena, 'config'):
            return
        
        for obs in arena.config.obstaculos:
            # Tipos de obstáculo que se tornam hazards
            if obs.tipo in ("lava", "espinhos", "barril_explosivo", "zona_veneno", 
                           "gelo_chao", "armadilha_urso"):
                hazard = ArenaHazard(obs.tipo, obs.x, obs.y, obs.largura, obs.altura, obs.cor)
                self.hazards.append(hazard)
            elif obs.destrutivel:
                hazard = ArenaHazard("pilar_destrutivel", obs.x, obs.y, obs.largura, obs.altura, obs.cor)
                hazard.hp = obs.hp
                self.hazards.append(hazard)
    
    def adicionar_hazard(self, tipo: str, x: float, y: float, 
                         largura: float = 2.0, altura: float = 2.0,
                         cor: Tuple[int, int, int] = (255, 0, 0)):
        """Adiciona um hazard dinâmico (ex: criado por skill ou evento)"""
        hazard = ArenaHazard(tipo, x, y, largura, altura, cor)
        self.hazards.append(hazard)
        return hazard
    
    def update(self, dt: float, lutadores: list) -> List[Dict[str, Any]]:
        """
        Atualiza hazards e aplica efeitos nos lutadores.
        Retorna lista de eventos para VFX.
        """
        eventos = []
        
        for idx, hazard in enumerate(self.hazards):
            if not hazard.ativo:
                continue
            
            hazard.timer_animacao += dt
            hazard.cooldown = max(0, hazard.cooldown - dt)
            
            # Atualiza cooldowns de dano por lutador
            if idx not in self._dano_cooldowns:
                self._dano_cooldowns[idx] = {}
            for lid in list(self._dano_cooldowns[idx].keys()):
                self._dano_cooldowns[idx][lid] -= dt
                if self._dano_cooldowns[idx][lid] <= 0:
                    del self._dano_cooldowns[idx][lid]
            
            for lut in lutadores:
                if lut.morto or lut.z > 0.5:  # No ar = seguro da maioria dos hazards
                    continue
                
                lid = id(lut)
                
                if not hazard.contem_ponto(lut.pos[0], lut.pos[1]):
                    continue
                
                # === LAVA ===
                if hazard.tipo == "lava":
                    if self._dano_cooldowns[idx].get(lid, 0) <= 0:
                        dano = hazard.dano_por_seg * dt * 3  # Tick rápido
                        lut.tomar_dano(dano, 0, 0, "QUEIMANDO")
                        lut.slow_timer = max(lut.slow_timer, 0.5)
                        lut.slow_fator = min(lut.slow_fator, hazard.slow_fator)
                        self._dano_cooldowns[idx][lid] = 0.3
                        eventos.append({
                            "tipo": "lava_dano",
                            "x": lut.pos[0], "y": lut.pos[1],
                            "lutador": lut
                        })
                
                # === ESPINHOS ===
                elif hazard.tipo == "espinhos" and hazard.cooldown <= 0:
                    if self._dano_cooldowns[idx].get(lid, 0) <= 0:
                        lut.tomar_dano(hazard.dano, 0, 0, "SANGRAMENTO")
                        self._dano_cooldowns[idx][lid] = hazard.cooldown_max
                        eventos.append({
                            "tipo": "espinhos_dano",
                            "x": lut.pos[0], "y": lut.pos[1],
                            "lutador": lut
                        })
                
                # === BARRIL EXPLOSIVO ===
                elif hazard.tipo == "barril_explosivo":
                    # Explode quando atingido por ataque (verificado em on_attack_hit)
                    # Aqui só verifica proximidade extrema
                    dist = hazard.distancia_ao_centro(lut.pos[0], lut.pos[1])
                    if dist < 0.5 and lut.atacando:
                        ev = self._explodir_barril(idx, hazard, lutadores)
                        if ev:
                            eventos.append(ev)
                
                # === ZONA DE VENENO ===
                elif hazard.tipo == "zona_veneno":
                    if self._dano_cooldowns[idx].get(lid, 0) <= 0:
                        dano = hazard.dano_por_seg * dt * 2
                        lut.tomar_dano(dano, 0, 0, "ENVENENADO")
                        self._dano_cooldowns[idx][lid] = 0.5
                
                # === GELO NO CHÃO ===
                elif hazard.tipo == "gelo_chao":
                    vel_mag = math.hypot(lut.vel[0], lut.vel[1])
                    if vel_mag > 2.0 and random.random() < hazard.chance_escorregar * dt:
                        ang = random.uniform(0, math.pi * 2)
                        lut.vel[0] += math.cos(ang) * 4.0
                        lut.vel[1] += math.sin(ang) * 4.0
                        lut.stun_timer = max(lut.stun_timer, 0.2)
                        eventos.append({
                            "tipo": "escorregar",
                            "x": lut.pos[0], "y": lut.pos[1]
                        })
                
                # === ARMADILHA DE URSO ===
                elif hazard.tipo == "armadilha_urso" and getattr(hazard, 'armada', False):
                    lut.tomar_dano(hazard.dano, 0, 0, "SANGRAMENTO")
                    lut._aplicar_efeito_status("ENRAIZADO", duracao=hazard.enraizar_duracao)
                    hazard.armada = False
                    hazard.cooldown = 10.0  # Re-arma depois de 10s
                    eventos.append({
                        "tipo": "armadilha",
                        "x": hazard.x, "y": hazard.y,
                        "lutador": lut
                    })
            
            # Re-armar armadilha
            if hazard.tipo == "armadilha_urso" and not getattr(hazard, 'armada', True):
                if hazard.cooldown <= 0:
                    hazard.armada = True
        
        # Remove hazards destruídos
        self.hazards = [h for h in self.hazards if h.ativo]
        
        return eventos
    
    def on_attack_hit_area(self, x: float, y: float, dano: float, raio: float = 1.5,
                           lutadores: Optional[list] = None) -> List[Dict]:
        """Verifica se um ataque atingiu algum hazard destrutível"""
        eventos = []
        for idx, hazard in enumerate(self.hazards):
            if not hazard.ativo:
                continue
            
            dist = hazard.distancia_ao_centro(x, y)
            
            if hazard.tipo == "barril_explosivo" and dist < raio + 1.0:
                ev = self._explodir_barril(idx, hazard, lutadores or [])
                if ev:
                    eventos.append(ev)
            
            elif hazard.tipo == "pilar_destrutivel" and dist < raio + 0.5:
                hazard.hp -= dano
                if hazard.hp <= 0:
                    hazard.ativo = False
                    eventos.append({
                        "tipo": "pilar_destruido",
                        "x": hazard.x, "y": hazard.y,
                        "largura": hazard.largura
                    })
        
        return eventos
    
    def _explodir_barril(self, idx: int, hazard: ArenaHazard, lutadores: list) -> Optional[Dict]:
        """Processa explosão de barril"""
        if not hazard.ativo:
            return None
        
        hazard.ativo = False
        raio = hazard.raio_explosao
        dano = hazard.dano_explosao
        
        for lut in lutadores:
            if lut.morto:
                continue
            dist = hazard.distancia_ao_centro(lut.pos[0], lut.pos[1])
            if dist < raio:
                dano_real = dano * (1.0 - dist / raio)
                dx = lut.pos[0] - hazard.x
                dy = lut.pos[1] - hazard.y
                d = max(math.hypot(dx, dy), 0.1)
                empx = (dx / d) * 0.5
                empy = (dy / d) * 0.5
                lut.tomar_dano(dano_real, empx, empy, "EXPLOSAO")
        
        return {
            "tipo": "barril_explosao",
            "x": hazard.x, "y": hazard.y,
            "raio": raio,
            "dano": dano
        }
    
    def get_hazards_info(self) -> List[Dict]:
        """Retorna lista de hazards para renderização"""
        info = []
        for h in self.hazards:
            if not h.ativo:
                continue
            info.append({
                "tipo": h.tipo,
                "x": h.x, "y": h.y,
                "largura": h.largura, "altura": h.altura,
                "cor": h.cor,
                "timer_anim": h.timer_animacao,
                "hp": h.hp if h.hp > 0 else None,
            })
        return info
