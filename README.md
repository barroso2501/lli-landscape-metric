# Edge Interception Index (EII)
### A systematic transect-based metric for landscape interface connectivity

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Active Development](https://img.shields.io/badge/Status-Active%20Development-blue)]()

---

## Overview

The **Edge Interception Index (EII)** is a landscape connectivity metric derived from 
the borders of a regular hexagonal grid applied to binary habitat rasters. Each cell 
border is treated as a systematic linear transect — analogous to the line intercept 
method in vegetation ecology (Canfield 1941) — and the proportion of the perimeter 
that intersects natural habitat defines the EII.

This approach measures **interface connectivity**: how permeable the contact between 
adjacent landscape units is, rather than how much habitat exists within each unit.

**Study area:** Brazilian Cerrado  
**Input data:** MapBiomas binary rasters (natural vegetation vs. non-natural), 30 m resolution  
**Temporal coverage:** 1985–2024 (annual)  
**Spatial units:** Hexagonal grid (~19,183 cells)

---

## Conceptual basis

For each cell *i* at time *t*, two metrics are computed:

**Within-cell area** — proportion of natural habitat pixels inside the cell:

$$A_i(t) = \frac{\text{natural pixels inside cell } i}{\text{total valid pixels inside cell } i}$$

**Edge Interception Index** — proportion of the cell perimeter intercepting natural habitat:

$$w_i(t) = \frac{L_i^{\text{nat}}(t)}{P_i^{\text{obs}}(t)}$$

where $L_i^{\text{nat}}$ is the perimeter length intersecting natural habitat and 
$P_i^{\text{obs}}$ is the total observable perimeter (excluding nodata pixels).

Both metrics range from 0 to 1. Their **joint distribution** (Area × EII) reveals 
landscape states that area-based metrics alone cannot detect — particularly decoupling 
states where interior habitat and interface connectivity diverge.

---

## Repository structure
```
eii-landscape-metric/
├── notebooks/
│   └── continuidade_refatorado.ipynb   # Main EII extraction pipeline
├── data/
│   └── indices_bordas_EIF_consolidado.csv  # Consolidated EII dataset (OBS 1985–2020)
├── docs/
│   ├── paper_outline_EII.md            # Full paper outline
│   └── analysis_roadmap_EII.md         # Ordered analysis plan with dependencies
├── config/
│   └── config_template.py              # Configuration template (edit before running)
├── .gitignore
├── LICENSE
└── README.md
```

---

## Getting started

### Requirements
```
Python >= 3.10
rasterstats
geopandas
rasterio
pandas
numpy
matplotlib
```

Install all dependencies:
```bash
pip install rasterstats geopandas rasterio pandas numpy matplotlib
```

### Running the pipeline

1. Clone this repository
2. Copy `config/config_template.py` and edit the paths to match your local data
3. Open `notebooks/continuidade_refatorado.ipynb` in Jupyter
4. Edit **only** the configuration cell (Section 1) with your paths
5. Run all cells sequentially

The notebook includes a **checkpoint system**: if interrupted, rerunning will resume 
from the last completed raster rather than starting over.

---

## Data

### Input (not included — available from MapBiomas)

- Binary rasters: natural vegetation (1) vs. non-natural (0), 30 m resolution
- Hexagonal grid shapefile (contact authors)
- Source: [MapBiomas Brazil](https://mapbiomas.org) — Collection 9

### Output (included in `data/`)

| File | Description | Rows | Columns |
|---|---|---|---|
| `indices_bordas_EIF_consolidado.csv` | EII and area metrics per cell, OBS 1985–2020 | 19,183 | 25 |

Column naming convention: `prop1_OBS_YYYY` = EII for observed scenario, year YYYY.

---

## Project status

This repository is under active development. Planned analyses:

- [x] EII extraction pipeline (OBS baseline 1985–2020)
- [ ] Annual time series (1985–2024)
- [ ] Grid configuration sensitivity (MAUP: shape, scale, jitter)
- [ ] Change point detection (Area vs. EII structural breaks)
- [ ] Scenario comparison (TNC, BAU, GOV — 2030)

See [`docs/analysis_roadmap_EII.md`](docs/analysis_roadmap_EII.md) for the full plan.

---

## Citation

If you use this code or data, please cite:

> Barroso et al. (in preparation). *The Edge Interception Index: a systematic 
> transect-based metric for landscape interface connectivity and its application 
> to four decades of habitat dynamics in the Brazilian Cerrado.*

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Contact

**Mario Barroso**  
The Nature Conservancy
```

---

**Passo 4.** No final da página, em **"Commit changes"**, escreva:
```
Write full README with method description and repository structure
