"""Turn GPX files into route geometry."""

from __future__ import annotations

from pathlib import Path

import gpxpy
from shapely.geometry import LineString

from . import GarmapError


def _line(points) -> LineString | None:
    """Build a LineString from gpxpy points, dropping consecutive duplicates.

    Returns None for anything that can't form a line (0 or 1 distinct points).
    """
    coords: list[tuple[float, float]] = []
    for p in points:
        xy = (p.longitude, p.latitude)
        if not coords or coords[-1] != xy:
            coords.append(xy)
    return LineString(coords) if len(coords) >= 2 else None


def read_gpx(path: Path) -> list[LineString]:
    """Extract every track segment and route from a GPX file, as WGS84 lines.

    Waypoints are ignored: a bag of unordered points is not a route corridor.
    """
    try:
        with path.open(encoding="utf-8") as fh:
            gpx = gpxpy.parse(fh)
    except FileNotFoundError:
        raise GarmapError(f"GPX file not found: {path}") from None
    except Exception as exc:  # gpxpy raises a variety of parse errors
        raise GarmapError(f"Could not parse GPX file {path}: {exc}") from exc

    lines: list[LineString] = []
    for track in gpx.tracks:
        for segment in track.segments:
            if (line := _line(segment.points)) is not None:
                lines.append(line)
    for route in gpx.routes:
        if (line := _line(route.points)) is not None:
            lines.append(line)

    if not lines:
        raise GarmapError(
            f"{path} contains no usable track or route geometry. "
            "garmap needs at least one <trkseg> or <rte> with two or more distinct points."
        )
    return lines


def read_all(paths: list[Path] | tuple[Path, ...]) -> list[LineString]:
    """Read several GPX files into one flat list of lines."""
    lines: list[LineString] = []
    for path in paths:
        lines.extend(read_gpx(path))
    return lines
