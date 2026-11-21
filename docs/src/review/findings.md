# Findings

Line numbers refer to commit `f125a77`.

## High

### H1 A reused `--work-dir` leaks old tiles into the new map

**Where:** `splitter.py:84-98`, `contours.py:105`, `mkgmap.py:108-116`

`splitter.split` creates `tiles/passN` with `exist_ok=True` and then collects every
`<digits>.osm.pbf` in it. Nothing empties the directory first. If an earlier build in
the same `--work-dir` produced more tiles than the current one, the extra files are
still there and are handed to mkgmap.

Reproduction, with `run_java` stubbed to write one new tile into a directory that
already held an old one:

```text
>>> splitter.split([extract], poly, work)
['63240001.osm.pbf', '63240007.osm.pbf']      # 63240007 is from the previous run
```

The same pattern exists in two more places:

- `contours.generate` globs `contours/*.osm.pbf`, so old contour tiles are reused;
- `mkgmap._tile_count` counts every `NNNNNNNN.img` in `out/`, so old tile images make
  the "mkgmap wrote no map tiles" check pass when the current run wrote none.

**Impact:** a map that silently contains data from another route, or a build that
reports success with stale output. The README recommends `--keep-work --work-dir ./work`
as the first debugging step, so repeated use of one directory is the expected workflow.

**Fix:** clear what each stage owns before it runs. `style.materialise` already does
this for `cycle/` (`style.py:38`).

```python
# splitter.split, per pass
shutil.rmtree(pass_dir, ignore_errors=True)
pass_dir.mkdir(parents=True)
```

Do the same for `work/contours` and `work/out`, and remove `tiles/` as a whole so that a
`pass1` from an earlier two-extract build does not linger.

### H2 Extract cache filenames collide

**Where:** `geofabrik.py:200-202`

```python
return extracts_dir() / region.pbf_url.rsplit("/", 1)[-1]
```

The cache key is the last path segment of the URL. Geofabrik reuses basenames across
parents. The country Georgia and the US state of Georgia are both
`georgia-latest.osm.pbf`:

```text
>>> local_path(europe_georgia) == local_path(us_georgia)
True
```

**Impact:** after building a map in one, a build in the other finds a "cached" file
younger than 14 days and uses it without a network request. splitter then clips the
wrong region and reports "produced no tiles", pointing the user at coverage, which is
not the problem. `--refresh` works around it but then overwrites the other entry.

**Fix:** key on the region id, which is unique and already path-shaped:

```python
return extracts_dir() / f"{region.id.replace('/', '_')}-latest.osm.pbf"
```

### H3 `--dem` points mkgmap at the wrong directory level

**Where:** `cli.py:258`, `contours.py:17`, `mkgmap.py:93`

`build` passes `dem_dir=hgt_dir()`, i.e. `~/.cache/garmap/hgt`, to mkgmap as
`--dem=<dir>`. pyhgtmap does not store tiles there. It stores them one level down, in a
directory per source:

```python
# pyhgtmap 4.1, sources/__init__.py
def get_cache_dir(self, resolution: int) -> str:
    return os.path.join(self.cache_dir_root, f"{self.NICKNAME.upper()}{resolution}")
```

With garmap's `view1,view3` sources, the tiles are in `hgt/VIEW1/` and `hgt/VIEW3/`.
mkgmap's `--dem` takes a list of directories or zip files that contain `.hgt` files
directly.

**Status:** the pyhgtmap layout is confirmed from its source. That mkgmap does not
search subdirectories is from its documentation and could not be run here. If it holds,
`--dem` yields a map with no usable elevation model, and no error.

**To confirm:** build with `--contours --dem -v --keep-work` and look for mkgmap's
messages about missing HGT files, or compare image sizes with and without `--dem`.

**Fix:** pass the source directories that exist, in preference order:

```python
dem_dirs = [d for d in (hgt_dir() / "VIEW1", hgt_dir() / "VIEW3") if d.is_dir()]
# --dem=VIEW1,VIEW3
```

No test covers `--dem`. Add an argument-level unit test and an integration assertion.

## Medium

### M1 Downloaded jars are executed without an integrity check

**Where:** `tools.py:98-129`, `config.py:11-15`, `http.py:25-88`

The mkgmap and splitter versions are pinned, but only by URL. The zip is downloaded
over HTTPS, unpacked, and its jar is run with the user's privileges. No digest is
checked, so a changed file at the same URL would run unnoticed. Geofabrik extracts are
likewise not compared with the `.md5` files published beside them.

**Fix:** add a SHA-256 per pinned version in `config.py` and verify it in `jar_path`
before unpacking. Bumping a version already requires a code change, so the digest costs
nothing extra. For extracts, fetching and checking `<url>.md5` is optional but cheap.

### M2 `doctor` crashes when the cache parent directory is missing

**Where:** `cli.py:454`

```python
usage = shutil.disk_usage(cache_dir().parent)
```

`disk_usage` raises `FileNotFoundError` if the path does not exist. A new macOS account
has no `~/.cache`, and `doctor` is the first command the README tells users to run.

```text
$ XDG_CACHE_HOME=/tmp/nope/deeper garmap doctor
...
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/nope/deeper'
```

**Fix:** walk up to the nearest existing ancestor before calling `disk_usage`, or
create the cache directory first.

### M3 A corrupt index cache cannot be repaired from the CLI

**Where:** `geofabrik.py:54-74`, `cli.py:101`, `cli.py:498-519`

Four things combine:

1. the index is written with `write_bytes` straight to its final path, so an
   interrupted run can leave a truncated file (`geofabrik.py:66`);
2. `json.loads` on that file is not guarded, so the next run ends in a
   `JSONDecodeError` traceback (`geofabrik.py:74`);
3. `load_index` has a `refresh` parameter, but the CLI never passes it, so
   `--refresh` does not help;
4. `cache clear --all` removes `jars/`, `geofabrik/` and `hgt/`, but the index lives
   beside them, not inside them.

The file stays broken until it is seven days old or the user deletes it by hand.

**Fix:** write to a temporary file and rename; on a parse error delete the file and
fetch again; pass `refresh` through from `build --refresh`; include the index in
`cache clear --extracts`.

### M4 `--dem` without `--contours` fails late

**Where:** `cli.py:244-245`

The check sits in the `elif` after the contour step, which runs after extracts have
been downloaded and split. A user who passes `--dem` alone waits minutes for an error
that could have been raised before any work started.

**Fix:** validate option combinations at the top of `build`, before "Checking tools".

### M5 Routing across the seam between extracts is untested

**Where:** `splitter.py` module docstring and `split`

Each extract is clipped to the *whole* corridor and tiled independently. Where the
corridor crosses from one extract to another, the result is two sets of tiles whose
rectangles overlap, with the border strip present in both. mkgmap joins routing between
tiles at shared tile boundaries. Tiles from different passes do not share boundaries.

The docstring acknowledges the duplicated strip. What is not established is whether the
Edge will route a single trip across the seam, and whether duplicated roads cause
doubled labels or odd turn instructions. The integration test uses one short route in
one extract, so it does not exercise this. The README's own Lajkonik example runs along
the małopolskie/podkarpackie boundary, so it is the common case, not a corner.

**To confirm:** build the Lajkonik example, load it in the device or in
[QMapShack](https://github.com/Maproom/qmapshack), and route between points on either
side of the voivodeship boundary.

**If it fails:** clip each pass to `corridor ∩ region` instead of the full corridor
to remove the overlap, or merge extracts before splitting.

### M6 No character set is chosen for the map

**Where:** `mkgmap.py:61-88`, `style/cycle.txt:14`

`build_args` passes none of `--unicode`, `--latin1` or `--code-page`. The TYP source
declares `CodePage=65001` (UTF-8). If mkgmap's default output encoding is a single-byte
Western code page, as its documentation describes, then:

- names with characters outside that code page (Polish `ł`, `ą`, `ś`, `ż`, which both
  sample routes are full of) are transliterated to ASCII on the device;
- the map and the TYP declare different code pages.

**Status:** not run. The first point is a quality issue; the second may be harmless.

**To confirm:** build a Polish route and look at street names on the device.

**Fix, if confirmed:** add `--unicode` (the Edge 1040 accepts Unicode maps) or
`--code-page=1250`, and make the TYP's `CodePage` agree.

### M7 No CI, and the orchestration code is barely tested

**Where:** project level

There is no CI configuration, no linter or type-checker configuration, and the code
with the most branches has the least coverage. Details are in
[Tests and tooling](tests.md). Findings H1, M2, M3 and M4 are all in code that no test
executes.

## Low

### L1 Dead and unreachable code

| Item | Where | Note |
|---|---|---|
| `BuildSettings` | `config.py:52` | never instantiated; has fields (`jobs`, `contour_source`, `style`) with no CLI option |
| `bbox` | `corridor.py:50` | no caller |
| `dry_run_command` ×2, `describe_command` | `splitter.py:115`, `mkgmap.py:180`, `tools.py:199` | tested, but there is no `--dry-run` option |
| `load_index(refresh=...)` | `geofabrik.py:54` | parameter never passed |
| `materialise(metric_contours=...)` | `style.py:35` | parameter never passed |
| `jobs`, `source` on `contours.generate` | `contours.py:67-74` | not reachable from the CLI |

Either wire these up (`--dry-run`, `--jobs` and `--contour-source` would all be useful) or
remove them.

### L2 Map name truncation and family-id derivation

**Where:** `cli.py:49-56`, `mkgmap.py:15-22`

- `default_map_name` appends ` +N` for extra GPX files and *then* truncates to 40
  characters, so a long first filename loses the suffix.
- The default name comes from the filename stem only. Two different routes both saved
  as `route.gpx` get the same name and the same family id, which is exactly the clash
  the README warns about.
- With 63,000 possible ids, two different names collide with probability about
  1 in 63,000 per pair. Acceptable, but the build report could mention the id's role.

**Fix:** truncate before adding the suffix. Consider warning when `--name` is omitted.

### L3 Preview total counts cached extracts

**Where:** `cli.py:310-318`

`total += size or 0` runs for every region, including cached ones, and the line then
says "(cached extracts are reused)". The figure shown is the total size, not the
download still needed. Print both, or only the uncached sum.

The coverage threshold `0.999` at `cli.py:105` duplicates `geofabrik.COVERAGE_TARGET`.

### L4 Preview HTML interpolates unescaped text

**Where:** `preview.py:13-55`, `preview.py:112-116`

The GPX-derived title goes into `<title>` unescaped, and `json.dumps` output goes into
a `<script>` block without escaping `</`. The inputs are the user's own filename and
Geofabrik's index, so the risk is low, but a `</script>` in either would break the page.
Leaflet is loaded from `unpkg.com` without Subresource Integrity.

**Fix:** `html.escape` the title, replace `</` with `<\/` in embedded JSON, add
`integrity` attributes.

### L5 Java banner and version parsing

**Where:** `tools.py:64-69`

- The banner shown to the user is the first line of `java -version` output. When
  `JAVA_TOOL_OPTIONS` is set, that line is `Picked up JAVA_TOOL_OPTIONS: ...`, not the
  version. Observed in the review environment.
- Java 8 reports `1.8.0`, so the message reads "Java 1 is too old".

**Fix:** show the line that matched the regex; map a leading `1.` to the second
number.

### L6 Install path is macOS-only and loosely matched

**Where:** `device.py:25`, `device.py:47-58`, `device.py:82-97`, `cli.py:372-377`

- Only `/Volumes` is scanned. Linux mounts under `/media` and `/run/media`.
- Any volume with a `Garmin/` folder matches, including a backup disk.
- `--force` is ignored on the MTP path, and there is no existing-file check there.
- No free-space check before copying to a volume.

### L7 `_common_ancestor` docstring and the silent collapse

**Where:** `geofabrik.py:122-128`, `geofabrik.py:173-175`

The docstring says "shallowest region that is an ancestor of every selection". The code
returns the common ancestor with the smallest area, which is the deepest one. The code
is right; the docstring is wrong.

When more than six regions collapse to that ancestor, the result can be a continent.
Nothing tells the user why the download suddenly became very large. Emit a message.

### L8 Option values are not validated

**Where:** `cli.py:144-172`, `cli.py:205`

`--contour-step 0`, a negative `--max-nodes`, and similar values go straight to the
external tools and fail there with their messages. Use `click.IntRange(min=1)`.
`-o` overwrites an existing file without notice.

### L9 Routable line types are misdescribed

**Where:** `README.md` ("Cycling style"), `style/cycle.txt:4-7`

Both say Garmin only routes over line types below `0x14`. The TYP itself restyles
`0x16` (path), which mkgmap's default style assigns to footways and paths as a routable
type. The design conclusion (do not use custom `0x10000+` types for anything that must
route) is sound. The stated rule is too narrow and should say "the standard routable
types" instead.

### L10 Repository hygiene

- No `LICENSE` file, so the code has no stated terms of use.
- No stated provenance or permission for the two GPX files in `resources/`.
- Map output is derived from OpenStreetMap (ODbL) and Viewfinder Panoramas data. The
  README credits the sources; a short "data licences" note would make the obligations
  explicit.
- `.gitignore` held only `*.pyc`. This change adds `.venv/`, `__pycache__/`,
  `.pytest_cache/`, `.coverage` and `docs/book/`. Built `*.img` and `*-preview.html`
  files in the repository root are still not ignored.
- There is no `__main__.py`, so `python -m garmap` does not work.

### L11 Concurrent runs share staging paths

**Where:** `tools.py:104-128`, `http.py:59`

Two garmap processes starting on an empty cache both unpack into
`jars/.mkgmap-unpack` and both write `<file>.part`. One can delete or overwrite the
other's work. Unlikely for a personal tool; a per-process suffix removes it.
