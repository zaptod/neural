"""
Audio Mixer — Captura eventos sonoros durante gravação e mixa pista de áudio.

Abordagem:
  1. Monkey-patch AudioManager.play() para logar (sound_name, timestamp, volume)
  2. Após gravação, mixa os sons reais (.mp3/.wav) nas posições certas
  3. Usa ffmpeg para juntar vídeo silencioso + áudio → vídeo final
"""
import io, math, os, subprocess, logging, warnings
from pathlib import Path
from typing import List, Tuple

_log = logging.getLogger("audio_mixer")

# ffmpeg bundled via imageio-ffmpeg
try:
    import imageio_ffmpeg
    _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    _ffmpeg_exe = "ffmpeg"

# Define antes do import do pydub para evitar warning de ffmpeg ausente
os.environ.setdefault("FFMPEG_BINARY", _ffmpeg_exe)
warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
    category=RuntimeWarning,
)

from pydub import AudioSegment

# Garante que o pydub use o ffmpeg correto
AudioSegment.converter = _ffmpeg_exe

_SAMPLE_RATE = 44100
_CHANNELS = 2
_SAMPLE_WIDTH = 2  # 16-bit


def _ffmpeg_timeout(expected_duration_s: float | None = None) -> int:
    """Calcula timeout conservador para ffmpeg conforme duração esperada."""
    if expected_duration_s is None or expected_duration_s <= 0:
        return 600  # fallback robusto
    # Base alta para máquinas mais lentas + fator por duração do vídeo
    return max(600, int(expected_duration_s * 6 + 120))


def _load_audio_ffmpeg(filepath: str) -> AudioSegment | None:
    """Carrega arquivo de áudio usando ffmpeg direto (sem ffprobe)."""
    cmd = [
        _ffmpeg_exe,
        "-i", filepath,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ar", str(_SAMPLE_RATE),
        "-ac", str(_CHANNELS),
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=10,
        )
        if result.returncode != 0 or not result.stdout:
            return None
        return AudioSegment(
            data=result.stdout,
            sample_width=_SAMPLE_WIDTH,
            frame_rate=_SAMPLE_RATE,
            channels=_CHANNELS,
        )
    except Exception as e:
        _log.debug("ffmpeg decode falhou para %s: %s", filepath, e)
        return None

# Diretório de sons do jogo
_project_root = Path(__file__).resolve().parent.parent
SOUNDS_DIR = _project_root / "sounds"


class AudioEventCapture:
    """Captura eventos de áudio durante uma gravação headless."""

    # Cooldown mínimo (s) entre eventos com mesmo nome de som
    _DEDUP_COOLDOWN = 0.15

    def __init__(self):
        self.events: List[Tuple[float, str, float]] = []  # (timestamp, sound_name, volume)
        self._elapsed = 0.0
        self._originals = {}
        self._manager = None
        self._last_play: dict[str, float] = {}  # sound_name → last timestamp

    def start(self):
        """Instala hooks em TODOS os métodos de play do AudioManager."""
        from effects.audio import AudioManager
        self._manager = AudioManager.get_instance()
        # Força enabled para que os if-guards não bloqueiem
        self._manager.enabled = True

        capture = self  # closure ref

        # Hook play() — ponto final de todos os sons
        orig_play = self._manager.play
        self._originals["play"] = orig_play

        def _hooked_play(sound_name: str, volume: float = 1.0, pan: float = 0.0):
            if sound_name:
                # Dedup: ignora mesmo som tocado em intervalo muito curto
                last = capture._last_play.get(sound_name, -1.0)
                if (capture._elapsed - last) < AudioEventCapture._DEDUP_COOLDOWN:
                    return
                capture._last_play[sound_name] = capture._elapsed

                category = capture._manager._get_sound_category(sound_name)
                cat_vol = capture._manager.category_volumes.get(category, 1.0)
                final_vol = volume * cat_vol * capture._manager.sfx_volume * capture._manager.master_volume
                capture.events.append((capture._elapsed, sound_name, final_vol))
            # Não chama o original — mixer não funciona em headless

        self._manager.play = _hooked_play

        # Hook play_positional() — tem seu próprio if-guard enabled,
        # calculamos atenuação e chamamos nosso hooked play direto
        orig_positional = self._manager.play_positional
        self._originals["play_positional"] = orig_positional

        def _hooked_positional(sound_name: str, pos_x: float, listener_x: float,
                               max_distance: float = 20.0, volume: float = 1.0):
            distance = abs(pos_x - listener_x)
            if distance > max_distance:
                return
            distance_volume = 1.0 - (distance / max_distance)
            pan = max(-1.0, min(1.0, (pos_x - listener_x) / max_distance))
            _hooked_play(sound_name, volume * distance_volume, pan)

        self._manager.play_positional = _hooked_positional

    def update_time(self, elapsed: float):
        """Atualiza o timestamp atual da gravação."""
        self._elapsed = elapsed

    def stop(self):
        """Remove hooks e restaura os métodos originais."""
        if self._manager:
            for name, orig in self._originals.items():
                setattr(self._manager, name, orig)
            self._originals.clear()
            self._manager = None


def _resolve_sound_file(sound_name: str) -> str | None:
    """Encontra o arquivo de som para um nome, tentando variações."""
    # Tenta nome exato
    for ext in [".mp3", ".wav", ".ogg"]:
        path = SOUNDS_DIR / f"{sound_name}{ext}"
        if path.exists():
            return str(path)

    # Fallback: mapeia nomes de evento → arquivos existentes
    _FALLBACKS = {
        "jump_land": "wall_impact_light",
        "impact_critical": "slash_critical",
        "energy_impact": "fireball_impact",
        "buff_activate": "energy_blast",
        "shield_up": "energy_blast",
        "beam_charge": "beam_fire",
        "beam_end": "fireball_impact",
        "wall_hit": "wall_impact_light",
    }
    fb = _FALLBACKS.get(sound_name)
    if fb:
        for ext in [".mp3", ".wav", ".ogg"]:
            path = SOUNDS_DIR / f"{fb}{ext}"
            if path.exists():
                return str(path)

    # Tenta buscar pelo grupo (ex: "punch" → "punch_light.mp3")
    for f in SOUNDS_DIR.iterdir():
        if f.stem.startswith(sound_name) and f.suffix in {".mp3", ".wav", ".ogg"}:
            return str(f)

    return None


def mix_audio_track(events: List[Tuple[float, str, float]],
                    duration_s: float,
                    output_wav: str) -> bool:
    """
    Mixa eventos de áudio em um arquivo WAV.

    Args:
        events: Lista de (timestamp_s, sound_name, volume)
        duration_s: Duração total em segundos
        output_wav: Caminho do WAV de saída
    Returns:
        True se gerou áudio com sucesso
    """
    if not events:
        _log.warning("Nenhum evento de áudio para mixar")
        return False

    # Cria pista silenciosa com duração total
    duration_ms = int(duration_s * 1000) + 500  # +500ms de margem
    mixed = AudioSegment.silent(duration=duration_ms, frame_rate=44100)

    # Cache de sons carregados
    sound_cache: dict[str, AudioSegment] = {}
    sounds_found = 0
    sounds_missing = set()

    for timestamp, sound_name, volume in events:
        # Resolve arquivo
        if sound_name not in sound_cache:
            filepath = _resolve_sound_file(sound_name)
            if filepath:
                seg = _load_audio_ffmpeg(filepath)
                if seg is None:
                    _log.debug("Erro ao carregar %s", filepath)
                sound_cache[sound_name] = seg
            else:
                sound_cache[sound_name] = None
                if sound_name not in sounds_missing:
                    sounds_missing.add(sound_name)

        segment = sound_cache.get(sound_name)
        if segment is None:
            continue

        # Aplica volume (pydub usa dB)
        vol_clamped = max(0.01, min(1.0, volume))
        db_adjustment = 20 * math.log10(vol_clamped)
        adjusted = segment + db_adjustment

        # Overlay na posição
        pos_ms = int(timestamp * 1000)
        if pos_ms < duration_ms:
            mixed = mixed.overlay(adjusted, position=pos_ms)
            sounds_found += 1

    if sounds_missing:
        _log.debug("Sons sem arquivo: %s", ", ".join(sorted(sounds_missing)))

    if sounds_found == 0:
        _log.warning("Nenhum som encontrado nos arquivos")
        return False

    _log.info("Áudio mixado: %d eventos, %d sons únicos, %.1fs",
              sounds_found, len(sound_cache) - len(sounds_missing), duration_s)

    # Exporta WAV
    mixed.export(output_wav, format="wav")
    return True


def mux_video_audio(video_path: str, audio_path: str, output_path: str,
                    expected_duration_s: float | None = None) -> bool:
    """
    Combina vídeo silencioso + áudio WAV → vídeo final com som.
    Re-encoda para H.264/AAC compatível com Instagram Reels:
      - Codec H.264 High Profile (exigido pelo Reels)
      - Bitrate máx 3.5 Mbps (recomendação do Instagram)
      - yuv420p para compatibilidade máxima de player
    """
    cmd = [
        _ffmpeg_exe,
        "-y",                       # Sobrescreve sem perguntar
        "-i", video_path,           # Vídeo de entrada (sem áudio)
        "-i", audio_path,           # Áudio de entrada
        "-c:v", "libx264",          # H.264 — codec exigido pelo Reels
        "-preset", "veryfast",      # Reduz tempo de encode sem quebrar compatibilidade
        "-profile:v", "high",
        "-level:v", "4.2",          # Suporta 1080p @ 60 fps
        "-pix_fmt", "yuv420p",      # Compatibilidade máxima de player
        "-b:v", "3500k",            # Bitrate alvo ≤ 3.5 Mbps
        "-maxrate", "3500k",        # Teto absoluto de bitrate
        "-bufsize", "7000k",        # Buffer = 2× maxrate
        "-c:a", "aac",              # Encode áudio em AAC
        "-b:a", "192k",             # Bitrate de áudio
        "-movflags", "+faststart",  # Moov atom no início (streaming)
        "-shortest",                # Corta no mais curto
        output_path,
    ]

    try:
        timeout_s = _ffmpeg_timeout(expected_duration_s)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if result.returncode != 0:
            _log.error("ffmpeg falhou: %s", result.stderr[-500:] if result.stderr else "")
            return False
        _log.info("Vídeo com áudio gerado: %s", output_path)
        return True
    except subprocess.TimeoutExpired:
        _log.error("ffmpeg timeout (mux)")
        return False
    except FileNotFoundError:
        _log.error("ffmpeg não encontrado")
        return False


def reencode_silent_video(input_path: str, output_path: str,
                          expected_duration_s: float | None = None) -> bool:
    """
    Re-encoda vídeo sem áudio para H.264 compatível com Instagram Reels.
    Usado nos caminhos de fallback onde não há trilha de áudio para mixar.
    """
    cmd = [
        _ffmpeg_exe,
        "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-profile:v", "high",
        "-level:v", "4.2",
        "-pix_fmt", "yuv420p",
        "-b:v", "3500k",
        "-maxrate", "3500k",
        "-bufsize", "7000k",
        "-an",                      # Sem áudio
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        timeout_s = _ffmpeg_timeout(expected_duration_s)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if result.returncode != 0:
            _log.error("ffmpeg re-encode falhou: %s", result.stderr[-500:] if result.stderr else "")
            return False
        _log.info("Vídeo re-encodado: %s", output_path)
        return True
    except subprocess.TimeoutExpired:
        _log.error("ffmpeg timeout no re-encode")
        return False
    except FileNotFoundError:
        _log.error("ffmpeg não encontrado")
        return False
