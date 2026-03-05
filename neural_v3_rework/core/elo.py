"""
NEURAL FIGHTS — Sistema de ELO / Ranking v1.0
===============================================
Rating persistente que sobrevive entre torneios e lutas.
Usa sistema ELO com K-factor adaptativo.
Salva em data/elo_rankings.json.
"""

import json
import os
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime


_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_HERE), "data")
_ELO_PATH = os.path.join(_DATA, "elo_rankings.json")


class EloSystem:
    """
    Sistema de rating ELO para personagens.
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
        # Config
        self.elo_inicial = 1000
        self.k_factor_base = 32
        self.k_factor_novato = 40   # K mais alto para novatos (ajuste rápido)
        self.k_factor_veterano = 24  # K mais baixo para veteranos (estabilidade)
        self.partidas_novato = 10
        self.partidas_veterano = 30
        self.bonus_ko_rapido = 5
        self.bonus_ko_threshold = 15.0  # segundos
        
        # Dados
        self.rankings: Dict[str, Dict] = {}
        self._carregar()
    
    def _carregar(self):
        """Carrega rankings do disco"""
        if os.path.exists(_ELO_PATH):
            try:
                with open(_ELO_PATH, "r", encoding="utf-8") as f:
                    self.rankings = json.load(f)
            except Exception as e:
                print(f"[ELO] Erro ao carregar rankings: {e}")
                self.rankings = {}
    
    def _salvar(self):
        """Salva rankings no disco"""
        try:
            os.makedirs(_DATA, exist_ok=True)
            tmp = _ELO_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.rankings, f, indent=2, ensure_ascii=False)
            os.replace(tmp, _ELO_PATH)
        except Exception as e:
            print(f"[ELO] Erro ao salvar rankings: {e}")
    
    def _get_ou_criar(self, nome: str) -> Dict:
        """Obtém ou cria entrada para um personagem"""
        if nome not in self.rankings:
            self.rankings[nome] = {
                "elo": self.elo_inicial,
                "partidas": 0,
                "vitorias": 0,
                "derrotas": 0,
                "ko_count": 0,
                "melhor_elo": self.elo_inicial,
                "pior_elo": self.elo_inicial,
                "streak_atual": 0,  # Positivo = wins, negativo = losses
                "melhor_streak": 0,
                "historico": [],  # Últimas 20 partidas
                "ultima_atualizacao": datetime.now().isoformat(),
            }
        return self.rankings[nome]
    
    def _get_k_factor(self, jogador: Dict) -> float:
        """Calcula K-factor adaptativo"""
        partidas = jogador["partidas"]
        if partidas < self.partidas_novato:
            return self.k_factor_novato
        elif partidas < self.partidas_veterano:
            # Interpolação linear
            t = (partidas - self.partidas_novato) / (self.partidas_veterano - self.partidas_novato)
            return self.k_factor_novato + (self.k_factor_veterano - self.k_factor_novato) * t
        return self.k_factor_veterano
    
    def _probabilidade_esperada(self, elo_a: float, elo_b: float) -> float:
        """Calcula probabilidade esperada de A vencer B"""
        return 1.0 / (1.0 + math.pow(10, (elo_b - elo_a) / 400.0))
    
    def registrar_resultado(self, vencedor: str, perdedor: str, 
                           duracao: float = 0.0, ko_type: str = "KO") -> Dict:
        """
        Registra resultado de uma luta e atualiza ELO.
        
        Returns:
            Dict com: elo_vencedor, elo_perdedor, delta_vencedor, delta_perdedor
        """
        v_data = self._get_ou_criar(vencedor)
        p_data = self._get_ou_criar(perdedor)
        
        elo_v_antes = v_data["elo"]
        elo_p_antes = p_data["elo"]
        
        # Probabilidades esperadas
        prob_v = self._probabilidade_esperada(elo_v_antes, elo_p_antes)
        prob_p = 1.0 - prob_v
        
        # K-factors
        k_v = self._get_k_factor(v_data)
        k_p = self._get_k_factor(p_data)
        
        # Deltas base
        delta_v = k_v * (1.0 - prob_v)
        delta_p = k_p * (0.0 - prob_p)
        
        # Bônus por KO rápido
        if duracao > 0 and duracao < self.bonus_ko_threshold:
            delta_v += self.bonus_ko_rapido
        
        # Aplica
        v_data["elo"] = round(elo_v_antes + delta_v)
        p_data["elo"] = round(max(100, elo_p_antes + delta_p))  # Mínimo 100
        
        # Atualiza stats do vencedor
        v_data["partidas"] += 1
        v_data["vitorias"] += 1
        v_data["melhor_elo"] = max(v_data["melhor_elo"], v_data["elo"])
        if "KO" in ko_type.upper():
            v_data["ko_count"] += 1
        v_data["streak_atual"] = max(1, v_data["streak_atual"] + 1) if v_data["streak_atual"] >= 0 else 1
        v_data["melhor_streak"] = max(v_data["melhor_streak"], v_data["streak_atual"])
        v_data["historico"].append({
            "oponente": perdedor, "resultado": "V", 
            "delta": round(delta_v), "data": datetime.now().isoformat()[:10]
        })
        if len(v_data["historico"]) > 20:
            v_data["historico"] = v_data["historico"][-20:]
        v_data["ultima_atualizacao"] = datetime.now().isoformat()
        
        # Atualiza stats do perdedor
        p_data["partidas"] += 1
        p_data["derrotas"] += 1
        p_data["pior_elo"] = min(p_data["pior_elo"], p_data["elo"])
        p_data["streak_atual"] = min(-1, p_data["streak_atual"] - 1) if p_data["streak_atual"] <= 0 else -1
        p_data["historico"].append({
            "oponente": vencedor, "resultado": "D",
            "delta": round(delta_p), "data": datetime.now().isoformat()[:10]
        })
        if len(p_data["historico"]) > 20:
            p_data["historico"] = p_data["historico"][-20:]
        p_data["ultima_atualizacao"] = datetime.now().isoformat()
        
        self._salvar()
        
        return {
            "elo_vencedor": v_data["elo"],
            "elo_perdedor": p_data["elo"],
            "delta_vencedor": round(delta_v),
            "delta_perdedor": round(delta_p),
            "elo_v_antes": elo_v_antes,
            "elo_p_antes": elo_p_antes,
        }
    
    def get_ranking(self, top_n: int = 50) -> List[Dict]:
        """Retorna ranking ordenado por ELO"""
        ranking = []
        for nome, data in self.rankings.items():
            ranking.append({
                "nome": nome,
                "elo": data["elo"],
                "partidas": data["partidas"],
                "vitorias": data["vitorias"],
                "derrotas": data["derrotas"],
                "winrate": round(data["vitorias"] / max(data["partidas"], 1) * 100, 1),
                "streak": data["streak_atual"],
                "melhor_streak": data["melhor_streak"],
                "ko_count": data.get("ko_count", 0),
            })
        
        ranking.sort(key=lambda x: x["elo"], reverse=True)
        return ranking[:top_n]
    
    def get_elo(self, nome: str) -> int:
        """Retorna ELO de um personagem"""
        data = self.rankings.get(nome)
        return data["elo"] if data else self.elo_inicial
    
    def get_player_stats(self, nome: str) -> Optional[Dict]:
        """Retorna stats completos de um personagem"""
        return self.rankings.get(nome)
    
    def get_tier(self, elo: int) -> str:
        """Retorna o tier/rank baseado no ELO"""
        if elo >= 1800: return "Lendário"
        elif elo >= 1600: return "Mestre"
        elif elo >= 1400: return "Diamante"
        elif elo >= 1200: return "Ouro"
        elif elo >= 1000: return "Prata"
        elif elo >= 800: return "Bronze"
        return "Ferro"
    
    def get_tier_cor(self, elo: int) -> Tuple[int, int, int]:
        """Retorna cor do tier"""
        tier = self.get_tier(elo)
        return {
            "Lendário": (255, 215, 0),
            "Mestre": (200, 50, 200),
            "Diamante": (100, 200, 255),
            "Ouro": (255, 200, 50),
            "Prata": (180, 180, 200),
            "Bronze": (180, 120, 60),
            "Ferro": (100, 100, 100),
        }.get(tier, (200, 200, 200))
    
    def seed_tournament(self, participantes: List[str]) -> List[str]:
        """Ordena participantes por ELO para seeding de torneio"""
        return sorted(participantes, key=lambda n: self.get_elo(n), reverse=True)
    
    def matchmaking(self, candidatos: List[str], alvo: str, top_n: int = 5) -> List[str]:
        """Encontra os N melhores oponentes por ELO similar"""
        elo_alvo = self.get_elo(alvo)
        outros = [n for n in candidatos if n != alvo]
        outros.sort(key=lambda n: abs(self.get_elo(n) - elo_alvo))
        return outros[:top_n]
