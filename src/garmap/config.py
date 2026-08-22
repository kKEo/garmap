"""Cache locations and pinned upstream tool versions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Pinned because mkgmap.org.uk offers no "latest" alias -- the version number is
# part of the download URL. Bump these deliberately.
MKGMAP_VERSION = "4924"
SPLITTER_VERSION = "654"

MKGMAP_URL = f"https://www.mkgmap.org.uk/download/mkgmap-r{MKGMAP_VERSION}.zip"
SPLITTER_URL = f"https://www.mkgmap.org.uk/download/splitter-r{SPLITTER_VERSION}.zip"

GEOFABRIK_INDEX_URL = "https://download.geofabrik.de/index-v1.json"
GEOFABRIK_INDEX_TTL_SECONDS = 7 * 24 * 3600

# splitter chokes on very large tiles; this is the value the mkgmap docs recommend.
DEFAULT_MAX_NODES = 1_400_000

DEFAULT_BUFFER_METRES = 15_000.0
DEFAULT_CONTOUR_STEP = 10

# mkgmap map ids must be 8 digits. Keep OSM tiles and contour tiles in separate
# ranges so a tile id is never reused across the two inputs.
OSM_MAPID = 63240001
CONTOUR_MAPID = 63250001


def cache_dir() -> Path:
    """Root of garmap's cache, honouring XDG_CACHE_HOME."""
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "garmap"


def jars_dir() -> Path:
    return cache_dir() / "jars"


def extracts_dir() -> Path:
    return cache_dir() / "geofabrik"


def hgt_dir() -> Path:
    return cache_dir() / "hgt"


@dataclass(frozen=True)
class BuildSettings:
    """Everything `garmap build` needs, resolved from CLI options."""

    gpx_paths: tuple[Path, ...]
    output: Path
    buffer_metres: float
    map_name: str
    contours: bool
    contour_step: int
    contour_source: str
    style: str | None
    max_nodes: int
    work_dir: Path
    keep_work: bool
    jobs: int
