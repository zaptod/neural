"""
Batch Runner — Orquestra a geração diária de vídeos (1 luta única por plataforma).
"""
import os, sys, json, logging, time
from pathlib import Path

_log = logging.getLogger("batch_runner")

# Garante path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from video_pipeline.config import OUTPUT_DIR, PLATFORMS
from video_pipeline.character_generator import (
    gerar_par_de_lutadores,
    _gap_poder,
    reset_coverage_rotation,
    set_coverage_rotation,
)
from video_pipeline.fight_recorder import FightRecorder
from video_pipeline.metadata_generator import (
    generate_all_platforms,
    format_metadata_plain_text,
    format_metadata_copy_text,
    format_all_platform_copies,
)


def run_batch(num_fights: int = None, cenarios: list = None,
              generation_mode: str = "hybrid",
              coverage_rotation: bool = True) -> list[dict]:
    """
    Gera um batch completo de vídeos — uma luta única por plataforma.

    Args:
        num_fights: Número de lutas (default: len(PLATFORMS), uma por plataforma).
        cenarios: Lista de cenários para usar. Se None, varia aleatoriamente.
        generation_mode: balanced | hybrid | pure_random.
        coverage_rotation: Se True, faz rotação para ampliar cobertura de atributos.
    Returns:
        Lista de dicts com info de cada vídeo gerado.
    """
    import random

    set_coverage_rotation(coverage_rotation)
    if coverage_rotation:
        reset_coverage_rotation()

    if num_fights is None:
        num_fights = len(PLATFORMS)

    if cenarios is None:
        cenarios = ["Arena", "Coliseu", "Templo", "Floresta", "Vulcão"]

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    batch_dir = Path(OUTPUT_DIR) / f"batch_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for idx in range(num_fights):
        platform = PLATFORMS[idx % len(PLATFORMS)]

        _log.info("=" * 60)
        _log.info("LUTA %d/%d → %s", idx + 1, num_fights, platform.upper())
        _log.info("=" * 60)

        # 1. Gerar lutadores (únicos para esta plataforma)
        c1, a1, c2, a2 = gerar_par_de_lutadores(generation_mode=generation_mode)
        nome1 = c1["nome"]
        nome2 = c2["nome"]
        classe1 = c1["classe"]
        classe2 = c2["classe"]
        gap_abs, gap_rel = _gap_poder(c1, a1, c2, a2)
        cenario = random.choice(cenarios)

        _log.info("  %s (%s) vs %s (%s) — %s", nome1, classe1, nome2, classe2, cenario)
        _log.info("  Balanceamento: gap_poder=%.2f (%.1f%%)", gap_abs, gap_rel * 100.0)

        # 2. Gravar luta direto no diretório da plataforma
        plat_dir = batch_dir / platform
        plat_dir.mkdir(exist_ok=True)

        try:
            fight_name = f"{platform}_{nome1.split()[0]}_vs_{nome2.split()[0]}"
            fight_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in fight_name)
            video_path = str(plat_dir / f"{fight_name}.mp4")

            recorder = FightRecorder(c1, a1, c2, a2, cenario=cenario,
                                     output_path=video_path)
            recorder.record()
        except Exception as e:
            _log.error("  ERRO na gravação: %s", e)
            import traceback
            traceback.print_exc()
            continue

        if recorder.total_frames == 0:
            _log.warning("  Nenhum frame capturado, pulando...")
            continue

        vencedor = recorder.winner
        _log.info("  Vencedor: %s | Frames: %d | Duração: %.1fs",
                  vencedor, recorder.total_frames, recorder.duration)

        # 3. Gerar metadados apenas para esta plataforma
        all_meta = generate_all_platforms(nome1, nome2, classe1, classe2, vencedor)
        meta = all_meta[platform]
        meta_file = plat_dir / f"{fight_name}_meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Versão texto simples (copiar e colar)
        meta_txt_file = plat_dir / f"{fight_name}_meta.txt"
        with open(meta_txt_file, "w", encoding="utf-8") as f:
            f.write(format_metadata_plain_text(meta))

        # Versão personalizada para copy/paste da plataforma atual
        meta_copy_file = plat_dir / f"{fight_name}_copy.txt"
        with open(meta_copy_file, "w", encoding="utf-8") as f:
            f.write(format_metadata_copy_text(meta, platform=platform))

        # Versão única com blocos para REELS/TIKTOK/SHORTS
        meta_all_platforms_file = plat_dir / f"{fight_name}_copy_all_platforms.txt"
        with open(meta_all_platforms_file, "w", encoding="utf-8") as f:
            f.write(format_all_platform_copies(all_meta))

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
        }
        results.append(fight_result)
        _log.info("  [%s] %s", platform.upper(), meta["title"])

    # Salva resumo do batch
    summary = {
        "timestamp": timestamp,
        "num_fights": len(results),
        "results": results,
    }
    summary_file = batch_dir / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    _log.info("=" * 60)
    _log.info("BATCH COMPLETO: %d lutas → %s", len(results), batch_dir)
    _log.info("=" * 60)

    return results
