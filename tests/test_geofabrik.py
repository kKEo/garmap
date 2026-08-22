from __future__ import annotations

import pytest
from shapely.geometry import LineString, box, mapping

from garmap import GarmapError
from garmap.corridor import build_corridor
from garmap.geofabrik import (
    Region,
    coverage_fraction,
    parse_index,
    select_regions,
)


def _feature(id_, parent, geom, name=None, pbf=True):
    props = {"id": id_, "name": name or id_, "urls": {}}
    if parent:
        props["parent"] = parent
    if pbf:
        props["urls"]["pbf"] = f"https://download.geofabrik.de/{id_}-latest.osm.pbf"
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


@pytest.fixture
def index():
    """A miniature region tree: europe > {poland > mazowieckie|malopolskie, germany}.

    Boxes are (min_lon, min_lat, max_lon, max_lat).
    """
    europe = box(5, 45, 25, 56)
    poland = box(14, 49, 24, 55)
    germany = box(5, 47, 15, 55)
    mazowieckie = box(19, 51, 23, 53)
    malopolskie = box(19, 49, 21, 51)
    return parse_index(
        {
            "features": [
                _feature("europe", None, europe),
                _feature("poland", "europe", poland),
                _feature("germany", "europe", germany),
                _feature("mazowieckie", "poland", mazowieckie),
                _feature("malopolskie", "poland", malopolskie),
            ]
        }
    )


def test_parse_index_extracts_properties(index):
    poland = index["poland"]
    assert isinstance(poland, Region)
    assert poland.parent == "europe"
    assert poland.pbf_url.endswith("poland-latest.osm.pbf")
    assert index["europe"].parent is None


def test_parse_index_skips_entries_without_a_pbf():
    parsed = parse_index({"features": [_feature("nopbf", None, box(0, 0, 1, 1), pbf=False)]})
    assert parsed == {}


def test_parse_index_skips_entries_without_geometry():
    parsed = parse_index(
        {"features": [{"type": "Feature", "properties": {"id": "x", "urls": {"pbf": "u"}}}]}
    )
    assert parsed == {}


def test_route_inside_one_subdivision_picks_that_subdivision(index):
    # Warsaw area, well inside mazowieckie.
    corridor = build_corridor([LineString([(21.0, 52.0), (21.3, 52.2)])], 10_000)
    assert [r.id for r in select_regions(corridor, index)] == ["mazowieckie"]


def test_route_spanning_two_subdivisions_picks_both_not_the_country(index):
    # Runs north-south from malopolskie into mazowieckie.
    corridor = build_corridor([LineString([(20.0, 49.5), (20.5, 52.5)])], 10_000)
    chosen = [r.id for r in select_regions(corridor, index)]
    assert chosen == ["malopolskie", "mazowieckie"]


def test_route_in_a_country_without_subdivisions_picks_the_country(index):
    corridor = build_corridor([LineString([(9.0, 50.0), (9.5, 50.5)])], 10_000)
    assert [r.id for r in select_regions(corridor, index)] == ["germany"]


def test_cross_border_route_picks_two_leaves_not_the_continent(index):
    # Germany -> Poland, but through the part of Poland with no subdivision,
    # so the country-level extract is the smallest thing available there.
    corridor = build_corridor([LineString([(14.0, 52.0), (17.0, 52.0)])], 10_000)
    chosen = [r.id for r in select_regions(corridor, index)]
    assert "europe" not in chosen
    assert set(chosen) == {"germany", "poland"}


def test_never_selects_a_region_and_its_ancestor(index):
    corridor = build_corridor([LineString([(15.0, 50.0), (22.0, 52.5)])], 20_000)
    chosen = {r.id for r in select_regions(corridor, index)}
    assert not ({"poland", "mazowieckie"} <= chosen)
    assert not ({"europe", "poland"} <= chosen)


def test_falls_back_to_the_continent_when_nothing_smaller_covers(index):
    # A corridor in a corner of europe covered by neither country box.
    corridor = build_corridor([LineString([(6.0, 45.5), (7.0, 46.0)])], 10_000)
    assert [r.id for r in select_regions(corridor, index)] == ["europe"]


def test_too_many_subdivisions_collapses_to_the_common_parent(index, monkeypatch):
    monkeypatch.setattr("garmap.geofabrik.MAX_REGIONS", 1)
    corridor = build_corridor([LineString([(20.0, 49.5), (20.5, 52.5)])], 10_000)
    assert [r.id for r in select_regions(corridor, index)] == ["poland"]


def test_route_off_the_map_raises(index):
    corridor = build_corridor([LineString([(-150.0, 20.0), (-149.0, 20.5)])], 10_000)
    with pytest.raises(GarmapError, match="No Geofabrik extract"):
        select_regions(corridor, index)


def test_coverage_fraction_full_and_partial(index):
    inside = build_corridor([LineString([(21.0, 52.0), (21.3, 52.2)])], 5_000)
    assert coverage_fraction(inside, [index["mazowieckie"]]) == pytest.approx(1.0)

    # Straddles mazowieckie's eastern edge (lon 23), so only part is covered.
    straddling = build_corridor([LineString([(22.9, 52.0), (23.5, 52.0)])], 5_000)
    partial = coverage_fraction(straddling, [index["mazowieckie"]])
    assert 0.0 < partial < 1.0


def test_coverage_fraction_of_nothing_is_zero(index):
    corridor = build_corridor([LineString([(21.0, 52.0), (21.3, 52.2)])], 5_000)
    assert coverage_fraction(corridor, []) == 0.0


def test_selection_covers_the_corridor(index):
    corridor = build_corridor([LineString([(14.5, 50.0), (22.0, 52.5)])], 15_000)
    chosen = select_regions(corridor, index)
    assert coverage_fraction(corridor, chosen) > 0.99


def test_region_names_are_stripped_of_geofabrik_markup():
    """Geofabrik embeds HTML in some names -- the Polish voivodeships arrive as
    'Wojewodztwo malopolskie<br />(Lesser Poland Voivodeship)'."""
    document = {
        "features": [
            _feature(
                "malopolskie",
                "poland",
                box(19, 49, 21, 51),
                name="Województwo małopolskie<br />(Lesser Poland Voivodeship)",
            )
        ]
    }
    assert parse_index(document)["malopolskie"].name == (
        "Województwo małopolskie (Lesser Poland Voivodeship)"
    )


def test_region_without_a_name_falls_back_to_its_id():
    document = {"features": [_feature("slovakia", "europe", box(17, 47, 22, 50))]}
    assert parse_index(document)["slovakia"].name == "slovakia"
