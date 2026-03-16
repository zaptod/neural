"""
Neural Fights — Video Pipeline v1.0
Geração automática de vídeos 9:16 para Reels / TikTok / Shorts.
"""

from video_pipeline.character_generator import gerar_par_de_lutadores, gerar_personagem
from video_pipeline.fight_recorder import FightRecorder
from video_pipeline.video_encoder import encode_video
from video_pipeline.metadata_generator import generate_metadata, generate_all_platforms
from video_pipeline.batch_runner import run_batch
