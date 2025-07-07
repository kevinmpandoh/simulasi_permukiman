import streamlit as st

from modules.preprocessing import load_shapefiles, convert_to_grid
from modules.ca_model import learn_threshold_from_history
from modules.ca_model import run_ca_model_multistep
from modules.visualization import show_prediction_map, plot_trend, show_growth_comparison
from modules.preprocessing import convert_to_grid, get_common_bounds, load_precomputed_grids

st.set_page_config(page_title="Simulasi Permukiman", layout="wide")

# ==== Setup Session State ====
if "page" not in st.session_state:
    st.session_state.page = "home"

if "selected_year" not in st.session_state:
    st.session_state.selected_year = 2025

if "view_year" not in st.session_state:
    st.session_state.view_year = 2020

# ==== Navigasi ====
def go_to_prediksi():
    st.session_state.page = "prediksi"

def back_to_home():
    st.session_state.page = "home"

shapefile_dir = "data/"
gdf_by_year = load_shapefiles(shapefile_dir)

# ==== Halaman Beranda ====
if st.session_state.page == "home":
    st.title("Simulasi Perkembangan Permukiman Kota Manado")

    col1, spacer, col2 = st.columns([1.4, 0.4, 1.4])

    with col1:
        plot_trend(gdf_by_year)

    with col2:

        st.subheader("Visualisasi Tahun Sebelumnya")
        view_year = st.selectbox("Pilih Tahun (2021–2024)", options=[2021, 2022, 2023, 2024])
        if st.button("Lihat Perbandingan Tahun"):
            st.session_state.view_year = view_year
            st.session_state.page = "visualisasi"
            st.rerun()

        st.subheader("Prediksi Permukiman")
        pred_year = st.number_input("Masukkan Tahun Prediksi (≥ 2025)", min_value=2025, max_value=2035, value=2025, step=1)
        if st.button("Lihat Prediksi"):
            st.session_state.selected_year = pred_year
            st.session_state.page = "prediksi"
            st.rerun()

     

# ==== Halaman Prediksi ====
elif st.session_state.page == "prediksi":
    pred_year = st.session_state.selected_year
    st.title(f"Prediksi Permukiman Tahun {pred_year}")

    common_bounds = get_common_bounds(gdf_by_year)

    with st.spinner("🔍 Belajar threshold dari data historis..."):
        precomputed_grids = load_precomputed_grids()
        threshold = learn_threshold_from_history(precomputed_grids)
        st.success(f"📊 Threshold optimal hasil pelatihan: {threshold}")

    with st.spinner("🔄 Mengonversi permukiman 2024 ke grid..."):
        precomputed_grids = load_precomputed_grids()
        grid_2024 = precomputed_grids[2024]

    steps = pred_year - 2024
    with st.spinner(f"🚀 Menjalankan prediksi hingga tahun {pred_year} ({steps} langkah)..."):
        predicted_grid = run_ca_model_multistep(grid_2024, threshold, steps)

    st.markdown("---")
    st.button("⬅️ Kembali ke Beranda", on_click=back_to_home)
    show_prediction_map(grid_2024, predicted_grid, f"Prediksi Permukiman Tahun {pred_year}", bounds=common_bounds)

# ==== Halaman Visualisasi Tahun Historis ====
elif st.session_state.page == "visualisasi":
    view_year = st.session_state.view_year
    st.title(f"Visualisasi Pertumbuhan Permukiman Tahun {view_year}")

    common_bounds = get_common_bounds(gdf_by_year)
    with st.spinner("🔄 Mengonversi data ke grid..."):
        precomputed_grids = load_precomputed_grids()
        grid_before = precomputed_grids.get(view_year - 1)
        grid_after = precomputed_grids.get(view_year)

    if grid_before is not None and grid_after is not None:
        show_growth_comparison(grid_before, grid_after, f"Perbandingan Permukiman Tahun {view_year - 1} ke {view_year}", bounds=common_bounds)
    else:
        st.warning("Data grid untuk tahun tersebut tidak tersedia.")

    st.button("⬅️ Kembali ke Beranda", on_click=back_to_home)
