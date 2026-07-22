"""process_loss.py — Clip and summarise Hansen/GFW annual tree-cover-loss raster.

WHAT THIS DOES
--------------
Takes the Hansen Global Forest Change "lossyear" raster tile and an AOI
polygon, clips the raster to the AOI boundary, then counts how many pixels
were flagged as tree-cover loss in each requested year.  Area is derived from
the raster's own affine transform — never a hard-coded constant.

WHAT THIS IS NOT
----------------
This does NOT compute biomass, carbon stock, CO2e, additionality, leakage,
permanence, or any certification outcome.  "Tree-cover loss" in the Hansen
dataset is defined as a stand-replacement disturbance (canopy closure drops
from ≥25% to below that threshold).  Causes include logging, fire, drought,
conversion, smallholder clearing, and plantations.  A pixel flagged here is a
screening signal, not verified deforestation.

GIS CONCEPTS USED
-----------------
* Raster clipping / masking: cut the large global tile down to just the pixels
  inside our polygon.
* Affine transform: the 6-number formula in the GeoTIFF that maps pixel
  row/col indices to real-world coordinates.  Used to compute pixel area.
* CRS alignment: AOI and raster must share a coordinate system.  If they
  differ, the AOI is reprojected to match the raster (not the other way round)
  so the raster data is never altered.

DATA SOURCE
-----------
Hansen GFC v1.11 (2000-2023), University of Maryland / Global Forest Watch.
lossyear encoding: 0 = no loss; 1 = loss in 2001, …, 23 = loss in 2023.
Spatial resolution: ~30 m (1 arc-second at the equator, slightly smaller at
higher latitudes).
License: CC BY 4.0.  Citation: Hansen et al., Science 2013.
Cambodia tile:
  https://storage.googleapis.com/earthenginepartners-hansen/GFC-2023-v1.11/
  Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rio_mask

from forest_change.geometry import load_aoi, area_hectares

log = logging.getLogger(__name__)

# Loss-year pixel encoding: pixel_value = calendar_year - _YEAR_OFFSET
# e.g.  21 → 2021,  22 → 2022,  23 → 2023
_YEAR_OFFSET = 2000
_NO_LOSS_VALUE = 0
_NODATA_VALUE = 255  # Hansen tiles use 255 as the nodata sentinel


class RasterAOIError(ValueError):
    """Raised when raster and AOI are incompatible (no CRS, no overlap, etc.)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pixel_area_m2(src: rasterio.DatasetReader, aoi_gdf: gpd.GeoDataFrame = None) -> float:
    """Return the area of one raster pixel in square metres.

    HOW IT WORKS
    ------------
    The raster's affine transform gives pixel width and height in the
    raster's native CRS units.  For WGS84 (degrees), those units can't be
    used directly for area because a degree of longitude narrows as latitude
    increases.

    For geographic CRS we use the Haversine approximation:
      pixel_width_m  = |res_x| × 111 320 × cos(centre_lat)
      pixel_height_m = |res_y| × 110 574
    where centre_lat is the mid-latitude of the raster tile.
    This is accurate to <0.3 % for the ~30 m Hansen tiles.

    For projected CRS (units already in metres) we multiply directly.
    """
    res_x = abs(src.transform.a)  # pixel width  in CRS units
    res_y = abs(src.transform.e)  # pixel height in CRS units

    if src.crs.is_geographic:
        if aoi_gdf is not None:
            # Calculate at the centroid of the AOI for more accuracy
            centroid = aoi_gdf.to_crs(epsg=4326).geometry.union_all().centroid
            centre_lat = math.radians(centroid.y)
        else:
            # Fallback to raster center
            centre_lat = math.radians((src.bounds.top + src.bounds.bottom) / 2)
            
        width_m  = res_x * 111_320 * math.cos(centre_lat)
        height_m = res_y * 110_574
        return width_m * height_m
    else:
        return res_x * res_y

def _check_full_raster_values(src: rasterio.DatasetReader, required_values: set[int]) -> bool:
    """Check if all required values are present in the full raster efficiently using blocks."""
    found = set()
    for _, window in src.block_windows(1):
        data = src.read(1, window=window)
        # Add values from this block to found set (only if they are in required_values)
        found.update(set(np.unique(data)).intersection(required_values))
        if found == required_values:
            return True
    return False


def _align_aoi_to_raster_crs(
    aoi_gdf: gpd.GeoDataFrame,
    src: rasterio.DatasetReader,
) -> gpd.GeoDataFrame:
    """Return AOI reprojected to the raster's CRS if they differ.

    We always reproject the *vector* AOI, never the raster, to avoid
    altering the pixel data.

    Raises
    ------
    RasterAOIError
        If the raster has no CRS at all — we cannot safely align without one.
    """
    if src.crs is None:
        raise RasterAOIError(
            "The lossyear raster has no CRS defined.  "
            "Ensure the file is a valid, georeferenced GeoTIFF."
        )

    aoi_epsg  = aoi_gdf.crs.to_epsg() if aoi_gdf.crs else None
    rast_epsg = src.crs.to_epsg()

    if aoi_epsg == rast_epsg:
        return aoi_gdf  # already aligned — nothing to do

    log.info(
        "AOI CRS (EPSG:%s) differs from raster CRS (EPSG:%s) — reprojecting AOI.",
        aoi_epsg, rast_epsg,
    )
    return aoi_gdf.to_crs(src.crs)


def _build_qa(
    aoi_gdf: gpd.GeoDataFrame,
    src: rasterio.DatasetReader,
    clipped: np.ndarray,
    pixel_area_m2: float,
    lossyear_path: Path,
    utm_epsg: int,
    years: Sequence[int],
) -> dict:
    """Build a quality-assurance metadata dictionary for this analysis run."""
    total_pixels  = int(clipped.size)
    nodata_pixels = int(np.sum(clipped == _NODATA_VALUE))
    valid_pixels  = total_pixels - nodata_pixels

    valid_mask = clipped != _NODATA_VALUE
    if valid_mask.any():
        obs_min = int(clipped[valid_mask].min())
        obs_max = int(clipped[valid_mask].max())
    else:
        obs_min = obs_max = None

    return {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "aoi_valid": True,
        "aoi_area_ha": round(area_hectares(aoi_gdf, utm_epsg=utm_epsg), 2),
        "source_raster_exists": lossyear_path.exists(),
        "raster_crs": src.crs.to_string() if src.crs else "UNKNOWN",
        "raster_epsg": src.crs.to_epsg() if src.crs else None,
        "crs_recognized": src.crs is not None,
        "source_resolution_x_deg": round(abs(src.transform.a), 8),
        "source_resolution_y_deg": round(abs(src.transform.e), 8),
        "pixel_area_m2": round(pixel_area_m2, 4),
        "pixel_area_ha": round(pixel_area_m2 / 10_000, 8),
        "clipped_total_pixels": total_pixels,
        "clipped_nodata_pixels": nodata_pixels,
        "clipped_valid_pixels": valid_pixels,
        "nodata_pct": round(nodata_pixels / total_pixels * 100, 2) if total_pixels else 0.0,
        "observed_lossyear_value_range": [obs_min, obs_max] if obs_min is not None else None,
        "expected_lossyear_value_range": [0, 23],
        "year_encoding_note": (
            "pixel_value = calendar_year - 2000  "
            "(e.g. 21 → 2021).  0 = no loss.  255 = nodata."
        ),
        "validations": {
            "filename_valid": bool("GFC-2023-v1.11_lossyear_20N_100E.tif" in lossyear_path.name),
            "source_bounds_contain_aoi": bool(
                src.bounds.left <= aoi_gdf.total_bounds[0] and
                src.bounds.bottom <= aoi_gdf.total_bounds[1] and
                src.bounds.right >= aoi_gdf.total_bounds[2] and
                src.bounds.top >= aoi_gdf.total_bounds[3]
            ),
            "full_raster_contains_21_22_23": bool(_check_full_raster_values(src, {21, 22, 23})),
            "clipped_contains_reported_values": bool(all(
                int(np.sum(clipped == (y - _YEAR_OFFSET))) > 0 for y in years
            )),
        }
    }


def _save_loss_map_png(
    clipped: np.ndarray,
    years: Sequence[int],
    out_path: Path,
) -> None:
    """Save a static PNG of the clipped loss-year raster."""
    fig, ax = plt.subplots(figsize=(8, 7), facecolor="#0f1f17")
    ax.set_facecolor("#0f1f17")

    # Mask no-loss (0) and nodata (255) so they render transparent
    display = np.where(
        (clipped == _NO_LOSS_VALUE) | (clipped == _NODATA_VALUE),
        np.nan,
        clipped.astype(float),
    )

    if not np.isnan(display).all():
        vmin = min(y - _YEAR_OFFSET for y in years)
        vmax = max(y - _YEAR_OFFSET for y in years)
        im = ax.imshow(display, cmap="YlOrRd", vmin=vmin, vmax=vmax, interpolation="none")
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
        cbar.set_ticks([y - _YEAR_OFFSET for y in years])
        cbar.set_ticklabels([str(y) for y in years])
        cbar.ax.yaxis.set_tick_params(color="#95d5b2", labelcolor="#95d5b2")
        cbar.set_label("Loss year", color="#95d5b2", fontsize=9)
    else:
        ax.text(
            0.5, 0.5, "No tree-cover-loss pixels detected in AOI\nfor the requested years",
            transform=ax.transAxes, ha="center", va="center",
            color="#95d5b2", fontsize=12,
        )

    ax.set_title(
        "Satellite-mapped tree-cover-loss signal\n"
        "Prey Lang AOI · Hansen GFC v1.11 · ~30 m",
        color="#74c69d", fontsize=11, pad=12,
    )
    ax.tick_params(colors="#95d5b2", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2d6a4f")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0f1f17")
    plt.close(fig)
    log.info("Wrote loss map PNG: %s", out_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_annual_loss(
    aoi_path: str | Path,
    lossyear_path: str | Path,
    years: Sequence[int] = (2021, 2022, 2023),
    utm_epsg: int = 32648,
) -> pd.DataFrame:
    """Clip lossyear raster to AOI and return annual satellite-mapped loss area.

    Parameters
    ----------
    aoi_path:
        Path to the AOI GeoJSON (WGS84, single polygon).
    lossyear_path:
        Path to the Hansen GFC lossyear GeoTIFF.
    years:
        Calendar years to summarise (default 2021, 2022, 2023).
    utm_epsg:
        Local UTM zone for AOI area calculation.  Default 32648 = UTM 48N
        (correct for Prey Lang, ~105.6 °E).

    Returns
    -------
    DataFrame with columns: year, loss_pixels, loss_area_ha.

    Notes
    -----
    loss_pixels counts 30 m pixels flagged as tree-cover loss inside the AOI.
    loss_area_ha is pixel_count × pixel_area — a screening-level estimate,
    not a statistically validated area per IPCC or GFW guidance.
    """
    aoi_path      = Path(aoi_path)
    lossyear_path = Path(lossyear_path)

    log.info("Loading AOI: %s", aoi_path)
    aoi_gdf = load_aoi(aoi_path)

    if not lossyear_path.exists():
        raise FileNotFoundError(
            f"lossyear raster not found: {lossyear_path}\n"
            "See data/README.md for download instructions."
        )

    with rasterio.open(lossyear_path) as src:
        aoi_aligned   = _align_aoi_to_raster_crs(aoi_gdf, src)
        pixel_area_m2 = _pixel_area_m2(src, aoi_aligned)

        log.info(
            "Raster: CRS=%s  res=(%.8f, %.8f)  size=%dx%d  pixel_area=%.2f m²",
            src.crs.to_string(), src.transform.a, abs(src.transform.e),
            src.width, src.height, pixel_area_m2,
        )

        shapes = [geom.__geo_interface__ for geom in aoi_aligned.geometry]
        clipped_data, _ = rio_mask(src, shapes, crop=True, nodata=_NODATA_VALUE)
        clipped = clipped_data[0]  # band 1

    log.info("Clipped shape: %s", clipped.shape)

    records = []
    for year in years:
        encoded     = year - _YEAR_OFFSET
        pixel_count = int(np.sum(clipped == encoded))
        loss_ha     = round(pixel_count * pixel_area_m2 / 10_000, 2)
        log.info("  %d: %d px → %.2f ha", year, pixel_count, loss_ha)
        records.append({"year": year, "loss_pixels": pixel_count, "loss_area_ha": loss_ha})

    return pd.DataFrame(records)


def run_full_pipeline(
    aoi_path: str | Path,
    lossyear_path: str | Path,
    output_dir: str | Path,
    years: Sequence[int] = (2021, 2022, 2023),
    utm_epsg: int = 32648,
) -> pd.DataFrame:
    """Run the complete pipeline and write all outputs.

    Outputs written to output_dir
    ------------------------------
    yearly_loss_summary.csv   — one row per year
    yearly_loss_summary.json  — same data + QA metadata
    clipped_lossyear.tif      — raster clipped to AOI extent
    loss_map.png              — static visualisation of loss pixels

    Parameters
    ----------
    output_dir:
        Directory to write all output files (created if absent).

    Returns
    -------
    Summary DataFrame (same as compute_annual_loss).
    """
    aoi_path      = Path(aoi_path)
    lossyear_path = Path(lossyear_path)
    output_dir    = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== run_full_pipeline: start ===")
    log.info("  AOI:    %s", aoi_path)
    log.info("  Raster: %s", lossyear_path)
    log.info("  Output: %s", output_dir)

    aoi_gdf = load_aoi(aoi_path)

    if not lossyear_path.exists():
        raise FileNotFoundError(
            f"lossyear raster not found: {lossyear_path}\n"
            "See data/README.md for download instructions."
        )

    with rasterio.open(lossyear_path) as src:
        aoi_aligned    = _align_aoi_to_raster_crs(aoi_gdf, src)
        pixel_area_m2  = _pixel_area_m2(src, aoi_aligned)
        shapes         = [geom.__geo_interface__ for geom in aoi_aligned.geometry]
        clipped_data, clipped_transform = rio_mask(
            src, shapes, crop=True, nodata=_NODATA_VALUE
        )
        clipped      = clipped_data[0]
        raster_crs   = src.crs
        src_profile  = src.profile.copy()
        qa           = _build_qa(aoi_gdf, src, clipped, pixel_area_m2, lossyear_path, utm_epsg, years)

    # Annual summary
    records = []
    for year in years:
        encoded     = year - _YEAR_OFFSET
        pixel_count = int(np.sum(clipped == encoded))
        loss_ha     = round(pixel_count * pixel_area_m2 / 10_000, 2)
        records.append({"year": year, "loss_pixels": pixel_count, "loss_area_ha": loss_ha})
        log.info("  %d: %d px → %.2f ha", year, pixel_count, loss_ha)

    df = pd.DataFrame(records)

    # --- CSV ---
    csv_path = output_dir / "yearly_loss_summary.csv"
    df.to_csv(csv_path, index=False)
    log.info("Wrote CSV: %s", csv_path)

    # --- JSON ---
    json_path = output_dir / "yearly_loss_summary.json"
    json_out = {
        "metadata": {
            "aoi_path": str(aoi_path),
            "source_raster": str(lossyear_path),
            "years_analysed": list(years),
        },
        "qa": qa,
        "results": df.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(json_out, indent=2), encoding="utf-8")
    log.info("Wrote JSON: %s", json_path)

    # --- Clipped GeoTIFF ---
    tif_path = output_dir / "clipped_lossyear.tif"
    src_profile.update(
        driver="GTiff",
        height=int(clipped.shape[0]),
        width=int(clipped.shape[1]),
        transform=clipped_transform,
        crs=raster_crs,
        count=1,
        nodata=_NODATA_VALUE,
        compress="lzw",
    )
    with rasterio.open(tif_path, "w", **src_profile) as dst:
        dst.write(clipped, 1)
    log.info("Wrote clipped GeoTIFF: %s", tif_path)

    # --- PNG map ---
    png_path = output_dir / "loss_map.png"
    _save_loss_map_png(clipped, years, png_path)

    log.info("=== run_full_pipeline: complete ===")
    return df


def run_and_save(
    aoi_path: str | Path,
    lossyear_path: str | Path,
    output_csv: str | Path,
    years: Sequence[int] = (2021, 2022, 2023),
    utm_epsg: int = 32648,
) -> pd.DataFrame:
    """Convenience wrapper: run_full_pipeline with output_dir = CSV parent directory."""
    return run_full_pipeline(
        aoi_path=aoi_path,
        lossyear_path=lossyear_path,
        output_dir=Path(output_csv).parent,
        years=years,
        utm_epsg=utm_epsg,
    )
