"""mkgmap argv, args-file layout, family ids and the empty-output guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from garmap import GarmapError, mkgmap
from garmap.config import CONTOUR_MAPID, OSM_MAPID


def test_family_id_is_stable_and_in_range():
    first = mkgmap.family_id("Podhale test")
    assert first == mkgmap.family_id("Podhale test")
    assert first != mkgmap.family_id("Alps tour")
    assert 2000 <= first <= 65000


def test_args_file_pairs_every_tile_with_an_explicit_id(tmp_path):
    """Relying on mkgmap's auto-increment would let contour tiles land on ids
    already used by OSM tiles."""
    path = mkgmap._args_file(
        tmp_path / "mkgmap.args",
        [Path("/tiles/pass0/a.osm.pbf"), Path("/tiles/pass1/b.osm.pbf")],
        [Path("/contours/c.osm.pbf")],
    )
    assert path.read_text(encoding="utf-8").splitlines() == [
        f"mapname: {OSM_MAPID}",
        "input-file: /tiles/pass0/a.osm.pbf",
        f"mapname: {OSM_MAPID + 1}",
        "input-file: /tiles/pass1/b.osm.pbf",
        f"mapname: {CONTOUR_MAPID}",
        "input-file: /contours/c.osm.pbf",
    ]


def test_argv_enables_routing_and_a_unique_family():
    args = mkgmap.build_args(
        Path("/work/mkgmap.args"),
        Path("/work/out"),
        "Podhale test",
        style_dir=Path("/work/style"),
    )
    assert "--route" in args
    assert "--index" in args
    assert "--gmapsupp" in args
    assert f"--family-id={mkgmap.family_id('Podhale test')}" in args
    assert "--style-file=/work/style" in args
    # `-c` needs a separate argument; only the long form accepts `=`.
    assert "--read-config=/work/mkgmap.args" in args


def test_typ_file_is_an_input_not_an_option():
    """mkgmap has no --typ-file: a .txt TYP source is passed as an input file
    and compiled on the fly."""
    args = mkgmap.build_args(
        Path("/work/mkgmap.args"),
        Path("/work/out"),
        "Map",
        style_dir=Path("/work/style"),
        typ_file=Path("/work/cycle.txt"),
    )
    assert args[-1] == "/work/cycle.txt"
    assert not any(a.startswith("--typ") for a in args)


def test_dem_requires_its_distance_list():
    args = mkgmap.build_args(
        Path("/a"), Path("/b"), "Map", style_dir=Path("/s"), dem_dir=Path("/hgt")
    )
    assert "--dem=/hgt" in args
    assert any(a.startswith("--dem-dists=") for a in args)


def _fake_mkgmap(monkeypatch, tmp_path, tile_ids):
    monkeypatch.setattr(mkgmap, "jar_path", lambda tool: tmp_path / "mkgmap.jar")

    def fake_run_java(jar, args, cwd, **kwargs):
        out = Path(next(a for a in args if a.startswith("--output-dir=")).split("=", 1)[1])
        for tile_id in tile_ids:
            (out / f"{tile_id}.img").write_bytes(b"tile")
            (out / f"ovm_{tile_id}.img").write_bytes(b"overview tile")
        (out / "overview.img").write_bytes(b"overview")
        (out / "gmapsupp.img").write_bytes(b"combined")
        return "mkgmap says very little on stdout"

    monkeypatch.setattr(mkgmap, "run_java", fake_run_java)


def test_compile_moves_the_gmapsupp_and_counts_only_tiles(monkeypatch, tmp_path):
    _fake_mkgmap(monkeypatch, tmp_path, [OSM_MAPID, OSM_MAPID + 1, CONTOUR_MAPID])
    output = tmp_path / "out" / "podhale.img"

    path, tiles = mkgmap.compile_map(
        [tmp_path / "a.osm.pbf", tmp_path / "b.osm.pbf"],
        [tmp_path / "c.osm.pbf"],
        tmp_path / "work",
        "Podhale test",
        output,
        style_dir=tmp_path / "style",
    )

    assert path == output
    assert output.read_bytes() == b"combined"
    # overview.img, ovm_*.img and gmapsupp.img are not map tiles.
    assert tiles == 3


def test_empty_output_is_an_error_even_though_mkgmap_exits_zero(monkeypatch, tmp_path):
    """mkgmap ignores an unrecognised option, still writes a header-only
    gmapsupp.img, and exits 0 -- so the return code cannot be trusted."""
    _fake_mkgmap(monkeypatch, tmp_path, [])

    with pytest.raises(GarmapError, match="no map tiles"):
        mkgmap.compile_map(
            [tmp_path / "a.osm.pbf"],
            [],
            tmp_path / "work",
            "Map",
            tmp_path / "out.img",
            style_dir=tmp_path / "style",
        )


def test_no_tiles_is_rejected_before_running_java(tmp_path):
    with pytest.raises(GarmapError, match="No OSM tiles"):
        mkgmap.compile_map(
            [], [], tmp_path / "work", "Map", tmp_path / "out.img",
            style_dir=tmp_path / "style",
        )
