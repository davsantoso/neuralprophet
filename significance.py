"""Uji Diebold-Mariano offline dari prediksi yang sudah tersimpan; tanpa pelatihan."""

import csv
import hashlib
import json
from pathlib import Path

from cargo_forecast.data import load_bps_data
from cargo_forecast.significance import BASELINES, LOSS_LABELS, LOSSES, PROTOCOLS, build_significance, verdict
from cargo_forecast.walkforward import atomic_json


ROOT = Path(__file__).resolve().parent
LABELS = {"bongkar": "Bongkar", "muat": "Muat"}
METHODS = {"neuralprophet": "NeuralProphet", "last_month": "Bulan sebelumnya", "same_month_last_year": "Bulan sama tahun lalu"}


def fmt(value, digits=2):
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def main():
    report_path = ROOT / "artifacts/report.json"
    original = report_path.read_bytes()
    diagnostics = json.loads((ROOT / "artifacts/diagnostics.json").read_text(encoding="utf-8"))
    walk_forward = json.loads((ROOT / "artifacts/walk_forward.json").read_text(encoding="utf-8"))
    result = build_significance(load_bps_data(ROOT / "data"), diagnostics, walk_forward,
                                report_sha256=hashlib.sha256(original).hexdigest())
    if report_path.read_bytes() != original:
        raise ValueError("Laporan resmi berubah selama analisis.")
    atomic_json(ROOT / "artifacts/significance.json", result)

    rows = []
    for target in LABELS:
        for protocol in PROTOCOLS:
            for baseline in BASELINES:
                for loss in LOSSES:
                    item = result["series"][target][protocol]["comparisons"][baseline][loss]
                    rows.append({"deret": target, "protokol": protocol, "pembanding": baseline, "loss": loss,
                                 "n": item["n"], "rata_selisih_loss": item["mean_loss_difference"],
                                 "dm_hln": item["dm_hln"], "p_value": item["p_value"], "kesimpulan": verdict(item)})
    with (ROOT / "artifacts/figures/uji_signifikansi.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = ["# Uji signifikansi perbedaan galat", "",
             "Analisis tambahan ini menguji apakah selisih galat NeuralProphet dan aturan pembanding cukup besar untuk dibedakan dari variasi acak. Tidak ada model yang dilatih; semua prediksi diambil dari `artifacts/diagnostics.json` (uji resmi 18 bulan) dan `artifacts/walk_forward.json` (backtest 42 bulan). Hasil resmi dan pilihan konfigurasi tidak berubah.", "",
             "## Metode", "",
             "Uji [Diebold dan Mariano (1995)](https://doi.org/10.1080/07350015.1995.10524599) membandingkan dua ramalan dari selisih loss tiap bulan, d_t = L(e_NeuralProphet,t) − L(e_pembanding,t). Statistik DM = d̄ / √(γ̂₀ / n), dengan γ̂₀ varians d_t; untuk horizon satu bulan tidak ada suku autokovarians. Karena sampel pendek, statistik dikoreksi menurut [Harvey, Leybourne, dan Newbold (1997)](https://doi.org/10.1016/S0169-2070(96)00719-4): DM* = DM × √((n − 1) / n), lalu dibandingkan dengan distribusi t berderajat bebas n − 1, dua sisi, α = 0,05.", "",
             "Loss absolut sejalan dengan MAE dan loss kuadrat sejalan dengan RMSE. Rata-rata selisih negatif berarti galat NeuralProphet lebih kecil. **p ≥ 0,05 berarti tidak ada bukti perbedaan, bukan bukti bahwa kedua metode identik.**", ""]
    for protocol, title in PROTOCOLS.items():
        lines += [f"## {title}", "",
                  "| Deret | Pembanding | Loss | n | Rata-rata selisih loss | DM* | p-value | Kesimpulan (α = 0,05) |",
                  "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |"]
        for row in rows:
            if row["protokol"] != protocol:
                continue
            lines.append(f"| {LABELS[row['deret']]} | {METHODS[row['pembanding']]} | {LOSS_LABELS[row['loss']]} | {row['n']} | "
                         f"{fmt(row['rata_selisih_loss'])} | {fmt(row['dm_hln'], 3)} | {fmt(row['p_value'], 4)} | {row['kesimpulan']} |")
        lines.append("")
        if protocol == "walk_forward_42":
            lines += ["Metrik 42 bulan termasuk aturan bulan sama tahun lalu, yang sebelumnya belum dihitung pada backtest:", "",
                      "| Deret | Metode | MAE (ton) | RMSE (ton) | MAPE (%) |", "| --- | --- | ---: | ---: | ---: |"]
            for target in LABELS:
                for method, metrics in result["series"][target]["walk_forward_42"]["metrics"].items():
                    lines.append(f"| {LABELS[target]} | {METHODS[method]} | {fmt(metrics['MAE'])} | {fmt(metrics['RMSE'])} | {fmt(metrics['MAPE'])} |")
            lines.append("")
    lines += ["## Batas interpretasi", "",
              "Uji 18 dan 42 bulan memakai protokol berbeda dan sebagian bulan beririsan, sehingga keduanya bukan dua uji independen. Banyaknya perbandingan meningkatkan peluang satu hasil signifikan secara kebetulan; hasil dibaca sebagai pola keseluruhan, bukan satu p-value tunggal. Sampel 18 bulan memiliki daya uji rendah: selisih kecil sulit dideteksi, sehingga kesimpulan yang tepat adalah *tidak terdapat bukti perbedaan*, bukan *terbukti sama*.", "",
              f"SHA-256 laporan resmi: `{result['source']['report_sha256']}`. SHA-256 snapshot kanonis: `{result['source']['data_sha256']}`. Jalankan ulang dengan `python significance.py`. Tabel CSV: `artifacts/figures/uji_signifikansi.csv`.", ""]
    (ROOT / "UJI_SIGNIFIKANSI.md").write_text("\n".join(lines), encoding="utf-8")
    print("Tersimpan: artifacts/significance.json, artifacts/figures/uji_signifikansi.csv, UJI_SIGNIFIKANSI.md")


if __name__ == "__main__":
    main()
