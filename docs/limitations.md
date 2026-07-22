# Limitations

*(Placeholder - to be filled in once we have real results to point
at specific examples.)*

Running list of everything that can make a raw "NDVI dropped"
signal misleading on its own, without further investigation:

- Normal seasonal greening/browning (not matching before/after
  windows to the same season)
- Cloud and cloud-shadow artefacts that survive masking
- Drought stress (vegetation still standing, just less green)
- Crop harvest cycles in non-forest pixels near the AOI edge
- Fire and regrowth dynamics
- Sensor/orbit differences between the two composites
- Sensitivity of results to the chosen thresholds
