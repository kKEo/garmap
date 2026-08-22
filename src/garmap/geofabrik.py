"""Pick and download the smallest set of Geofabrik extracts covering a corridor."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
from shapely.geometry import MultiPolygon, shape
from shapely.prepared import prep

from . import GarmapError
from .config import (
    GEOFABRIK_INDEX_TTL_SECONDS,
    GEOFABRIK_INDEX_URL,
    cache_dir,
    extracts_dir,
)
from .http import download

# Below this fraction of the corridor covered, we keep adding extracts.
COVERAGE_TARGET = 0.999
# A gain smaller than this fraction of the corridor isn't worth another download;
# such slivers are usually cross-border noise from the buffer, not real coverage.
MIN_GAIN = 0.001
# Past this many extracts, downloading each subdivision costs more than just
# taking the common parent.
MAX_REGIONS = 6


@dataclass
class Region:
    """One Geofabrik extract."""

    id: str
    name: str
    parent: str | None
    pbf_url: str
    geometry: MultiPolygon = field(repr=False)

    @property
    def area(self) -> float:
        """Area in square degrees -- a cheap stand-in for download size."""
        return self.geometry.area


def _index_path() -> Path:
    return cache_dir() / "geofabrik-index-v1.json"


def load_index(refresh: bool = False) -> dict[str, Region]:
    """Fetch (or reuse a cached copy of) Geofabrik's region index."""
    path = _index_path()
    fresh = (
        path.exists()
        and (time.time() - path.stat().st_mtime) < GEOFABRIK_INDEX_TTL_SECONDS
    )
    if refresh or not fresh:
        try:
            response = requests.get(GEOFABRIK_INDEX_URL, timeout=60)
            response.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        except requests.RequestException as exc:
            if not path.exists():
                raise GarmapError(
                    f"Could not fetch the Geofabrik region index: {exc}"
                ) from exc
            # Stale index beats no index.

    return parse_index(json.loads(path.read_text(encoding="utf-8")))


def clean_name(name: str) -> str:
    """Geofabrik embeds markup in some names, e.g. the Polish voivodeships come
    through as 'Wojewodztwo malopolskie<br />(Lesser Poland Voivodeship)'."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", name)).strip()


def parse_index(document: dict) -> dict[str, Region]:
    """Turn the index GeoJSON into Regions, keyed by id. Entries without a
    .osm.pbf download are skipped -- we can't use them."""
    regions: dict[str, Region] = {}
    for feature in document.get("features", []):
        props = feature.get("properties", {})
        url = props.get("urls", {}).get("pbf")
        if not url or not feature.get("geometry"):
            continue
        regions[props["id"]] = Region(
            id=props["id"],
            name=clean_name(props.get("name") or props["id"]),
            parent=props.get("parent"),
            pbf_url=url,
            geometry=shape(feature["geometry"]),
        )
    return regions


def _ancestors(region: Region, regions: dict[str, Region]) -> list[str]:
    chain, current = [], region.parent
    while current and current in regions:
        chain.append(current)
        current = regions[current].parent
    return chain


def _drop_redundant(chosen: list[Region], regions: dict[str, Region]) -> list[Region]:
    """Remove regions whose ancestor is also selected.

    Downloading both `bayern` and `germany` would feed splitter two copies of the
    same OSM elements.
    """
    selected = {r.id for r in chosen}
    return [
        r for r in chosen if not any(a in selected for a in _ancestors(r, regions))
    ]


def _common_ancestor(chosen: list[Region], regions: dict[str, Region]) -> Region | None:
    """Shallowest region that is an ancestor of every selection, if any."""
    chains = [[r.id] + _ancestors(r, regions) for r in chosen]
    shared = set(chains[0]).intersection(*(set(c) for c in chains[1:]))
    if not shared:
        return None
    return min((regions[i] for i in shared), key=lambda r: r.area)


def select_regions(
    corridor: MultiPolygon, regions: dict[str, Region]
) -> list[Region]:
    """Choose the cheapest set of extracts that covers the corridor.

    Weighted greedy set cover: at each step take the candidate with the best
    newly-covered-area per unit of region area. That naturally prefers a small
    subdivision over the country containing it, and the country over the
    continent, without needing to reason about the region tree's depth.
    """
    prepared = prep(corridor)
    candidates = [r for r in regions.values() if prepared.intersects(r.geometry)]
    if not candidates:
        raise GarmapError(
            "No Geofabrik extract covers this route. Check the GPX coordinates "
            "are in lon/lat order and land somewhere on Earth."
        )

    total = corridor.area
    remaining = corridor
    chosen: list[Region] = []

    while remaining.area / total > (1 - COVERAGE_TARGET) and candidates:
        scored = []
        for region in candidates:
            gain = remaining.intersection(region.geometry).area
            if gain / total >= MIN_GAIN:
                scored.append((gain / region.area, gain, region))
        if not scored:
            break
        _, gain, best = max(scored, key=lambda s: (s[0], -s[2].area))
        chosen.append(best)
        candidates.remove(best)
        remaining = remaining.difference(best.geometry)

    if not chosen:
        # Corridor is tiny relative to every candidate; just take the smallest
        # region that touches it.
        chosen = [min(candidates, key=lambda r: r.area)]

    chosen = _drop_redundant(chosen, regions)

    if len(chosen) > MAX_REGIONS:
        if (parent := _common_ancestor(chosen, regions)) is not None:
            return [parent]

    return sorted(chosen, key=lambda r: r.id)


def coverage_fraction(corridor: MultiPolygon, chosen: list[Region]) -> float:
    """How much of the corridor the chosen extracts actually cover, 0..1."""
    if not chosen:
        return 0.0
    covered = MultiPolygon()
    for region in chosen:
        covered = covered.union(region.geometry)
    return corridor.intersection(covered).area / corridor.area


def remote_size(region: Region) -> int | None:
    """Content-Length of the extract, or None if the server won't say."""
    try:
        response = requests.head(region.pbf_url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return int(response.headers["Content-Length"])
    except (requests.RequestException, KeyError, ValueError):
        return None


def local_path(region: Region) -> Path:
    """Where a downloaded extract lives in the cache."""
    return extracts_dir() / region.pbf_url.rsplit("/", 1)[-1]


def fetch(region: Region, refresh: bool = False) -> Path:
    """Download the extract unless a current copy is already cached."""
    destination = local_path(region)
    return download(
        region.pbf_url,
        destination,
        label=f"{region.name} extract",
        refresh=refresh,
    )
