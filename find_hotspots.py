"""
Find nearby pixels with 2021-2023 loss and suggest a better AOI.
Scans a wider area around Prey Lang to locate actual loss hotspots.
"""
import rasterio
import numpy as np
from rasterio.windows import from_bounds

# Scan a wider region around Prey Lang (~30km buffer)
# Original AOI center: 105.619°E, 13.174°N
SEARCH_WEST  = 104.5
SEARCH_EAST  = 106.5
SEARCH_SOUTH = 12.5
SEARCH_NORTH = 14.0

print("Scanning wider Prey Lang region for 2021-2023 loss pixels...")
print(f"Search area: {SEARCH_WEST}°E–{SEARCH_EAST}°E, {SEARCH_SOUTH}°N–{SEARCH_NORTH}°N\n")

with rasterio.open('data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif') as src:
    win = from_bounds(SEARCH_WEST, SEARCH_SOUTH, SEARCH_EAST, SEARCH_NORTH, src.transform)
    data = src.read(1, window=win)
    
    transform = src.window_transform(win)
    res = abs(src.transform.a)

    print(f"Scan window: {data.shape[1]} x {data.shape[0]} pixels")
    
    for target_year in [2021, 2022, 2023]:
        encoded = target_year - 2000
        ys, xs = np.where(data == encoded)
        count = len(ys)
        print(f"\nYear {target_year}: {count} loss pixels found in search area")
        
        if count > 0:
            # Convert pixel coords back to geographic coordinates
            lons = transform.c + xs * transform.a + res / 2
            lats = transform.f + ys * transform.e - res / 2

            # Find the densest cluster (bin into 0.05° cells)
            bin_size = 0.05
            lon_bins = np.floor(lons / bin_size) * bin_size
            lat_bins = np.floor(lats / bin_size) * bin_size
            
            from collections import Counter
            bins = Counter(zip(lon_bins.tolist(), lat_bins.tolist()))
            top3 = bins.most_common(3)
            
            print(f"  Top hotspot cells for {target_year}:")
            for (lon_b, lat_b), cnt in top3:
                print(f"    -> Center ~({lon_b+bin_size/2:.3f}E, {lat_b+bin_size/2:.3f}N): {cnt} pixels")
                # Suggest an AOI box
                pad = 0.025
                print(f"      Suggested AOI bbox: [{lon_b-pad:.4f}, {lat_b-pad:.4f}, {lon_b+bin_size+pad:.4f}, {lat_b+bin_size+pad:.4f}]")

# Also: inspect the exact current AOI for ALL years (not just 2021-2023)
print("\n\n=== Current AOI — Loss by year (ALL years) ===")
with rasterio.open('data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif') as src:
    win = from_bounds(105.605, 13.160, 105.633, 13.188, src.transform)
    aoi = src.read(1, window=win)
    unique, counts = np.unique(aoi, return_counts=True)
    for v, c in zip(unique, counts):
        if v == 0:
            yr = "no-loss"
        elif v == 255:
            yr = "nodata"
        else:
            yr = str(2000 + int(v))
        if v != 0:  # skip the no-loss dominant value
            print(f"  value {v:3d} -> year {yr}: {c} pixels")
