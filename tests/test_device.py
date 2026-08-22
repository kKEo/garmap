"""The three install paths, against a fake device tree."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from garmap import GarmapError, device


@pytest.fixture
def img(tmp_path) -> Path:
    path = tmp_path / "podhale.img"
    path.write_bytes(b"map bytes")
    return path


@pytest.fixture
def edge(tmp_path, monkeypatch) -> Path:
    """A mounted volume that looks like a Garmin device."""
    volumes = tmp_path / "Volumes"
    root = volumes / "GARMIN"
    (root / device.MAP_SUBDIR).mkdir(parents=True)
    monkeypatch.setattr(device, "VOLUMES", volumes)
    return root


def test_find_mounted_spots_a_garmin_volume(edge):
    assert [d.root for d in device.find_mounted()] == [edge]


def test_find_mounted_ignores_other_volumes(tmp_path, monkeypatch):
    volumes = tmp_path / "Volumes"
    (volumes / "Backup Disk" / "Documents").mkdir(parents=True)
    monkeypatch.setattr(device, "VOLUMES", volumes)
    assert device.find_mounted() == []


def test_install_to_mounted_lands_in_the_map_directory(img, edge):
    target = device.install_to_mounted(img, device.MountedDevice(edge))
    assert target == edge / device.MAP_SUBDIR / "podhale.img"
    assert target.read_bytes() == b"map bytes"


def test_install_to_mounted_creates_a_missing_map_directory(img, tmp_path, monkeypatch):
    volumes = tmp_path / "Volumes"
    root = volumes / "GARMIN"
    (root / "Garmin").mkdir(parents=True)
    monkeypatch.setattr(device, "VOLUMES", volumes)

    target = device.install_to_mounted(img, device.MountedDevice(root))
    assert target.is_file()


def test_install_refuses_to_overwrite_without_force(img, edge):
    mounted = device.MountedDevice(edge)
    device.install_to_mounted(img, mounted)
    img.write_bytes(b"new map bytes")

    with pytest.raises(GarmapError, match="--force"):
        device.install_to_mounted(img, mounted)

    target = device.install_to_mounted(img, mounted, force=True)
    assert target.read_bytes() == b"new map bytes"


def test_install_honours_an_explicit_name(img, edge):
    target = device.install_to_mounted(img, device.MountedDevice(edge), name="tour.img")
    assert target.name == "tour.img"


def test_mtp_install_sends_to_the_map_subdir(img, monkeypatch):
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "Sent 9 bytes", "")

    monkeypatch.setattr(device, "mtp_available", lambda: True)
    monkeypatch.setattr(device.subprocess, "run", fake_run)

    assert "Sent 9 bytes" in device.install_via_mtp(img)
    assert calls == [["mtp-sendfile", str(img), "Garmin/Map/podhale.img"]]


def test_mtp_failure_falls_back_to_printed_instructions(img, monkeypatch):
    monkeypatch.setattr(device, "mtp_available", lambda: True)
    monkeypatch.setattr(
        device.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, "", "libmtp: device busy"
        ),
    )

    with pytest.raises(GarmapError) as excinfo:
        device.install_via_mtp(img)

    message = str(excinfo.value)
    assert "device busy" in message
    assert "lap button" in message  # the instructions came along


def test_mtp_install_without_libmtp_says_how_to_get_it(img, monkeypatch):
    monkeypatch.setattr(device, "mtp_available", lambda: False)
    with pytest.raises(GarmapError, match="brew install libmtp"):
        device.install_via_mtp(img)


def test_manual_instructions_cover_the_edge_1040_gotchas(img):
    text = device.manual_instructions(img)
    assert "Garmin Express" in text
    assert "lap button" in text
    assert str(img) in text
    assert device.MAP_LIST_WARNING in text
