from pathlib import Path
from typing import Optional
import os
import re
import shutil


DEFAULT_UPLOAD_DIR = "uploads"


def get_upload_root(upload_dir: Optional[str] = None) -> Path:
    root = Path(upload_dir or os.getenv("UPLOAD_DIR") or DEFAULT_UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")
    return cleaned.strip("._") or "file"


def save_upload_file(file_obj, *, filename: str, upload_dir: Optional[str] = None) -> str:
    target_root = get_upload_root(upload_dir)
    target_path = target_root / filename
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)

    return str(target_path)


def build_static_path(filename: str) -> str:
    return f"/static/{filename}"
