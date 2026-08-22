"""Compile map tiles into a routable Garmin .img."""

from __future__ import annotations

import re
import shutil
import zlib
from pathlib import Path

from . import GarmapError
from .config import CONTOUR_MAPID, OSM_MAPID
from .tools import MKGMAP, describe_command, jar_path, run_java


def family_id(map_name: str) -> int:
    """A stable family id derived from the map name.

    Every map on the device needs its own family id: sharing one with the stock
    Garmin Cycle Map makes the new map invisible or corrupts the other's
    rendering. Range 2000-65000 avoids the low ids Garmin itself uses.
    """
    return 2000 + (zlib.crc32(map_name.encode("utf-8")) % 63000)


def _args_file(
    path: Path,
    osm_tiles: list[Path],
    contour_tiles: list[Path],
) -> Path:
    """Write an explicit mapname/input-file pairing for mkgmap's -c option.

    Every tile gets an id spelled out rather than relying on mkgmap's
    auto-increment, so OSM tiles and contour tiles can never collide.
    """
    lines: list[str] = []
    for group, base in ((osm_tiles, OSM_MAPID), (contour_tiles, CONTOUR_MAPID)):
        for offset, tile in enumerate(group):
            lines.append(f"mapname: {base + offset:08d}")
            lines.append(f"input-file: {tile}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_args(
    args_file: Path,
    output_dir: Path,
    map_name: str,
    style_dir: Path,
    typ_file: Path | None = None,
    bounds_dir: Path | None = None,
    dem_dir: Path | None = None,
    drive_on: str = "detect",
    generate_sea: bool = False,
) -> list[str]:
    """mkgmap's argv for a routable, cycling-oriented map.

    Note there is no --typ-file option in mkgmap: a TYP file is passed as an
    input file and compiled on the fly if it is a .txt source. It is therefore
    listed in the args file alongside the tiles.
    """
    args = [
        # Routing: the whole point of a map for a navigation-capable Edge.
        "--route",
        f"--drive-on={drive_on}",
        "--link-pois-to-ways",
        "--add-pois-to-areas",
        "--process-destination",
        "--process-exits",
        # Searchability.
        "--index",
        "--housenumbers",
        "--location-autofill=is_in,nearest",
        # Rendering.
        f"--style-file={style_dir}",
        # Identity: a unique family keeps this map from clashing with the stock
        # Garmin maps or with other garmap outputs already on the device.
        f"--family-id={family_id(map_name)}",
        "--product-id=1",
        f"--family-name={map_name}",
        f"--series-name={map_name}",
        f"--description={map_name}",
        "--area-name=garmap",
        "--overview-mapname=overview",
        # Output.
        f"--output-dir={output_dir}",
        "--gmapsupp",
        "--max-jobs",
    ]
    if bounds_dir is not None:
        args.append(f"--bounds={bounds_dir}")
    if dem_dir is not None:
        # DEM gives the Edge shaded relief and elevation readouts off-route.
        args += [f"--dem={dem_dir}", "--dem-dists=3312,13248"]
    if generate_sea:
        args.append(
            "--generate-sea=multipolygon,extend-sea-sectors,close-gaps=6000,floodblocker"
        )
    # `-c` takes a separate argument; only the long form accepts `=`.
    args.append(f"--read-config={args_file}")
    if typ_file is not None:
        args.append(str(typ_file))
    return args


TILE_IMAGE = re.compile(r"^\d{8}\.img$")


def _tile_count(output_dir: Path) -> int:
    """How many map tiles mkgmap actually compiled.

    Counted from the files on disk rather than scraped from the log: mkgmap says
    very little on stdout unless its loggers are configured, and it exits 0 even
    when it compiled nothing.  `overview.img`, `ovm_*.img` and `gmapsupp.img`
    are not tiles.
    """
    return sum(1 for p in output_dir.glob("*.img") if TILE_IMAGE.match(p.name))


def compile_map(
    osm_tiles: list[Path],
    contour_tiles: list[Path],
    output_dir: Path,
    map_name: str,
    output: Path,
    style_dir: Path,
    typ_file: Path | None = None,
    bounds_dir: Path | None = None,
    dem_dir: Path | None = None,
    drive_on: str = "detect",
    generate_sea: bool = False,
    verbose: bool = False,
) -> tuple[Path, int]:
    """Compile the tiles and move the result to `output`. Returns (path, tiles)."""
    if not osm_tiles:
        raise GarmapError("No OSM tiles to compile.")
    output_dir.mkdir(parents=True, exist_ok=True)

    args_file = _args_file(output_dir / "mkgmap.args", osm_tiles, contour_tiles)
    run_java(
        jar_path(MKGMAP),
        build_args(
            args_file,
            output_dir,
            map_name,
            style_dir=style_dir,
            typ_file=typ_file,
            bounds_dir=bounds_dir,
            dem_dir=dem_dir,
            drive_on=drive_on,
            generate_sea=generate_sea,
        ),
        cwd=output_dir,
        verbose=verbose,
    )

    produced = output_dir / "gmapsupp.img"
    if not produced.is_file():
        raise GarmapError(
            "mkgmap finished but produced no gmapsupp.img. Re-run with --verbose "
            "to see its output."
        )

    written = _tile_count(output_dir)
    if written == 0:
        # mkgmap exits 0 and still writes a header-only gmapsupp.img when it
        # rejects an option, so an empty result has to be caught here rather
        # than by the return code.
        raise GarmapError(
            "mkgmap wrote no map tiles, so the .img would be empty. Re-run with "
            "--verbose to see its output."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    # shutil.move, not Path.replace: the work dir is often a temp dir on a
    # different filesystem from the output.
    shutil.move(str(produced), str(output))
    return output, written


def dry_run_command(output_dir: Path, map_name: str, style_dir: Path, **kwargs) -> list[str]:
    return describe_command(
        jar_path(MKGMAP),
        build_args(
            output_dir / "mkgmap.args", output_dir, map_name, style_dir, **kwargs
        ),
    )
