"""Buffer a route into a coverage corridor and emit it as a .poly clip file."""

from __future__ import annotations

from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import transform, unary_union

from . import GarmapError

# A route corridor is at most a few hundred km across, so a local azimuthal
# equidistant projection centred on the route is accurate enough to buffer in
# metres without the distortion a global projection would introduce.
_WGS84 = CRS.from_epsg(4326)


def _local_crs(lon: float, lat: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
    )


def build_corridor(lines: list[LineString], buffer_metres: float) -> MultiPolygon:
    """Buffer route lines by `buffer_metres` and return the merged corridor.

    Interior rings are stripped: splitter r654 does not handle holes in .poly
    files, and a loop route buffers into exactly that shape. Keeping the hole
    would make splitter silently drop data in the middle of the loop.
    """
    if not lines:
        raise GarmapError("No route geometry to build a corridor from.")
    if buffer_metres <= 0:
        raise GarmapError(f"Buffer must be positive, got {buffer_metres} m.")

    merged = unary_union(lines)
    centroid = merged.centroid
    local = _local_crs(centroid.x, centroid.y)
    to_local = Transformer.from_crs(_WGS84, local, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(local, _WGS84, always_xy=True).transform

    buffered = transform(to_local, merged).buffer(buffer_metres, quad_segs=8)
    corridor = transform(to_wgs84, buffered)

    parts = list(corridor.geoms) if isinstance(corridor, MultiPolygon) else [corridor]
    return MultiPolygon([Polygon(p.exterior) for p in parts])


def bbox(geom) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat)."""
    return geom.bounds


def write_poly(corridor: MultiPolygon, path: Path, name: str = "corridor") -> Path:
    """Write the corridor in the osmosis/mkgmap .poly format.

    Format: a name line, then one numbered section per ring, each a list of
    "lon lat" pairs terminated by END, with a final END for the file.
    """
    lines = [name]
    for i, poly in enumerate(corridor.geoms, start=1):
        lines.append(str(i))
        for lon, lat in poly.exterior.coords:
            lines.append(f"   {lon:.7E}   {lat:.7E}")
        lines.append("END")
    lines.append("END")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def area_km2(corridor: MultiPolygon) -> float:
    """Approximate corridor area, for reporting and download-size sanity checks."""
    centroid = corridor.centroid
    to_local = Transformer.from_crs(
        _WGS84, _local_crs(centroid.x, centroid.y), always_xy=True
    ).transform
    return transform(to_local, corridor).area / 1_000_000
