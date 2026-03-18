import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pipeline_video.encounter_recorder import EncounterRecorder
from pipeline_video.metadata_generator import generate_encounter_all_platforms
from utilitarios.encounter_config import build_horde_match_config, build_team_match_config


def setup_module():
    pygame.init()
    pygame.font.init()


def teardown_module():
    pygame.quit()


def test_encounter_recorder_draws_team_intro_overlay():
    config = build_team_match_config(
        [
            {"team_id": 0, "label": "Guardioes", "members": ["Astra", "Borin"]},
            {"team_id": 1, "label": "Ruptura", "members": ["Nyx", "Kara"]},
        ],
        extra={"portrait_mode": True},
    )
    recorder = EncounterRecorder(config)
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)

    recorder._draw_intro_overlay(surface, 0.92)

    assert pygame.surfarray.array_alpha(surface).sum() > 0


def test_encounter_recorder_draws_horde_hud_overlay():
    config = build_horde_match_config(
        [{"team_id": 0, "label": "Expedicao", "members": ["Astra"]}],
        {"preset_id": "sobrevivencia_basica"},
        extra={"portrait_mode": True},
    )
    recorder = EncounterRecorder(config)
    surface = pygame.Surface((540, 960), pygame.SRCALPHA)
    sim = SimpleNamespace(
        fighters=[
            SimpleNamespace(team_id=0, morto=False, dados=SimpleNamespace(nome="Astra", r=90, g=180, b=255), vida=80, vida_max=100),
            SimpleNamespace(team_id=1, morto=False, dados=SimpleNamespace(nome="Zumbi", r=140, g=160, b=120), vida=25, vida_max=25),
        ],
        horde_manager=SimpleNamespace(export_summary=lambda: {"wave_atual": 2, "waves_total": 3, "total_killed": 5}),
    )

    recorder._draw_persistent_hud(surface, sim)

    assert pygame.surfarray.array_alpha(surface).sum() > 0


def test_generate_encounter_all_platforms_has_mode():
    all_meta = generate_encounter_all_platforms("Guardioes", "Ruptura", mode="equipes", winner="Guardioes")

    assert set(all_meta.keys()) == {"reels", "tiktok", "shorts"}
    assert all_meta["reels"]["mode"] == "equipes"
