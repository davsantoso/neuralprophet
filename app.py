"""Aplikasi web prediksi kargo domestik berbasis NeuralProphet."""

from __future__ import annotations

import json
import hashlib
import logging
from pathlib import Path
import sys
import threading

import altair as alt
import pandas as pd
import streamlit as st

from cargo_forecast.data import descriptive_stats, load_bps_data, parse_additional_csv


ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "artifacts" / "report.json"
LABELS = {"bongkar": "Bongkar", "muat": "Muat"}
BPS_URL = "https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html"


@st.cache_data
def thesis_data() -> pd.DataFrame:
    return load_bps_data(ROOT / "data")


@st.cache_data
def latest_file_data() -> pd.DataFrame:
    return load_bps_data(ROOT / "data", through=pd.Timestamp("2026-07-01"))


@st.cache_data
def saved_report() -> dict | None:
    if not REPORT_PATH.exists():
        return None
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@st.cache_resource
def training_lock() -> threading.Lock:
    """One training job at a time across all visitors."""
    return threading.Lock()


def ton(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".") + " ton"


def history_plot(frame: pd.DataFrame, series: list[str]) -> alt.Chart:
    values = frame.melt(id_vars="ds", value_vars=series, var_name="Deret", value_name="Ton")
    values["Deret"] = values["Deret"].map(LABELS)
    return (
        alt.Chart(values)
        .mark_line(point=True)
        .encode(x=alt.X("ds:T", title="Bulan"), y=alt.Y("Ton:Q", title="Ton"), color="Deret:N", tooltip=["ds:T", "Deret:N", "Ton:Q"])
        .properties(height=360)
        .interactive()
    )


def test_plot(records: list[dict], title: str) -> alt.Chart:
    frame = pd.DataFrame(records)
    frame["ds"] = pd.to_datetime(frame["ds"])
    values = frame.melt(id_vars="ds", value_vars=["aktual", "prediksi"], var_name="Jenis", value_name="Ton")
    values["Jenis"] = values["Jenis"].map({"aktual": "Aktual", "prediksi": "Prediksi"})
    return (
        alt.Chart(values)
        .mark_line(point=True)
        .encode(x=alt.X("ds:T", title="Bulan"), y=alt.Y("Ton:Q", title="Ton"), color="Jenis:N", tooltip=["ds:T", "Jenis:N", "Ton:Q"])
        .properties(title=title, height=340)
        .interactive()
    )


st.set_page_config(page_title="Prediksi Kargo Udara Domestik", page_icon="✈️", layout="wide")
st.title("Prediksi volume kargo udara domestik")
st.caption("NeuralProphet · data bulanan BPS · kategori Soekarno Hatta-Jakarta · satu bulan ke depan")

try:
    data = thesis_data()
except (ValueError, FileNotFoundError) as exc:
    st.error(f"Data BPS tidak dapat dibaca: {exc}")
    st.stop()

report = saved_report()
tabs = st.tabs(["Ringkasan", "Data", "Evaluasi model", "Eksperimen"])

with tabs[0]:
    st.subheader("Data penelitian: Januari 2017–Juni 2026")
    first, second, third = st.columns(3)
    first.metric("Observasi per deret", len(data))
    second.metric("Bongkar Juni 2026", ton(data.iloc[-1]["bongkar"]))
    third.metric("Muat Juni 2026", ton(data.iloc[-1]["muat"]))
    st.altair_chart(history_plot(data, ["bongkar", "muat"]), width="stretch")
    if report:
        st.subheader("Prediksi Juli 2026")
        left, right = st.columns(2)
        for column, target in ((left, "bongkar"), (right, "muat")):
            item = report["series"][target]
            column.metric(f"{LABELS[target]} · estimasi", ton(item["next_month"]["prediksi"]))
            column.caption(f"MAE data uji: {ton(item['test_metrics']['MAE'])} | MAPE: {item['test_metrics']['MAPE']:.2f}%")
        st.info("Prediksi di atas dibuat dengan model yang dilatih ulang pada 114 bulan hingga Juni 2026. Juli 2026 yang kini tersedia di berkas BPS tidak dipakai dalam eksperimen skripsi.")
    else:
        st.info("Laporan model belum dibuat. Jalankan `python train.py` atau latih melalui tab Evaluasi model.")

with tabs[1]:
    st.subheader("Sumber dan cakupan")
    st.markdown(f"[Tabel statistik BPS: bongkar dan muat barang angkutan udara dalam negeri]({BPS_URL})")
    st.write("Kategori yang digunakan sebagai label data publik adalah **Soekarno Hatta-Jakarta**. Kedua deret dianalisis secara terpisah dalam satuan ton per bulan.")
    st.write("**Statistik deskriptif, Januari 2017–Juni 2026**")
    st.dataframe(descriptive_stats(data), hide_index=True, width="stretch")
    st.caption("Perubahan absolut bulanan adalah besar selisih dari bulan sebelumnya tanpa memperhatikan arah. Persentase dihitung relatif terhadap nilai bulan sebelumnya.")
    choice = st.selectbox("Lihat deret", ["bongkar", "muat"], format_func=lambda x: LABELS[x])
    st.altair_chart(history_plot(data, [choice]), width="stretch")
    st.dataframe(data.assign(ds=data["ds"].dt.strftime("%Y-%m")).rename(columns={"ds": "Bulan", "bongkar": "Bongkar (ton)", "muat": "Muat (ton)"}), hide_index=True, width="stretch")
    export = data.assign(ds=data["ds"].dt.strftime("%Y-%m")).to_csv(index=False).encode("utf-8")
    st.download_button("Unduh data penelitian (CSV)", export, file_name="kargo_domestik_2017_2026_juni.csv", mime="text/csv")

with tabs[2]:
    st.subheader("Pembagian kronologis")
    st.dataframe(pd.DataFrame([
        {"Bagian": "Train", "Periode": "Jan 2017–Des 2023", "Bulan": 84, "Tujuan": "Melatih kandidat lookback"},
        {"Bagian": "Validasi", "Periode": "Jan–Des 2024", "Bulan": 12, "Tujuan": "Memilih lookback dengan MAE terendah"},
        {"Bagian": "Uji", "Periode": "Jan 2025–Jun 2026", "Bulan": 18, "Tujuan": "Evaluasi akhir pada data yang belum dipakai memilih model"},
    ]), hide_index=True, width="stretch")
    st.caption("Setiap prediksi uji adalah prediksi satu bulan ke depan dengan nilai aktual bulan-bulan sebelumnya sebagai riwayat. Model tidak dilatih ulang pada setiap bulan uji.")
    if report is None:
        st.error("Laporan penelitian tidak ditemukan. Jalankan `python train.py` di lingkungan penelitian dan sertakan `artifacts/report.json` saat deploy.")
    else:
        target = st.selectbox("Deret evaluasi", ["bongkar", "muat"], format_func=lambda x: LABELS[x], key="evaluation_target")
        item = report["series"][target]
        st.write(f"**Lookback terpilih:** {item['selected_n_lags']} bulan")
        candidates = pd.DataFrame([
            {"Lookback (bulan)": candidate["n_lags"], **candidate["metrics"]}
            for candidate in item["validation_candidates"]
        ])
        st.write("**Hasil validasi 2024**")
        st.dataframe(candidates, hide_index=True, width="stretch")
        metrics = item["test_metrics"]
        a, b, c = st.columns(3)
        a.metric("MAE uji", ton(metrics["MAE"]))
        b.metric("RMSE uji", ton(metrics["RMSE"]))
        c.metric("MAPE uji", f"{metrics['MAPE']:.2f}%")
        st.altair_chart(test_plot(item["test_predictions"], f"Aktual vs prediksi uji · {LABELS[target]}"), width="stretch")
        st.dataframe(pd.DataFrame(item["test_predictions"]).rename(columns={"ds": "Bulan", "aktual": "Aktual (ton)", "prediksi": "Prediksi (ton)"}), hide_index=True, width="stretch")
        st.download_button("Unduh laporan eksperimen (JSON)", json.dumps(report, ensure_ascii=False, indent=2), file_name="laporan_neuralprophet.json", mime="application/json")

with tabs[3]:
    st.subheader("Latih ulang untuk bulan berikutnya")
    st.write("Eksperimen ini dapat memakai bulan baru. Hasilnya hanya berlaku untuk sesi ini dan tidak mengubah evaluasi skripsi yang memakai 114 bulan.")
    add_july = st.checkbox("Tambahkan Juli 2026 dari berkas BPS yang tersedia", value=False)
    experiment_data = latest_file_data() if add_july else data
    st.caption("Centang Juli hanya menambah data masukan; pelatihan dimulai setelah tombol di bawah ditekan.")
    st.caption(f"Bulan terakhir saat ini: {experiment_data['ds'].max():%Y-%m} ({len(experiment_data)} observasi).")
    template_month = experiment_data["ds"].max() + pd.offsets.MonthBegin(1)
    template = f"ds,bongkar,muat\n{template_month:%Y-%m},10000,15000\n"
    st.download_button("Unduh contoh format CSV tambahan", template, file_name="contoh_data_tambahan.csv", mime="text/csv")
    uploaded = st.file_uploader("Unggah data tambahan berurutan (kolom ds,bongkar,muat)", type="csv")
    if uploaded is not None:
        try:
            experiment_data = parse_additional_csv(uploaded.getvalue(), experiment_data)
            st.success(f"Data diterima sampai {experiment_data['ds'].max():%Y-%m} ({len(experiment_data)} observasi).")
        except (ValueError, pd.errors.ParserError) as exc:
            st.error(str(exc))
            experiment_data = None
    if report is None:
        st.info("Laporan penelitian diperlukan agar lookback terpilih tersedia.")
    elif experiment_data is not None:
        fingerprint = hashlib.sha256(experiment_data.to_csv(index=False).encode("utf-8")).hexdigest()
        if sys.version_info >= (3, 13):
            st.error("Pelatihan ulang memerlukan Python 3.12.")
        else:
            target = st.selectbox("Deret yang dilatih ulang", list(LABELS), format_func=lambda name: LABELS[name], key="experiment_target")
            st.caption("Satu deret dilatih per klik untuk membatasi beban CPU. Konfigurasi resmi tetap 100 epoch dan lookback hasil validasi.")
            results = st.session_state.setdefault("experiment_results", {})
            prior = results.get(target)
            already_done = prior is not None and prior["fingerprint"] == fingerprint
            if st.button("Latih ulang dan prediksi", type="primary", disabled=already_done):
                lock = training_lock()
                if not lock.acquire(blocking=False):
                    st.warning("Pelatihan lain sedang berjalan. Coba lagi setelah selesai.")
                else:
                    try:
                        from cargo_forecast.modeling import retrain_target_for_next_month

                        n_lags = report["series"][target]["selected_n_lags"]
                        with st.spinner(f"Melatih ulang deret {LABELS[target].lower()}..."):
                            result = retrain_target_for_next_month(experiment_data, target, n_lags)
                        results[target] = {"fingerprint": fingerprint, "result": result}
                    except Exception:
                        logging.exception("Pelatihan ulang %s gagal", target)
                        st.error("Pelatihan ulang gagal. Periksa Manage app → Logs atau coba lagi setelah pembatasan CPU berakhir.")
                    finally:
                        lock.release()
            if already_done:
                st.info("Prediksi untuk deret dan data ini sudah tersedia dalam sesi. Ubah data jika ingin melatih ulang.")
            available = {name: entry["result"] for name, entry in results.items() if entry["fingerprint"] == fingerprint}
            if available:
                st.write(f"**Hasil eksperimen:** data hingga {experiment_data['ds'].max():%Y-%m} ({len(experiment_data)} bulan).")
                columns = st.columns(len(available))
                for column, (name, result) in zip(columns, available.items()):
                    forecast = result["forecast"]
                    column.metric(f"{LABELS[name]} {forecast['ds']}", ton(forecast["prediksi"]))
                    column.caption(f"Durasi pelatihan: {result['duration_seconds']:.1f} detik")

