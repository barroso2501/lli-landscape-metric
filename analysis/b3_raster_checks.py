"""
b3_raster_checks.py — Raster-based checks for the LLI audit (Block 3: A1, A7, A8, A12).

RUN THIS ON YOUR MACHINE: it needs the annual MapBiomas rasters and the HEX-20
shapefile, which are not in the repository. Edit ONLY the CONFIGURATION block.

Version 2 (2026-09-25): faster (vectorised sampling, one raster read per cell) and
RESUMABLE — results are saved every CHUNK cells; if the run is interrupted, running
the script again skips the cells (and years) already done.

What it does (one pass per cell and per selected year)
-------------------------------------------------------
  A7  Orientation diagnostic (shapefile only): for each of the six segments, the
      direction it is traversed in (the notebook's "angle") and the compass bearing
      of the side it FACES (from the cell centroid to the segment midpoint).

  A8  Two versions of the perimeter index:
        w_px  : pixel-count LLI exactly as the pipeline (rasterstats, all_touched=True).
                Validated automatically against the published eii CSV.
        w_len : length-weighted LLI: the boundary is sampled every SAMPLE_STEP_M
                metres, so every metre counts equally whatever its orientation.
      and per-segment versions of both.

  A1  Null model for delta: two concentric inner hexagons (scales 0.4 and 0.6; total
      length = perimeter). If the perimeter's delta beyond "own + neighbour cover" is
      similar to the rings', it is consistent with line-sampling error.

  A12 Valid-data coverage (share of non-255 pixels) of interior and perimeter.

Outputs (in OUTPUT_FOLDER)
--------------------------
  orientation_diagnostic.csv       one row per segment index (A7)
  cells_<year>.csv                 one row per cell with all metrics (final)
  partial_<year>.csv               progress file while a year is running (resume)
  raster_checks_summary.txt        the numbers to bring back into the audit

Runtime: about 0.05-0.1 s per cell (≈ 10-20 min per year), depending on disk.
Requirements: numpy, pandas, geopandas, shapely>=2, rasterio, pyproj, rasterstats.

What can break, and how you would notice
----------------------------------------
- PUBLISHED_EII_CSV not found -> the script stops at the start and tells you, so
  you do not wait an hour for an unvalidated run. Fix the path (or set
  REQUIRE_VALIDATION = False to run anyway).
- Raster for a year missing -> FileNotFoundError naming the file.
- Validation line "w_px vs published eii" should show max |diff| <= 0.001. A larger
  value means a different grid or raster version; stop and report it.
- If you change settings (e.g. SAMPLE_STEP_M) after a partial run, delete the
  partial_<year>.csv files first, otherwise old and new cells are mixed.
"""

# ============================ CONFIGURATION ======================================
RASTER_FOLDER = r"D:\EII_Landscape\raster_binario"
RASTER_PATTERN = "reclass_{year}.tif"                 # file name for each year
GRID_SHAPEFILE = r"D:\EII_Landscape\grids\hex_20000ha.shp"
# Published annual LLI matrix, used ONLY to validate w_px. It is the file
# data/eii_HEX20_annual.csv of the GitHub repository (download it) or the
# phase-2 output on your disk. Put its full path here:
PUBLISHED_EII_CSV = r"D:\EII_Landscape\phase2_annual\eii_HEX20_annual.csv"
REQUIRE_VALIDATION = True                             # stop at start if the CSV is missing
OUTPUT_FOLDER = r"D:\EII_Landscape\block3_raster_checks"
YEARS = [1986, 2023]                                  # each year is one full pass
NODATA = 255                                          # outside-domain value (never 0)
VEG = 1                                               # natural vegetation value
SAMPLE_STEP_M = 5.0                                   # boundary sampling step for w_len (m)
RING_SCALES = (0.4, 0.6)                              # inner rings; lengths sum to P
MIN_VALID_FRAC = 0.5                                  # coverage threshold (A12)
TAU = 0.5                                             # state threshold (Type I / II)
CHUNK = 250                                           # save progress every CHUNK cells
MAX_CELLS = None                                      # e.g. 200 for a quick trial
# =================================================================================

import os
import math
import time
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import LineString, Polygon
from shapely.ops import transform as shp_transform
from pyproj import Transformer
from rasterstats.io import Raster as RSRaster        # internal API, rasterstats >= 0.19
from rasterstats.utils import rasterize_geom

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
summary = []
say = lambda s="": (print(s, flush=True), summary.append(s))

# ---------------------------------------------------------------------------------
# Validation file: check BEFORE the long run
# ---------------------------------------------------------------------------------
published = None
if os.path.exists(PUBLISHED_EII_CSV):
    published = pd.read_csv(PUBLISHED_EII_CSV, encoding="utf-8-sig").set_index("ID_UNICO")
elif REQUIRE_VALIDATION:
    raise FileNotFoundError(
        f"Validation file not found: {PUBLISHED_EII_CSV}\n"
        "Set PUBLISHED_EII_CSV to the full path of eii_HEX20_annual.csv "
        "(or REQUIRE_VALIDATION = False to run without validation).")
else:
    say(f"WARNING: {PUBLISHED_EII_CSV} not found — validation SKIPPED.")

# ---------------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------------
grid = gpd.read_file(GRID_SHAPEFILE)
if "ID_UNICO" not in grid.columns:
    grid["ID_UNICO"] = grid.index.astype(int)
grid = grid.sort_values("ID_UNICO").reset_index(drop=True)
if MAX_CELLS:
    grid = grid.iloc[:MAX_CELLS].copy()
say(f"Grid: {len(grid)} cells | CRS: {grid.crs.name if grid.crs else None}")


def compass(dx, dy):
    """Compass bearing in degrees (0 = North, 90 = East) of vector (dx, dy)."""
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


def vertices(poly):
    """Exterior vertices (closed: first repeated at the end), in shapefile order."""
    return np.asarray(poly.exterior.coords)


# ---------------------------------------------------------------------------------
# A7 — orientation diagnostic (no raster needed)
# ---------------------------------------------------------------------------------
orient = []
for poly in grid.geometry:
    v = vertices(poly)
    cx, cy = poly.centroid.x, poly.centroid.y
    for k in range(len(v) - 1):
        (x0, y0), (x1, y1) = v[k], v[k + 1]
        trav = (math.degrees(math.atan2(y1 - y0, x1 - x0)) + 360) % 360   # math convention, as notebook
        orient.append({"seg_idx": k, "traversal_angle_math": round(trav) % 360,
                       "faces_bearing": round(compass((x0 + x1) / 2 - cx, (y0 + y1) / 2 - cy)) % 360})
orient = pd.DataFrame(orient)
tab = orient.groupby(["seg_idx", "traversal_angle_math", "faces_bearing"]).size().rename("n_cells").reset_index()
tab.to_csv(os.path.join(OUTPUT_FOLDER, "orientation_diagnostic.csv"), index=False)
say("\n[A7] Orientation diagnostic")
say(f"  vertices per cell: {grid.geometry.apply(lambda g: len(g.exterior.coords) - 1).value_counts().to_dict()} "
    f"| rings counter-clockwise: {grid.geometry.apply(lambda g: g.exterior.is_ccw).mean():.0%}")
for _, r in tab.iterrows():
    say(f"    seg {r.seg_idx} (w{r.seg_idx + 1}): traversal {r.traversal_angle_math:3d}°  "
        f"faces {r.faces_bearing:3d}°  (n={r.n_cells})")

# ---------------------------------------------------------------------------------
# Neighbours (queen contiguity from the shapefile) for the A1 comparison
# ---------------------------------------------------------------------------------
sidx = grid.sindex
nbrs = [np.array([j for j in sidx.query(p, predicate="touches") if j != i]) for i, p in enumerate(grid.geometry)]


def nbr_mean(x):
    return np.array([np.nanmean(x[nb]) if len(nb) else np.nan for nb in nbrs])


# ---------------------------------------------------------------------------------
# Per-cell computation
# ---------------------------------------------------------------------------------
def edge_points(v, step):
    """Points every `step` metres along each straight edge of a closed vertex array.
    Returns (points, edge index of each point). Vectorised: no per-point Python loop."""
    pts, idx = [], []
    for k in range(len(v) - 1):
        L = np.hypot(*(v[k + 1] - v[k]))
        m = max(1, int(round(L / step)))
        f = (np.arange(m) + 0.5) / m                       # midpoints of m equal pieces
        pts.append(v[k] + f[:, None] * (v[k + 1] - v[k]))
        idx.append(np.full(m, k))
    return np.vstack(pts), np.concatenate(idx)


def sample(pts_r, arr, wt):
    """Raster values at points given in RASTER CRS (255 outside the window)."""
    cols, rows = (~wt) * (pts_r[:, 0], pts_r[:, 1])
    rows, cols = np.floor(rows).astype(int), np.floor(cols).astype(int)
    ok = (rows >= 0) & (rows < arr.shape[0]) & (cols >= 0) & (cols < arr.shape[1])
    out = np.full(len(pts_r), NODATA, dtype=arr.dtype)
    out[ok] = arr[rows[ok], cols[ok]]
    return out


def cover(vals):
    """Share of valid values that are vegetation."""
    valid = vals != NODATA
    return (vals[valid] == VEG).mean() if valid.any() else np.nan


def process_cell(row, rs, to_r):
    poly = row.geometry
    v = vertices(poly)
    # geometries grid CRS -> raster CRS, vertex-only (as GeoDataFrame.to_crs in the pipeline)
    vr = np.column_stack(to_r(v[:, 0], v[:, 1]))
    bline = LineString(vr)

    # ONE raster read per cell: window = bbox of the boundary (exactly what zonal_stats
    # reads for the perimeter), which also contains the interior and the rings.
    fs = rs.read(bounds=bline.bounds)
    arr, wt = fs.array, fs.affine
    if isinstance(arr, np.ma.MaskedArray):
        arr = arr.filled(NODATA)
    valid, veg = arr != NODATA, arr == VEG

    # Area (all_touched=False on the polygon, as in the pipeline)
    inside = geometry_mask([Polygon(vr)], arr.shape, wt, invert=True, all_touched=False)
    n_in, n_in_valid = inside.sum(), (inside & valid).sum()
    A = (inside & veg).sum() / n_in_valid if n_in_valid else np.nan

    # w_px: pixel count on the boundary (all_touched=True), identical to zonal_stats
    touched = rasterize_geom(bline, like=fs, all_touched=True)
    n_b, n_b_valid = touched.sum(), (touched & valid).sum()
    w_px = (touched & veg).sum() / n_b_valid if n_b_valid else np.nan

    rec = {"ID_UNICO": row.ID_UNICO, "area": A, "w_px": w_px,
           "valid_frac_interior": n_in_valid / n_in if n_in else np.nan,
           "valid_frac_perimeter": n_b_valid / n_b if n_b else np.nan}

    # Per-segment pixel count, using the same window (the segment notebook read a
    # window per segment; results differ only when an edge lies exactly on a pixel border)
    seg_px = []
    for k in range(len(vr) - 1):
        m = rasterize_geom(LineString(vr[k:k + 2]), like=fs, all_touched=True)
        nv = (m & valid).sum()
        seg_px.append((m & veg).sum() / nv if nv else np.nan)
        rec[f"w_px_seg{k}"] = seg_px[-1]

    # Length-weighted perimeter and per-segment values (sampling in metres, grid CRS)
    p, e = edge_points(v, SAMPLE_STEP_M)
    vals = sample(np.column_stack(to_r(p[:, 0], p[:, 1])), arr, wt)
    rec["w_len"] = cover(vals)
    seg_len = [cover(vals[e == k]) for k in range(len(v) - 1)]
    for k, c in enumerate(seg_len):
        rec[f"w_len_seg{k}"] = c
    rec["w_px_segmean"] = np.nanmean(seg_px)
    rec["w_len_segmean"] = np.nanmean(seg_len)

    # A1 null: concentric inner hexagons, total length = perimeter
    c = np.array([poly.centroid.x, poly.centroid.y])
    ring_vals = []
    for s in RING_SCALES:
        pr, _ = edge_points(c + s * (v - c), SAMPLE_STEP_M)
        ring_vals.append(sample(np.column_stack(to_r(pr[:, 0], pr[:, 1])), arr, wt))
    rec["w_ring"] = cover(np.concatenate(ring_vals))
    return rec


def process_year(year):
    final = os.path.join(OUTPUT_FOLDER, f"cells_{year}.csv")
    if os.path.exists(final) and len(pd.read_csv(final)) == len(grid):
        say(f"\n{year}: already complete — loading {final}")
        return pd.read_csv(final)
    path = os.path.join(RASTER_FOLDER, RASTER_PATTERN.format(year=year))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Raster for {year} not found: {path}")

    partial = os.path.join(OUTPUT_FOLDER, f"partial_{year}.csv")
    done = set(pd.read_csv(partial).ID_UNICO) if os.path.exists(partial) else set()
    todo = grid[~grid.ID_UNICO.isin(done)]
    print(f"\n{year}: {len(done)} cells already done, {len(todo)} to go", flush=True)

    buf, t0 = [], time.time()
    with RSRaster(path, nodata=NODATA) as rs, rasterio.open(path) as src:
        if not summary or "Raster CRS" not in " ".join(summary):
            say(f"Raster CRS: {src.crs} | pixel size: {src.res}")
        to_r = Transformer.from_crs(grid.crs, src.crs, always_xy=True).transform
        for n, (_, row) in enumerate(todo.iterrows(), 1):
            buf.append(process_cell(row, rs, to_r))
            if len(buf) >= CHUNK or n == len(todo):
                pd.DataFrame(buf).round(5).to_csv(partial, mode="a", index=False,
                                                  header=not os.path.exists(partial))
                buf = []
                rate = (time.time() - t0) / n
                print(f"  {year}: {len(done) + n}/{len(grid)} cells | {rate:.3f} s/cell | "
                      f"~{rate * (len(todo) - n) / 60:.0f} min left (saved)", flush=True)
    df = pd.read_csv(partial).drop_duplicates("ID_UNICO").set_index("ID_UNICO").loc[grid.ID_UNICO].reset_index()
    df.to_csv(final, index=False)
    os.remove(partial)
    return df


def ols(y, X):
    """OLS with intercept on finite rows: (coefficients, R², residual SD)."""
    M = np.column_stack([y] + X)
    M = M[np.isfinite(M).all(axis=1)]
    y_, X_ = M[:, 0], np.column_stack([np.ones(len(M)), M[:, 1:]])
    beta, *_ = np.linalg.lstsq(X_, y_, rcond=None)
    res = y_ - X_ @ beta
    return beta, 1 - res.var() / y_.var(), res.std()


for year in YEARS:
    df = process_year(year)
    A = df.area.values
    say(f"\n===== {year} =====")
    col = f"eii_OBS_{year}"
    if published is not None and col in published.columns:
        dif = np.abs(df.w_px.values - published.loc[df.ID_UNICO, col].values)
        say(f"  Validation w_px vs published eii: max |diff| {np.nanmax(dif):.4f}, mean {np.nanmean(dif):.5f}")
    say("  [A8] Weighting")
    say(f"    w_px - w_len: mean {np.nanmean(df.w_px - df.w_len):+.4f}, SD {np.nanstd(df.w_px - df.w_len):.4f}, "
        f"max |.| {np.nanmax(np.abs(df.w_px - df.w_len)):.4f}")
    say(f"    full-perimeter w_px - mean of 6 segment w_px: mean {np.nanmean(df.w_px - df.w_px_segmean):+.4f}")
    say(f"    full-perimeter w_len - mean of 6 segment w_len: mean {np.nanmean(df.w_len - df.w_len_segmean):+.4f} "
        "(~0 means length-weighting removes the offset)")
    low = (df.valid_frac_interior < MIN_VALID_FRAC) | (df.valid_frac_perimeter < MIN_VALID_FRAC)
    say(f"  [A12] Cells with valid fraction < {MIN_VALID_FRAC:.0%} (interior or perimeter): {int(low.sum())}; "
        f"IDs: {df.ID_UNICO[low].tolist()[:40]}{' ...' if low.sum() > 40 else ''}")
    say("  [A1] Null model: perimeter vs inner rings of equal total length")
    nA = nbr_mean(A)
    for name, wv in (("perimeter w_px", df.w_px.values), ("perimeter w_len", df.w_len.values),
                     ("inner rings", df.w_ring.values)):
        d = wv - A
        (b0, b_own, b_nbr), r2, sd_res = ols(wv, [A, nA])
        say(f"    {name:<16}: SD(delta) {np.nanstd(d):.4f}; |delta|>0.10 {np.nanmean(np.abs(d) > 0.10):.1%}; "
            f"w ~ own Area {b_own:.3f} + nbr Area {b_nbr:.3f} (R² {r2:.3f}); residual SD {sd_res:.4f}")
    div_p = (A >= TAU) != (df.w_px.values >= TAU)
    div_r = (A >= TAU) != (df.w_ring.values >= TAU)
    say(f"    Type I+II share: perimeter {np.nanmean(div_p):.1%} vs inner rings {np.nanmean(div_r):.1%}")

open(os.path.join(OUTPUT_FOLDER, "raster_checks_summary.txt"), "w", encoding="utf-8").write("\n".join(summary) + "\n")
print(f"\nDone. Send back: {os.path.join(OUTPUT_FOLDER, 'raster_checks_summary.txt')} and orientation_diagnostic.csv")
