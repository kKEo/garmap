"""Emit a GeoJSON + standalone HTML preview of the corridor and its coverage."""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import MultiPolygon, mapping
from shapely.ops import unary_union

from .geofabrik import Region

_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>garmap preview: {title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body,#map {{ height:100%; margin:0 }}
  .legend {{ background:#fff; padding:8px 10px; font:13px/1.5 system-ui,sans-serif;
             box-shadow:0 1px 4px rgba(0,0,0,.3); border-radius:4px }}
  .legend i {{ display:inline-block; width:12px; height:12px; margin-right:6px;
               vertical-align:-1px }}
</style></head><body><div id="map"></div><script>
const data = {geojson};
const map = L.map('map');
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

const styles = {{
  region:   {{ color:'#888', weight:1, fillColor:'#888', fillOpacity:0.10, dashArray:'4 4' }},
  corridor: {{ color:'#0050C8', weight:2, fillColor:'#0050C8', fillOpacity:0.18 }},
  route:    {{ color:'#E8112D', weight:4 }},
}};
const order = ['region', 'corridor', 'route'];
for (const kind of order) {{
  L.geoJSON(data, {{
    filter: f => f.properties.kind === kind,
    style: styles[kind],
    onEachFeature: (f, l) => f.properties.label && l.bindPopup(f.properties.label),
  }}).addTo(map);
}}

const corridor = L.geoJSON(data, {{ filter: f => f.properties.kind === 'corridor' }});
map.fitBounds(corridor.getBounds(), {{ padding: [20, 20] }});

const legend = L.control({{ position:'bottomright' }});
legend.onAdd = () => {{
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = {legend};
  return div;
}};
legend.addTo(map);
</script></body></html>
"""


def build_geojson(
    lines: list,
    corridor: MultiPolygon,
    regions: list[Region] | None = None,
) -> dict:
    """FeatureCollection of the route, the corridor and the chosen extracts."""
    features = []
    for region in regions or []:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "kind": "region",
                    "label": f"Geofabrik extract: {region.name} ({region.id})",
                },
                "geometry": mapping(region.geometry),
            }
        )
    features.append(
        {
            "type": "Feature",
            "properties": {"kind": "corridor", "label": "Download / build corridor"},
            "geometry": mapping(corridor),
        }
    )
    features.append(
        {
            "type": "Feature",
            "properties": {"kind": "route", "label": "GPX route"},
            "geometry": mapping(unary_union(lines)),
        }
    )
    return {"type": "FeatureCollection", "features": features}


def write(
    geojson: dict,
    html_path: Path,
    geojson_path: Path,
    title: str,
    summary_lines: list[str],
) -> tuple[Path, Path]:
    """Write both preview artefacts and return their paths."""
    geojson_path.parent.mkdir(parents=True, exist_ok=True)
    geojson_path.write_text(json.dumps(geojson), encoding="utf-8")

    legend_html = (
        "<b>garmap</b><br>"
        "<i style='background:#E8112D'></i>GPX route<br>"
        "<i style='background:#0050C8'></i>Corridor<br>"
        "<i style='background:#888'></i>Geofabrik extract<br>"
        + "<br>".join(summary_lines)
    )
    html_path.write_text(
        _HTML.format(
            title=title,
            geojson=json.dumps(geojson),
            legend=json.dumps(legend_html),
        ),
        encoding="utf-8",
    )
    return html_path, geojson_path
