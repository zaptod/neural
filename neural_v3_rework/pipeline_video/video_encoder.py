"""
Video Encoder â€” Converte frames numpy em arquivo MP4 usando OpenCV.
"""
import os, logging, time
import numpy as np
import cv2

from pipeline_video.config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    VIDEO_CODEC, VIDEO_EXT, OUTPUT_DIR,
)

_log = logging.getLogger("video_encoder")


def encode_video(frames: list[np.ndarray], filename: str = None,
                 output_dir: str = None) -> str:
    """
    Codifica lista de frames RGB em arquivo MP4.

    Args:
        frames: Lista de numpy arrays (H, W, 3) em RGB
        filename: Nome do arquivo (sem extensÃ£o). Auto-gerado se None.
        output_dir: Pasta de saÃ­da. Usa OUTPUT_DIR se None.
    Returns:
        Caminho completo do arquivo gerado.
    """
    if not frames:
        raise ValueError("Lista de frames vazia")

    out_dir = str(output_dir or OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"fight_{timestamp}"
    
    filepath = os.path.join(out_dir, f"{filename}{VIDEO_EXT}")

    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
    writer = cv2.VideoWriter(filepath, fourcc, VIDEO_FPS, (w, h))

    if not writer.isOpened():
        raise RuntimeError(f"Falha ao abrir VideoWriter: codec={VIDEO_CODEC}, {w}x{h}")

    _log.info("Encoding %d frames â†’ %s (%dx%d @ %dfps)",
              len(frames), filepath, w, h, VIDEO_FPS)

    for frame in frames:
        # OpenCV espera BGR
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        writer.write(bgr)

    writer.release()

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    _log.info("VÃ­deo salvo: %s (%.1f MB, %d frames, %.1fs)",
              filepath, size_mb, len(frames), len(frames) / VIDEO_FPS)

    return filepath

