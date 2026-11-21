# Troubleshooting

Start with a verbose build into a fresh, kept work directory:

```console
$ rm -rf ./work
$ uv run garmap build tour.gpx --buffer 8km --keep-work --work-dir ./work -v
```

| Symptom | Likely cause | What to do |
|---|---|---|
| `Java not found` | no JDK on `PATH` and `JAVA_HOME` unset | install a JDK 17+ |
| `Java N is too old` | JDK older than 17 | upgrade; Java 8 is reported as "Java 1" |
| `doctor` ends in `FileNotFoundError` | `~/.cache` does not exist | `mkdir -p ~/.cache` |
| Traceback ending in `JSONDecodeError` during "Choosing OSM extracts" | corrupt cached region index | delete `~/.cache/garmap/geofabrik-index-v1.json` |
| `No Geofabrik extract covers this route` | coordinates outside every extract | check the GPX is lon/lat on land |
| `warning: extracts cover N% of the corridor` | part of the corridor is outside all extracts (sea, or a gap) | usually harmless at coasts; otherwise check the preview |
| `splitter produced no tiles` | corridor outside the downloaded data, or the wrong cached file was used | run `preview`; try `--refresh`; see finding H2 |
| `splitter.jar failed (exit 1)` with an out-of-memory message | heap too small for the extract | close other programs; reduce `--buffer` |
| `pyhgtmap failed to generate contour lines` | elevation host unavailable | retry later, or build without `--contours` |
| `mkgmap wrote no map tiles` | mkgmap rejected an option or an input | re-run with `-v` and read its output |
| Map contains roads far from the route | a reused `--work-dir` had old tiles in it | delete the work directory and rebuild |
| Map not listed on the device | map-list cap, duplicate family id, or old firmware | see [device details](device.md#device-details) |
| Transfer stalls part-way | device not in MTP mode | hold the lap button while connecting |
| Preview page is blank | no network: Leaflet and tiles load from the internet | open it while online |

## Reading the intermediates

- `work/corridor.poly`: the clip polygon. Load the preview GeoJSON in any GIS tool to
  see the same shape.
- `work/tiles/passN/areas.list`: the tile rectangles splitter chose for extract *N*.
- `work/out/mkgmap.args`: the exact tile list and map ids mkgmap was given.
- `work/cycle/`: the patched style. Diff it against mkgmap's `default` style to see
  the two changes garmap makes.
