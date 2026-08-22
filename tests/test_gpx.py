from __future__ import annotations

import pytest

from garmap import GarmapError
from garmap.gpx import read_all, read_gpx

from .conftest import MULTI_SEGMENT_BODY, ROUTE_BODY, TRACK_BODY


def test_reads_track_segment(write_gpx):
    lines = read_gpx(write_gpx(TRACK_BODY))
    assert len(lines) == 1
    # GPX is lat/lon; shapely coords must be lon/lat.
    assert lines[0].coords[0] == (21.0, 52.0)
    assert len(lines[0].coords) == 3


def test_reads_route_when_there_is_no_track(write_gpx):
    lines = read_gpx(write_gpx(ROUTE_BODY))
    assert len(lines) == 1
    assert lines[0].coords[0] == (19.9, 50.0)


def test_each_segment_becomes_its_own_line(write_gpx):
    assert len(read_gpx(write_gpx(MULTI_SEGMENT_BODY))) == 2


def test_tracks_and_routes_are_both_collected(write_gpx):
    assert len(read_gpx(write_gpx(TRACK_BODY + "\n" + ROUTE_BODY))) == 2


def test_consecutive_duplicate_points_are_dropped(write_gpx):
    body = """\
  <trk><trkseg>
    <trkpt lat="52.0" lon="21.0"/>
    <trkpt lat="52.0" lon="21.0"/>
    <trkpt lat="52.1" lon="21.1"/>
  </trkseg></trk>"""
    assert len(read_gpx(write_gpx(body)).pop().coords) == 2


def test_single_point_segment_is_not_a_line(write_gpx):
    body = '  <trk><trkseg><trkpt lat="52.0" lon="21.0"/></trkseg></trk>'
    with pytest.raises(GarmapError, match="no usable track or route"):
        read_gpx(write_gpx(body))


def test_empty_gpx_raises(write_gpx):
    with pytest.raises(GarmapError, match="no usable track or route"):
        read_gpx(write_gpx("  <metadata><name>nothing</name></metadata>"))


def test_waypoints_alone_are_not_a_route(write_gpx):
    body = """\
  <wpt lat="52.0" lon="21.0"><name>A</name></wpt>
  <wpt lat="52.1" lon="21.1"><name>B</name></wpt>"""
    with pytest.raises(GarmapError):
        read_gpx(write_gpx(body))


def test_missing_file_raises_garmap_error(tmp_path):
    with pytest.raises(GarmapError, match="not found"):
        read_gpx(tmp_path / "nope.gpx")


def test_malformed_xml_raises_garmap_error(tmp_path):
    path = tmp_path / "bad.gpx"
    path.write_text("<gpx><trk>", encoding="utf-8")
    with pytest.raises(GarmapError, match="Could not parse"):
        read_gpx(path)


def test_read_all_flattens_multiple_files(write_gpx):
    a = write_gpx(TRACK_BODY, "a.gpx")
    b = write_gpx(MULTI_SEGMENT_BODY, "b.gpx")
    assert len(read_all([a, b])) == 3
