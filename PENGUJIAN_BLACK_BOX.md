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

## Pemeriksaan manual di browser daring

AppTest tidak membuktikan bahwa pengunduhan berhasil di browser, respons jaringan BPS yang sebenarnya, atau kapasitas CPU Streamlit Cloud. Isi tabel ini saat melakukan pengujian pada `https://prediksi-kargo-domestik.streamlit.app/` setelah versi dengan tab Diagnostik diterbitkan. Jangan tulis `Lulus` sebelum aksi dan hasilnya benar-benar diamati.

| ID | Langkah dan hasil yang harus dilihat | Status saat dokumen dibuat | Bukti yang perlu disimpan |
| --- | --- | --- | --- |
| BB-11 | Buka URL sebagai pengunjung tanpa login; tab Data menampilkan status BPS sampai bulan terbaru yang tersedia dan lima kategori bandara. | Sebagian terverifikasi pada versi sebelumnya: pengguna melaporkan API tampil dan pilihan Bali. Perlu ulang pada versi baru. | Tangkapan layar URL, tanggal/jam, status Data, pilihan bandara. |
| BB-12 | Pilih Bali → Bongkar → 60 bulan → lookback 3 → 25 epoch; tekan latih sekali; bulan prediksi harus satu bulan setelah data terakhir, tanpa galat atau throttle. | Sebagian terverifikasi pada versi sebelumnya: pengguna melaporkan prediksi muncul. Perlu ulang pada versi baru. | Tangkapan layar parameter, hasil, durasi, dan Cloud logs bila ada galat. |
| BB-13 | Unduh CSV data serta JSON laporan, diagnostik, dan jejak eksperimen; buka berkas dan cocokkan bandara, target, bulan, serta parameter dengan layar. | Belum diuji dari browser. | Empat berkas unduhan dan tangkapan layar parameter. |
| BB-14 | Buka tab Diagnostik; ganti Bongkar/Muat; pastikan metrik, tolok ukur, dan tabel seed berubah sesuai deret. | Belum diuji di Cloud karena versi ini belum diterbitkan. | Tangkapan layar kedua pilihan. |
| BB-15 | Coba pelatihan berat atau dua pengguna serentak; amati apakah muncul pesan antrean, galat, atau CPU throttle. | Belum diuji; hindari klaim kapasitas Cloud sebelum pengamatan. | Jam kejadian, parameter, durasi, dan Cloud logs. |

Catat per pengujian manual: tanggal/jam, URL/versi commit, browser dan perangkat, data terakhir BPS, pelaksana, hasil aktual, status, serta nama berkas bukti. Untuk BB-12, perubahan tanggal rilis BPS dapat menggeser bulan prediksi; aturan yang diuji adalah **satu bulan setelah observasi terakhir**, bukan selalu Agustus 2026.

## Naskah ringkas untuk laporan skripsi

**BAB III — metode pengujian sistem.** Pengujian fungsional aplikasi dilakukan dengan metode black-box berdasarkan hubungan masukan dan keluaran. Skenario meliputi akses ringkasan penelitian, filter data langsung BPS, pemilihan deret evaluasi dan diagnostik, pengaturan eksperimen, eksekusi pelatihan, pencegahan penggunaan hasil konfigurasi lama, serta respons saat API atau pelatihan gagal. Setiap kasus dibandingkan dengan keluaran yang diharapkan. Pengujian UI otomatis memakai fixture layanan eksternal agar skenario normal dan galat dapat diulang. Pengujian manual browser daring digunakan untuk memeriksa integrasi jaringan, unduhan, dan batas sumber daya.

**BAB IV — hasil yang sudah terbukti secara lokal.** Sepuluh kasus pengujian black-box otomatis pada versi lokal berhasil memenuhi keluaran yang diharapkan. Hasil tersebut menunjukkan fungsi antarmuka yang diuji bekerja untuk masukan dan fixture yang ditetapkan. Pengujian ini tidak mengukur ketepatan prediksi; ketepatan model dibahas dari MAE, RMSE, dan MAPE pada data uji kronologis. Hasil pengujian browser daring yang belum selesai harus dilaporkan sesuai temuan aktual setelah versi yang sama diterbitkan.
