import streamlit as st

from modules.ca_model import learn_threshold_from_history
from modules.ca_model import run_ca_model_multistep
from modules.visualization import show_prediction_map, plot_trend, show_growth_comparison
from modules.preprocessing import get_common_bounds, load_precomputed_grids, load_shapefiles

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

shapefile_dir = "data/shapefile/"
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

     
# ==== Halaman Visualisasi Tahun Historis ====
elif st.session_state.page == "visualisasi":
    left, center, right = st.columns([1, 6, 1])
    with center:
        view_year = st.session_state.view_year
        st.title(f"Visualisasi Pertumbuhan Permukiman Tahun {view_year}")        

        st.button("⬅️ Kembali ke Beranda", on_click=back_to_home)

        common_bounds = get_common_bounds(gdf_by_year)
        with st.spinner("🔄 Mengonversi data ke grid..."):
            precomputed_grids = load_precomputed_grids()
            grid_before = precomputed_grids.get(view_year - 1)
            grid_after = precomputed_grids.get(view_year)

        if grid_before is not None and grid_after is not None:            

            # Tampilkan dua peta berdampingan: sebelum dan sesudah
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"### Permukiman Tahun {view_year - 1}")
                show_prediction_map(grid_before, grid_before, "", bounds=common_bounds)

            with col2:
                st.markdown(f"### Permukiman Tahun {view_year}")
                show_growth_comparison(grid_before, grid_after, "", bounds=common_bounds)                
                    
            # Tambahkan keterangan
            st.markdown("#### Keterangan:")
            st.markdown("""
            <ul>            
                <li><span style="color:green;"><strong>Hijau</strong></span>: Baru terbangun </li>
                <li><span style="color:red;"><strong>Merah</strong></span>: Tetap terbangun </li>
            </ul>
            """, unsafe_allow_html=True)
        else:
            st.warning("Data grid untuk tahun tersebut tidak tersedia.")


# ==== Halaman Prediksi ====
elif st.session_state.page == "prediksi":
    left, center, right = st.columns([1, 2, 1])
    with center:
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

         # Tambahkan keterangan
        st.markdown("#### Keterangan:")
        st.markdown("""
        <ul>            
            <li><span style="color:green;"><strong>Hijau</strong></span>: Baru terbangun </li>
            <li><span style="color:red;"><strong>Merah</strong></span>: Tetap terbangun </li>
        </ul>
        """, unsafe_allow_html=True)    

