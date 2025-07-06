# modules/visualization.py

import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import pydeck as pdk
import matplotlib.colors as mcolors
import folium
from streamlit_folium import st_folium
from PIL import Image
import io
import base64

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



# def show_prediction_map(before, after, title="Peta Perubahan Permukiman"):
#     """
#     Menampilkan perbandingan dua grid permukiman dengan warna:
#     - Merah (2): 0 → 1 (baru terbangun)
#     - Hijau (1): 1 → 1 (tetap terbangun)
#     - Abu (0): sisanya
#     """
#     st.subheader(title)

#     # Buat grid perubahan:
#     change_map = np.zeros_like(before)

#     # Tetap terbangun: 1 -> 1
#     change_map[(before == 1) & (after == 1)] = 1

#     # Baru terbangun: 0 -> 1
#     change_map[(before == 0) & (after == 1)] = 2

#     # Warna:
#     cmap = mcolors.ListedColormap(["lightgrey", "green", "red"])
#     labels = ["Kosong / Tetap Kosong", "Tetap Terbangun", "Baru Terbangun"]

#     fig, ax = plt.subplots(figsize=(8, 8))
#     im = ax.imshow(change_map, cmap=cmap, interpolation="nearest")
#     ax.set_title("Perubahan Permukiman")
#     ax.axis("off")

#     # Buat legenda manual
#     from matplotlib.patches import Patch
#     legend_elements = [
#         Patch(facecolor='lightgrey', label=labels[0]),
#         Patch(facecolor='green', label=labels[1]),
#         Patch(facecolor='red', label=labels[2]),
#     ]
#     ax.legend(handles=legend_elements, loc='upper right')

#     st.pyplot(fig)

def show_prediction_map(before, after, title, bounds=None, resolution=100):
    if before is None or after is None:
        st.error("Grid tidak valid.")
        return

    diff = after - before
    change_mask = np.where(diff == 1, 1, 0)  # Hanya tunjukkan pertumbuhan (0 → 1)

    if np.sum(change_mask) == 0:
        st.warning("Tidak ada perubahan terdeteksi.")
        return

    # === Buat gambar transparan ===
    cmap = mcolors.ListedColormap(['none', 'red'])  # 0 = transparan, 1 = merah
    norm = mcolors.BoundaryNorm([0, 0.5, 1], cmap.N)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
    ax.imshow(change_mask, cmap=cmap, norm=norm)
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    overlay_image = Image.open(buf)

    # === Transformasi koordinat bounds ke EPSG:4326 ===
    if bounds is None:
        st.error("Bounds tidak tersedia.")
        return

    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:32651", "EPSG:4326", always_xy=True)
    xmin, ymin, xmax, ymax = bounds
    (xmin_lon, ymin_lat) = transformer.transform(xmin, ymin)
    (xmax_lon, ymax_lat) = transformer.transform(xmax, ymax)
    bounds_latlon = [[ymin_lat, xmin_lon], [ymax_lat, xmax_lon]]

    png_data = buf.getvalue()
    data_url = 'data:image/png;base64,' + base64.b64encode(png_data).decode('utf-8')

    # === Tampilkan di Folium ===
    m = folium.Map(location=[(ymin_lat + ymax_lat) / 2, (xmin_lon + xmax_lon) / 2], zoom_start=12, tiles="CartoDB positron")

    folium.raster_layers.ImageOverlay(
            image=data_url,
            bounds=bounds_latlon,
            opacity=0.7,
            name="Perubahan Permukiman"
    ).add_to(m)

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
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(years, areas, marker="o", color="green")
    ax.set_xlabel("Tahun")
    ax.set_ylabel("Luas Permukiman (Ha)")
    ax.set_title("Tren Luas Permukiman Terbangun per Tahun")
    st.pyplot(fig)
