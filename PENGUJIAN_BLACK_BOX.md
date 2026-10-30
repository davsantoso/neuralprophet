# Pengujian black-box aplikasi prediksi kargo

## Tujuan dan ruang lingkup

Pengujian black-box memeriksa **masukan pengguna dan keluaran aplikasi** tanpa menjadikan cara kerja internal model sebagai kriteria kelulusan. Objeknya adalah aplikasi Streamlit: navigasi, tampilan data, pemilihan deret dan bandara, hasil penelitian, pelatihan interaktif, dan penanganan galat. Akurasi NeuralProphet diuji terpisah melalui MAE, RMSE, dan MAPE pada 18 bulan uji, bukan melalui pengujian black-box.

Pengujian otomatis memakai `streamlit.testing.v1.AppTest` pada aplikasi lokal. Respons API BPS dan hasil pelatihan diganti dengan **fixture terkendali** agar setiap skenario dapat diulang. Fixture memiliki label lima bandara dan 115 bulan hingga Juli 2026; angkanya untuk pengujian antarmuka dan **bukan klaim angka sebenarnya untuk bandara selain Soekarno Hatta-Jakarta**. Hasil penelitian resmi tetap dibaca dari snapshot 114 bulan Januari 2017–Juni 2026 dan `artifacts/report.json`.

Lingkungan pelaksanaan: Windows, Python 3.12.13, Streamlit sesuai `requirements.txt`, 1 Oktober 2026. Berkas pelaksana: [`tests/test_black_box.py`](tests/test_black_box.py). Status di bawah adalah hasil pengujian **versi lokal** pada tanggal tersebut, bukan otomatis bukti versi yang sedang tayang di Cloud.

## Kasus uji otomatis

| ID | Masukan/tindakan pengguna | Keluaran yang diharapkan | Hasil aktual lokal | Status |
| --- | --- | --- | --- | --- |
| BB-01 | Buka aplikasi dengan respons API tersedia. | Lima tab tampil; ringkasan penelitian menunjukkan 114 observasi per deret dan prediksi Juli 2026. | Lima tab dan kedua informasi tampil. | Lulus |
| BB-02 | Buka tab Data, pilih `Ngurah Rai-Bali`. | Status data BPS sampai `2026-07`, pilihan Bali tersedia, keterangan berubah menjadi Bali dan 115 bulan. | Semua keluaran tersebut tampil. | Lulus |
| BB-03 | Pada tab Data pilih `Muat` dan rentang tahun `2025–2026`. | Keterangan menunjukkan 19 bulan; tabel tampilan hanya memiliki kolom Muat, tanpa kolom Bongkar. | 19 bulan dan kolom Muat tampil. | Lulus |
| BB-04 | Pada Evaluasi model ganti deret `Bongkar` ke `Muat`. | MAE uji berubah sesuai deret; lookback terpilih tetap ditampilkan. | MAE berubah dan keterangan lookback tampil. | Lulus |
| BB-05 | Pada Diagnostik penelitian ganti deret `Bongkar` ke `Muat`. | Rata-rata galat bertanda berubah sesuai deret. | Nilai berubah. | Lulus |
| BB-06 | API BPS mengembalikan galat saat aplikasi dibuka. | Arsip penelitian 114 observasi tetap terlihat; alasan data langsung tidak tersedia ditampilkan; tombol pelatihan tidak muncul. | Ketiga perilaku sesuai harapan. | Lulus |
| BB-07 | Di Eksperimen pilih Bali, Muat, 60 bulan, lookback 3, dan 25 epoch tanpa menekan tombol latih. | Ringkasan parameter berubah; pelatihan belum dimulai. | Ringkasan berubah dan fungsi pelatihan tidak dipanggil. | Lulus |
| BB-08 | Tekan `Latih model dan prediksi satu bulan` dengan data sampai Juli 2026; jalankan ulang tampilan tanpa mengganti masukan. | Prediksi Agustus 2026 ditampilkan; masukan yang sama tidak memicu pelatihan kedua. | Prediksi fixture `1.234 ton` tampil; pelatihan dipanggil sekali; tombol dinonaktifkan. | Lulus |
| BB-09 | Setelah BB-08, ganti bandara eksperimen. | Prediksi dari konfigurasi lama tidak ditampilkan sebagai hasil bandara baru. | Prediksi lama hilang. | Lulus |
| BB-10 | Fungsi pelatihan mengembalikan galat. | Pesan kegagalan yang aman tampil; rincian galat internal tidak dibocorkan. | Pesan umum tampil tanpa rincian internal fixture. | Lulus |
| BB-16 | Ganti deret diagnostik dari Bongkar ke Muat. | MASE berubah, komponen dan keterangan bobot AR tetap tersedia untuk deret terpilih. | MASE berubah dan komponen tampil. | Lulus, lokal 2 Oktober 2026 |
| BB-17 | Buka analisis walk-forward. | Hasil 42 bulan dan frekuensi lag tampil dari artefak tanpa pelatihan baru. | Hasil tampil; fungsi fit tidak dipanggil saat render. | Lulus, lokal 2 Oktober 2026 |
| BB-18 | Artefak MASE/komponen dan walk-forward tidak tersedia. | Hasil resmi 114 bulan tetap terlihat dan informasi analisis belum tersedia tampil. | Keduanya sesuai harapan. | Lulus, lokal 2 Oktober 2026 |
| BB-19 | Hash laporan pada artefak analisis tambahan berbeda. | Analisis tambahan ditolak dengan pesan aman; ringkasan resmi tetap terlihat. | Pesan ketidakcocokan tampil dan observasi resmi tetap 114. | Lulus, lokal 2 Oktober 2026 |
| BB-21 | Buka uji signifikansi Diebold-Mariano, lalu ganti deret dari Bongkar ke Muat. | Tabel 8 perbandingan (uji 18 bulan dan walk-forward 42 bulan) tampil dari artefak tanpa pelatihan; nilai berubah sesuai deret. | Tabel tampil dengan n = 18 dan 42; DM* berubah; fungsi fit tidak dipanggil. | Lulus, lokal 29 Oktober 2026 |
| BB-22 | Buka kurva loss dan sensitivitas epoch. | Grafik loss, tabel epoch 25/50/100/150/200 dengan 100 sebagai konfigurasi resmi, serta keterangan reproduksi uji resmi tampil. | Semua keluaran tampil. | Lulus, lokal 29 Oktober 2026 |
| BB-23 | API BPS gagal; pengguna lalu mengganti pilihan deret dua kali. | Pesan kegagalan menyebut jeda coba ulang lima menit; API tidak dipanggil ulang pada setiap interaksi. | API dipanggil sekali selama tiga kali render; pesan tampil. | Lulus, lokal 29 Oktober 2026 |
| BB-24 | API memuat bulan yang baru terbit untuk sebagian bandara. | Tab Data menjelaskan bulan yang ditahan; batas data tetap bulan terakhir yang lengkap untuk kelima bandara. | Keterangan `2026-08` tampil; status tetap sampai `2026-07`. | Lulus, lokal 29 Oktober 2026 |

Kriteria lulus: keluaran yang terlihat memenuhi semua keluaran yang diharapkan dan tidak ada exception aplikasi. Pada BB-07 dan BB-08, jumlah pemanggilan pelatihan hanya dipakai untuk membuktikan bahwa aksi tombol benar-benar mengendalikan proses. Pada BB-08 angka `1.234 ton` berasal dari fixture, sehingga **bukan** prediksi model yang dinilai benar.

## Pelaksanaan ulang dan bukti

Jalankan dari akar proyek pada Windows:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_black_box.py -v
```

Hasil 1 Oktober 2026: **10 pengujian dijalankan, 10 lulus, 0 gagal, 0 error pengujian**. Proses keluar dengan kode `0`. Pada sandbox Windows, Streamlit/AppTest mencetak traceback saat membersihkan direktori sementara setelah seluruh pengujian selesai; traceback itu terjadi sesudah ringkasan `OK` dan tidak mengubah hasil kasus uji. Simpan keluaran perintah sebagai lampiran bila kampus meminta bukti eksekusi.

Pengujian model nyata, parser API, reproduksibilitas laporan, dan provenance ada pada suite proyek yang berbeda. Jalankan seluruhnya dengan:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe audit_provenance.py
```

Pada tanggal yang sama, seluruh suite menghasilkan **26 pengujian lulus** dan audit provenance menyatakan 10 CSV, 114 bulan, laporan model, serta versi lingkungan cocok. Peringatan dependensi NeuralProphet dan traceback pembersihan sementara Windows muncul setelah pengujian, dengan kode keluar tetap `0`.

Pada **2 Oktober 2026**, versi pengayaan menghasilkan **14 kasus black-box otomatis lulus** dan **35 pengujian seluruh proyek lulus**, tanpa kasus yang dilewati. Pemeriksaan mencakup MASE dengan 95 selisih train, rekonstruksi komponen, seluruh 42 bulan kedua deret, batas waktu nested validation, dan checkpoint yang dapat dilanjutkan. Audit provenance resmi tetap lulus. Traceback pembersihan direktori sementara AppTest muncul setelah `OK`; kode keluar tetap `0`.

Pada **29 Oktober 2026**, setelah tindak lanjut audit, terdapat **18 kasus black-box otomatis** (BB-01–BB-10, BB-16–BB-19, BB-21–BB-24). Seluruh proyek berisi **52 pengujian**, dan semuanya lulus di Windows dengan Python 3.12.13 serta Streamlit 1.66.1, tanpa kasus dilewati. Audit provenance tetap cocok. Tambahan sejak 2 Oktober:

- uji Diebold-Mariano (3);
- diagnostik pelatihan (1);
- klien API dengan permintaan per tiga tahun dan bulan parsial (5);
- kecocokan dokumen hasil dengan generatornya (2);
- validasi input nol, negatif, kosong, tabel kosong, tanggal bukan tanggal 1, kolom hilang, dan riwayat eksperimen kosong atau kurang dari 60 bulan (2);
- isi ZIP grafik/tabel per deret (1);
- empat kasus black-box baru.

Aplikasi juga dirender dengan API BPS asli: status data sampai 2026-08, tanpa exception. Lingkungan Linux diperiksa terpisah (lihat [PENGUJIAN_DEPLOYMENT.md](PENGUJIAN_DEPLOYMENT.md)).

## Pemeriksaan manual di browser daring

AppTest tidak membuktikan bahwa pengunduhan berhasil di browser, respons jaringan BPS yang sebenarnya, atau kapasitas CPU Streamlit Cloud. Hasil 23 Oktober 2026 di bawah berasal dari pemeriksaan peneliti di browser, sesuai Tabel 4.17 naskah. Kolom terakhir menandai bagian yang berubah pada versi 29 Oktober dan perlu diuji ulang setelah versi itu terbit. Jangan tulis `Lulus` sebelum aksi dan hasilnya benar-benar diamati.

| ID | Langkah dan hasil yang harus dilihat | Hasil 23 Oktober 2026 (versi yang tayang saat itu, Streamlit 1.57) | Uji ulang setelah versi 29 Oktober terbit |
| --- | --- | --- | --- |
| BB-11 | Buka URL sebagai pengunjung tanpa login; tab Data menampilkan status BPS sampai bulan terbaru yang tersedia dan lima kategori bandara. | Lulus. Data BPS sampai 2026-08 dan lima kategori bandara tampil. | **Wajib**: klien API berubah (permintaan per tiga tahun). Status harus kembali hijau, bukan arsip. |
| BB-12 | Pilih Bali → Bongkar → 60 bulan → lookback 3 → 25 epoch; tekan latih sekali; bulan prediksi harus satu bulan setelah data terakhir, tanpa galat atau throttle. | Lulus. Prediksi 2026-09 sebesar 1.295 ton dalam 13,9 detik. | Disarankan, karena data API kembali dipakai. |
| BB-13 | Unduh CSV data serta JSON laporan, diagnostik, dan jejak eksperimen; buka berkas dan cocokkan bandara, target, bulan, serta parameter dengan layar. | Lulus. CSV 116 bulan (115 bulan sama dengan arsip) dan JSON sesuai. | Disarankan; jejak eksperimen kini memuat `parameter_tahun_api`. |
| BB-14 | Buka tab Diagnostik; ganti Bongkar/Muat; pastikan metrik, tolok ukur, dan tabel seed berubah sesuai deret. | Lulus. Galat bertanda 124 → 923 ton, MASE 1,070 → 0,741, lag 6 → 3. | Tidak wajib. |
| BB-15 | Coba pelatihan berat atau dua pengguna serentak; amati apakah muncul pesan antrean, galat, atau CPU throttle. | Lulus sebagian. Pelatihan terberat (116 bulan, lag 12, 100 epoch) selesai 7,0 detik; dua pengguna serentak belum diuji. | Dua pengguna serentak masih terbuka. |
| BB-20 | Pada versi pengayaan daring, buka MASE, komponen, walk-forward, uji Diebold-Mariano, serta kurva loss dan sensitivitas epoch. Unduh JSON serta ZIP grafik/tabel, lalu periksa isinya sesuai deret; ZIP harus memuat `data_114_bulan.png` dan `uji_signifikansi.csv`. | Gagal sebagian. MASE, komponen, dan walk-forward tampil dan JSON terunduh, tetapi ZIP mengembalikan HTTP 500 untuk kedua deret. | **Wajib**: expander DM dan kurva loss baru, serta ZIP. Jika ZIP masih 500, simpan Cloud logs pada jam klik (lihat catatan di bawah). |

**Penelusuran ZIP HTTP 500 (29 Oktober 2026).** Bug ini tidak dapat direproduksi di luar Cloud. Probe yang membuka sesi Streamlit seperti browser lalu mengunduh setiap URL media mendapat HTTP 200 dan ZIP valid 850.027 byte (12 berkas) pada Windows dengan Streamlit 1.57.0 dan 1.66.1, serta pada Linux dengan 1.66.1. Endpoint media Streamlit mengembalikan 404, bukan 500, untuk berkas yang tidak ditemukan. Karena itu, penyebab 500 kemungkinan berada di lapisan Cloud, bukan di kode aplikasi. Belum ada perbaikan kode yang diklaim. Tes `test_figures_bundle_is_a_valid_zip_per_series` menjaga isi ZIP. Jika uji ulang di Cloud masih 500, buka Manage app → Logs tepat setelah klik dan simpan exception-nya.

Catat per pengujian manual: tanggal/jam, URL/versi commit, browser dan perangkat, data terakhir BPS, pelaksana, hasil aktual, status, serta nama berkas bukti. Untuk BB-12, perubahan tanggal rilis BPS dapat menggeser bulan prediksi; aturan yang diuji adalah **satu bulan setelah observasi terakhir**, bukan selalu Agustus 2026.

## Naskah ringkas untuk laporan skripsi

**BAB III — metode pengujian sistem.** Pengujian fungsional aplikasi dilakukan dengan metode black-box berdasarkan hubungan masukan dan keluaran. Skenario meliputi akses ringkasan penelitian, filter data langsung BPS, pemilihan deret evaluasi dan diagnostik, pengaturan eksperimen, eksekusi pelatihan, pencegahan penggunaan hasil konfigurasi lama, serta respons saat API atau pelatihan gagal. Setiap kasus dibandingkan dengan keluaran yang diharapkan. Pengujian UI otomatis memakai fixture layanan eksternal agar skenario normal dan galat dapat diulang. Pengujian manual browser daring digunakan untuk memeriksa integrasi jaringan, unduhan, dan batas sumber daya.

**BAB IV — hasil yang sudah terbukti secara lokal.** Delapan belas kasus pengujian black-box otomatis pada versi lokal berhasil memenuhi keluaran yang diharapkan pada 29 Oktober 2026. Hasil tersebut menunjukkan bahwa fungsi antarmuka yang diuji bekerja untuk masukan dan fixture yang ditetapkan. Cakupannya meliputi tampilan MASE, komponen, walk-forward, uji Diebold-Mariano, kurva loss, penolakan artefak yang tidak cocok, jeda coba ulang saat API gagal, dan penahanan bulan yang baru terbit sebagian. Pengujian ini tidak mengukur ketepatan prediksi; ketepatan model dibahas dari metrik pada data uji kronologis dan backtest tambahan yang dilaporkan terpisah. Hasil pengujian browser daring yang belum selesai harus dilaporkan sesuai temuan aktual setelah versi yang sama diterbitkan.
