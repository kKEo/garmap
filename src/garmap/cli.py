"""garmap command line interface."""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

import click

from . import GarmapError, __version__
from .config import (
    DEFAULT_BUFFER_METRES,
    DEFAULT_CONTOUR_STEP,
    DEFAULT_MAX_NODES,
    cache_dir,
    extracts_dir,
    hgt_dir,
    jars_dir,
)
from .http import human_size

BUFFER_PATTERN = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*(km|m)?\s*$", re.IGNORECASE)


def parse_buffer(value: str) -> float:
    """'15km' / '15000m' / '15000' -> metres."""
    match = BUFFER_PATTERN.match(value)
    if not match:
        raise click.BadParameter(
            f"{value!r} is not a distance. Use e.g. '15km', '2500m' or '2500'."
        )
    amount = float(match.group(1))
    metres = amount * 1000 if (match.group(2) or "m").lower() == "km" else amount
    if metres <= 0:
        raise click.BadParameter("Buffer must be greater than zero.")
    return metres


class BufferParam(click.ParamType):
    name = "distance"

    def convert(self, value, param, ctx):
        return parse_buffer(str(value))


def default_map_name(gpx_paths: tuple[Path, ...]) -> str:
    """A human-readable map name derived from the GPX filename(s)."""
    stem = gpx_paths[0].stem
    name = re.sub(r"[_-]+", " ", stem).strip() or "garmap route"
    if len(gpx_paths) > 1:
        name = f"{name} +{len(gpx_paths) - 1}"
    # mkgmap writes these into fixed-width header fields; keep them short.
    return name[:40]


def echo_step(message: str) -> None:
    click.secho(f"==> {message}", fg="cyan", bold=True)


# --------------------------------------------------------------------------- #


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="garmap")
def main() -> None:
    """Build routable, cycling-tuned Garmin .img maps covering a GPX route.

    \b
    Typical use:
      garmap preview tour.gpx --buffer 15km   # check coverage first
      garmap build tour.gpx --buffer 15km --contours -o tour.img
      garmap install tour.img
    """


# --------------------------------------------------------------------------- #


def _corridor_for(gpx_paths, buffer_metres):
    """Shared front half of build/preview: GPX -> corridor -> chosen extracts."""
    from .corridor import area_km2, build_corridor
    from .geofabrik import coverage_fraction, load_index, select_regions
    from .gpx import read_all

    lines = read_all(list(gpx_paths))
    total_km = sum(_length_km(line) for line in lines)
    click.echo(
        f"    {len(lines)} route segment(s), {total_km:.0f} km of track"
    )

    corridor = build_corridor(lines, buffer_metres)
    click.echo(
        f"    corridor: {area_km2(corridor):,.0f} km2 "
        f"({buffer_metres / 1000:g} km either side)"
    )

    echo_step("Choosing OSM extracts")
    regions = select_regions(corridor, load_index())
    coverage = coverage_fraction(corridor, regions)
    for region in regions:
        click.echo(f"    {region.name} ({region.id})")
    if coverage < 0.999:
        click.secho(
            f"    warning: extracts cover {coverage:.1%} of the corridor; "
            "the edges of the map may be missing data.",
            fg="yellow",
        )
    return lines, corridor, regions


def _length_km(line) -> float:
    from pyproj import Geod

    geod = Geod(ellps="WGS84")
    return geod.geometry_length(line) / 1000


# --------------------------------------------------------------------------- #


@main.command()
@click.argument(
    "gpx", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path)
)
@click.option(
    "--buffer",
    "buffer_metres",
    type=BufferParam(),
    default=f"{DEFAULT_BUFFER_METRES:.0f}m",
    show_default="15km",
    help="How far either side of the route to include.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output .img path.  [default: <gpx name>.img]",
)
@click.option("--name", "map_name", help="Map name shown on the device.")
@click.option("--contours/--no-contours", default=False, help="Add contour lines.")
@click.option(
    "--contour-step",
    default=DEFAULT_CONTOUR_STEP,
    show_default=True,
    help="Contour interval in metres.",
)
@click.option(
    "--dem/--no-dem",
    default=False,
    help="Embed elevation data for shaded relief (needs --contours to have "
    "downloaded the HGT tiles, and makes the map noticeably bigger).",
)
@click.option(
    "--drive-on",
    type=click.Choice(["detect", "left", "right"]),
    default="detect",
    show_default=True,
    help="Driving side for routing. 'detect' needs boundary data in the "
    "corridor; set it explicitly for left-hand-traffic countries.",
)
@click.option("--sea", is_flag=True, help="Generate sea polygons (coastal routes).")
@click.option(
    "--bounds",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Precompiled mkgmap bounds directory, for address search.",
)
@click.option(
    "--max-nodes", default=DEFAULT_MAX_NODES, show_default=True, help="Nodes per tile."
)
@click.option("--refresh", is_flag=True, help="Re-download cached OSM extracts.")
@click.option(
    "--work-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Where to put intermediates.  [default: a temporary directory]",
)
@click.option("--keep-work", is_flag=True, help="Keep intermediates for debugging.")
@click.option("-v", "--verbose", is_flag=True, help="Stream mkgmap/splitter output.")
def build(
    gpx,
    buffer_metres,
    output,
    map_name,
    contours,
    contour_step,
    dem,
    drive_on,
    sea,
    bounds,
    max_nodes,
    refresh,
    work_dir,
    keep_work,
    verbose,
):
    """Build a Garmin .img covering the route(s) in GPX."""
    from . import contours as contours_mod
    from . import geofabrik, mkgmap, splitter, style
    from .corridor import write_poly
    from .tools import check_java

    map_name = map_name or default_map_name(gpx)
    output = output or Path(f"{gpx[0].stem}.img")

    echo_step("Checking tools")
    click.echo(f"    {check_java()}")

    echo_step("Reading route")
    lines, corridor, regions = _corridor_for(gpx, buffer_metres)

    owned_work_dir = work_dir is None
    work = Path(tempfile.mkdtemp(prefix="garmap-")) if owned_work_dir else work_dir
    work.mkdir(parents=True, exist_ok=True)

    try:
        poly = write_poly(corridor, work / "corridor.poly", name=map_name)

        echo_step("Downloading OSM data")
        extracts = []
        for region in regions:
            path = geofabrik.fetch(region, refresh=refresh)
            click.echo(f"    {path.name} ({human_size(path.stat().st_size)})")
            extracts.append(path)

        echo_step("Clipping and splitting into tiles")
        tiles = splitter.split(
            extracts,
            poly,
            work / "tiles",
            max_nodes=max_nodes,
            verbose=verbose,
        )
        click.echo(f"    {len(tiles)} tile(s)")

        contour_tiles = []
        if contours:
            echo_step(f"Generating {contour_step} m contour lines")
            contour_tiles = contours_mod.generate(
                poly, work / "contours", step=contour_step, verbose=verbose
            )
            click.echo(f"    {len(contour_tiles)} contour tile(s)")
        elif dem:
            raise GarmapError("--dem needs --contours, which downloads the elevation data.")

        echo_step("Compiling map")
        style_dir = style.materialise(work)
        img, written = mkgmap.compile_map(
            tiles,
            contour_tiles,
            work / "out",
            map_name,
            output,
            style_dir=style_dir,
            typ_file=style.typ_file(),
            bounds_dir=bounds,
            dem_dir=hgt_dir() if dem else None,
            drive_on=drive_on,
            generate_sea=sea,
            verbose=verbose,
        )
    finally:
        if owned_work_dir and not keep_work:
            shutil.rmtree(work, ignore_errors=True)
        elif keep_work:
            click.echo(f"    intermediates kept in {work}")

    click.echo()
    click.secho(f"Built {img}", fg="green", bold=True)
    click.echo(f"    name        {map_name}")
    click.echo(f"    family id   {mkgmap.family_id(map_name)}")
    click.echo(f"    size        {human_size(img.stat().st_size)}")
    click.echo(f"    tiles       {written}")
    click.echo()
    click.echo(f"Next: garmap install {img}")


# --------------------------------------------------------------------------- #


@main.command()
@click.argument(
    "gpx", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path)
)
@click.option(
    "--buffer",
    "buffer_metres",
    type=BufferParam(),
    default=f"{DEFAULT_BUFFER_METRES:.0f}m",
    show_default="15km",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="HTML preview path.  [default: <gpx name>-preview.html]",
)
@click.option("--open/--no-open", "open_browser", default=True, help="Open in a browser.")
def preview(gpx, buffer_metres, output, open_browser):
    """Show what a build would cover, without building anything."""
    from . import geofabrik, preview as preview_mod

    echo_step("Reading route")
    lines, corridor, regions = _corridor_for(gpx, buffer_metres)

    echo_step("Estimating download")
    summary = []
    total = 0
    for region in regions:
        size = geofabrik.remote_size(region)
        cached = geofabrik.local_path(region).exists()
        total += size or 0
        state = "cached" if cached else human_size(size)
        summary.append(f"{region.name}: {state}")
        click.echo(f"    {region.name} ({region.id}): {state}")
    if total:
        click.echo(f"    total {human_size(total)} (cached extracts are reused)")

    html = output or Path(f"{gpx[0].stem}-preview.html")
    geojson = html.with_suffix(".geojson")
    html_path, geojson_path = preview_mod.write(
        preview_mod.build_geojson(lines, corridor, regions),
        html,
        geojson,
        title=default_map_name(gpx),
        summary_lines=summary,
    )

    click.echo()
    click.secho(f"Wrote {html_path}", fg="green", bold=True)
    click.echo(f"      {geojson_path}")
    if open_browser:
        click.launch(str(html_path))


# --------------------------------------------------------------------------- #


@main.command()
@click.argument("img", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--name", help="Filename to use on the device.  [default: same as IMG]")
@click.option("--force", is_flag=True, help="Overwrite an existing map of that name.")
@click.option("--mtp/--no-mtp", default=True, help="Try libmtp if no volume is mounted.")
def install(img, name, force, mtp):
    """Copy a built .img onto a connected Garmin Edge."""
    from . import device

    if img.suffix.lower() != ".img":
        click.secho(
            f"warning: {img.name} does not end in .img; the Edge will ignore it.",
            fg="yellow",
        )

    mounted = device.find_mounted()
    if mounted:
        if len(mounted) > 1:
            click.echo("Multiple Garmin volumes found:")
            for index, candidate in enumerate(mounted, 1):
                click.echo(f"    {index}. {candidate.root}")
            choice = click.prompt("Which one?", type=click.IntRange(1, len(mounted)))
            target_device = mounted[choice - 1]
        else:
            target_device = mounted[0]

        echo_step(f"Copying to {target_device.root}")
        target = device.install_to_mounted(img, target_device, name=name, force=force)
        click.secho(f"Installed {target}", fg="green", bold=True)
        click.echo(f"\n{device.MAP_LIST_WARNING}")
        return

    if mtp and device.mtp_available():
        echo_step("No Garmin volume mounted; sending over MTP")
        click.echo(device.install_via_mtp(img, name=name))
        click.secho("Sent over MTP.", fg="green", bold=True)
        click.echo(f"\n{device.MAP_LIST_WARNING}")
        return

    click.secho("No Garmin volume is mounted.", fg="yellow", bold=True)
    if mtp:
        click.echo(
            "The Edge 1040 uses MTP, which macOS does not mount as a volume.\n"
            "`brew install libmtp` would let garmap push the file directly.\n"
        )
    click.echo(device.manual_instructions(img, name=name))


# --------------------------------------------------------------------------- #


@main.command()
def doctor():
    """Check that everything garmap needs is present."""
    from . import contours as contours_mod
    from . import device
    from .tools import MKGMAP, SPLITTER, _install_dir, heap_mb, total_memory_mb

    ok = True

    def report(label: str, good: bool, detail: str, required: bool = True) -> None:
        """`required=False` reports absence as a note, not a failure -- an
        optional dependency being missing only rules out one feature."""
        nonlocal ok
        if good:
            tag, colour = "OK  ", "green"
        elif required:
            tag, colour = "FAIL", "red"
            ok = False
        else:
            tag, colour = "--  ", "yellow"
        click.secho(f"  {tag}", fg=colour, nl=False)
        click.echo(f"  {label:<18} {detail}")

    click.echo("Java")
    try:
        from .tools import check_java

        report("runtime", True, check_java())
    except GarmapError as exc:
        report("runtime", False, str(exc).splitlines()[0])

    click.echo("Map tools")
    for tool in (MKGMAP, SPLITTER):
        installed = (_install_dir(tool) / tool.jar_name).is_file()
        report(
            tool.name,
            True,  # not fatal: a missing jar is downloaded on the first build
            f"r{tool.version} "
            + ("cached" if installed else "(will download on first build)"),
        )

    click.echo("Optional")
    report(
        "pyhgtmap",
        contours_mod.available(),
        "found"
        if contours_mod.available()
        else "absent; --contours needs `uv sync --extra contours`",
        required=False,
    )
    report(
        "libmtp",
        device.mtp_available(),
        "mtp-sendfile found"
        if device.mtp_available()
        else "absent; `brew install libmtp` for direct install, else "
        "garmap prints manual steps",
        required=False,
    )

    click.echo("Resources")
    total = total_memory_mb()
    report("memory", True, f"{total or '?'} MB total, {heap_mb()} MB heap for Java")
    usage = shutil.disk_usage(cache_dir().parent)
    report(
        "disk",
        usage.free > 2 << 30,
        f"{human_size(usage.free)} free (extracts can be hundreds of MB)",
    )
    report("cache", True, str(cache_dir()))

    click.echo()
    if ok:
        click.secho("Ready to build.", fg="green", bold=True)
    else:
        click.secho("Some checks failed; see above.", fg="red", bold=True)
        raise SystemExit(1)


# --------------------------------------------------------------------------- #


@main.group()
def cache():
    """Inspect and clear cached downloads."""


def _dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


@cache.command("list")
def cache_list():
    """Show what garmap has cached."""
    total = 0
    for label, path in (
        ("jars", jars_dir()),
        ("extracts", extracts_dir()),
        ("hgt", hgt_dir()),
    ):
        size = _dir_size(path) if path.is_dir() else 0
        total += size
        count = len(list(path.glob("*"))) if path.is_dir() else 0
        click.echo(f"  {label:<10} {human_size(size):>10}  {count} item(s)  {path}")
    click.echo(f"  {'total':<10} {human_size(total):>10}")


@cache.command("clear")
@click.option("--extracts", is_flag=True, help="Clear downloaded OSM extracts.")
@click.option("--hgt", is_flag=True, help="Clear downloaded elevation tiles.")
@click.option("--jars", is_flag=True, help="Clear mkgmap/splitter.")
@click.option("--all", "clear_all", is_flag=True, help="Clear everything.")
def cache_clear(extracts, hgt, jars, clear_all):
    """Delete cached downloads."""
    targets = {
        "extracts": extracts_dir() if (extracts or clear_all) else None,
        "hgt": hgt_dir() if (hgt or clear_all) else None,
        "jars": jars_dir() if (jars or clear_all) else None,
    }
    if not any(targets.values()):
        raise click.UsageError(
            "Nothing selected. Pass --extracts, --hgt, --jars or --all."
        )
    for label, path in targets.items():
        if path is None:
            continue
        freed = _dir_size(path) if path.is_dir() else 0
        shutil.rmtree(path, ignore_errors=True)
        click.echo(f"  cleared {label} ({human_size(freed)})")


def entrypoint() -> None:
    try:
        main(standalone_mode=False)
    except GarmapError as exc:
        click.secho(f"error: {exc}", fg="red", err=True)
        sys.exit(1)
    except click.ClickException as exc:
        exc.show()
        sys.exit(exc.exit_code)
    except click.exceptions.Abort:
        click.echo("Aborted.", err=True)
        sys.exit(130)


if __name__ == "__main__":
    entrypoint()
