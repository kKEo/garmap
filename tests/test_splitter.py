"""splitter argv and the one-pass-per-extract behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

from garmap import GarmapError, splitter
from garmap.config import OSM_MAPID


def test_argv_clips_with_the_polygon_file():
    args = splitter.build_args(
        [Path("/cache/poland.osm.pbf")],
        Path("/work/corridor.poly"),
        Path("/work/tiles"),
        max_nodes=1_400_000,
    )
    assert args == [
        "--polygon-file=/work/corridor.poly",
        "--output-dir=/work/tiles",
        "--output=pbf",
        "--max-nodes=1400000",
        f"--mapid={OSM_MAPID}",
        "--keep-complete=true",
        "--description=garmap",
        "/cache/poland.osm.pbf",
    ]


@pytest.fixture
def fake_splitter(monkeypatch, tmp_path):
    """Record each invocation and drop plausible tiles in the output dir."""
    runs: list[list[str]] = []

    def fake_run_java(jar, args, cwd, **kwargs):
        runs.append(args)
        mapid = int(next(a for a in args if a.startswith("--mapid=")).split("=")[1])
        out = Path(next(a for a in args if a.startswith("--output-dir=")).split("=", 1)[1])
        for offset in range(2):
            (out / f"{mapid + offset}.osm.pbf").write_bytes(b"tile")
        # splitter also writes these fixed-name reports next to the tiles.
        (out / "areas.list").write_text("")
        return ""

    monkeypatch.setattr(splitter, "jar_path", lambda tool: tmp_path / "splitter.jar")
    monkeypatch.setattr(splitter, "run_java", fake_run_java)
    return runs


def test_each_extract_gets_its_own_pass_and_mapid_block(fake_splitter, tmp_path):
    """splitter refuses a multi-file run whose node ids are not globally sorted,
    which two Geofabrik extracts never are."""
    extracts = [tmp_path / "malopolskie.osm.pbf", tmp_path / "slovakia.osm.pbf"]
    for extract in extracts:
        extract.write_bytes(b"pbf")

    tiles = splitter.split(extracts, tmp_path / "corridor.poly", tmp_path / "tiles")

    assert len(fake_splitter) == 2
    assert [a for a in fake_splitter[0] if a.startswith("--mapid")] == [
        f"--mapid={OSM_MAPID}"
    ]
    assert [a for a in fake_splitter[1] if a.startswith("--mapid")] == [
        f"--mapid={OSM_MAPID + splitter.MAPID_BLOCK}"
    ]
    # One extract per pass, never both on one command line.
    assert str(extracts[0]) in fake_splitter[0]
    assert str(extracts[1]) not in fake_splitter[0]
    assert len(tiles) == 4


def test_passes_get_separate_directories(fake_splitter, tmp_path):
    """areas.list and template.args have fixed names a second pass would clobber."""
    extracts = [tmp_path / "a.osm.pbf", tmp_path / "b.osm.pbf"]
    for extract in extracts:
        extract.write_bytes(b"pbf")

    splitter.split(extracts, tmp_path / "corridor.poly", tmp_path / "tiles")

    assert (tmp_path / "tiles" / "pass0" / "areas.list").is_file()
    assert (tmp_path / "tiles" / "pass1" / "areas.list").is_file()


def test_no_tiles_points_at_the_coverage_check(monkeypatch, tmp_path):
    monkeypatch.setattr(splitter, "jar_path", lambda tool: tmp_path / "splitter.jar")
    monkeypatch.setattr(splitter, "run_java", lambda *a, **k: "")
    (tmp_path / "extract.osm.pbf").write_bytes(b"pbf")

    with pytest.raises(GarmapError, match="garmap preview"):
        splitter.split(
            [tmp_path / "extract.osm.pbf"],
            tmp_path / "corridor.poly",
            tmp_path / "tiles",
        )


def test_no_extracts_is_rejected(tmp_path):
    with pytest.raises(GarmapError, match="No OSM extracts"):
        splitter.split([], tmp_path / "corridor.poly", tmp_path / "tiles")


def test_more_extracts_than_mapid_blocks_is_rejected(tmp_path):
    extracts = [tmp_path / f"{i}.osm.pbf" for i in range(splitter.MAX_PASSES + 1)]
    with pytest.raises(GarmapError, match="map-id blocks"):
        splitter.split(extracts, tmp_path / "corridor.poly", tmp_path / "tiles")
