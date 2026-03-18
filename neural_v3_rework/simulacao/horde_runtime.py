"""
Runtime base do modo horda sobre o motor principal.

V1:
- ondas de monstros melee simples
- IA de contato basica
- base pronta para outros arquetipos depois
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import math
import random

from modelos import Arma, Personagem
from nucleo.lutador import Lutador


ROOT = Path(__file__).resolve().parents[1]
FILE_MONSTROS = ROOT / "dados" / "monstros.json"


def load_monster_catalog() -> dict:
    if not FILE_MONSTROS.exists():
        return {"monstros": []}
    with FILE_MONSTROS.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_monster_definition(monster_id: str) -> dict | None:
    for monster in load_monster_catalog().get("monstros", []):
        if monster.get("id") == monster_id:
            return deepcopy(monster)
    return None


class MonsterBrain:
    """IA bem simples para hordas V1: perseguir e bater por contato."""

    def __init__(self, lutador: Lutador, monster_data: dict, base_brain):
        self.lutador = lutador
        self.monster_data = monster_data
        self._base_brain = base_brain
        self.acao_atual = "APROXIMAR"
        self.dir_circular = random.choice([-1, 1])
        self.tracos = []
        self.medo = 0.0
        self.ritmo_combate = 1.0
        self.momentum = 0.0
        self._pos_interceptacao = None
        self.memoria_cena = {"tipo": None, "intensidade": 0.0, "duracao": 0.0}
        self.memoria_oponente = {"id_atual": None, "adaptacao_por_oponente": {}}
        self.multi_awareness = {"aliados": [], "inimigos": []}

    def __getattr__(self, item):
        return getattr(self._base_brain, item)

    def processar(self, dt, distancia, inimigo, todos_lutadores=None):
        if inimigo is None or getattr(inimigo, "morto", False):
            self.acao_atual = "NEUTRO"
            return
        alcance = max(1.15, float(getattr(self.lutador, "alcance_ideal", 2.0) or 2.0))
        if distancia > alcance * 0.92:
            self.acao_atual = "APROXIMAR"
        elif distancia > alcance * 0.55:
            self.acao_atual = "PRESSIONAR"
        else:
            self.acao_atual = "MATAR"


class HordeWaveManager:
    def __init__(self, sim, config: dict):
        self.sim = sim
        self.config = deepcopy(config or {})
        self.team_id = int(self.config.get("team_id", 1) or 1)
        self.label = str(self.config.get("label", "Horda"))
        inter_wave_delay = self.config.get("inter_wave_delay", 2.5)
        spawn_interval = self.config.get("spawn_interval", 0.45)
        self.inter_wave_delay = float(2.5 if inter_wave_delay is None else inter_wave_delay)
        self.spawn_interval = float(0.45 if spawn_interval is None else spawn_interval)
        self.waves = deepcopy(self.config.get("waves", []))

        self.current_wave_index = -1
        self.current_wave_label = ""
        self.pending_spawns: list[str] = []
        self.spawn_timer = 0.0
        self.intermission_timer = 0.0
        self.started = False
        self.completed = False
        self.failed = False
        self.total_spawned = 0
        self.total_killed = 0
        self.kills_by_monster = Counter()
        self.wave_history: list[dict] = []

    def start(self):
        if self.started:
            return
        self.started = True
        if not self.waves:
            self.completed = True
            return
        self._begin_wave(0)

    def update(self, dt: float):
        if not self.started or self.completed or self.failed:
            return

        if not self._players_alive():
            self.failed = True
            return

        self.total_killed = sum(1 for fighter in self.sim.fighters if getattr(fighter, "is_monster", False) and fighter.morto)

        if self.pending_spawns:
            self.spawn_timer -= dt
            while self.pending_spawns and self.spawn_timer <= 0.0:
                monster_id = self.pending_spawns.pop(0)
                self._spawn_monster(monster_id)
                self.spawn_timer = self.spawn_interval
                if self.spawn_interval > 0:
                    break
            return

        if self._alive_monsters():
            return

        if self.current_wave_index >= len(self.waves) - 1:
            self.completed = True
            return

        self.intermission_timer += dt
        if self.intermission_timer >= self.inter_wave_delay:
            self.intermission_timer = 0.0
            self._begin_wave(self.current_wave_index + 1)

    def export_summary(self) -> dict:
        return {
            "label": self.label,
            "waves_total": len(self.waves),
            "wave_atual": max(0, self.current_wave_index + 1),
            "wave_label": self.current_wave_label,
            "total_spawned": self.total_spawned,
            "total_killed": self.total_killed,
            "completed": self.completed,
            "failed": self.failed,
            "ativos": len(self._alive_monsters()),
            "historico": deepcopy(self.wave_history),
        }

    def _begin_wave(self, wave_index: int):
        self.current_wave_index = wave_index
        wave = self.waves[wave_index]
        self.current_wave_label = str(wave.get("label", f"Wave {wave_index + 1}"))
        self.pending_spawns = []
        for entry in wave.get("entries", []):
            monster_id = str(entry.get("monster_id", "")).strip()
            quantidade = int(entry.get("quantidade", 0) or 0)
            for _ in range(max(0, quantidade)):
                self.pending_spawns.append(monster_id)
        self.spawn_timer = 0.0
        self.wave_history.append(
            {
                "wave": wave_index + 1,
                "label": self.current_wave_label,
                "planned": len(self.pending_spawns),
            }
        )

    def _spawn_monster(self, monster_id: str):
        monster = get_monster_definition(monster_id)
        if not monster:
            return

        arma_data = deepcopy(monster.get("arma", {}))
        arma = Arma(
            nome=arma_data.get("nome", monster["nome"]),
            familia=arma_data.get("familia", "lamina"),
            subtipo=arma_data.get("subtipo", "garra"),
            tipo=arma_data.get("tipo", "Reta"),
            dano=arma_data.get("dano", 3.0),
            peso=arma_data.get("peso", 2.0),
            velocidade_ataque=arma_data.get("velocidade_ataque", 0.9),
            critico=arma_data.get("critico", 0.01),
            habilidades=arma_data.get("habilidades", []),
            raridade="Padrão",
            estilo="Monstro",
        )
        stats = monster.get("stats", {})
        visual = monster.get("visual", {})
        personagem = Personagem(
            nome=f"{monster['nome']} #{self.total_spawned + 1:02d}",
            tamanho=stats.get("tamanho", 1.7),
            forca=stats.get("forca", 3.5),
            mana=max(1.0, float(stats.get("mana", 1.0) or 1.0)),
            nome_arma=arma.nome,
            peso_arma_cache=arma.peso,
            r=visual.get("cor_r", 140),
            g=visual.get("cor_g", 160),
            b=visual.get("cor_b", 120),
            classe=monster.get("classe", "Guerreiro (Força Bruta)"),
            personalidade=monster.get("personalidade", "Agressivo"),
            lore=f"Monstro de horda: {monster.get('id', 'desconhecido')}",
        )
        personagem.arma_obj = arma
        lutador = Lutador(personagem, 0, 0, team_id=self.team_id)
        lutador.brain = MonsterBrain(lutador, monster, lutador.brain)
        lutador.is_monster = True
        lutador.monster_id = monster.get("id")
        lutador.monster_tipo = monster.get("tipo", "minion")
        lutador.monster_tags = list(monster.get("tags", []))

        self._attach_to_sim(lutador)
        self.total_spawned += 1

    def _attach_to_sim(self, lutador: Lutador):
        spawn_x, spawn_y = self._resolve_spawn_position()
        lutador.pos[0] = spawn_x
        lutador.pos[1] = spawn_y
        self.sim.fighters.append(lutador)
        self.sim.teams.setdefault(lutador.team_id, []).append(lutador)
        self.sim.rastros[lutador] = []
        self.sim.vida_visual[lutador] = lutador.vida_max
        self.sim._prev_z[lutador] = 0
        self.sim._prev_acao_ai[lutador] = ""
        self.sim._prev_stagger[lutador] = False
        self.sim._prev_dash[lutador] = 0
        if hasattr(self.sim, "stats_collector"):
            self.sim.stats_collector.register(lutador.dados.nome)
            lutador.stats_collector = self.sim.stats_collector
        lutador.encounter_mode = "horda"
        lutador.objective_config = dict(getattr(self.sim, "objective_config", {}) or {})
        lutador.campaign_context = dict(getattr(self.sim, "campaign_context", {}) or {})
        if getattr(lutador, "brain", None) is not None:
            lutador.brain.encounter_mode = "horda"
            lutador.brain.objective_config = dict(getattr(self.sim, "objective_config", {}) or {})
            lutador.brain.campaign_context = dict(getattr(self.sim, "campaign_context", {}) or {})

    def _resolve_spawn_position(self) -> tuple[float, float]:
        arena = getattr(self.sim, "arena", None)
        if arena is None:
            return 18.0, 8.0
        cx = float(getattr(arena, "centro_x", 15.0))
        cy = float(getattr(arena, "centro_y", 10.0))
        largura = float(getattr(arena, "largura", 30.0))
        altura = float(getattr(arena, "altura", 20.0))
        margem_x = max(1.5, largura * 0.42)
        margem_y = max(1.5, altura * 0.42)
        borda = random.choice(("esquerda", "direita", "topo", "base"))
        if borda == "esquerda":
            return cx - margem_x, cy + random.uniform(-margem_y, margem_y)
        if borda == "direita":
            return cx + margem_x, cy + random.uniform(-margem_y, margem_y)
        if borda == "topo":
            return cx + random.uniform(-margem_x, margem_x), cy - margem_y
        return cx + random.uniform(-margem_x, margem_x), cy + margem_y

    def _players_alive(self) -> list[Lutador]:
        return [
            fighter for fighter in self.sim.fighters
            if fighter.team_id != self.team_id and not fighter.morto
        ]

    def _alive_monsters(self) -> list[Lutador]:
        return [
            fighter for fighter in self.sim.fighters
            if fighter.team_id == self.team_id and not fighter.morto
        ]
