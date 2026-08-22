"""Generate contour lines for the corridor with pyhgtmap."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import GarmapError
from .config import DEFAULT_CONTOUR_STEP, hgt_dir

# Viewfinder Panoramas needs no credentials and covers the whole world at 3",
# including the voids and the >60degN gap in NASA SRTM. `srtm1`/`srtm3` would
# need a USGS EarthExplorer account, which is a bad first-run experience.
DEFAULT_SOURCE = "view1,view3"

# Simplification tolerance in degrees. Upstream benchmarking puts 1e-5 as
# visually indistinguishable from unsimplified while roughly halving node count
# -- which is what keeps the .img small enough for a bike computer.
SIMPLIFY_EPSILON = 0.00001


def available() -> bool:
    return _executable() is not None


def _executable() -> list[str] | None:
    """How to invoke pyhgtmap: as a console script, or as a module."""
    if found := shutil.which("pyhgtmap"):
        return [found]
    try:
        subprocess.run(
            [sys.executable, "-m", "pyhgtmap", "--help"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return [sys.executable, "-m", "pyhgtmap"]


def build_args(
    poly_file: Path,
    step: int = DEFAULT_CONTOUR_STEP,
    source: str = DEFAULT_SOURCE,
    jobs: int | None = None,
    hgt_cache: Path | None = None,
) -> list[str]:
    """pyhgtmap's argv."""
    return [
        f"--polygon={poly_file}",
        f"--step={step}",
        # Major every 100 m, medium every 50 m: matches the elevation_major /
        # _medium / _minor tags garmap's contour style rules expect.
        "--line-cat=100,50",
        f"--sources={source}",
        f"--hgtdir={hgt_cache or hgt_dir()}",
        f"--simplifyContoursEpsilon={SIMPLIFY_EPSILON}",
        "--pbf",
        "--start-node-id=20000000000",
        "--start-way-id=20000000000",
        f"--jobs={jobs or os.cpu_count() or 4}",
    ]


def generate(
    poly_file: Path,
    output_dir: Path,
    step: int = DEFAULT_CONTOUR_STEP,
    source: str = DEFAULT_SOURCE,
    jobs: int | None = None,
    verbose: bool = False,
) -> list[Path]:
    """Produce contour tiles for the corridor. Returns the .osm.pbf files."""
    executable = _executable()
    if executable is None:
        raise GarmapError(
            "pyhgtmap is not installed, so contour lines cannot be generated.\n"
            "Install it with `uv sync --extra contours` (or `pip install pyhgtmap`), "
            "or re-run without --contours."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    (hgt_dir()).mkdir(parents=True, exist_ok=True)

    command = executable + build_args(poly_file, step, source, jobs)
    result = subprocess.run(
        command,
        cwd=output_dir,
        capture_output=not verbose,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        tail = "\n".join(detail.splitlines()[-15:])
        raise GarmapError(
            "pyhgtmap failed to generate contour lines"
            + (f":\n{tail}" if tail else ".")
            + "\n\nElevation data hosting is occasionally unavailable. You can "
            "re-run without --contours to build the map without them."
        )

    tiles = sorted(output_dir.glob("*.osm.pbf"))
    if not tiles:
        raise GarmapError(
            "pyhgtmap reported success but produced no contour tiles. The "
            "corridor may be entirely over water, or outside the elevation "
            "dataset's coverage."
        )
    return tiles
