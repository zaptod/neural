"""
Neural Fights â€” Video Pipeline v1.0
GeraÃ§Ã£o automÃ¡tica de vÃ­deos 9:16 para Reels / TikTok / Shorts.
"""

from pipeline_video.character_generator import gerar_par_de_lutadores, gerar_personagem
from pipeline_video.fight_recorder import FightRecorder
from pipeline_video.video_encoder import encode_video
from pipeline_video.metadata_generator import generate_metadata, generate_all_platforms
from pipeline_video.batch_runner import run_batch

