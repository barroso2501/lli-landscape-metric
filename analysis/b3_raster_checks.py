"""
b3_raster_checks.py — Raster-based checks for the LLI audit (Block 3: A1, A7, A8, A12).

RUN THIS ON YOUR MACHINE: it needs the annual MapBiomas rasters and the HEX-20
shapefile, which are not in the repository. Edit ONLY the CONFIGURATION block.

What it does (one pass per cell and per selected year)
-------------------------------------------------------
Each cell is processed from a small raster window around it, so the whole
1,500 x 1,500 km raster never has to fit in memory.

  A7  Orientation diagnostic (shapefile only, no raster): for each of the six
      segments, the direction it is traversed in (what the segment notebook
      calls its "angle") and the compass bearing of the side it FACES (outward
      normal, from the cell centroid to the segment midpoint).
      -> tells whether grad_EW / grad_NESW / grad_NWSE are correctly named.

  A8  Two versions of the perimeter index:
        w_px  : pixel-count LLI, as in the pipeline (all_touched=True).
                Must reproduce data/eii_HEX20_annual.csv; this is checked
                automatically (validation line in the summary).
        w_len : length-weighted LLI, sampling the boundary every SAMPLE_STEP_M
                metres, so every metre of boundary counts equally whatever its
                orientation.
      and the same two versions per segment, to separate the vertex double-count
      explanation from the orientation-weighting explanation.

  A1  Null model for delta. The perimeter is one particular line of length P.
      If delta = w - A were mostly line-sampling error, any other line of the
      same length inside the cell would give a similar delta. Two concentric
      hexagons scaled 0.4 and 0.6 about the centroid have total length
      0.4P + 0.6P = P; w_ring is their length-weighted cover.
      For each line, w is regressed on own Area and mean neighbour Area. The
      perimeter is expected to load on neighbour Area by geometry alone (it lies
      between cells); the rings should not. What the perimeter carries beyond
      "own + neighbour cover" is its residual; comparing that residual with the
      rings' residual indicates how much of it is line-sampling error.

  A12 Valid-data coverage of each cell (interior and perimeter): share of
      pixels that are not 255. Cells below MIN_VALID_FRAC are flagged.

Outputs (in OUTPUT_FOLDER)
--------------------------
  orientation_diagnostic.csv        one row per segment index (A7)
  cells_<year>.csv                  one row per cell with all metrics
  raster_checks_summary.txt         the numbers to bring back into the audit

Runtime: roughly 5-15 min per year for 11,500 cells (depends on disk speed).
Requirements: numpy, pandas, geopandas, shapely>=2, rasterio, pyproj, rasterstats.

What can break, and how you would notice
----------------------------------------
- Raster file not found for a year -> FileNotFoundError naming the year; check
  RASTER_PATTERN.
- Grid and raster in different CRS -> handled (geometries are transformed); the
  summary prints both CRS. If the raster is geographic (EPSG:4326), w_px will
  still match the pipeline, but pixel sizes vary with latitude; w_len is exact
  in metres.
- The validation line "w_px vs published eii" should show max |difference|
  close to 0 (<= 0.001). A larger value means the emulation differs from the
  pipeline (e.g. different grid file or raster version); stop and report it.
"""

# ============================ CONFIGURATION ======================================
RASTER_FOLDER = r"D:\Modelo_LAPIG\rasters_binarios"
RASTER_PATTERN = "reclass_{year}.tif"          # file name for each year
GRID_SHAPEFILE = r"D:\Modelo_LAPIG\grids\hex_20000ha.shp"
PUBLISHED_EII_CSV = r"D:\Modelo_LAPIG\phase2_annual\eii_HEX20_annual.csv"   # used only for validation
OUTPUT_FOLDER = r"D:\Modelo_LAPIG\block3_raster_checks"
YEARS = [1986, 2004, 2023]                     # keep short: each year is one full pass
NODATA = 255                                   # outside-domain value (never 0)
VEG = 1                                        # natural vegetation value
SAMPLE_STEP_M = 5.0                            # boundary sampling step for w_len (metres)
RING_SCALES = (0.4, 0.6)                       # inner rings; their lengths sum to P
MIN_VALID_FRAC = 0.5                           # coverage threshold for flagging (A12)
TAU = 0.5                                      # state threshold (Type I / II)
MAX_CELLS = None                               # set e.g. 200 for a quick trial run
# =================================================================================

import os
import math
import time
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
from shapely.geometry import LineString, Polygon
from shapely import affinity
from shapely.ops import transform as shp_transform
from pyproj import Transformer
from rasterstats.io import Raster as RSRaster   # internal API, rasterstats >= 0.19
from rasterstats.utils import rasterize_geom

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
summary = []
say = lambda s="": (print(s), summary.append(s))

# ---------------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------------
grid = gpd.read_file(GRID_SHAPEFILE)
if "ID_UNICO" not in grid.columns:
    grid["ID_UNICO"] = grid.index.astype(int)
grid = grid.sort_values("ID_UNICO").reset_index(drop=True)
if MAX_CELLS:
    grid = grid.iloc[:MAX_CELLS].copy()
say(f"Grid: {len(grid)} cells | CRS: {grid.crs}")


def compass(dx, dy):
    """Compass bearing in degrees (0 = North, 90 = East) of vector (dx, dy)."""
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


def segments_of(poly):
    """The six boundary segments, in the vertex order the segment notebook uses."""
    c = list(poly.exterior.coords)
    return [LineString([c[k], c[k + 1]]) for k in range(len(c) - 1)]


# ---------------------------------------------------------------------------------
# A7 — orientation diagnostic (no raster needed)
# ---------------------------------------------------------------------------------
orient = []
n_vertices = grid.geometry.apply(lambda g: len(g.exterior.coords) - 1)
ccw = grid.geometry.apply(lambda g: g.exterior.is_ccw)
for poly in grid.geometry:
    cx, cy = poly.centroid.x, poly.centroid.y
    for k, seg in enumerate(segments_of(poly)[:6]):
        (x0, y0), (x1, y1) = seg.coords
        trav = (math.degrees(math.atan2(y1 - y0, x1 - x0)) + 360) % 360   # math convention, as in notebook
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        orient.append({"seg_idx": k, "traversal_angle_math": round(trav) % 360,
                       "faces_bearing": round(compass(mx - cx, my - cy)) % 360})
orient = pd.DataFrame(orient)
tab = (orient.groupby(["seg_idx", "traversal_angle_math", "faces_bearing"]).size()
       .rename("n_cells").reset_index())
tab.to_csv(os.path.join(OUTPUT_FOLDER, "orientation_diagnostic.csv"), index=False)
say("\n[A7] Orientation diagnostic")
say(f"  vertices per cell: {n_vertices.value_counts().to_dict()} | rings counter-clockwise: {ccw.mean():.0%}")
say("  seg_idx -> traversal angle (math, as in notebook) -> side it FACES (compass bearing), n cells:")
for _, r in tab.iterrows():
    say(f"    seg {r.seg_idx}: traversal {r.traversal_angle_math:3d}°  faces {r.faces_bearing:3d}°  (n={r.n_cells})")
say("  Notebook assumes seg1..seg6 = 240,180,120,60,0,300 and names grad_EW = seg(0°) - seg(180°).")
say("  If the segment with traversal 0° FACES ~0° (North), grad_EW is actually a North-South gradient.")

# ---------------------------------------------------------------------------------
# Neighbours (queen contiguity from the shapefile) for the A1 comparison
# ---------------------------------------------------------------------------------
sidx = grid.sindex
nbrs = []
for i, poly in enumerate(grid.geometry):
    cand = sidx.query(poly, predicate="touches")
    nbrs.append(np.array([j for j in cand if j != i]))


def nbr_mean(x):
    return np.array([np.nanmean(x[nb]) if len(nb) else np.nan for nb in nbrs])


# ---------------------------------------------------------------------------------
# Per-cell computation
# ---------------------------------------------------------------------------------
def dense_points(line, step):
    """Points every `step` metres along a line (segment midpoints of equal length)."""
    L = line.length
    m = max(1, int(round(L / step)))
    d = (np.arange(m) + 0.5) * L / m
    return np.array([line.interpolate(x).coords[0] for x in d])


def cover_from_points(pts, arr, win_transform):
    """Share of valid samples that fall on vegetation, given points in RASTER CRS."""
    inv = ~win_transform
    cols, rows = inv * (pts[:, 0], pts[:, 1])
    rows = np.floor(rows).astype(int)
    cols = np.floor(cols).astype(int)
    inside = (rows >= 0) & (rows < arr.shape[0]) & (cols >= 0) & (cols < arr.shape[1])
    v = np.full(len(pts), NODATA, dtype=arr.dtype)
    v[inside] = arr[rows[inside], cols[inside]]
    valid = v != NODATA
    return (v[valid] == VEG).mean() if valid.any() else np.nan, valid.mean()


def pixel_count_cover(rs, line):
    """Pixel-count cover of a line, replicating rasterstats.zonal_stats(all_touched=True).
    Returns (cover, n touched pixels, n valid touched pixels)."""
    fs = rs.read(bounds=line.bounds)                      # window = geometry bbox, as zonal_stats
    if 0 in fs.array.shape:                               # line exactly on a pixel border: empty window
        return np.nan, 0, 0
    m = rasterize_geom(line, like=fs, all_touched=True)
    v = fs.array[m]
    nv = (v != NODATA).sum()
    return ((v == VEG).sum() / nv if nv else np.nan), m.sum(), nv


def process_year(year):
    path = os.path.join(RASTER_FOLDER, RASTER_PATTERN.format(year=year))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Raster for {year} not found: {path}")
    out = []
    t0 = time.time()
    # rasterstats' own reader is used for the pixel-count metrics, so the emulation is
    # exact: it reads a window clipped to each geometry's bounding box, which drops
    # pixels touched just outside that box (matters when an edge lies on a pixel border).
    with rasterio.open(path) as src, RSRaster(path, nodata=NODATA) as rs:
        if year == YEARS[0]:
            say(f"\nRaster CRS: {src.crs} | pixel size: {src.res}")
        to_r = Transformer.from_crs(grid.crs, src.crs, always_xy=True).transform
        for i, row in grid.iterrows():
            poly = row.geometry
            # geometries in grid CRS (metres) -> raster CRS
            # vertex-only transform, exactly as the pipeline (GeoDataFrame.to_crs); no densification
            poly_r = shp_transform(to_r, poly)
            minx, miny, maxx, maxy = poly_r.buffer(abs(src.res[0]) * 3).bounds
            win = from_bounds(minx, miny, maxx, maxy, src.transform).round_offsets().round_lengths()
            arr = src.read(1, window=win, boundless=True, fill_value=NODATA)
            wt = src.window_transform(win)
            valid = arr != NODATA
            veg = arr == VEG

            # Area (all_touched=False, as in the pipeline)
            inside = geometry_mask([poly_r], arr.shape, wt, invert=True, all_touched=False)
            n_in, n_in_valid = inside.sum(), (inside & valid).sum()
            A = (inside & veg).sum() / n_in_valid if n_in_valid else np.nan

            # w_px: pixel-count on the boundary line (all_touched=True), exactly as zonal_stats
            bline = LineString(shp_transform(to_r, poly.exterior).coords)   # plain line, as .boundary
            w_px, n_b, n_b_valid = pixel_count_cover(rs, bline)

            # w_len and per-segment values: dense points in grid CRS -> raster CRS
            rec = {"ID_UNICO": row.ID_UNICO, "area": A, "w_px": w_px,
                   "valid_frac_interior": n_in_valid / n_in if n_in else np.nan,
                   "valid_frac_perimeter": n_b_valid / n_b if n_b else np.nan}
            seg_len, seg_px = [], []
            all_pts = []
            for k, seg in enumerate(segments_of(poly)[:6]):
                p = dense_points(seg, SAMPLE_STEP_M)
                all_pts.append(p)
                pr = np.column_stack(to_r(p[:, 0], p[:, 1]))
                c, _ = cover_from_points(pr, arr, wt)
                seg_len.append(c)
                sr = shp_transform(to_r, seg)                                  # segment in raster CRS
                seg_px.append(pixel_count_cover(rs, sr)[0])                    # as the segment notebook
                rec[f"w_len_seg{k}"] = c
                rec[f"w_px_seg{k}"] = seg_px[-1]
            P = np.vstack(all_pts)
            rec["w_len"], _ = cover_from_points(np.column_stack(to_r(P[:, 0], P[:, 1])), arr, wt)
            rec["w_px_segmean"] = np.nanmean(seg_px)
            rec["w_len_segmean"] = np.nanmean(seg_len)

            # A1 null: concentric rings of total length P (length-weighted cover)
            ring_pts = []
            for s in RING_SCALES:
                ring = affinity.scale(poly.exterior, xfact=s, yfact=s, origin=poly.centroid)
                ring_pts.append(dense_points(ring, SAMPLE_STEP_M))
            R = np.vstack(ring_pts)
            rec["w_ring"], _ = cover_from_points(np.column_stack(to_r(R[:, 0], R[:, 1])), arr, wt)
            out.append(rec)
            if (i + 1) % 1000 == 0:
                print(f"  {year}: {i + 1}/{len(grid)} cells ({time.time() - t0:.0f}s)")
    df = pd.DataFrame(out)
    df.round(5).to_csv(os.path.join(OUTPUT_FOLDER, f"cells_{year}.csv"), index=False)
    return df


def ols(y, X):
    """OLS with intercept on finite rows: (coefficients, R², residual SD)."""
    M = np.column_stack([y] + X)
    M = M[np.isfinite(M).all(axis=1)]
    y_, X_ = M[:, 0], np.column_stack([np.ones(len(M)), M[:, 1:]])
    beta, *_ = np.linalg.lstsq(X_, y_, rcond=None)
    res = y_ - X_ @ beta
    return beta, 1 - res.var() / y_.var(), res.std()


published = None
if os.path.exists(PUBLISHED_EII_CSV):
    published = pd.read_csv(PUBLISHED_EII_CSV, encoding="utf-8-sig").set_index("ID_UNICO")
else:
    say(f"WARNING: {PUBLISHED_EII_CSV} not found — validation against the pipeline will be SKIPPED.")

for year in YEARS:
    df = process_year(year)
    A = df.area.values
    say(f"\n===== {year} =====")
    # validation against the pipeline
    col = f"eii_OBS_{year}"
    if published is not None and col in published.columns:
        pub = published.loc[df.ID_UNICO, col].values
        dif = np.abs(df.w_px.values - pub)
        say(f"  Validation w_px vs published eii: max |diff| {np.nanmax(dif):.4f}, mean {np.nanmean(dif):.5f}")
    # A8 — weighting
    say("  [A8] Weighting")
    say(f"    w_px - w_len: mean {np.nanmean(df.w_px - df.w_len):+.4f}, SD {np.nanstd(df.w_px - df.w_len):.4f}, "
        f"max |.| {np.nanmax(np.abs(df.w_px - df.w_len)):.4f}")
    say(f"    full-perimeter w_px - mean of 6 segment w_px: mean {np.nanmean(df.w_px - df.w_px_segmean):+.4f}")
    say(f"    full-perimeter w_len - mean of 6 segment w_len: mean {np.nanmean(df.w_len - df.w_len_segmean):+.4f} "
        "(~0 means length-weighting removes the offset)")
    # A12 — coverage
    low = (df.valid_frac_interior < MIN_VALID_FRAC) | (df.valid_frac_perimeter < MIN_VALID_FRAC)
    say(f"  [A12] Cells with valid fraction < {MIN_VALID_FRAC:.0%} (interior or perimeter): {int(low.sum())} "
        f"-> IDs listed in cells_{year}.csv (columns valid_frac_*)")
    # A1 — null model
    say("  [A1] Null model: perimeter vs inner rings of equal total length")
    nA = nbr_mean(A)
    for name, wv in (("perimeter w_px", df.w_px.values), ("perimeter w_len", df.w_len.values),
                     ("inner rings", df.w_ring.values)):
        d = wv - A
        (b0, b_own, b_nbr), r2, sd_res = ols(wv, [A, nA])
        say(f"    {name:<16}: SD(delta) {np.nanstd(d):.4f}; |delta|>0.10 {np.nanmean(np.abs(d) > 0.10):.1%}; "
            f"w ~ own Area {b_own:.3f} + nbr Area {b_nbr:.3f} (R² {r2:.3f}); residual SD {sd_res:.4f}")
    say("    Reading: the perimeter sits between cells, so a weight on neighbour Area is expected")
    say("    from geometry alone, in any landscape. The rings (inside the cell) should show a weight")
    say("    near 0. Information beyond 'own + neighbour cover' is what remains in the residual:")
    say("    if the perimeter residual SD is close to the ring residual SD, the remaining delta is")
    say("    consistent with line-sampling error.")
    div_p = (A >= TAU) != (df.w_px.values >= TAU)
    div_r = (A >= TAU) != (df.w_ring.values >= TAU)
    say(f"    Type I+II share: perimeter {np.nanmean(div_p):.1%} vs inner rings {np.nanmean(div_r):.1%}")

open(os.path.join(OUTPUT_FOLDER, "raster_checks_summary.txt"), "w", encoding="utf-8").write("\n".join(summary) + "\n")
print(f"\nDone. Send back: {os.path.join(OUTPUT_FOLDER, 'raster_checks_summary.txt')} and orientation_diagnostic.csv")
