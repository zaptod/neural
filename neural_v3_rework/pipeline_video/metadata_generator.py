"""
Metadata generator para as copias de video das plataformas sociais.
"""

from __future__ import annotations

import random
import re
import unicodedata

from pipeline_video.config import PLATFORMS


_MOJIBAKE_TOKENS = (
    "\u00c3",
    "\u00c2",
    "\u00f0",
    "\u00ef",
    "\u00e2\u20ac",
    "\u00e2\u02c6",
    "\ufffd",
)

_TITLE_TEMPLATES = {
    "reels": [
        "{n1} vs {n2}: quem domina a arena?",
        "Duelo de IA: {n1} contra {n2}",
        "{n1} x {n2}: combate sem roteiro",
        "Arena aberta: {n1} vs {n2}",
    ],
    "tiktok": [
        "{n1} vs {n2}: quem leva essa?",
        "IA vs IA: {n1} contra {n2}",
        "{n1} x {n2}: luta imprevisivel",
        "{n1} vs {n2}: quem sobrevive?",
    ],
    "shorts": [
        "{n1} vs {n2}: assista ate o fim",
        "{n1} x {n2}: so um sai de pe",
        "{n1} contra {n2}: o final decide tudo",
        "{n1} vs {n2}: duelo rapido e brutal",
    ],
}

_DESCRIPTION_TEMPLATES = {
    "reels": [
        "A arena abriu para {n1} ({c1}) e {n2} ({c2}).\nIA contra IA, leitura tatica e resultado sem roteiro.",
        "{n1} ({c1}) entrou para pressionar. {n2} ({c2}) entrou para responder.\nTudo aqui e decidido pela IA, em tempo real.",
        "Dois estilos, duas builds e nenhuma coreografia combinada:\n{n1} ({c1}) vs {n2} ({c2}).",
    ],
    "tiktok": [
        "{n1} ({c1}) vs {n2} ({c2}).\nOs dois sao controlados pela IA e o resultado muda toda luta.",
        "Sem script, sem player humano:\n{n1} ({c1}) contra {n2} ({c2}).",
        "{n1} ({c1}) entrou na arena para enfrentar {n2} ({c2}).\nA IA controla os dois lados.",
    ],
    "shorts": [
        "{n1} ({c1}) enfrenta {n2} ({c2}) em uma luta gerada por IA.\nAssista ate o fim para ver quem fecha a arena.",
        "{n1} ({c1}) e {n2} ({c2}) se encontram em um duelo curto e brutal.\nO final muda rapido.",
        "Dois lutadores, uma arena e IA nos dois controles:\n{n1} ({c1}) vs {n2} ({c2}).",
    ],
}

_CTA_TEMPLATES = {
    "reels": [
        "Comente o nome do seu lutador para entrar na arena.",
        "Se fosse o seu campeao, voce colocaria quem nessa luta?",
        "Escolhe um lado nos comentarios e monta a proxima batalha.",
    ],
    "tiktok": [
        "Comenta quem vence a proxima e eu boto na arena.",
        "Escolhe um lutador nos comentarios para a proxima luta.",
        "Se esse combate fosse seu, em quem voce apostava?",
    ],
    "shorts": [
        "Comente qual lutador voce quer ver no proximo duelo.",
        "Escolha o proximo desafiante nos comentarios.",
        "Se quiser outra luta, deixa o nome do seu campeao.",
    ],
}

_HASHTAGS_BASE = [
    "#NeuralFights",
    "#LutaIA",
    "#AIFight",
    "#BatalhaEpica",
    "#pvp",
    "#versus",
    "#combate",
    "#gaming",
    "#gamedev",
    "#indiegame",
    "#python",
    "#pygame",
]

_PLATFORM_HASHTAGS = {
    "reels": ["#reels", "#reelsinstagram", "#reelsviral", "#viral"],
    "tiktok": ["#tiktok", "#fyp", "#foryou", "#foryoupage", "#fy"],
    "shorts": ["#shorts", "#youtubeshorts", "#short"],
}

_COPY_RULES = {
    "reels": {
        "nome": "INSTAGRAM REELS",
        "title_max": 90,
        "description_max": 2200,
        "hashtags_max": 24,
        "caption_label": "LEGENDA",
    },
    "tiktok": {
        "nome": "TIKTOK",
        "title_max": 100,
        "description_max": 2200,
        "hashtags_max": 15,
        "caption_label": "CAPTION",
    },
    "shorts": {
        "nome": "YOUTUBE SHORTS",
        "title_max": 100,
        "description_max": 5000,
        "hashtags_max": 15,
        "caption_label": "DESCRICAO",
    },
}


def _looks_broken(text: str) -> bool:
    return any(token in text for token in _MOJIBAKE_TOKENS)


def _repair_mojibake(text: str) -> str:
    if not text or not _looks_broken(text):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    original_score = sum(text.count(token) for token in _MOJIBAKE_TOKENS)
    repaired_score = sum(repaired.count(token) for token in _MOJIBAKE_TOKENS)
    return repaired if repaired_score < original_score else text


def _clean_text(text: str | None) -> str:
    value = _repair_mojibake(str(text or ""))
    value = value.replace("\r\n", "\n")
    lines = [" ".join(line.split()) for line in value.split("\n")]
    value = "\n".join(lines)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _normalize_platform(platform: str | None) -> str:
    candidate = _clean_text(platform or "reels").lower()
    return candidate if candidate in _COPY_RULES else "reels"


def _slug_hashtag(text: str) -> str:
    cleaned = _clean_text(text).split("(")[0].strip()
    normalized = unicodedata.normalize("NFKD", cleaned)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^A-Za-z0-9]+", "", normalized)
    return normalized


def _truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    cut = text[: max_len - 3]
    last_space = cut.rfind(" ")
    if last_space > int(max_len * 0.6):
        cut = cut[:last_space]
    return cut.rstrip() + "..."


def _build_title(nome1: str, nome2: str, platform: str) -> str:
    template = random.choice(_TITLE_TEMPLATES[platform])
    return _clean_text(template.format(n1=nome1, n2=nome2))


def _build_description(nome1: str, nome2: str, classe1: str, classe2: str, vencedor: str | None, platform: str) -> str:
    opener = random.choice(_DESCRIPTION_TEMPLATES[platform]).format(
        n1=nome1,
        n2=nome2,
        c1=classe1,
        c2=classe2,
    )
    cta = random.choice(_CTA_TEMPLATES[platform])
    blocks = [_clean_text(opener), _clean_text(cta)]
    if vencedor:
        blocks.append(f"Vencedor: {_clean_text(vencedor)}")
    return "\n\n".join(blocks)


def _build_hashtags(classe1: str, classe2: str, platform: str) -> list[str]:
    rules = _COPY_RULES[platform]
    class_tags = []
    for classe in (classe1, classe2):
        slug = _slug_hashtag(classe)
        if slug:
            class_tags.append(f"#{slug}")

    tags = list(_PLATFORM_HASHTAGS.get(platform, []))
    tags.extend(class_tags)
    tags.extend(_HASHTAGS_BASE)

    dedup: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(tag)

    return dedup[: rules["hashtags_max"]]


def generate_metadata(
    nome1: str,
    nome2: str,
    classe1: str,
    classe2: str,
    vencedor: str | None = None,
    platform: str = "reels",
) -> dict:
    """
    Gera metadados completos para um video de luta.
    """
    p = _normalize_platform(platform)
    clean_nome1 = _clean_text(nome1)
    clean_nome2 = _clean_text(nome2)
    clean_classe1 = _clean_text(classe1)
    clean_classe2 = _clean_text(classe2)
    clean_vencedor = _clean_text(vencedor) if vencedor else None

    rules = _COPY_RULES[p]
    title = _truncate_text(_build_title(clean_nome1, clean_nome2, p), rules["title_max"])
    description = _truncate_text(
        _build_description(clean_nome1, clean_nome2, clean_classe1, clean_classe2, clean_vencedor, p),
        rules["description_max"],
    )
    hashtags = _build_hashtags(clean_classe1, clean_classe2, p)

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "tags_str": " ".join(hashtags),
        "platform": p,
        "fighter1": clean_nome1,
        "fighter2": clean_nome2,
        "winner": clean_vencedor,
    }


def generate_all_platforms(
    nome1: str,
    nome2: str,
    classe1: str,
    classe2: str,
    vencedor: str | None = None,
) -> dict:
    return {
        platform: generate_metadata(nome1, nome2, classe1, classe2, vencedor, platform)
        for platform in PLATFORMS
    }


def generate_encounter_metadata(
    side_a: str,
    side_b: str,
    *,
    mode: str = "equipes",
    winner: str | None = None,
    platform: str = "reels",
) -> dict:
    mode_label = {
        "equipes": "Batalha em Equipe",
        "horda": "Modo Horda",
    }.get(str(mode or "").lower(), "Combate Especial")
    title = f"{side_a} vs {side_b}: {mode_label}"
    description = (
        f"{mode_label} em Neural Fights.\n"
        f"{side_a} enfrenta {side_b} usando a simulacao principal.\n\n"
        f"{'Vencedor: ' + _clean_text(winner) if winner else 'Resultado em aberto ate o fim.'}"
    )
    hashtags = _build_hashtags(mode_label, side_b, _normalize_platform(platform))
    return {
        "title": _truncate_text(_clean_text(title), _COPY_RULES[_normalize_platform(platform)]["title_max"]),
        "description": _truncate_text(_clean_text(description), _COPY_RULES[_normalize_platform(platform)]["description_max"]),
        "hashtags": hashtags,
        "tags_str": " ".join(hashtags),
        "platform": _normalize_platform(platform),
        "fighter1": _clean_text(side_a),
        "fighter2": _clean_text(side_b),
        "winner": _clean_text(winner) if winner else None,
        "mode": str(mode),
    }


def generate_encounter_all_platforms(side_a: str, side_b: str, *, mode: str, winner: str | None = None) -> dict:
    return {
        platform: generate_encounter_metadata(side_a, side_b, mode=mode, winner=winner, platform=platform)
        for platform in PLATFORMS
    }


def generate_story_metadata(story: dict, vencedor: str | None = None, platform: str = "reels") -> dict:
    """
    Gera copy para o formato principal de comentario + roleta + versus.
    """
    p = _normalize_platform(platform)
    rules = _COPY_RULES[p]
    comment = _clean_text(story.get("comment"))
    hero = _clean_text(story.get("hero_name") or story.get("fighter1", {}).get("nome"))
    enemy = _clean_text(story.get("enemy_name") or story.get("fighter2", {}).get("nome"))
    race = _clean_text(story.get("results", {}).get("raca", {}).get("nome"))
    title = _clean_text(story.get("results", {}).get("titulo", {}).get("nome"))
    powers = _clean_text(story.get("results", {}).get("poderes", {}).get("nome"))
    winner = _clean_text(vencedor) if vencedor else None

    title_templates = {
        "reels": f'Respondi "{comment}" e saiu {hero} contra {enemy}',
        "tiktok": f'Comentaram "{comment}" e a roleta montou {hero}',
        "shorts": f'Roleta de status: {hero} vs {enemy}',
    }
    description = (
        f'Comentario escolhido: "{comment}"\n'
        f"Build final: {hero} | {race} | {title}\n"
        f"Poderes: {powers}\n"
        f"Oponente final: {enemy}\n\n"
        "Comenta a proxima ideia que eu monto outra build e jogo na arena."
    )
    if winner:
        description += f"\n\nVencedor: {winner}"

    hashtags = [
        "#RoletaDeStatus",
        "#ComentandoBuilds",
        "#NeuralFights",
        "#LutaIA",
        "#AIFight",
        "#versus",
        "#gaming",
        "#gamedev",
        "#anime",
        "#isekai",
    ]
    platform_tags = _PLATFORM_HASHTAGS.get(p, [])
    tags = []
    seen = set()
    for tag in platform_tags + hashtags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(tag)

    return {
        "title": _truncate_text(title_templates[p], rules["title_max"]),
        "description": _truncate_text(description, rules["description_max"]),
        "hashtags": tags[: rules["hashtags_max"]],
        "tags_str": " ".join(tags[: rules["hashtags_max"]]),
        "platform": p,
        "fighter1": hero,
        "fighter2": enemy,
        "winner": winner,
    }


def generate_story_all_platforms(story: dict, vencedor: str | None = None) -> dict:
    return {platform: generate_story_metadata(story, vencedor=vencedor, platform=platform) for platform in PLATFORMS}


def _normalize_hashtags(meta: dict, platform: str) -> tuple[list[str], str]:
    rules = _COPY_RULES.get(platform, _COPY_RULES["reels"])
    tags = list(meta.get("hashtags", []))
    if not tags and meta.get("tags_str"):
        tags = [token for token in _clean_text(meta.get("tags_str")).split() if token.startswith("#")]

    dedup: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        current = _clean_text(tag)
        if not current:
            continue
        if not current.startswith("#"):
            current = "#" + current
        key = current.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(current)

    dedup = dedup[: rules["hashtags_max"]]
    return dedup, " ".join(dedup)


def format_metadata_plain_text(meta: dict) -> str:
    platform = _normalize_platform(meta.get("platform"))
    title = _clean_text(meta.get("title"))
    description = _clean_text(meta.get("description"))
    _, tags_str = _normalize_hashtags(meta, platform)

    return (
        f"PLATAFORMA: {platform.upper()}\n\n"
        f"TITULO:\n{title}\n\n"
        f"DESCRICAO:\n{description}\n\n"
        f"HASHTAGS:\n{tags_str}\n"
    )


def format_metadata_copy_text(meta: dict, platform: str | None = None) -> str:
    p = _normalize_platform(platform or meta.get("platform"))
    rules = _COPY_RULES[p]

    title = _truncate_text(_clean_text(meta.get("title")), rules["title_max"])
    description = _truncate_text(_clean_text(meta.get("description")), rules["description_max"])
    tags_list, tags_str = _normalize_hashtags(meta, p)
    caption_full = description if not tags_str else f"{description}\n\n{tags_str}"
    hashtags_block = tags_str if tags_list else "(sem hashtags)"

    return (
        f"=== {rules['nome']} ===\n\n"
        f"TITULO (copiar):\n{title}\n\n"
        f"{rules['caption_label']} (copiar):\n{caption_full}\n\n"
        f"HASHTAGS (copiar):\n{hashtags_block}\n\n"
        f"POST COMPLETO (copiar):\n{caption_full}\n"
    )


def format_all_platform_copies(all_meta: dict) -> str:
    ordered = ["reels", "tiktok", "shorts"]
    blocks = []
    for platform in ordered:
        meta = all_meta.get(platform)
        if meta:
            blocks.append(format_metadata_copy_text(meta, platform=platform))
    return "\n" + ("\n" + "-" * 70 + "\n\n").join(blocks).strip() + "\n"
