# Uji signifikansi perbedaan galat

Analisis tambahan ini menguji apakah selisih galat NeuralProphet dan aturan pembanding cukup besar untuk dibedakan dari variasi acak. Tidak ada model yang dilatih; semua prediksi diambil dari `artifacts/diagnostics.json` (uji resmi 18 bulan) dan `artifacts/walk_forward.json` (backtest 42 bulan). Hasil resmi dan pilihan konfigurasi tidak berubah.

## Metode

Uji [Diebold dan Mariano (1995)](https://doi.org/10.1080/07350015.1995.10524599) membandingkan dua ramalan dari selisih loss tiap bulan, d_t = L(e_NeuralProphet,t) − L(e_pembanding,t). Statistik DM = d̄ / √(γ̂₀ / n), dengan γ̂₀ varians d_t; untuk horizon satu bulan tidak ada suku autokovarians. Karena sampel pendek, statistik dikoreksi menurut [Harvey, Leybourne, dan Newbold (1997)](https://doi.org/10.1016/S0169-2070(96)00719-4): DM* = DM × √((n − 1) / n), lalu dibandingkan dengan distribusi t berderajat bebas n − 1, dua sisi, α = 0,05.

Loss absolut sejalan dengan MAE dan loss kuadrat sejalan dengan RMSE. Rata-rata selisih negatif berarti galat NeuralProphet lebih kecil. **p ≥ 0,05 berarti tidak ada bukti perbedaan, bukan bukti bahwa kedua metode identik.**

## Uji resmi 18 bulan

| Deret | Pembanding | Loss | n | Rata-rata selisih loss | DM* | p-value | Kesimpulan (α = 0,05) |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Bongkar | Bulan sebelumnya | Absolut (selaras MAE) | 18 | -195,09 | -0,884 | 0,3892 | Tidak berbeda signifikan |
| Bongkar | Bulan sebelumnya | Kuadrat (selaras RMSE) | 18 | -592.087,52 | -0,826 | 0,4202 | Tidak berbeda signifikan |
| Bongkar | Bulan sama tahun lalu | Absolut (selaras MAE) | 18 | 87,58 | 0,425 | 0,6759 | Tidak berbeda signifikan |
| Bongkar | Bulan sama tahun lalu | Kuadrat (selaras RMSE) | 18 | 129.726,48 | 0,236 | 0,8163 | Tidak berbeda signifikan |
| Muat | Bulan sebelumnya | Absolut (selaras MAE) | 18 | 80,33 | 0,287 | 0,7774 | Tidak berbeda signifikan |
| Muat | Bulan sebelumnya | Kuadrat (selaras RMSE) | 18 | -70.338,61 | -0,067 | 0,9477 | Tidak berbeda signifikan |
| Muat | Bulan sama tahun lalu | Absolut (selaras MAE) | 18 | -1.311,56 | -2,913 | 0,0097 | NeuralProphet lebih kecil |
| Muat | Bulan sama tahun lalu | Kuadrat (selaras RMSE) | 18 | -8.100.093,28 | -2,818 | 0,0119 | NeuralProphet lebih kecil |

## Walk-forward 42 bulan

| Deret | Pembanding | Loss | n | Rata-rata selisih loss | DM* | p-value | Kesimpulan (α = 0,05) |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Bongkar | Bulan sebelumnya | Absolut (selaras MAE) | 42 | -108,30 | -0,833 | 0,4099 | Tidak berbeda signifikan |
| Bongkar | Bulan sebelumnya | Kuadrat (selaras RMSE) | 42 | -263.966,81 | -0,670 | 0,5064 | Tidak berbeda signifikan |
| Bongkar | Bulan sama tahun lalu | Absolut (selaras MAE) | 42 | -407,94 | -3,041 | 0,0041 | NeuralProphet lebih kecil |
| Bongkar | Bulan sama tahun lalu | Kuadrat (selaras RMSE) | 42 | -862.573,17 | -2,265 | 0,0288 | NeuralProphet lebih kecil |
| Muat | Bulan sebelumnya | Absolut (selaras MAE) | 42 | 144,77 | 0,910 | 0,3683 | Tidak berbeda signifikan |
| Muat | Bulan sebelumnya | Kuadrat (selaras RMSE) | 42 | 185.823,98 | 0,300 | 0,7659 | Tidak berbeda signifikan |
| Muat | Bulan sama tahun lalu | Absolut (selaras MAE) | 42 | -1.733,97 | -4,383 | 0,0001 | NeuralProphet lebih kecil |
| Muat | Bulan sama tahun lalu | Kuadrat (selaras RMSE) | 42 | -12.516.014,99 | -4,042 | 0,0002 | NeuralProphet lebih kecil |

Metrik 42 bulan termasuk aturan bulan sama tahun lalu, yang sebelumnya belum dihitung pada backtest:

| Deret | Metode | MAE (ton) | RMSE (ton) | MAPE (%) |
| --- | --- | ---: | ---: | ---: |
| Bongkar | NeuralProphet | 836,68 | 1.136,52 | 9,66 |
| Bongkar | Bulan sebelumnya | 944,98 | 1.247,26 | 10,37 |
| Bongkar | Bulan sama tahun lalu | 1.244,62 | 1.467,74 | 14,09 |
| Muat | NeuralProphet | 1.557,37 | 1.878,61 | 8,65 |
| Muat | Bulan sebelumnya | 1.412,60 | 1.828,48 | 7,71 |
| Muat | Bulan sama tahun lalu | 3.291,33 | 4.005,64 | 18,91 |

## Batas interpretasi

Uji 18 dan 42 bulan memakai protokol berbeda dan sebagian bulan beririsan, sehingga keduanya bukan dua uji independen. Banyaknya perbandingan meningkatkan peluang satu hasil signifikan secara kebetulan; hasil dibaca sebagai pola keseluruhan, bukan satu p-value tunggal. Sampel 18 bulan memiliki daya uji rendah: selisih kecil sulit dideteksi, sehingga kesimpulan yang tepat adalah *tidak terdapat bukti perbedaan*, bukan *terbukti sama*.

SHA-256 laporan resmi: `ceb808f172f90de63350565bb661f29d75a8d9c3b8957fc5900299f8b49b0f7f`. SHA-256 snapshot kanonis: `09efd78fe3c15adf1c05683e38ba54b1c677cc1d3ec0285cf8c2c60eace69131`. Jalankan ulang dengan `python significance.py`. Tabel CSV: `artifacts/figures/uji_signifikansi.csv`.
