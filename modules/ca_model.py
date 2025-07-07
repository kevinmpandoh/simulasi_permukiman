# modules/ca_model.py

import numpy as np
from scipy.ndimage import convolve
import streamlit as st

from modules.preprocessing import convert_to_grid, get_common_bounds

def run_ca_model(grid, threshold=5):
    """
    Menjalankan simulasi CA satu langkah untuk prediksi permukiman.
    Jika sebuah sel kosong (0) memiliki tetangga terbangun (1) ≥ threshold, maka menjadi 1.
    """
    # Kernel tetangga Moore 3x3 (tidak termasuk diri sendiri)
    kernel = np.array([
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1]
    ])

    # Hitung jumlah tetangga yang sudah terbangun
    neighbors = convolve(grid, kernel, mode='constant', cval=0)

    # Aturan pertumbuhan CA: hanya untuk sel kosong (0) dengan tetangga ≥ threshold
    growth = (grid == 0) & (neighbors >= threshold)

    # Salin grid lama, ubah yang tumbuh jadi 1
    new_grid = grid.copy()
    new_grid[growth] = 1

    return new_grid

def learn_threshold_from_history(precomputed_grids):
    """
    Menemukan threshold terbaik untuk CA berdasarkan data grid tahun 2020–2024.
    Membandingkan hasil prediksi terhadap grid aktual, lalu mencari threshold dengan error terkecil.
    """
    thresholds = range(1, 9)
    total_errors = {}

    for t in thresholds:
        total_error = 0
        for year in range(2020, 2024):  # Tahun 2020–2023
            grid_start = precomputed_grids.get(year)
            grid_target = precomputed_grids.get(year + 1)

            if grid_start is None or grid_target is None:
                continue

            pred = run_ca_model(grid_start, threshold=t)
            error = np.sum(np.abs(pred - grid_target))  # Total sel yang salah
            total_error += error

        total_errors[t] = total_error

    best_threshold = min(total_errors, key=total_errors.get)
    return best_threshold


@st.cache_data
def run_ca_model_multistep(initial_grid, threshold, steps):
    """
    Menjalankan CA untuk beberapa tahun ke depan (steps kali).
    """
    current = initial_grid.copy()
    for _ in range(steps):
        current = run_ca_model(current, threshold)
    return current