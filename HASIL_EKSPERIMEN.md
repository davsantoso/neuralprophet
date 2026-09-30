# Hasil eksperimen NeuralProphet

**Sumber:** [tabel statistik BPS](https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html), kategori data Soekarno Hatta-Jakarta. Satuan: ton per bulan.

Dataset penelitian berisi **114 bulan, Januari 2017–Juni 2026**. Deret bongkar dan muat dimodelkan secara univariat dan terpisah. Juli 2026 yang sudah ada pada berkas sumber tidak dipakai untuk melatih atau mengevaluasi hasil di bawah.

## Statistik deskriptif

| Deret | Minimum (ton) | Maksimum (ton) | Rata-rata (ton) | Rata-rata perubahan absolut bulanan (ton) | Rata-rata perubahan absolut bulanan (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bongkar | 2.994 | 14.368 | 8.335,21 | 1.154,91 | 14,99 |
| Muat | 8.980 | 25.539 | 17.010,66 | 1.682,81 | 10,16 |

## Rancangan evaluasi

Train: Januari 2017–Desember 2023 (84 bulan). Validasi: Januari–Desember 2024 (12 bulan). Uji: Januari 2025–Juni 2026 (18 bulan). Kandidat lookback 3, 6, dan 12 bulan dipilih memakai MAE validasi masing-masing deret. Model terpilih dilatih ulang pada train + validasi sebelum diuji. Setiap prediksi adalah satu bulan ke depan dengan nilai aktual bulan sebelumnya sebagai riwayat; bobot model tetap selama blok uji.

Konfigurasi tetap: tren, musiman tahunan, autoregresi, `n_forecasts=1`, seed 42, 100 epoch, learning rate 0.01. Tidak ada regressor silang atau pembanding SARIMA.

## Hasil validasi dan uji

### Bongkar

| Lookback (bulan) | MAE validasi (ton) | RMSE validasi (ton) | MAPE validasi (%) |
| ---: | ---: | ---: | ---: |
| 3 | 739,02 | 860,96 | 7,57 |
| 6 | 669,06 | 758,39 | 6,99 |
| 12 | 1.116,32 | 1.200,93 | 11,44 |

Lookback terpilih: **6 bulan**. Pada 18 bulan uji: **MAE 1.189,47 ton**, **RMSE 1.457,03 ton**, dan **MAPE 13,66%**.

Setelah dilatih ulang pada seluruh 114 bulan, prediksi untuk **2026-07** adalah **9.768,53 ton**. Nilai aktual Juli 2026 tidak dipakai untuk menghasilkan angka ini.

### Muat

| Lookback (bulan) | MAE validasi (ton) | RMSE validasi (ton) | MAPE validasi (%) |
| ---: | ---: | ---: | ---: |
| 3 | 1.631,90 | 1.882,20 | 8,29 |
| 6 | 1.633,48 | 1.910,65 | 8,36 |
| 12 | 2.077,39 | 2.393,01 | 10,28 |

Lookback terpilih: **3 bulan**. Pada 18 bulan uji: **MAE 1.310,38 ton**, **RMSE 1.561,21 ton**, dan **MAPE 7,36%**.

Setelah dilatih ulang pada seluruh 114 bulan, prediksi untuk **2026-07** adalah **16.909,51 ton**. Nilai aktual Juli 2026 tidak dipakai untuk menghasilkan angka ini.

## Rincian 18 bulan uji

| Bulan | Bongkar aktual | Bongkar prediksi | Muat aktual | Muat prediksi |
| --- | ---: | ---: | ---: | ---: |
| 2025-01 | 11.923 | 10.527,83 | 20.907 | 21.294,93 |
| 2025-02 | 9.253 | 11.013,82 | 18.985 | 21.050,17 |
| 2025-03 | 11.150 | 10.563,04 | 22.808 | 21.533,70 |
| 2025-04 | 10.224 | 10.485,24 | 19.760 | 20.622,64 |
| 2025-05 | 10.696 | 9.456,17 | 19.945 | 20.295,97 |
| 2025-06 | 7.541 | 9.840,07 | 20.466 | 19.027,97 |
| 2025-07 | 5.630 | 8.887,11 | 19.016 | 21.372,91 |
| 2025-08 | 7.477 | 8.448,58 | 19.389 | 21.328,06 |
| 2025-09 | 9.840 | 7.649,40 | 18.638 | 19.499,57 |
| 2025-10 | 10.219 | 8.118,60 | 19.409 | 18.894,47 |
| 2025-11 | 9.505 | 8.958,29 | 18.651 | 19.207,12 |
| 2025-12 | 10.791 | 11.155,86 | 18.241 | 20.509,74 |
| 2026-01 | 10.196 | 11.874,20 | 15.998 | 18.866,06 |
| 2026-02 | 10.207 | 10.279,88 | 14.966 | 17.119,54 |
| 2026-03 | 12.174 | 11.257,64 | 15.993 | 18.117,29 |
| 2026-04 | 9.912 | 10.613,81 | 16.325 | 16.132,63 |
| 2026-05 | 10.233 | 9.622,09 | 16.419 | 16.350,87 |
| 2026-06 | 9.612 | 10.067,88 | 14.855 | 16.159,54 |

## Batas interpretasi

Metrik di atas menggambarkan kesalahan pada 18 bulan uji dengan prosedur satu langkah yang didefinisikan. Hasil tidak membuktikan model akan memiliki kesalahan yang sama pada semua bulan mendatang. Prediksi Juli 2026 berasal dari titik akhir Juni 2026; karena nilai aktual Juli kini tersedia, hasil tersebut harus tetap dibedakan dari metrik uji yang sudah ditetapkan. Aplikasi menyediakan penggunaan Juli hanya pada tab eksperimen pelatihan ulang.

Angka tidak dibulatkan dalam `artifacts/report.json`; pembulatan di dokumen ini hanya untuk penyajian.
