# Diagnostik tambahan penelitian

Analisis ini memakai **snapshot penelitian 114 bulan**, kategori data BPS **Soekarno Hatta-Jakarta**, dan periode uji **Januari 2025–Juni 2026 (18 bulan)**. Hasil resmi di `artifacts/report.json` tidak diubah. Tolok ukur sederhana dipakai untuk memberi konteks kesalahan NeuralProphet, bukan sebagai perbandingan SARIMA atau pemilihan model baru.

Setiap ramalan pembanding memakai hanya nilai aktual yang sudah tersedia sebelum bulan target: nilai bulan sebelumnya atau nilai bulan yang sama pada tahun sebelumnya. Semua metrik memakai 18 bulan dan satuan yang sama. Lihat [rujukan evaluasi deret waktu](https://otexts.com/fpp3/tscv.html).

## Tolok ukur pada periode uji yang sama

| Deret | Metode | MAE (ton) | RMSE (ton) | MAPE (%) |
| --- | --- | ---: | ---: | ---: |
| Bongkar | NeuralProphet | 1.189,47 | 1.457,03 | 13,66 |
| Bongkar | Bulan sebelumnya | 1.384,56 | 1.647,73 | 15,24 |
| Bongkar | Bulan sama tahun lalu | 1.101,89 | 1.411,81 | 12,99 |
| Muat | NeuralProphet | 1.310,38 | 1.561,21 | 7,36 |
| Muat | Bulan sebelumnya | 1.230,06 | 1.583,57 | 6,61 |
| Muat | Bulan sama tahun lalu | 2.621,94 | 3.246,14 | 15,39 |

NeuralProphet tidak menjadi yang terbaik pada semua metrik. Pada bongkar, aturan bulan yang sama tahun lalu memiliki MAE dan MAPE lebih rendah. Pada muat, aturan bulan sebelumnya memiliki MAE dan MAPE lebih rendah, sedangkan NeuralProphet memiliki RMSE sedikit lebih rendah. Ini adalah temuan pada 18 bulan uji, bukan bukti bahwa satu metode selalu lebih baik pada periode lain.

## Arah dan bulan kesalahan terbesar

### Bongkar

Galat bertanda didefinisikan sebagai prediksi dikurangi aktual. Rata-ratanya **124,25 ton**, sehingga arah rata-rata adalah **terlalu tinggi**. Prediksi lebih tinggi pada 10 bulan dan lebih rendah pada 8 bulan. Angka ini menggambarkan bias pada periode uji, tanpa menjelaskan penyebabnya.

| Bulan | Aktual (ton) | Prediksi (ton) | Galat (ton) | APE (%) |
| --- | ---: | ---: | ---: | ---: |
| 2025-07 | 5.630 | 8.887,11 | 3.257,11 | 57,85 |
| 2025-06 | 7.541 | 9.840,07 | 2.299,07 | 30,49 |
| 2025-09 | 9.840 | 7.649,40 | -2.190,60 | 22,26 |

### Muat

Galat bertanda didefinisikan sebagai prediksi dikurangi aktual. Rata-ratanya **922,90 ton**, sehingga arah rata-rata adalah **terlalu tinggi**. Prediksi lebih tinggi pada 13 bulan dan lebih rendah pada 5 bulan. Angka ini menggambarkan bias pada periode uji, tanpa menjelaskan penyebabnya.

| Bulan | Aktual (ton) | Prediksi (ton) | Galat (ton) | APE (%) |
| --- | ---: | ---: | ---: | ---: |
| 2026-01 | 15.998 | 18.866,06 | 2.868,06 | 17,93 |
| 2025-07 | 19.016 | 21.372,91 | 2.356,91 | 12,39 |
| 2025-12 | 18.241 | 20.509,74 | 2.268,74 | 12,44 |

## Kepekaan terhadap seed pelatihan

Lima seed diuji dengan lookback yang **sudah dipilih pada validasi resmi seed 42** (bongkar 6, muat 3), 100 epoch, musiman tahunan aktif, data latih sampai Desember 2024, dan 18 bulan uji yang sama. Seed tidak dipilih berdasarkan hasil uji. Ringkasan ini mengukur variasi pelatihan pada konfigurasi tetap; tidak mengukur ketidakpastian prediksi atau kestabilan pemilihan lookback.

| Deret | Seed | MAE (ton) | RMSE (ton) | MAPE (%) |
| --- | ---: | ---: | ---: | ---: |
| Bongkar | 7 | 1.259,01 | 1.902,82 | 15,10 |
| Bongkar | 21 | 1.115,76 | 1.486,45 | 13,00 |
| Bongkar | 42 | 1.189,47 | 1.457,03 | 13,66 |
| Bongkar | 123 | 1.273,29 | 1.680,17 | 13,70 |
| Bongkar | 2026 | 1.138,46 | 1.505,14 | 13,71 |
| Muat | 7 | 1.224,63 | 1.451,82 | 6,68 |
| Muat | 21 | 1.269,32 | 1.450,08 | 7,10 |
| Muat | 42 | 1.310,38 | 1.561,21 | 7,36 |
| Muat | 123 | 1.715,48 | 2.292,24 | 10,01 |
| Muat | 2026 | 1.261,71 | 1.401,52 | 6,97 |

| Deret | Metrik | Rata-rata | Simpangan baku sampel | Minimum | Maksimum |
| --- | --- | ---: | ---: | ---: | ---: |
| Bongkar | MAE | 1.195,20 | 70,24 | 1.115,76 | 1.273,29 |
| Bongkar | RMSE | 1.606,32 | 187,25 | 1.457,03 | 1.902,82 |
| Bongkar | MAPE | 13,84 | 0,77 | 13,00 | 15,10 |
| Muat | MAE | 1.356,31 | 203,08 | 1.224,63 | 1.715,48 |
| Muat | RMSE | 1.631,37 | 374,03 | 1.401,52 | 2.292,24 |
| Muat | MAPE | 7,62 | 1,36 | 6,68 | 10,01 |

Kelima hasil berbagi periode uji yang sama sehingga bukan lima sampel uji independen. Sebaran seed tidak boleh ditafsirkan sebagai interval kepercayaan kinerja masa depan. Perbedaan prediksi seed 42 terhadap laporan resmi dicatat dalam JSON untuk memeriksa reproduksi.

## Jejak dan batas interpretasi

SHA-256 laporan resmi: `ceb808f172f90de63350565bb661f29d75a8d9c3b8957fc5900299f8b49b0f7f`. SHA-256 tabel penelitian kanonik: `09efd78fe3c15adf1c05683e38ba54b1c677cc1d3ec0285cf8c2c60eace69131`. Prediksi bulanan, metrik lengkap, dan semua seed tersedia di `artifacts/diagnostics.json`. Jalankan `python diagnose.py` untuk menghitung ulang secara offline.

Analisis ini bersifat tambahan setelah laporan inti dibuat. Pembandingan tidak dipakai untuk mengubah pilihan lookback, seed resmi, metrik utama, atau prediksi Juli 2026. Interpretasi di BAB IV sebaiknya menekankan bahwa hasil ini berlaku pada kategori dan periode yang diuji.
