# ============================================================
# EII PIPELINE — CONFIGURATION TEMPLATE
# ============================================================
# Instructions:
#   1. Copy this file and rename it (e.g., config_local.py)
#   2. Edit the paths below to match your local data structure
#   3. In the notebook, import or paste your config values
#      into the configuration cell (Section 1)
#
# Do NOT commit your personal config file to the repository
# (it is already listed in .gitignore as config_local.py)
# ============================================================

# Root folder containing binary .tif rasters and the grid shapefile
DATA_FOLDER = r"path/to/your/raster/folder"

# Hexagonal grid shapefile (polygons — converted to perimeters internally)
GRID_SHAPEFILE = r"path/to/your/grid.shp"

# Checkpoint folder (created automatically if it does not exist)
CHECKPOINT_FOLDER = r"path/to/your/checkpoints"

# Consolidated output CSV
OUTPUT_CSV = r"path/to/your/output/eif_consolidated.csv"

# Nodata fallback value (used when raster metadata does not define nodata)
NODATA_FALLBACK = 255

# Pixel value representing natural vegetation in the binary rasters
VEGETATION_VALUE = 1

# Scenario label mapping: fragment of filename (lowercase) → scenario label
# First match wins; add or remove entries as needed
SCENARIO_MAP = {
    "obs":  "OBS",    # observed / baseline
    "tnc1": "TNC1",
    "tnc2": "TNC2",
    "bau":  "BAU",
    "gov":  "GOV",
}

# ---- Visualization settings (used in notebook Section 6) ----
VIZ_SCENARIO = "OBS"
VIZ_YEAR     = "2020"
VIZ_CSV_IN   = r"path/to/your/visualization_input.csv"
VIZ_OUT_DIR  = r"path/to/your/visualization_outputs"
```

**Passo 5.** Na mensagem de commit escreva:
```
Add configuration template with documented parameters
```

**Passo 6.** Clique em **"Commit changes"**

---

## Bloco 8 — Adicionar tópicos ao repositório

Isso ajuda o repositório a ser encontrado por outros pesquisadores no GitHub. É rápido.

**Passo 1.** Na página principal do repositório, clique no ícone de engrenagem ⚙️ ao lado de **"About"** (canto superior direito, acima dos arquivos)

**Passo 2.** No campo **"Topics"**, adicione um por vez:
```
landscape-ecology
cerrado
mapbiomas
remote-sensing
habitat-connectivity
python
geopandas
time-series
