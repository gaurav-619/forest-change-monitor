# forest-change-monitor

Work in progress - an educational, satellite-based forest/vegetation
change-monitoring prototype, built step by step as a portfolio
project while learning geospatial Python.

## What this is

A small, transparent pipeline that:

1. Takes a project boundary (GeoJSON)
2. Compares two Sentinel-2 satellite image composites of that area,
   before and after a chosen time window
3. Computes NDVI (a vegetation-greenness index) for each
4. Flags pixels where NDVI dropped sharply - a possible sign of
   vegetation loss
5. Reports the flagged area in hectares, with maps, data files, and
   a written report explaining exactly how the numbers were produced

## What this is *not*

Not a carbon-credit calculator. Not a certified deforestation-
detection system. It does not estimate biomass or CO2e, and a
"flagged" pixel is a hypothesis for a human to check, not a verified
finding. See `docs/limitations.md`.

## Why this exists

Built while learning geospatial Python, informed by the public
methodology documents of [Equitable Earth](https://www.eq-earth.com),
a nature-based carbon certification standard. `docs/methodology.md`
lays out exactly how this project's simplified approach compares to
their real, much more rigorous workflow.

## Status

Scaffold only so far (Phase 0). README will be filled in properly
once the pipeline runs end to end.
