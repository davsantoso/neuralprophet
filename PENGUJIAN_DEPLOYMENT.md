# Catatan pengujian aplikasi

URL: https://prediksi-kargo-domestik.streamlit.app/  
Sumber deployment: `davsantoso/neuralprophet`, branch `main`, `app.py`.

## Pemeriksaan lokal integrasi API, 1 Oktober 2026

| Alur | Hasil |
| --- | --- |
| Key lokal | `.streamlit/secrets.toml` telah dibetulkan menjadi TOML valid berisi key saja; berkas tetap diabaikan Git. |
| BPS Web API `var/2351`, tahun 2017–2026 | Respons OK; 575 baris = 5 bandara × 115 bulan sampai Juli 2026, dua nilai kargo per baris. Label dan ID berasal dari metadata API. |
| Kesesuaian dengan arsip | Seluruh 575 kombinasi bandara-bulan dan kedua nilainya sama dengan 10 CSV lokal (0 perbedaan). Contoh: Soekarno Hatta Juni 2026: bongkar 9.612, muat 14.855 ton; Ngurah Rai-Bali Juli 2026: bongkar 1.521, muat 874 ton. |
| Dua belas pengujian otomatis | Lulus pada Python 3.12, termasuk parser, pesan kesalahan tanpa key, pilihan Bali di UI, hasil penelitian yang dibekukan, dan pelatihan ulang. |
| Pelatihan eksplorasi nyata | Data API Ngurah Rai-Bali, 60 bulan, bongkar, lookback 3, 25 epoch, musiman tahunan aktif: prediksi Agustus 2026 berhingga; pelatihan lokal 2,94 detik. |
| Hasil penelitian resmi | `artifacts/report.json` dan snapshot 114 bulan tidak diubah. |

Perintah pengujian: `python -m unittest discover -s tests -v` dan `python audit_provenance.py`.

AppTest pada sandbox Windows kadang menampilkan traceback pembersihan direktori sementara saat proses Python keluar, walaupun pengujian selesai dan exit code 0. Ini berkaitan dengan izin direktori sementara sandbox lokal.

## Pemeriksaan daring

Sebelum integrasi API, permintaan anonim dengan sesi cookie dalam memori mengikuti pengalihan Streamlit dan berakhir pada HTTP 200. Pengguna juga dapat membuka aplikasi melalui browser lain. Aksi widget langsung di Cloud belum dapat diotomatisasi dari lingkungan ini.

Fitur API versi ini memerlukan `BPS_API_KEY` di **Settings → Secrets** Streamlit Community Cloud; secret lokal tidak otomatis ikut terunggah. Setelah kode terpasang dan secret disimpan, periksa sebagai pengunjung: lima pilihan bandara, nilai Bali, waktu data API, unduhan CSV, pilihan parameter tanpa pelatihan otomatis, satu pelatihan ringan, unduhan jejak JSON, dan tab hasil penelitian yang tetap 114 bulan.

Pengguna pernah melaporkan banner CPU throttle pada versi sebelumnya. Banner saja tidak menunjukkan penyebab; log Cloud saat kejadian belum tersedia. Pengujian lokal satu pelatihan tidak membuktikan batas CPU Cloud aman. Catat durasi serta Cloud logs setelah pelatihan daring. Jika satu pelatihan ringan masih terkena throttle, pindahkan pekerjaan pelatihan ke layanan komputasi lain dan pertahankan tampilan data serta hasil penelitian di Streamlit.
