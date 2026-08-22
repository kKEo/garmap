"""Materialise garmap's cycling style by patching mkgmap's default style.

Rather than shipping a whole style (which would drift out of sync with each
mkgmap release, and would have to re-implement the default style's access,
address and road-speed logic), garmap copies the `default` style out of the
pinned mkgmap.jar and applies two surgical patches:

  * `inc/contour_lines` is replaced, so contour labels are metres not feet.
  * a cycle-route rule is appended to `relations`, so signed route references
    end up in the way names the Edge displays.

Everything else about the cycling emphasis is rendering, and lives in the TYP
file -- that keeps the routable line types the default style assigns untouched,
which matters because Garmin will not route over custom (0x10000+) types.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from . import GarmapError
from .tools import MKGMAP, jar_path

DATA_DIR = Path(__file__).parent / "style"
TYP_SOURCE = DATA_DIR / "cycle.txt"
CONTOUR_PATCH = DATA_DIR / "contour_lines"
RELATIONS_PATCH = DATA_DIR / "relations_cycle"

BASE_STYLE = "default"
_PREFIX = f"styles/{BASE_STYLE}/"


def materialise(target: Path, metric_contours: bool = True) -> Path:
    """Write the patched style into `target` and return its directory."""
    style_dir = target / "cycle"
    shutil.rmtree(style_dir, ignore_errors=True)
    style_dir.mkdir(parents=True)

    jar = jar_path(MKGMAP)
    with zipfile.ZipFile(jar) as zf:
        members = [n for n in zf.namelist() if n.startswith(_PREFIX) and not n.endswith("/")]
        if not members:
            raise GarmapError(
                f"mkgmap.jar does not contain the '{BASE_STYLE}' style; the pinned "
                "mkgmap version may have reorganised its resources."
            )
        for name in members:
            destination = style_dir / name[len(_PREFIX) :]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(zf.read(name))

    if metric_contours:
        contour_target = style_dir / "inc" / "contour_lines"
        if not contour_target.exists():
            raise GarmapError(
                "mkgmap's default style no longer has inc/contour_lines; "
                "garmap's metric-contour patch needs updating."
            )
        contour_target.write_text(
            CONTOUR_PATCH.read_text(encoding="utf-8"), encoding="utf-8"
        )

    relations = style_dir / "relations"
    with relations.open("a", encoding="utf-8") as fh:
        fh.write(RELATIONS_PATCH.read_text(encoding="utf-8"))

    (style_dir / "info").write_text(
        "summary: garmap cycling style\n"
        "version=1.0\n"
        "description {\n"
        "mkgmap's default style with metric contour labels and signed cycle\n"
        "route references folded into way names.\n"
        "}\n",
        encoding="utf-8",
    )
    return style_dir


def typ_file() -> Path:
    return TYP_SOURCE
