import argparse
import sys
from pathlib import Path
import json
import rasterio
import pandas as pd
import numpy as np

def validate_pipeline(qa_json_path="outputs/yearly_loss_summary.json"):
    qa_path = Path(qa_json_path)
    if not qa_path.exists():
        print(f"Error: {qa_path} not found. Run the pipeline first.")
        sys.exit(1)

    with open(qa_path) as f:
        qa_data = json.load(f)

    validations = qa_data.get("qa", {}).get("validations", {})
    if not validations:
        print("Error: Validations section not found in QA metadata.")
        sys.exit(1)

    print("=== Pipeline Validation ===")
    all_passed = True
    
    # 1. Filename valid
    passed = validations.get("filename_valid", False)
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] Data-lineage check: filename includes GFC-2023-v1.11_lossyear_20N_100E.tif")
    
    # 2. Source bounds contain AOI
    passed = validations.get("source_bounds_contain_aoi", False)
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] source bounds contain the AOI")
    
    # 3. Full raster contains values 21, 22, 23
    passed = validations.get("full_raster_contains_21_22_23", False)
    all_passed &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] full raster contains values 21, 22, and 23")
    
    # 4. Clipped AOI contains values reported in CSV
    # Strengthened validation: explicitly read CSV and clipped raster
    csv_path = qa_path.parent / "yearly_loss_summary.csv"
    tif_path = qa_path.parent / "clipped_lossyear.tif"
    
    if not csv_path.exists() or not tif_path.exists():
        print("[FAIL] clipped AOI contains the values reported in the summary CSV (missing files)")
        all_passed = False
    else:
        df = pd.read_csv(csv_path)
        pixel_area_m2 = qa_data["qa"]["pixel_area_m2"]
        csv_passed = True
        
        with rasterio.open(tif_path) as src:
            clipped = src.read(1)
            
        for year in [2021, 2022, 2023]:
            encoded = year - 2000
            raster_count = int(np.sum(clipped == encoded))
            
            # Check CSV row exists
            row = df[df["year"] == year]
            if row.empty:
                csv_passed = False
                print(f"  -> Missing year {year} in CSV")
                continue
                
            csv_count = int(row["loss_pixels"].iloc[0])
            csv_ha = float(row["loss_area_ha"].iloc[0])
            
            computed_ha = round(raster_count * pixel_area_m2 / 10_000, 2)
            
            if raster_count != csv_count:
                csv_passed = False
                print(f"  -> Year {year}: pixel count mismatch (Raster: {raster_count}, CSV: {csv_count})")
            if computed_ha != csv_ha:
                csv_passed = False
                print(f"  -> Year {year}: hectare mismatch (Computed: {computed_ha}, CSV: {csv_ha})")
                
        all_passed &= csv_passed
        print(f"[{'PASS' if csv_passed else 'FAIL'}] clipped AOI contains the values reported in the summary CSV")

    print("\nResult: " + ("ALL PASSED" if all_passed else "VALIDATION FAILED"))
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate pipeline output via QA report.")
    parser.add_argument("--qa-file", default="outputs/yearly_loss_summary.json", help="Path to QA JSON")
    args = parser.parse_args()
    validate_pipeline(args.qa_file)
