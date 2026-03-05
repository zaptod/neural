"""
NEURAL FIGHTS — Sistema de Replay v1.0
========================================
Grava keyframes durante a luta e permite reprodução posterior.
Formato leve baseado em snapshots periódicos + eventos importantes.
"""

import json
import os
import time
from typing import Dict, List, Optional, Any


_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(os.path.dirname(_HERE), "data")
_REPLAYS_DIR = os.path.join(_DATA, "replays")


class ReplayFrame:
    """Um snapshot do estado da luta num instante."""
    __slots__ = ("tempo", "fighters", "eventos")
    
    def __init__(self, tempo: float, fighters: List[Dict], eventos: Optional[List[Dict]] = None):
        self.tempo = tempo
        self.fighters = fighters
        self.eventos = eventos or []
    
    def to_dict(self) -> Dict:
        return {
            "t": round(self.tempo, 3),
            "f": self.fighters,
            "e": self.eventos,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "ReplayFrame":
        return cls(d["t"], d["f"], d.get("e", []))


class ReplayRecorder:
    """Grava replay de uma luta."""
    
    def __init__(self, intervalo_keyframe: float = 0.1):
        self.intervalo = intervalo_keyframe  # 0.1s = 10 keyframes/segundo
        self.frames: List[ReplayFrame] = []
        self.eventos_pendentes: List[Dict] = []
        self.timer = 0.0
        self.metadata: Dict = {}
        self.gravando = False
    
    def iniciar(self, p1_nome: str, p2_nome: str, arena: str = "Arena",
                p1_classe: str = "", p2_classe: str = ""):
        """Inicia gravação"""
        self.frames = []
        self.eventos_pendentes = []
        self.timer = 0.0
        self.gravando = True
        self.metadata = {
            "p1": p1_nome,
            "p2": p2_nome,
            "p1_classe": p1_classe,
            "p2_classe": p2_classe,
            "arena": arena,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "versao": "1.0",
        }
    
    def _snapshot_lutador(self, lutador) -> Dict:
        """Captura snapshot mínimo de um lutador"""
        return {
            "n": lutador.dados.nome,
            "x": round(lutador.pos[0], 2),
            "y": round(lutador.pos[1], 2),
            "z": round(getattr(lutador, 'z', 0), 2),
            "hp": round(lutador.vida, 1),
            "hpm": round(lutador.vida_max, 1),
            "mp": round(getattr(lutador, 'mana', 0), 1),
            "st": round(getattr(lutador, 'estamina', 100), 1),
            "ang": round(getattr(lutador, 'angulo_olhar', 0), 1),
            "atk": getattr(lutador, 'atacando', False),
            "stun": round(getattr(lutador, 'stun_timer', 0), 2),
            "dead": getattr(lutador, 'morto', False),
            "acao": getattr(getattr(lutador, 'brain', None), 'acao_atual', "IDLE") if getattr(lutador, 'brain', None) else "IDLE",
        }
    
    def registrar_evento(self, tipo: str, **kwargs):
        """Registra evento importante (golpe, skill, morte, etc.)"""
        if not self.gravando:
            return
        evento = {"tipo": tipo}
        evento.update(kwargs)
        self.eventos_pendentes.append(evento)
    
    def update(self, dt: float, fighters: list):
        """Atualiza gravação — chama a cada frame"""
        if not self.gravando:
            return
        
        self.timer += dt
        
        # Captura keyframe no intervalo
        if self.timer >= self.intervalo:
            self.timer -= self.intervalo
            
            f_data = [self._snapshot_lutador(f) for f in fighters]
            frame = ReplayFrame(
                tempo=len(self.frames) * self.intervalo,
                fighters=f_data,
                eventos=self.eventos_pendentes
            )
            self.frames.append(frame)
            self.eventos_pendentes = []
    
    def finalizar(self, vencedor: str = "", duracao: float = 0.0) -> Dict:
        """Finaliza gravação e retorna dados"""
        self.gravando = False
        self.metadata["vencedor"] = vencedor
        self.metadata["duracao"] = round(duracao, 2)
        self.metadata["total_frames"] = len(self.frames)
        
        return {
            "meta": self.metadata,
            "frames": [f.to_dict() for f in self.frames],
        }
    
    def salvar(self, vencedor: str = "", duracao: float = 0.0) -> Optional[str]:
        """Salva replay em disco"""
        dados = self.finalizar(vencedor, duracao)
        
        os.makedirs(_REPLAYS_DIR, exist_ok=True)
        
        p1 = self.metadata.get("p1", "??")
        p2 = self.metadata.get("p2", "??")
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"replay_{p1}_vs_{p2}_{ts}.json"
        # Sanitiza nome do arquivo
        filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        filepath = os.path.join(_REPLAYS_DIR, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False)
            return filepath
        except Exception as e:
            print(f"[Replay] Erro ao salvar: {e}")
            return None


class ReplayPlayer:
    """Reproduz um replay gravado."""
    
    def __init__(self):
        self.dados: Optional[Dict] = None
        self.frames: List[ReplayFrame] = []
        self.frame_atual = 0
        self.tempo = 0.0
        self.reproduzindo = False
        self.velocidade = 1.0
    
    def carregar(self, filepath: str) -> bool:
        """Carrega replay do disco"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.dados = json.load(f)
            
            self.frames = [ReplayFrame.from_dict(fd) for fd in self.dados.get("frames", [])] if self.dados else []
            self.frame_atual = 0
            self.tempo = 0.0
            self.reproduzindo = True
            return True
        except Exception as e:
            print(f"[Replay] Erro ao carregar: {e}")
            return False
    
    def get_metadata(self) -> Dict:
        """Retorna metadados do replay"""
        return self.dados.get("meta", {}) if self.dados else {}
    
    def update(self, dt: float) -> Optional[ReplayFrame]:
        """Avança o replay e retorna o frame atual"""
        if not self.reproduzindo or not self.frames:
            return None
        
        self.tempo += dt * self.velocidade
        
        # Encontra frame correspondente
        while (self.frame_atual < len(self.frames) - 1 and 
               self.frames[self.frame_atual + 1].tempo <= self.tempo):
            self.frame_atual += 1
        
        if self.frame_atual >= len(self.frames) - 1:
            self.reproduzindo = False
        
        return self.frames[self.frame_atual]
    
    def seek(self, tempo: float):
        """Pula para um tempo específico"""
        self.tempo = max(0, tempo)
        self.frame_atual = 0
        for i, frame in enumerate(self.frames):
            if frame.tempo > self.tempo:
                break
            self.frame_atual = i
        self.reproduzindo = True
    
    def pausar(self):
        self.reproduzindo = not self.reproduzindo
    
    def set_velocidade(self, vel: float):
        self.velocidade = max(0.1, min(5.0, vel))
    
    def get_progresso(self) -> float:
        """Retorna progresso 0.0 → 1.0"""
        if not self.frames:
            return 0.0
        return self.frame_atual / max(1, len(self.frames) - 1)


class ReplaySystem:
    """
    Sistema de Replay — singleton gerenciador.
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
        self.recorder = ReplayRecorder()
        self.player = ReplayPlayer()
        self.auto_salvar = True
        self.max_replays = 50
    
    def iniciar_gravacao(self, p1_nome: str, p2_nome: str, arena: str = "Arena",
                        p1_classe: str = "", p2_classe: str = ""):
        """Inicia gravação de replay"""
        self.recorder.iniciar(p1_nome, p2_nome, arena, p1_classe, p2_classe)
    
    def update_gravacao(self, dt: float, fighters: list):
        """Atualiza gravação"""
        self.recorder.update(dt, fighters)
    
    def registrar_evento(self, tipo: str, **kwargs):
        """Registra evento no replay"""
        self.recorder.registrar_evento(tipo, **kwargs)
    
    def finalizar_gravacao(self, vencedor: str = "", duracao: float = 0.0) -> Optional[str]:
        """Finaliza e opcionalmente salva"""
        if self.auto_salvar:
            path = self.recorder.salvar(vencedor, duracao)
            self._limpar_replays_antigos()
            return path
        self.recorder.finalizar(vencedor, duracao)
        return None
    
    def listar_replays(self) -> List[Dict]:
        """Lista replays disponíveis"""
        replays = []
        if not os.path.exists(_REPLAYS_DIR):
            return replays
        
        for f in sorted(os.listdir(_REPLAYS_DIR), reverse=True):
            if f.endswith(".json"):
                filepath = os.path.join(_REPLAYS_DIR, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        dados = json.load(fh)
                        meta = dados.get("meta", {})
                        meta["filepath"] = filepath
                        replays.append(meta)
                except Exception:
                    pass
        
        return replays
    
    def _limpar_replays_antigos(self):
        """Remove replays mais antigos que o limite"""
        if not os.path.exists(_REPLAYS_DIR):
            return
        
        arquivos = sorted(
            [os.path.join(_REPLAYS_DIR, f) for f in os.listdir(_REPLAYS_DIR) if f.endswith(".json")],
            key=os.path.getmtime, reverse=True
        )
        
        for arq in arquivos[self.max_replays:]:
            try:
                os.remove(arq)
            except Exception:
                pass
