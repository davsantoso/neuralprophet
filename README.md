# Prediksi kargo udara domestik dengan NeuralProphet

Aplikasi skripsi untuk dua deret bulanan **bongkar** dan **muat** kargo udara domestik (ton/bulan). Kategori data publik BPS yang dipakai adalah **Soekarno Hatta-Jakarta**. Setiap deret dilatih sebagai model univariat tersendiri untuk memprediksi satu bulan berikutnya.

Rancangan penelitian dan pengembangan lengkap: [PLAN_PROYEK.md](PLAN_PROYEK.md).
Angka hasil validasi, uji, dan rincian prediksi bulanan: [HASIL_EKSPERIMEN.md](HASIL_EKSPERIMEN.md).

## Data dan rancangan eksperimen

Data penelitian dibekukan pada **Januari 2017–Juni 2026 (114 bulan)**. Berkas BPS di `data/` sudah memuat Juli 2026, tetapi bulan itu hanya dapat digunakan dalam tab eksperimen aplikasi. Sumber: [tabel statistik BPS](https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html).

| Bagian | Periode | Banyak bulan | Fungsi |
| --- | --- | ---: | --- |
| Train | Jan 2017–Des 2023 | 84 | Latih kandidat `n_lags` |
| Validasi | Jan–Des 2024 | 12 | Pilih `n_lags` dengan MAE terkecil |
| Uji | Jan 2025–Jun 2026 | 18 | Evaluasi akhir MAE, RMSE, MAPE |

Kandidat lookback adalah 3, 6, dan 12 bulan. Setiap model memiliki tren, musiman tahunan, dan autoregresi (`n_forecasts=1`), dengan 100 epoch dan learning rate 0,01 yang sama. Pada validasi dan uji, `yhat1` untuk bulan tertentu memakai data aktual dari bulan-bulan sebelumnya sebagai riwayat. Parameter model tetap dibekukan sepanjang masing-masing periode evaluasi. Setelah lookback dipilih, model dilatih ulang dengan train+validasi sebelum diuji; setelah pengujian, model dilatih pada seluruh 114 bulan untuk prediksi Juli 2026. Nilai uji tidak dipakai untuk memilih lookback.

Prediksi Juli 2026 yang ditampilkan adalah prediksi yang dibuat seolah-olah data berakhir pada Juni 2026. Nilai Juli yang kini tersedia di berkas BPS tidak dimasukkan ke eksperimen inti.

| Deret | Lookback terpilih | MAE uji (ton) | RMSE uji (ton) | MAPE uji | Prediksi Juli 2026 (ton) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bongkar | 6 bulan | 1.189,47 | 1.457,03 | 13,66% | 9.768,53 |
| Muat | 3 bulan | 1.310,38 | 1.561,21 | 7,36% | 16.909,51 |

Semua angka dihitung dari model nyata dan disimpan dengan presisi penuh di `artifacts/report.json`. Metrik uji berasal dari 18 bulan uji per deret; prediksi Juli dibuat setelah model dilatih ulang pada 114 bulan.

Statistik deskriptif 114 bulan dapat diperiksa ulang dengan `python audit_data.py`:

| Deret | Minimum (ton) | Maksimum (ton) | Rata-rata perubahan absolut bulanan (ton) | Rata-rata perubahan absolut bulanan (%) |
| --- | ---: | ---: | ---: | ---: |
| Bongkar | 2.994 | 14.368 | 1.154,91 | 14,99 |
| Muat | 8.980 | 25.539 | 1.682,81 | 10,16 |

Angka tersebut menunjukkan perbedaan rentang dan besarnya perubahan relatif, sehingga dapat dipakai sebagai uraian deskriptif dua deret pada latar belakang. Angka persentase adalah rata-rata nilai absolut perubahan terhadap bulan sebelumnya.

## Menjalankan secara lokal

NeuralProphet 0.9.0 memerlukan **Python 3.9–3.12**; gunakan Python 3.12. Python 3.13 tidak dapat memasang versi tersebut.
Proyek NeuralProphet [menyarankan WSL2 untuk Windows](https://pypi.org/project/neuralprophet/); target deployment Streamlit Community Cloud berbasis Linux.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python train.py
streamlit run app.py
```

`train.py` dapat membuat ulang `artifacts/report.json` berisi konfigurasi, hasil validasi, prediksi dan metrik uji, serta prediksi satu bulan berikutnya. Artefak hasil saat ini sudah tersedia. Aplikasi membacanya tanpa melatih ulang saat setiap pengunjung membuka halaman. Jika berkas belum ada, pelatihan juga dapat dipicu dari tab **Evaluasi model**. Jalankan `python export_results.py` setelah pelatihan untuk memperbarui `HASIL_EKSPERIMEN.md`.

Uji data, hasil, batas waktu prediksi, dan pelatihan ulang dengan data Juli dapat dijalankan lewat `python -m unittest discover -s tests -v`. `requirements-lock.txt` merekam versi lengkap paket pada lingkungan yang menghasilkan hasil di atas.

## Interaksi aplikasi

- **Ringkasan:** grafik dua deret, prediksi Juli 2026, dan ukuran kesalahan uji.
- **Data:** grafik dan tabel 114 bulan, unduhan CSV, serta tautan ke sumber BPS.
- **Evaluasi model:** pembagian kronologis, kandidat lookback, MAE/RMSE/MAPE uji, dan grafik aktual versus prediksi.
- **Eksperimen:** tambahkan Juli 2026 dari berkas BPS atau unggah CSV bulan baru; latih ulang kedua model dengan lookback terpilih. Hasil eksperimen tersimpan di sesi pengguna dan tidak mengganti laporan skripsi.

CSV tambahan memakai format `ds,bongkar,muat`, misalnya:

```csv
ds,bongkar,muat
2026-08,10000,15000
```

Bulan yang diunggah harus berurutan langsung dari bulan terakhir yang sedang dipakai. Contoh angka di atas hanya menunjukkan format, bukan data BPS.

## Menayangkan secara online

1. Simpan kode, `data/`, dan `artifacts/report.json` di repositori GitHub. Jangan unggah `.venv/`, `.python/`, atau berkas checkpoint sementara; semuanya sudah diabaikan oleh `.gitignore`.
2. Buat atau masuk ke akun [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) dengan GitHub, lalu pilih repositori tersebut.
3. Pilih `app.py` sebagai entrypoint dan **Python 3.12** pada Advanced settings. Setelah deploy, buka URL aplikasi dan uji halaman utama, unduhan laporan, serta pelatihan ulang.

Aplikasi online tidak bergantung pada laptop lokal setelah deploy. Community Cloud menidurkan aplikasi yang tidak dikunjungi selama 12 jam; pengunjung dapat membangunkannya. Pelatihan ulang memerlukan sumber daya lebih besar daripada membaca hasil tersimpan, sehingga pengujian fitur tersebut di platform hosting tetap diperlukan.

