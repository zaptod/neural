"""
Batch Runner - Orquestra a geracao diaria de videos.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path


_log = logging.getLogger("batch_runner")

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pipeline_video.character_generator import (
    _gap_poder,
    gerar_par_de_lutadores,
    reset_coverage_rotation,
    set_coverage_rotation,
)
from pipeline_video.config import OUTPUT_DIR, PLATFORMS
from pipeline_video.fight_recorder import FightRecorder
from pipeline_video.metadata_generator import (
    format_all_platform_copies,
    format_metadata_copy_text,
    format_metadata_plain_text,
    generate_all_platforms,
    generate_story_all_platforms,
)
from pipeline_video.roulette_status import gerar_story_roleta_status, slugify_comment


def run_batch(
    num_fights: int | None = None,
    cenarios: list[str] | None = None,
    generation_mode: str = "hybrid",
    coverage_rotation: bool = True,
    video_format: str = "comment_roulette",
    comment: str | None = None,
) -> list[dict]:
    """
    Gera um batch completo de videos, uma luta por plataforma.
    """
    import random

    set_coverage_rotation(coverage_rotation)
    if coverage_rotation:
        reset_coverage_rotation()

    if num_fights is None:
        num_fights = len(PLATFORMS)

    if cenarios is None:
        cenarios = ["Arena", "Coliseu", "Templo", "Floresta", "Vulcao"]

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    batch_dir = Path(OUTPUT_DIR) / f"batch_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    for idx in range(num_fights):
        platform = PLATFORMS[idx % len(PLATFORMS)]

        _log.info("=" * 60)
        _log.info("LUTA %d/%d -> %s", idx + 1, num_fights, platform.upper())
        _log.info("=" * 60)

        story = None
        if video_format == "comment_roulette":
            story = gerar_story_roleta_status(comment, fight_index=idx)
            c1, a1 = story["fighter1"], story["weapon1"]
            c2, a2 = story["fighter2"], story["weapon2"]
        else:
            c1, a1, c2, a2 = gerar_par_de_lutadores(generation_mode=generation_mode)

        nome1 = c1["nome"]
        nome2 = c2["nome"]
        classe1 = c1["classe"]
        classe2 = c2["classe"]
        gap_abs, gap_rel = _gap_poder(c1, a1, c2, a2)
        cenario = random.choice(cenarios)

        _log.info("  %s (%s) vs %s (%s) - %s", nome1, classe1, nome2, classe2, cenario)
        _log.info("  Balanceamento: gap_poder=%.2f (%.1f%%)", gap_abs, gap_rel * 100.0)

        plat_dir = batch_dir / platform
        plat_dir.mkdir(exist_ok=True)

        try:
            if story:
                fight_name = f"{platform}_{slugify_comment(story['comment'])}_{nome1.split()[0]}_vs_{nome2.split()[0]}"
            else:
                fight_name = f"{platform}_{nome1.split()[0]}_vs_{nome2.split()[0]}"
            fight_name = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in fight_name)
            video_path = str(plat_dir / f"{fight_name}.mp4")

            recorder = FightRecorder(
                c1,
                a1,
                c2,
                a2,
                cenario=cenario,
                output_path=video_path,
                story_mode="roleta_status" if story else "classic",
                roulette_story=story,
            )
            recorder.record()
        except Exception as exc:
            _log.error("  ERRO na gravacao: %s", exc)
            import traceback

            traceback.print_exc()
            continue

        if recorder.total_frames == 0:
            _log.warning("  Nenhum frame capturado, pulando...")
            continue

        vencedor = recorder.winner
        _log.info(
            "  Vencedor: %s | Frames: %d | Duracao: %.1fs",
            vencedor,
            recorder.total_frames,
            recorder.duration,
        )

        all_meta = (
            generate_story_all_platforms(story, vencedor=vencedor)
            if story
            else generate_all_platforms(nome1, nome2, classe1, classe2, vencedor)
        )
        meta = all_meta[platform]
        meta_file = plat_dir / f"{fight_name}_meta.json"
        with open(meta_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2)

        meta_txt_file = plat_dir / f"{fight_name}_meta.txt"
        with open(meta_txt_file, "w", encoding="utf-8") as file:
            file.write(format_metadata_plain_text(meta))

        meta_copy_file = plat_dir / f"{fight_name}_copy.txt"
        with open(meta_copy_file, "w", encoding="utf-8") as file:
            file.write(format_metadata_copy_text(meta, platform=platform))

        meta_all_platforms_file = plat_dir / f"{fight_name}_copy_all_platforms.txt"
        with open(meta_all_platforms_file, "w", encoding="utf-8") as file:
            file.write(format_all_platform_copies(all_meta))

        story_file = None
        if story:
            story_file = plat_dir / f"{fight_name}_story.json"
            with open(story_file, "w", encoding="utf-8") as file:
                json.dump(story, file, ensure_ascii=False, indent=2)

        fight_result = {
            "platform": platform,
            "fighter1": {"nome": nome1, "classe": classe1},
            "fighter2": {"nome": nome2, "classe": classe2},
            "winner": vencedor,
            "duration": recorder.duration,
            "frames": recorder.total_frames,
            "video": str(video_path),
            "metadata": str(meta_file),
            "metadata_text": str(meta_txt_file),
            "metadata_copy": str(meta_copy_file),
            "metadata_copy_all_platforms": str(meta_all_platforms_file),
            "title": meta["title"],
            "story": str(story_file) if story_file else None,
        }
        results.append(fight_result)
        _log.info("  [%s] %s", platform.upper(), meta["title"])

    summary = {
        "timestamp": timestamp,
        "num_fights": len(results),
        "results": results,
    }
    summary_file = batch_dir / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    _log.info("=" * 60)
    _log.info("BATCH COMPLETO: %d lutas -> %s", len(results), batch_dir)
    _log.info("=" * 60)

    return results
