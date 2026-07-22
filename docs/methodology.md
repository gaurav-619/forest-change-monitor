# Methodology: Forest Change Monitor

This project analyzes satellite-derived tree-cover loss using a programmatic spatial pipeline. The goal is to accurately calculate the area of disturbed forest canopy within a specific Area of Interest (AOI).

## 1. Input Data
* **Raster**: Hansen Global Forest Change v1.11 `lossyear` tile. This is a global dataset indicating the first year of stand-replacement disturbance (tree canopy dropping below 25%).
* **AOI**: A GeoJSON polygon representing the region to analyze (in our demonstration, ~12,000 hectares near Prey Lang, Cambodia).

## 2. Coordinate Reference System (CRS) Alignment
Geospatial data only aligns correctly if it shares a coordinate system. 
* The Hansen raster uses `EPSG:4326` (WGS84 Geographic Degrees).
* To prevent altering the source raster pixels (which degrades data integrity), the pipeline reprojects the *vector AOI* to match the raster's CRS, never the other way around.

## 3. Raster Masking
Rather than processing the entire 109MB (40,000 x 40,000 pixel) global tile, the pipeline uses `rasterio.mask` to physically clip the array down to the exact boundary of the AOI polygon. Pixels outside the polygon are converted to a `NoData` value (`255`).

## 4. Year Encoding and Counting
The `lossyear` dataset uses an integer offset encoding:
* `0` = No loss
* `1` = Loss in 2001 ... `23` = Loss in 2023
* `255` = NoData

The pipeline subtracts the base year (2000) from the target year (e.g., `2021 - 2000 = 21`). It then performs a highly efficient NumPy boolean sum across the clipped array to count how many pixels exactly match that encoded value.

## 5. Pixel Area Calculation (Haversine Approximation)
Because the raster is in geographic degrees, the physical width (in meters) of a `0.00025°` pixel shrinks as you move away from the equator. Hard-coding "30 meters" is mathematically incorrect.

Instead, the pipeline:
1. Extracts the exact latitude of the AOI polygon's centroid.
2. Applies the Haversine trigonometric formula to calculate the pixel's width in meters at that specific latitude:
   `width_m = 0.00025 * 111,320 * cos(latitude)`
3. Multiplies by the pixel height (which remains constant) to get the exact square-meter area of a pixel.

## 6. Hectare Conversion
The final tree-cover loss area is calculated as:
`Total Hectares = (Pixel Count * Pixel Area in m²) / 10,000`

This exact value is saved to `outputs/yearly_loss_summary.csv` for the dashboard to render.
