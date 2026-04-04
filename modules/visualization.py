# modules/visualization.py

import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors
import io
import base64
from pyproj import Transformer
import folium
from streamlit_folium import st_folium
from PIL import Image

def show_map(gdf, title="Peta Permukiman"):
    """
    Menampilkan GeoDataFrame (shapefile) sebagai peta di Streamlit.
    Mengambil centroid sebagai lat/lon.
    """
    st.subheader(title)

    # Ubah ke CRS WGS 84 (lat/lon)
    gdf_wgs = gdf.to_crs(epsg=4326)

    # Ambil titik tengah (centroid) dari geometri
    gdf_wgs["latitude"] = gdf_wgs.geometry.centroid.y
    gdf_wgs["longitude"] = gdf_wgs.geometry.centroid.x

    # Buat DataFrame hanya dengan lat/lon
    df_map = gdf_wgs[["latitude", "longitude"]]

    # Tampilkan peta
    st.map(df_map)

    # Opsi: tampilkan tabel aslinya
    st.dataframe(gdf_wgs.drop(columns="geometry"))

def show_prediction_map(before, after, title, bounds=None):
    if before is None or after is None:
        st.error("Grid tidak valid.")
        return

    # === Mask ===
    mask_still = ((before == 1) & (after == 1)).astype(np.uint8)   # Tetap terbangun
    mask_new = ((before == 0) & (after == 1)).astype(np.uint8)     # Baru tumbuh
    mask_base = (before == 1).astype(np.uint8)                     # Peta dasar 2024

    # === Fungsi bantu buat overlay transparan ===
    def create_overlay_image(mask, color):
        cmap = mcolors.ListedColormap(['none', color])
        norm = mcolors.BoundaryNorm([0, 0.5, 1], cmap.N)
        fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
        ax.imshow(mask, cmap=cmap, norm=norm)
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    # overlay_still = create_overlay_image(mask_still, "green")
    # overlay_new = create_overlay_image(mask_new, "red")
    # overlay_base = create_overlay_image(mask_base, "gray")
    overlay_base = create_overlay_image(mask_base, "gray")       # Abu-abu → Dasar
    overlay_still = create_overlay_image(mask_still, "red")       # Merah → Tetap terbangun
    overlay_new = create_overlay_image(mask_new, "limegreen")   # Hijau → Baru terbangun

    # === Transformasi koordinat EPSG:32651 → WGS84 ===
    if bounds is None:
        st.error("Bounds tidak tersedia.")
        return

    transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
    xmin, ymin, xmax, ymax = bounds
    (xmin_lon, ymin_lat) = transformer.transform(xmin, ymin)
    (xmax_lon, ymax_lat) = transformer.transform(xmax, ymax)
    bounds_latlon = [[ymin_lat, xmin_lon], [ymax_lat, xmax_lon]]

    # === Tampilkan di peta interaktif ===
    m = folium.Map(
        location=[(ymin_lat + ymax_lat)/2, (xmin_lon + xmax_lon)/2],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    # 🏙️ Dasar (abu-abu)
    folium.raster_layers.ImageOverlay(
        image=overlay_base,
        bounds=bounds_latlon,
        opacity=0.3,
        name="Permukiman 2024 (Dasar)"
    ).add_to(m)

    # 🟩 Baru tumbuh (0→1) → HIJAU → tampilkan dulu agar tidak tertutup
    folium.raster_layers.ImageOverlay(
        image=overlay_new,
        bounds=bounds_latlon,
        opacity=0.6,
        name="Baru Terbangun (0→1)"
    ).add_to(m)

    # 🟥 Tetap terbangun (1→1) → MERAH
    folium.raster_layers.ImageOverlay(
        image=overlay_still,
        bounds=bounds_latlon,
        opacity=0.5,
        name="Tetap Terbangun (1→1)"
    ).add_to(m)

    # # 🏙️ Lapisan dasar permukiman 2024
    # folium.raster_layers.ImageOverlay(
    #     image=overlay_base,
    #     bounds=bounds_latlon,
    #     opacity=0.3,
    #     name="Permukiman 2024 (Dasar)"
    # ).add_to(m)

    # # ✅ Tetap terbangun (1→1)
    # folium.raster_layers.ImageOverlay(
    #     image=overlay_still,
    #     bounds=bounds_latlon,
    #     opacity=0.6,
    #     name="Tetap Terbangun (1→1)"
    # ).add_to(m)

    # # 🟥 Baru terbangun (0→1)
    # folium.raster_layers.ImageOverlay(
    #     image=overlay_new,
    #     bounds=bounds_latlon,
    #     opacity=0.7,
    #     name="Baru Terbangun (0→1)"
    # ).add_to(m)

    folium.LayerControl().add_to(m)

    st.markdown(f"### {title}")
    st_folium(m, width=700, height=500)
    

def plot_trend(gdf_by_year):
    st.subheader("📈 Tren Pertumbuhan Permukiman")

    years = []
    areas = []

    for year in sorted(gdf_by_year.keys()):
        gdf = gdf_by_year[year]

        # Filter hanya kawasan terbangun
        gdf = gdf[gdf['Filter'].astype(str).str.lower().str.strip() == 'kawasan terbangun'].copy()

        # Pastikan CRS projected sebelum hitung area
        if not gdf.crs or not gdf.crs.is_projected:
            gdf = gdf.to_crs(epsg=32751)

        # Hitung luas total (m²) → konversi ke hektar (/10_000)
        total_area_ha = gdf.geometry.area.sum() / 10_000
        years.append(year)
        areas.append(total_area_ha)

    # Plot
    fig, ax = plt.subplots()
    ax.plot(years, areas, marker="o", color="green")
    ax.set_xlabel("Tahun")
    ax.set_ylabel("Luas Permukiman (Ha)")
    ax.set_title("Tren Luas Permukiman Terbangun per Tahun")
    st.pyplot(fig)


def plot_trend_from_grids(precomputed_grids, cell_size=100):
    st.subheader("📈 Tren Pertumbuhan Permukiman (berdasarkan Grid)")

    years = sorted(precomputed_grids.keys())
    areas_ha = []

    for year in years:
        grid = precomputed_grids[year]
        built_cells = np.sum(grid == 1)
        area_m2 = built_cells * (cell_size ** 2)
        area_ha = area_m2 / 10_000
        areas_ha.append(area_ha)

    fig, ax = plt.subplots()
    ax.plot(years, areas_ha, marker="o", color="green")
    ax.set_xlabel("Tahun")
    ax.set_ylabel("Luas Permukiman (Ha)")
    ax.set_title("Tren Luas Permukiman Terbangun per Tahun (Grid)")
    st.pyplot(fig)

def show_growth_comparison(before, after, title, bounds=None):
    if before is None or after is None:
        st.error("Grid tidak valid.")
        return

    # === Mask ===
    mask_still = ((before == 1) & (after == 1)).astype(np.uint8)   # Tetap terbangun
    mask_new = ((before == 0) & (after == 1)).astype(np.uint8)     # Baru tumbuh

    # === Fungsi bantu buat overlay transparan ===
    def create_overlay_image(mask, color):
        cmap = mcolors.ListedColormap(['none', color])
        norm = mcolors.BoundaryNorm([0, 0.5, 1], cmap.N)
        fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
        ax.imshow(mask, cmap=cmap, norm=norm)
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    overlay_still = create_overlay_image(mask_still, "red")
    overlay_new = create_overlay_image(mask_new, "green")

    # === Transformasi koordinat EPSG:32651 → WGS84 ===
    if bounds is None:
        st.error("Bounds tidak tersedia.")
        return

    xmin, ymin, xmax, ymax = bounds
    transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
    (xmin_lon, ymin_lat) = transformer.transform(xmin, ymin)
    (xmax_lon, ymax_lat) = transformer.transform(xmax, ymax)
    bounds_latlon = [[ymin_lat, xmin_lon], [ymax_lat, xmax_lon]]

    # === Tampilkan di peta interaktif ===
    m = folium.Map(
        location=[(ymin_lat + ymax_lat)/2, (xmin_lon + xmax_lon)/2],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    # ✅ Tetap terbangun (1→1)
    folium.raster_layers.ImageOverlay(
        image=overlay_still,
        bounds=bounds_latlon,
        opacity=0.6,
        name="Tetap Terbangun (1→1)"
    ).add_to(m)

    # 🟩 Baru terbangun (0→1)
    folium.raster_layers.ImageOverlay(
        image=overlay_new,
        bounds=bounds_latlon,
        opacity=0.7,
        name="Baru Terbangun (0→1)"
    ).add_to(m)

    folium.LayerControl().add_to(m)

    st.markdown(f"### {title}")
    st_folium(m, width=700, height=500)

def show_base_map(before, bounds=None):
    if before is None:
        st.error("Grid tidak valid.")
        return

    # === Mask ===    
    base_mask = ((before == 1)).astype(np.uint8)    # Semua yang terbangun di salah satu tahun 

    # === Fungsi bantu buat overlay transparan ===
    def create_overlay_image(mask, color):
        cmap = mcolors.ListedColormap(['none', color])
        norm = mcolors.BoundaryNorm([0, 0.5, 1], cmap.N)
        fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
        ax.imshow(mask, cmap=cmap, norm=norm)
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    # Sesuaikan warna dengan keterangan legend Anda    
    overlay_base = create_overlay_image(base_mask, "red")  # Semua terbangun = Abu-abu muda    

    # === Transformasi koordinat EPSG:32651 → WGS84 ===
    if bounds is None:
        st.error("Bounds tidak tersedia.")
        return

    transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
    xmin, ymin, xmax, ymax = bounds
    (xmin_lon, ymin_lat) = transformer.transform(xmin, ymin)
    (xmax_lon, ymax_lat) = transformer.transform(xmax, ymax)
    bounds_latlon = [[ymin_lat, xmin_lon], [ymax_lat, xmax_lon]]

    # === Tampilkan di peta interaktif ===
    m = folium.Map(
        location=[(ymin_lat + ymax_lat)/2, (xmin_lon + xmax_lon)/2],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    folium.raster_layers.ImageOverlay(
        image=overlay_base,
        bounds=bounds_latlon,
        opacity=0.7, # Opacity rendah agar tidak mengganggu warna lain
        name="Semua Terbangun",
        zindex=2
    ).add_to(m)

    folium.LayerControl().add_to(m) 
    st_folium(m, width=700, height=500)

def show_comparison_map(before, after, title="", bounds=None):
    if before is None or after is None:
        st.error("Grid tidak valid.")
        return

    # === Mask ===
    mask_still = ((before == 1) & (after == 1)).astype(np.uint8)   # Tetap terbangun -> Merah
    mask_new = ((before == 0) & (after == 1)).astype(np.uint8)     # Baru tumbuh -> Hijau
    
    # Mask KHUSUS untuk area yang ada di tahun sebelumnya tapi "hilang" di data tahun ini
    mask_lost = ((after == 1) ).astype(np.uint8)    # Hilang / Beda Data -> Abu-abu

    # === Fungsi bantu buat overlay transparan ===
    def create_overlay_image(mask, color):
        cmap = mcolors.ListedColormap(['none', color])
        norm = mcolors.BoundaryNorm([0, 0.5, 1], cmap.N)
        fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
        ax.imshow(mask, cmap=cmap, norm=norm)
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    # Buat overlay gambar
    overlay_still = create_overlay_image(mask_still, "red") 
    overlay_new = create_overlay_image(mask_new, "green")  
    overlay_lost = create_overlay_image(mask_lost, "green") 

    # === Transformasi koordinat EPSG:32651 → WGS84 ===
    if bounds is None:
        st.error("Bounds tidak tersedia.")
        return

    transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
    xmin, ymin, xmax, ymax = bounds
    (xmin_lon, ymin_lat) = transformer.transform(xmin, ymin)
    (xmax_lon, ymax_lat) = transformer.transform(xmax, ymax)
    bounds_latlon = [[ymin_lat, xmin_lon], [ymax_lat, xmax_lon]]

    # === Tampilkan di peta interaktif ===
    m = folium.Map(
        location=[(ymin_lat + ymax_lat)/2, (xmin_lon + xmax_lon)/2],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    # ⬜ Area yang hilang di data terbaru (Abu-abu)
    folium.raster_layers.ImageOverlay(
        image=overlay_lost,
        bounds=bounds_latlon,
        opacity=0.4, 
        name="Hilang (Beda Data)"
    ).add_to(m)

    # 🟥 Tetap terbangun (1→1) → MERAH
    folium.raster_layers.ImageOverlay(
        image=overlay_still,
        bounds=bounds_latlon,
        opacity=0.7, 
        name="Tetap Terbangun"
    ).add_to(m)

    # 🟩 Baru tumbuh (0→1) → HIJAU
    folium.raster_layers.ImageOverlay(
        image=overlay_new,
        bounds=bounds_latlon,
        opacity=0.9, # Opacity tinggi (0.9) agar titik hijau kecil dari 2024 sangat terlihat
        name="Baru Terbangun"
    ).add_to(m)

    folium.LayerControl().add_to(m)
    
    if title:
        st.markdown(f"### {title}")
    st_folium(m, width=700, height=500)
    