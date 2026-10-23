"""Grafik data 114 bulan, kurva loss model uji resmi, dan sensitivitas epoch pada validasi.

Analisis tambahan offline. Kurva loss berasal dari fit ulang yang wajib mereproduksi
18 prediksi resmi; sensitivitas epoch hanya memakai blok validasi 2024, tidak
memakai data uji, dan tidak mengubah konfigurasi resmi 100 epoch.
"""

import gc
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import warnings

import pandas as pd

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mpl-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cargo_forecast.data import COLUMNS, load_bps_data
from cargo_forecast.enrichment import data_sha256
from cargo_forecast.modeling import EPOCHS, TRAIN_END, VALIDATION_END, _fit, _metrics, _predict_range
from cargo_forecast.walkforward import atomic_json


LABELS = {"bongkar": "Bongkar", "muat": "Muat"}
EPOCH_GRID = (25, 50, 100, 150, 200)
VALIDATION_START = TRAIN_END + pd.offsets.MonthBegin(1)
TEST_START = VALIDATION_END + pd.offsets.MonthBegin(1)


def fmt(value, digits=2):
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(ROOT / "artifacts" / "figures" / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def data_figure(data):
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    for axis, target in zip(axes, COLUMNS, strict=True):
        axis.axvspan(VALIDATION_START, VALIDATION_END + pd.offsets.MonthEnd(1), color="#f2c14e", alpha=0.25, label="Validasi (12 bulan)")
        axis.axvspan(TEST_START, data["ds"].max() + pd.offsets.MonthEnd(1), color="#d1495b", alpha=0.18, label="Uji (18 bulan)")
        axis.plot(data["ds"], data[target], color="#1f4e79", marker="o", markersize=2.5, linewidth=1.2, label="Aktual")
        axis.set_ylabel("Ton per bulan")
        axis.set_title(f"{LABELS[target]}: Januari 2017–Juni 2026 (pelatihan 84 bulan sebelum area berwarna)")
        axis.grid(alpha=0.25)
    axes[0].legend(loc="upper left", fontsize=8)
    axes[-1].set_xlabel("Bulan")
    save(fig, "data_114_bulan.png")


def main():
    if sys.version_info >= (3, 13):
        raise SystemExit("Gunakan Python 3.12.")
    warnings.filterwarnings("ignore")
    import torch
    torch.set_num_threads(1)
    report_path = ROOT / "artifacts/report.json"
    original = report_path.read_bytes()
    report = json.loads(original)
    data = load_bps_data(ROOT / "data")
    train = data.loc[data["ds"] <= TRAIN_END]
    through_validation = data.loc[data["ds"] <= VALIDATION_END]
    (ROOT / "artifacts/figures").mkdir(exist_ok=True)
    data_figure(data)
    result = {"schema_version": 1, "kind": "diagnostik_pelatihan_tambahan_bukan_pengganti_uji_resmi",
              "source": {"report_sha256": hashlib.sha256(original).hexdigest(), "data_sha256": data_sha256(data)},
              "environment": {"python": sys.version.split()[0], "neuralprophet": version("neuralprophet")},
              "notes": {"loss_curve": "Fit ulang 96 bulan (Jan 2017–Des 2024), seed 42, lag resmi; wajib mereproduksi 18 prediksi uji resmi.",
                        "loss_scale": "Loss dihitung NeuralProphet pada skala ternormalisasi; MAE latih dalam ton.",
                        "epoch_sensitivity": "Fit 84 bulan dan MAE validasi Jan–Des 2024 saja; post-hoc, tidak memilih ulang epoch resmi."},
              "series": {}}
    for target in COLUMNS:
        official = report["series"][target]
        lag = official["selected_n_lags"]
        model = _fit(through_validation, target, lag)
        try:
            test = _predict_range(model, data, target, TEST_START)
            curve = model.fit_metrics
        finally:
            del model
            gc.collect()
        difference = max(abs(float(value) - row["prediksi"]) for value, row in zip(test["prediksi"], official["test_predictions"], strict=True))
        if len(test) != 18 or difference > 1e-5:
            raise ValueError(f"Fit ulang {target} tidak mereproduksi prediksi resmi: {difference} ton.")
        loss_curve = [{"epoch": int(row.epoch) + 1, "loss": float(row.Loss), "train_mae_ton": float(row.MAE)}
                      for row in curve.itertuples(index=False)]
        if len(loss_curve) != EPOCHS:
            raise ValueError("Kurva loss harus berisi 100 epoch.")
        official_validation = next(item["metrics"]["MAE"] for item in official["validation_candidates"] if item["n_lags"] == lag)
        sensitivity = []
        for epochs in EPOCH_GRID:
            model = _fit(train, target, lag, epochs=epochs)
            try:
                validation = _predict_range(model, through_validation, target, VALIDATION_START)
            finally:
                del model
                gc.collect()
            if len(validation) != 12:
                raise ValueError("Validasi harus 12 bulan.")
            sensitivity.append({"epochs": epochs, "validation": _metrics(validation)})
            print(f"{target}: {epochs} epoch, MAE validasi {sensitivity[-1]['validation']['MAE']:.2f}", flush=True)
        reproduced = next(item for item in sensitivity if item["epochs"] == EPOCHS)["validation"]["MAE"]
        if abs(reproduced - official_validation) > 1e-4:
            raise ValueError(f"MAE validasi 100 epoch {target} tidak sama dengan laporan resmi.")
        result["series"][target] = {"selected_n_lags": lag, "max_forecast_difference_ton": difference,
                                    "loss_curve": loss_curve, "epoch_sensitivity": sensitivity}

        fig, (left, right) = plt.subplots(1, 2, figsize=(10, 3.6))
        left.plot([r["epoch"] for r in loss_curve], [r["loss"] for r in loss_curve], color="#1f4e79")
        left.set(title=f"{LABELS[target]}: loss pelatihan (skala ternormalisasi)", xlabel="Epoch", ylabel="Loss")
        right.plot([r["epoch"] for r in loss_curve], [r["train_mae_ton"] for r in loss_curve], color="#d1495b")
        right.set(title=f"{LABELS[target]}: MAE data latih", xlabel="Epoch", ylabel="Ton")
        for axis in (left, right):
            axis.grid(alpha=0.25)
        save(fig, f"{target}_kurva_loss.png")

        fig, axis = plt.subplots(figsize=(6.5, 3.6))
        axis.plot(EPOCH_GRID, [r["validation"]["MAE"] for r in sensitivity], marker="o", color="#1f4e79")
        axis.axvline(EPOCHS, color="#777", linestyle="--", label="Konfigurasi resmi (100)")
        axis.set(title=f"{LABELS[target]}: MAE validasi 2024 menurut epoch (lag {lag})", xlabel="Epoch", ylabel="MAE validasi (ton)")
        axis.set_xticks(EPOCH_GRID)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
        save(fig, f"{target}_sensitivitas_epoch.png")
        print(f"{target}: kurva loss mereproduksi uji resmi (selisih {difference:.6f} ton)", flush=True)
    if report_path.read_bytes() != original:
        raise ValueError("Laporan resmi berubah selama analisis.")
    atomic_json(ROOT / "artifacts/training_diagnostics.json", result)

    lines = ["# Diagnostik pelatihan tambahan", "",
             "Analisis offline ini menjawab dua pertanyaan: bagaimana loss berkembang selama 100 epoch, dan apakah jumlah epoch lain akan memberi MAE validasi yang sangat berbeda. Hasil resmi, lag, seed, dan 100 epoch tidak diubah.", "",
             "![Data 114 bulan](artifacts/figures/data_114_bulan.png)", "",
             "## Kurva loss model uji resmi", "",
             "Model dilatih ulang pada 96 bulan (Januari 2017–Desember 2024) dengan konfigurasi resmi. Fit ulang ini mereproduksi 18 prediksi uji resmi; selisih maksimum dicatat di bawah. Loss dihitung NeuralProphet pada skala ternormalisasi, sedangkan MAE latih dalam ton.", "",
             "| Deret | Lag | Selisih maks. terhadap prediksi resmi (ton) | Loss epoch 1 | Loss epoch 50 | Loss epoch 100 | MAE latih epoch 100 (ton) |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for target in COLUMNS:
        item = result["series"][target]
        curve = item["loss_curve"]
        lines.append(f"| {LABELS[target]} | {item['selected_n_lags']} | {fmt(item['max_forecast_difference_ton'], 6)} | {fmt(curve[0]['loss'], 4)} | "
                     f"{fmt(curve[49]['loss'], 4)} | {fmt(curve[-1]['loss'], 4)} | {fmt(curve[-1]['train_mae_ton'])} |")
    lines += ["", "![Kurva loss Bongkar](artifacts/figures/bongkar_kurva_loss.png)", "", "![Kurva loss Muat](artifacts/figures/muat_kurva_loss.png)", "",
              "## Sensitivitas epoch pada validasi 2024", "",
              "Kandidat dilatih pada 84 bulan dengan lag resmi dan seed 42, lalu dinilai pada 12 bulan validasi dengan prosedur satu langkah yang sama. Data uji tidak dipakai. NeuralProphet menyesuaikan jadwal learning rate dengan jumlah epoch, sehingga setiap baris adalah pelatihan lengkap tersendiri.", "",
              "| Deret | Epoch | MAE validasi (ton) | RMSE validasi (ton) | MAPE validasi (%) |", "| --- | ---: | ---: | ---: | ---: |"]
    for target in COLUMNS:
        for item in result["series"][target]["epoch_sensitivity"]:
            metrics = item["validation"]
            marker = " (resmi)" if item["epochs"] == EPOCHS else ""
            lines.append(f"| {LABELS[target]} | {item['epochs']}{marker} | {fmt(metrics['MAE'])} | {fmt(metrics['RMSE'])} | {fmt(metrics['MAPE'])} |")
    lines += ["", "![Sensitivitas epoch Bongkar](artifacts/figures/bongkar_sensitivitas_epoch.png)", "", "![Sensitivitas epoch Muat](artifacts/figures/muat_sensitivitas_epoch.png)", "",
              "## Batas interpretasi", "",
              "Analisis epoch dilakukan setelah eksperimen resmi dan hanya memakai validasi. Hasilnya menunjukkan kepekaan, bukan dasar mengganti 100 epoch; memilih epoch terbaik dari tabel ini lalu melaporkannya pada data uji akan menjadi pemilihan ulang konfigurasi. Kurva loss latih yang menurun tidak membuktikan model bebas overfitting; bukti kinerja di luar data latih tetap berasal dari validasi dan uji kronologis.", "",
              f"SHA-256 laporan resmi: `{result['source']['report_sha256']}`. Jalankan ulang dengan `python training_diagnostics.py`.", ""]
    (ROOT / "DIAGNOSTIK_PELATIHAN.md").write_text("\n".join(lines), encoding="utf-8")
    print("Tersimpan: artifacts/training_diagnostics.json, DIAGNOSTIK_PELATIHAN.md, dan grafik di artifacts/figures/")


if __name__ == "__main__":
    main()
