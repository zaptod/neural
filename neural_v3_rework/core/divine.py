"""
NEURAL FIGHTS — Sistema Divino v1.0
====================================
Bênçãos dos deuses que afetam combate.
Cada deus concede uma passiva e uma bênção ativa (1x por luta).
Integra com god_id dos personagens e com gods.json.
"""

import math
import random
from typing import Optional, Dict, Any


# ============================================================================
# DADOS DOS DEUSES — Passivas e Bênçãos Ativas
# ============================================================================

DEUSES = {
    # === OS NOVE DEUSES DE AETHERMOOR ===
    
    "god_balance": {
        "name": "Libra, Deusa do Equilíbrio",
        "nature": "Balance",
        "color": (180, 160, 255),
        "passiva": {
            "nome": "Equilíbrio Divino",
            "descricao": "Quando HP cai abaixo de 50%, regen de mana +50%. Quando mana < 30%, dano +10%.",
            "tipo": "adaptive"
        },
        "bencao": {
            "nome": "Balança Cósmica",
            "descricao": "Iguala HP de ambos os lutadores à média dos dois por 5s.",
            "tipo": "equalize",
            "duracao": 5.0
        }
    },
    
    "god_fear": {
        "name": "Phobos, Deus do Medo",
        "nature": "Fear",
        "color": (80, 0, 0),
        "passiva": {
            "nome": "Aura de Terror",
            "descricao": "Inimigos abaixo de 30% HP causam -15% de dano contra este lutador.",
            "tipo": "fear_aura"
        },
        "bencao": {
            "nome": "Grito do Pavor",
            "descricao": "Aplica MEDO em todos os inimigos por 3s + stun 1s.",
            "tipo": "mass_fear",
            "duracao": 3.0,
            "stun": 1.0
        }
    },
    
    "god_greed": {
        "name": "Mammon, Deus da Ganância",
        "nature": "Greed",
        "color": (255, 200, 0),
        "passiva": {
            "nome": "Ouro Sangrento",
            "descricao": "Recupera 3% da vida ao matar ou ao aplicar status effect.",
            "tipo": "lifesteal_on_status"
        },
        "bencao": {
            "nome": "Toque de Midas",
            "descricao": "Próximos 3 ataques causam +50% de dano e aplicam MARCADO.",
            "tipo": "empower_attacks",
            "ataques": 3,
            "dano_bonus": 0.5
        }
    },
    
    "god_war": {
        "name": "Ares, Deus da Guerra",
        "nature": "War",
        "color": (200, 30, 30),
        "passiva": {
            "nome": "Sede de Sangue",
            "descricao": "+5% dano por cada 10% de vida perdida (máx +25% a 50% HP).",
            "tipo": "blood_rage"
        },
        "bencao": {
            "nome": "Fúria Marcial",
            "descricao": "Por 6s: +30% dano, +20% velocidade de ataque, imune a stun.",
            "tipo": "war_frenzy",
            "duracao": 6.0,
            "dano_bonus": 0.3,
            "vel_bonus": 0.2
        }
    },
    
    "god_wisdom": {
        "name": "Athena, Deusa da Sabedoria",
        "nature": "Wisdom",
        "color": (100, 180, 255),
        "passiva": {
            "nome": "Mente Tática",
            "descricao": "Cooldown de skills reduzido em 15%. Esquiva +10% quando com mana cheia.",
            "tipo": "tactical_mind"
        },
        "bencao": {
            "nome": "Prelúdio Perfeito",
            "descricao": "Por 5s: todas as skills sem cooldown e custo de mana reduzido 50%.",
            "tipo": "perfect_cast",
            "duracao": 5.0,
            "cd_reducao": 1.0,
            "mana_reducao": 0.5
        }
    },
    
    "god_nature": {
        "name": "Gaia, Deusa da Natureza",
        "nature": "Nature",
        "color": (50, 180, 50),
        "passiva": {
            "nome": "Regeneração Natural",
            "descricao": "Regenera 0.8% HP/s. Venenos duram 50% menos neste lutador.",
            "tipo": "natural_regen"
        },
        "bencao": {
            "nome": "Abraço de Gaia",
            "descricao": "Cura 35% do HP máximo + remove todos os debuffs. Enraíza inimigos 2s.",
            "tipo": "full_restore",
            "cura_pct": 0.35,
            "enraizar_duracao": 2.0
        }
    },
    
    "god_death": {
        "name": "Thanatos, Deus da Morte",
        "nature": "Death",
        "color": (40, 0, 60),
        "passiva": {
            "nome": "Marca da Morte",
            "descricao": "Ataques contra inimigos abaixo de 20% HP causam +40% dano.",
            "tipo": "execute_bonus"
        },
        "bencao": {
            "nome": "Ceifar",
            "descricao": "Se inimigo está abaixo de 25% HP, causa 999 dano (execução). Senão, causa 30% do HP atual.",
            "tipo": "reap",
            "execute_threshold": 0.25,
            "dano_nao_execute_pct": 0.30
        }
    },
    
    "god_chaos": {
        "name": "Eris, Deusa do Caos",
        "nature": "Chaos",
        "color": (200, 50, 200),
        "passiva": {
            "nome": "Entropia",
            "descricao": "10% de chance que qualquer ataque cause um efeito elemental aleatório.",
            "tipo": "random_element"
        },
        "bencao": {
            "nome": "Loucura Cósmica",
            "descricao": "Por 4s: cada ataque tem elemento aleatório, velocidade +40%, mas perde 2% HP/s.",
            "tipo": "chaos_mode",
            "duracao": 4.0,
            "vel_bonus": 0.4,
            "hp_drain_pct": 0.02
        }
    },
    
    "god_time": {
        "name": "Chronos, Deus do Tempo",
        "nature": "Time",
        "color": (200, 180, 255),
        "passiva": {
            "nome": "Dilatação Temporal",
            "descricao": "A cada 10s de luta, ganha 1s de slow-mo pessoal (move +30%, inimigos parecem -20%).",
            "tipo": "time_dilation"
        },
        "bencao": {
            "nome": "Parar o Tempo",
            "descricao": "Congela todos os inimigos por 2.5s. O abençoado se move normalmente.",
            "tipo": "time_stop",
            "duracao": 2.5
        }
    },
}


class DivineBlessingManager:
    """
    Gerencia bênçãos divinas durante o combate.
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
        # {lutador_id: dados da bênção}
        self._blessings_used = set()  # IDs de lutadores que já usaram bênção
        self._blessing_active = {}     # {lutador_id: {tipo, timer, dados...}}
        self._passive_cache = {}       # {lutador_id: god_data}
        self._time_dilation_timers = {}  # Para Chronos
    
    def registrar_lutador(self, lutador):
        """Registra um lutador e seu deus patrono"""
        god_id = getattr(lutador.dados, 'god_id', None)
        if god_id and god_id in DEUSES:
            lid = id(lutador)
            self._passive_cache[lid] = DEUSES[god_id]
            self._time_dilation_timers[lid] = 0.0
    
    def get_god_data(self, lutador) -> Optional[Dict]:
        """Retorna dados do deus do lutador"""
        return self._passive_cache.get(id(lutador))
    
    def pode_usar_bencao(self, lutador) -> bool:
        """Verifica se o lutador pode usar sua bênção divina"""
        lid = id(lutador)
        god_data = self._passive_cache.get(lid)
        if not god_data:
            return False
        return lid not in self._blessings_used and lid not in self._blessing_active
    
    def usar_bencao(self, lutador, todos_lutadores=None) -> Dict[str, Any]:
        """
        Ativa a bênção divina do lutador. Retorna dict com resultados para VFX.
        Cada lutador só pode usar 1x por luta.
        """
        lid = id(lutador)
        god_data = self._passive_cache.get(lid)
        if not god_data or lid in self._blessings_used:
            return {"sucesso": False}
        
        bencao = god_data["bencao"]
        tipo = bencao["tipo"]
        resultado = {"sucesso": True, "nome": bencao["nome"], "tipo": tipo, 
                      "cor": god_data["color"], "descricao": bencao["descricao"]}
        
        self._blessings_used.add(lid)
        
        inimigos = []
        if todos_lutadores:
            inimigos = [f for f in todos_lutadores 
                       if f is not lutador and not f.morto and f.team_id != lutador.team_id]
        
        # === IMPLEMENTAÇÃO DE CADA BÊNÇÃO ===
        
        if tipo == "equalize":
            # Libra: iguala HP
            if inimigos:
                alvo = inimigos[0]
                media = (lutador.vida + alvo.vida) / 2
                lutador.vida = min(lutador.vida_max, media)
                alvo.vida = min(alvo.vida_max, media)
                resultado["hp_equalizado"] = media
        
        elif tipo == "mass_fear":
            # Phobos: medo em todos
            for inimigo in inimigos:
                inimigo._aplicar_efeito_status("MEDO", duracao=bencao["duracao"])
                inimigo.stun_timer = max(inimigo.stun_timer, bencao.get("stun", 0.5))
            resultado["alvos_afetados"] = len(inimigos)
        
        elif tipo == "empower_attacks":
            # Mammon: empoderar ataques
            self._blessing_active[lid] = {
                "tipo": "empower",
                "ataques_restantes": bencao["ataques"],
                "dano_bonus": bencao["dano_bonus"]
            }
            resultado["ataques"] = bencao["ataques"]
        
        elif tipo == "war_frenzy":
            # Ares: fúria marcial
            self._blessing_active[lid] = {
                "tipo": "war_frenzy",
                "timer": bencao["duracao"],
                "dano_bonus": bencao["dano_bonus"],
                "vel_bonus": bencao["vel_bonus"]
            }
            lutador.invencivel_timer = max(lutador.invencivel_timer, 0.5)  # Brief invuln
            resultado["duracao"] = bencao["duracao"]
        
        elif tipo == "perfect_cast":
            # Athena: conjuração perfeita
            self._blessing_active[lid] = {
                "tipo": "perfect_cast",
                "timer": bencao["duracao"],
            }
            # Reseta todos os cooldowns
            for skill_nome in lutador.cd_skills:
                lutador.cd_skills[skill_nome] = 0
            resultado["duracao"] = bencao["duracao"]
        
        elif tipo == "full_restore":
            # Gaia: cura massiva
            cura = lutador.vida_max * bencao["cura_pct"]
            lutador.vida = min(lutador.vida_max, lutador.vida + cura)
            # Remove debuffs
            lutador.slow_timer = 0; lutador.slow_fator = 1.0
            lutador.stun_timer = 0; lutador.silenciado_timer = 0
            lutador.cego_timer = 0; lutador.medo_timer = 0
            lutador.dots_ativos.clear()
            lutador.congelado = False; lutador.dormindo = False
            # Enraíza inimigos
            for inimigo in inimigos:
                inimigo._aplicar_efeito_status("ENRAIZADO", duracao=bencao["enraizar_duracao"])
            resultado["cura"] = cura
        
        elif tipo == "reap":
            # Thanatos: ceifar
            if inimigos:
                alvo = min(inimigos, key=lambda f: f.vida / max(f.vida_max, 1))
                hp_pct = alvo.vida / max(alvo.vida_max, 1)
                if hp_pct < bencao["execute_threshold"]:
                    alvo.vida = 0
                    alvo.morrer()
                    resultado["execute"] = True
                else:
                    dano = alvo.vida * bencao["dano_nao_execute_pct"]
                    alvo.vida -= dano
                    resultado["dano"] = dano
        
        elif tipo == "chaos_mode":
            # Eris: caos
            self._blessing_active[lid] = {
                "tipo": "chaos_mode",
                "timer": bencao["duracao"],
                "vel_bonus": bencao["vel_bonus"],
                "hp_drain_pct": bencao["hp_drain_pct"]
            }
            resultado["duracao"] = bencao["duracao"]
        
        elif tipo == "time_stop":
            # Chronos: parar o tempo
            for inimigo in inimigos:
                inimigo._aplicar_efeito_status("TEMPO_PARADO", duracao=bencao["duracao"])
            resultado["duracao"] = bencao["duracao"]
        
        return resultado
    
    def aplicar_passiva_dano(self, lutador, dano: float, alvo=None) -> float:
        """
        Modifica dano baseado nas passivas divinas do ATACANTE.
        Chamado em calcular_dano_ataque().
        """
        lid = id(lutador)
        god_data = self._passive_cache.get(lid)
        if not god_data:
            return dano
        
        passiva = god_data["passiva"]
        tipo = passiva["tipo"]
        
        # Ares: +5% dano por cada 10% de vida perdida
        if tipo == "blood_rage":
            hp_perdido = 1.0 - (lutador.vida / max(lutador.vida_max, 1))
            bonus = min(0.25, hp_perdido * 0.5)  # Cap +25%
            dano *= (1.0 + bonus)
        
        # Thanatos: +40% contra inimigos < 20% HP
        elif tipo == "execute_bonus":
            if alvo and alvo.vida / max(alvo.vida_max, 1) < 0.2:
                dano *= 1.40
        
        # Eris: 10% chance de elemento aleatório (dano inalterado aqui, efeito aplicado em apply_hit)
        # Handled in aplicar_passiva_on_hit
        
        # Mammon empowered attacks
        blessing = self._blessing_active.get(lid)
        if blessing and blessing.get("tipo") == "empower":
            dano *= (1.0 + blessing["dano_bonus"])
            blessing["ataques_restantes"] -= 1
            if blessing["ataques_restantes"] <= 0:
                del self._blessing_active[lid]
        
        # Ares war frenzy bonus
        if blessing and blessing.get("tipo") == "war_frenzy":
            dano *= (1.0 + blessing["dano_bonus"])
        
        return dano
    
    def aplicar_passiva_defesa(self, lutador, dano: float, atacante) -> float:
        """
        Modifica dano recebido baseado nas passivas divinas do DEFENSOR.
        Chamado em tomar_dano().
        """
        lid = id(lutador)
        god_data = self._passive_cache.get(lid)
        if not god_data:
            return dano
        
        passiva = god_data["passiva"]
        tipo = passiva["tipo"]
        
        # Phobos: inimigos com < 30% HP causam -15% dano
        if tipo == "fear_aura":
            if atacante and atacante.vida / max(atacante.vida_max, 1) < 0.3:
                dano *= 0.85
        
        # Libra: adaptativo (não reduz dano diretamente)
        
        return dano
    
    def aplicar_passiva_on_hit(self, lutador, alvo, dano_causado: float) -> Dict[str, Any]:
        """
        Aplica efeitos pós-hit baseados nas passivas divinas.
        Retorna dict com efeitos para VFX.
        """
        lid = id(lutador)
        god_data = self._passive_cache.get(lid)
        resultado = {}
        if not god_data:
            return resultado
        
        passiva = god_data["passiva"]
        tipo = passiva["tipo"]
        
        # Mammon: cura ao aplicar status
        if tipo == "lifesteal_on_status":
            if alvo.dots_ativos or alvo.stun_timer > 0 or alvo.slow_timer > 0:
                cura = lutador.vida_max * 0.03
                lutador.vida = min(lutador.vida_max, lutador.vida + cura)
                resultado["lifesteal"] = cura
        
        # Eris: 10% chance de elemento aleatório
        if tipo == "random_element":
            if random.random() < 0.10:
                from core.combat import DotEffect
                elemento = random.choice(["QUEIMANDO", "ENVENENADO", "LENTO", "PARALISIA"])
                alvo._aplicar_efeito_status(elemento, duracao=2.0)
                resultado["random_element"] = elemento
        
        return resultado
    
    def update(self, dt: float, todos_lutadores: list):
        """Atualiza timers de bênçãos ativas e passivas temporais"""
        for lid in list(self._blessing_active.keys()):
            blessing = self._blessing_active[lid]
            
            if "timer" in blessing:
                blessing["timer"] -= dt
                if blessing["timer"] <= 0:
                    del self._blessing_active[lid]
                    continue
            
            # Caos: drena HP
            if blessing.get("tipo") == "chaos_mode":
                lutador = self._find_lutador(lid, todos_lutadores)
                if lutador:
                    drain = lutador.vida_max * blessing["hp_drain_pct"] * dt
                    lutador.vida = max(1, lutador.vida - drain)
        
        # Passivas temporais
        for lutador in todos_lutadores:
            if lutador.morto:
                continue
            lid = id(lutador)
            god_data = self._passive_cache.get(lid)
            if not god_data:
                continue
            
            passiva = god_data["passiva"]
            
            # Gaia: regen natural
            if passiva["tipo"] == "natural_regen":
                regen = lutador.vida_max * 0.008 * dt
                if getattr(lutador, 'cura_bloqueada', 0) <= 0:
                    lutador.vida = min(lutador.vida_max, lutador.vida + regen)
            
            # Libra: adaptive
            elif passiva["tipo"] == "adaptive":
                hp_pct = lutador.vida / max(lutador.vida_max, 1)
                mana_pct = lutador.mana / max(lutador.mana_max, 1)
                if hp_pct < 0.5:
                    # Mana regen +50% (aplicado via multiplicador temporário)
                    lutador.mana = min(lutador.mana_max, 
                                       lutador.mana + lutador.regen_mana_base * 0.5 * dt)
            
            # Athena: CD reduction (permanente)
            elif passiva["tipo"] == "tactical_mind":
                # Aplicado em calcular_dano_ataque e cd reduction é feito no hook de skill
                pass
            
            # Chronos: time dilation counter
            elif passiva["tipo"] == "time_dilation":
                self._time_dilation_timers[lid] = self._time_dilation_timers.get(lid, 0) + dt
                if self._time_dilation_timers[lid] >= 10.0:
                    self._time_dilation_timers[lid] -= 10.0
                    # Concede 1s de boost de velocidade
                    lutador.slow_fator = max(lutador.slow_fator, 1.0)
                    # Bonus armazenado como buff temporário via mod_velocidade
                    if not hasattr(lutador, '_chronos_boost'):
                        lutador._chronos_boost = 0
                    lutador._chronos_boost = 1.0  # Timer de 1s
            
            # Decrementa boost do Chronos
            if hasattr(lutador, '_chronos_boost') and lutador._chronos_boost > 0:
                lutador._chronos_boost -= dt
    
    def get_mod_cooldown(self, lutador) -> float:
        """Retorna multiplicador de cooldown (< 1.0 = mais rápido)"""
        lid = id(lutador)
        
        # Athena passiva: -15% CD
        god_data = self._passive_cache.get(lid)
        if god_data and god_data["passiva"]["tipo"] == "tactical_mind":
            mult = 0.85
        else:
            mult = 1.0
        
        # Athena bênção ativa: CD zerado
        blessing = self._blessing_active.get(lid)
        if blessing and blessing.get("tipo") == "perfect_cast":
            mult = 0.0
        
        return mult
    
    def get_mod_velocidade(self, lutador) -> float:
        """Retorna multiplicador de velocidade de bênçãos ativas"""
        lid = id(lutador)
        blessing = self._blessing_active.get(lid)
        if not blessing:
            # Chronos boost
            if hasattr(lutador, '_chronos_boost') and lutador._chronos_boost > 0:
                return 1.3
            return 1.0
        
        if blessing.get("tipo") == "war_frenzy":
            return 1.0 + blessing.get("vel_bonus", 0)
        elif blessing.get("tipo") == "chaos_mode":
            return 1.0 + blessing.get("vel_bonus", 0)
        return 1.0
    
    def get_mod_custo_mana(self, lutador) -> float:
        """Retorna multiplicador de custo de mana"""
        lid = id(lutador)
        blessing = self._blessing_active.get(lid)
        if blessing and blessing.get("tipo") == "perfect_cast":
            return 0.5
        return 1.0
    
    def is_stun_immune(self, lutador) -> bool:
        """Verifica se lutador é imune a stun (Ares frenzy)"""
        lid = id(lutador)
        blessing = self._blessing_active.get(lid)
        if blessing and blessing.get("tipo") == "war_frenzy":
            return True
        return False
    
    def get_poison_reduction(self, lutador) -> float:
        """Retorna fator de redução de veneno (Gaia)"""
        lid = id(lutador)
        god_data = self._passive_cache.get(lid)
        if god_data and god_data["passiva"]["tipo"] == "natural_regen":
            return 0.5  # Venenos duram 50% menos
        return 1.0
    
    def _find_lutador(self, lid: int, todos_lutadores: list):
        """Encontra lutador pelo id()"""
        for f in todos_lutadores:
            if id(f) == lid:
                return f
        return None
    
    def has_active_blessing(self, lutador) -> bool:
        """Verifica se há bênção ativa"""
        return id(lutador) in self._blessing_active
    
    def get_blessing_info(self, lutador) -> Optional[Dict]:
        """Retorna info da bênção ativa para renderização"""
        lid = id(lutador)
        if lid not in self._blessing_active:
            god_data = self._passive_cache.get(lid)
            if god_data:
                return {"passiva": god_data["passiva"]["nome"], "cor": god_data["color"]}
            return None
        blessing = self._blessing_active[lid]
        god_data = self._passive_cache.get(lid)
        cor = god_data["color"] if god_data else (255, 255, 255)
        return {"ativa": True, "tipo": blessing["tipo"], "cor": cor,
                "timer": blessing.get("timer", 0)}
