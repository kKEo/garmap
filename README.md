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

`resources/` holds two real routes to try it on — see [Examples](#examples).

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

## Examples

Two real routes ship in `resources/`, one hilly and one flat, and between them they cover most of
the decisions you'll actually have to make. No output is quoted below — run `preview` and read
your own numbers off it, which is the habit worth building anyway.

### Lajkonik — 242 km in the Beskid Niski

```console
$ uv run garmap preview resources/Lajkonik_250km_.final.gpx --buffer 8km
$ uv run garmap build resources/Lajkonik_250km_.final.gpx \
      --buffer 8km --contours --name "Lajkonik 2025" -o lajkonik.img
$ uv run garmap install lajkonik.img
```

- 242 km of track in 6736 points, between 242 m and 762 m of elevation. That range is why
  `--contours` is worth its size here: on this route the contour lines tell you what the next
  hour is going to feel like.
- **Preview first.** Corridor area grows with route length *and* buffer, so 8 km either side of
  242 km of track is a far bigger download than 8 km either side of a 30 km loop. The preview
  legend gives you the figure before anything is fetched.
- The corridor runs along the małopolskie/podkarpackie boundary, which is exactly the case the
  greedy set cover in step 3 exists for. The preview page shows which extracts it settled on, and
  that choice is what the download size mostly comes down to.
- `--name` matters more than it looks: the family id is derived from it, and two maps sharing a
  family id make each other invisible or corrupt. One name per trip.

### Sudovia GRVL — 181 km of gravel near the Lithuanian border

```console
$ uv run garmap preview "resources/Sudovia GRVL KLASYK 20-05-26.gpx" --buffer 6km
$ uv run garmap build "resources/Sudovia GRVL KLASYK 20-05-26.gpx" \
      --buffer 6km --contours --contour-step 20 \
      --name "Sudovia 2026" -o sudovia.img
```

- **Quote the path.** This filename has spaces in it; unquoted, the shell hands garmap three
  arguments and it fails on the first one that isn't a file.
- Gravel is where the cycling TYP earns its keep: `highway=track` draws brown and clearly
  distinct from a thin grey path, so a wrong turn onto a footpath is visible on the Edge's screen
  rather than something you discover by pushing the bike.
- 181 km between 123 m and 281 m — flat. `--contour-step 10` would draw a great many nearly
  meaningless lines, so 20 m is the sensible interval. `--contours` still has to be there: it's
  what fetches the elevation tiles that `--contour-step` then spaces out.
- The north-east corner of this corridor is up against the Polish–Lithuanian border. Check the
  preview: if the buffer spills over, a second country extract joins the build, and that single
  fact can multiply the download. Tightening `--buffer` is the lever.

### Several routes, one map

```console
$ uv run garmap preview resources/*.gpx --buffer 6km        # look before you build
```

`build` and `preview` both accept several GPX files, so the days of a tour can share one `.img`.
The corridor is their union, though — and these two particular routes sit at opposite ends of
Poland, so the set cover has to reach for something far larger than either route needs on its own.
Preview it and read the estimate. Multi-GPX is for days that adjoin, not for unrelated rides.

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

`slides/` holds a Slidev deck — a beginner-friendly introduction and a full user guide.
`cd slides && npm install && npm run dev`.

The mkgmap and splitter versions are pinned in `src/garmap/config.py`: their
download URLs contain the revision and upstream offers no `latest` alias, so
bumping them is a deliberate act.
