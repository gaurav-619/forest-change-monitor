"""
Helper script to execute the Forest Change pipeline manually.

This script demonstrates how to run the core pipeline bypassing the Streamlit UI.
The Hansen GFC raster must be downloaded and placed in the data/raw directory first.
"""
import sys
from pathlib import Path
from forest_change.process_loss import run_full_pipeline

def main():
    root_dir = Path(__file__).resolve().parent.parent
    
    aoi_path = root_dir / "data" / "aoi" / "demo_site.geojson"
    lossyear_path = root_dir / "data" / "raw" / "Hansen_GFC-2023-v1.11_lossyear_20N_100E.tif"
    output_dir = root_dir / "outputs"
    
    if not lossyear_path.exists():
        print(f"Error: Raw raster not found at {lossyear_path}")
        print("Please download it according to the instructions in the README.")
        sys.exit(1)
        
    print(f"Running pipeline for AOI: {aoi_path.name}...")
    run_full_pipeline(
        aoi_path=aoi_path,
        lossyear_path=lossyear_path,
        output_dir=output_dir,
        years=(2021, 2022, 2023),
        utm_epsg=32648
    )
    print("Pipeline completed successfully. Check the outputs/ directory.")

if __name__ == "__main__":
    main()
