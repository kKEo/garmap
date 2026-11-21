# Installation

## Requirements

| Requirement | Why | Notes |
|---|---|---|
| Python 3.11+ | garmap itself | declared in `pyproject.toml` |
| [uv](https://docs.astral.sh/uv/) | environment and lockfile | `uv.lock` is committed |
| JDK 17+ | mkgmap and splitter are Java programs | found through `JAVA_HOME`, then `PATH` |
| pyhgtmap | contour lines | optional extra, `--extra contours` |
| libmtp | direct copy to an MTP device | optional, `brew install libmtp` |

## Install

```console
$ uv sync --extra contours       # drop --extra contours if you don't want them
$ uv run garmap doctor           # checks Java, jars, optional deps, disk
```

`doctor` prints one line per check. `FAIL` lines are fatal; `--` lines mark an optional
feature that is unavailable.

```text
Java
  OK    runtime            openjdk version "21.0.6" 2025-01-21
Map tools
  OK    mkgmap             r4924 (will download on first build)
  OK    splitter           r654 (will download on first build)
Optional
  OK    pyhgtmap           found
  --    libmtp             absent; `brew install libmtp` for direct install, else garmap prints manual steps
Resources
  OK    memory             16384 MB total, 8192 MB heap for Java
  OK    disk               59.7 GiB free (extracts can be hundreds of MB)
  OK    cache              /Users/you/.cache/garmap
```

> **Known issue.** On a machine where `~/.cache` does not exist yet, `doctor` currently
> ends with a `FileNotFoundError` at the disk check. Run `mkdir -p ~/.cache` first. See
> finding [M2](../review/findings.md#m2-doctor-crashes-when-the-cache-parent-directory-is-missing).

## What gets downloaded, and where

Nothing is downloaded at install time. The first `build` fetches the two Java tools;
each build fetches whichever extracts and elevation tiles it needs.

| Directory | Contents | Typical size |
|---|---|---|
| `~/.cache/garmap/jars/` | unpacked mkgmap and splitter releases, plus their zips | tens of MB |
| `~/.cache/garmap/geofabrik/` | `.osm.pbf` extracts and `.etag` sidecars | hundreds of MB per region |
| `~/.cache/garmap/geofabrik-index-v1.json` | Geofabrik's region index | a few MB |
| `~/.cache/garmap/hgt/` | elevation tiles fetched by pyhgtmap | a few MB per 1° tile |

`XDG_CACHE_HOME` moves the whole tree. `garmap cache list` shows sizes;
`garmap cache clear --extracts|--hgt|--jars|--all` deletes them.

## Pinned tool versions

mkgmap and splitter are pinned in `src/garmap/config.py` (`MKGMAP_VERSION`,
`SPLITTER_VERSION`). Upstream has no `latest` URL, so a bump is an explicit code change.
The style patching in `style.py` depends on the layout of mkgmap's built-in `default`
style, so a bump should be followed by `uv run pytest -m integration`.
