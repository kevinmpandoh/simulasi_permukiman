import streamlit as st

from modules.preprocessing import load_shapefiles, convert_to_grid
from modules.ca_model import learn_threshold_from_history
from modules.ca_model import run_ca_model_multistep
from modules.visualization import show_prediction_map, plot_trend
from modules.preprocessing import convert_to_grid, get_common_bounds

st.set_page_config(page_title="Simulasi Permukiman", layout="wide")

# ==== Setup Session State ====
if "page" not in st.session_state:
    st.session_state.page = "home"

if "selected_year" not in st.session_state:
    st.session_state.selected_year = 2025

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

        st.subheader("Prediksi Permukiman")
        pred_year = st.number_input("Masukkan Tahun Prediksi (≥ 2025)", min_value=2025, max_value=2028, value=2025, step=1)

        

        if st.button("Lihat Prediksi"):
            st.session_state.selected_year = pred_year
            st.session_state.page = "prediksi"

# ==== Halaman Prediksi ====
elif st.session_state.page == "prediksi":
    pred_year = st.session_state.selected_year
    st.set_page_config(page_title=f"Prediksi {pred_year}", layout="centered")
    st.title(f"Prediksi Permukiman Tahun {pred_year}")
    

    # Ambil batas umum (agar grid konsisten)
    common_bounds = get_common_bounds(gdf_by_year)

    # Belajar threshold optimal dari data 2020–2024
    with st.spinner("🔍 Belajar threshold dari data historis..."):
        threshold = learn_threshold_from_history(gdf_by_year, bounds=common_bounds)
        st.success(f"📊 Threshold optimal hasil pelatihan: {threshold}")

    with st.spinner("🔄 Mengonversi permukiman 2024 ke grid..."):
        grid_2024 = convert_to_grid(gdf_by_year[2024], bounds=common_bounds)        

    # Jalankan simulasi multi-step CA
    steps = pred_year - 2024
    with st.spinner(f"🚀 Menjalankan prediksi hingga tahun {pred_year} ({steps} langkah)..."):
        predicted_grid = run_ca_model_multistep(grid_2024, threshold, steps)

    # Tampilkan hasil
    show_prediction_map(grid_2024, predicted_grid, f"Prediksi Permukiman Tahun {pred_year}", bounds=common_bounds)
    

    st.markdown("---")
    st.button("⬅️ Kembali ke Beranda", on_click=back_to_home)

