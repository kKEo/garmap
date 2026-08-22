---
theme: seriph
title: garmap
info: |
  ## garmap
  Build a small, routable, cycling-tuned Garmin map that covers exactly one GPX route.

  A beginner-friendly introduction and user guide.
class: text-center
transition: slide-left
# NOTE: `mdc: true` is deliberately absent. Slidev 52.19.1's MDC plugin renders
# inline code through markdown-it's synchronous path, which now throws
# "async rule detected" for every slide with a `backtick` span in a heading,
# table cell or raw HTML block. No MDC attribute syntax is used in this deck.
---

# garmap

One route in. One map out.

<div class="pt-6 opacity-80">
Build a small, routable, cycling-tuned Garmin <code>.img</code><br>
that covers exactly the ride you planned — and nothing else.
</div>

<div class="abs-br m-6 text-sm opacity-50">
Edge 1040 · mkgmap r4924 · splitter r654
</div>

<!--
Twenty minutes, three acts: why you'd want this, how to set it up, then the guide.

If your audience already has a working install, Act 2 is skippable — but do not skip
the `doctor` slide, it saves the most support questions.
-->

---
layout: section
---

# Act 1

Why build your own map?

---

# The problem

You planned a ride somewhere your Edge doesn't know well.

<v-clicks>

- Garmin's stock maps are **multi-gigabyte** and **region-locked** — a European map won't help you in Colorado.
- Buying and installing a new region for one trip is slow, and the download is enormous.
- The cycling detail is coarse: unpaved tracks, cycleways and signed cycle routes all look much the same.
- Free community maps exist, but they're whole-country downloads too — you get 300 MB of Slovakia for a 35 km loop.

</v-clicks>

<div v-click class="mt-8 p-4 border-l-4 border-blue-400 bg-blue-400 bg-opacity-10">

You don't need a map of a country. You need a map of **a corridor around your route**.

</div>

<!--
The audience pain point is almost always a specific trip: a tour, a training camp, an
event abroad. Ask the room where they're going next — it makes the rest concrete.
-->

---
layout: two-cols
layoutClass: gap-8
---

# The idea

Take the route. Draw a band around it. Build a map of just that band.

<v-clicks>

- The **route** is your GPX file — red.
- The **corridor** is the route plus a buffer, say 6 km either side — blue.
- The corridor decides what gets downloaded, and what ends up on your device.
- If the corridor crosses a border, you need data from **both** sides — grey.

</v-clicks>

::right::

<div class="pt-14">
  <Corridor />
</div>

<div class="text-center text-sm opacity-60 mt-2">
A 35 km route in the Tatras, 6 km buffer: a 517 km² corridor
</div>

<!--
This is the single most important slide in the deck. Everything else is mechanics.

The border case is not an edge case — mountain routes sit on borders constantly, which is
exactly why the Tatras example was chosen.
-->

---

# What's in a Garmin map file?

A `.img` is a container. What matters is which parts are inside it.

| Inside | What it does | Without it |
|---|---|---|
| `TRE` `RGN` `LBL` | geometry and labels | nothing draws |
| `NET` `NOD` | the **routing graph** | the map draws but can't navigate |
| `MDR` | the search index | you can't search for places |
| `TYP` | rendering rules — colours, widths | everything looks like Garmin's default |

<div v-click class="mt-6">

garmap builds all of them. That `NET`/`NOD` pair is the difference between a picture of a
map and a map your Edge can give you turn-by-turn directions on.

</div>

<!--
People conflate "the map shows up" with "the map works". Routing is a separate data
structure and it's the thing that silently goes missing in hand-rolled builds.
-->

---

# What garmap does

<div class="pt-10 pb-8">
  <Pipeline />
</div>

<v-clicks>

- garmap itself is **orchestration** — a few thousand lines of Python.
- The actual map building is done by **splitter** and **mkgmap**, the tools the OpenStreetMap-to-Garmin world has used for fifteen years.
- Map data comes from **Geofabrik**, contour lines from **Viewfinder Panoramas** via pyhgtmap.
- All of it is downloaded and cached on first use. You install nothing by hand.

</v-clicks>

<!--
Worth saying out loud: garmap is not a new map compiler. Reusing mkgmap is why the output
is trustworthy. We contribute the "which data, clipped to what" decisions.
-->

---
layout: center
class: text-center
---

# The whole thing is three commands

```bash
garmap preview tour.gpx --buffer 15km
garmap build   tour.gpx --buffer 15km --contours -o alps-tour.img
garmap install alps-tour.img
```

<div class="mt-8 opacity-70">
Look before you download · build · copy to the device
</div>

<!--
Put this slide up and leave it. Everything in Act 3 is a detail hanging off one of
these three lines.
-->

---

# What garmap is not

<v-clicks>

- **Not a route planner.** Bring a GPX from Komoot, RideWithGPS, Strava, Garmin Connect — anywhere.
- **Not a replacement for Garmin Connect.** Your activities, workouts and sync are untouched.
- **Not a full-country map.** That's the point. If you want all of France, download all of France from someone else.
- **Not magic about data quality.** It's OpenStreetMap. If a trail is missing from OSM, it's missing from your map — and you can go fix it.

</v-clicks>

<div v-click class="mt-8 opacity-70">

It's one narrow job: *this route → a working map*.

</div>

<!--
The last point is a good place to plug OSM editing. People who build their own maps often
become good mappers, because they see the gaps.
-->

---
layout: section
---

# Act 2

Getting set up

---
layout: two-cols
layoutClass: gap-8
---

# Two things to install

## 1. A Java runtime

```bash
brew install --cask temurin
```

JDK **17 or newer**. splitter and mkgmap are Java programs — this is what actually
builds your map.

## 2. uv

```bash
brew install uv
```

Runs garmap and its Python dependencies without you managing a virtualenv.

::right::

<div class="pt-14">

## Then garmap itself

```bash
cd garmin
uv sync --extra contours
```

<div class="mt-4 text-sm opacity-75">

`--extra contours` pulls in pyhgtmap, which draws the contour lines. Leave it off if you
don't want them; you can always add it later.

</div>

<div class="mt-8 p-4 border-l-4 border-amber-400 bg-amber-400 bg-opacity-10 text-sm">

On macOS, also consider `brew install libmtp`. It's optional, but it's what lets garmap
push the finished map onto an Edge 1040 directly. More on that later.

</div>

</div>

<!--
Nothing else needs installing: mkgmap, splitter and the elevation data are all fetched
on demand and cached. That's deliberate — those are GPL Java tools we invoke, not vendor.
-->

---

# Check it: `garmap doctor`

<Terminal title="uv run garmap doctor">

```text
Java
  OK    runtime            openjdk version "21.0.6" 2025-01-21 LTS
Map tools
  OK    mkgmap             r4924 cached
  OK    splitter           r654 cached
Optional
  OK    pyhgtmap           found
  --    libmtp             absent; `brew install libmtp` for direct install, else
                           garmap prints manual steps
Resources
  OK    memory             18432 MB total, 9216 MB heap for Java
  OK    disk               4.6 GiB free (extracts can be hundreds of MB)
  OK    cache              /Users/you/.cache/garmap

Ready to build.
```

</Terminal>

<div v-click class="mt-4">

Three states, and only one of them is bad:

**`OK`** fine · **`--`** optional and absent, one feature unavailable · **`FAIL`** must be fixed

</div>

<!--
The yellow `--` rows are the most common support question: people read any non-green row as
broken. Say explicitly that a `--` on libmtp just means "you'll copy the file by hand".

"r4924 cached" vs "will download on first build" is also normal — both are fine.
-->

---

# Where things get downloaded

<Terminal title="uv run garmap cache list">

```text
  jars         10.7 MiB  6 item(s)  /Users/you/.cache/garmap/jars
  extracts    518.2 MiB  4 item(s)  /Users/you/.cache/garmap/geofabrik
  hgt         569.0 MiB  2 item(s)  /Users/you/.cache/garmap/hgt
  total         1.1 GiB
```

</Terminal>

<v-clicks>

- **jars** — mkgmap and splitter. Tiny, download once, never again.
- **extracts** — the OpenStreetMap country/region files. Hundreds of MB each. These are the reason your first build is slow and your second is fast.
- **hgt** — elevation tiles for contours. Also large, also reused.

</v-clicks>

<div v-click class="mt-6">

```bash
garmap cache clear --extracts   # reclaim the big one
garmap cache clear --all        # start completely fresh
```

</div>

<!--
Set the expectation now: the first build of a new region downloads a lot. Every later
build in the same region is fast. Extracts are revalidated by ETag, not re-downloaded
blindly — a two-week-old cached extract is reused unless you pass --refresh.
-->

---
layout: section
---

# Act 3

The user guide

---

# Always preview first

`preview` does everything `build` does — except the slow, expensive parts.

<Terminal title="uv run garmap preview tour.gpx --buffer 6km">

```text
==> Reading route
    1 route segment(s), 35 km of track
    corridor: 517 km2 (6 km either side)
==> Choosing OSM extracts
    Województwo małopolskie (Lesser Poland Voivodeship) (malopolskie)
    Slovakia (slovakia)
==> Estimating download
    Województwo małopolskie (malopolskie): cached
    Slovakia (slovakia): cached
    total 518.2 MiB (cached extracts are reused)

Wrote tour-preview.html
      tour-preview.geojson
```

</Terminal>

<div v-click class="mt-4">

It opens the HTML in your browser automatically. `--no-open` if you'd rather it didn't.

</div>

<!--
"total 518.2 MiB" is the number that stops mistakes. If someone accidentally buffers by
150 km instead of 15, they find out here in two seconds instead of after a 4 GB download.
-->

---
layout: two-cols
layoutClass: gap-8
---

# Reading the preview

<div class="pt-4">
  <Corridor />
</div>

::right::

<div class="pt-10">

<v-clicks>

**Red** — your route, exactly as the GPX describes it. If this looks wrong, the problem is
your GPX, not garmap.

**Blue** — the corridor. Check it actually contains everywhere you might detour, bail out,
or find a shop.

**Grey, dashed** — the OSM extracts garmap picked. Two here, because the route sits on the
Poland/Slovakia border.

</v-clicks>

<div v-click class="mt-6 text-sm opacity-75">

garmap picks the *smallest* extracts that cover the corridor. For this route that's one
Polish voivodeship plus Slovakia — not all of Europe.

</div>

</div>

<!--
If the legend shows a whole continent, the corridor is probably enormous by accident, or
the route crosses many small regions and garmap collapsed them to a common parent.
-->

---

# `--buffer` is the main dial

How far either side of the route to include. Default **15 km**.

| `--buffer` | Corridor | Map size |
|---|---|---|
| `2km` | 149 km² | 2.2 MiB |
| `6km` | 517 km² | 3.9 MiB |
| `15km` (default) | 1,682 km² | 8.5 MiB |

<div class="text-sm opacity-60 mt-2">
Measured on the same 35 km route, no contours. Your numbers scale with route length and how built-up the area is.
</div>

<v-clicks>

- Accepts `15km`, `2500m`, or a bare `2500` (metres).
- **Too small** and one wrong turn puts you off the edge of the map.
- **Too big** costs download time and device storage — but even 15 km here is under 10 MB, so err generous.

</v-clicks>

<!--
Rule of thumb to give the room: whatever detour you'd actually consider mid-ride, plus the
nearest town with a train station. For most people that's 10–15 km.
-->

---

# `build`, stage by stage

<div class="grid grid-cols-2 gap-6">

<Terminal title="garmap build tour.gpx --buffer 6km --contours">

```text
==> Checking tools
    openjdk version "21.0.6" 2025-01-21 LTS
==> Reading route
    1 route segment(s), 35 km of track
    corridor: 517 km2 (6 km either side)
==> Choosing OSM extracts
    Województwo małopolskie (malopolskie)
    Slovakia (slovakia)
==> Downloading OSM data
    malopolskie-latest.osm.pbf (191.2 MiB)
    slovakia-latest.osm.pbf (326.9 MiB)
==> Clipping and splitting into tiles
    16 tile(s)
==> Generating 10 m contour lines
    2 contour tile(s)
==> Compiling map
```

</Terminal>

<div class="text-sm">

<v-clicks>

**Checking tools** — Java, and the two jars, downloaded on first use.

**Reading route** — your GPX becomes one buffered corridor.

**Choosing extracts** — smallest regions that cover it. Two, because of the border.

**Downloading** — the slow step. Once per region, then cached forever.

**Clipping + splitting** — the corridor is handed to splitter as a polygon; it clips and cuts.

**Contours** — elevation tiles fetched and traced.

**Compiling** — mkgmap turns 18 tiles into one `.img`.

</v-clicks>

</div>

</div>

<!--
Timings on a 2023 MacBook Pro: split ~35 s, contours ~40 s, compile ~7 s. The download
dominates a cold run and disappears entirely on a warm one.
-->

---

# Reading the report

<Terminal title="the last thing build prints">

```text
Built /Users/you/rides/podhale.img
    name        Podhale test
    family id   55602
    size        4.7 MiB
    tiles       18

Next: garmap install /Users/you/rides/podhale.img
```

</Terminal>

<v-clicks>

- **name** — what you'll see on the device. Set it with `--name`; it defaults to the GPX filename.
- **family id** — derived from the name, and **unique per map**. This is what stops your map colliding with Garmin's stock maps, or with your other garmap maps. Two maps sharing one family id make each other invisible or corrupt.
- **size** — what it costs on the device.
- **tiles** — map tiles compiled. `16 + 2` here: sixteen OSM, two contour.

</v-clicks>

<div v-click class="mt-4 text-sm opacity-75">

Different `--name` → different family id. Give each trip its own name and they coexist happily.

</div>

<!--
The family-id explanation is worth the time. It's the single most confusing Garmin concept
and it's why "my new map made my other map disappear" happens to people who hand-roll this.
-->

---

# Contour lines

```bash
garmap build tour.gpx --buffer 6km --contours --contour-step 10
```

<v-clicks>

- **`--contours`** adds elevation lines, labelled **in metres**.
- **`--contour-step`** is the interval, default `10` m. Use `20` or `25` in the high mountains — 10 m contours in the Alps are a grey smear on a bike computer screen.
- Data comes from Viewfinder Panoramas, which needs no account or API key.
- Cost on the example route: **3.9 MiB → 4.7 MiB**. Cheap.

</v-clicks>

<div v-click class="mt-6 p-4 border-l-4 border-blue-400 bg-blue-400 bg-opacity-10">

Contours need the `contours` extra: `uv sync --extra contours`. If it's missing, `doctor`
tells you, and `build` fails with a message saying you can re-run without `--contours`.

</div>

<!--
Contours are the single biggest quality-of-life win for anyone riding hills, because the
Edge's climb detection gets better data to work with.
-->

---

# Shaded relief: `--dem`

```bash
garmap build tour.gpx --buffer 6km --contours --dem
```

<v-clicks>

- Embeds the raw elevation grid, so the Edge can shade the terrain rather than just draw lines.
- **Requires `--contours`** — that's the step that downloads the elevation tiles. Asking for `--dem` alone is an error, not a silent no-op.
- Makes the map **noticeably** bigger. Try it on a small corridor first.

</v-clicks>

<div v-click class="mt-8 opacity-75">

Nice on a screen you're looking at while stopped. Optional for navigation.

</div>

<!--
This is the one flag where the size cost can surprise people — the DEM grid does not care
how few roads are in your corridor.
-->

---

# `--drive-on`: which side of the road?

```bash
garmap build tour.gpx --drive-on left     # UK, Ireland, Japan, Australia...
```

<v-clicks>

- Default is **`detect`**, which reads administrative boundary data inside the corridor.
- Small corridors sometimes contain no boundary data at all. Then mkgmap warns:

  ```
  Found 2 roads with unknown country and driving side
  ```

- Harmless for two roads. But if you're building for a left-hand-traffic country, **set it explicitly** — routing instructions depend on it.

</v-clicks>

<div v-click class="mt-6 text-sm opacity-75">

`--bounds <dir>` points at a precompiled mkgmap bounds directory if you have one, which
fixes `detect` properly and enables address search.

</div>

<!--
Turn instructions at roundabouts are what break first when the driving side is wrong.
-->

---

# Flags you'll probably never need

<v-clicks>

**`--sea`**
Generates sea polygons. Worth it for coastal routes, where without it the sea renders as
undefined blank space.

**`--max-nodes 1400000`**
How finely the data is cut into tiles. The default is mkgmap's recommendation. Only touch
it if splitter runs out of memory.

**`--refresh`**
Re-download the OSM extracts even if cached. Use it when you know OSM has been fixed
recently and you want that fix.

**`--bounds <dir>`**
Precompiled boundary data, for address search and reliable driving-side detection.

</v-clicks>

<!--
Say the quiet part: the defaults are chosen so that a beginner never needs this slide. It's
here so nobody wonders what the flags in `--help` do.
-->

---
layout: center
class: text-center
---

# Getting it onto the Edge

```bash
garmap install podhale.img
```

<div class="mt-8 text-left max-w-2xl mx-auto">

garmap tries three things, in order:

1. A **mounted volume** with a `Garmin/Map/` folder — older units, and SD cards.
2. **`mtp-sendfile`** from libmtp, if you installed it.
3. **Printed instructions**, if neither worked.

</div>

<div v-click class="mt-8 p-4 border-l-4 border-amber-400 bg-amber-400 bg-opacity-10 text-left max-w-2xl mx-auto">

Path 3 is not a failure. **The Edge 1040 is MTP-only** — macOS does not mount it as a
volume at all — so for a lot of people it's the only route that works reliably.

</div>

<!--
Set expectations here or people think garmap is broken. It isn't; Apple and MTP are just
not friends.
-->

---

# The manual path, in full

<Terminal title="garmap install podhale.img — with no volume mounted">

```text
No Garmin volume is mounted.
The Edge 1040 uses MTP, which macOS does not mount as a volume.
`brew install libmtp` would let garmap push the file directly.

Copy the map across by hand:

  1. Quit Garmin Express AND stop its background service in Activity
     Monitor -- only one program can talk to the Edge over USB at a time.
  2. Power the Edge off completely.
  3. Hold the lap button (bottom left) while connecting the USB cable,
     until the screen shows 'usb mtp mode'. Large .img transfers
     routinely stall without this.
  4. Open the device in an MTP client -- OpenMTP is the most reliable
     on macOS (https://openmtp.ganeshrvel.com/).
  5. Copy podhale.img into Garmin/Map/ on the device, as podhale.img.
```

</Terminal>

<!--
garmap prints this for you, so nobody has to remember it. Walk through it anyway — steps 1
and 3 are the two that people skip and then spend an hour on.
-->

---

# Four gotchas that each cost an hour

<v-clicks>

**Firmware 9.2.9 or newer.**
Older firmware renders custom maps as blank. Update the Edge first.

**The map list has a cap, independent of free space.**
If your map doesn't appear in *Map Information* despite gigabytes free, delete some
preinstalled Garmin maps you don't use. Inactive maps still count.

**Hold the lap button while plugging in.**
Power off completely, hold the bottom-left button, connect USB, wait for `usb mtp mode`.
Large transfers stall without it.

**Quit Garmin Express *and* its background service.**
Only one program can hold the USB connection. Quitting the window is not enough — stop the
service in Activity Monitor.

</v-clicks>

<!--
Every one of these was learned the hard way. If your audience takes one slide home, this
is the one — it is also reproduced in the README.
-->

---

# One more device detail

<v-clicks>

- Maps live in **`Garmin/Map/`** on the device, with **unique filenames**.
- Not as a single `gmapsupp.img` at the device root — that name collides with other maps.
- `garmap install` refuses to overwrite an existing map unless you pass `--force`.
- `--name` on install changes the filename on the device without rebuilding.

</v-clicks>

<div v-click class="mt-8">

```bash
garmap install podhale.img --name tatras-2026.img
garmap install podhale.img --force           # replace what's there
```

</div>

<div v-click class="mt-6 opacity-75">

On the device: **Menu → Maps → Map Information**, enable it, and navigate your route.

</div>

<!--
The refuse-to-overwrite default has saved people from clobbering the map they were
currently navigating with.
-->

---

# When something goes wrong

<div class="mb-4">

The first thing to reach for:

```bash
garmap build tour.gpx --buffer 6km --keep-work --work-dir ./work -v
```

`-v` streams what splitter and mkgmap are actually doing; `--keep-work` leaves every
intermediate file in `./work` instead of deleting it.

</div>

<v-clicks>

| Symptom | Cause | Fix |
|---|---|---|
| `extracts cover 87% of the corridor` | route leaves the available data | check `preview`; it's often a bad GPX coordinate |
| `splitter produced no tiles` | corridor doesn't intersect the data | run `preview` — usually lat/lon swapped |
| `Java heap space` | corridor too big for the machine | smaller `--buffer`, or raise `--max-nodes` |
| build dies on download | Geofabrik hiccup | re-run; partial downloads are never reused |

</v-clicks>

<!--
The lat/lon swap is by far the most common real-world failure, and `preview` catches it
instantly — the route shows up in the ocean off West Africa.
-->

---
layout: center
class: text-center
---

# That's the whole guide

```bash
garmap preview tour.gpx --buffer 15km
garmap build   tour.gpx --buffer 15km --contours -o alps-tour.img
garmap install alps-tour.img
```

<div class="mt-10 opacity-70">

`garmap doctor` when something looks off · `garmap cache list` when your disk fills up

</div>

<div class="mt-10 text-sm opacity-50">
The rest of this deck is optional — how it works underneath.
</div>

<!--
Natural stopping point. If the room is beginners, stop here and take questions; the
appendix is for the curious and for contributors.
-->

---
layout: section
---

# Appendix

Under the hood — safe to skip

---

# The pipeline in full

<div class="pt-6 pb-6">
  <Pipeline />
</div>

<div class="text-sm">

| Stage | What happens | Tool |
|---|---|---|
| Route | every `<trk>` and `<rte>` is read; waypoints ignored | gpxpy |
| Corridor | buffered in a local equidistant projection, so metres mean metres | shapely + pyproj |
| Extracts | weighted greedy set cover over Geofabrik's region tree | — |
| Clip + split | `--polygon-file` clips; tiles capped at 1.4 M nodes | splitter r654 |
| Contours | Viewfinder Panoramas elevation → contour ways | pyhgtmap |
| Compile | routing, index, style, TYP → `gmapsupp.img` | mkgmap r4924 |

</div>

<div v-click class="mt-4 text-sm opacity-75">

Note what's *absent*: no osmium, no osmconvert. splitter's `--polygon-file` does the
clipping, so there's one less thing to install.

</div>

<!--
The "waypoints ignored" decision is deliberate: a bag of unordered points is not a route
corridor, and buffering it would produce nonsense.
-->

---

# Why one splitter pass per extract

<v-clicks>

Hand splitter two Geofabrik extracts at once and it refuses:

```
Error: Node ids are not sorted. Use e.g. osmosis to sort the input data.
This is not supported with keep-complete=true or --problem-list
```

Each extract is sorted **within itself**, never across the pair. Three options:

- Merge them first → needs osmosis or osmium, the dependency we're avoiding.
- Drop `--keep-complete` → silently truncates ways and relations at tile edges, **damaging routing**.
- **One pass per extract** → keeps both, at the cost of a thin strip of duplicated data at borders.

</v-clicks>

<div v-click class="mt-6 text-sm opacity-75">

Each pass gets its own directory (splitter writes `areas.list` with a fixed name) and its
own block of 1000 map ids, so tile ids can never collide.

</div>

<!--
This is the kind of constraint that only shows up on a real cross-border route — which is
exactly why the test fixture is a border route.
-->

---

# Why the cycling look lives in the TYP

<v-clicks>

The obvious approach is to give cycleways their own prominent line type. It doesn't work:

<div class="p-4 border-l-4 border-red-400 bg-red-400 bg-opacity-10">

**Garmin only routes over line types below `0x14`.** Custom types (`0x10000`+) render
beautifully and are completely unroutable.

</div>

So the split is:

- **Style** (rules: which OSM tag becomes which Garmin type) — left almost entirely as mkgmap's default, so routable types stay routable.
- **TYP** (rendering: colour, width, label) — where all the cycling emphasis lives. Cycleways blue at width 6, tracks brown, paths thin grey, residential roads dialled back, contours in browns.

</v-clicks>

<!--
A pretty, unroutable map is the classic first-timer mistake with custom Garmin maps. Worth
naming so nobody in the room repeats it.
-->

---

# Why the style is patched, not written

<v-clicks>

garmap copies mkgmap's `default` style **out of the pinned jar** at build time and patches
exactly two things:

1. **Contours labelled in metres**, not feet.
2. **Cycle route names appended** to member ways — so the Edge says *"Lane (EV4)"* rather than just *"Lane"*.

</v-clicks>

<div v-click class="mt-6">

Everything else is untouched. A hand-written style would drift from upstream with every
mkgmap release and quietly lose POIs and routing attributes.

</div>

<div v-click class="mt-6 text-sm opacity-75">

The versions are pinned in `src/garmap/config.py` — mkgmap's download URLs contain the
revision and upstream offers no `latest` alias, so bumping them is a deliberate act.

</div>

<!--
The relation patch has a subtlety: inside mkgmap's `apply` block, `${name}` is the
*relation's* name and `$(name)` is the *member way's*. Getting it backwards throws away
every road name in the map.
-->

---

# Contributing

<v-clicks>

```bash
uv run pytest              # 84 tests, fully offline, ~0.5 s
uv run pytest -m integration   # real download + real build, ~2 min
```

- Unit tests mock the network and the Java tools, and assert the **argv** those tools get — that's where the subtle bugs live.
- The integration test builds a real map from a real extract and asserts the `NET`/`NOD` subfiles are present. A map that isn't routable fails the suite.
- `tests/fixtures/short-route.gpx` is a 35 km Tatras loop that deliberately **crosses a border** and **closes on itself** — the two cases that broke things during development.

</v-clicks>

<!--
The loop-closing fixture is a regression test for splitter's hole handling: buffering a
loop produces a polygon with an interior ring, which splitter r654 mishandles, so garmap
strips interior rings before writing the .poly.
-->

---
layout: center
class: text-center
---

# Go build a map

```bash
garmap preview your-next-ride.gpx --buffer 15km
```

<div class="mt-10 opacity-70">
Full reference in <code>README.md</code> · <code>garmap doctor</code> if in doubt
</div>

<!--
End on the command you want them to run tonight, not on a thank-you slide.
-->
