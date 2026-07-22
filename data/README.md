# data/

## Directory structure

```
data/
  aoi/
    demo_site.geojson   — illustrative AOI polygon (WGS84, ~12,000 ha)
  raw/
    Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif — Hansen GFC lossyear raster (YOU must download this)
```

Note: The current AOI was selected from a regional Hansen loss-year scan to demonstrate non-zero pipeline output; it is not a representative sample or verified event boundary.

`aoi/` is committed to Git — it is a small vector file.
`raw/` is in `.gitignore` — the raster is ~600 MB and cannot be stored in Git.

---

## How to obtain `data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif`

This file is the **Hansen Global Forest Change v1.11 (2000–2023) annual
tree-cover-loss ("lossyear") raster**, produced by the University of Maryland
and distributed by Global Forest Watch.

**License:** Creative Commons Attribution 4.0 (CC BY 4.0). Free to use with
attribution. No registration or login required.

**Tile to download:** The AOI (Prey Lang, ~13°N 105.6°E) falls in the tile
covering 10°N–20°N, 100°E–110°E.

### Option A — Browser download (recommended for first-time users)

1. Open this URL in your browser:

   ```
   https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif
   ```

   The download will start automatically (~600 MB).

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

### Verification

```bash
ls -lh data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif
# Expected: approximately 580–620 MB
```

---

## What is this raster?

| Property | Value |
|---|---|
| Dataset | Hansen Global Forest Change v1.11 (GFC-2023) |
| Variable | Annual tree-cover-loss year ("lossyear") |
| Spatial resolution | ~30 m (1 arc-second) |
| Temporal coverage | 2001–2023 |
| Pixel encoding | `0` = no loss; `N` = loss in year `2000 + N` (e.g. `21` → 2021) |
| Nodata value | `255` |
| CRS | WGS84 (EPSG:4326) |
| Tile coverage | 10°N–20°N, 100°E–110°E (all of Cambodia) |
| License | CC BY 4.0 |
| Citation | Hansen et al., Science 2013, doi:10.1126/science.1244693 |
| Full download index | https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/download.html |

---

## What "tree-cover loss" means (and does not mean)

The Hansen dataset detects a **stand-replacement disturbance** — a location where
canopy cover dropped from ≥25% to below that threshold in a given year. This
includes commercial logging, smallholder clearing, fire, drought die-off,
plantation harvest, and mapping artefacts. A flagged pixel is a **screening
signal requiring contextual review**, not a verified deforestation record. See
`docs/limitations.md`.

---

## What happens after placing the file

The next time you run `streamlit run app.py`, the app will automatically:

1. Clip the raster to the AOI boundary.
2. Count loss pixels for 2021, 2022, and 2023.
3. Calculate hectares from the raster's affine transform.
4. Write `outputs/yearly_loss_summary.csv` and `outputs/yearly_loss_summary.json`.
5. Write `outputs/clipped_lossyear.tif` and `outputs/loss_map.png`.

On subsequent runs the cached CSV is used directly (no raster re-processing).
