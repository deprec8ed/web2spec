from __future__ import annotations

import base64
import re
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit


def normalize_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def slugify(value: str) -> str:
    normalized = normalize_whitespace(value).lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "item"


def safe_filename_from_url(url: str) -> str:
    parts = urlsplit(url)
    host = slugify(parts.netloc)
    raw_path = parts.path if parts.path and parts.path != "/" else "home"
    path = slugify(raw_path)
    if parts.query:
        query = slugify(parts.query)[:40]
        return f"{host}-{path}-{query}"
    return f"{host}-{path}"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()

    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"

    normalized = SplitResult(
        scheme=scheme,
        netloc=netloc,
        path=path,
        query=parts.query,
        fragment="",
    )
    return urlunsplit(normalized)


def image_to_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
