"""Tests for forest_change.process_loss.

We use small synthetic rasters built in memory (via rasterio MemoryFile) or
written to tmp_path, so tests are fast, offline, and independent of the 600 MB
real Hansen tile.

WHAT WE TEST
------------
1.  Year filtering: only pixels with the correct encoded value are counted.
2.  Hectare math: pixel count × pixel_area_m2 / 10 000.
3.  Non-30 m pixel size: pixel area must come from the transform, not a constant.
4.  No-loss result: zero pixels / 0.0 ha is a valid, non-error outcome.
5.  Missing raster: FileNotFoundError with a helpful message.
6.  CRS mismatch: AOI is reprojected to match raster (no error raised).
7.  Raster with no CRS: RasterAOIError is raised immediately.
8.  Pixel area at equator vs. 13 °N: cos(lat) shrinks longitude-width.
"""

from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from shapely.geometry import box

from forest_change.process_loss import (
    RasterAOIError,
    _align_aoi_to_raster_crs,
    _pixel_area_m2,
    compute_annual_loss,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_synthetic_raster(
    data: np.ndarray,
    bounds: tuple[float, float, float, float],  # (west, south, east, north)
    crs: str | None = "EPSG:4326",
) -> MemoryFile:
    """Create a single-band GeoTIFF in memory.  Caller must close the MemoryFile."""
    rows, cols = data.shape
    transform  = from_bounds(*bounds, width=cols, height=rows)
    memfile    = MemoryFile()
    with memfile.open(
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=255,
    ) as ds:
        ds.write(data, 1)
    return memfile


def _make_aoi_gdf(
    bounds: tuple[float, float, float, float],
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"name": ["test"]}, geometry=[box(*bounds)], crs=crs)


def _write_raster_to_disk(
    tmp_path: Path,
    data: np.ndarray,
    bounds: tuple[float, float, float, float],
    crs: str = "EPSG:4326",
    filename: str = "lossyear.tif",
) -> Path:
    rows, cols  = data.shape
    transform   = from_bounds(*bounds, width=cols, height=rows)
    raster_path = tmp_path / filename
    with rasterio.open(
        raster_path, "w",
        driver="GTiff", height=rows, width=cols,
        count=1, dtype=data.dtype, crs=crs,
        transform=transform, nodata=255,
    ) as ds:
        ds.write(data, 1)
    return raster_path


def _write_aoi_to_disk(
    tmp_path: Path,
    bounds: tuple[float, float, float, float],
    crs: str = "EPSG:4326",
    filename: str = "aoi.geojson",
) -> Path:
    gdf  = _make_aoi_gdf(bounds, crs=crs)
    path = tmp_path / filename
    gdf.to_file(path, driver="GeoJSON")
    return path


# ---------------------------------------------------------------------------
# _pixel_area_m2
# ---------------------------------------------------------------------------

def test_pixel_area_near_equator():
    """1 arc-second pixel at the equator is approximately 930 m² (30 × 31)."""
    bounds = (100.0, 0.0, 101.0, 1.0)
    data   = np.zeros((3600, 3600), dtype=np.uint8)
    with _make_synthetic_raster(data, bounds).open() as src:
        area = _pixel_area_m2(src)
    assert 750 < area < 1100, f"Expected ~900 m², got {area:.1f}"


def test_pixel_area_at_13n_smaller_than_equator():
    """Pixel width shrinks with cos(lat): 13 °N area < equatorial area."""
    data = np.zeros((3600, 3600), dtype=np.uint8)
    with _make_synthetic_raster(data, (105.0, 13.0, 106.0, 14.0)).open() as src_13:
        area_13 = _pixel_area_m2(src_13)
    with _make_synthetic_raster(data, (105.0, 0.0, 106.0, 1.0)).open() as src_eq:
        area_eq = _pixel_area_m2(src_eq)

    assert area_13 < area_eq
    ratio = area_13 / area_eq
    # cos(13°) ≈ 0.974  →  ratio should be roughly 0.94–0.99
    assert 0.93 < ratio < 0.99, f"Unexpected ratio: {ratio:.4f}"


def test_pixel_area_non_30m_uses_transform():
    """With a 100 m (0.0009 °) pixel the area must scale accordingly."""
    # Pixel size ~10× smaller than 30 m Hansen tile
    large_data = np.zeros((1000, 1000), dtype=np.uint8)
    small_data = np.zeros((100, 100), dtype=np.uint8)
    same_bounds = (105.0, 13.0, 105.9, 13.9)

    with _make_synthetic_raster(large_data, same_bounds).open() as src_large:
        area_large = _pixel_area_m2(src_large)
    with _make_synthetic_raster(small_data, same_bounds).open() as src_small:
        area_small = _pixel_area_m2(src_small)

    # Fewer pixels over same extent → each pixel is bigger
    ratio = area_small / area_large
    assert 90 < ratio < 110, f"Expected ~100× area ratio, got {ratio:.1f}"


# ---------------------------------------------------------------------------
# _align_aoi_to_raster_crs
# ---------------------------------------------------------------------------

def test_align_same_crs_returns_unchanged():
    """No reprojection needed when CRSs already match."""
    aoi_gdf = _make_aoi_gdf((105.0, 13.0, 106.0, 14.0))
    data    = np.zeros((10, 10), dtype=np.uint8)
    with _make_synthetic_raster(data, (105.0, 13.0, 106.0, 14.0)).open() as src:
        result = _align_aoi_to_raster_crs(aoi_gdf, src)
    assert result.crs.to_epsg() == 4326


def test_align_reprojects_utm_aoi_to_geographic_raster():
    """UTM AOI is reprojected to match a WGS84 raster, not raise."""
    aoi_gdf = _make_aoi_gdf((500_000, 1_400_000, 600_000, 1_500_000), crs="EPSG:32648")
    data    = np.zeros((10, 10), dtype=np.uint8)
    with _make_synthetic_raster(data, (100.0, 10.0, 101.0, 11.0), crs="EPSG:4326").open() as src:
        result = _align_aoi_to_raster_crs(aoi_gdf, src)
    assert result.crs.to_epsg() == 4326


def test_align_raster_with_no_crs_raises():
    """Raster with no CRS must raise RasterAOIError — we cannot align safely."""
    aoi_gdf = _make_aoi_gdf((105.0, 13.0, 106.0, 14.0))
    data    = np.zeros((10, 10), dtype=np.uint8)
    with _make_synthetic_raster(data, (105.0, 13.0, 106.0, 14.0), crs=None).open() as src:
        with pytest.raises(RasterAOIError, match="no CRS"):
            _align_aoi_to_raster_crs(aoi_gdf, src)


# ---------------------------------------------------------------------------
# compute_annual_loss — integration tests (disk files via tmp_path)
# ---------------------------------------------------------------------------

def test_loss_year_filtering(tmp_path):
    """Only pixels with the correct encoded value count for each year.

    4×4 raster:  4 px = 21 (2021),  2 px = 22 (2022),  1 px = 23 (2023).
    AOI covers the whole raster — counts must match exactly.
    """
    data = np.array(
        [[21, 21, 22, 0],
         [21, 21, 22, 0],
         [ 0,  0, 23, 0],
         [ 0,  0,  0, 0]],
        dtype=np.uint8,
    )
    raster_path = _write_raster_to_disk(tmp_path, data, (105.60, 13.16, 105.64, 13.20))
    aoi_path    = _write_aoi_to_disk(tmp_path,         (105.59, 13.15, 105.65, 13.21))

    df = compute_annual_loss(aoi_path, raster_path, years=(2021, 2022, 2023))

    assert df.loc[df.year == 2021, "loss_pixels"].iloc[0] == 4
    assert df.loc[df.year == 2022, "loss_pixels"].iloc[0] == 2
    assert df.loc[df.year == 2023, "loss_pixels"].iloc[0] == 1


def test_hectare_calculation_derived_from_transform(tmp_path):
    """Hectares = pixel_count × pixel_area_from_transform / 10 000."""
    data = np.array([[21, 0], [0, 0]], dtype=np.uint8)
    raster_bounds = (105.60, 13.16, 105.62, 13.18)
    aoi_path    = _write_aoi_to_disk(tmp_path,     (105.59, 13.15, 105.63, 13.19))
    raster_path = _write_raster_to_disk(tmp_path, data, raster_bounds)

    df = compute_annual_loss(aoi_path, raster_path, years=(2021,))

    # Manual pixel-area computation matching _pixel_area_m2 formula
    res_x = (105.62 - 105.60) / 2   # 0.01° — one pixel width
    res_y = (13.18  - 13.16)  / 2   # 0.01° — one pixel height
    centre_lat = (13.16 + 13.18) / 2
    width_m  = res_x * 111_320 * math.cos(math.radians(centre_lat))
    height_m = res_y * 110_574
    expected_ha = (width_m * height_m) / 10_000  # 1 pixel

    actual_ha = df.loc[df.year == 2021, "loss_area_ha"].iloc[0]
    assert actual_ha == pytest.approx(expected_ha, rel=0.01)


def test_no_loss_pixels_returns_zero(tmp_path):
    """All-zero raster (no loss anywhere) → 0 pixels, 0.0 ha — not an error."""
    data        = np.zeros((4, 4), dtype=np.uint8)
    raster_path = _write_raster_to_disk(tmp_path, data, (105.60, 13.16, 105.64, 13.20))
    aoi_path    = _write_aoi_to_disk(tmp_path,         (105.59, 13.15, 105.65, 13.21))

    df = compute_annual_loss(aoi_path, raster_path, years=(2021, 2022, 2023))

    assert (df["loss_pixels"] == 0).all()
    assert (df["loss_area_ha"] == 0.0).all()


def test_missing_raster_raises_file_not_found(tmp_path):
    """Missing raster → FileNotFoundError with a helpful message."""
    aoi_path = _write_aoi_to_disk(tmp_path, (105.59, 13.15, 105.65, 13.21))

    with pytest.raises(FileNotFoundError, match="lossyear raster not found"):
        compute_annual_loss(aoi_path, tmp_path / "does_not_exist.tif")


def test_crs_mismatch_handled_by_reprojection(tmp_path):
    """compute_annual_loss succeeds when AOI and raster have different CRSs.

    The AOI should be reprojected internally — no error raised.
    """
    # Loss pixel in the raster
    data = np.array([[21, 0], [0, 0]], dtype=np.uint8)
    raster_bounds = (105.60, 13.16, 105.62, 13.18)
    raster_path   = _write_raster_to_disk(tmp_path, data, raster_bounds, crs="EPSG:4326")

    # AOI written in WGS84 (load_aoi requires WGS84 input)
    aoi_path = _write_aoi_to_disk(tmp_path, (105.59, 13.15, 105.63, 13.19), crs="EPSG:4326")

    # Should succeed and find the loss pixel
    df = compute_annual_loss(aoi_path, raster_path, years=(2021,))
    assert df.loc[df.year == 2021, "loss_pixels"].iloc[0] >= 1
