import random

from pipeline_video.metadata_generator import (
    format_all_platform_copies,
    format_metadata_copy_text,
    generate_all_platforms,
    generate_metadata,
)


_BROKEN_MARKERS = (
    "\u00c3",
    "\u00f0\u0178",
    "\u00e2\u20ac\u201d",
    "\u00e2\u0161",
    "\u00ef\u00b8",
    "\u00c2",
    "\ufffd",
)


def _assert_clean_text(text: str):
    assert not any(marker in text for marker in _BROKEN_MARKERS)


def test_generate_metadata_repairs_mojibake_inputs():
    random.seed(7)
    broken_name = "Riven a L\u00c3\u00a2mina"
    fixed_name = "Riven a L\u00e2mina"
    meta = generate_metadata(
        broken_name,
        "Fiora a Noturna",
        "Mago (Arcano)",
        "Monge (Chi)",
        vencedor=broken_name,
        platform="reels",
    )

    _assert_clean_text(meta["title"])
    _assert_clean_text(meta["description"])
    assert meta["fighter1"] == fixed_name
    assert f"Vencedor: {fixed_name}" in meta["description"]


def test_tiktok_copy_respects_hashtag_limit_and_stays_clean():
    random.seed(11)
    meta = generate_metadata(
        "Ahri",
        "Pandora a Invicta",
        "Cavaleiro (Defesa)",
        "Ninja (Velocidade)",
        vencedor="Pandora a Invicta",
        platform="tiktok",
    )

    copy_text = format_metadata_copy_text(meta, platform="tiktok")

    _assert_clean_text(copy_text)
    assert len(meta["hashtags"]) <= 15
    assert "#tiktok" in copy_text


def test_generate_all_platforms_returns_distinct_platform_blocks():
    random.seed(21)
    all_meta = generate_all_platforms(
        "Aria a Fantasma",
        "Lilith a Lunar",
        "Assassino (Critico)",
        "Criomante (Gelo)",
        vencedor="Aria a Fantasma",
    )

    combined = format_all_platform_copies(all_meta)

    _assert_clean_text(combined)
    assert "=== INSTAGRAM REELS ===" in combined
    assert "=== TIKTOK ===" in combined
    assert "=== YOUTUBE SHORTS ===" in combined
