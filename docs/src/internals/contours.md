# Contours and DEM

## Contour lines (`contours.py`)

With `--contours`, garmap runs pyhgtmap over the same `corridor.poly`. pyhgtmap
downloads elevation tiles, traces contour lines and writes them as OSM data, which
mkgmap then compiles like any other input.

```text
--polygon=<work>/corridor.poly
--step=10
--line-cat=100,50
--sources=view1,view3
--hgtdir=~/.cache/garmap/hgt
--simplifyContoursEpsilon=1e-05
--pbf
--start-node-id=20000000000
--start-way-id=20000000000
--jobs=<cpu count>
```

| Choice | Reason given in the code |
|---|---|
| `view1,view3` (Viewfinder Panoramas) | needs no account, covers the whole world, fills the voids and the >60° N gap in SRTM. NASA sources need an EarthExplorer login. |
| `--line-cat=100,50` | tags each line as major (every 100 m), medium (every 50 m) or minor. garmap's contour style rules key on those tags. |
| `--simplifyContoursEpsilon=1e-05` | roughly halves the node count with no visible difference, which keeps the image small |
| ids starting at 20,000,000,000 | far above real OSM ids, so contour elements cannot collide with map data |

pyhgtmap is found either as a console script or as `python -m pyhgtmap`. All options
above were checked against pyhgtmap 4.1's `--help`.

Contour tiles are not passed through splitter. pyhgtmap tiles its own output, and
`mkgmap._args_file` gives each contour tile an id from the `63250001` range.

### How contours are drawn

Three pieces cooperate:

1. pyhgtmap tags lines `contour=elevation` with `contour_ext=elevation_minor`,
   `_medium` or `_major`.
2. The patched style file `inc/contour_lines` maps those to Garmin line types `0x20`,
   `0x21`, `0x22` at resolutions 23, 21 and 20, and labels them with `${ele}`, in metres.
   mkgmap's shipped version converts to feet.
3. The TYP file draws the three types in increasingly dark browns. Minor lines have
   no label.

So when zoomed out, only major contours are drawn. Zooming in adds medium, then
minor.

## DEM / shaded relief

`--dem` adds `--dem=<hgt cache> --dem-dists=3312,13248` to the mkgmap command. mkgmap
then embeds a digital elevation model, which gives the device shaded relief and
elevation readouts away from the route.

`--dem` requires `--contours`, because the contour step is what downloads the HGT
tiles.

Two problems are covered in the review:

- the directory handed to mkgmap is one level above where pyhgtmap stores the tiles
  ([H3](../review/findings.md#h3---dem-points-mkgmap-at-the-wrong-directory-level));
- `--dem` without `--contours` is rejected only after the download and split have
  finished ([M4](../review/findings.md#m4---dem-without---contours-fails-late)).
