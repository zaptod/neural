#!/usr/bin/env python3
"""
run_pipeline.py - Ponto de entrada da pipeline de video.

Uso:
    python run_pipeline.py
    python run_pipeline.py --fights 1
    python run_pipeline.py --generation-mode hybrid
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Neural Fights - Video Pipeline")
    parser.add_argument(
        "--fights",
        type=int,
        default=None,
        help="Numero de lutas (default: 1 por plataforma)",
    )
    parser.add_argument(
        "--generation-mode",
        type=str,
        default="hybrid",
        choices=["balanced", "hybrid", "pure_random"],
        help="Modo de geracao de pares: balanced, hybrid ou pure_random",
    )
    parser.add_argument(
        "--video-format",
        type=str,
        default="comment_roulette",
        choices=["comment_roulette", "classic"],
        help="Formato principal do video: roleta por comentario ou luta classica",
    )
    parser.add_argument(
        "--encounter-mode",
        type=str,
        default="duelo",
        choices=["duelo", "equipes", "horda"],
        help="Tipo de encontro da pipeline: duelo, equipes ou horda.",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="Template tatico para encounter-mode equipes/horda.",
    )
    parser.add_argument(
        "--fighter1",
        type=str,
        default=None,
        help="Nome do primeiro lutador para duelo direto da pipeline.",
    )
    parser.add_argument(
        "--fighter2",
        type=str,
        default=None,
        help="Nome do segundo lutador para duelo direto da pipeline.",
    )
    parser.add_argument(
        "--cenario",
        type=str,
        default=None,
        help="Cenario forcado para a gravacao do encontro alvo.",
    )
    parser.add_argument(
        "--comment",
        type=str,
        default=None,
        help="Comentario base para o gancho e a build da roleta",
    )
    parser.add_argument(
        "--no-coverage-rotation",
        action="store_true",
        help="Desativa rotacao de cobertura de atributos",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Logging detalhado")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    log = logging.getLogger("pipeline")
    log.info("Neural Fights Video Pipeline")
    log.info(
        "Generation mode: %s | Video format: %s | Coverage rotation: %s",
        args.generation_mode,
        args.video_format,
        "off" if args.no_coverage_rotation else "on",
    )
    log.info("Encounter mode: %s | Template: %s", args.encounter_mode, args.template or "auto")

    from pipeline_video.batch_runner import run_batch

    results = run_batch(
        num_fights=args.fights,
        generation_mode=args.generation_mode,
        coverage_rotation=not args.no_coverage_rotation,
        video_format=args.video_format,
        comment=args.comment,
        encounter_mode=args.encounter_mode,
        template_id=args.template,
        fighter1_name=args.fighter1,
        fighter2_name=args.fighter2,
        forced_cenario=args.cenario,
    )

    if results:
        log.info("%d videos gerados com sucesso.", len(results))
        for result in results:
            log.info(
                "  [%s] %s vs %s -> Vencedor: %s",
                result["platform"].upper(),
                result["fighter1"]["nome"],
                result["fighter2"]["nome"],
                result["winner"] or "Empate",
            )
        return

    log.error("Nenhum video gerado.")
    sys.exit(1)


if __name__ == "__main__":
    main()
