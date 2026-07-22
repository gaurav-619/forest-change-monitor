# Limitations

This document lists everything that should be understood before treating any
output of this project as evidence of deforestation, carbon loss, or any other
certified finding.

---

## 1. The AOI is illustrative

The polygon in `data/aoi/demo_site.geojson` is a rectangular bounding box
drawn around a well-documented land-cover change hotspot within Prey Lang
Wildlife Sanctuary, Cambodia.  It was chosen for educational and portfolio
purposes.

It is **not**:
- a surveyed project boundary
- a concession boundary
- the exact footprint of any documented clearing event
- a legally or administratively defined area

Figures derived from this AOI describe activity within an arbitrary box, not
within any formally delimited area.

---

## 2. Tree-cover loss is not automatically deforestation

The Hansen GFC dataset detects **stand-replacement disturbance** — any
location where tree-canopy cover dropped from ≥25% to below that threshold
within a calendar year.

Causes that all produce a positive detection include:
- Commercial and artisanal logging (legal or illegal)
- Smallholder agriculture expansion
- Fire and burn scars
- Drought-induced canopy die-off
- Palm oil and rubber plantation harvesting
- Temporary land clearing for infrastructure
- Mapping artefacts from cloud shadow or poor Landsat scenes

A detection does not indicate which of these applied, or whether any
was permitted under local law.

---

## 3. Cause cannot be determined from this processing alone

This pipeline processes a raster that tells you *where* and *when* canopy
cover changed.  It provides no information about *why*.  Determining cause
requires additional data sources: field surveys, very-high-resolution imagery,
local land-use records, permit registers, or expert local knowledge.

---

## 4. No biomass, carbon, or CO₂e is calculated

This project does not produce:
- above-ground biomass (AGB) estimates
- below-ground biomass (BGB) or root-to-shoot ratios
- carbon stock or carbon stock change
- CO₂e emissions or removals
- additionality, leakage, permanence, or buffer pool calculations
- any number that could appear in a carbon accounting registry

It is explicitly and deliberately out of scope.

---

## 5. 30 m satellite mapping has spatial and temporal limitations

- **Minimum mapping unit:** Clearing events smaller than approximately one
  pixel (~900 m² at the equator) may not be detected, or may produce a mixed
  signal in a boundary pixel.
- **Temporal resolution:** Loss is assigned to a calendar year, not a specific
  date.  An event in December 2021 and one in January 2021 both produce
  `pixel value = 21`.
- **Landsat availability:** Cloud cover reduces the number of usable
  Landsat scenes differently across years and seasons, potentially
  influencing detection sensitivity.
- **Reprocessing boundary:** The Hansen product was reprocessed from 2011
  onward with improved algorithms.  Year-to-year comparisons that straddle
  2010–2011 require additional care.

---

## 6. Raw pixel counts are not a statistically validated area estimate

The IPCC and FAO provide guidance on acceptable methods for area estimation
from remotely-sensed data.  Multiplying pixel counts by nominal pixel area
does not meet those requirements because:
- It assumes every pixel is uniformly correctly classified.
- It includes no uncertainty bounds or confidence intervals.
- It does not account for systematic over- or under-estimation at the class
  boundary (the ≥25% canopy-cover threshold).

Results from this project should be labelled as **screening-level estimates**
only.

---

## 7. Results require contextual, field, and high-resolution review

Before any finding from this project could be used in a conservation or
carbon decision:
- Results would need independent verification against very-high-resolution
  imagery (commercial satellite or aerial photography).
- Field visits or local expert review would be required for a sample of
  flagged pixels.
- Legal context (land tenure, permit status, concession boundaries) would
  need to be layered in.

---

## 8. This is not an Equitable Earth product or methodology

This project is an independent educational portfolio piece.  It references
Equitable Earth's publicly documented approach only to illustrate the gap
between a simplified prototype and a real certification workflow.

It is **not**:
- affiliated with, endorsed by, or commissioned by Equitable Earth
- an implementation of any Equitable Earth standard or methodology document
- suitable for submission to any carbon registry or certification body
- a substitute for Equitable Earth's or any other accredited MRV system
