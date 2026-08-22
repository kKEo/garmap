"""End-to-end build against the real Geofabrik data and the real Java tools.

Deselected by default (`addopts = -m 'not integration'`): it downloads hundreds
of megabytes on a cold cache and takes minutes. Run it with:

    uv run pytest -m integration

A small --buffer keeps the corridor to a couple of tiles; the extracts it needs
are cached under ~/.cache/garmap and reused between runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from garmap.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "short-route.gpx"

pytestmark = pytest.mark.integration


def _subfile_types(img: Path) -> dict[str, int]:
    """How many of each Garmin subfile type the image contains.

    NET and NOD are the routing subfiles; their absence means the map renders
    but cannot navigate, which is the failure that matters most here.
    """
    blob = img.read_bytes()
    return {name: blob.count(name.encode()) for name in ("RGN", "TRE", "NET", "NOD", "TYP")}


def test_build_produces_a_routable_img(tmp_path):
    output = tmp_path / "route.img"
    result = CliRunner().invoke(
        main,
        [
            "build",
            str(FIXTURE),
            "--buffer",
            "3km",
            "-o",
            str(output),
            "--name",
            "garmap integration",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert output.is_file()
    # A corridor this size is megabytes; anything tiny means mkgmap wrote a
    # header and no tiles.
    assert output.stat().st_size > 512 * 1024

    counts = _subfile_types(output)
    assert counts["RGN"] and counts["TRE"], counts
    assert counts["NET"] and counts["NOD"], "map is not routable"
    assert counts["TYP"], "custom TYP was not embedded"

    assert "tiles" in result.output


def test_build_with_contours(tmp_path):
    pytest.importorskip("pyhgtmap", reason="install with `uv sync --extra contours`")
    output = tmp_path / "contours.img"
    result = CliRunner().invoke(
        main,
        [
            "build",
            str(FIXTURE),
            "--buffer",
            "3km",
            "--contours",
            "--contour-step",
            "20",
            "-o",
            str(output),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "contour tile(s)" in result.output
    assert output.stat().st_size > 512 * 1024
