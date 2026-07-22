import rasterio
import numpy as np

with rasterio.open('data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif') as src:
    print('CRS:', src.crs)
    print('Driver:', src.driver)
    print('Size:', src.width, 'x', src.height, 'pixels')
    print('Bounds:', src.bounds)
    print('Resolution (deg):', round(abs(src.transform.a), 7), 'x', round(abs(src.transform.e), 7))
    print('NoData:', src.nodata)
    print('Bands:', src.count)

    # Sample a small chunk to avoid reading 600MB at once
    data = src.read(1, window=rasterio.windows.Window(0, 0, min(src.width, 2000), min(src.height, 2000)))
    valid = data[data != 255]
    print('\n--- Sample window (top-left 2000x2000 pixels) ---')
    print('Valid pixels in sample:', len(valid))
    unique, counts = np.unique(valid, return_counts=True)
    print('Unique pixel values (value -> year):')
    for v, c in zip(unique, counts):
        yr = str(2000 + int(v)) if int(v) > 0 else 'no-loss'
        print(f'  value {v:3d} -> {yr:10s}  ({c} pixels)')

print('\n--- AOI region check ---')
# AOI bbox: lon 105.6053-105.6330, lat 13.1609-13.1879
with rasterio.open('data/raw/Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif') as src:
    # Convert AOI bbox to pixel window
    from rasterio.windows import from_bounds
    win = from_bounds(105.605, 13.160, 105.633, 13.188, src.transform)
    print('AOI window in raster pixels:', win)
    aoi_data = src.read(1, window=win)
    print('AOI data shape:', aoi_data.shape)
    print('AOI total pixels:', aoi_data.size)
    valid_aoi = aoi_data[aoi_data != 255]
    print('AOI valid pixels:', len(valid_aoi))
    if len(valid_aoi) > 0:
        u, c = np.unique(valid_aoi, return_counts=True)
        print('AOI pixel values:')
        for v, cnt in zip(u, c):
            yr = str(2000 + int(v)) if int(v) > 0 else 'no-loss'
            print(f'  value {v:3d} -> {yr}  ({cnt} pixels)')
    else:
        print('NO valid pixels in AOI! The AOI may be outside the raster extent.')
    print('\nRaster full bounds:', src.bounds)
    print('AOI bounds:        (105.605, 13.160, 105.633, 13.188)')
