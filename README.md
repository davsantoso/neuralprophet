# Prediksi kargo udara domestik dengan NeuralProphet

Aplikasi skripsi untuk dua deret bulanan **bongkar** dan **muat** kargo udara domestik (ton/bulan). Kategori data publik BPS yang dipakai adalah **Soekarno Hatta-Jakarta**. Setiap deret dilatih sebagai model univariat tersendiri untuk memprediksi satu bulan berikutnya.

Rancangan penelitian dan pengembangan lengkap: [PLAN_PROYEK.md](PLAN_PROYEK.md).
Angka hasil validasi, uji, dan rincian prediksi bulanan: [HASIL_EKSPERIMEN.md](HASIL_EKSPERIMEN.md).
Analisis galat, tolok ukur sederhana, dan kepekaan seed: [DIAGNOSTIK_PENELITIAN.md](DIAGNOSTIK_PENELITIAN.md).
Jejak sumber, sidik jari data, dan versi lingkungan: [JEJAK_PENELITIAN.md](JEJAK_PENELITIAN.md).
Rancangan dan keputusan integrasi data langsung: [RENCANA_INTEGRASI_BPS_API.md](RENCANA_INTEGRASI_BPS_API.md).
Matriks dan hasil pengujian fungsional black-box: [PENGUJIAN_BLACK_BOX.md](PENGUJIAN_BLACK_BOX.md).

## Data dan rancangan eksperimen

Data penelitian dibekukan pada **Januari 2017–Juni 2026 (114 bulan)**. Berkas BPS di `data/` sudah memuat Juli 2026, tetapi bulan itu tidak masuk eksperimen inti. Tab Data dan Eksperimen memakai [BPS Web API](https://webapi.bps.go.id/documentation/) untuk membaca publikasi terbaru, yang mungkin telah direvisi. Sumber tabel: [BPS](https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html).

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

Untuk mengaktifkan data langsung, buat `.streamlit/secrets.toml` (sudah diabaikan Git) dengan isi:

```toml
BPS_API_KEY = "key-anda-dari-bps"
```

Nilainya adalah **key saja**, bukan URL endpoint. Pada Streamlit Community Cloud, simpan baris yang sama di **Settings → Secrets**. Jangan memasukkan key ke repositori atau mengirimkannya lewat chat. Tanpa key atau saat API gagal, tab Data menampilkan arsip penelitian yang diberi label, dan pelatihan dengan data terbaru tidak tersedia.

`train.py` dapat membuat ulang `artifacts/report.json` berisi konfigurasi, hasil validasi, prediksi dan metrik uji, serta prediksi satu bulan berikutnya. Artefak hasil saat ini sudah tersedia. Aplikasi membacanya tanpa melatih ulang saat setiap pengunjung membuka halaman. Jika berkas belum ada, buat dengan `python train.py` sebelum deploy. Jalankan `python export_results.py` setelah pelatihan untuk memperbarui `HASIL_EKSPERIMEN.md` dan `python audit_provenance.py --write` setelah meninjau perubahan untuk memperbarui sidik jari penelitian.

Jalankan `python diagnose.py` **secara offline** untuk menghitung ulang analisis tambahan. Perintah ini melatih sepuluh model (lima seed untuk masing-masing deret) dengan lookback yang sudah dipilih, lalu menulis `artifacts/diagnostics.json` dan `DIAGNOSTIK_PENELITIAN.md`. Aplikasi hanya membaca artefak tersebut; membuka tab Diagnostik tidak menjalankan pelatihan. Seed 42 mereproduksi prediksi uji resmi, dan artefak tambahan menyimpan SHA-256 data serta laporan resmi.

Uji data, parser API, antarmuka, hasil, diagnostik, batas waktu prediksi, jejak penelitian, dan pelatihan ulang dapat dijalankan lewat `python -m unittest discover -s tests -v`. `python audit_provenance.py` memeriksa bahwa CSV, laporan, dan versi lingkungan masih cocok dengan manifest. `requirements-lock.txt` merekam versi lengkap paket pada lingkungan yang menghasilkan hasil di atas.

## Interaksi aplikasi

- **Ringkasan:** grafik dua deret, prediksi Juli 2026, dan ukuran kesalahan uji.
- **Data:** grafik, statistik, tabel, dan unduhan CSV dari API BPS; pilih salah satu dari lima bandara utama, deret bongkar/muat, dan rentang tahun. Waktu pengambilan dan bulan terakhir tersedia ditampilkan.
- **Evaluasi model:** pembagian kronologis, kandidat lookback, MAE/RMSE/MAPE uji, dan grafik aktual versus prediksi.
- **Diagnostik penelitian:** galat bertanda per bulan, tiga bulan dengan galat terbesar, metrik aturan bulan sebelumnya dan bulan sama tahun lalu pada 18 bulan uji yang sama, serta variasi hasil lima seed. Analisis ini hanya untuk kategori penelitian Soekarno Hatta-Jakarta.
- **Eksperimen:** pilih bandara, target bongkar atau muat, riwayat 60/84/semua bulan, lookback 3/6/12, epoch 25/50/100, dan musiman tahunan. Data diambil dari API tanpa unggah CSV. Satu klik melatih satu deret dan memprediksi satu bulan berikutnya. Hasil dan jejak parameter dapat diunduh sebagai JSON; hasil tersimpan hanya dalam sesi pengguna dan tidak mengganti laporan skripsi.

Eksperimen satu kali pelatihan tidak memiliki metrik uji tersendiri. MAE, RMSE, dan MAPE pada tab Evaluasi model hanya berlaku bagi dua deret penelitian Soekarno Hatta-Jakarta. Aplikasi memakai cache API enam jam, satu pekerjaan pelatihan untuk semua pengunjung, dan satu thread CPU. Pelatihan NeuralProphet tetap dapat terkena batas CPU Streamlit Community Cloud; catat durasi dan periksa Cloud logs jika terjadi pembatasan.

## Menayangkan secara online

Deployment berada di [prediksi-kargo-domestik.streamlit.app](https://prediksi-kargo-domestik.streamlit.app/), dari [repositori GitHub proyek](https://github.com/davsantoso/neuralprophet), branch `main`, entrypoint `app.py`, dan Python 3.12. `.venv/`, `.python/`, dan checkpoint sementara diabaikan oleh `.gitignore`. Catatan pemeriksaan ada di [PENGUJIAN_DEPLOYMENT.md](PENGUJIAN_DEPLOYMENT.md).

Aplikasi online tidak bergantung pada laptop lokal setelah deploy. Community Cloud menidurkan aplikasi yang tidak dikunjungi selama 12 jam; pengunjung dapat membangunkannya. Pelatihan ulang memerlukan sumber daya lebih besar daripada membaca hasil tersimpan, sehingga pengujian fitur tersebut di platform hosting tetap diperlukan.

