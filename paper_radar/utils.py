from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "topic"


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def normalize_whitespace(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_date_guess(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    patterns = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y %b %d",
        "%Y %B %d",
        "%Y %b",
        "%Y %B",
        "%Y",
        "%Y-%m",
    ]
    for fmt in patterns:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def days_since(date_text: str | None) -> int | None:
    dt = parse_date_guess(date_text)
    if dt is None:
        return None
    return max(0, (utc_now() - dt).days)


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    out = OrderedDict()
    for v in values:
        if v is None:
            continue
        vv = normalize_whitespace(v)
        if vv:
            out[vv] = True
    return list(out.keys())


def stable_paper_id(source: str, source_id: str, title: str) -> str:
    raw = f"{source}|{source_id}|{title}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def json_dump(path: str | Path, payload: object) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
