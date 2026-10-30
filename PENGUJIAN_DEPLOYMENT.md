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

## Pengayaan penelitian: 2 Oktober 2026, lokal

MASE, ACF galat uji, komponen tren/musiman/AR, bobot lag, kandidat changepoint, dan grafik sensitivitas lag sudah ditambahkan. Kedua model interpretasi mereproduksi seluruh prediksi resmi dengan selisih maksimum 0 ton. Nested walk-forward selesai untuk 42 bulan per deret, Januari 2023–Juni 2026, dengan tiga kandidat lag dan refit tiap origin. Setiap origin memakai 12 bulan validasi yang telah berlalu; 336 fit dijalankan offline. Checkpoint dan pemilihan lag berdasarkan masa lalu diuji otomatis.

Seluruh **35 tes** lulus pada Python 3.12.13, termasuk **14 kasus black-box**. Audit provenance resmi tetap cocok. Sepuluh PNG dan enam CSV penelitian telah diekspor dari artefak yang diverifikasi. Aplikasi membaca hasil prahitung; membuka analisis ini tidak melatih model. Aksi widget baru dan unduhan ZIP belum diuji langsung di browser Cloud. Versi pengayaan masih merupakan perubahan lokal sampai diterbitkan.


## Perbaikan hash artefak: 16 Oktober 2026

Pengguna melaporkan tab Diagnostik menampilkan penolakan hash laporan. Penyebab terkonfirmasi: `core.autocrlf=true` mengubah laporan CRLF lokal menjadi LF dalam Git, sehingga SHA-256 deployment berbeda meskipun seluruh isi JSON sama. Aturan `.gitattributes` kini mempertahankan byte laporan resmi dan CSV mentah. Laporan ditambahkan ulang dengan byte asli yang cocok dengan ketiga artefak tambahan dan manifest; tidak ada pelatihan ulang atau perubahan angka.

Salinan bersih dibuat dari Git index dengan `core.autocrlf=false`, tanpa secret lokal. Ketiga hash sumber cocok, seluruh isi JSON laporan sama dengan versi sebelumnya, dan seluruh 35 pengujian lulus, termasuk tab Diagnostik, MASE, komponen, walk-forward, dan penolakan analisis yang benar-benar tidak cocok. Pengujian antarmuka kini memasok key dummy untuk fixture agar tidak bergantung pada secret lokal. Pemeriksaan ini memakai checkout dengan konfigurasi akhir baris deployment, dijalankan pada Python Windows; bukan pengujian langsung browser Cloud atau runtime Linux. Hasil browser Cloud setelah penerbitan belum diverifikasi.

## Tindak lanjut audit: 29 Oktober 2026, lokal

**API BPS sempat tidak berfungsi.** Permintaan lama `th/117,126` kini ditolak BPS dengan HTTP 400. Aturan barunya: rentang memakai `:`, dan satu permintaan paling banyak tiga tahun. Akibatnya, tab Data dan Eksperimen versi daring sebelumnya kemungkinan jatuh ke arsip. Klien kini mengambil `117:119`, `120:122`, `123:125`, dan `126`, lalu menggabungkannya.

Pemeriksaan langsung dengan key lokal:
- 580 baris, 5 bandara, data sampai Agustus 2026, pembaruan BPS 2026-10-01;
- seluruh 230 nilai Soekarno Hatta 2017-01–2026-07 identik dengan CSV arsip;
- aplikasi dirender dengan API asli tanpa exception, dan kelima expander analisis tambahan tampil.

**Perubahan deployment:**
- `requirements.txt` kini mengunci semua dependensi turunan ke `requirements-lock.txt` (`-c`).
- Di Linux x86_64, `torch` dipasang dari wheel CPU (`2.14.0+cpu`). Sebelumnya Cloud ikut menarik 18 paket CUDA/NVIDIA. Resolusi `uv` untuk Linux menghasilkan 72 paket tanpa CUDA, identik dengan lock file kecuali `colorama` (khusus Windows). Untuk Windows hasilnya identik dengan lock file, dan `.venv` lokal tidak berubah.
- Jika API gagal, aplikasi menunggu lima menit sebelum mencoba lagi.
- Pelatihan eksperimen menghapus folder `lightning_logs` miliknya setelah selesai.
- Devcontainer kini memakai Python 3.12 dan proteksi XSRF bawaan Streamlit.

**Hasil pengujian:**
- Windows: 49 tes lulus; audit provenance cocok. Setelah tes validasi input dan tes isi ZIP ditambahkan, jumlahnya menjadi 52 dan semuanya lulus.
- Simulasi CI di Ubuntu (WSL), Python 3.12, paket dari `requirements.txt`: 48 dari 49 tes lulus pada percobaan pertama. Tes yang gagal membandingkan p-value Diebold-Mariano secara persis, padahal pustaka matematika Linux berbeda di digit ke-16. Tes itu kini memakai toleransi relatif 1e-12 dan lulus di Linux.
- `test_provenance` lulus di Linux dengan `CI=true`. Hash CSV dan laporan cocok byte per byte pada checkout Linux; hanya versi Python/torch yang berbeda dari lingkungan penelitian.

**Belum terverifikasi di Cloud (perlu dicek setelah push ke `main`):**
- log build tidak memuat paket `nvidia-*`;
- aplikasi terbuka dan tab Data menampilkan status sampai bulan terbaru;
- satu pelatihan ringan berhasil;
- GitHub Actions `Tes` hijau.

**Kronologi API:** pada pemeriksaan browser 23 Oktober 2026 (Tabel 4.17 naskah), tab Data masih menampilkan data BPS sampai 2026-08. Permintaan dengan format lama baru terbukti ditolak pada 29 Oktober, jadi perubahan aturan BPS terjadi di antara kedua tanggal itu.

## Penelusuran unduhan ZIP (HTTP 500), 29 Oktober 2026

Pada uji browser 23 Oktober, unduhan ZIP grafik/tabel gagal dengan HTTP 500 untuk kedua deret, sedangkan semua unduhan CSV dan JSON berhasil. Penelusuran dengan probe yang membuka sesi Streamlit lewat WebSocket seperti browser, lalu mengunduh setiap URL media tombol:

| Lingkungan | Streamlit | Hasil ZIP |
| --- | --- | --- |
| Windows, lokal | 1.57.0 (versi lock 23 Oktober) | 200, 850.027 byte, ZIP valid berisi 12 berkas |
| Windows, lokal | 1.66.1 | 200, 850.027 byte |
| Linux (WSL Ubuntu), lokal | 1.66.1 | 200, 850.027 byte |

Endpoint media Streamlit mengembalikan 404, bukan 500, untuk berkas yang tidak ditemukan. Berkas unduhan juga mendapat masa tenggang satu siklus sebelum dihapus. Jadi HTTP 500 tidak berasal dari jalur kode yang dapat direproduksi. Dugaan terkuat adalah lapisan Cloud (proxy di depan aplikasi) atau kondisi sesaat di server Cloud.

Probe langsung ke Cloud tidak dapat membentuk WebSocket dari luar browser, karena proxy menolak handshake. Belum ada perbaikan kode yang diklaim. Tes isi ZIP ditambahkan sebagai pengaman. Setelah versi baru terbit, uji ulang ZIP. Jika masih 500, simpan Cloud logs pada jam klik.
