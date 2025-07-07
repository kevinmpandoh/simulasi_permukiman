import os
import numpy as np
from modules.preprocessing import load_shapefiles, convert_to_grid, get_common_bounds

# Folder shapefile dan folder output grid
shapefile_dir = "data/"
output_dir = "precomputed_grids/"
os.makedirs(output_dir, exist_ok=True)

# Load semua shapefile
gdf_by_year = load_shapefiles(shapefile_dir)
common_bounds = get_common_bounds(gdf_by_year)

for year, gdf in gdf_by_year.items():
    print(f"🔄 Konversi {year}...")
    grid = convert_to_grid(gdf, bounds=common_bounds)
    if grid is not None:
        np.save(os.path.join(output_dir, f"grid_{year}.npy"), grid)
        print(f"✅ grid_{year}.npy disimpan.")
    else:
        print(f"❌ Grid tahun {year} gagal dikonversi.")
