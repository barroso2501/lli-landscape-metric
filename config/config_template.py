# ============================================================
# LLI PIPELINE — CONFIGURATION TEMPLATE
# ============================================================
# Reference values for the configuration cell (Section 1) of each notebook.
#
# How to use:
#   1. Copy this file to config/config_local.py (ignored by git).
#   2. Edit the paths below to match your local data structure.
#   3. Paste the values into the configuration cell of each notebook.
#      The notebooks do not import this file automatically.
#
# Naming note: data files and columns still use the legacy prefix "eii_"
# (Edge Interception Index, the metric's former name). "eii" == LLI.
# ============================================================

# ---- Inputs -------------------------------------------------

# Folder with ALL annual binary rasters (.tif), named e.g. reclass_YYYY.tif.
# Encoding: 1 = natural vegetation, 0 = non-natural, 255 = outside domain.
RASTER_FOLDER = r"path/to/rasters_binarios"

# Primary grid (HEX-20, 20,000 ha regular hexagons, ESRI:102033).
GRID_SHAPEFILE = r"path/to/grids/hex_20000ha.shp"

# Folder with the named sensitivity grids (HEX-10, HEX-20, HEX-40, SQ-20)
# and folder with the 25 jitter realizations (Phase 1 / RQ3).
GRID_FOLDER = r"path/to/grids"
JITTER_FOLDER = r"path/to/jitter_grids"

# ---- Outputs ------------------------------------------------

# Checkpoint folder: one CSV per raster; allows safe interruption/resumption.
CHECKPOINT_FOLDER = r"path/to/phase2_annual/checkpoints"

# Consolidated outputs of the annual pipeline (phase2_annual_pipeline).
EII_CSV_OUT = r"path/to/phase2_annual/eii_HEX20_annual.csv"       # LLI matrix
AREA_CSV_OUT = r"path/to/phase2_annual/area_HEX20_annual.csv"     # Area matrix
PAIRED_CSV_OUT = r"path/to/phase2_annual/eii_area_HEX20_annual.csv"

# ---- Raster encoding ----------------------------------------

# Nodata is HARDCODED to 255 in the analysis notebooks. MapBiomas binary
# rasters declare nodata=0 in their metadata, but 0 = non-natural cover,
# a valid value that must stay in the denominator. Do not read nodata
# from the raster metadata.
NODATA = 255

# Pixel value representing natural vegetation.
VEGETATION_VALUE = 1

# ---- Scenario labels ----------------------------------------

# Lowercase filename fragment -> scenario label. First match wins,
# so put more specific fragments first.
SCENARIO_MAP = {
    "reclass": "OBS",   # observed MapBiomas series (reclass_YYYY.tif)
    "obs":     "OBS",
    "tnc1":    "TNC1",
    "tnc2":    "TNC2",
    "bau":     "BAU",
    "gov":     "GOV",
}

# ---- Analysis period ----------------------------------------

# 1985 and 2024 are excluded from analyses because of truncated temporal
# filters at the ends of the MapBiomas series.
YEAR_START = 1986
YEAR_END = 2023
