"""Build a readable research result summary from the verified JSON artifact."""

from __future__ import annotations

import json
from pathlib import Path

from cargo_forecast.data import descriptive_stats, load_bps_data


REPORT_PATH = Path("artifacts/report.json")
OUTPUT_PATH = Path("HASIL_EKSPERIMEN.md")
LABELS = {"bongkar": "Bongkar", "muat": "Muat"}


def decimal(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def main() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    data = load_bps_data()
    if report["n_observations"] != len(data) or report["cutoff"] != "2026-06":
        raise ValueError("Laporan model tidak cocok dengan dataset penelitian.")
    stats = descriptive_stats(data)
    lines = [
        "# Hasil eksperimen NeuralProphet",
        "",
        "**Sumber:** [tabel statistik BPS](https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html), kategori data Soekarno Hatta-Jakarta. Satuan: ton per bulan.",
        "",
        "Dataset penelitian berisi **114 bulan, Januari 2017–Juni 2026**. Deret bongkar dan muat dimodelkan secara univariat dan terpisah. Juli 2026 yang sudah ada pada berkas sumber tidak dipakai untuk melatih atau mengevaluasi hasil di bawah.",
        "",
        "## Statistik deskriptif",
        "",
        "| Deret | Minimum (ton) | Maksimum (ton) | Rata-rata (ton) | Rata-rata perubahan absolut bulanan (ton) | Rata-rata perubahan absolut bulanan (%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in stats.itertuples(index=False, name=None):
        label, minimum, maximum, mean, delta_ton, delta_percent = row
        lines.append(f"| {label} | {decimal(minimum, 0)} | {decimal(maximum, 0)} | {decimal(mean)} | {decimal(delta_ton)} | {decimal(delta_percent)} |")
    lines.extend([
        "",
        "## Rancangan evaluasi",
        "",
        "Train: Januari 2017–Desember 2023 (84 bulan). Validasi: Januari–Desember 2024 (12 bulan). Uji: Januari 2025–Juni 2026 (18 bulan). Kandidat lookback 3, 6, dan 12 bulan dipilih memakai MAE validasi masing-masing deret. Model terpilih dilatih ulang pada train + validasi sebelum diuji. Setiap prediksi adalah satu bulan ke depan dengan nilai aktual bulan sebelumnya sebagai riwayat; bobot model tetap selama blok uji.",
        "",
        f"Konfigurasi tetap: tren, musiman tahunan, autoregresi, `n_forecasts=1`, seed {report['seed']}, {report['epochs']} epoch, learning rate {report['learning_rate']}. Tidak ada regressor silang atau pembanding SARIMA.",
        "",
        "## Hasil validasi dan uji",
        "",
    ])
    for target in ("bongkar", "muat"):
        result = report["series"][target]
        lines.extend([
            f"### {LABELS[target]}",
            "",
            "| Lookback (bulan) | MAE validasi (ton) | RMSE validasi (ton) | MAPE validasi (%) |",
            "| ---: | ---: | ---: | ---: |",
        ])
        for candidate in result["validation_candidates"]:
            metrics = candidate["metrics"]
            lines.append(f"| {candidate['n_lags']} | {decimal(metrics['MAE'])} | {decimal(metrics['RMSE'])} | {decimal(metrics['MAPE'])} |")
        test = result["test_metrics"]
        future = result["next_month"]
        lines.extend([
            "",
            f"Lookback terpilih: **{result['selected_n_lags']} bulan**. Pada 18 bulan uji: **MAE {decimal(test['MAE'])} ton**, **RMSE {decimal(test['RMSE'])} ton**, dan **MAPE {decimal(test['MAPE'])}%**.",
            "",
            f"Setelah dilatih ulang pada seluruh 114 bulan, prediksi untuk **{future['ds']}** adalah **{decimal(future['prediksi'])} ton**. Nilai aktual Juli 2026 tidak dipakai untuk menghasilkan angka ini.",
            "",
        ])
    lines.extend([
        "## Rincian 18 bulan uji",
        "",
        "| Bulan | Bongkar aktual | Bongkar prediksi | Muat aktual | Muat prediksi |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    bongkar = report["series"]["bongkar"]["test_predictions"]
    muat = report["series"]["muat"]["test_predictions"]
    for left, right in zip(bongkar, muat, strict=True):
        if left["ds"] != right["ds"]:
            raise ValueError("Tanggal prediksi uji kedua deret berbeda.")
        lines.append(
            f"| {left['ds']} | {decimal(left['aktual'], 0)} | {decimal(left['prediksi'])} | "
            f"{decimal(right['aktual'], 0)} | {decimal(right['prediksi'])} |"
        )
    lines.extend([
        "",
        "## Batas interpretasi",
        "",
        "Metrik di atas menggambarkan kesalahan pada 18 bulan uji dengan prosedur satu langkah yang didefinisikan. Hasil tidak membuktikan model akan memiliki kesalahan yang sama pada semua bulan mendatang. Prediksi Juli 2026 berasal dari titik akhir Juni 2026; karena nilai aktual Juli kini tersedia, hasil tersebut harus tetap dibedakan dari metrik uji yang sudah ditetapkan. Tab eksperimen memakai data terbaru dari BPS Web API tanpa mengubah hasil penelitian ini.",
        "",
        "Angka tidak dibulatkan dalam `artifacts/report.json`; pembulatan di dokumen ini hanya untuk penyajian.",
        "",
    ])
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Hasil tertulis tersimpan: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

