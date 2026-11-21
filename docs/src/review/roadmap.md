# Recommended order of work

Ordered by how much wrong behaviour each step removes per line changed.

## 1. Fix the three high-severity bugs

| Step | Finding | Size |
|---|---|---|
| Empty `tiles/`, `contours/` and `out/` before each stage writes to them | H1 | about 6 lines |
| Key the extract cache on the region id | H2 | 1 line, plus a note that old cache entries are orphaned |
| Point `--dem` at `hgt/VIEW1,hgt/VIEW3`, then confirm with a real build | H3 | about 5 lines |

Add a regression test with each.

## 2. Make the first run robust

| Step | Finding |
|---|---|
| `doctor`: tolerate a missing cache parent | M2 |
| Index cache: atomic write, self-heal on parse error, honour `--refresh`, clear with `cache clear` | M3 |
| Validate `--dem` / `--contours` and numeric ranges before any work | M4, L8 |
| Show the real Java version line | L5 |

## 3. Answer the two open questions on a device

Both need a real build and an Edge (or QMapShack):

- Does routing cross the seam between two extracts? (M5)
- Do Polish street names display correctly, or does the build need `--unicode`? (M6)

Record the answers in the splitter and mkgmap module docstrings, where the other
decisions are already documented.

## 4. Add a safety net

- CI running the unit tests and a linter (M7).
- `CliRunner` tests for `build`, `preview` and `doctor` (see
  [Tests and tooling](tests.md)).
- SHA-256 digests for the pinned tool zips (M1).

## 5. Tidy

- Remove or wire up the dead code (L1). `--dry-run` and `--jobs` are the two worth
  wiring up.
- Fix the map-name truncation and the misleading preview total (L2, L3).
- Escape text in the preview HTML (L4).
- Correct the routable-types wording and the `_common_ancestor` docstring (L9, L7).
- Add a `LICENSE` and a data-licence note (L10).

## Ideas beyond the findings

These are not defects. They came up while reading the code.

- **Clip each splitter pass to `corridor ∩ region`.** This removes the duplicated strip
  between extracts and may settle M5 outright.
- **Resume interrupted downloads** with a `Range` request against the `.part` file.
  Extracts are hundreds of megabytes.
- **Linux install support**: scan `/media/$USER` and `/run/media/$USER`.
- **Report corridor area and extract sizes in `build` too**, so a user who skipped
  `preview` still sees what they are about to download.
