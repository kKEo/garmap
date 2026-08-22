"""Java discovery, jar unpacking and the argv the Java tools are given."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from garmap import GarmapError, config, tools


@pytest.fixture
def cache(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    return config.jars_dir()


def _release_zip(path: Path, tool: tools.Tool) -> Path:
    """A stand-in for an upstream release: everything under one top directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    top = f"{tool.name}-r{tool.version}"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{top}/{tool.jar_name}", "jar bytes")
        zf.writestr(f"{top}/lib/dependency.jar", "lib bytes")
        zf.writestr(f"{top}/resources/styles/default/lines", "# style")
    return path


def test_jar_path_unpacks_the_whole_release(cache, monkeypatch):
    """mkgmap's manifest Class-Path points at a sibling lib/, and the built-in
    styles ship in the release, so the jar alone is not enough."""

    def fake_download(url, destination, label=None, **kwargs):
        return _release_zip(destination, tools.MKGMAP)

    monkeypatch.setattr(tools, "download", fake_download)

    jar = tools.jar_path(tools.MKGMAP)

    assert jar.is_file()
    assert (jar.parent / "lib" / "dependency.jar").is_file()
    assert (jar.parent / "resources" / "styles" / "default" / "lines").is_file()


def test_jar_path_reuses_the_cached_release(cache, monkeypatch):
    calls = []

    def fake_download(url, destination, label=None, **kwargs):
        calls.append(url)
        return _release_zip(destination, tools.SPLITTER)

    monkeypatch.setattr(tools, "download", fake_download)

    first = tools.jar_path(tools.SPLITTER)
    second = tools.jar_path(tools.SPLITTER)

    assert first == second
    assert len(calls) == 1


def test_corrupt_archive_is_discarded(cache, monkeypatch):
    written: list[Path] = []

    def fake_download(url, destination, label=None, **kwargs):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"this is not a zip")
        written.append(destination)
        return destination

    monkeypatch.setattr(tools, "download", fake_download)

    with pytest.raises(GarmapError, match="corrupt"):
        tools.jar_path(tools.MKGMAP)
    # Deleted, so the next run re-downloads instead of failing forever.
    assert not written[0].exists()


def test_missing_jar_in_archive_names_the_tool(cache, monkeypatch):
    def fake_download(url, destination, label=None, **kwargs):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w") as zf:
            zf.writestr("mkgmap-r4924/README", "no jar here")
        return destination

    monkeypatch.setattr(tools, "download", fake_download)

    with pytest.raises(GarmapError, match="mkgmap.jar"):
        tools.jar_path(tools.MKGMAP)


def test_java_version_parses_the_stderr_banner(monkeypatch):
    banner = 'openjdk version "21.0.6" 2025-01-21 LTS\nOpenJDK Runtime Environment'

    class Result:
        stderr = banner
        stdout = ""

    monkeypatch.setattr(tools, "java_executable", lambda: "/usr/bin/java")
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **k: Result())

    assert tools.java_version() == (21, 'openjdk version "21.0.6" 2025-01-21 LTS')


def test_check_java_rejects_an_old_runtime(monkeypatch):
    monkeypatch.setattr(tools, "java_version", lambda: (11, 'java version "11.0.1"'))
    with pytest.raises(GarmapError, match="too old"):
        tools.check_java()


def test_heap_is_bounded_regardless_of_machine_size(monkeypatch):
    monkeypatch.setattr(tools, "total_memory_mb", lambda: 512)
    assert tools.heap_mb() == 1024
    monkeypatch.setattr(tools, "total_memory_mb", lambda: 262144)
    assert tools.heap_mb() == 12288
    monkeypatch.setattr(tools, "total_memory_mb", lambda: None)
    assert tools.heap_mb() == 2048


def test_describe_command_is_a_runnable_argv(monkeypatch):
    monkeypatch.setattr(tools, "java_executable", lambda: "/usr/bin/java")
    command = tools.describe_command(Path("/jars/mkgmap.jar"), ["--route"], heap=4096)
    assert command == ["/usr/bin/java", "-Xmx4096m", "-jar", "/jars/mkgmap.jar", "--route"]
