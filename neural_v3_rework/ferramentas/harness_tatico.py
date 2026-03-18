#!/usr/bin/env python3
"""
Harness tatico do posto headless.

Objetivo:
- Selecionar composicoes reais do roster por papel tatico
- Rodar cenarios 1v1, grupo vs grupo e grupo vs horda em modo dummy/headless
- Gerar relatorio comparavel por template e por papel
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dados.app_state import AppState
from modelos import Arma, Personagem
from nucleo.skills import get_skill_classification
from simulacao import Simulador
from utilitarios.postos_operacao import ensure_posto_dirs
from utilitarios.encounter_config import build_horde_match_config, build_team_match_config, get_horde_preset

FILE_PAPEIS = ROOT / "dados" / "papeis_taticos.json"
FILE_PLANO = ROOT / "dados" / "plano_testes_taticos.json"
FILE_TEMPLATES = ROOT / "dados" / "templates_composicao_tatica.json"


@dataclass
class CandidatoTatico:
    personagem: Personagem
    arma: Arma
    papel_id: str
    score: float
    motivos: list[str]


def normalizar_texto(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(ch for ch in base if not unicodedata.combining(ch))
    return sem_acento.upper().strip()


def carregar_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def carregar_catalogos() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        carregar_json(FILE_PAPEIS),
        carregar_json(FILE_PLANO),
        carregar_json(FILE_TEMPLATES),
    )


def score_personagem_para_papel(personagem: Personagem, arma: Arma, papel: dict[str, Any]) -> CandidatoTatico:
    score = 0.0
    motivos: list[str] = []
    classe = normalizar_texto(getattr(personagem, "classe", ""))
    personalidade = normalizar_texto(getattr(personagem, "personalidade", ""))
    familia = str(getattr(arma, "familia", "") or "").strip().lower()

    for token in papel.get("arquetipos_prioritarios", []):
        token_norm = normalizar_texto(token)
        if token_norm and token_norm in classe:
            score += 4.0
            motivos.append(f"classe:{token}")

    for token in papel.get("tracos_prioritarios", []):
        token_norm = normalizar_texto(token)
        if token_norm and token_norm in personalidade:
            score += 3.0
            motivos.append(f"traco:{token}")

    if familia in set(papel.get("familias_arma_preferidas", []) or []):
        score += 4.0
        motivos.append(f"familia:{familia}")

    classes_magia = {normalizar_texto(v) for v in papel.get("classes_magia_preferidas", [])}
    forcas_magia = {normalizar_texto(v) for v in papel.get("forcas_magia_preferidas", [])}
    for skill in getattr(arma, "habilidades", []) or []:
        if isinstance(skill, dict):
            nome_skill = skill.get("nome", "")
        else:
            nome_skill = str(skill)
        if not nome_skill:
            continue
        try:
            classificacao = get_skill_classification(nome_skill)
        except Exception:
            continue
        utilidade = normalizar_texto(getattr(classificacao, "classe_utilidade", ""))
        forca = normalizar_texto(getattr(classificacao, "classe_forca", ""))
        if utilidade in classes_magia:
            score += 1.5
            motivos.append(f"skill_util:{nome_skill}")
        if forca in forcas_magia:
            score += 1.0
            motivos.append(f"skill_forca:{nome_skill}")

    stats = getattr(personagem, "stats", None) or {}
    vida = float(stats.get("vida_max", 100.0) or 100.0)
    mana = float(stats.get("mana_max", getattr(personagem, "mana", 0.0)) or 0.0)
    forca_attr = float(getattr(personagem, "forca", 0.0) or 0.0)

    papel_id = papel["id"]
    if papel_id == "defensor":
        score += min(vida / 60.0, 3.0)
    elif papel_id == "curandeiro":
        score += min(mana / 25.0, 3.0)
    elif papel_id in {"bruiser", "assassino", "duelista"}:
        score += min(forca_attr / 3.0, 2.0)
    elif papel_id in {"atirador", "suporte_controle", "invocador", "controlador_de_area"}:
        score += min(mana / 30.0, 2.5)

    return CandidatoTatico(
        personagem=personagem,
        arma=arma,
        papel_id=papel_id,
        score=round(score, 3),
        motivos=motivos[:8],
    )


def construir_pool_tatico() -> tuple[AppState, dict[str, dict[str, Any]], list[CandidatoTatico]]:
    state = AppState.get()
    papeis_data, _, _ = carregar_catalogos()
    papeis = {item["id"]: item for item in papeis_data.get("papeis", [])}
    weapons = {arma.nome: arma for arma in state.weapons}
    candidatos: list[CandidatoTatico] = []
    for personagem in state.characters:
        arma = weapons.get(getattr(personagem, "nome_arma", ""))
        if arma is None:
            continue
        for papel in papeis.values():
            candidatos.append(score_personagem_para_papel(personagem, arma, papel))
    return state, papeis, candidatos


def selecionar_para_papel(
    papel_id: str,
    candidatos: list[CandidatoTatico],
    usados: set[str] | None = None,
    limite: int = 1,
) -> list[CandidatoTatico]:
    usados = usados or set()
    filtrados = [
        c for c in candidatos
        if c.papel_id == papel_id and c.personagem.nome not in usados
    ]
    filtrados.sort(key=lambda c: (c.score, c.personagem.nome), reverse=True)
    return filtrados[:limite]


def montar_template_selecionado(template_id: str) -> dict[str, Any]:
    state, papeis, candidatos = construir_pool_tatico()
    _, _, templates_data = carregar_catalogos()
    template = next((t for t in templates_data.get("templates", []) if t["id"] == template_id), None)
    if template is None:
        raise ValueError(f"Template tatico nao encontrado: {template_id}")

    usados_globais: set[str] = set()
    selecao = {
        "template": deepcopy(template),
        "team_a": [],
        "team_b": [],
        "horda": [],
        "horda_config": None,
    }

    for team_key in ("team_a", "team_b"):
        for slot in template.get(team_key, {}).get("slots", []):
            papel_id = slot["papel"]
            escolhidos = selecionar_para_papel(papel_id, candidatos, usados_globais, limite=1)
            if not escolhidos:
                raise ValueError(f"Nao encontrei personagem para o papel '{papel_id}' no template '{template_id}'")
            escolhido = escolhidos[0]
            usados_globais.add(escolhido.personagem.nome)
            selecao[team_key].append(
                {
                    "papel": papel_id,
                    "personagem": escolhido.personagem,
                    "arma": escolhido.arma,
                    "score": escolhido.score,
                    "motivos": escolhido.motivos,
                }
            )

    if template["modo"] == "grupo_vs_horda":
        preset_id = (template.get("horda") or {}).get("preset_id")
        preset = get_horde_preset(preset_id)
        if preset is None and template.get("horda"):
            preset = deepcopy(template["horda"])
        selecao["horda_config"] = preset or {}
        selecao["horda"] = gerar_horda(template.get("horda") or {})

    return selecao


def gerar_horda(config_horda: dict[str, Any]) -> list[dict[str, Any]]:
    quantidade = int(config_horda.get("quantidade", 5))
    familia = str(config_horda.get("familia_arma", "lamina"))
    classe = str(config_horda.get("classe", "Guerreiro (Força Bruta)"))
    personalidade = str(config_horda.get("personalidade", "Agressivo"))
    horda: list[dict[str, Any]] = []
    for idx in range(quantidade):
        arma = Arma(
            nome=f"Horda Lixo {idx + 1}",
            familia=familia,
            categoria="arma_fisica",
            subtipo="garra" if familia == "lamina" else "improviso",
            tipo="Reta",
            dano=3.2,
            peso=2.1,
            velocidade_ataque=0.88,
            critico=0.02,
            habilidades=[],
            afinidade_elemento=None,
            estilo="Rustico",
            raridade="Padrão",
        )
        personagem = Personagem(
            nome=f"Zumbi_{idx + 1:02d}",
            tamanho=1.68,
            forca=3.4,
            mana=1.2,
            nome_arma=arma.nome,
            peso_arma_cache=arma.peso,
            r=110,
            g=145,
            b=110,
            classe=classe,
            personalidade=personalidade,
            lore="Minion temporario gerado pelo harness tatico.",
        )
        horda.append({"papel": "horda", "personagem": personagem, "arma": arma, "score": 0.0, "motivos": ["horda_temporaria"]})
    return horda


class OverlayState:
    def __init__(self, state: AppState, extra_chars: list[Personagem], extra_weapons: list[Arma], match_config: dict[str, Any]):
        self.state = state
        self.extra_chars = extra_chars
        self.extra_weapons = extra_weapons
        self.match_config = match_config
        self.old_match = deepcopy(state.match_config)
        self.old_chars = list(state._characters)
        self.old_weapons = list(state._weapons)

    def __enter__(self):
        self.state._characters = self.old_chars + list(self.extra_chars)
        self.state._weapons = self.old_weapons + list(self.extra_weapons)
        self.state._match = {**self.old_match, **self.match_config}
        return self

    def __exit__(self, exc_type, exc, tb):
        self.state._characters = self.old_chars
        self.state._weapons = self.old_weapons
        self.state._match = self.old_match
        return False


def _resumir_times(sim: Simulador, nomes_a: set[str], nomes_b: set[str]) -> dict[str, Any]:
    stats = sim.stats_collector.get_summary() if hasattr(sim, "stats_collector") else {}
    fighters = getattr(sim, "fighters", []) or []
    team_status = {
        "team_a": {"vivos": 0, "mortos": 0, "names": []},
        "team_b": {"vivos": 0, "mortos": 0, "names": []},
    }
    for fighter in fighters:
        nome = getattr(getattr(fighter, "dados", None), "nome", "")
        if nome in nomes_a:
            bucket = "team_a"
        elif nome in nomes_b:
            bucket = "team_b"
        else:
            continue
        team_status[bucket]["names"].append(nome)
        if getattr(fighter, "morto", False):
            team_status[bucket]["mortos"] += 1
        else:
            team_status[bucket]["vivos"] += 1

    team_stats = {
        "team_a": {"damage_dealt": 0.0, "damage_taken": 0.0, "kills": 0, "deaths": 0, "skills_cast": 0, "mana_spent": 0.0},
        "team_b": {"damage_dealt": 0.0, "damage_taken": 0.0, "kills": 0, "deaths": 0, "skills_cast": 0, "mana_spent": 0.0},
    }
    for nome, fighter_stats in stats.items():
        if nome in nomes_a:
            bucket = "team_a"
        elif nome in nomes_b:
            bucket = "team_b"
        else:
            continue
        team_stats[bucket]["damage_dealt"] += float(fighter_stats.get("damage_dealt", 0.0) or 0.0)
        team_stats[bucket]["damage_taken"] += float(fighter_stats.get("damage_taken", 0.0) or 0.0)
        team_stats[bucket]["kills"] += int(fighter_stats.get("kills", 0) or 0)
        team_stats[bucket]["deaths"] += int(fighter_stats.get("deaths", 0) or 0)
        team_stats[bucket]["skills_cast"] += int(fighter_stats.get("skills_cast", 0) or 0)
        team_stats[bucket]["mana_spent"] += float(fighter_stats.get("mana_spent", 0.0) or 0.0)

    team_stats["team_a"] = {k: round(v, 3) if isinstance(v, float) else v for k, v in team_stats["team_a"].items()}
    team_stats["team_b"] = {k: round(v, 3) if isinstance(v, float) else v for k, v in team_stats["team_b"].items()}
    return {"fighters": stats, "team_stats": team_stats, "team_status": team_status}


def executar_match_headless_real(
    state: AppState,
    team_a: list[dict[str, Any]],
    team_b: list[dict[str, Any]],
    *,
    cenario: str,
    duracao_max_seg: float,
    modo: str = "grupo_vs_grupo",
    horda_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra_slots = team_a if modo == "grupo_vs_horda" else (team_a + team_b)
    extra_chars = [slot["personagem"] for slot in extra_slots if slot["personagem"].nome not in state.character_names()]
    extra_weapons = [slot["arma"] for slot in extra_slots if slot["arma"].nome not in state.weapon_names()]
    if modo == "grupo_vs_horda":
        match_config = build_horde_match_config(
            [
                {
                    "team_id": 0,
                    "label": "Expedicao",
                    "members": [slot["personagem"].nome for slot in team_a],
                }
            ],
            horda_config or {},
            cenario=cenario,
        )
    else:
        match_config = build_team_match_config(
            [
                {
                    "team_id": 0,
                    "label": "Time 1",
                    "members": [slot["personagem"].nome for slot in team_a],
                },
                {
                    "team_id": 1,
                    "label": "Time 2",
                    "members": [slot["personagem"].nome for slot in team_b],
                },
            ],
            cenario=cenario,
        )

    with OverlayState(state, extra_chars, extra_weapons, match_config):
        sim = Simulador()
        sim.TEMPO_MAX_LUTA = float(duracao_max_seg)
        dt = 1.0 / 60.0
        start = time.perf_counter()
        max_frames = int(duracao_max_seg * 60) + 30
        for _ in range(max_frames):
            if sim.vencedor:
                break
            sim.update(dt)
        elapsed_real = round(time.perf_counter() - start, 3)
        resumo = _resumir_times(
            sim,
            {slot["personagem"].nome for slot in team_a},
            {slot["personagem"].nome for slot in team_b},
        )
        vencedor = str(sim.vencedor or "Sem vencedor")
        frames = int(getattr(getattr(sim, "stats_collector", None), "_frame", 0) or 0)
        try:
            import pygame
            pygame.display.quit()
            pygame.mixer.quit()
            pygame.quit()
        except Exception:
            pass
        payload = {
            "vencedor": vencedor,
            "frames": frames,
            "tempo_simulado": round(frames / 60.0, 3),
            "tempo_real": elapsed_real,
            **resumo,
        }
        if modo == "grupo_vs_horda" and getattr(sim, "horde_manager", None):
            payload["horda"] = sim.horde_manager.export_summary()
        return payload


def agregar_relatorio(template: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    team_wins = Counter()
    fighter_wins = Counter()
    frames = 0
    tempo_simulado = 0.0
    tempo_real = 0.0
    damage_totals = {"team_a": 0.0, "team_b": 0.0}
    papel_resumo: dict[str, dict[str, Any]] = defaultdict(lambda: {"presencas": 0, "damage_dealt": 0.0, "kills": 0})
    horda_wave_total = 0.0
    horda_kills_total = 0.0

    for run in runs:
        frames += int(run.get("frames", 0) or 0)
        tempo_simulado += float(run.get("tempo_simulado", 0.0) or 0.0)
        tempo_real += float(run.get("tempo_real", 0.0) or 0.0)
        vencedor = str(run.get("vencedor", ""))
        if vencedor.startswith("Time 1") or vencedor in run.get("team_status", {}).get("team_a", {}).get("names", []):
            team_wins["team_a"] += 1
        elif vencedor.startswith("Time 2") or vencedor in run.get("team_status", {}).get("team_b", {}).get("names", []):
            team_wins["team_b"] += 1
        fighter_wins[vencedor] += 1

        for team_key in ("team_a", "team_b"):
            damage_totals[team_key] += float(run.get("team_stats", {}).get(team_key, {}).get("damage_dealt", 0.0) or 0.0)
        if run.get("horda"):
            horda_wave_total += float(run["horda"].get("wave_atual", 0) or 0)
            horda_kills_total += float(run["horda"].get("total_killed", 0) or 0)

        fighter_stats = run.get("fighters", {}) or {}
        papel_lookup = {}
        for team_key in ("team_a", "team_b"):
            for slot in template[team_key]:
                nome = slot.get("nome")
                if not nome and "personagem" in slot:
                    nome = getattr(slot["personagem"], "nome", "")
                if nome:
                    papel_lookup[nome] = slot["papel"]
        for nome, stats in fighter_stats.items():
            papel_id = papel_lookup.get(nome, "horda")
            papel_resumo[papel_id]["presencas"] += 1
            papel_resumo[papel_id]["damage_dealt"] += float(stats.get("damage_dealt", 0.0) or 0.0)
            papel_resumo[papel_id]["kills"] += int(stats.get("kills", 0) or 0)

    total_runs = max(len(runs), 1)
    resumo = {
        "template_id": template["template_meta"]["id"],
        "modo": template["template_meta"]["modo"],
        "runs": len(runs),
        "team_wins": dict(team_wins),
        "winner_counts": dict(fighter_wins),
        "avg_frames": round(frames / total_runs, 2),
        "avg_tempo_simulado": round(tempo_simulado / total_runs, 3),
        "avg_tempo_real": round(tempo_real / total_runs, 3),
        "team_damage_avg": {
            "team_a": round(damage_totals["team_a"] / total_runs, 3),
            "team_b": round(damage_totals["team_b"] / total_runs, 3),
        },
        "papeis": {
            papel: {
                "presencas": dados["presencas"],
                "damage_dealt": round(dados["damage_dealt"], 3),
                "kills": dados["kills"],
            }
            for papel, dados in sorted(papel_resumo.items())
        },
    }
    if horda_wave_total > 0:
        resumo["horda"] = {
            "avg_wave_alcancada": round(horda_wave_total / total_runs, 3),
            "avg_abates_horda": round(horda_kills_total / total_runs, 3),
        }
    return resumo


def executar_template(template_id: str, runs: int, seed: int = 0) -> dict[str, Any]:
    random.seed(seed)
    selecao = montar_template_selecionado(template_id)
    state = AppState.get()
    template_meta = selecao["template"]
    if selecao["horda"]:
        team_b = selecao["horda"]
    else:
        team_b = selecao["team_b"]

    lutas = []
    for idx in range(runs):
        random.seed(seed + idx)
        resultado = executar_match_headless_real(
            state,
            selecao["team_a"],
            team_b,
            cenario=template_meta.get("cenario", "Arena"),
            duracao_max_seg=float(template_meta.get("duracao_max_seg", 90.0) or 90.0),
            modo=template_meta.get("modo", "grupo_vs_grupo"),
            horda_config=selecao.get("horda_config"),
        )
        resultado["run_index"] = idx
        lutas.append(resultado)

    report_template = {
        "template_meta": {
            "id": template_meta["id"],
            "modo": template_meta["modo"],
            "nome": template_meta["nome"],
            "cenario": template_meta.get("cenario", "Arena"),
        },
        "team_a": [
            {
                "papel": slot["papel"],
                "nome": slot["personagem"].nome,
                "arma": slot["arma"].nome,
                "familia_arma": slot["arma"].familia,
                "score": slot["score"],
            }
            for slot in selecao["team_a"]
        ],
        "team_b": [
            {
                "papel": slot["papel"],
                "nome": slot["personagem"].nome,
                "arma": slot["arma"].nome,
                "familia_arma": slot["arma"].familia,
                "score": slot["score"],
            }
            for slot in team_b
        ],
    }
    report = agregar_relatorio(report_template, lutas)
    report.update(report_template)
    report["lutas"] = lutas
    return report


def listar_templates() -> list[dict[str, Any]]:
    _, _, templates_data = carregar_catalogos()
    return templates_data.get("templates", [])


def salvar_relatorio(report: dict[str, Any], json_out: str | None) -> Path:
    dirs = ensure_posto_dirs()
    if json_out:
        path = Path(json_out)
    else:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = dirs["headless_reports"] / f"harness_tatico_{report['template_id']}_{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness tatico do posto headless")
    parser.add_argument("--modo", choices=["1v1", "grupo_vs_grupo", "grupo_vs_horda", "todos"], default="todos")
    parser.add_argument("--template", default=None, help="ID de um template especifico")
    parser.add_argument("--runs", type=int, default=None, help="Quantidade de execucoes por template")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--listar-templates", action="store_true")
    args = parser.parse_args()

    templates = listar_templates()
    if args.listar_templates:
        print(json.dumps(templates, ensure_ascii=False, indent=2))
        return 0

    filtrados = templates
    if args.template:
        filtrados = [tpl for tpl in templates if tpl["id"] == args.template]
        if not filtrados:
            raise SystemExit(f"Template nao encontrado: {args.template}")
    elif args.modo != "todos":
        filtrados = [tpl for tpl in templates if tpl["modo"] == args.modo]

    reports = []
    for idx, template in enumerate(filtrados):
        runs = int(args.runs or template.get("runs_recomendados", 1))
        report = executar_template(template["id"], runs=runs, seed=args.seed + idx * 17)
        reports.append(report)

    payload: dict[str, Any]
    if len(reports) == 1:
        payload = reports[0]
    else:
        payload = {
            "modo": args.modo,
            "templates": reports,
            "total_templates": len(reports),
        }

    path = salvar_relatorio(payload, args.json_out)
    print(f"[harness tatico] relatorio salvo em: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
