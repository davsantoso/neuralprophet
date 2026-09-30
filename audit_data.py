"""Cetak statistik deskriptif dari 114 bulan penelitian."""

from cargo_forecast.data import descriptive_stats, load_bps_data


if __name__ == "__main__":
    print(descriptive_stats(load_bps_data()).to_string(index=False, float_format=lambda value: f"{value:.2f}"))

