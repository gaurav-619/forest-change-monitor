# Quality Assurance (QA) Controls

The Forest Change Monitor pipeline implements a rigorous automated QA process to ensure data integrity and mathematically honest reporting. The `outputs/yearly_loss_summary.json` file contains a detailed record of the exact spatial parameters and the results of four automated validation checks.

The `validate.py` script automatically runs these checks against the pipeline's output.

## 1. Data-lineage check
**Check**: `filename includes GFC-2023-v1.11_lossyear_20N_100E.tif`

**Why it matters**: Ensures the pipeline processed the intended official dataset from the University of Maryland / Global Forest Watch, rather than an arbitrary raster.

**What it does NOT prove**: This does not cryptographically prove file authenticity (e.g., via SHA256 hashing) because anyone can rename a file. It is solely a data-lineage check.

## 2. Spatial Coverage Check
**Check**: `source bounds contain the AOI`

**Why it matters**: Confirms that the provided Area of Interest (AOI) polygon is fully inside the boundaries of the downloaded raster. If the AOI falls outside the map, the pipeline would falsely report 0 hectares of loss rather than failing.

## 3. Year-Encoding Check
**Check**: `full raster contains values 21, 22, and 23`

**Why it matters**: Verifies that the source map actually contains data up to the year 2023. Instead of loading the entire Hansen Global Forest Change dataset into memory, this check uses a memory-efficient block-wise scan to explicitly find the values `21`, `22`, and `23`. It ensures we aren't querying an outdated version of the map (e.g., v1.8 which only goes up to 2020) and getting 0 loss due to missing data.

## 4. Independent CSV Cross-Check
**Check**: `clipped AOI contains the values reported in the summary CSV`

**Why it matters**: This is the strongest validation in the pipeline. `validate.py` explicitly loads the generated `outputs/clipped_lossyear.tif` and the `outputs/yearly_loss_summary.csv`. For every year, it:
1. Independently recalculates the exact pixel counts in the clipped raster.
2. Asserts that the count exactly equals the `loss_pixels` written in the CSV.
3. Recomputes the hectares using the exact latitude-adjusted pixel area.
4. Asserts that the computed area equals the `loss_area_ha` written in the CSV.

This verifies that the data presented on the dashboard strictly reflects the underlying spatial reality of the clipped map.
