"""Get a built .img onto a Garmin Edge.

The Edge 1040 speaks MTP, not USB mass storage, and macOS does not mount MTP
devices as volumes. So there are three paths, tried in order:

  1. a mounted volume with a Garmin/Map directory (mass-storage-capable units,
     and SD cards on the models that have a slot);
  2. libmtp's `mtp-sendfile`, if installed;
  3. printed instructions, including the trick needed for large files.

Path 3 is not a failure mode to apologise for -- for many users on macOS it is
the only route that works reliably.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import GarmapError

MAP_SUBDIR = "Garmin/Map"
VOLUMES = Path("/Volumes")

# The Edge shows only a limited number of maps in its map list regardless of
# free space; inactive stock maps count towards it.
MAP_LIST_WARNING = (
    "If the map does not appear in Map Information, delete some of the "
    "preinstalled Garmin maps you don't use -- the Edge's map list has a cap "
    "that is independent of free space."
)


@dataclass(frozen=True)
class MountedDevice:
    """A Garmin device visible as a filesystem."""

    root: Path

    @property
    def map_dir(self) -> Path:
        return self.root / MAP_SUBDIR


def find_mounted() -> list[MountedDevice]:
    """Mounted volumes that look like a Garmin device."""
    if not VOLUMES.is_dir():
        return []
    found = []
    for volume in sorted(VOLUMES.iterdir()):
        try:
            if (volume / MAP_SUBDIR).is_dir() or (volume / "Garmin").is_dir():
                found.append(MountedDevice(volume))
        except OSError:
            continue  # unreadable or disconnecting mid-scan
    return found


def mtp_available() -> bool:
    return shutil.which("mtp-sendfile") is not None


def install_to_mounted(
    img: Path, device: MountedDevice, name: str | None = None, force: bool = False
) -> Path:
    """Copy the image into the device's Garmin/Map directory."""
    target_dir = device.map_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (name or img.name)

    if target.exists() and not force:
        raise GarmapError(
            f"{target} already exists. Pass --force to overwrite it, or choose "
            "another name with --name."
        )
    shutil.copy2(img, target)
    return target


def install_via_mtp(img: Path, name: str | None = None) -> str:
    """Push the image with libmtp. Returns the tool's output."""
    if not mtp_available():
        raise GarmapError("mtp-sendfile is not installed (try `brew install libmtp`).")
    remote = f"{MAP_SUBDIR}/{name or img.name}"
    result = subprocess.run(
        ["mtp-sendfile", str(img), remote], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise GarmapError(
            "mtp-sendfile failed:\n"
            + (result.stderr or result.stdout).strip()
            + "\n\n"
            + manual_instructions(img, name)
        )
    return result.stdout


def manual_instructions(img: Path, name: str | None = None) -> str:
    """What to do by hand when neither automated path is available."""
    filename = name or img.name
    return "\n".join(
        [
            "Copy the map across by hand:",
            "",
            "  1. Quit Garmin Express AND stop its background service in Activity",
            "     Monitor -- only one program can talk to the Edge over USB at a time.",
            "  2. Power the Edge off completely.",
            "  3. Hold the lap button (bottom left) while connecting the USB cable,",
            "     until the screen shows 'usb mtp mode'. Large .img transfers",
            "     routinely stall without this.",
            "  4. Open the device in an MTP client -- OpenMTP is the most reliable",
            "     on macOS (https://openmtp.ganeshrvel.com/).",
            f"  5. Copy {img} into {MAP_SUBDIR}/ on the device, as {filename}.",
            "",
            f"  {MAP_LIST_WARNING}",
        ]
    )
