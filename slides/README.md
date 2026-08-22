# garmap slides

A ~20 minute [Slidev](https://sli.dev/) deck: beginner-friendly introduction to why you'd
build your own Garmin map, then a full user guide, then an optional appendix on how it works
underneath.

## Running it

```console
$ cd slides
$ npm install
$ npm run dev        # opens http://localhost:3030
```

Navigate with arrow keys or space. Press <kbd>o</kbd> for the slide overview, <kbd>d</kbd> to
toggle dark mode, and open <http://localhost:3030/presenter> for presenter view — every
content slide has speaker notes, so the deck can be delivered by someone who didn't write it.

## Sharing it

```console
$ npm run build      # static site in dist/, deployable anywhere
$ npm run export     # slides.pdf (downloads a headless Chromium the first time)
```

## Layout

| Path | What it is |
|---|---|
| `slides.md` | the deck |
| `components/Terminal.vue` | framed terminal window for shell transcripts |
| `components/Pipeline.vue` | the six-stage build pipeline, with optional per-stage highlight |
| `components/Corridor.vue` | inline SVG of route, corridor and OSM extracts |

## Keeping it honest

Every transcript in the deck is **real captured output**, and the size figures are measured,
not estimated:

| Quoted | Source |
|---|---|
| `doctor`, `cache list`, `preview`, `build`, `install` output | run against `tests/fixtures/short-route.gpx` |
| buffer → corridor → size table | three real builds at 2 km / 6 km / 15 km |
| flag names, defaults, help text | `src/garmap/cli.py` |
| the manual install steps | `device.manual_instructions()` in `src/garmap/device.py` |

If you change the CLI surface, re-run the commands and update the deck. The install
instructions in particular are quoted verbatim from `device.py` and must not drift from what
the tool actually prints.
