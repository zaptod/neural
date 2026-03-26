"""Inferencia leve de pacote tatico para equipes e horda."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
import json
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
FILE_PAPEIS = ROOT / "dados" / "papeis_taticos.json"


PACKAGE_TO_TEAM_ROLE = {
    "defensor": "VANGUARD",
    "bastiao_orbital": "VANGUARD",
    "curandeiro": "SUPPORT",
    "suporte_controle": "CONTROLLER",
    "maestro_astral": "CONTROLLER",
    "atirador": "ARTILLERY",
    "artilheiro_orbital": "ARTILLERY",
    "assassino": "FLANKER",
    "duelista": "STRIKER",
    "bruiser": "STRIKER",
    "invocador": "CONTROLLER",
    "controlador_de_area": "CONTROLLER",
    "limpador_de_horda": "ARTILLERY",
}


def _norm(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return base.strip().lower()


@lru_cache(maxsize=1)
def load_tactical_packages() -> dict:
    if not FILE_PAPEIS.exists():
        return {"papeis": []}
    with FILE_PAPEIS.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _fighter_traits(fighter) -> set[str]:
    brain = getattr(fighter, "brain", None)
    tracos = set()
    for traco in getattr(brain, "tracos", []) or []:
        tracos.add(_norm(traco))
    return tracos


def _fighter_archetypes(fighter) -> set[str]:
    brain = getattr(fighter, "brain", None)
    dados = getattr(fighter, "dados", None)
    classe = _norm(getattr(dados, "classe", ""))
    arqu = _norm(getattr(brain, "arquetipo", ""))
    tokens = {classe, arqu}
    for token in classe.replace("(", " ").replace(")", " ").replace("-", " ").split():
        tokens.add(_norm(token))
    if arqu:
        tokens.add(arqu)
    return {token for token in tokens if token}


def _fighter_weapon_family(fighter) -> str:
    arma = getattr(getattr(fighter, "dados", None), "arma_obj", None)
    return _norm(getattr(arma, "familia", "") or "lamina")


def _fighter_skill_markers(fighter) -> set[str]:
    markers = set()
    strategy = getattr(getattr(fighter, "brain", None), "skill_strategy", None)
    role = getattr(getattr(strategy, "role_principal", None), "value", "")
    if role:
        markers.add(_norm(role))
    return markers


def inferir_papel_tatico(fighter) -> dict:
    packages = load_tactical_packages().get("papeis", [])
    if not packages:
        return {"papel_id": "bruiser", "confidence": 0.0, "score": 0.0}

    traits = _fighter_traits(fighter)
    archetypes = _fighter_archetypes(fighter)
    family = _fighter_weapon_family(fighter)
    skill_markers = _fighter_skill_markers(fighter)

    best = None
    second_score = 0.0
    second_role = ""
    score_map = {}

    for papel in packages:
        score = 0.0
        if family in {_norm(v) for v in papel.get("familias_arma_preferidas", [])}:
            score += 2.4

        for token in papel.get("arquetipos_prioritarios", []):
            norm_token = _norm(token)
            if norm_token in archetypes:
                score += 1.8
            elif any(norm_token in entry for entry in archetypes):
                score += 1.1

        for traco in papel.get("tracos_prioritarios", []):
            if _norm(traco) in traits:
                score += 0.95

        papel_id = _norm(papel.get("id", ""))
        if papel_id == "curandeiro" and {"buffer", "battle_mage"} & skill_markers:
            score += 0.5
        if papel_id in {"controlador_de_area", "suporte_controle"} and {"control_mage", "trap_master", "summoner"} & skill_markers:
            score += 0.6
        if papel_id == "limpador_de_horda" and {"artillery", "summoner", "control_mage"} & skill_markers:
            score += 0.6
        if papel_id == "assassino" and {"dasher", "burst_mage"} & skill_markers:
            score += 0.45

        score_map[papel_id] = round(score, 3)
        if best is None or score > best["score"]:
            if best is not None:
                second_score = best["score"]
                second_role = PACKAGE_TO_TEAM_ROLE.get(_norm(best["papel_id"]), "STRIKER")
            best = {
                "papel_id": papel.get("id", "bruiser"),
                "nome": papel.get("nome", papel.get("id", "Bruiser")),
                "score": score,
                "forte_em": list(papel.get("forte_em", [])),
                "fraco_em": list(papel.get("fraco_em", [])),
                "familia_arma": family,
            }
        else:
            second_score = max(second_score, score)
            if score >= second_score:
                second_role = PACKAGE_TO_TEAM_ROLE.get(_norm(papel.get("id", "")), "STRIKER")

    if best is None:
        return {"papel_id": "bruiser", "confidence": 0.0, "score": 0.0}

    best_role = PACKAGE_TO_TEAM_ROLE.get(_norm(best["papel_id"]), "STRIKER")
    confidence = 1.0 if best["score"] <= 0 else max(0.15, min(1.0, (best["score"] - second_score + 1.0) / (best["score"] + 1.0)))
    if second_role and second_role == best_role:
        confidence = min(1.0, confidence + 0.08)
    best["confidence"] = round(confidence, 3)
    best["score_map"] = score_map
    best["team_role"] = best_role
    return best


def summarize_package_counts(fighters) -> Counter:
    counts = Counter()
    for fighter in fighters:
        if getattr(fighter, "morto", False):
            continue
        counts[inferir_papel_tatico(fighter).get("papel_id", "bruiser")] += 1
    return counts
