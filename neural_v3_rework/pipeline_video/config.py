"""
Pipeline Config - Constantes e configuracoes do sistema de video.
"""

from __future__ import annotations

import os
import pathlib


# === PATHS ===
_ROOT = pathlib.Path(__file__).resolve().parent.parent  # neural_v3_rework/
OUTPUT_DIR = pathlib.Path(os.environ.get("NF_PIPELINE_OUTPUT_DIR", str(_ROOT / "video_pipeline" / "output")))
FRAMES_DIR = pathlib.Path(os.environ.get("NF_PIPELINE_FRAMES_DIR", str(_ROOT / "video_pipeline" / "_frames")))
PORTRAITS_DIR = pathlib.Path(os.environ.get("NF_PIPELINE_PORTRAITS_DIR", str(_ROOT / "video_pipeline" / "portraits")))

# === VIDEO ===
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 60
VIDEO_CODEC = "mp4v"  # OpenCV fourcc (H.264 via mp4v ou avc1)
VIDEO_EXT = ".mp4"
MIN_FIGHT_DURATION = 60.0  # Luta deve durar no minimo 60s

# === GAME RENDER ===
# Renderizamos direto em portrait (9:16) - sem crop
RENDER_WIDTH = VIDEO_WIDTH
RENDER_HEIGHT = VIDEO_HEIGHT

# === PIPELINE ===
PLATFORMS = ["reels", "tiktok", "shorts"]

# === VISUAL ===
NOME_FONT_SIZE = 20  # Tamanho da fonte do nome acima da cabeca
HP_BAR_HEIGHT = 5    # Barra de vida mini abaixo do nome
END_TEXT = "Comente o nome do seu campeao"
END_TEXT_DURATION = 4.0
FADE_OUT_DURATION = 1.5

# === CHARACTER GENERATION ===
NOMES_MASCULINOS = [
    "Kael", "Draven", "Zed", "Sylas", "Darius", "Talon", "Sett", "Yasuo",
    "Pyke", "Kayn", "Viego", "Yone", "Garen", "Lucian", "Thresh", "Rengar",
    "Orion", "Atlas", "Magnus", "Fenrir", "Aldric", "Caelum", "Dante", "Erebos",
    "Hector", "Kain", "Leoric", "Mordred", "Nero", "Ragnar", "Sigurd", "Thane",
    "Viktor", "Xerath", "Zagreus", "Balthazar", "Corvus", "Drake", "Ezra", "Griffin",
]

NOMES_FEMININOS = [
    "Luna", "Aria", "Nova", "Ahri", "Lux", "Jinx", "Akali", "Gwen", "Nilah",
    "Riven", "Katarina", "Morgana", "Leona", "Caitlyn", "Fiora", "Irelia",
    "Selene", "Astrid", "Freya", "Hestia", "Nyx", "Rhea", "Thalia", "Valkyria",
    "Artemis", "Calypso", "Elektra", "Helena", "Isolde", "Lilith", "Medea", "Ophelia",
    "Pandora", "Seraphina", "Tempest", "Aurora", "Briar", "Crimson", "Dahlia", "Ember",
]

TITULOS = [
    "o Implacavel", "a Destruidora", "o Imortal", "a Sombria", "o Lendario",
    "a Invicta", "o Carmesim", "a Tempestade", "o Predador", "a Fantasma",
    "o Titao", "a Valquiria", "o Dragao", "a Fenix", "o Relampago",
    "a Serpente", "o Colosso", "a Lamina", "o Inferno", "a Gelida",
    "o Trovao", "a Noturna", "o Solar", "a Lunar", "o Abissal",
]


for directory in [OUTPUT_DIR, FRAMES_DIR, PORTRAITS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
