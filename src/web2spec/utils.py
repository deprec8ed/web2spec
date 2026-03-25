from __future__ import annotations

import base64
import re
from pathlib import Path
from urllib.parse import urlsplit


def normalize_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def slugify(value: str) -> str:
    normalized = normalize_whitespace(value).lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "item"


def safe_filename_from_url(url: str) -> str:
    parts = urlsplit(url)
    host = slugify(parts.netloc)
    path = slugify(parts.path or "home")
    if parts.query:
        query = slugify(parts.query)[:40]
        return f"{host}-{path}-{query}"
    return f"{host}-{path}"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def image_to_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")

