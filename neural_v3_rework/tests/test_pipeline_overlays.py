import os
from types import SimpleNamespace

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pipeline_video.fight_recorder import FightRecorder


def _dummy_fighter(nome, classe, cor, vida, vida_max):
    return SimpleNamespace(
        dados=SimpleNamespace(nome=nome, classe=classe, r=cor[0], g=cor[1], b=cor[2]),
        vida=vida,
        vida_max=vida_max,
    )


def _dummy_recorder():
    return FightRecorder(
        {"nome": "Astra", "cor_r": 90, "cor_g": 180, "cor_b": 255},
        {"nome": "Lanca Solar"},
        {"nome": "Vesper", "cor_r": 255, "cor_g": 96, "cor_b": 130},
        {"nome": "Lamina Lunar"},
    )


def setup_module():
    pygame.init()
    pygame.font.init()


def teardown_module():
    pygame.quit()


def test_persistent_hud_draws_top_panels_and_bottom_cta():
    recorder = _dummy_recorder()
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)
    sim = SimpleNamespace(
        p1=_dummy_fighter("Astra", "Magista (Impacto)", (90, 180, 255), 84, 100),
        p2=_dummy_fighter("Vesper", "Assassino (Sombra)", (255, 96, 130), 47, 100),
    )

    recorder._draw_persistent_hud(surface, sim)

    pixels = pygame.surfarray.array3d(surface)
    assert pixels.sum() > 0
    assert pixels[:, :180, :].sum() > 0
    assert pixels[:, 780:, :].sum() > 0


def test_intro_overlay_draws_matchup_cards_and_center_vs():
    recorder = _dummy_recorder()
    recorder.char1["classe"] = "Cavaleiro (Defesa)"
    recorder.char2["classe"] = "Ninja (Velocidade)"
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)

    recorder._draw_intro_overlay(surface, 0.95)

    pixels = pygame.surfarray.array3d(surface)
    alpha = pygame.surfarray.array_alpha(surface)
    assert pixels.sum() > 0
    assert alpha[40:500, 120:420].sum() > 0
    assert alpha[170:370, 150:420].sum() > 0


def test_victory_overlay_draws_central_card_and_cta():
    recorder = _dummy_recorder()
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)

    recorder._draw_victory_overlay(surface, "Vesper", 0.9)

    pixels = pygame.surfarray.array3d(surface)
    alpha = pygame.surfarray.array_alpha(surface)
    assert pixels.sum() > 0
    assert alpha.sum() > 0
    assert alpha[120:420, 180:760].sum() > 0
    assert alpha[120:420, 620:860].sum() > 0


def test_palette_from_name_uses_character_colors_for_winner_overlay():
    recorder = _dummy_recorder()
    accent, accent_dark = recorder._palette_from_fighter(None, fallback_name="Vesper")

    assert accent == (255, 96, 130)
    assert all(channel > 0 for channel in accent_dark)
    assert accent_dark != accent
