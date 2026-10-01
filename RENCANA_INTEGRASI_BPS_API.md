# Rencana integrasi BPS Web API dan eksperimen interaktif

**Status 1 Oktober 2026:** integrasi API, tampilan lima bandara, pelatihan dengan parameter pilihan, jejak eksperimen, dan pengujian lokal telah diimplementasikan pada commit `489152c`. Pengguna telah memverifikasi dari browser publik bahwa data API tampil dan pelatihan ringan Ngurah Rai-Bali menghasilkan prediksi Agustus 2026. Batas CPU Cloud untuk pilihan paling berat belum terukur; rincian bukti ada di [PENGUJIAN_DEPLOYMENT.md](PENGUJIAN_DEPLOYMENT.md).

## Tujuan dan batas tetap

Aplikasi akan mengambil data asli BPS melalui Web API untuk tampilan data dan eksperimen prediksi terbaru. Pengunjung dapat memilih salah satu kategori bandara utama, termasuk Ngurah Rai-Bali, memilih deret bongkar atau muat, mengatur konfigurasi NeuralProphet dalam batas yang aman, lalu melatih satu model untuk memprediksi **satu bulan setelah data BPS terakhir yang tersedia**. Pengunjung tidak perlu mengunggah CSV.

Eksperimen resmi skripsi **tetap** memakai snapshot CSV Januari 2017–Juni 2026 (114 bulan) kategori Soekarno Hatta-Jakarta, split 84/12/18, pilihan lookback validasi, hasil uji MAE/RMSE/MAPE, dan artefak `artifacts/report.json`. Data API yang lebih baru atau direvisi tidak menimpa angka tersebut. Hasil bandara lain dan konfigurasi pengguna diberi label **eksperimen**, bukan hasil penelitian resmi.

## 1. Verifikasi API setelah key tersedia

Endpoint awal yang diberikan pengguna adalah `https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/2351/th/126/key/{KEY}`. Menurut [dokumentasi BPS](https://webapi.bps.go.id/documentation/), `model/data` mengembalikan metadata `var`, `turvar`, `vervar`, `tahun`, `turtahun`, dan `datacontent`. `domain/0000` adalah domain pusat. Dokumentasi memberi contoh `th_id=117` untuk 2017, sehingga `126` diperkirakan menunjuk 2026; label pada respons harus menjadi sumber verifikasi akhirnya.

Langkah pembuktian pertama:

1. Panggil data 2026 dengan key melalui server, tanpa menampilkan URL berkunci pada log atau antarmuka.
2. Pastikan `var/2351` benar-benar tabel **bongkar dan muat barang angkutan udara dalam negeri di lima bandara utama**, satuan ton.
3. Petakan ID dan label `vervar` untuk lima bandara bernama; petakan `turvar` untuk bongkar dan muat serta `turtahun` untuk bulan. Jangan menebak posisi digit pada kunci `datacontent` sebelum respons nyata diperiksa.
4. Cocokkan beberapa titik dengan snapshot CSV, misalnya Juni 2026 Soekarno Hatta-Jakarta (bongkar 9.612; muat 14.855 ton) dan Juli 2026 Ngurah Rai-Bali (bongkar 1.521; muat 874 ton). Jika BPS telah merevisi nilai, catat selisih sebagai revisi sumber; jangan memaksa API mengikuti snapshot.
5. Uji pengambilan beberapa tahun (`th` rentang atau daftar ID sesuai kemampuan endpoint) dan penanganan bulan yang belum dirilis. Batas request atau pagination tidak diasumsikan sebelum diuji dengan key.

## 2. Lapisan data API

Bangun modul `cargo_forecast/bps_api.py` yang melakukan permintaan HTTPS dari server dengan timeout, retry terbatas, pemeriksaan status dan skema respons, serta pesan kesalahan yang ramah. Key dibaca dari `st.secrets` atau variabel lingkungan `BPS_API_KEY`; key tidak disimpan di Git dan tidak dikirim ke browser. Jangan log URL lengkap karena key berada pada path endpoint.

Normalisasi respons menjadi tabel `ds,bandara,bongkar,muat` dengan satuan ton per bulan. Nama bandara berasal dari metadata API, bukan daftar label yang diketik ulang. Pilihan pelatihan menampilkan hanya lima bandara bernama; agregat seperti `TOTAL` dan `Bandara Lainnya` boleh ditampilkan sebagai konteks data, tetapi tidak dicampur dengan kategori bandara. Validasi bulan berurutan, nilai numerik positif, duplikasi, label, dan periode terakhir tersedia. Respons API di-cache per variabel/periode selama sekitar 6 jam agar perubahan pilihan bandara tidak memanggil BPS berulang. Tampilkan waktu akses dan bulan terakhir publikasi secara terpisah.

Jika API gagal, halaman data boleh menampilkan snapshot lokal dengan label **data arsip**, waktu cakupan, dan penjelasan gangguan. Tombol **latih dengan data terbaru** dinonaktifkan sampai respons API valid, agar pengguna tidak mengira arsip adalah data terkini.

## 3. Perubahan antarmuka

| Bagian | Perubahan |
| --- | --- |
| Ringkasan penelitian | Tetap menampilkan hasil resmi dari 114 bulan, prediksi Juli 2026 yang dibuat dari data hingga Juni, dan ukuran kesalahan uji. Beri label jelas bahwa ini hasil penelitian yang dibekukan. |
| Data BPS langsung | Pilih bandara, deret bongkar/muat atau keduanya, dan rentang tahun. Tampilkan grafik, tabel, sumber API, bulan terakhir tersedia, waktu pengambilan, serta unduh CSV hasil API. |
| Evaluasi penelitian | Tetap hanya untuk dua model resmi Soekarno Hatta-Jakarta. Metriknya tidak ditempelkan pada bandara atau konfigurasi lain. |
| Eksperimen prediksi | Pilih bandara dan satu target; ambil deret terkini dari API; pilih parameter dalam batas; tampilkan ringkasan input sebelum tombol latihan; latih satu model; tampilkan bulan dan nilai prediksi, durasi, parameter, serta sumber data. Hapus kebutuhan unggah CSV dan pilihan manual Juli setelah API terbukti bekerja. |

## 4. Parameter eksperimen dan kendali sumber daya

Parameter awal yang dapat diubah: panjang riwayat (seluruh data tersedia atau 60/84 bulan terakhir), `n_lags` (3, 6, 12), epoch (25, 50, 100), dan musiman tahunan aktif/nonaktif. Learning rate tetap 0,01 pada versi pertama agar pilihan tidak terlalu banyak; dapat ditambahkan sebagai opsi lanjutan setelah uji kestabilan. Tren tetap aktif, setiap model tetap univariat, dan horizon tetap **satu bulan**. Default eksperimen ditampilkan sebagai pilihan aplikasi, bukan konfigurasi yang diklaim optimal untuk semua bandara.

Minimal 60 bulan lengkap diperlukan untuk pilihan riwayat eksperimen. Batasi satu pekerjaan pelatihan untuk seluruh aplikasi, satu bandara dan satu target per klik, satu thread CPU, dan tolak klik ulang untuk kombinasi data serta parameter yang identik dalam sesi. Simpan hasil kecil berdasarkan sidik jari data dan konfigurasi untuk menghindari perhitungan yang sama berulang; model tidak perlu dipertahankan di memori setelah prediksi. Catat durasi dan kegagalan secara aman tanpa mencatat key. [Community Cloud dapat memperlambat aplikasi yang melewati batas CPU atau memori](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app); uji beban nyata tetap menjadi gerbang sebelum fitur ini dinyatakan stabil.

Prediksi eksperimen yang hanya memakai satu pelatihan **tidak mempunyai MAE/RMSE/MAPE uji baru**. Antarmuka harus mengatakannya secara jelas. Metrik resmi skripsi tidak boleh dipakai seolah mengukur kualitas konfigurasi pilihan pengguna. Jika pengujian historis per konfigurasi kelak diperlukan, itu menjadi pekerjaan dan biaya komputasi terpisah.

## 5. Jejak setiap hasil eksperimen

Tampilkan dan sediakan unduhan JSON berisi: URL sumber tanpa key, waktu respons API, label bandara, target, satuan, bulan awal/akhir, jumlah observasi, hash data yang dipakai, parameter, seed, versi paket, durasi, bulan prediksi, dan nilai prediksi. Hasil disimpan hanya dalam sesi dan unduhan pengguna; database belum diperlukan. Data atau hasil penelitian resmi tidak dimodifikasi.

## 6. Pengujian dan kriteria selesai

1. **Parser API:** uji respons contoh dari BPS, lima label bandara, dua deret, bulan parsial tahun berjalan, data kosong, data revisi, respons gagal, dan key tidak pernah muncul di pesan/log.
2. **Kesesuaian sumber:** bandingkan titik API terhadap CSV arsip; dokumentasikan revisi bila ada. Hasil resmi tetap identik sebelum dan sesudah integrasi.
3. **Alur pengguna:** memilih Bali memperbarui grafik tanpa melatih; memilih parameter tidak memulai pelatihan; satu klik melatih satu target dan menghasilkan tepat satu bulan berikutnya; perubahan bandara/parameter menghapus label hasil lama yang tidak relevan.
4. **Daring:** uji di Streamlit Cloud sebagai pengunjung, termasuk waktu buka halaman, cache API, kegagalan jaringan, satu pelatihan parameter ringan dan berat, durasi, Cloud logs, dan apakah CPU kembali terkena throttle. Jika satu pelatihan tetap tidak layak di Community Cloud, pindahkan pekerjaan pelatihan ke layanan komputasi terpisah sambil menjaga halaman data dan hasil resmi di Streamlit.

## Urutan implementasi

1. Dapatkan key dan simpan sebagai secret lokal/Cloud. Verifikasi skema respons nyata dan peta ID tahun/bandara/jenis kargo.
2. Implementasikan klien API, parser, validasi, cache, serta pengujian unit memakai respons contoh tanpa key.
3. Ubah tab Data menjadi pembaca API dengan penanda kesegaran dan fallback arsip.
4. Ubah tab Eksperimen menjadi pilihan bandara, target, dan parameter; hapus unggah CSV; pertahankan pengunci CPU.
5. Uji seluruh alur lokal dan daring, perbarui README/diagram/metodologi aplikasi, lalu rilis. Eksperimen resmi 114 bulan dan metriknya diperiksa tetap sama.
