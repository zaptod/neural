"""
Sistema principal de videos "Roleta de Status".

Fluxo:
1. Gancho baseado em comentario
2. Rolagens em ordem fixa
3. Resumo da build
4. Oponente final
5. Luta na engine existente
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Any

from pipeline_video.character_generator import gerar_cor_harmonica


DEFAULT_COMMENTS = [
    "Eu serei Deus de outro mundo",
    "Me transforma no personagem mais roubado do isekai",
    "Quero nascer quebrado e sem piedade",
    "Monta minha build lendaria para esmagar geral",
    "Se eu reencarnasse agora, eu seria o mais absurdo",
]


_CATEGORY_DEFS = [
    {
        "key": "raca",
        "label": "RACA",
        "options": [
            {"nome": "Hibrido Celestial", "tier": "god", "tema": "celestial"},
            {"nome": "Alien Predatorio", "tier": "high", "tema": "cosmico"},
            {"nome": "Demonio de Guerra", "tier": "high", "tema": "infernal"},
            {"nome": "Humano Abençoado", "tier": "mid", "tema": "heroico"},
            {"nome": "Dragao Ancestral", "tier": "god", "tema": "draconico"},
            {"nome": "Aberracao do Vazio", "tier": "god", "tema": "vazio"},
        ],
    },
    {
        "key": "titulo",
        "label": "TITULO",
        "options": [
            {"nome": "O Conquistador de Mundos", "tier": "god", "tema": "imperio"},
            {"nome": "A Voz do Apocalipse", "tier": "high", "tema": "cataclismo"},
            {"nome": "O Santo da Carnificina", "tier": "high", "tema": "fanatico"},
            {"nome": "O Ultimo Monarca", "tier": "mid", "tema": "nobre"},
            {"nome": "O Andarilho Sem Nome", "tier": "low", "tema": "tragico"},
            {"nome": "A Coroa do Vazio", "tier": "god", "tema": "vazio"},
        ],
    },
    {
        "key": "base",
        "label": "REENCARNACAO",
        "options": [
            {"nome": "Minato", "tier": "high", "tema": "flash"},
            {"nome": "Gojo", "tier": "god", "tema": "arcano"},
            {"nome": "Toji", "tier": "high", "tema": "assassino"},
            {"nome": "Aizen", "tier": "god", "tema": "controle"},
            {"nome": "Sung Jin-Woo", "tier": "god", "tema": "sombras"},
            {"nome": "Cid Kagenou", "tier": "mid", "tema": "edgelord"},
        ],
    },
    {
        "key": "qi",
        "label": "Q.I.",
        "options": [
            {"nome": "Genialidade Monstruosa", "tier": "god", "tema": "mente"},
            {"nome": "Genio de Guerra", "tier": "high", "tema": "tatica"},
            {"nome": "Acima da Media", "tier": "mid", "tema": "ok"},
            {"nome": "Instinto Puro", "tier": "mid", "tema": "feral"},
            {"nome": "Normal", "tier": "low", "tema": "basico"},
            {"nome": "Cerebro em Curto", "tier": "low", "tema": "meme"},
        ],
    },
    {
        "key": "forca",
        "label": "FORCA",
        "options": [
            {"nome": "Acima da Media", "tier": "mid", "tema": "forte"},
            {"nome": "Monstruosa", "tier": "high", "tema": "brutal"},
            {"nome": "Nivel Kaiju", "tier": "god", "tema": "gigante"},
            {"nome": "Forca Divina", "tier": "god", "tema": "celestial"},
            {"nome": "Normal", "tier": "low", "tema": "fraco"},
        ],
    },
    {
        "key": "velocidade",
        "label": "VELOCIDADE",
        "options": [
            {"nome": "Gogeta", "tier": "god", "tema": "flash"},
            {"nome": "Relampago Negro", "tier": "high", "tema": "raio"},
            {"nome": "Quase Invisivel", "tier": "high", "tema": "sombra"},
            {"nome": "Acima da Media", "tier": "mid", "tema": "rapido"},
            {"nome": "Pesado Demais", "tier": "low", "tema": "lento"},
        ],
    },
    {
        "key": "combate",
        "label": "COMBATE",
        "options": [
            {"nome": "Kaido", "tier": "god", "tema": "dominante"},
            {"nome": "Mestre de Arena", "tier": "high", "tema": "duelo"},
            {"nome": "Assassino Cirurgico", "tier": "high", "tema": "letal"},
            {"nome": "Soldado Experiente", "tier": "mid", "tema": "disciplinado"},
            {"nome": "Briguento de Rua", "tier": "low", "tema": "caotico"},
        ],
    },
    {
        "key": "poderes",
        "label": "PODERES",
        "options": [
            {
                "nome": "3 poderes: Gravidade, Clones e Seis Olhos",
                "tier": "god",
                "tema": "arcano",
                "elemento": "vazio",
                "poderes": ["Manipulacao de Gravidade", "Criar Clones", "Os Seis Olhos"],
            },
            {
                "nome": "2 poderes: Chamas Draconicas e Regeneracao",
                "tier": "high",
                "tema": "fogo",
                "elemento": "fogo",
                "poderes": ["Chamas Draconicas", "Regeneracao Selvagem"],
            },
            {
                "nome": "4 poderes: Gelo, Raios, Portais e Metamorfose",
                "tier": "god",
                "tema": "tempestade",
                "elemento": "raio",
                "poderes": ["Gelo Absoluto", "Raios Vivos", "Abrir Portais", "Metamorfose"],
            },
            {
                "nome": "1 poder: Soco Muito Honesto",
                "tier": "low",
                "tema": "meme",
                "elemento": "terra",
                "poderes": ["Soco Muito Honesto"],
            },
            {
                "nome": "2 poderes: Sombras e Invocacoes",
                "tier": "high",
                "tema": "sombras",
                "elemento": "trevas",
                "poderes": ["Manto de Sombras", "Invocacao de Servos"],
            },
        ],
    },
    {
        "key": "armas",
        "label": "ARMAS",
        "options": [
            {"nome": "SIM: Arsenal Lendario", "tier": "high", "tema": "armado", "usa_arma": True},
            {"nome": "SIM: Arma Unica Quebrada", "tier": "god", "tema": "artefato", "usa_arma": True},
            {"nome": "NAO: So Punhos e Aura", "tier": "mid", "tema": "desarmado", "usa_arma": False},
            {"nome": "NAO: Magia de Curto Alcance", "tier": "mid", "tema": "focus", "usa_arma": False},
        ],
    },
]


_OPONENTES_FINAIS = [
    {"nome": "Absoluto Cinema", "tema": "lendario", "tier": "god"},
    {"nome": "O Juiz do Multiverso", "tema": "cosmico", "tier": "god"},
    {"nome": "A Besta do Fim", "tema": "cataclismo", "tier": "high"},
    {"nome": "A Execucao Perfeita", "tema": "tecnico", "tier": "high"},
    {"nome": "O Rei da Arena", "tema": "arena", "tier": "mid"},
]


_TIER_REACTIONS = {
    "god": ("ABSURDO", "Parece chefe final de anime."),
    "high": ("PESADO", "Ja entrou quebrado na rodada."),
    "mid": ("SOLIDO", "Build boa, mas ainda precisa provar."),
    "low": ("COMPLICOU", "Isso aqui pode virar meme."),
}


_THEME_REACTIONS = {
    "meme": ("AZEDOU", "A roleta trollou bonito."),
    "vazio": ("AMEACADOR", "Tem cara de poder proibido."),
    "arcano": ("INSANO", "Esse pacote veio quebrado."),
    "fogo": ("CAOTICO", "Energia de boss agressivo."),
    "sombras": ("SOMBRIO", "Silent killer total."),
    "flash": ("FLASH", "Piscou, sumiu da tela."),
    "dominante": ("MONSTRO", "Clima de dominio total."),
    "duelo": ("AFIADO", "Leitura e tecnica no maximo."),
    "desarmado": ("NA MAO", "Vai ter que resolver na brutalidade."),
}


_TIER_SCORE = {"low": 0.28, "mid": 0.55, "high": 0.78, "god": 0.96}


def _clean_text(value: str | None) -> str:
    text = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    return text.strip()


def _seed_from_comment(comment: str) -> int:
    digest = hashlib.sha256(comment.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _pick_comment(comment: str | None, fight_index: int = 0) -> str:
    cleaned = _clean_text(comment)
    if cleaned:
        return cleaned
    return DEFAULT_COMMENTS[fight_index % len(DEFAULT_COMMENTS)]


def _choose_option(rng: random.Random, category: dict[str, Any]) -> dict[str, Any]:
    options = list(category["options"])
    selected = dict(rng.choice(options))
    selected.setdefault("tier", "mid")
    selected.setdefault("tema", "ok")
    react = _THEME_REACTIONS.get(selected["tema"]) or _TIER_REACTIONS.get(selected["tier"], _TIER_REACTIONS["mid"])
    selected["reaction_label"] = react[0]
    selected["reaction_note"] = react[1]
    return selected


def _visible_options(rng: random.Random, category: dict[str, Any], selected_name: str) -> list[str]:
    pool = [opt["nome"] for opt in category["options"]]
    others = [name for name in pool if name != selected_name]
    rng.shuffle(others)
    visible = others[: min(4, len(others))]
    visible.append(selected_name)
    rng.shuffle(visible)
    return visible


def _resolve_element(build: dict[str, Any]) -> str:
    powers = build["results"]["poderes"]
    if powers.get("elemento"):
        return powers["elemento"]
    race_theme = build["results"]["raca"].get("tema")
    if race_theme in {"infernal", "draconico"}:
        return "fogo"
    if race_theme in {"vazio", "cosmico"}:
        return "vazio"
    if race_theme == "celestial":
        return "luz"
    return "arcano"


def _build_name(build: dict[str, Any]) -> str:
    base = build["results"]["base"]["nome"]
    titulo = build["results"]["titulo"]["nome"]
    suffix = titulo.replace("O ", "").replace("A ", "").replace("o ", "").replace("a ", "")
    return _clean_text(f"{base} {suffix}")


def _class_from_build(build: dict[str, Any]) -> str:
    race = build["results"]["raca"]["nome"]
    combat = build["results"]["combate"]["nome"]
    return f"{race} ({combat})"


def _personality_from_build(build: dict[str, Any]) -> str:
    qi = build["results"]["qi"]["tier"]
    combat = build["results"]["combate"]["tema"]
    if qi == "god":
        return "Calculista"
    if combat in {"dominante", "cataclismo"}:
        return "Berserker"
    if combat == "duelo":
        return "Tecnico"
    return "Determinado"


def _theme_color(elemento: str, rng: random.Random) -> tuple[int, int, int]:
    palettes = {
        "fogo": (255, 112, 72),
        "gelo": (122, 216, 255),
        "raio": (255, 222, 84),
        "trevas": (154, 118, 255),
        "luz": (255, 238, 162),
        "vazio": (186, 112, 255),
        "terra": (182, 154, 108),
        "arcano": (106, 192, 255),
    }
    base = palettes.get(elemento, gerar_cor_harmonica())
    return tuple(max(36, min(255, int(channel + rng.randint(-14, 14)))) for channel in base)


def _weapon_from_build(build: dict[str, Any], rng: random.Random, color: tuple[int, int, int]) -> dict[str, Any]:
    armas = build["results"]["armas"]
    combate = build["results"]["combate"]
    velocidade = build["results"]["velocidade"]
    elemento = _resolve_element(build)
    powers = build["results"]["poderes"].get("poderes", [])
    uses_weapon = bool(armas.get("usa_arma"))

    if not uses_weapon:
        return {
            "nome": "Foco Primordial",
            "tipo": "Magica",
            "familia": "foco",
            "dano": 8.8,
            "peso": 2.4,
            "velocidade_ataque": 1.18,
            "raridade": "Lendario",
            "r": color[0],
            "g": color[1],
            "b": color[2],
            "estilo": "Arcano",
            "habilidades": [{"nome": power, "custo": 18.0} for power in powers[:2]],
            "habilidade": powers[0] if powers else "Descarga Arcana",
            "custo_mana": 18.0,
            "afinidade_elemento": elemento.upper(),
        }

    if velocidade["tier"] == "god":
        tipo = "Dupla"
        familia = "dupla"
        nome = "Laminas do Flash"
    elif combate["tema"] in {"dominante", "cataclismo"}:
        tipo = "Corrente"
        familia = "corrente"
        nome = "Grilhão do Cataclismo"
    elif powers and elemento in {"vazio", "arcano", "trevas", "luz"}:
        tipo = "Transformavel"
        familia = "hibrida"
        nome = "Relicario Mutante"
    else:
        tipo = "Reta"
        familia = "lamina"
        nome = "Lamina do Destino"

    return {
        "nome": nome,
        "tipo": tipo,
        "familia": familia,
        "dano": 9.4 if build["power_score"] >= 0.8 else 8.2,
        "peso": 3.2 if tipo != "Corrente" else 4.3,
        "velocidade_ataque": 1.22 if velocidade["tier"] in {"god", "high"} else 0.98,
        "raridade": "Mitico" if build["power_score"] >= 0.86 else "Lendario",
        "r": color[0],
        "g": color[1],
        "b": color[2],
        "estilo": "Misto",
        "habilidades": [{"nome": power, "custo": 20.0} for power in powers[:2]],
        "habilidade": powers[0] if powers else "Golpe Supremo",
        "custo_mana": 20.0,
        "afinidade_elemento": elemento.upper(),
    }


def _fighter_from_build(build: dict[str, Any], rng: random.Random) -> tuple[dict[str, Any], dict[str, Any]]:
    elemento = _resolve_element(build)
    color = _theme_color(elemento, rng)
    forca_score = _TIER_SCORE.get(build["results"]["forca"]["tier"], 0.55)
    qi_score = _TIER_SCORE.get(build["results"]["qi"]["tier"], 0.55)
    speed_score = _TIER_SCORE.get(build["results"]["velocidade"]["tier"], 0.55)
    power_score = build["power_score"]

    weapon = _weapon_from_build(build, rng, color)
    char = {
        "nome": _build_name(build),
        "tamanho": round(1.65 + (forca_score - 0.5) * 0.55, 2),
        "forca": round(4.5 + forca_score * 5.2, 1),
        "mana": round(4.0 + max(qi_score, power_score) * 5.4, 1),
        "nome_arma": weapon["nome"],
        "cor_r": color[0],
        "cor_g": color[1],
        "cor_b": color[2],
        "classe": _class_from_build(build),
        "personalidade": _personality_from_build(build),
        "comentario_hook": build["comment"],
        "velocidade_roleta": speed_score,
        "titulo_roleta": build["results"]["titulo"]["nome"],
    }
    return char, weapon


def _opponent_weapon_for_theme(theme: str, color: tuple[int, int, int]) -> dict[str, Any]:
    mapping = {
        "lendario": ("Transformavel", "hibrida", "Lamina de Cinema"),
        "cosmico": ("Magica", "foco", "Cetro do Juizo"),
        "cataclismo": ("Corrente", "corrente", "Meteora Terminal"),
        "tecnico": ("Dupla", "dupla", "Par de Facas Perfeitas"),
        "arena": ("Reta", "lamina", "Espada do Rei"),
    }
    tipo, familia, nome = mapping.get(theme, ("Reta", "lamina", "Lamina Rival"))
    return {
        "nome": nome,
        "tipo": tipo,
        "familia": familia,
        "dano": 8.8,
        "peso": 3.4,
        "velocidade_ataque": 1.05,
        "raridade": "Lendario",
        "r": color[0],
        "g": color[1],
        "b": color[2],
        "estilo": "Misto",
        "habilidade": "Golpe de Resposta",
        "custo_mana": 12.0,
    }


def _opponent_from_story(story: dict[str, Any], rng: random.Random) -> tuple[dict[str, Any], dict[str, Any]]:
    final_enemy = dict(rng.choice(_OPONENTES_FINAIS))
    color = _theme_color("vazio" if final_enemy["tema"] == "cosmico" else "fogo", rng)
    weapon = _opponent_weapon_for_theme(final_enemy["tema"], color)
    char = {
        "nome": final_enemy["nome"],
        "tamanho": 1.9,
        "forca": round(8.0 + rng.uniform(0.4, 1.8), 1),
        "mana": round(7.8 + rng.uniform(0.2, 1.5), 1),
        "nome_arma": weapon["nome"],
        "cor_r": color[0],
        "cor_g": color[1],
        "cor_b": color[2],
        "classe": f"Chefe Final ({final_enemy['tema'].title()})",
        "personalidade": "Predador",
    }
    story["opponent"] = final_enemy
    return char, weapon


def construir_timeline_roleta(story: dict[str, Any]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    cursor = 0.0

    def add_segment(kind: str, duration: float, payload: dict[str, Any] | None = None):
        nonlocal cursor
        timeline.append(
            {
                "kind": kind,
                "start": cursor,
                "end": cursor + duration,
                "duration": duration,
                "payload": payload or {},
            }
        )
        cursor += duration

    add_segment("hook", 1.25, {"comment": story["comment"], "hook": story["hook"]})
    for roll in story["rolls"]:
        add_segment("roulette_spin", 0.55, {"roll": roll})
        add_segment("roulette_result", 0.34, {"roll": roll})
        add_segment("roulette_reaction", 0.46, {"roll": roll})
    add_segment("build_summary", 1.45, {"story": story})
    add_segment("versus_reveal", 1.10, {"story": story})
    story["timeline_duration"] = round(cursor, 3)
    return timeline


def gerar_story_roleta_status(comment: str | None = None, *, fight_index: int = 0) -> dict[str, Any]:
    comment_text = _pick_comment(comment, fight_index=fight_index)
    seed = _seed_from_comment(f"{fight_index}:{comment_text}")
    rng = random.Random(seed)

    results: dict[str, dict[str, Any]] = {}
    rolls: list[dict[str, Any]] = []
    total_score = 0.0

    for category in _CATEGORY_DEFS:
        selected = _choose_option(rng, category)
        results[category["key"]] = selected
        total_score += _TIER_SCORE.get(selected["tier"], 0.55)
        rolls.append(
            {
                "key": category["key"],
                "label": category["label"],
                "selected": selected["nome"],
                "tier": selected["tier"],
                "theme": selected["tema"],
                "reaction_label": selected["reaction_label"],
                "reaction_note": selected["reaction_note"],
                "visible_options": _visible_options(rng, category, selected["nome"]),
            }
        )

    story = {
        "mode": "roleta_status",
        "comment": comment_text,
        "hook": f'Respondendo ao comentario: "{comment_text}"',
        "seed": seed,
        "rolls": rolls,
        "results": results,
        "power_score": round(total_score / max(1, len(_CATEGORY_DEFS)), 3),
    }

    fighter1, weapon1 = _fighter_from_build(story, rng)
    fighter2, weapon2 = _opponent_from_story(story, rng)
    story["fighter1"] = fighter1
    story["weapon1"] = weapon1
    story["fighter2"] = fighter2
    story["weapon2"] = weapon2
    story["hero_name"] = fighter1["nome"]
    story["enemy_name"] = fighter2["nome"]
    story["build_lines"] = [f"{roll['label']}: {roll['selected']}" for roll in rolls]
    story["timeline"] = construir_timeline_roleta(story)
    return story


def get_story_segment(story: dict[str, Any], story_time: float) -> dict[str, Any] | None:
    for segment in story.get("timeline", []):
        if segment["start"] <= story_time < segment["end"]:
            return segment
    return story.get("timeline", [])[-1] if story.get("timeline") else None


def slugify_comment(comment: str) -> str:
    cleaned = _clean_text(comment).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")[:48] or "comentario"
