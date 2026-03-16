"""Debug test: check audio event capture."""
import sys, os, logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from video_pipeline.character_generator import gerar_par_de_lutadores
from video_pipeline.fight_recorder import FightRecorder

c1, a1, c2, a2 = gerar_par_de_lutadores()
print(f"{c1['nome']} vs {c2['nome']}")

rec = FightRecorder(c1, a1, c2, a2, max_duration=10.0)
rec.record()
print(f"\nFrames: {rec.total_frames}, Duration: {rec.duration:.1f}s")
print(f"File: {rec.video_file}")
# Check for temp files
silent = rec.video_file.replace(".mp4", "_silent.mp4")
wav = rec.video_file.replace(".mp4", "_audio.wav")
print(f"Silent exists: {os.path.exists(silent)}")
print(f"WAV exists: {os.path.exists(wav)}")
fsize = os.path.getsize(rec.video_file)
print(f"File size: {fsize / 1024 / 1024:.1f} MB")
