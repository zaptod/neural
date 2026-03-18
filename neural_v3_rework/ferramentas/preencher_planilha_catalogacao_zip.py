from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ferramentas.criar_planilha_catalogacao_memes import write_xlsx


DEFAULT_OUTPUT = ROOT / "pipeline_video" / "catalogacao_memes_preenchida.xlsx"
MEDIA_EXTS = {".mp4", ".mp3", ".wav", ".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".ogg", ".m4a"}


def _safe_str(value) -> str:
    return "" if value is None else str(value)


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return ""
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def _orientation(width: int | None, height: int | None) -> str:
    if not width or not height:
        return ""
    if width == height:
        return "quadrado"
    return "vertical" if height > width else "horizontal"


def _mp4_has_audio(path: Path) -> bool | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"hdlr" in data and b"soun" in data:
        return True
    if b"mp4a" in data or b"sowt" in data:
        return True
    if path.suffix.lower() in AUDIO_EXTS:
        return True
    return False if path.suffix.lower() in VIDEO_EXTS else None


def _probe_video(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"duracao": None, "largura": None, "altura": None}
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
        duration = None
        if fps > 0 and frames > 0:
            duration = frames / fps
        return {"duracao": duration, "largura": width, "altura": height}
    finally:
        cap.release()


def _probe_image(path: Path) -> dict:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return {"duracao": None, "largura": None, "altura": None}
    height, width = img.shape[:2]
    return {"duracao": None, "largura": int(width), "altura": int(height)}


def _build_row(index: int, original_name: str, rel_path: str, tmp_file: Path, file_size: int) -> list[str]:
    ext = tmp_file.suffix.lower()
    if ext in VIDEO_EXTS:
        media_type = "video"
        meta = _probe_video(tmp_file)
        has_audio = _mp4_has_audio(tmp_file)
    elif ext in IMAGE_EXTS:
        media_type = "foto"
        meta = _probe_image(tmp_file)
        has_audio = False
    else:
        media_type = ""
        meta = {"duracao": None, "largura": None, "altura": None}
        has_audio = True if ext in AUDIO_EXTS else None

    width = meta["largura"]
    height = meta["altura"]
    orientation = _orientation(width, height)

    row = [
        f"meme_{index:04d}",
        media_type,
        "nao_revisado",
        original_name,
        rel_path,
        _format_duration(meta["duracao"]),
        _safe_str(width),
        _safe_str(height),
        orientation,
        "sim" if has_audio is True else ("nao" if has_audio is False else ""),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        f"origem_zip | tamanho_bytes={file_size}",
    ]
    return row


def build_rows_from_zip(zip_path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with tempfile.TemporaryDirectory(prefix="meme_zip_probe_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(zip_path, "r") as zf:
            entries = [e for e in zf.infolist() if not e.is_dir() and Path(e.filename).suffix.lower() in MEDIA_EXTS]
            entries.sort(key=lambda e: e.filename.lower())
            for idx, entry in enumerate(entries, start=1):
                tmp_file = tmp_dir / f"probe_{idx:04d}{Path(entry.filename).suffix.lower()}"
                with zf.open(entry, "r") as src, open(tmp_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                rows.append(
                    _build_row(
                        idx,
                        Path(entry.filename).name,
                        entry.filename,
                        tmp_file,
                        entry.file_size,
                    )
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Preenche uma planilha Excel com metadados tecnicos confiaveis de um ZIP de memes.")
    parser.add_argument("--zip", dest="zip_path", required=True, help="Caminho para o arquivo zip com fotos/videos.")
    parser.add_argument("--output", dest="output_path", default=str(DEFAULT_OUTPUT), help="Caminho do xlsx de saida.")
    args = parser.parse_args()

    zip_path = Path(args.zip_path).expanduser()
    output_path = Path(args.output_path).expanduser()
    rows = build_rows_from_zip(zip_path)
    write_xlsx(output_path, prefilled_rows=rows)
    print(output_path)
    print(f"linhas={len(rows)}")


if __name__ == "__main__":
    main()
