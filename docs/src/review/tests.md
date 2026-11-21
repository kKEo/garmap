# Tests and tooling

## What exists

```console
$ uv run pytest                    # 84 passed, 2 deselected, about 1 s
$ uv run pytest -m integration     # real downloads and a real build; minutes
```

- Unit tests are offline. HTTP is faked, Java is not started, and `/Volumes` is
  redirected to a temporary directory.
- Two integration tests build a real map from `tests/fixtures/short-route.gpx` and
  check that the image contains the `RGN`, `TRE`, `NET`, `NOD` and `TYP` subfiles.
  `NET` and `NOD` are the routing data, so this catches "renders but cannot navigate".
- Integration tests are deselected by default through `addopts`.

## Coverage

Measured with `uv run --with pytest-cov pytest --cov=garmap`:

| Module | Statements | Covered |
|---|---|---|
| `gpx.py` | 36 | 100 % |
| `corridor.py` | 40 | 98 % |
| `http.py` | 55 | 95 % |
| `config.py` | 39 | 95 % |
| `splitter.py` | 30 | 93 % |
| `mkgmap.py` | 50 | 92 % |
| `device.py` | 47 | 91 % |
| `geofabrik.py` | 112 | 78 % |
| `tools.py` | 95 | 69 % |
| `cli.py` | 262 | 25 % |
| `contours.py` | 38 | 0 % |
| `preview.py` | 20 | 0 % |
| `style.py` | 37 | 0 % |
| **Total** | **863** | **58 %** |

The pattern is clear: pure functions are well covered, and the code that sequences them
is not. `cli.py` is the largest module and holds the option validation, the work-directory
lifecycle and `doctor`. That is where findings H1, M2, M3 and M4 live.

## Gaps, in order of value

1. **CLI tests with `CliRunner`.** Stub `splitter.split`, `contours.generate` and
   `mkgmap.compile_map`, then test `build` end to end: option validation order, work
   directory cleanup, `--keep-work`, the final report. Test `doctor` with a missing
   cache directory. Test `preview` output files. This alone would have caught M2 and
   M4.
2. **Stale-directory tests.** Run `splitter.split` twice into one directory with
   different fake outputs (H1).
3. **`style.materialise` against a fake jar.** A zip with `styles/default/relations`
   and `inc/contour_lines` is enough to test both patches and both failure messages.
4. **`contours.build_args`.** A pure function with no test.
5. **`preview.build_geojson` and `write`.** Check the three feature kinds and that the
   HTML is well formed with awkward titles (L4).
6. **`geofabrik.local_path` uniqueness** across a real index snapshot (H2).
7. **A two-extract integration test** with a routing assertion (M5), and one with
   `--dem` (H3).

## Tooling that is missing

| Missing | Suggestion |
|---|---|
| CI | a GitHub Actions workflow: `uv sync`, `uv run pytest`, on Python 3.11 and 3.13 |
| Linter and formatter | `ruff check` and `ruff format`; `ruff check` with default rules reports 5 issues today |
| Type checking | most of the code is annotated (the `cli.py` command functions are not); `mypy` or `pyright` would be cheap to adopt |
| Scheduled integration run | weekly, so that upstream changes at Geofabrik, Viewfinder or mkgmap.org.uk are noticed |
| Docs build | `mdbook build docs` in CI, to keep this book from rotting |

## Slides

`slides/` is a Slidev deck that repeats much of the README. It was skimmed for this review,
not checked line by line. Because it restates option names and behaviour, it should
be re-checked whenever the CLI changes.
