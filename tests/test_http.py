"""Download caching: freshness, revalidation, partial files and offline fallback."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import requests

from garmap import GarmapError, http

URL = "https://example.invalid/extract.osm.pbf"


class FakeResponse:
    def __init__(self, body=b"", status=200, headers=None):
        self.content = body
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, chunk_size=1):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _age(path: Path, seconds: float) -> None:
    past = time.time() - seconds
    os.utime(path, (past, past))


def test_fresh_cache_is_returned_without_touching_the_network(tmp_path, monkeypatch):
    destination = tmp_path / "extract.osm.pbf"
    destination.write_bytes(b"cached")

    def explode(*args, **kwargs):
        raise AssertionError("should not have made a request")

    monkeypatch.setattr(http.requests, "get", explode)
    monkeypatch.setattr(http.requests, "head", explode)

    assert http.download(URL, destination).read_bytes() == b"cached"


def test_download_writes_via_a_part_file(tmp_path, monkeypatch):
    destination = tmp_path / "nested" / "extract.osm.pbf"
    seen: list[Path] = []

    def fake_get(url, **kwargs):
        # While the body is streaming, only the .part file may exist.
        seen.append(destination.with_suffix(destination.suffix + ".part"))
        return FakeResponse(b"payload", headers={"Content-Length": "7", "ETag": '"v1"'})

    monkeypatch.setattr(http.requests, "get", fake_get)

    path = http.download(URL, destination)

    assert path.read_bytes() == b"payload"
    assert not seen[0].exists()  # renamed into place, nothing left behind
    assert (tmp_path / "nested" / "extract.osm.pbf.etag").read_text() == '"v1"'


def test_stale_cache_is_revalidated_with_the_etag(tmp_path, monkeypatch):
    destination = tmp_path / "extract.osm.pbf"
    destination.write_bytes(b"cached")
    (tmp_path / "extract.osm.pbf.etag").write_text('"v1"')
    _age(destination, http.STALE_AFTER_SECONDS * 2)

    requested = {}

    def fake_head(url, headers=None, **kwargs):
        requested.update(headers or {})
        return FakeResponse(status=304)

    monkeypatch.setattr(http.requests, "head", fake_head)
    monkeypatch.setattr(
        http.requests, "get", lambda *a, **k: pytest.fail("304 should skip the body")
    )

    path = http.download(URL, destination)

    assert requested == {"If-None-Match": '"v1"'}
    assert path.read_bytes() == b"cached"
    # The staleness clock was reset, so the next run skips even the HEAD.
    assert http.age_seconds(path) < 60


def test_refresh_redownloads_a_fresh_cache(tmp_path, monkeypatch):
    destination = tmp_path / "extract.osm.pbf"
    destination.write_bytes(b"old")
    monkeypatch.setattr(
        http.requests, "get", lambda *a, **k: FakeResponse(b"new")
    )

    assert http.download(URL, destination, refresh=True).read_bytes() == b"new"


def test_offline_falls_back_to_the_stale_cache(tmp_path, monkeypatch):
    destination = tmp_path / "extract.osm.pbf"
    destination.write_bytes(b"cached")
    _age(destination, http.STALE_AFTER_SECONDS * 2)

    def offline(*args, **kwargs):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(http.requests, "get", offline)
    monkeypatch.setattr(http.requests, "head", offline)

    assert http.download(URL, destination).read_bytes() == b"cached"


def test_offline_with_no_cache_is_an_error(tmp_path, monkeypatch):
    def offline(*args, **kwargs):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(http.requests, "get", offline)

    with pytest.raises(GarmapError, match="Failed to download"):
        http.download(URL, tmp_path / "extract.osm.pbf")


def test_a_failed_download_leaves_no_partial_file(tmp_path, monkeypatch):
    destination = tmp_path / "extract.osm.pbf"

    def fail_midway(url, **kwargs):
        raise requests.ConnectionError("reset")

    monkeypatch.setattr(http.requests, "get", fail_midway)

    with pytest.raises(GarmapError):
        http.download(URL, destination)
    assert not (tmp_path / "extract.osm.pbf.part").exists()


@pytest.mark.parametrize(
    "size,expected",
    [(None, "unknown size"), (512, "512 B"), (2048, "2.0 KiB"), (5 << 20, "5.0 MiB")],
)
def test_human_size(size, expected):
    assert http.human_size(size) == expected
