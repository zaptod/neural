"""
Metadata Generator — Gera título, descrição e hashtags para cada luta/plataforma.
"""
import random
from typing import Tuple

from video_pipeline.config import PLATFORMS


# Templates de título (com slots para nomes)
_TITLE_TEMPLATES = [
    "⚔️ {n1} vs {n2} — Quem vence?",
    "🔥 {n1} × {n2} | LUTA ÉPICA",
    "💀 {n1} contra {n2} — Batalha brutal!",
    "⚡ {n1} vs {n2} | Quem sobrevive?",
    "🗡️ {n1} × {n2} — RESULTADO INSANO",
    "👊 {n1} desafia {n2} — ASSISTA ATÉ O FIM",
    "🏆 {n1} vs {n2} | O MAIS FORTE VENCE",
    "💥 {n1} × {n2} — Combate até a morte!",
]

_HASHTAGS_BASE = [
    "#NeuralFights", "#LutaIA", "#AIFight", "#BatalhaEpica",
    "#fights", "#versus", "#pvp", "#combate", "#gaming",
    "#gamedev", "#indiegame", "#python", "#pygame",
]

_HASHTAGS_REELS = ["#reels", "#reelsinstagram", "#reelsviral", "#viral"]
_HASHTAGS_TIKTOK = ["#tiktok", "#fyp", "#foryou", "#foryoupage", "#fy"]
_HASHTAGS_SHORTS = ["#shorts", "#youtubeshorts", "#short"]

_PLATFORM_HASHTAGS = {
    "reels": _HASHTAGS_REELS,
    "tiktok": _HASHTAGS_TIKTOK,
    "shorts": _HASHTAGS_SHORTS,
}

_COPY_RULES = {
    "reels": {
        "nome": "INSTAGRAM REELS",
        "title_max": 90,
        "description_max": 2200,
        "hashtags_max": 30,
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

_DESCRIPTION_TEMPLATES = [
    "🤖 Luta gerada por IA! {n1} ({c1}) contra {n2} ({c2}) na arena.\n"
    "Quem você acha que vence? Comenta aí! 👇\n\n"
    "Comente o nome do seu lutador para entrar na arena! ⚔️",

    "💥 Batalha épica entre {n1} ({c1}) e {n2} ({c2})!\n"
    "Assista até o final para ver o resultado! 😱\n\n"
    "Quer lutar? Comente seu nome de guerreiro! 🗡️",

    "⚔️ {n1} ({c1}) vs {n2} ({c2}) — Quem é o mais forte?\n"
    "IA controla os dois lutadores, resultado imprevisível! 🔥\n\n"
    "Comente o nome do seu lutador para entrar na arena!",
]


def generate_metadata(nome1: str, nome2: str, classe1: str, classe2: str,
                      vencedor: str = None, platform: str = "reels") -> dict:
    """
    Gera metadados completos para um vídeo de luta.

    Returns:
        dict com keys: title, description, hashtags, tags_str
    """
    # Título
    title = random.choice(_TITLE_TEMPLATES).format(n1=nome1, n2=nome2)

    # Descrição
    desc = random.choice(_DESCRIPTION_TEMPLATES).format(
        n1=nome1, n2=nome2, c1=classe1, c2=classe2)
    if vencedor:
        desc += f"\n\n🏆 Vencedor: {vencedor}"

    # Hashtags: base + platform-specific + classes
    tags = list(_HASHTAGS_BASE)
    tags.extend(_PLATFORM_HASHTAGS.get(platform, []))

    # Adiciona classes como hashtag
    for c in [classe1, classe2]:
        tag = "#" + c.split("(")[0].strip().replace(" ", "")
        if tag not in tags:
            tags.append(tag)

    random.shuffle(tags)
    # Limita a 30 hashtags (limite do Instagram)
    tags = tags[:30]
    tags_str = " ".join(tags)

    return {
        "title": title,
        "description": desc,
        "hashtags": tags,
        "tags_str": tags_str,
        "platform": platform,
        "fighter1": nome1,
        "fighter2": nome2,
        "winner": vencedor,
    }


def generate_all_platforms(nome1: str, nome2: str, classe1: str, classe2: str,
                           vencedor: str = None) -> dict:
    """Gera metadados para todas as plataformas.

    Returns:
        dict com keys reels/tiktok/shorts, cada uma com metadata
    """
    return {
        platform: generate_metadata(nome1, nome2, classe1, classe2, vencedor, platform)
        for platform in PLATFORMS
    }


def format_metadata_plain_text(meta: dict) -> str:
    """Formata metadados em texto simples para copiar e colar facilmente."""
    platform = (meta.get("platform") or "").upper()
    title = meta.get("title", "")
    description = meta.get("description", "")
    tags_str = meta.get("tags_str", "")

    return (
        f"PLATAFORMA: {platform}\n\n"
        f"TITULO:\n{title}\n\n"
        f"DESCRICAO:\n{description}\n\n"
        f"HASHTAGS:\n{tags_str}\n"
    )


def _truncate_text(text: str, max_len: int) -> str:
    """Corta texto respeitando palavra final e adiciona reticências quando necessário."""
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    cut = text[:max_len - 3]
    last_space = cut.rfind(" ")
    if last_space > int(max_len * 0.6):
        cut = cut[:last_space]
    return cut.rstrip() + "..."


def _normalize_hashtags(meta: dict, platform: str) -> tuple[list[str], str]:
    """Normaliza hashtags para limite por plataforma."""
    rules = _COPY_RULES.get(platform, _COPY_RULES["reels"])
    tags = list(meta.get("hashtags", []))
    if not tags and meta.get("tags_str"):
        tags = [t for t in str(meta.get("tags_str", "")).split() if t.startswith("#")]

    dedup = []
    seen = set()
    for tag in tags:
        if not tag.startswith("#"):
            tag = "#" + tag
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(tag)

    dedup = dedup[:rules["hashtags_max"]]
    return dedup, " ".join(dedup)


def format_metadata_copy_text(meta: dict, platform: str = None) -> str:
    """Gera bloco pronto para copiar e colar, personalizado por plataforma."""
    p = (platform or meta.get("platform") or "reels").lower()
    rules = _COPY_RULES.get(p, _COPY_RULES["reels"])

    title = _truncate_text(str(meta.get("title", "")).strip(), rules["title_max"])
    description = _truncate_text(str(meta.get("description", "")).strip(), rules["description_max"])
    tags_list, tags_str = _normalize_hashtags(meta, p)

    if p == "shorts":
        # Shorts costuma funcionar melhor com hashtags no fim da descrição.
        caption_full = description
        if tags_str:
            caption_full = f"{description}\n\n{tags_str}"
    else:
        caption_full = description
        if tags_str:
            caption_full = f"{description}\n\n{tags_str}"

    return (
        f"=== {rules['nome']} ===\n\n"
        f"TITULO (copiar):\n{title}\n\n"
        f"{rules['caption_label']} (copiar):\n{caption_full}\n\n"
        f"HASHTAGS (copiar):\n{tags_str}\n\n"
        f"POST COMPLETO (copiar):\n{caption_full}\n"
    )


def format_all_platform_copies(all_meta: dict) -> str:
    """Concatena blocos de cópia para reels, tiktok e shorts em um único TXT."""
    ordered = ["reels", "tiktok", "shorts"]
    blocks = []
    for p in ordered:
        meta = all_meta.get(p)
        if not meta:
            continue
        blocks.append(format_metadata_copy_text(meta, platform=p))
    return "\n" + ("\n" + "-" * 70 + "\n\n").join(blocks).strip() + "\n"
