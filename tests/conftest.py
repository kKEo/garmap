from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


_TEMPLATE = textwrap.dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
    {body}
    </gpx>
    """
)


def _gpx(body: str) -> str:
    # Interpolate *after* dedent -- the body carries its own indentation, which
    # would otherwise skew dedent's common-prefix calculation.
    return _TEMPLATE.format(body=body)


@pytest.fixture
def write_gpx(tmp_path: Path):
    """Write a GPX file from a body fragment and return its path."""

    def _write(body: str, name: str = "route.gpx") -> Path:
        path = tmp_path / name
        path.write_text(_gpx(body), encoding="utf-8")
        return path

    return _write


TRACK_BODY = """\
  <trk><name>Track</name><trkseg>
    <trkpt lat="52.0" lon="21.0"/>
    <trkpt lat="52.1" lon="21.1"/>
    <trkpt lat="52.2" lon="21.2"/>
  </trkseg></trk>"""

ROUTE_BODY = """\
  <rte><name>Route</name>
    <rtept lat="50.0" lon="19.9"/>
    <rtept lat="50.1" lon="20.0"/>
  </rte>"""

MULTI_SEGMENT_BODY = """\
  <trk><trkseg>
    <trkpt lat="52.0" lon="21.0"/>
    <trkpt lat="52.1" lon="21.1"/>
  </trkseg><trkseg>
    <trkpt lat="52.5" lon="21.5"/>
    <trkpt lat="52.6" lon="21.6"/>
  </trkseg></trk>"""
