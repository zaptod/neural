"""
Helpers para normalizacao do match_config em um encounter_config canonico.

Objetivo:
- manter compatibilidade com o fluxo legado 1v1
- suportar equipes, horda e fundacao da campanha no mesmo formato
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
FILE_HORDA_PRESETS = ROOT / "dados" / "ondas_horda.json"


DEFAULT_ENCOUNTER_CONFIG = {
    "modo_partida": "duelo",
    "p1_nome": "",
    "p2_nome": "",
    "cenario": "Arena",
    "best_of": 1,
    "portrait_mode": False,
    "teams": None,
    "horda_config": None,
    "campaign_context": {},
    "objective_config": {},
    "metadata": {},
}


def _load_json(path: Path, default):
    if not path.exists():
        return deepcopy(default)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return deepcopy(default)


def load_horde_presets() -> dict:
    data = _load_json(FILE_HORDA_PRESETS, {"presets": []})
    presets = {}
    for preset in data.get("presets", []):
        if isinstance(preset, dict) and preset.get("id"):
            presets[str(preset["id"])] = preset
    return presets


def get_horde_preset(preset_id: str | None) -> dict | None:
    if not preset_id:
        return None
    return deepcopy(load_horde_presets().get(str(preset_id)))


def _normalize_team(team: dict, index: int) -> dict:
    members = [str(name).strip() for name in team.get("members", []) if str(name).strip()]
    return {
        "team_id": int(team.get("team_id", index)),
        "label": str(team.get("label") or f"Time {index + 1}"),
        "members": members,
    }


def infer_mode(config: dict) -> str:
    explicit = str(config.get("modo_partida", "") or "").strip().lower()
    if explicit in {"duelo", "equipes", "horda", "campanha"}:
        return explicit
    if config.get("horda_config"):
        return "horda"
    teams = config.get("teams")
    if isinstance(teams, list) and teams:
        return "equipes"
    return "duelo"


def normalize_match_config(config: dict | None) -> dict:
    raw = dict(config) if isinstance(config, dict) else {}
    merged = deepcopy(DEFAULT_ENCOUNTER_CONFIG)
    if isinstance(config, dict):
        merged.update(config)

    if raw.get("modo_partida") in {"duelo", "equipes", "horda", "campanha"}:
        modo = str(raw.get("modo_partida"))
    else:
        modo = infer_mode(raw or merged)
    merged["modo_partida"] = modo

    teams = merged.get("teams")
    if isinstance(teams, list) and teams:
        merged["teams"] = [_normalize_team(team, idx) for idx, team in enumerate(teams)]
    else:
        merged["teams"] = None

    if modo == "duelo":
        if not merged.get("p1_nome") and merged["teams"] and merged["teams"][0]["members"]:
            merged["p1_nome"] = merged["teams"][0]["members"][0]
        if not merged.get("p2_nome") and merged["teams"] and len(merged["teams"]) > 1 and merged["teams"][1]["members"]:
            merged["p2_nome"] = merged["teams"][1]["members"][0]
        if not merged["teams"] and merged.get("p1_nome") and merged.get("p2_nome"):
            merged["teams"] = [
                {"team_id": 0, "label": "Time 1", "members": [merged["p1_nome"]]},
                {"team_id": 1, "label": "Time 2", "members": [merged["p2_nome"]]},
            ]
    elif modo == "equipes":
        if not merged["teams"] and merged.get("p1_nome") and merged.get("p2_nome"):
            merged["teams"] = [
                {"team_id": 0, "label": "Time 1", "members": [merged["p1_nome"]]},
                {"team_id": 1, "label": "Time 2", "members": [merged["p2_nome"]]},
            ]
        if merged["teams"]:
            if merged["teams"][0]["members"]:
                merged["p1_nome"] = merged["teams"][0]["members"][0]
            if len(merged["teams"]) > 1 and merged["teams"][1]["members"]:
                merged["p2_nome"] = merged["teams"][1]["members"][0]
    elif modo == "horda":
        if not merged["teams"] and merged.get("p1_nome"):
            members = [merged["p1_nome"]]
            if merged.get("p2_nome") and merged["p2_nome"] != merged["p1_nome"]:
                members.append(merged["p2_nome"])
            merged["teams"] = [{"team_id": 0, "label": "Expedicao", "members": members}]
        horda = deepcopy(merged.get("horda_config") or {})
        preset_id = horda.get("preset_id")
        preset = get_horde_preset(preset_id)
        if preset:
            base = deepcopy(preset)
            base.update(horda)
            horda = base
        horda.setdefault("preset_id", preset_id or "")
        horda.setdefault("label", horda.get("nome", "Horda"))
        horda.setdefault("team_id", 1)
        horda.setdefault("inter_wave_delay", 2.5)
        horda.setdefault("spawn_interval", 0.45)
        horda.setdefault("waves", [])
        merged["horda_config"] = horda
        if merged["teams"] and merged["teams"][0]["members"]:
            merged["p1_nome"] = merged["teams"][0]["members"][0]
        if not merged.get("p2_nome"):
            merged["p2_nome"] = str(horda.get("label", "Horda"))
    else:
        merged["campaign_context"] = deepcopy(merged.get("campaign_context") or {})
        merged["objective_config"] = deepcopy(merged.get("objective_config") or {})

    merged["best_of"] = int(merged.get("best_of", 1) or 1)
    merged["portrait_mode"] = bool(merged.get("portrait_mode", False))
    merged["campaign_context"] = deepcopy(merged.get("campaign_context") or {})
    merged["objective_config"] = deepcopy(merged.get("objective_config") or {})
    merged["metadata"] = deepcopy(merged.get("metadata") or {})
    return merged


def build_duel_match_config(
    p1_nome: str,
    p2_nome: str,
    *,
    cenario: str = "Arena",
    best_of: int = 1,
    portrait_mode: bool = False,
    extra: dict | None = None,
) -> dict:
    config = {
        "modo_partida": "duelo",
        "p1_nome": p1_nome,
        "p2_nome": p2_nome,
        "cenario": cenario,
        "best_of": best_of,
        "portrait_mode": portrait_mode,
    }
    if extra:
        config.update(extra)
    return normalize_match_config(config)


def build_team_match_config(
    teams: list[dict],
    *,
    cenario: str = "Arena",
    portrait_mode: bool = False,
    extra: dict | None = None,
) -> dict:
    config = {
        "modo_partida": "equipes",
        "cenario": cenario,
        "portrait_mode": portrait_mode,
        "teams": teams,
    }
    if extra:
        config.update(extra)
    return normalize_match_config(config)


def build_horde_match_config(
    teams: list[dict],
    horda_config: dict,
    *,
    cenario: str = "Campo de Batalha",
    portrait_mode: bool = False,
    extra: dict | None = None,
) -> dict:
    config = {
        "modo_partida": "horda",
        "cenario": cenario,
        "portrait_mode": portrait_mode,
        "teams": teams,
        "horda_config": deepcopy(horda_config),
    }
    if extra:
        config.update(extra)
    return normalize_match_config(config)


def get_encounter_side_labels(config: dict) -> tuple[str, str]:
    normalized = normalize_match_config(config)
    modo = normalized["modo_partida"]
    if modo == "duelo":
        return normalized.get("p1_nome", "P1"), normalized.get("p2_nome", "P2")
    teams = normalized.get("teams") or []
    side_a = teams[0]["label"] if teams else "Time 1"
    if modo == "horda":
        horda_label = str((normalized.get("horda_config") or {}).get("label", "Horda"))
        return side_a, horda_label
    side_b = teams[1]["label"] if len(teams) > 1 else "Time 2"
    return side_a, side_b
