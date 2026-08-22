# garmap

Build a small, routable, cycling-tuned Garmin `.img` map that covers exactly one
GPX route — sized to sit alongside the stock maps on an Edge 1040.

```console
$ garmap preview tour.gpx --buffer 15km          # check coverage before downloading
$ garmap build tour.gpx --buffer 15km --contours -o alps-tour.img
$ garmap install alps-tour.img
```

`garmap` is an orchestration layer. The map itself is built by
[splitter](https://www.mkgmap.org.uk/) and [mkgmap](https://www.mkgmap.org.uk/),
which it downloads and caches on first use; OSM data comes from
[Geofabrik](https://download.geofabrik.de/) and contour lines from
[pyhgtmap](https://pypi.org/project/pyhgtmap/).

## Install

Needs a JDK 17 or newer (mkgmap and splitter are Java programs) and
[uv](https://docs.astral.sh/uv/).

```console
$ uv sync --extra contours       # drop --extra contours if you don't want them
$ uv run garmap doctor           # checks Java, jars, optional deps, disk
```

`brew install libmtp` is optional but recommended on macOS — see
[Getting the map onto the device](#getting-the-map-onto-the-device).

## How it works

1. **Route** — every `<trk>` segment and `<rte>` in the GPX is read. Waypoints are
   ignored: a bag of unordered points is not a route corridor.
2. **Corridor** — the route is buffered by `--buffer` in a local equidistant
   projection, so the distance is metres on the ground rather than degrees.
   Interior rings are dropped, because splitter r654 mishandles holes and a loop
   route buffers into a holed polygon.
3. **Extracts** — Geofabrik's region index is searched with a weighted greedy set
   cover, which prefers the smallest subdivisions that cover the corridor (a
   Tatras route picks `malopolskie` + `slovakia`, not `europe`). Extracts are
   cached and revalidated by ETag.
4. **Clip and split** — splitter clips to the corridor `.poly` and cuts it into
   tiles. One pass per extract: splitter rejects a multi-file run whose node ids
   aren't globally sorted, and two Geofabrik extracts never are.
5. **Contours** — optional; pyhgtmap over Viewfinder Panoramas data, which needs
   no account. HGT tiles are cached.
6. **Compile** — mkgmap with routing, a search index, a patched cycling style and
   a TYP file, into a `gmapsupp.img` renamed to your `-o`.

Everything downloaded lives under `~/.cache/garmap` (`garmap cache list` /
`garmap cache clear`).

## Commands

| Command | What it does |
|---|---|
| `garmap build GPX...` | Build the `.img`. |
| `garmap preview GPX...` | Write a Leaflet HTML map of the route, corridor and chosen extracts, plus the download size — no build. |
| `garmap install IMG` | Copy the map onto a connected Edge. |
| `garmap doctor` | Check Java, cached jars, optional dependencies, free disk. |
| `garmap cache list\|clear` | Inspect or clear cached downloads. |

Useful `build` options:

- `--buffer 15km` — how far either side of the route to include. This is the main
  size dial; the map grows roughly linearly with it.
- `--contours` / `--contour-step 10` — contour lines, labelled in metres.
- `--dem` — embed elevation data for shaded relief. Needs `--contours` (that's
  what downloads the HGT tiles) and makes the map noticeably bigger.
- `--drive-on left|right|detect` — `detect` needs boundary data inside the
  corridor; set it explicitly for left-hand-traffic countries.
- `--sea` — sea polygons, for coastal routes.
- `--keep-work --work-dir ./work -v` — keep the intermediates and stream the Java
  tools' output. Reach for this first when something goes wrong.

## Cycling style

Rather than hand-write a style that would drift from upstream, garmap copies
mkgmap's `default` style out of the pinned jar and patches two things:

- contours are labelled in **metres**, not feet;
- ways carrying a signed cycle route relation get the route's `ref`/`name`
  appended, so the Edge announces "Lane (EV4)" rather than just "Lane".

Everything else is *rendering*, and lives in the bundled TYP: cycleways in blue
at width 6, tracks in brown, paths thin and grey, residential roads dialled back,
contours in browns. That split is deliberate — **Garmin only routes over line
types below `0x14`**, so promoting cycleways to a custom type (`0x10000`+) would
make them pretty and unroutable.

POIs that matter mid-ride (drinking water, bike shops, cafés, toilets, stations)
come through from the default style already; garmap does not re-declare them.

## Getting the map onto the device

**The Edge 1040 is MTP-only.** It does not appear in Finder as a volume on macOS,
so there is no drag-and-drop from a mounted disk. `garmap install` tries, in
order:

1. a mounted volume containing `Garmin/Map/` — mass-storage-capable units and SD
   cards;
2. `mtp-sendfile` from libmtp (`brew install libmtp`);
3. printed instructions.

Path 3 is not a fallback to be embarrassed about; for many people on macOS it is
the only reliable route.

### Edge 1040 gotchas

- **Firmware 9.2.9 or newer** is needed for converted maps to render at all.
- **The map list has a cap independent of free space.** If your new map does not
  show up in *Map Information* despite plenty of storage, delete some of the
  preinstalled Garmin maps you don't use.
- **Large transfers stall unless the device is booted into MTP mode.** Power the
  Edge off completely, then hold the lap button (bottom left) while connecting the
  USB cable until the screen says `usb mtp mode`.
- **Only one program can talk to the Edge at a time.** Quit Garmin Express *and*
  stop its background service in Activity Monitor first.
- Maps go in `Garmin/Map/` with unique filenames — not as a single `gmapsupp.img`
  at the root, which would collide.
- [OpenMTP](https://openmtp.ganeshrvel.com/) is the most reliable MTP client on
  macOS if you are copying by hand.

## Development

```console
$ uv run pytest                    # unit tests, offline, ~1s
$ uv run pytest -m integration      # real download + real build, minutes
```

The mkgmap and splitter versions are pinned in `src/garmap/config.py`: their
download URLs contain the revision and upstream offers no `latest` alias, so
bumping them is a deliberate act.
