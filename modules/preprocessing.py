# modules/preprocessing.py

import geopandas as gpd
import os
import numpy as np
from rasterio import features
from shapely.geometry import box
from rasterio.transform import from_origin


def load_shapefiles(folder_path):
    """
    Memuat semua shapefile permukiman dalam folder berdasarkan nama tahun.
    Return: dict {2020: GeoDataFrame, 2021: GeoDataFrame, ...}
    """
    shapefiles = {}
    for file in os.listdir(folder_path):
        if file.endswith(".shp"):
            year = int(''.join(filter(str.isdigit, file)))
            gdf = gpd.read_file(os.path.join(folder_path, file))
            shapefiles[year] = gdf
    return shapefiles


def convert_to_grid(gdf, resolution=100, bounds=None):
    if gdf is None or gdf.empty:
        print("⚠️ GeoDataFrame kosong!")
        return None

    # 🔍 Gunakan kolom 'Filter' saja secara konsisten
    if 'Filter' not in gdf.columns:
        print("❌ Kolom 'Filter' tidak ditemukan dalam data.")
        return None

    # 🔍 Filter hanya 'Kawasan Terbangun' (case-insensitive)
    gdf = gdf[gdf['Filter'].astype(str).str.lower().str.strip() == 'kawasan terbangun'].copy()
    

    if gdf.empty:
        print("⚠️ Tidak ada fitur dengan Filter == 'Kawasan Terbangun'")
        return None

    # ✅ Pastikan CRS sudah projected (EPSG:32751 = UTM zona Manado)
    if not gdf.crs:
        print("⚠️ CRS tidak tersedia.")
        return None
    if not gdf.crs.is_projected:
        gdf = gdf.to_crs(epsg=32751)

    # ✅ Perbaiki geometri invalid (penting!)
    if not gdf.geometry.is_valid.all():
        print("⚠️ Ada geometri invalid, memperbaiki dengan buffer(0)...")
        gdf["geometry"] = gdf["geometry"].buffer(0)

    # Hapus geometri kosong atau tanpa luas
    gdf = gdf[
        gdf.geometry.notnull() &
        gdf.geometry.is_valid &
        ~gdf.geometry.is_empty &
        (gdf.geometry.area > 0)
    ]

    if gdf.empty:
        print("⚠️ Semua geometri rusak atau tidak valid setelah perbaikan.")
        return None

    # ✅ Gunakan bounds umum kalau tersedia
    if bounds:
        xmin, ymin, xmax, ymax = bounds
    else:
        xmin, ymin, xmax, ymax = gdf.total_bounds

    width = int((xmax - xmin) / resolution)
    height = int((ymax - ymin) / resolution)

    if width <= 0 or height <= 0:
        print("⚠️ Ukuran grid invalid.")
        return None
    
    transform = from_origin(xmin, ymax, resolution, resolution)

    shapes = ((geom, 1) for geom in gdf.geometry)

    try:
        from rasterio import features
        raster = features.rasterize(
            shapes=shapes,
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.uint8
        )
        return raster
    except Exception as e:
        print(f"❌ Gagal rasterisasi: {e}")
        return None


def get_common_bounds(gdf_dict):
    """
    Ambil batas terluas (xmin, ymin, xmax, ymax) dari semua GeoDataFrame.
    """
    xmin_list, ymin_list, xmax_list, ymax_list = [], [], [], []

    for gdf in gdf_dict.values():
        if not gdf.empty:
            bounds = gdf.total_bounds
            xmin_list.append(bounds[0])
            ymin_list.append(bounds[1])
            xmax_list.append(bounds[2])
            ymax_list.append(bounds[3])

    xmin = min(xmin_list)
    ymin = min(ymin_list)
    xmax = max(xmax_list)
    ymax = max(ymax_list)

    return xmin, ymin, xmax, ymax