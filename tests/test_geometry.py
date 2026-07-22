"""Tests for forest_change.geometry.

These build small synthetic geometries in memory rather than relying
on the real demo site file, so they stay fast and independent of any
real data.
"""

import geopandas as gpd
import pytest
from shapely.geometry import Polygon, box

from forest_change.geometry import InvalidAOIError, area_hectares, load_aoi, validate_gdf


def _write_geojson(tmp_path, polygon, crs="EPSG:4326"):
    gdf = gpd.GeoDataFrame({"name": ["test"]}, geometry=[polygon], crs=crs)
    path = tmp_path / "aoi.geojson"
    gdf.to_file(path, driver="GeoJSON")
    return path


def test_load_valid_aoi(tmp_path):
    square = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    path = _write_geojson(tmp_path, square)

    gdf = load_aoi(path)

    assert len(gdf) == 1
    assert gdf.crs.to_epsg() == 4326


def test_missing_file_raises(tmp_path):
    with pytest.raises(InvalidAOIError):
        load_aoi(tmp_path / "does_not_exist.geojson")


def test_invalid_geometry_raises(tmp_path):
    # A classic self-intersecting "bowtie" polygon.
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    path = _write_geojson(tmp_path, bowtie)

    with pytest.raises(InvalidAOIError):
        load_aoi(path)


def test_wrong_crs_raises():
    square = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    gdf = gpd.GeoDataFrame({"name": ["test"]}, geometry=[square], crs="EPSG:32648")

    with pytest.raises(InvalidAOIError):
        validate_gdf(gdf)


def test_area_hectares_known_square():
    # A 1km x 1km square built directly in UTM zone 48N (area exactly
    # 100 hectares), then reprojected to WGS84 to mimic a real file.
    square_utm = box(500_000, 1_456_000, 501_000, 1_457_000)
    gdf_utm = gpd.GeoDataFrame({"name": ["test"]}, geometry=[square_utm], crs="EPSG:32648")
    gdf_wgs84 = gdf_utm.to_crs(epsg=4326)

    hectares = area_hectares(gdf_wgs84, utm_epsg=32648)

    assert hectares == pytest.approx(100, rel=0.01)
