"""Load and validate the AOI (Area Of Interest) GeoJSON boundary.

An AOI is the shape drawn around the piece of land we're analysing.
Before we trust that shape enough to do anything else with it, this
module checks three things:

1. Does the file actually contain exactly one valid polygon (no
   self-intersections, no empty geometry)?
2. Is it in the CRS we expect? GeoJSON's spec requires WGS84
   (EPSG:4326 - plain latitude/longitude), so anything else means
   something upstream reprojected it and it needs fixing before use.
3. How big is it in real units (hectares)? We can't measure area
   accurately in WGS84, since a degree of longitude covers a
   different number of metres depending on latitude - so this
   reprojects into a local, metre-based UTM zone first.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.validation import explain_validity


class InvalidAOIError(ValueError):
    """Raised when an AOI GeoDataFrame fails validation."""


def validate_gdf(gdf: gpd.GeoDataFrame, source: str = "<in-memory>") -> gpd.GeoDataFrame:
    """Run our validation checks against an already-loaded GeoDataFrame.

    Separated from `load_aoi` so it can be tested directly against
    in-memory GeoDataFrames, without needing to round-trip through a
    file on disk.
    """
    if len(gdf) == 0:
        raise InvalidAOIError(f"AOI has no features: {source}")
    if len(gdf) > 1:
        raise InvalidAOIError(
            f"Expected exactly one AOI feature, found {len(gdf)}: {source}"
        )

    geom = gdf.geometry.iloc[0]
    if geom is None or geom.is_empty:
        raise InvalidAOIError(f"AOI geometry is empty: {source}")
    if not geom.is_valid:
        raise InvalidAOIError(
            f"AOI geometry is not valid ({explain_validity(geom)}): {source}"
        )

    if gdf.crs is None:
        raise InvalidAOIError(
            f"AOI has no CRS - GeoJSON should be WGS84 (EPSG:4326): {source}"
        )
    if gdf.crs.to_epsg() != 4326:
        raise InvalidAOIError(
            f"Expected WGS84 (EPSG:4326), got {gdf.crs}: {source}"
        )

    return gdf


def load_aoi(path: str | Path) -> gpd.GeoDataFrame:
    """Load an AOI GeoJSON file into a GeoDataFrame and validate it.

    Parameters
    ----------
    path:
        Path to a GeoJSON file containing exactly one polygon feature.

    Returns
    -------
    A one-row GeoDataFrame in WGS84 (EPSG:4326).

    Raises
    ------
    InvalidAOIError
        If the file is missing, empty, has more than one feature,
        contains an invalid geometry, or isn't in WGS84.
    """
    path = Path(path)
    if not path.exists():
        raise InvalidAOIError(f"AOI file not found: {path}")

    gdf = gpd.read_file(path)
    return validate_gdf(gdf, source=str(path))


def area_hectares(gdf: gpd.GeoDataFrame, utm_epsg: int) -> float:
    """Compute an AOI's area in hectares.

    Parameters
    ----------
    gdf:
        AOI GeoDataFrame, as returned by `load_aoi` (WGS84).
    utm_epsg:
        EPSG code of the local UTM zone to reproject into before
        measuring (e.g. 32648 for UTM zone 48N, which covers our
        Cambodia demo site).

    Returns
    -------
    Area in hectares (1 hectare = 10,000 sq metres).
    """
    projected = gdf.to_crs(epsg=utm_epsg)
    area_m2 = projected.geometry.area.sum()
    return area_m2 / 10_000
