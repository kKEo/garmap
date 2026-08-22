"""Locate Java, and fetch/cache the pinned mkgmap and splitter releases."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import GarmapError
from .config import (
    MKGMAP_URL,
    MKGMAP_VERSION,
    SPLITTER_URL,
    SPLITTER_VERSION,
    jars_dir,
)
from .http import download

MIN_JAVA_MAJOR = 17


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    url: str
    jar_name: str


MKGMAP = Tool("mkgmap", MKGMAP_VERSION, MKGMAP_URL, "mkgmap.jar")
SPLITTER = Tool("splitter", SPLITTER_VERSION, SPLITTER_URL, "splitter.jar")


def java_executable() -> str:
    """Path to a usable `java`, or raise with installation guidance."""
    if java_home := os.environ.get("JAVA_HOME"):
        candidate = Path(java_home) / "bin" / "java"
        if candidate.is_file():
            return str(candidate)
    if found := shutil.which("java"):
        return found
    raise GarmapError(
        "Java not found. mkgmap and splitter are Java programs.\n"
        "Install a JDK 17+ (e.g. `brew install --cask temurin`) and retry."
    )


def java_version() -> tuple[int, str]:
    """(major, full version string) reported by `java -version`."""
    try:
        result = subprocess.run(
            [java_executable(), "-version"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise GarmapError(f"`java -version` failed: {exc.stderr.strip()}") from exc

    # java prints its version banner on stderr, e.g. `openjdk version "21.0.6"`.
    text = (result.stderr or result.stdout).strip()
    match = re.search(r'version "(\d+)(?:\.(\d+))?', text)
    if not match:
        raise GarmapError(f"Could not parse Java version from: {text!r}")
    return int(match.group(1)), text.splitlines()[0]


def check_java() -> str:
    major, banner = java_version()
    if major < MIN_JAVA_MAJOR:
        raise GarmapError(
            f"Java {major} is too old for mkgmap r{MKGMAP_VERSION}; "
            f"Java {MIN_JAVA_MAJOR}+ is required. Found: {banner}"
        )
    return banner


def _install_dir(tool: Tool) -> Path:
    return jars_dir() / f"{tool.name}-r{tool.version}"


def jar_path(tool: Tool) -> Path:
    """Cached jar path, downloading and unpacking the release if needed.

    The whole release directory is kept, not just the jar: mkgmap's manifest
    Class-Path points at its sibling lib/ directory and the built-in styles ship
    inside the release.
    """
    target = _install_dir(tool)
    jar = target / tool.jar_name
    if jar.is_file():
        return jar

    archive = download(
        tool.url,
        jars_dir() / f"{tool.name}-r{tool.version}.zip",
        label=f"{tool.name} r{tool.version}",
    )

    staging = jars_dir() / f".{tool.name}-unpack"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(staging)
    except zipfile.BadZipFile as exc:
        archive.unlink(missing_ok=True)
        raise GarmapError(
            f"The downloaded {tool.name} archive is corrupt; it has been deleted. "
            "Re-run to try again."
        ) from exc

    # The release zip wraps everything in a single top-level directory.
    found = next((p.parent for p in staging.rglob(tool.jar_name)), None)
    if found is None:
        shutil.rmtree(staging, ignore_errors=True)
        raise GarmapError(
            f"{tool.jar_name} was not present in {tool.url}. "
            f"The pinned {tool.name} version may have been withdrawn upstream."
        )

    shutil.rmtree(target, ignore_errors=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    found.replace(target)
    shutil.rmtree(staging, ignore_errors=True)
    return target / tool.jar_name


def total_memory_mb() -> int | None:
    try:
        return (
            os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // (1024 * 1024)
        )
    except (ValueError, OSError, AttributeError):
        return None


def heap_mb(fraction: float = 0.5, minimum: int = 1024, maximum: int = 12288) -> int:
    """Heap size for the Java tools.

    Deliberately conservative: splitter and mkgmap are I/O heavy, and starving
    the OS page cache to grow the heap makes them slower, not faster.
    """
    total = total_memory_mb()
    if total is None:
        return minimum * 2
    return max(minimum, min(maximum, int(total * fraction)))


def run_java(
    jar: Path,
    args: list[str],
    cwd: Path,
    heap: int | None = None,
    verbose: bool = False,
) -> str:
    """Run a Java tool, returning its combined output.

    Output is streamed to the terminal when `verbose`, and captured either way so
    later stages can inspect it (tile counts, routing warnings).
    """
    command = [
        java_executable(),
        f"-Xmx{heap or heap_mb()}m",
        "-jar",
        str(jar),
        *args,
    ]
    captured: list[str] = []
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        captured.append(line)
        if verbose:
            print(f"  {line.rstrip()}")
    code = process.wait()
    output = "".join(captured)

    if code != 0:
        tail = "\n".join(output.strip().splitlines()[-25:])
        raise GarmapError(
            f"{jar.name} failed (exit {code}).\n"
            f"Command: {' '.join(command)}\n"
            f"Last output:\n{tail}"
        )
    return output


def describe_command(jar: Path, args: list[str], heap: int | None = None) -> list[str]:
    """The argv `run_java` would use -- for --dry-run and for tests."""
    return [
        java_executable(),
        f"-Xmx{heap or heap_mb()}m",
        "-jar",
        str(jar),
        *args,
    ]
