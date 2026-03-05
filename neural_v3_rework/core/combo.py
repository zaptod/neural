"""
NEURAL FIGHTS — Sistema de Combo v1.0
======================================
Detecta e recompensa sequências de ataques.
Integra com o hit-detection em sim_combat.py e com entities.py.

Um combo é uma sequência de hits dentro de uma janela de tempo.
Cada hit subsequente escala dano e knockback.
No final do combo (hit final ou timeout), aplica um finisher.
"""

import time
import math
import random
from typing import Dict, List, Optional, Any


# ============================================================================
# DADOS DE COMBO
# ============================================================================

COMBO_FINISHERS = {
    "launch": {
        "nome": "Lançamento",
        "descricao": "Lança o inimigo no ar",
        "vel_z": 14.0,
        "stun": 0.8,
        "dano_mult": 1.0,
    },
    "wallbounce": {
        "nome": "Ricochete",
        "descricao": "Empurra com força contra a parede",
        "knockback_mult": 2.5,
        "stun": 0.6,
        "dano_mult": 1.2,
    },
    "ground_slam": {
        "nome": "Esmagar",
        "descricao": "Golpe de área devastador",
        "dano_mult": 1.8,
        "area_raio": 2.0,
        "stun": 0.4,
    },
}

# Classes que preferem cada tipo de finisher
FINISHER_POR_CLASSE = {
    "Guerreiro": "ground_slam",
    "Berserker": "ground_slam",
    "Gladiador": "wallbounce",
    "Cavaleiro": "wallbounce",
    "Assassino": "launch",
    "Ladino": "launch",
    "Ninja": "launch",
    "Duelista": "wallbounce",
    "Mago": "launch",
    "Piromante": "ground_slam",
    "Criomante": "ground_slam",
    "Necromante": "launch",
    "Paladino": "wallbounce",
    "Druida": "ground_slam",
    "Feiticeiro": "launch",
    "Monge": "launch",
}


class ComboTracker:
    """Rastreia combos de um lutador individual"""
    
    def __init__(self, lutador):
        self.lutador = lutador
        self.combo_count = 0
        self.ultimo_hit_time = 0.0
        self.combo_timer = 0.0
        self.dano_total_combo = 0.0
        self.alvos_no_combo = set()
        self.melhor_combo = 0  # Melhor combo da luta
        self._combo_janela = 1.2  # Segundos para manter o combo
        
        # Escalonamento
        self._dano_escalar = [1.0, 1.1, 1.2, 1.35, 1.5]
        self._kb_escalar = [1.0, 1.0, 1.1, 1.2, 1.5]
        self._max_hits = 5
        
        # Finisher preferido baseado na classe
        classe_nome = getattr(lutador, 'classe_nome', '')
        self.finisher_preferido = "launch"  # Default
        for cls_key, finisher in FINISHER_POR_CLASSE.items():
            if cls_key in classe_nome:
                self.finisher_preferido = finisher
                break
    
    def registrar_hit(self, dano: float, alvo, tempo_atual: float) -> Dict[str, Any]:
        """
        Registra um hit e retorna modificadores de combo.
        
        Returns:
            dict com: dano_mult, kb_mult, combo_count, is_finisher, finisher_data
        """
        resultado = {
            "dano_mult": 1.0,
            "kb_mult": 1.0,
            "combo_count": 0,
            "is_finisher": False,
            "finisher_data": None,
            "novo_combo": False,
        }
        
        # Verifica se está dentro da janela de combo
        if (tempo_atual - self.ultimo_hit_time) <= self._combo_janela and self.combo_count > 0:
            self.combo_count += 1
        else:
            # Novo combo ou primeiro hit
            if self.combo_count >= 3:
                # Combo anterior terminou — salva stats
                self.melhor_combo = max(self.melhor_combo, self.combo_count)
            self.combo_count = 1
            self.dano_total_combo = 0.0
            self.alvos_no_combo.clear()
            resultado["novo_combo"] = True
        
        self.ultimo_hit_time = tempo_atual
        self.combo_timer = self._combo_janela
        self.alvos_no_combo.add(id(alvo))
        
        # Escalonamento
        idx = min(self.combo_count - 1, len(self._dano_escalar) - 1)
        resultado["dano_mult"] = self._dano_escalar[idx]
        resultado["kb_mult"] = self._kb_escalar[idx]
        resultado["combo_count"] = self.combo_count
        
        # Finisher: no hit máximo do combo
        if self.combo_count >= self._max_hits:
            resultado["is_finisher"] = True
            resultado["finisher_data"] = COMBO_FINISHERS.get(
                self.finisher_preferido, COMBO_FINISHERS["launch"])
            # Reset combo após finisher
            self.melhor_combo = max(self.melhor_combo, self.combo_count)
            self.combo_count = 0
        
        self.dano_total_combo += dano * resultado["dano_mult"]
        return resultado
    
    def update(self, dt: float):
        """Atualiza timer do combo"""
        if self.combo_count > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                # Combo expirou
                self.melhor_combo = max(self.melhor_combo, self.combo_count)
                self.combo_count = 0
                self.dano_total_combo = 0.0
                self.alvos_no_combo.clear()
    
    def get_combo_display(self) -> Optional[Dict]:
        """Retorna dados para exibição do combo (None se < 2 hits)"""
        if self.combo_count < 2:
            return None
        return {
            "hits": self.combo_count,
            "dano_total": self.dano_total_combo,
            "timer_pct": self.combo_timer / self._combo_janela,
            "max_hits": self._max_hits,
        }


class ComboSystem:
    """
    Gerenciador global de combos.
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
        self._trackers: Dict[int, ComboTracker] = {}
        self._tempo_luta = 0.0
        self._combo_breaker_cooldowns: Dict[int, float] = {}
    
    def registrar_lutador(self, lutador):
        """Registra um lutador no sistema de combo"""
        self._trackers[id(lutador)] = ComboTracker(lutador)
    
    def on_hit(self, atacante, alvo, dano_base: float) -> Dict[str, Any]:
        """
        Chamado quando um ataque acerta.
        Retorna modificadores de combo a serem aplicados.
        """
        tracker = self._trackers.get(id(atacante))
        if not tracker:
            return {"dano_mult": 1.0, "kb_mult": 1.0, "combo_count": 0,
                    "is_finisher": False, "finisher_data": None}
        
        return tracker.registrar_hit(dano_base, alvo, self._tempo_luta)
    
    def aplicar_finisher(self, atacante, alvo, finisher_data: Dict) -> Dict[str, Any]:
        """
        Aplica o efeito do finisher no alvo.
        Retorna dados para VFX.
        """
        resultado = {"tipo": "finisher", "finisher": finisher_data.get("nome", "?")}
        
        # Launch: joga no ar
        if "vel_z" in finisher_data:
            alvo.vel_z = finisher_data["vel_z"]
            alvo.stun_timer = max(alvo.stun_timer, finisher_data.get("stun", 0.5))
            resultado["launch"] = True
        
        # Wallbounce: empurrão forte
        if "knockback_mult" in finisher_data:
            dx = alvo.pos[0] - atacante.pos[0]
            dy = alvo.pos[1] - atacante.pos[1]
            dist = math.hypot(dx, dy)
            if dist > 0.01:
                nx, ny = dx / dist, dy / dist
                force = 20.0 * finisher_data["knockback_mult"]
                alvo.vel[0] += nx * force
                alvo.vel[1] += ny * force
            alvo.stun_timer = max(alvo.stun_timer, finisher_data.get("stun", 0.5))
            resultado["wallbounce"] = True
        
        # Ground slam: dano em área
        if "area_raio" in finisher_data:
            resultado["area_dano"] = {
                "x": alvo.pos[0], "y": alvo.pos[1],
                "raio": finisher_data["area_raio"],
                "dano_mult": finisher_data.get("dano_mult", 1.5),
            }
            alvo.stun_timer = max(alvo.stun_timer, finisher_data.get("stun", 0.3))
            resultado["ground_slam"] = True
        
        return resultado
    
    def tentar_combo_breaker(self, lutador) -> bool:
        """
        Tenta quebrar o combo que está sofrendo (custa estamina).
        Retorna True se conseguiu.
        """
        lid = id(lutador)
        
        # Cooldown de combo breaker
        if self._combo_breaker_cooldowns.get(lid, 0) > 0:
            return False
        
        custo_estamina = 30.0
        if lutador.estamina < custo_estamina:
            return False
        
        # Verifica se está realmente em combo (algum atacante tem combo contra este lutador)
        em_combo = False
        for tracker in self._trackers.values():
            if id(lutador) in tracker.alvos_no_combo and tracker.combo_count >= 2:
                tracker.combo_count = 0
                tracker.dano_total_combo = 0
                tracker.alvos_no_combo.discard(id(lutador))
                em_combo = True
        
        if not em_combo:
            return False
        
        lutador.estamina -= custo_estamina
        self._combo_breaker_cooldowns[lid] = 5.0  # 5s cooldown
        
        # Empurrão de escape
        lutador.invencivel_timer = max(lutador.invencivel_timer, 0.5)
        
        return True
    
    def update(self, dt: float):
        """Atualiza todos os trackers"""
        self._tempo_luta += dt
        
        for tracker in self._trackers.values():
            tracker.update(dt)
        
        # Cooldowns de combo breaker
        for lid in list(self._combo_breaker_cooldowns.keys()):
            self._combo_breaker_cooldowns[lid] -= dt
            if self._combo_breaker_cooldowns[lid] <= 0:
                del self._combo_breaker_cooldowns[lid]
    
    def get_combo_display(self, lutador) -> Optional[Dict]:
        """Retorna dados de combo para display"""
        tracker = self._trackers.get(id(lutador))
        if not tracker:
            return None
        return tracker.get_combo_display()
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de combos da luta"""
        stats = {}
        for lid, tracker in self._trackers.items():
            nome = getattr(tracker.lutador, 'dados', None)
            nome_str = getattr(nome, 'nome', '?') if nome else '?'
            stats[nome_str] = {
                "melhor_combo": tracker.melhor_combo,
                "combo_atual": tracker.combo_count,
                "dano_combo_atual": tracker.dano_total_combo,
            }
        return stats
