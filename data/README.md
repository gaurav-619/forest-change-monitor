# Data

## Directory Structure

```text
data/
├── aoi/
│   └── demo_site.geojson
└── raw/
    └── Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif
```

- `aoi/demo_site.geojson` is a small illustrative AOI polygon in WGS84 and is
  committed to Git.
- `raw/` is excluded through `.gitignore` because the source GeoTIFF is too
  large to include in the repository. Users download it separately when they
  want to run the full local pipeline.
- The AOI was selected from a regional Hansen loss-year scan to demonstrate
  non-zero pipeline output. It is not a representative sample, legally
  surveyed project boundary, or verified event boundary.

---

## How to obtain `data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif`

This file is the **Hansen Global Forest Change v1.11 (2000–2023) annual
tree-cover-loss ("lossyear") raster**, produced by the University of Maryland
and distributed by Global Forest Watch.

The file is too large to include in this repository and is excluded through
`.gitignore`. Download time and file size may vary by dataset version and
compression. The dataset is distributed in GeoTIFF tiles and is available under CC BY 4.0. No registration or login required.

**Tile to download:** The illustrative AOI lies in the Prey Lang region of Cambodia, within the 10°N–20°N, 100°E–110°E Hansen raster tile.

### Option A — Browser download (recommended for first-time users)

1. Open this URL in your browser:

   ```
   https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif
   ```

   The download will start automatically.

2. Move the file to the correct location:

   ```bash
   mkdir -p data/raw
   mv ~/Downloads/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif \
      data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif
   ```

### Option B — Command-line download

```bash
mkdir -p data/raw
curl -L -o data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif \
  "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif"
```

On Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path data\raw
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif" `
  -OutFile "data\raw\Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif"
```

---

## What is this raster?

| Property | Value |
|---|---|
| Dataset | Hansen Global Forest Change v1.11 (GFC-2023) |
| Variable | Annual tree-cover-loss year ("lossyear") |
| Spatial resolution | ~30 m (1 arc-second) |
| Temporal coverage | 2001–2023 |
| Pixel encoding | `0` = no loss; `N` = loss in year `2000 + N` (1 = 2001 … 23 = 2023) |
| Nodata value | `255` |
| CRS | WGS84 (EPSG:4326) |
| Tile coverage | 10°N–20°N, 100°E–110°E (all of Cambodia) |
| License | CC BY 4.0 |
| Citation | Hansen et al., Science 2013, doi:10.1126/science.1244693 |
| Full download index | https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/download.html |

---

## What "tree-cover loss" means (and does not mean)

The Hansen `lossyear` product records a satellite-derived **gross forest-cover
loss event**, defined by the dataset as a stand-replacement disturbance: a
change from a forest to a non-forest state at the Landsat-pixel scale.

A flagged pixel indicates that the Hansen processing detected tree-cover loss
at that location in the encoded year. It is useful as a spatial monitoring
signal, but it does not by itself establish:

- that the event was permanent deforestation;
- the cause of loss, such as agriculture, logging, fire, storm damage, or
  plantation harvesting;
- whether tree cover later regrew;
- whether the event was legal or illegal; or
- a certification or carbon-accounting outcome.

Additional imagery, land-use information, project records, and/or field
evidence would be needed to interpret the cause and permanence of the
detected loss.

---

## What happens after placing the file

The next time you run `streamlit run app.py`, the app will automatically:

1. Clip the raster to the AOI boundary.
2. Count loss pixels for 2021, 2022, and 2023.
3. Calculate hectares from the raster's affine transform.
4. Write `outputs/yearly_loss_summary.csv` and `outputs/yearly_loss_summary.json`.
5. Write `outputs/clipped_lossyear.tif` and `outputs/loss_map.png`.

On subsequent runs the cached CSV is used directly (no raster re-processing).
