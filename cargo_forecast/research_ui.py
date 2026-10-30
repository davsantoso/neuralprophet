"""Render precomputed supplementary research; opening the UI never fits models."""

import json
import io
from pathlib import Path
import zipfile

import altair as alt
import pandas as pd
import streamlit as st

from .modeling import EPOCHS
from .significance import LOSS_LABELS, PROTOCOLS, verdict


METHODS = {"neuralprophet": "NeuralProphet", "last_month": "Bulan sebelumnya",
           "same_month_last_year": "Bulan sama tahun lalu"}
# Figures that cover both series belong in each per-series bundle.
SHARED_FIGURES = ("data_114_bulan.png", "uji_signifikansi.csv")


@st.cache_data
def figures_bundle(target):
    folder = Path(__file__).resolve().parents[1] / "artifacts/figures"
    paths = sorted(folder.glob(f"{target}_*"))
    if not paths:
        return None
    paths += [folder / name for name in SHARED_FIGURES if (folder / name).exists()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.writestr(path.name, path.read_bytes())
    return buffer.getvalue()


def render_significance(target, significance, source):
    if significance is None:
        st.info("Uji signifikansi Diebold-Mariano belum tersedia untuk versi hasil ini.")
        return
    if significance.get("source") != source:
        st.error("Uji signifikansi tidak cocok dengan snapshot dan laporan penelitian.")
        return
    with st.expander("Uji signifikansi Diebold-Mariano · analisis tambahan", expanded=False):
        st.write("Uji ini memeriksa apakah selisih galat NeuralProphet dan aturan pembanding cukup besar untuk dibedakan dari variasi acak. Statistik DM dikoreksi menurut Harvey-Leybourne-Newbold, lalu dibandingkan dengan distribusi t berderajat bebas n − 1, dua sisi, α = 0,05.")
        rows = [{"Protokol": label, "Pembanding": METHODS[baseline], "Loss": LOSS_LABELS[loss], "n": item["n"],
                 "Rata-rata selisih loss": item["mean_loss_difference"], "DM*": item["dm_hln"],
                 "p-value": item["p_value"], "Kesimpulan": verdict(item)}
                for protocol, label in PROTOCOLS.items()
                for baseline, losses in significance["series"][target][protocol]["comparisons"].items()
                for loss, item in losses.items()]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Selisih loss = loss NeuralProphet dikurangi loss pembanding; nilai negatif berarti galat NeuralProphet lebih kecil. p ≥ 0,05 berarti tidak ada bukti perbedaan, bukan bukti bahwa kedua metode sama. Uji 18 dan 42 bulan sebagian beririsan dan jumlah perbandingannya banyak, sehingga hasil dibaca sebagai pola keseluruhan.")
        st.markdown("[Diebold dan Mariano (1995)](https://doi.org/10.1080/07350015.1995.10524599) · [Harvey, Leybourne, dan Newbold (1997)](https://doi.org/10.1016/S0169-2070(96)00719-4)")
        st.download_button("Unduh uji signifikansi (JSON)", json.dumps(significance, ensure_ascii=False, indent=2),
                           file_name="uji_signifikansi.json", mime="application/json")


def render_training_diagnostics(target, training, source):
    if training is None:
        st.info("Kurva loss dan sensitivitas epoch belum tersedia untuk versi hasil ini.")
        return
    if training.get("source") != source:
        st.error("Diagnostik pelatihan tidak cocok dengan snapshot dan laporan penelitian.")
        return
    item = training["series"][target]
    with st.expander("Kurva loss dan sensitivitas epoch · analisis tambahan", expanded=False):
        st.caption(f"Model dilatih ulang pada Januari 2017–Desember 2024 dengan lag {item['selected_n_lags']}, seed 42, dan {EPOCHS} epoch. Fit ulang ini mereproduksi 18 prediksi uji resmi (selisih maksimum {item['max_forecast_difference_ton']:.6f} ton).")
        curve = pd.DataFrame(item["loss_curve"])
        first, second = st.columns(2)
        first.altair_chart(alt.Chart(curve).mark_line().encode(x=alt.X("epoch:Q", title="Epoch"),
            y=alt.Y("loss:Q", title="Loss (skala ternormalisasi)"), tooltip=["epoch:Q", "loss:Q"]).properties(height=220), width="stretch")
        second.altair_chart(alt.Chart(curve).mark_line(color="#c65b45").encode(x=alt.X("epoch:Q", title="Epoch"),
            y=alt.Y("train_mae_ton:Q", title="MAE data latih (ton)"), tooltip=["epoch:Q", "train_mae_ton:Q"]).properties(height=220), width="stretch")
        st.caption("Loss dihitung NeuralProphet pada skala ternormalisasi. Kurva latih yang menurun tidak membuktikan model bebas overfitting; kinerja di luar data latih tetap dibaca dari validasi dan uji kronologis.")
        st.dataframe(pd.DataFrame([{"Epoch": row["epochs"], "Konfigurasi resmi": row["epochs"] == EPOCHS, **row["validation"]}
                                   for row in item["epoch_sensitivity"]]), hide_index=True, width="stretch")
        st.caption("Sensitivitas epoch dihitung setelah eksperimen resmi, memakai latih 84 bulan dan validasi 2024 saja. Tabel ini tidak dipakai mengganti 100 epoch resmi; memilih epoch terbaik lalu melaporkannya pada data uji berarti memilih ulang konfigurasi.")


def render_research_extensions(target, report, diagnostics, enrichment, walk_forward, source, *, significance, training):
    if enrichment is None:
        st.info("MASE dan interpretasi komponen belum tersedia untuk versi hasil ini.")
    elif enrichment.get("source") != source:
        st.error("Analisis tambahan tidak cocok dengan snapshot dan laporan penelitian.")
    else:
        detail = enrichment["series"][target]
        with st.expander("MASE dan pola residual", expanded=False):
            mase = detail["mase"]
            st.write("MASE = MAE uji ÷ rata-rata selisih absolut satu bulan pada data latih Januari 2017–Desember 2024.")
            first, second = st.columns(2)
            first.metric("MASE NeuralProphet", f"{mase['methods']['neuralprophet']:.3f}")
            second.metric("MASE bulan sebelumnya", f"{mase['methods']['last_month']:.3f}")
            st.caption(f"Penyebut: {mase['scale_ton']:,.2f} ton, dari 95 selisih pada 96 bulan data latih. MASE < 1 berarti MAE lebih kecil daripada skala kesalahan naif pada data latih; kemenangan atas baseline pada data uji tetap dibaca dari metrik kedua metode.")
            st.dataframe(pd.DataFrame([{"Metode": METHODS[name], "MAE uji (ton)": diagnostics["metrics"][name]["MAE"], "MASE": value}
                                       for name, value in mase["methods"].items()]), hide_index=True, width="stretch")
            acf = pd.DataFrame(detail["residual"]["acf"])
            st.altair_chart(alt.Chart(acf).mark_bar().encode(x=alt.X("lag:O", title="Lag residual (bulan)"),
                y=alt.Y("acf:Q", title="Autokorelasi residual", scale=alt.Scale(domain=[-1, 1])),
                tooltip=["lag:O", "acf:Q"]).properties(height=200), width="stretch")
            st.caption("ACF memakai 18 residual uji yang dipusatkan pada rata-ratanya. Grafik ini bersifat deskriptif; jumlah titik kecil dan korelasi rendah tidak membuktikan bahwa galat sudah acak. Penyebab kesalahan memerlukan bukti di luar pola angka.")
            st.markdown("[Definisi MASE: Hyndman dan Koehler (2006)](https://otext.robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/)")
        with st.expander("Komponen tren, musiman, dan AR linear", expanded=False):
            components = detail["components"]
            st.caption("Komponen berasal dari model yang dilatih sampai Desember 2024, seed 42, dan mereproduksi 18 prediksi uji resmi. Bagian setelah Desember 2024 adalah komponen ramalan dari model tersebut.")
            timeline = pd.DataFrame(components["timeline"])
            timeline["ds"] = pd.to_datetime(timeline["ds"])
            points = pd.DataFrame(components["potential_changepoints"])
            points["date"] = pd.to_datetime(points["date"])
            trend = alt.Chart(timeline).mark_line().encode(x=alt.X("ds:T", title="Bulan"),
                y=alt.Y("trend:Q", title="Komponen tren (ton)"), tooltip=["ds:T", "trend:Q"])
            rules = alt.Chart(points).mark_rule(color="#c65b45", opacity=0.4).encode(x="date:T",
                tooltip=["date:T", "slope_change_ton_per_nominal_month:Q"])
            test_start = alt.Chart(pd.DataFrame({"ds": [pd.Timestamp("2025-01-01")]})).mark_rule(
                color="#333", strokeDash=[5, 5]).encode(x="ds:T")
            st.altair_chart((trend + rules + test_start).properties(height=240), width="stretch")
            st.caption("Garis vertikal menunjukkan 10 lokasi kandidat changepoint otomatis. Besaran perubahan kemiringan adalah parameter model, bukan bukti perubahan struktural yang signifikan atau penyebab perubahan kargo.")
            st.caption("Garis putus-putus pada Januari 2025 menandai awal data uji.")
            st.dataframe(points.rename(columns={"date": "Lokasi kandidat", "slope_change_ton_per_nominal_month": "Perubahan kemiringan (ton/bulan nominal)"}), hide_index=True, width="stretch")
            st.caption("Bulan nominal = 365,25/12 hari untuk mengubah kemiringan dari skala waktu normalisasi model.")
            seasonal = pd.DataFrame(components["yearly_monthly_mean"])
            st.altair_chart(alt.Chart(seasonal).mark_bar().encode(x=alt.X("month:O", title="Bulan kalender"),
                y=alt.Y("contribution_ton:Q", title="Rata-rata komponen musiman (ton)"),
                tooltip=["month:O", "contribution_ton:Q"]).properties(height=220), width="stretch")
            st.caption(f"Rata-rata komponen tahunan pada 2017–2024 tertinggi di bulan {components['yearly_peak_month']} dan terendah di bulan {components['yearly_low_month']}. Ini kontribusi musiman model, bukan bulan dengan volume aktual tertinggi atau terendah.")
            st.altair_chart(alt.Chart(timeline).mark_line().encode(x=alt.X("ds:T", title="Bulan"),
                y=alt.Y("ar:Q", title="Kontribusi AR (ton)"), tooltip=["ds:T", "ar:Q"]).properties(height=200), width="stretch")
            ar = pd.DataFrame(components["ar_weights"])
            st.altair_chart(alt.Chart(ar).mark_bar().encode(x=alt.X("lag:O", title="Lag (bulan sebelumnya)"),
                y=alt.Y("weight:Q", title="Bobot AR linear"), tooltip=["lag:O", "weight:Q"]).properties(height=200), width="stretch")
            st.caption(f"Lag dengan bobot absolut terbesar: {components['largest_absolute_ar_lag']} bulan. AR memakai satu lapisan linear tanpa hidden layer. Bobot menggambarkan koefisien model dalam skala normalisasi, bukan pengaruh sebab akibat.")
        st.download_button("Unduh analisis tambahan (JSON)", json.dumps(enrichment, ensure_ascii=False, indent=2),
                           file_name="analisis_tambahan.json", mime="application/json")
        bundle = figures_bundle(target)
        if bundle:
            st.download_button("Unduh grafik dan tabel deret (ZIP)", bundle,
                               file_name=f"grafik_tabel_{target}.zip", mime="application/zip")
    if walk_forward is None:
        st.info("Backtest walk-forward tambahan belum tersedia untuk versi hasil ini.")
    elif walk_forward.get("source") != source:
        st.error("Backtest walk-forward tidak cocok dengan snapshot dan laporan penelitian.")
    else:
        with st.expander("Walk-forward 42 bulan · analisis tambahan", expanded=False):
            st.write("Januari 2023–Juni 2026: setiap bulan memilih lag melalui 12 bulan validasi yang sudah berlalu, melatih ulang sampai bulan asal, lalu memprediksi satu bulan berikutnya. Train dalam pertama memiliki 60 bulan; semua pemilihan memakai hanya masa lalu.")
            st.caption("Hasil ini menggunakan periode dan pembaruan model yang berbeda dari uji resmi 18 bulan. Angkanya tidak digabungkan dengan metrik resmi dan bukan sampel uji independen kedua.")
            item = walk_forward["series"][target]
            st.dataframe(pd.DataFrame([{"Metode": METHODS[name], **metrics} for name, metrics in item["metrics"]["all_42"].items()]), hide_index=True, width="stretch")
            monthly = pd.DataFrame(item["monthly"])
            monthly["ds"] = pd.to_datetime(monthly["ds"])
            chart = monthly.melt(id_vars="ds", value_vars=["actual", "neuralprophet", "last_month"], var_name="Metode", value_name="Ton")
            chart["Metode"] = chart["Metode"].map({"actual": "Aktual", **METHODS})
            st.altair_chart(alt.Chart(chart).mark_line(point=True).encode(x=alt.X("ds:T", title="Bulan target"),
                y=alt.Y("Ton:Q", title="Ton"), color="Metode:N", tooltip=["ds:T", "Metode:N", "Ton:Q"]).properties(height=280), width="stretch")
            st.caption("Frekuensi lag terpilih: " + "; ".join(f"lag {lag}: {count} bulan" for lag, count in item["lag_counts"].items()))
            st.dataframe(monthly[["ds", "origin", "inner_train_end", "inner_validation_start", "selected_n_lags", "actual", "neuralprophet", "last_month"]], hide_index=True, width="stretch")
            st.download_button("Unduh walk-forward lengkap (JSON)", json.dumps(walk_forward, ensure_ascii=False, indent=2),
                               file_name="walk_forward_42_bulan.json", mime="application/json")
    render_significance(target, significance, source)
    render_training_diagnostics(target, training, source)
