"""
Pipeline Config — Constantes e configurações do sistema de vídeo.
"""
import os, pathlib

# === PATHS ===
_ROOT = pathlib.Path(__file__).resolve().parent.parent  # neural_v3_rework/
OUTPUT_DIR   = _ROOT / "video_pipeline" / "output"
FRAMES_DIR   = _ROOT / "video_pipeline" / "_frames"
PORTRAITS_DIR = _ROOT / "video_pipeline" / "portraits"

# === VIDEO ===
VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS    = 60
VIDEO_CODEC  = "mp4v"          # OpenCV fourcc (H.264 via mp4v ou avc1)
VIDEO_EXT    = ".mp4"
MIN_FIGHT_DURATION = 60.0      # Luta deve durar no mínimo 60s

# === GAME RENDER ===
# Renderizamos direto em portrait (9:16) — sem crop
RENDER_WIDTH  = VIDEO_WIDTH   # 1080
RENDER_HEIGHT = VIDEO_HEIGHT  # 1920

# === PIPELINE ===
PLATFORMS        = ["reels", "tiktok", "shorts"]

# === VISUAL ===
NOME_FONT_SIZE   = 20          # Tamanho da fonte do nome acima da cabeça
HP_BAR_HEIGHT    = 5           # Barra de vida mini abaixo do nome
END_TEXT          = "Comente o nome do seu lutador para entrar na arena"
END_TEXT_DURATION = 4.0        # Segundos que o texto final fica na tela
FADE_OUT_DURATION = 1.5        # Fade to black no final

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
    "o Implacável", "a Destruidora", "o Imortal", "a Sombria", "o Lendário",
    "a Invicta", "o Carmesim", "a Tempestade", "o Predador", "a Fantasma",
    "o Titã", "a Valquíria", "o Dragão", "a Fênix", "o Relâmpago",
    "a Serpente", "o Colosso", "a Lâmina", "o Inferno", "a Gélida",
    "o Trovão", "a Noturna", "o Solar", "a Lunar", "o Abissal",
]

# Criar diretórios na importação
for d in [OUTPUT_DIR, FRAMES_DIR, PORTRAITS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
