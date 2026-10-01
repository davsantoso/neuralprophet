"""Build supplementary diagnostics offline; never change the thesis report."""

from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

from cargo_forecast.data import load_bps_data
from cargo_forecast.diagnostics import build_diagnostics
from cargo_forecast.modeling import evaluate_seed_sensitivity


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "artifacts" / "report.json"
OUTPUT = ROOT / "artifacts" / "diagnostics.json"
DOCUMENT = ROOT / "DIAGNOSTIK_PENELITIAN.md"
LABELS = {"bongkar": "Bongkar", "muat": "Muat"}
METHODS = {"neuralprophet": "NeuralProphet", "last_month": "Bulan sebelumnya", "same_month_last_year": "Bulan sama tahun lalu"}


def decimal(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def document_lines(diagnostics: dict) -> list[str]:
    lines = [
        "# Diagnostik tambahan penelitian",
        "",
        "Analisis ini memakai **snapshot penelitian 114 bulan**, kategori data BPS **Soekarno Hatta-Jakarta**, dan periode uji **Januari 2025–Juni 2026 (18 bulan)**. Hasil resmi di `artifacts/report.json` tidak diubah. Tolok ukur sederhana dipakai untuk memberi konteks kesalahan NeuralProphet, bukan sebagai perbandingan SARIMA atau pemilihan model baru.",
        "",
        "Setiap ramalan pembanding memakai hanya nilai aktual yang sudah tersedia sebelum bulan target: nilai bulan sebelumnya atau nilai bulan yang sama pada tahun sebelumnya. Semua metrik memakai 18 bulan dan satuan yang sama. Lihat [rujukan evaluasi deret waktu](https://otexts.com/fpp3/tscv.html).",
        "",
        "## Tolok ukur pada periode uji yang sama",
        "",
        "| Deret | Metode | MAE (ton) | RMSE (ton) | MAPE (%) |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for target in ("bongkar", "muat"):
        series = diagnostics["series"][target]
        for method, label in METHODS.items():
            metric = series["metrics"][method]
            lines.append(f"| {LABELS[target]} | {label} | {decimal(metric['MAE'])} | {decimal(metric['RMSE'])} | {decimal(metric['MAPE'])} |")
    lines.extend([
        "",
        "NeuralProphet tidak menjadi yang terbaik pada semua metrik. Pada bongkar, aturan bulan yang sama tahun lalu memiliki MAE dan MAPE lebih rendah. Pada muat, aturan bulan sebelumnya memiliki MAE dan MAPE lebih rendah, sedangkan NeuralProphet memiliki RMSE sedikit lebih rendah. Ini adalah temuan pada 18 bulan uji, bukan bukti bahwa satu metode selalu lebih baik pada periode lain.",
        "",
        "## Arah dan bulan kesalahan terbesar",
        "",
    ])
    for target in ("bongkar", "muat"):
        series = diagnostics["series"][target]
        bias = series["bias"]
        direction = "terlalu tinggi" if bias["mean_error"] > 0 else "terlalu rendah"
        lines.extend([
            f"### {LABELS[target]}",
            "",
            f"Galat bertanda didefinisikan sebagai prediksi dikurangi aktual. Rata-ratanya **{decimal(bias['mean_error'])} ton**, sehingga arah rata-rata adalah **{direction}**. Prediksi lebih tinggi pada {bias['overprediction_months']} bulan dan lebih rendah pada {bias['underprediction_months']} bulan. Angka ini menggambarkan bias pada periode uji, tanpa menjelaskan penyebabnya.",
            "",
            "| Bulan | Aktual (ton) | Prediksi (ton) | Galat (ton) | APE (%) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ])
        for row in series["largest_errors"]:
            lines.append(f"| {row['ds']} | {decimal(row['actual'], 0)} | {decimal(row['neuralprophet'])} | {decimal(row['error'])} | {decimal(row['ape_percent'])} |")
        lines.append("")
    lines.extend([
        "## Kepekaan terhadap seed pelatihan",
        "",
        "Lima seed diuji dengan lookback yang **sudah dipilih pada validasi resmi seed 42** (bongkar 6, muat 3), 100 epoch, musiman tahunan aktif, data latih sampai Desember 2024, dan 18 bulan uji yang sama. Seed tidak dipilih berdasarkan hasil uji. Ringkasan ini mengukur variasi pelatihan pada konfigurasi tetap; tidak mengukur ketidakpastian prediksi atau kestabilan pemilihan lookback.",
        "",
        "| Deret | Seed | MAE (ton) | RMSE (ton) | MAPE (%) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for target in ("bongkar", "muat"):
        series = diagnostics["series"][target]
        for run in series["seed_runs"]:
            metric = run["metrics"]
            lines.append(f"| {LABELS[target]} | {run['seed']} | {decimal(metric['MAE'])} | {decimal(metric['RMSE'])} | {decimal(metric['MAPE'])} |")
    lines.extend(["", "| Deret | Metrik | Rata-rata | Simpangan baku sampel | Minimum | Maksimum |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for target in ("bongkar", "muat"):
        for metric in ("MAE", "RMSE", "MAPE"):
            summary = diagnostics["series"][target]["seed_summary"][metric]
            lines.append(f"| {LABELS[target]} | {metric} | {decimal(summary['mean'])} | {decimal(summary['sample_std'])} | {decimal(summary['min'])} | {decimal(summary['max'])} |")
    lines.extend([
        "",
        "Kelima hasil berbagi periode uji yang sama sehingga bukan lima sampel uji independen. Sebaran seed tidak boleh ditafsirkan sebagai interval kepercayaan kinerja masa depan. Perbedaan prediksi seed 42 terhadap laporan resmi dicatat dalam JSON untuk memeriksa reproduksi.",
        "",
        "## Jejak dan batas interpretasi",
        "",
        f"SHA-256 laporan resmi: `{diagnostics['source']['report_sha256']}`. SHA-256 tabel penelitian kanonik: `{diagnostics['source']['data_sha256']}`. Prediksi bulanan, metrik lengkap, dan semua seed tersedia di `artifacts/diagnostics.json`. Jalankan `python diagnose.py` untuk menghitung ulang secara offline.",
        "",
        "Analisis ini bersifat tambahan setelah laporan inti dibuat. Pembandingan tidak dipakai untuk mengubah pilihan lookback, seed resmi, metrik utama, atau prediksi Juli 2026. Interpretasi di BAB IV sebaiknya menekankan bahwa hasil ini berlaku pada kategori dan periode yang diuji.",
        "",
    ])
    return lines


def main() -> None:
    if sys.version_info >= (3, 13):
        raise RuntimeError("Analisis NeuralProphet memerlukan Python 3.12.")
    raw_report = REPORT.read_bytes()
    report = json.loads(raw_report)
    data = load_bps_data(ROOT / "data")
    selected_lags = {target: report["series"][target]["selected_n_lags"] for target in ("bongkar", "muat")}
    seed_runs = evaluate_seed_sensitivity(data, selected_lags)
    diagnostics = build_diagnostics(data, report, seed_runs, report_sha256=hashlib.sha256(raw_report).hexdigest())
    diagnostics["environment"] = {
        "python": sys.version.split()[0],
        "packages": {name: version(name) for name in ("neuralprophet", "pandas", "torch")},
    }
    OUTPUT.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DOCUMENT.write_text("\n".join(document_lines(diagnostics)), encoding="utf-8")
    print(f"Diagnostik tersimpan: {OUTPUT} dan {DOCUMENT}")


if __name__ == "__main__":
    main()
