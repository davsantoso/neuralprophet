"""Export thesis-ready figures, tables and discussion from verified artifacts."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mpl-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


LABELS = {"bongkar": "Bongkar", "muat": "Muat"}
METHODS = {"neuralprophet": "NeuralProphet", "last_month": "Bulan sebelumnya", "same_month_last_year": "Bulan sama tahun lalu"}


def fmt(value, digits=2):
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def save_plot(fig, target, name):
    fig.tight_layout()
    fig.savefig(ROOT / "artifacts" / "figures" / f"{target}_{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    report_bytes = (ROOT / "artifacts/report.json").read_bytes()
    report = json.loads(report_bytes)
    extra = json.loads((ROOT / "artifacts/enrichment.json").read_text(encoding="utf-8"))
    walk = json.loads((ROOT / "artifacts/walk_forward.json").read_text(encoding="utf-8"))
    diag = json.loads((ROOT / "artifacts/diagnostics.json").read_text(encoding="utf-8"))
    if extra["source"] != walk["source"] or extra["source"]["report_sha256"] != hashlib.sha256(report_bytes).hexdigest():
        raise ValueError("Artefak ekspor tidak cocok dengan laporan resmi.")
    figures = ROOT / "artifacts/figures"
    figures.mkdir(exist_ok=True)
    lines = ["# Pengayaan analisis penelitian", "",
             "Analisis tambahan ini memakai snapshot 114 bulan Soekarno Hatta-Jakarta. Hasil resmi pada `artifacts/report.json` tetap mengikuti split 84/12/18 dan tidak dipilih ulang dari hasil analisis ini.", "",
             "## Konfigurasi dan batas tuning", "",
             "| Parameter | Nilai | Status |", "| --- | --- | --- |",
             "| n_lags | 3, 6, 12 | Dipilih berdasarkan MAE validasi; bongkar 6, muat 3 pada eksperimen resmi |",
             "| ar_layers | [] | Tetap; AR linear tanpa hidden layer |",
             "| n_changepoints | 10 | Tetap; lokasi kandidat otomatis |",
             "| epochs | 100 | Tetap |", "| learning_rate | 0,01 | Tetap |",
             "| Musiman | Tahunan aktif; mingguan/harian nonaktif | Tetap |",
             "| Seed | 42 | Resmi; lima seed dianalisis terpisah pada konfigurasi resmi |", "",
             "Pemilihan konfigurasi pada eksperimen ini hanya mencakup lookback. Tidak ada klaim bahwa semua parameter NeuralProphet telah dioptimalkan. Grid besar pada 12 bulan validasi berisiko memilih konfigurasi yang kebetulan cocok. AR-Net nonlinear dan intervensi pandemi tidak ditambahkan agar kompleksitas model tetap sesuai rancangan yang diuji.", "",
             "## MASE pada 18 bulan uji resmi", "",
             "MASE = MAE uji / rata-rata |y_t − y_(t−1)| pada data latih Januari 2017–Desember 2024. Penyebut memakai 95 selisih dari 96 bulan; data uji tidak masuk penyebut. [Hyndman dan Koehler (2006)](https://otext.robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/).", "",
             "| Deret | Metode | MAE uji (ton) | MASE | Penyebut (ton) |", "| --- | --- | ---: | ---: | ---: |"]
    for target in LABELS:
        mase = extra["series"][target]["mase"]
        for method, value in mase["methods"].items():
            lines.append(f"| {LABELS[target]} | {METHODS[method]} | {fmt(diag['series'][target]['metrics'][method]['MAE'])} | {fmt(value, 3)} | {fmt(mase['scale_ton'])} |")
    lines += ["", "NeuralProphet mengungguli naif bulan sebelumnya pada MAE bongkar, tetapi kalah pada muat. Aturan bulan sama tahun lalu juga mengungguli NeuralProphet pada MAE bongkar. MASE < 1 berarti kesalahan lebih kecil daripada skala naif *data latih*; hal itu tidak otomatis berarti mengalahkan naif pada *data uji*.", "", "## Sensitivitas lag, residual, dan komponen", ""]
    for target, label in LABELS.items():
        item = extra["series"][target]
        component = item["components"]
        candidates = report["series"][target]["validation_candidates"]
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.plot([r["n_lags"] for r in candidates], [r["metrics"]["MAE"] for r in candidates], marker="o")
        selected = next(r for r in candidates if r["n_lags"] == report["series"][target]["selected_n_lags"])
        ax.scatter([selected["n_lags"]], [selected["metrics"]["MAE"]], color="#c65b45", s=70, label="Terpilih", zorder=3)
        ax.legend()
        ax.set(xlabel="Lookback (bulan)", ylabel="MAE validasi (ton)", title=f"{label}: sensitivitas pada validasi 2024", xticks=[3, 6, 12])
        ax.grid(alpha=0.25)
        save_plot(fig, target, "sensitivitas_lag")
        monthly = pd.DataFrame(diag["series"][target]["monthly"])
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
        axes[0].plot(pd.to_datetime(monthly["ds"]), monthly["error"], marker="o")
        axes[0].axhline(0, color="black", linewidth=0.8)
        axes[0].set(title=f"{label}: residual uji", ylabel="Prediksi − aktual (ton)", xlabel="Bulan")
        axes[0].tick_params(axis="x", rotation=45)
        acf = item["residual"]["acf"]
        axes[1].bar([r["lag"] for r in acf], [r["acf"] for r in acf])
        axes[1].set(xlabel="Lag (bulan)", ylabel="ACF residual", ylim=(-1, 1), xticks=[1, 2, 3], title="Deskriptif; 18 titik")
        save_plot(fig, target, "residual")
        timeline = pd.DataFrame(component["timeline"])
        dates = pd.to_datetime(timeline["ds"])
        fig, axes = plt.subplots(3, 1, figsize=(9, 8))
        axes[0].plot(dates, timeline["trend"])
        for index, cp in enumerate(component["potential_changepoints"]):
            axes[0].axvline(pd.Timestamp(cp["date"]), color="#b55c45", alpha=0.25,
                            label="Kandidat changepoint" if index == 0 else None)
        axes[0].set(title=f"{label}: komponen model yang dilatih sampai Desember 2024", ylabel="Tren (ton)")
        axes[1].plot(dates, timeline["yearly"])
        axes[1].set(ylabel="Musiman tahunan (ton)")
        axes[2].plot(dates, timeline["ar"])
        axes[2].set(ylabel="Kontribusi AR (ton)", xlabel="Bulan")
        for axis in axes:
            axis.axvline(pd.Timestamp("2025-01-01"), color="black", linestyle="--", alpha=0.5,
                        label="Awal uji" if axis is axes[0] else None)
            axis.grid(alpha=0.2)
        axes[0].legend(fontsize=9)
        save_plot(fig, target, "komponen")
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.bar([r["lag"] for r in component["ar_weights"]], [r["weight"] for r in component["ar_weights"]])
        ax.set(title=f"{label}: bobot AR linear", xlabel="Lag (bulan sebelumnya)", ylabel="Koefisien normalisasi")
        save_plot(fig, target, "bobot_ar")
        timeline.to_csv(figures / f"{target}_komponen.csv", index=False)
        pd.DataFrame(component["ar_weights"]).to_csv(figures / f"{target}_bobot_ar.csv", index=False)
        lines += [f"### {label}", "", f"Model interpretasi mereproduksi prediksi uji resmi dengan selisih maksimum {fmt(component['max_forecast_difference_ton'], 6)} ton. Komponen tahunan rata-rata pada data latih tertinggi di bulan {component['yearly_peak_month']} dan terendah di bulan {component['yearly_low_month']}. Lag dengan bobot absolut terbesar adalah {component['largest_absolute_ar_lag']} bulan. Bobot tidak mengukur pengaruh sebab akibat.", "", "| Lag residual | ACF |", "| ---: | ---: |"]
        lines += [f"| {row['lag']} | {fmt(row['acf'], 3)} |" for row in acf]
        strongest = max(acf, key=lambda row: abs(row["acf"]))
        training_timeline = timeline.loc[timeline["ds"] <= "2024-12"]
        low = training_timeline.loc[training_timeline["trend"].idxmin()]
        high = training_timeline.loc[training_timeline["trend"].idxmax()]
        lines += ["", f"ACF absolut terbesar di antara lag 1–3 berada pada lag {strongest['lag']}: {fmt(strongest['acf'], 3)}. Nilai ini menggambarkan hubungan dalam sampel galat yang kecil; tidak dijadikan uji signifikansi atau bukti keacakan.", "",
                  f"Pada rentang data latih, komponen tren minimum berada pada {low['ds']} sebesar {fmt(low['trend'])} ton dan maksimum pada {high['ds']} sebesar {fmt(high['trend'])} ton. Angka ini adalah komponen yang dipelajari model, bukan minimum/maksimum volume aktual."]
        lines += ["", "| Bulan galat terbesar | Perubahan aktual dari bulan lalu (%) | Galat prediksi (ton) |", "| --- | ---: | ---: |"]
        lines += [f"| {row['ds']} | {fmt((row['actual'] / row['last_month'] - 1) * 100)} | {fmt(row['error'])} |"
                  for row in diag["series"][target]["largest_errors"]]
        lines += ["", f"![Sensitivitas {label}](artifacts/figures/{target}_sensitivitas_lag.png)", "", f"![Residual {label}](artifacts/figures/{target}_residual.png)", "", f"![Komponen {label}](artifacts/figures/{target}_komponen.png)", "", "| Lokasi kandidat changepoint | Perubahan kemiringan (ton/bulan nominal) |", "| --- | ---: |"]
        lines += [f"| {row['date']} | {fmt(row['slope_change_ton_per_nominal_month'])} |" for row in component["potential_changepoints"]]
        lines += [""]
    lines += ["ACF memakai residual yang dipusatkan pada rata-rata; 18 titik membatasi penilaian pola galat. ACF rendah tidak membuktikan galat acak. Kandidat changepoint ditempatkan otomatis dan parameternya tidak membuktikan perubahan struktural yang signifikan. Satu bulan nominal = 365,25/12 hari. Volume aktual tertinggi/terendah berbeda dari kontribusi musiman tertinggi/terendah.", "",
              "Garis konteks Maret 2020 pada aplikasi merujuk [pernyataan WHO 11 Maret 2020](https://www.who.int/news-room/speeches/item/who-director-general-s-opening-remarks-at-the-media-briefing-on-covid-19---11-march-2020). Tidak ada dummy pandemi atau penghapusan nilai masa pandemi. Penyebab kesalahan 2025–2026 tidak boleh diasumsikan sebagai pandemi.", "",
              "## Backtest nested walk-forward 42 bulan", "",
              "Target Januari 2023–Juni 2026. Pada setiap origin, tiga kandidat lag dilatih pada prefix sebelum 12 bulan validasi terakhir. MAE validasi memilih lag; kandidat terpilih kemudian dilatih ulang sampai origin dan memprediksi satu bulan berikutnya. Origin pertama Desember 2022 memiliki train dalam 60 bulan dan validasi Januari–Desember 2022. Sebanyak 336 fit dijalankan offline, dengan seed 42 dan konfigurasi tetap. Checkpoint dapat dilanjutkan; pelatihan tidak dijalankan di Cloud.", "",
              "| Deret | Metode | MAE 42 bulan (ton) | RMSE (ton) | MAPE (%) |", "| --- | --- | ---: | ---: | ---: |"]
    for target, label in LABELS.items():
        item = walk["series"][target]
        for method, metric in item["metrics"]["all_42"].items():
            lines.append(f"| {label} | {METHODS[method]} | {fmt(metric['MAE'])} | {fmt(metric['RMSE'])} | {fmt(metric['MAPE'])} |")
        frame = pd.DataFrame(item["monthly"])
        fig, ax = plt.subplots(figsize=(10, 4))
        for field, caption in (("actual", "Aktual"), ("neuralprophet", "NeuralProphet"), ("last_month", "Naif bulan sebelumnya")):
            ax.plot(pd.to_datetime(frame["ds"]), frame[field], label=caption, linewidth=1.4)
        ax.set(title=f"{label}: backtest 42 bulan", xlabel="Bulan target", ylabel="Ton")
        ax.legend()
        ax.grid(alpha=0.2)
        save_plot(fig, target, "walk_forward")
        frame.to_csv(figures / f"{target}_walk_forward.csv", index=False)
    lines += ["", "Periode 42 bulan dan model yang diperbarui berbeda dari uji resmi 18 bulan. Metriknya dilaporkan terpisah, tidak dijumlahkan dengan uji resmi dan bukan uji independen kedua. Pemilihan lag setiap origin hanya memakai masa lalu; nilai aktual bulan target dipakai setelah prediksi untuk menghitung error.", ""]
    for target, label in LABELS.items():
        counts = walk["series"][target]["lag_counts"]
        lines += [f"{label}: " + "; ".join(f"lag {lag} dipilih {count} kali" for lag, count in counts.items()) + ".", "", f"![Walk-forward {label}](artifacts/figures/{target}_walk_forward.png)", ""]
    lines += ["## Reproduksi dan penggunaan dalam naskah", "",
              "Jalankan `python enrich.py`, `python walk_forward.py --workers 4`, lalu `python export_enrichment.py` dari lingkungan Python 3.12. Worker lokal masing-masing memakai satu thread CPU; gunakan `--workers 1` untuk beban lebih kecil. Checkpoint ada di `.tmp/` yang diabaikan Git. Artefak akhir ada di `artifacts/enrichment.json` dan `artifacts/walk_forward.json`; grafik PNG serta tabel CSV ada di `artifacts/figures/`.", "",
              "BAB II: jelaskan AR linear, MASE, dan prinsip origin bergulir. BAB III: pertahankan prosedur resmi, lalu jelaskan protokol tambahan dan batas data tiap origin. BAB IV: bahas kemenangan/kekalahan terhadap baseline, variasi lag, residual, komponen, serta hasil 42 bulan. BAB V: batasi klaim pada kategori dan periode yang diuji; hindari klaim kausal dari bobot atau changepoint.", "",
              f"SHA-256 laporan resmi: `{extra['source']['report_sha256']}`. SHA-256 snapshot kanonis: `{extra['source']['data_sha256']}`.", ""]
    lines += ["## Pilihan yang tidak ditambahkan", "", "| Usulan | Alasan keputusan |", "| --- | --- |",
              "| Grid n_changepoints, epoch, learning rate, dan ar_layers | Validasi resmi 12 bulan; pencarian besar berisiko memilih kecocokan kebetulan. Parameter tetap dilaporkan terbuka. |",
              "| AR-Net dengan hidden layer | Sampel 114 bulan terbatas; AR linear lebih mudah dijelaskan melalui bobot lag. Tidak ada klaim bahwa linear selalu lebih baik. |",
              "| Dummy atau koreksi pandemi | Memerlukan definisi intervensi dan mengubah eksperimen utama; penanda konteks saja tidak menambah variabel model. |",
              "| Lima seed untuk seluruh walk-forward | Memperbesar 336 fit menjadi 1.680 fit. Lima seed pada konfigurasi resmi sudah memberi analisis variasi pelatihan yang terbatas dan jelas. |",
              "| Walk-forward dihitung di Cloud | Beban pelatihan berulang mengganggu respons aplikasi; hasil dihitung offline dan dibaca dari artefak. |",
              "| MASE/backtest mengganti metrik resmi | Protokol dan periode baru dilaporkan sebagai pelengkap agar hasil resmi tetap dapat diaudit. |", ""]
    (ROOT / "PENGAYAAN_PENELITIAN.md").write_text("\n".join(lines), encoding="utf-8")
    print("Dokumen, grafik PNG, dan tabel CSV pengayaan tersimpan.")


if __name__ == "__main__":
    main()
