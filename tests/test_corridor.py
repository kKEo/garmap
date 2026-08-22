from __future__ import annotations

import math

import pytest
from pyproj import Geod
from shapely.geometry import LineString, MultiPolygon, Point

from garmap import GarmapError
from garmap.corridor import area_km2, build_corridor, write_poly

GEOD = Geod(ellps="WGS84")


def test_corridor_contains_the_route():
    line = LineString([(21.0, 52.0), (21.5, 52.3)])
    corridor = build_corridor([line], 5_000)
    assert corridor.contains(line)


def test_buffer_distance_is_metres_on_the_ground():
    """A point 9 km off the route must be inside a 10 km corridor, and one at 11 km out."""
    line = LineString([(21.0, 52.0), (21.5, 52.0)])
    corridor = build_corridor([line], 10_000)
    mid_lon, mid_lat = 21.25, 52.0
    for distance, expected_inside in ((9_000, True), (11_000, False)):
        lon, lat, _ = GEOD.fwd(mid_lon, mid_lat, 0, distance)  # due north
        assert corridor.contains(Point(lon, lat)) is expected_inside, distance


def test_buffer_edge_is_close_to_the_requested_distance():
    line = LineString([(21.0, 52.0), (21.5, 52.0)])
    corridor = build_corridor([line], 10_000)
    lon, lat, _ = GEOD.fwd(21.25, 52.0, 0, 10_000)
    # The polygon boundary should sit within a few hundred metres of the target.
    ring = corridor.geoms[0].exterior
    nearest = ring.interpolate(ring.project(Point(lon, lat)))
    _, _, error = GEOD.inv(lon, lat, nearest.x, nearest.y)
    assert error < 300, f"buffer edge off by {error:.0f} m"


def test_loop_route_corridor_has_no_holes():
    """Regression: splitter r654 mishandles holes, so the inner ring must be dropped."""
    # A square loop ~20 km on a side; a 2 km buffer leaves an untouched middle.
    loop = LineString([(21.0, 52.0), (21.3, 52.0), (21.3, 52.2), (21.0, 52.2), (21.0, 52.0)])
    corridor = build_corridor([loop], 2_000)
    assert len(corridor.geoms) == 1
    poly = corridor.geoms[0]
    assert len(poly.interiors) == 0
    # And the middle of the loop is therefore covered.
    assert poly.contains(Point(21.15, 52.1))


def test_distant_routes_stay_separate_polygons():
    a = LineString([(21.0, 52.0), (21.1, 52.0)])
    b = LineString([(2.3, 48.8), (2.4, 48.8)])  # Paris, far from Warsaw
    corridor = build_corridor([a, b], 5_000)
    assert len(corridor.geoms) == 2


def test_nearby_routes_merge_into_one_polygon():
    a = LineString([(21.0, 52.0), (21.1, 52.0)])
    b = LineString([(21.0, 52.01), (21.1, 52.01)])
    assert len(build_corridor([a, b], 5_000).geoms) == 1


def test_always_returns_a_multipolygon():
    corridor = build_corridor([LineString([(21.0, 52.0), (21.1, 52.1)])], 1_000)
    assert isinstance(corridor, MultiPolygon)


def test_empty_input_raises():
    with pytest.raises(GarmapError, match="No route geometry"):
        build_corridor([], 5_000)


@pytest.mark.parametrize("buffer_metres", [0, -1])
def test_non_positive_buffer_raises(buffer_metres):
    with pytest.raises(GarmapError, match="must be positive"):
        build_corridor([LineString([(21.0, 52.0), (21.1, 52.1)])], buffer_metres)


def test_poly_file_format(tmp_path):
    corridor = build_corridor([LineString([(21.0, 52.0), (21.1, 52.0)])], 1_000)
    path = write_poly(corridor, tmp_path / "c.poly", name="myroute")
    text = path.read_text()
    lines = text.splitlines()

    assert lines[0] == "myroute"
    assert lines[1] == "1"  # first ring section
    assert lines[-1] == "END"  # file terminator
    assert lines[-2] == "END"  # ring terminator
    assert text.count("\nEND") == 2
    # Coordinate lines are "lon lat" in scientific notation.
    lon, lat = lines[2].split()
    assert 20.9 < float(lon) < 21.2
    assert 51.9 < float(lat) < 52.1


def test_poly_file_has_one_section_per_polygon(tmp_path):
    a = LineString([(21.0, 52.0), (21.1, 52.0)])
    b = LineString([(2.3, 48.8), (2.4, 48.8)])
    path = write_poly(build_corridor([a, b], 5_000), tmp_path / "c.poly")
    lines = path.read_text().splitlines()
    assert "1" in lines and "2" in lines
    assert lines.count("END") == 3  # two rings + file terminator


def test_poly_rings_are_closed(tmp_path):
    corridor = build_corridor([LineString([(21.0, 52.0), (21.1, 52.0)])], 1_000)
    path = write_poly(corridor, tmp_path / "c.poly")
    coords = [l for l in path.read_text().splitlines() if l.startswith("   ")]
    assert coords[0] == coords[-1]


def test_area_km2_is_plausible():
    # A 100 km straight route with a 10 km buffer: ~2*10*100 + pi*10^2 = 2314 km2.
    line = LineString([(21.0, 52.0), (21.0, 52.9)])  # ~100 km north
    area = area_km2(build_corridor([line], 10_000))
    assert math.isclose(area, 2300, rel_tol=0.1), area
