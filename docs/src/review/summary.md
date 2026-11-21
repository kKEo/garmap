# Review summary

Reviewed: garmap 0.1.0 at commit `f125a77`, all of `src/garmap/`, the tests, and the
project configuration.

## Verdict

The code is well organised and unusually well explained for its size. The pipeline is
split along the right seams, external tools are wrapped in thin, testable argument
builders, and the comments record why each non-obvious choice was made. The unit suite
is fast (84 tests in about a second) and offline.

The weak spots are at the edges of the happy path: cache identity, reuse of
intermediate directories, one feature (`--dem`) that probably does not work, and first-run
behaviour on a clean machine. None requires a redesign. The three high-severity
findings are each a fix of a few lines.

## Findings at a glance

| Severity | Count | Meaning |
|---|---|---|
| High | 3 | produces a wrong map or a feature that silently does nothing |
| Medium | 7 | crash, wasted time, or an unverified risk in a core path |
| Low | 11 | polish, hygiene, documentation |

| Id | Finding | Module | Status |
|---|---|---|---|
| [H1](findings.md#h1-a-reused---work-dir-leaks-old-tiles-into-the-new-map) | Reused `--work-dir` leaks old tiles into the new map | splitter, contours, mkgmap | reproduced |
| [H2](findings.md#h2-extract-cache-filenames-collide) | Extract cache filenames collide | geofabrik | reproduced |
| [H3](findings.md#h3---dem-points-mkgmap-at-the-wrong-directory-level) | `--dem` points mkgmap at the wrong directory level | cli, contours | half verified |
| [M1](findings.md#m1-downloaded-jars-are-executed-without-an-integrity-check) | Jars executed without an integrity check | tools, http | by reading |
| [M2](findings.md#m2-doctor-crashes-when-the-cache-parent-directory-is-missing) | `doctor` crashes when the cache parent is missing | cli | reproduced |
| [M3](findings.md#m3-a-corrupt-index-cache-cannot-be-repaired-from-the-cli) | Corrupt index cache cannot be repaired from the CLI | geofabrik, cli | reproduced |
| [M4](findings.md#m4---dem-without---contours-fails-late) | `--dem` without `--contours` fails late | cli | by reading |
| [M5](findings.md#m5-routing-across-the-seam-between-extracts-is-untested) | Routing across the extract seam is untested | splitter | open question |
| [M6](findings.md#m6-no-character-set-is-chosen-for-the-map) | No character set chosen for the map | mkgmap, TYP | open question |
| [M7](findings.md#m7-no-ci-and-the-orchestration-code-is-barely-tested) | No CI; orchestration code barely tested | project | measured |
| [L1](findings.md#l1-dead-and-unreachable-code)–[L11](findings.md#l11-concurrent-runs-share-staging-paths) | eleven low-severity items | various | mixed |

## How the findings were checked

- **Reproduced**: a short script or command showed the behaviour on this checkout.
- **By reading**: follows directly from the code; nothing to run.
- **Measured**: from `pytest --cov`.
- **Half verified / open question**: depends on how mkgmap or splitter behaves at
  runtime. No full build could be run during the review, because the review
  environment could not reach `download.geofabrik.de` or `mkgmap.org.uk`. These items
  say exactly what remains to be confirmed.

## Strengths worth keeping

- **Reasons in comments.** `splitter.py`'s module docstring, the hole-stripping note in
  `corridor.py` and the "exits 0 with nothing compiled" note in `mkgmap.py` each save a
  future maintainer a long debugging session.
- **Patch, don't fork, the style.** Copying mkgmap's default style out of the pinned
  jar and making two small changes avoids a whole class of drift.
- **Rendering in the TYP, routing in the style.** A clean split that keeps custom
  looks from breaking routing.
- **Download discipline.** `.part` files, ETag revalidation and offline fallback are
  all present and tested.
- **Verification by artefact.** Counting compiled tiles instead of trusting mkgmap's
  exit code catches a real failure mode.
- **Honest user-facing text.** Error messages say what to do next. The README and
  `device.py` are frank about MTP on macOS.
