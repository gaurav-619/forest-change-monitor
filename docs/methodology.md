# Methodology

## What this pipeline does

This document describes the Version 1 processing pipeline step by step.
The goal is transparency: a future reviewer should be able to replicate every
number from the inputs and the code.

---

## Pipeline overview

```
GeoJSON AOI boundary
       ↓
   [1] Load & validate
       ↓
   Hansen GFC lossyear GeoTIFF  →  [2] Open raster
       ↓
   [3] Align CRS  (reproject AOI if needed)
       ↓
   [4] Clip raster to AOI
       ↓
   [5] Interpret pixel values as loss years
       ↓
   [6] Count pixels → calculate hectares
       ↓
   [7] QA checks
       ↓
   [8] Write outputs (CSV, JSON, GeoTIFF, PNG)
```

---

## Step 1 — Load and validate the AOI

**File:** `src/forest_change/geometry.py`

The Area of Interest (AOI) is loaded from a GeoJSON file using GeoPandas.
Before any processing, four checks are enforced:

- The file must exist and contain exactly one feature.
- The geometry must be non-empty and geometrically valid (no self-intersections,
  no empty rings).
- The CRS must be WGS84 (EPSG:4326), as required by the GeoJSON specification.
- AOI area in hectares is computed by reprojecting into a local UTM zone
  (EPSG:32648 for the Prey Lang site) and calculating m² / 10 000.

If any check fails, an `InvalidAOIError` is raised with a descriptive message.

---

## Step 2 — Open the lossyear raster

**File:** `src/forest_change/process_loss.py`

The Hansen GFC lossyear raster is a single-band GeoTIFF where each pixel value
encodes the year of the most-recent tree-cover-loss detection:

```
pixel value = 0       → no loss detected (2001–2023)
pixel value = N       → loss detected in year (2000 + N)
                          e.g.  21 → 2021,  22 → 2022,  23 → 2023
pixel value = 255     → nodata
```

This encoding is fixed by the Hansen dataset documentation and is not guessed.
Source: Hansen et al., Science 2013 / GFW download page.

---

## Step 3 — CRS alignment

The raster is always in WGS84 (EPSG:4326).  The AOI is also delivered in
WGS84.  The pipeline aligns the AOI to the raster's CRS — not the other way
around — so pixel data is never resampled or modified.

If the AOI were in a different CRS (e.g. a projected UTM file), it would be
reprojected to match.  If the raster has no CRS at all, the pipeline raises
an error because alignment is impossible.

---

## Step 4 — Clip the raster to the AOI

Using `rasterio.mask()`, only pixels whose centres fall within the AOI polygon
are kept.  The rest are masked with the nodata value (255).  The clip returns
a new array and a new affine transform describing the smaller bounding box.

---

## Step 5 — Pixel-area calculation

Pixel area is derived from the raster's affine transform — never a hard-coded
constant.  This matters because:

- The pixel size at ~30 m varies slightly with latitude.
- The formula must also work for any other raster with different resolution.

For geographic CRS (degrees), the Haversine approximation is used:

```
pixel_width_m  = |res_x| × 111 320 × cos(centre_latitude)
pixel_height_m = |res_y| × 110 574
pixel_area_m²  = pixel_width_m × pixel_height_m
```

where `centre_latitude` is the mid-latitude of the full tile (not the AOI),
and `res_x`, `res_y` are the pixel dimensions in degrees from the transform.

This is accurate to <0.3 % for the Prey Lang site (~13 °N).

---

## Step 6 — Count pixels and calculate hectares

For each requested year:

1. Compute the encoded pixel value: `encoded = year - 2000`.
2. Count pixels in the clipped array where `value == encoded`.
3. Multiply by pixel area: `loss_m² = pixel_count × pixel_area_m²`.
4. Convert: `loss_ha = loss_m² / 10 000`.

Zero loss pixels is a valid result, not an error.

---

## Step 7 — QA checks

A quality-assurance dictionary is assembled with:

- AOI validity flag and computed area.
- Raster existence and CRS recognition.
- Observed pixel value range (to catch truncated or wrong tiles).
- Expected value range (0–23 for v1.11).
- Nodata percentage in the clipped extent.
- Source resolution and computed pixel area.
- Analysis timestamp (UTC).

All QA fields are written into the JSON output for traceability.

---

## Step 8 — Outputs

| File | Description |
|---|---|
| `outputs/yearly_loss_summary.csv` | Year, pixel count, hectares — one row per year |
| `outputs/yearly_loss_summary.json` | Same data + QA metadata + analysis parameters |
| `outputs/clipped_lossyear.tif` | Raster clipped to AOI extent (LZW compressed) |
| `outputs/loss_map.png` | Static map of loss pixels coloured by year |

---

## What this pipeline does NOT do

- It does not determine the **cause** of tree-cover change.
- It does not compute above-ground biomass (AGB), carbon stock, CO₂e,
  additionality, leakage, or permanence.
- It does not perform statistical area estimation with uncertainty bounds.
- It does not qualify for use in a certified carbon accounting framework.

---

## Data citation

Hansen, M. C., P. V. Potapov, R. Moore, M. Hancher, S. A. Turubanova,
A. Tyukavina, D. Thau, S. V. Stehman, S. J. Goetz, T. R. Loveland, A.
Kommareddy, A. Egorov, L. Chini, C. O. Justice, and J. R. G. Townshend.
2013. "High-Resolution Global Maps of 21st-Century Forest Cover Change."
*Science* 342 (15 November): 850–53.
doi:10.1126/science.1244693.
