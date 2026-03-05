"""
NEURAL FIGHTS — Modo Horda / Sobrevivência v1.0
=================================================
Um lutador (ou equipe) enfrenta waves de inimigos
com dificuldade crescente. Cura parcial entre waves.
"""

import random
import math
from typing import Dict, List, Optional, Tuple


class HordeWave:
    """Representa uma wave de inimigos."""
    
    def __init__(self, numero: int, inimigos: List[Dict], boss: bool = False):
        self.numero = numero
        self.inimigos = inimigos  # [{"nome": ..., "classe": ..., "level": ...}]
        self.boss = boss
        self.concluida = False
        self.tempo_inicio = 0.0
        self.tempo_fim = 0.0


class HordeConfig:
    """Configuração do modo horda."""
    
    def __init__(self):
        # Escalamento por wave
        self.hp_mult_por_wave = 0.08     # +8% HP por wave
        self.dano_mult_por_wave = 0.05   # +5% dano por wave
        self.vel_mult_por_wave = 0.02    # +2% velocidade por wave
        self.inimigos_base = 1           # 1 inimigo na primeira wave
        self.inimigos_max = 4            # Até 4 por wave
        self.wave_para_add_inimigo = 3   # A cada 3 waves: +1 inimigo
        self.boss_a_cada = 5             # Boss a cada 5 waves
        
        # Cura entre waves
        self.cura_entre_waves = 0.30     # 30% HP recuperado
        self.mana_entre_waves = 0.50     # 50% mana recuperado
        self.tempo_descanso = 5.0        # 5s entre waves
        
        # Classes inimigas (progresso)
        self.classes_iniciais = [
            "Guerreiro (Força Bruta)",
            "Ladino (Reflexos Rápidos)",
        ]
        self.classes_intermediarias = [
            "Espadachim (Duelista)",
            "Cavaleiro (Tanque Blindado)",
            "Bárbaro (Fúria Primal)",
            "Ranger (Predador)",
        ]
        self.classes_avancadas = [
            "Mago (Elementalista)",
            "Assassino (Sombras)",
            "Paladino (Arauto da Luz)",
            "Feiticeiro (Caos)",
        ]
        self.classes_boss = [
            "Colosso (Titã Ancestral)",
            "Necromante (Pacto Sombrio)",
            "Berserker (Instinto Selvagem)",
        ]
        
        # Armas base para inimigos
        self.tipos_arma = ["Reta", "Dupla", "Arco", "Arremesso", "Corrente", "Mágica"]


class HordeState:
    """Estado do modo horda durante execução."""
    
    def __init__(self, config: Optional[HordeConfig] = None):
        self.config = config or HordeConfig()
        self.wave_atual = 0
        self.waves_completas = 0
        self.inimigos_derrotados = 0
        self.dano_total_dado = 0.0
        self.dano_total_recebido = 0.0
        self.tempo_total = 0.0
        self.fase = "preparando"  # "preparando", "combate", "descanso", "derrota", "boss"
        self.timer_descanso = 0.0
        self.melhor_wave = 0
        self.kills_por_wave: List[int] = []
    
    def gerar_wave(self) -> HordeWave:
        """Gera próxima wave de inimigos."""
        self.wave_atual += 1
        cfg = self.config
        
        # Determina se é boss wave
        is_boss = self.wave_atual % cfg.boss_a_cada == 0
        
        # Quantidade de inimigos
        n_inimigos = min(
            cfg.inimigos_max,
            cfg.inimigos_base + (self.wave_atual - 1) // cfg.wave_para_add_inimigo
        )
        if is_boss:
            n_inimigos = 1  # Boss vem sozinho
        
        # Seleciona classes baseado na progressão
        if is_boss:
            pool = cfg.classes_boss
        elif self.wave_atual <= 3:
            pool = cfg.classes_iniciais
        elif self.wave_atual <= 8:
            pool = cfg.classes_iniciais + cfg.classes_intermediarias
        elif self.wave_atual <= 15:
            pool = cfg.classes_intermediarias + cfg.classes_avancadas
        else:
            pool = cfg.classes_avancadas + cfg.classes_boss
        
        # Gera inimigos
        inimigos = []
        for i in range(n_inimigos):
            classe = random.choice(pool)
            tipo_arma = random.choice(cfg.tipos_arma)
            
            # Level baseado na wave
            level = self.wave_atual
            if is_boss:
                level = int(self.wave_atual * 1.5)
            
            # Multiplexadores
            hp_mult = 1.0 + (self.wave_atual - 1) * cfg.hp_mult_por_wave
            dano_mult = 1.0 + (self.wave_atual - 1) * cfg.dano_mult_por_wave
            vel_mult = 1.0 + min((self.wave_atual - 1) * cfg.vel_mult_por_wave, 0.5)
            
            if is_boss:
                hp_mult *= 2.5
                dano_mult *= 1.5
            
            inimigos.append({
                "classe": classe,
                "tipo_arma": tipo_arma,
                "level": level,
                "hp_mult": hp_mult,
                "dano_mult": dano_mult,
                "vel_mult": vel_mult,
                "boss": is_boss,
                "nome": f"Horda-W{self.wave_atual}-{i+1}",
            })
        
        return HordeWave(self.wave_atual, inimigos, boss=is_boss)
    
    def aplicar_cura_entre_waves(self, jogador) -> Dict:
        """Aplica cura entre waves. Retorna {hp_curado, mana_curada}"""
        cfg = self.config
        
        hp_antes = jogador.vida
        mana_antes = jogador.mana
        
        cura_hp = jogador.vida_max * cfg.cura_entre_waves
        cura_mana = jogador.mana_max * cfg.mana_entre_waves
        
        jogador.vida = min(jogador.vida_max, jogador.vida + cura_hp)
        jogador.mana = min(jogador.mana_max, jogador.mana + cura_mana)
        
        # Limpa debuffs
        jogador.stun_timer = 0
        jogador.slow_timer = 0
        jogador.slow_fator = 1.0
        jogador.dots_ativos.clear()
        jogador.congelado = False
        jogador.dormindo = False
        jogador.dano_reduzido = 1.0
        jogador.vulnerabilidade = 1.0
        
        return {
            "hp_curado": jogador.vida - hp_antes,
            "mana_curada": jogador.mana - mana_antes,
        }
    
    def registrar_kill(self):
        """Registra um kill na wave atual."""
        self.inimigos_derrotados += 1
    
    def wave_concluida(self):
        """Marca wave como concluída."""
        self.waves_completas += 1
        self.melhor_wave = max(self.melhor_wave, self.wave_atual)
        self.fase = "descanso"
        self.timer_descanso = self.config.tempo_descanso
    
    def derrota(self):
        """Jogador perdeu."""
        self.fase = "derrota"
    
    def get_resumo(self) -> Dict:
        """Retorna resumo do modo horda."""
        return {
            "waves_completas": self.waves_completas,
            "melhor_wave": self.melhor_wave,
            "inimigos_derrotados": self.inimigos_derrotados,
            "dano_total_dado": round(self.dano_total_dado),
            "dano_total_recebido": round(self.dano_total_recebido),
            "tempo_total": round(self.tempo_total, 1),
        }


class HordeMode:
    """
    Gerenciador do Modo Horda — singleton.
    Integra com Simulador para controlar waves e spawns.
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
        self.state: Optional[HordeState] = None
        self.wave_atual: Optional[HordeWave] = None
        self.ativo = False
    
    def iniciar(self, config: Optional[HordeConfig] = None):
        """Inicia modo horda."""
        self.state = HordeState(config)
        self.ativo = True
        self.state.fase = "preparando"
    
    def gerar_proxima_wave(self) -> Optional[HordeWave]:
        """Gera e retorna a próxima wave."""
        if self.state is None:
            return None
        self.wave_atual = self.state.gerar_wave()
        self.state.fase = "boss" if self.wave_atual.boss else "combate"
        return self.wave_atual
    
    def update(self, dt: float, jogador=None, inimigos_vivos: int = 0) -> Dict:
        """
        Atualiza estado do horde mode.
        
        Retorna dict com ações para simulação:
            - {"acao": "proxima_wave"} — hora de spawnar wave
            - {"acao": "cura", "resultado": {...}} — cura aplicada
            - {"acao": "derrota", "resumo": {...}} — jogador perdeu
            - {"acao": "nenhuma"} — nada a fazer
        """
        if not self.ativo or self.state is None:
            return {"acao": "nenhuma"}
        
        self.state.tempo_total += dt
        
        # Verifica derrota do jogador
        if jogador and jogador.morto:
            self.state.derrota()
            return {"acao": "derrota", "resumo": self.state.get_resumo()}
        
        # Fase descanso
        if self.state.fase == "descanso":
            self.state.timer_descanso -= dt
            if self.state.timer_descanso <= 0:
                # Cura e prepara próxima wave
                resultado_cura = {}
                if jogador:
                    resultado_cura = self.state.aplicar_cura_entre_waves(jogador)
                return {"acao": "proxima_wave", "cura": resultado_cura}
        
        # Fase combate — verifica se wave acabou
        elif self.state.fase in ("combate", "boss"):
            if inimigos_vivos <= 0 and self.wave_atual is not None:
                self.state.wave_concluida()
                return {"acao": "wave_concluida", "wave": self.wave_atual.numero}
        
        # Fase preparando — primeira wave
        elif self.state.fase == "preparando":
            return {"acao": "proxima_wave"}
        
        return {"acao": "nenhuma"}
    
    def finalizar(self) -> Dict:
        """Finaliza modo horda e retorna resumo."""
        self.ativo = False
        if self.state:
            return self.state.get_resumo()
        return {}
