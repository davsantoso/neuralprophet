"""Aplikasi web penelitian dan eksplorasi prediksi kargo udara domestik."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import threading

import altair as alt
import pandas as pd
import streamlit as st

from cargo_forecast.bps_api import BpsApiError, fetch_bps_cargo
from cargo_forecast.data import descriptive_stats, load_bps_data
from cargo_forecast.modeling import LEARNING_RATE, SEED


ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "artifacts" / "report.json"
LABELS = {"bongkar": "Bongkar", "muat": "Muat"}
BPS_URL = "https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html"


@st.cache_data
def thesis_data() -> pd.DataFrame:
    return load_bps_data(ROOT / "data")


@st.cache_data
def saved_report() -> dict | None:
    if not REPORT_PATH.exists():
        return None
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def live_dataset() -> dict:
    key = os.environ.get("BPS_API_KEY")
    if not key:
        try:
            key = str(st.secrets["BPS_API_KEY"])
        except (FileNotFoundError, KeyError):
            raise BpsApiError("BPS_API_KEY belum tersedia pada Secrets aplikasi.") from None
    return fetch_bps_cargo(key)


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
        .encode(
            x=alt.X("ds:T", title="Bulan"),
            y=alt.Y("Ton:Q", title="Ton"),
            color="Deret:N",
            tooltip=["ds:T", "Deret:N", "Ton:Q"],
        )
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
        .encode(
            x=alt.X("ds:T", title="Bulan"),
            y=alt.Y("Ton:Q", title="Ton"),
            color="Jenis:N",
            tooltip=["ds:T", "Jenis:N", "Ton:Q"],
        )
        .properties(title=title, height=340)
        .interactive()
    )


st.set_page_config(page_title="Prediksi Kargo Udara Domestik", page_icon="✈️", layout="wide")
st.title("Prediksi volume kargo udara domestik")
st.caption("NeuralProphet · penelitian Soekarno Hatta-Jakarta · eksplorasi lima bandara BPS · horizon satu bulan")

try:
    data = thesis_data()
except (ValueError, FileNotFoundError) as exc:
    st.error(f"Data penelitian tidak dapat dibaca: {exc}")
    st.stop()

report = saved_report()
try:
    with st.spinner("Mengambil data terbaru dari BPS..."):
        live = live_dataset()
    api_error = None
except BpsApiError as exc:
    live = None
    api_error = str(exc)
except Exception:
    live = None
    api_error = "Data BPS langsung belum dapat dibaca. Coba muat ulang nanti."

tabs = st.tabs(["Ringkasan", "Data", "Evaluasi model", "Eksperimen"])

with tabs[0]:
    st.subheader("Data penelitian: Januari 2017–Juni 2026")
    first, second, third = st.columns(3)
    first.metric("Observasi per deret", len(data))
    second.metric("Bongkar Juni 2026", ton(data.iloc[-1]["bongkar"]))
    third.metric("Muat Juni 2026", ton(data.iloc[-1]["muat"]))
    st.altair_chart(history_plot(data, ["bongkar", "muat"]), width="stretch")
    if report:
        st.subheader("Prediksi Juli 2026 · hasil penelitian")
        left, right = st.columns(2)
        for column, target in ((left, "bongkar"), (right, "muat")):
            item = report["series"][target]
            column.metric(f"{LABELS[target]} · estimasi", ton(item["next_month"]["prediksi"]))
            column.caption(f"MAE data uji: {ton(item['test_metrics']['MAE'])} | MAPE: {item['test_metrics']['MAPE']:.2f}%")
        st.info("Prediksi penelitian dibuat dari 114 bulan sampai Juni 2026. Data BPS yang terbit kemudian tidak mengubah hasil dan metrik penelitian ini.")
    else:
        st.info("Laporan model belum tersedia. Jalankan `python train.py` di lingkungan penelitian.")

with tabs[1]:
    st.subheader("Data BPS langsung")
    st.markdown(f"[Tabel statistik BPS: bongkar dan muat barang angkutan udara dalam negeri]({BPS_URL})")
    if live is None:
        st.warning(f"Data langsung belum tersedia: {api_error}")
        st.info("Di bawah ini adalah arsip penelitian Soekarno Hatta-Jakarta sampai Juni 2026, bukan data terbaru dari API.")
        st.dataframe(descriptive_stats(data), hide_index=True, width="stretch")
        st.altair_chart(history_plot(data, ["bongkar", "muat"]), width="stretch")
        st.dataframe(data.assign(ds=data["ds"].dt.strftime("%Y-%m")), hide_index=True, width="stretch")
    else:
        st.success(f"Data langsung BPS tersedia sampai {live['last_month']}. Diambil {live['fetched_at']} UTC; pembaruan sumber: {live['last_update']}.")
        airport = st.selectbox("Kategori bandara", live["airports"], key="data_airport")
        series_choice = st.selectbox("Deret yang ditampilkan", ["Keduanya", "Bongkar", "Muat"], key="data_series")
        airport_data = live["frame"].loc[live["frame"]["bandara"] == airport, ["ds", "bongkar", "muat"]].copy()
        years = (int(airport_data["ds"].dt.year.min()), int(airport_data["ds"].dt.year.max()))
        year_range = st.slider("Rentang tahun", min_value=years[0], max_value=years[1], value=years, key="data_years")
        shown = airport_data.loc[airport_data["ds"].dt.year.between(*year_range)].copy()
        series = ["bongkar", "muat"] if series_choice == "Keduanya" else [series_choice.lower()]
        st.caption(f"{airport} · {len(shown)} bulan ditampilkan · ton per bulan. Data berasal dari API BPS dan dapat berbeda dari arsip penelitian jika ada revisi.")
        st.altair_chart(history_plot(shown, series), width="stretch")
        st.dataframe(descriptive_stats(airport_data), hide_index=True, width="stretch")
        export = shown.loc[:, ["ds", *series]].copy()
        export["ds"] = export["ds"].dt.strftime("%Y-%m")
        st.dataframe(export.rename(columns={"ds": "Bulan", "bongkar": "Bongkar (ton)", "muat": "Muat (ton)"}), hide_index=True, width="stretch")
        st.download_button("Unduh data BPS yang ditampilkan (CSV)", export.to_csv(index=False).encode("utf-8"), file_name="data_kargo_bps_langsung.csv", mime="text/csv")
        st.caption(f"Endpoint: {live['source_url']} · cache aplikasi maksimal 6 jam.")

with tabs[2]:
    st.subheader("Pembagian kronologis penelitian")
    st.dataframe(pd.DataFrame([
        {"Bagian": "Train", "Periode": "Jan 2017–Des 2023", "Bulan": 84, "Tujuan": "Melatih kandidat lookback"},
        {"Bagian": "Validasi", "Periode": "Jan–Des 2024", "Bulan": 12, "Tujuan": "Memilih lookback dengan MAE terendah"},
        {"Bagian": "Uji", "Periode": "Jan 2025–Jun 2026", "Bulan": 18, "Tujuan": "Evaluasi akhir pada data yang belum dipakai memilih model"},
    ]), hide_index=True, width="stretch")
    st.caption("Setiap prediksi uji memakai nilai aktual bulan-bulan sebelumnya sebagai riwayat. Model tidak dilatih ulang pada setiap bulan uji.")
    if report is None:
        st.error("Laporan penelitian tidak ditemukan. Jalankan `python train.py` dan sertakan `artifacts/report.json` saat deploy.")
    else:
        target = st.selectbox("Deret evaluasi", ["bongkar", "muat"], format_func=lambda x: LABELS[x], key="evaluation_target")
        item = report["series"][target]
        st.write(f"**Lookback terpilih:** {item['selected_n_lags']} bulan")
        candidates = pd.DataFrame([{"Lookback (bulan)": candidate["n_lags"], **candidate["metrics"]} for candidate in item["validation_candidates"]])
        st.write("**Hasil validasi 2024**")
        st.dataframe(candidates, hide_index=True, width="stretch")
        metrics = item["test_metrics"]
        a, b, c = st.columns(3)
        a.metric("MAE uji", ton(metrics["MAE"]))
        b.metric("RMSE uji", ton(metrics["RMSE"]))
        c.metric("MAPE uji", f"{metrics['MAPE']:.2f}%")
        st.altair_chart(test_plot(item["test_predictions"], f"Aktual vs prediksi uji · {LABELS[target]}"), width="stretch")
        st.dataframe(pd.DataFrame(item["test_predictions"]).rename(columns={"ds": "Bulan", "aktual": "Aktual (ton)", "prediksi": "Prediksi (ton)"}), hide_index=True, width="stretch")
        st.download_button("Unduh laporan penelitian (JSON)", json.dumps(report, ensure_ascii=False, indent=2), file_name="laporan_neuralprophet.json", mime="application/json")

with tabs[3]:
    st.subheader("Eksperimen prediksi dari data BPS langsung")
    st.write("Pilih bandara, satu deret, dan parameter. Pelatihan dimulai hanya setelah tombol ditekan. Hasil eksperimen tidak mengubah penelitian 114 bulan.")
    if live is None:
        st.warning(f"Pelatihan dengan data terbaru belum tersedia: {api_error}")
    elif sys.version_info >= (3, 13):
        st.error("Pelatihan NeuralProphet memerlukan Python 3.12.")
    else:
        airport = st.selectbox("Kategori bandara untuk eksperimen", live["airports"], key="experiment_airport")
        target = st.selectbox("Deret untuk eksperimen", list(LABELS), format_func=lambda name: LABELS[name], key="experiment_target")
        a, b = st.columns(2)
        history = a.selectbox("Riwayat pelatihan", ["Semua data", "84 bulan terakhir", "60 bulan terakhir"], key="experiment_history")
        n_lags = b.selectbox("Lookback (bulan)", [3, 6, 12], index=1, key="experiment_lags")
        c, d = st.columns(2)
        epochs = c.selectbox("Epoch", [25, 50, 100], key="experiment_epochs")
        yearly = d.checkbox("Musiman tahunan", value=True, key="experiment_yearly")
        airport_data = live["frame"].loc[live["frame"]["bandara"] == airport, ["ds", "bongkar", "muat"]].copy()
        count = {"Semua data": len(airport_data), "84 bulan terakhir": 84, "60 bulan terakhir": 60}[history]
        experiment_data = airport_data.tail(count).reset_index(drop=True)
        st.caption(f"Masukan: {airport} · {LABELS[target]} · {experiment_data['ds'].min():%Y-%m} sampai {experiment_data['ds'].max():%Y-%m} ({len(experiment_data)} bulan) · {n_lags} lookback · {epochs} epoch · musiman tahunan {'aktif' if yearly else 'nonaktif'}.")
        st.caption("Tren aktif, learning rate 0,01, horizon satu bulan. Parameter ini adalah pilihan eksperimen pengguna, bukan konfigurasi terbaik untuk semua bandara.")
        if len(experiment_data) < 60:
            st.error("Data eksperimen memerlukan minimal 60 bulan lengkap.")
        else:
            model_input = experiment_data.loc[:, ["ds", target]].copy()
            data_hash = hashlib.sha256(model_input.to_csv(index=False).encode("utf-8")).hexdigest()
            parameters = {"n_lags": n_lags, "epochs": epochs, "yearly_seasonality": yearly, "learning_rate": LEARNING_RATE, "n_forecasts": 1, "seed": SEED}
            signature = hashlib.sha256(json.dumps({"airport": airport, "target": target, "data_sha256": data_hash, "parameters": parameters}, sort_keys=True).encode("utf-8")).hexdigest()
            results = st.session_state.setdefault("experiment_results", {})
            already_done = signature in results
            if st.button("Latih model dan prediksi satu bulan", type="primary", disabled=already_done):
                lock = training_lock()
                if not lock.acquire(blocking=False):
                    st.warning("Pelatihan lain sedang berjalan. Coba lagi setelah selesai.")
                else:
                    try:
                        from cargo_forecast.modeling import retrain_target_for_next_month

                        with st.spinner(f"Melatih {LABELS[target].lower()} untuk {airport}..."):
                            result = retrain_target_for_next_month(experiment_data, target, n_lags, epochs=epochs, yearly_seasonality=yearly)
                        provenance = {
                            "jenis": "eksperimen_pengguna",
                            "sumber": live["source_url"],
                            "waktu_ambil_api_utc": live["fetched_at"],
                            "pembaruan_bps": live["last_update"],
                            "waktu_hasil_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "bandara": airport,
                            "target": target,
                            "satuan": "ton per bulan",
                            "bulan_awal": experiment_data["ds"].min().strftime("%Y-%m"),
                            "bulan_akhir": experiment_data["ds"].max().strftime("%Y-%m"),
                            "jumlah_observasi": len(experiment_data),
                            "data_sha256": data_hash,
                            "parameter": parameters,
                            "versi_paket": {name: version(name) for name in ("neuralprophet", "torch", "streamlit")},
                            "durasi_detik": result["duration_seconds"],
                            "prediksi": result["forecast"],
                        }
                        results[signature] = provenance
                        if len(results) > 10:
                            del results[next(iter(results))]
                    except Exception:
                        st.error("Pelatihan eksperimen gagal. Periksa log aplikasi atau coba konfigurasi lebih ringan.")
                    finally:
                        lock.release()
            stored = results.get(signature)
            if stored:
                forecast = stored["prediksi"]
                st.metric(f"Prediksi {LABELS[target]} · {forecast['ds']}", ton(forecast["prediksi"]))
                st.caption(f"Durasi pelatihan: {stored['durasi_detik']:.1f} detik. Hasil ini tersedia dalam sesi untuk konfigurasi dan data yang sama.")
                st.download_button("Unduh jejak eksperimen (JSON)", json.dumps(stored, ensure_ascii=False, indent=2), file_name="jejak_eksperimen_bps.json", mime="application/json")
            st.info("Eksperimen satu kali pelatihan ini tidak menghasilkan MAE, RMSE, atau MAPE uji baru. Metrik pada tab Evaluasi model hanya berlaku untuk penelitian resmi Soekarno Hatta-Jakarta.")
