"""Cached HTTP downloads with a progress bar."""

from __future__ import annotations

import time
from pathlib import Path

import requests
from tqdm import tqdm

from . import GarmapError

# Geofabrik rebuilds extracts daily, but re-downloading a multi-hundred-MB file
# for a one-day-fresher map is a bad trade. Revalidate only when the cached copy
# is older than this (or when --refresh is passed).
STALE_AFTER_SECONDS = 14 * 24 * 3600

CHUNK = 1 << 20


def age_seconds(path: Path) -> float:
    return time.time() - path.stat().st_mtime


def download(
    url: str,
    destination: Path,
    label: str | None = None,
    refresh: bool = False,
    stale_after: float = STALE_AFTER_SECONDS,
) -> Path:
    """Fetch `url` to `destination`, reusing a cached copy when reasonable.

    A partial download is written to a .part file and only moved into place once
    complete, so an interrupted run never leaves a truncated file that a later
    run would mistake for a valid cache entry.
    """
    label = label or destination.name
    etag_path = destination.with_suffix(destination.suffix + ".etag")

    if destination.exists() and not refresh:
        if age_seconds(destination) < stale_after:
            return destination
        headers = {}
        if etag_path.exists():
            headers["If-None-Match"] = etag_path.read_text(encoding="utf-8").strip()
        if headers:
            try:
                response = requests.head(
                    url, headers=headers, timeout=30, allow_redirects=True
                )
                if response.status_code == 304:
                    destination.touch()  # confirmed current; reset the staleness clock
                    return destination
            except requests.RequestException:
                return destination  # offline: the cached copy is what we have

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    try:
        with requests.get(url, stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0)) or None
            with (
                partial.open("wb") as fh,
                tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=label,
                    leave=False,
                ) as bar,
            ):
                for chunk in response.iter_content(chunk_size=CHUNK):
                    fh.write(chunk)
                    bar.update(len(chunk))
            if etag := response.headers.get("ETag"):
                etag_path.write_text(etag, encoding="utf-8")
    except requests.RequestException as exc:
        partial.unlink(missing_ok=True)
        if destination.exists():
            return destination  # fall back to the stale cache rather than failing
        raise GarmapError(f"Failed to download {label} from {url}: {exc}") from exc

    partial.replace(destination)
    return destination


def human_size(num_bytes: int | None) -> str:
    if num_bytes is None:
        return "unknown size"
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GiB"
