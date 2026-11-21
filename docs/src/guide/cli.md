# Command reference

All commands accept `-h` / `--help`. `garmap --version` prints the version.

## `garmap build GPX...`

Builds a Garmin `.img` covering the route(s).

| Option | Default | Meaning |
|---|---|---|
| `--buffer DISTANCE` | `15km` | Distance either side of the route. Accepts `15km`, `2500m` or a bare number of metres. |
| `-o`, `--output PATH` | `<first gpx stem>.img` | Output file. An existing file is overwritten. |
| `--name TEXT` | from the first GPX filename | Map name on the device. Also determines the family id. |
| `--contours` / `--no-contours` | off | Add contour lines (needs pyhgtmap). |
| `--contour-step INT` | `10` | Contour interval in metres. |
| `--dem` / `--no-dem` | off | Embed elevation data for shaded relief. Requires `--contours`. |
| `--drive-on detect\|left\|right` | `detect` | Driving side for routing. `detect` needs boundary data; set it explicitly for left-hand-traffic countries. |
| `--sea` | off | Generate sea polygons, for coastal routes. |
| `--bounds DIR` | none | Precompiled mkgmap bounds directory, for address search. |
| `--max-nodes INT` | `1400000` | Maximum nodes per tile, passed to splitter. |
| `--refresh` | off | Re-download cached extracts. |
| `--work-dir DIR` | a temporary directory | Where intermediates go. |
| `--keep-work` | off | Keep intermediates after the build. |
| `-v`, `--verbose` | off | Stream splitter, pyhgtmap and mkgmap output. |

When something fails, re-run with `--keep-work --work-dir ./work -v`. Use an **empty**
work directory each time: leftovers from an earlier run are currently picked up by the
next one (finding [H1](../review/findings.md#h1-a-reused---work-dir-leaks-old-tiles-into-the-new-map)).

### Work directory layout

```text
<work>/
  corridor.poly            clip polygon, read by splitter and pyhgtmap
  tiles/pass0/             splitter output for the first extract
        63240001.osm.pbf   one file per tile
        areas.list, template.args, densities-out.txt
  tiles/pass1/             ... one directory per extract
  contours/*.osm.pbf       pyhgtmap output (with --contours)
  cycle/                   the patched mkgmap style
  out/mkgmap.args          tile list handed to mkgmap
  out/6324NNNN.img         compiled tiles
  out/gmapsupp.img         moved to your -o path at the end
```

## `garmap preview GPX...`

Shows what a build would cover without building.

| Option | Default | Meaning |
|---|---|---|
| `--buffer DISTANCE` | `15km` | As for `build`. |
| `-o`, `--output PATH` | `<first gpx stem>-preview.html` | HTML path. The GeoJSON is written beside it. |
| `--open` / `--no-open` | open | Open the HTML in a browser. |

The HTML loads Leaflet from `unpkg.com` and tiles from `tile.openstreetmap.org`, so it
needs a network connection to display.

## `garmap install IMG`

Copies a built map onto a connected device.

| Option | Default | Meaning |
|---|---|---|
| `--name TEXT` | same as `IMG` | Filename to use on the device. |
| `--force` | off | Overwrite an existing file. Applies to the mounted-volume path only. |
| `--mtp` / `--no-mtp` | on | Try `mtp-sendfile` when no volume is mounted. |

## `garmap doctor`

Checks Java, the cached jars, pyhgtmap, libmtp, memory, and free disk. Exits 1 if a
required check fails.

## `garmap cache list` and `garmap cache clear`

`list` shows the size and item count of `jars`, `extracts` and `hgt`.

`clear` takes one or more of `--extracts`, `--hgt`, `--jars`, `--all`. It does not
remove the cached Geofabrik index file; delete
`~/.cache/garmap/geofabrik-index-v1.json` by hand if you need to.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | a `GarmapError` (reported as `error: ...`), or a failed `doctor` |
| 2 | bad usage, reported by click |
| 130 | interrupted |
