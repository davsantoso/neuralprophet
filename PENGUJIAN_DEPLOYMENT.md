# Catatan pengujian aplikasi

URL: https://prediksi-kargo-domestik.streamlit.app/  
Sumber deployment: `davsantoso/neuralprophet`, branch `main`, `app.py`.

## Pemeriksaan lokal integrasi API, 1 Oktober 2026

| Alur | Hasil |
| --- | --- |
| Key lokal | `.streamlit/secrets.toml` telah dibetulkan menjadi TOML valid berisi key saja; berkas tetap diabaikan Git. |
| BPS Web API `var/2351`, tahun 2017–2026 | Respons OK; 575 baris = 5 bandara × 115 bulan sampai Juli 2026, dua nilai kargo per baris. Label dan ID berasal dari metadata API. |
| Kesesuaian dengan arsip | Seluruh 575 kombinasi bandara-bulan dan kedua nilainya sama dengan 10 CSV lokal (0 perbedaan). Contoh: Soekarno Hatta Juni 2026: bongkar 9.612, muat 14.855 ton; Ngurah Rai-Bali Juli 2026: bongkar 1.521, muat 874 ton. |
| Tiga belas pengujian otomatis | Lulus pada Python 3.12, termasuk parser, pesan kesalahan tanpa key, pilihan Bali di UI, kegagalan API dengan arsip tetap terlihat, hasil penelitian yang dibekukan, dan pelatihan ulang. |
| Pelatihan eksplorasi nyata | Data API Ngurah Rai-Bali, 60 bulan, bongkar, lookback 3, 25 epoch, musiman tahunan aktif: prediksi Agustus 2026 berhingga; pelatihan lokal 2,94 detik. |
| Hasil penelitian resmi | `artifacts/report.json` dan snapshot 114 bulan tidak diubah. |

Perintah pengujian: `python -m unittest discover -s tests -v` dan `python audit_provenance.py`.

AppTest pada sandbox Windows kadang menampilkan traceback pembersihan direktori sementara saat proses Python keluar, walaupun pengujian selesai dan exit code 0. Ini berkaitan dengan izin direktori sementara sandbox lokal.

## Pemeriksaan daring

Commit integrasi `489152c` sudah diunggah ke `main`. Setelah pengunggahan, permintaan anonim dengan sesi cookie dalam memori mengikuti pengalihan Streamlit dan berakhir pada HTTP 200. HTTP 200 hanya memastikan halaman dasar dapat dijangkau, bukan bahwa widget dan data API berhasil dirender. Aksi widget langsung di Cloud belum dapat diotomatisasi dari lingkungan ini karena browser computer use tidak tersedia dan koneksi Streamlit WebSocket tidak dapat dibentuk dari jalur jaringan tersebut.

Fitur API versi ini memerlukan `BPS_API_KEY` di **Settings → Secrets** Streamlit Community Cloud; pengguna menyatakan secret sudah disimpan. Pada 1 Oktober 2026, pengguna membuka URL publik dan melaporkan bahwa tab Data menampilkan status hijau data API sampai Juli 2026 serta pilihan Ngurah Rai-Bali. Pengguna juga menjalankan eksperimen Ngurah Rai-Bali → Bongkar → 60 bulan → lookback 3 → 25 epoch dan melaporkan prediksi Agustus 2026 muncul. Ini memverifikasi alur baca data dan satu pelatihan ringan dari sisi pengunjung.

Unduhan CSV/JSON, seluruh kombinasi bandara dan parameter, serta 100 epoch pada CPU Cloud belum diuji langsung dari browser. Perilaku throttle untuk beban terberat masih perlu dipantau saat penggunaan nyata.

Pengguna pernah melaporkan banner CPU throttle pada versi sebelumnya. Banner saja tidak menunjukkan penyebab; log Cloud saat kejadian belum tersedia. Pengujian lokal satu pelatihan tidak membuktikan batas CPU Cloud aman. Catat durasi serta Cloud logs setelah pelatihan daring. Jika satu pelatihan ringan masih terkena throttle, pindahkan pekerjaan pelatihan ke layanan komputasi lain dan pertahankan tampilan data serta hasil penelitian di Streamlit.

## Diagnostik tambahan: pemeriksaan lokal

Sepuluh pelatihan offline untuk lima seed pada kedua deret selesai pada Python 3.12. Seed 42 mereproduksi seluruh 18 prediksi uji resmi per deret dengan selisih maksimum **0 ton**. Tolok ukur bulan sebelumnya dan bulan sama tahun lalu dihitung dari nilai yang mendahului tiap bulan uji. Artefak `artifacts/diagnostics.json` memiliki SHA-256 data yang cocok dengan `artifacts/provenance.json`, sementara `artifacts/report.json` tetap. Enam belas pengujian otomatis, termasuk pembatasan data latih seed sampai Desember 2024, lulus secara lokal. Tab Diagnostik lima bagian juga lulus Streamlit AppTest ketika API langsung gagal. Versi tab tambahan ini belum diuji di Cloud sampai perubahan diterbitkan.
