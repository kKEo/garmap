"""Clip the downloaded extracts to the corridor and split them into map tiles.

splitter is run once per extract rather than once over all of them. It refuses a
multi-file run whose node ids are not globally sorted -- and two Geofabrik
extracts never are, since each is sorted only within itself:

    Error: Node ids are not sorted. Use e.g. osmosis to sort the input data.
    This is not supported with keep-complete=true or --problem-list

The alternatives are merging the extracts first (which would mean depending on
osmosis or osmium, the dependency garmap exists to avoid) or dropping
--keep-complete, which silently truncates ways and relations at tile edges and
so damages routing. One pass per extract keeps both, at the cost of a thin strip
of duplicated data where two extracts overlap at a border.
"""

from __future__ import annotations

from pathlib import Path

from . import GarmapError
from .config import CONTOUR_MAPID, DEFAULT_MAX_NODES, OSM_MAPID
from .tools import SPLITTER, describe_command, jar_path, run_java

# Map ids each pass may use before it would collide with the next pass.
MAPID_BLOCK = 1000
MAX_PASSES = (CONTOUR_MAPID - OSM_MAPID) // MAPID_BLOCK


def build_args(
    extracts: list[Path],
    poly_file: Path,
    output_dir: Path,
    max_nodes: int = DEFAULT_MAX_NODES,
    mapid: int = OSM_MAPID,
) -> list[str]:
    """splitter's argv for one pass.

    --polygon-file is what actually clips the data to the route corridor, which
    is why garmap needs no osmium/osmconvert dependency.
    """
    return [
        f"--polygon-file={poly_file}",
        f"--output-dir={output_dir}",
        "--output=pbf",
        f"--max-nodes={max_nodes}",
        f"--mapid={mapid}",
        "--keep-complete=true",
        "--description=garmap",
        *(str(path) for path in extracts),
    ]


def tiles_in(output_dir: Path) -> list[Path]:
    """Tile files splitter produced, in map-id order."""
    return sorted(
        p
        for p in output_dir.rglob("*.osm.pbf")
        if p.stem.split(".")[0].isdigit()
    )


def split(
    extracts: list[Path],
    poly_file: Path,
    output_dir: Path,
    max_nodes: int = DEFAULT_MAX_NODES,
    mapid: int = OSM_MAPID,
    verbose: bool = False,
) -> list[Path]:
    """Clip and split every extract; return all resulting tile files."""
    if not extracts:
        raise GarmapError("No OSM extracts to split.")
    if len(extracts) > MAX_PASSES:
        raise GarmapError(
            f"{len(extracts)} extracts exceeds the {MAX_PASSES} map-id blocks "
            "reserved for OSM tiles. Use a smaller --buffer."
        )

    tiles: list[Path] = []
    for index, extract in enumerate(extracts):
        # A directory per pass: splitter writes areas.list, template.args and
        # densities-out.txt with fixed names that a second pass would overwrite.
        pass_dir = output_dir / f"pass{index}"
        pass_dir.mkdir(parents=True, exist_ok=True)
        run_java(
            jar_path(SPLITTER),
            build_args(
                [extract],
                poly_file,
                pass_dir,
                max_nodes,
                mapid + index * MAPID_BLOCK,
            ),
            cwd=pass_dir,
            verbose=verbose,
        )
        produced = tiles_in(pass_dir)
        if len(produced) > MAPID_BLOCK:
            raise GarmapError(
                f"{extract.name} split into {len(produced)} tiles, more than the "
                f"{MAPID_BLOCK} map ids reserved per extract. Use a smaller "
                "--buffer."
            )
        tiles.extend(produced)

    if not tiles:
        raise GarmapError(
            "splitter produced no tiles. The corridor probably falls outside the "
            "downloaded extracts -- run `garmap preview` to check coverage."
        )
    return tiles


def dry_run_command(
    extracts: list[Path],
    poly_file: Path,
    output_dir: Path,
    max_nodes: int = DEFAULT_MAX_NODES,
    mapid: int = OSM_MAPID,
) -> list[str]:
    return describe_command(
        jar_path(SPLITTER),
        build_args(extracts, poly_file, output_dir, max_nodes, mapid),
    )
