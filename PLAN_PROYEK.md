# Rencana lengkap proyek skripsi

**Judul final:** IMPLEMENTASI *NEURALPROPHET* UNTUK PREDIKSI VOLUME BONGKAR DAN MUAT KARGO UDARA DOMESTIK

Dokumen ini menjadi acuan penelitian, implementasi model, pengembangan aplikasi web, dan penulisan laporan. Keputusan inti di bawah mengikuti ringkasan skripsi yang diberikan. Hal yang belum selesai ditandai pada bagian **Status proyek**.

## 1. Keputusan yang sudah tetap

| Aspek | Keputusan |
| --- | --- |
| Fokus | Implementasi dan evaluasi NeuralProphet; tidak ada perbandingan dengan SARIMA atau model lain sebagai tujuan penelitian. |
| Data utama | Data bulanan publik BPS, Januari 2017–Juni 2026, tepat 114 observasi per deret. |
| Kategori pada tabel BPS | **Soekarno Hatta-Jakarta**, dipakai sebagai label data di batasan dan metodologi; penelitian tidak dinyatakan sebagai studi kasus atau penilaian institusi. |
| Target | Volume **bongkar** dan volume **muat** kargo udara domestik, masing-masing dalam ton/bulan. |
| Bentuk model | Dua model univariat independen; tidak saling memakai deret lain sebagai regressor. |
| Horizon | Satu bulan ke depan (`n_forecasts=1`). |
| Komponen | Tren, musiman tahunan, dan autoregresi. |
| Pemilihan konfigurasi | Lookback (`n_lags`) dipilih dari hasil validasi kronologis, secara terpisah untuk bongkar dan muat. |
| Evaluasi akhir | MAE, RMSE, dan MAPE pada data uji yang tidak dipakai memilih konfigurasi. |
| Produk | Aplikasi web interaktif; proses pengembangan perangkat lunak didokumentasikan dengan Waterfall. |

**Batas data penting:** berkas 2026 yang tersedia sudah berisi Juli. Juli 2026 dikeluarkan dari dataset penelitian agar tetap 114 bulan. Juli hanya dapat digunakan sebagai data tambahan pada fitur eksperimen, terpisah dari hasil resmi skripsi.

## 2. Arah BAB I dan klaim ilmiah

### Fenomena dan urgensi

Latar belakang dimulai dari dinamika kargo udara global berdasarkan [publikasi bulanan IATA](https://www.iata.org/en/publications/economics/economics-library/?EconomicsL2=147&Ordering=DateDesc&Search=&page=1), lalu mengerucut pada data kargo udara domestik Indonesia dari [tabel publik BPS](https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html). Untuk fenomena nasional, gunakan baris **TOTAL** BPS; untuk deret yang dimodelkan, gunakan label kategori yang ditetapkan di bagian data. Ukuran IATA (cargo tonne-kilometers/CTK) dan ukuran BPS (ton/bulan) berbeda; keduanya dipakai sebagai konteks pada tingkat yang berbeda, bukan dibandingkan angkanya secara langsung.

Urgensi penelitian adalah kebutuhan memperkirakan volume bulan berikutnya untuk persiapan kapasitas. Kesalahan estimasi ke bawah dan ke atas sama-sama dapat memengaruhi perencanaan. Karena itu, hasil prediksi selalu disertai ukuran kesalahan hasil pengujian. Narasi tidak menyatakan bahwa institusi tertentu belum optimal atau gagal merencanakan kapasitas.

### Deskripsi awal dua deret

Data 114 bulan telah menghasilkan angka berikut (`python audit_data.py`):

| Deret | Rentang (ton/bulan) | Rata-rata perubahan absolut bulan ke bulan | Rata-rata perubahan absolut relatif |
| --- | ---: | ---: | ---: |
| Bongkar | 2.994–14.368 | 1.154,91 ton | 14,99% |
| Muat | 8.980–25.539 | 1.682,81 ton | 10,16% |

Angka ini bisa diletakkan di akhir paragraf pertama latar belakang untuk menjelaskan perbedaan skala dan besarnya fluktuasi relatif. Gunakan rumusan deskriptif seperti **“kedua deret menunjukkan rentang nilai dan perubahan bulanan yang berbeda”**. Hindari klaim bahwa pola musiman atau mekanisme penyebabnya pasti berbeda sebelum hasil analisis mendukungnya.

### Kebaruan dan sitasi

Kebaruan yang diajukan berada pada kombinasi **NeuralProphet dan data kargo udara domestik Indonesia**, dengan dua deret bongkar dan muat yang dimodelkan terpisah. Tinjauan pustaka perlu memeriksa penelitian terdahulu sebelum menyatakan bahwa kombinasi ini belum pernah diteliti.

Saat mengutip [Triebe dkk. (2021)](https://arxiv.org/abs/2111.15397), jelaskan bahwa paper tersebut membandingkan NeuralProphet dengan **Prophet** dan melaporkan peningkatan akurasi 55–92% pada kumpulan data yang diuji penulis untuk horizon pendek hingga menengah. Angka tersebut bukan hasil penelitian ini dan bukan perbandingan dengan ARIMA/SARIMA.

### Rumusan masalah dan tujuan yang konsisten

1. Bagaimana mengimplementasikan NeuralProphet untuk prediksi volume bongkar dan volume muat kargo udara domestik satu bulan ke depan?
2. Bagaimana memilih lookback berdasarkan validasi kronologis untuk masing-masing deret?
3. Bagaimana kinerja prediksi kedua model pada data uji menurut MAE, RMSE, dan MAPE?
4. Bagaimana menyajikan data, prediksi, dan hasil evaluasi melalui aplikasi web?

Tujuan penelitian mengikuti keempat pertanyaan tersebut. Nama kategori BPS diterangkan pada batasan masalah dan metodologi, bukan dimasukkan ke judul, urgensi, atau rumusan masalah.

## 3. Sumber dan pengolahan data

**Sumber data sekunder:** unduhan CSV dari tabel statistik BPS yang sudah ada dalam folder `data/`. Snapshot berkas lokal dipakai agar eksperimen dapat direproduksi walaupun tabel web diperbarui. [Web API BPS](https://webapi.bps.go.id/documentation/) dapat dipertimbangkan sebagai fitur pembaruan pada masa depan; layanan itu memerlukan key/token dan tidak diperlukan untuk menjalankan penelitian inti.

Alur pengolahan:

1. Baca CSV tahunan 2017–2026 tanpa mengubah berkas mentah.
2. Ambil tepat satu baris berlabel **Soekarno Hatta-Jakarta** per tahun.
3. Ambil 12 kolom bulanan untuk barang yang dibongkar dan 12 kolom bulanan untuk barang yang dimuat. Abaikan total tahunan dan kategori bandara lain sebagai target.
4. Susun tabel kerja `ds,bongkar,muat`, dengan `ds` tanggal pertama setiap bulan dan nilai dalam ton.
5. Potong pada Juni 2026 dan periksa jumlah 114, kelengkapan bulan, duplikasi, nilai kosong, serta nilai tidak positif. Jika ada koreksi sumber BPS di kemudian hari, dokumentasikan versi data sebelum menjalankan ulang seluruh eksperimen.
6. Simpan dua tampilan input model: `ds,y` untuk bongkar dan `ds,y` untuk muat. Semua transformasi atau normalisasi internal NeuralProphet dipelajari dari bagian data yang sedang dilatih, bukan dari bagian validasi atau uji.

Data ekstrem, termasuk perubahan pada masa pandemi, tidak dihapus otomatis. Jika ada nilai yang tampak janggal, cocokkan dengan sumber BPS dan jelaskan hasil pemeriksaannya.

## 4. Eksplorasi dan analisis deskriptif

Untuk setiap deret, sajikan grafik bulanan 2017–Juni 2026, minimum, maksimum, rata-rata, serta perubahan absolut bulan ke bulan dalam ton dan persen. Tandai batas train, validasi, dan uji pada grafik atau tabel. Uraian hanya mendeskripsikan hal yang tampak pada data; penjelasan sebab perubahan memerlukan sumber pendukung.

Hasil bagian ini dipakai untuk memperkuat latar belakang dan membantu membaca kesalahan prediksi pada periode uji. Statistik deskriptif tidak dipakai untuk memilih lookback setelah melihat hasil uji.

## 5. Rancangan eksperimen NeuralProphet

### Pembagian kronologis

| Bagian | Rentang | Jumlah | Peran |
| --- | --- | ---: | --- |
| Train | Januari 2017–Desember 2023 | 84 bulan | Melatih kandidat model. |
| Validasi | Januari–Desember 2024 | 12 bulan | Memilih lookback dari hasil prediksi satu langkah. |
| Uji | Januari 2025–Juni 2026 | 18 bulan | Mengukur kinerja akhir satu kali setelah konfigurasi dipilih. |

Pembagian ini menjaga urutan waktu dan menyediakan satu siklus tahunan penuh pada validasi, serta 18 bulan pada uji. Keterbatasannya tetap dicatat: dataset total relatif pendek untuk model musiman dan hanya menyediakan satu blok validasi serta satu blok uji.

### Konfigurasi dan pemilihan

- Bangun **dua model NeuralProphet independen**, masing-masing dengan tren, `yearly_seasonality=True`, autoregresi, `n_forecasts=1`, dan tanpa regressor silang.
- Kandidat `n_lags`: **3, 6, dan 12 bulan**. Gunakan konfigurasi lain yang sama untuk setiap kandidat: seed 42, 100 epoch, dan learning rate 0,01. Catat juga versi paket yang dipakai.
- Latih kandidat hanya pada Januari 2017–Desember 2023. Prediksi setiap bulan pada 2024 memakai nilai aktual yang sudah tersedia sampai bulan sebelumnya. Pilih kandidat dengan **MAE validasi paling rendah** untuk masing-masing target; jika seri, pilih lookback lebih kecil.
- Setelah pilihan ditetapkan, latih ulang model terpilih pada train + validasi (Januari 2017–Desember 2024), lalu evaluasi pada 18 bulan uji. Tidak ada pemilihan ulang berdasarkan hasil uji.
- Untuk prediksi satu bulan setelah titik akhir data (Juli 2026), latih ulang model terpilih pada seluruh 114 bulan hingga Juni 2026. Prediksi dari posisi Juni tersebut disajikan terpisah dari metrik uji; nilai aktual Juli yang sudah tersedia tidak masuk ke proses pelatihannya.

### Arti prediksi satu langkah pada validasi dan uji

Pada bulan target *t*, model menggunakan tanggal *t* serta nilai aktual deret sampai *t−1* untuk komponen autoregresi. Bobot model tidak dilatih ulang tiap bulan selama blok validasi atau uji. Metode ini merepresentasikan penggunaan aplikasi ketika angka bulan sebelumnya sudah tersedia sebelum memprediksi bulan berikutnya. Tidak boleh memakai nilai aktual bulan *t* atau bulan setelahnya sebagai input prediksi untuk *t*.

### Metrik dan keluaran

Hitung metrik pada **18 pasang aktual dan prediksi uji per deret**:

- **MAE:** rata-rata nilai absolut `|aktual − prediksi|` dalam ton.
- **RMSE:** akar rata-rata kuadrat kesalahan dalam ton; lebih peka terhadap kesalahan besar.
- **MAPE:** rata-rata `|aktual − prediksi| / aktual × 100%`. Semua nilai aktual pada dataset saat ini positif, sehingga penyebutnya valid.

Simpan juga tabel bulanan aktual dan prediksi, grafik keduanya, konfigurasi terpilih, hasil tiap kandidat validasi, dan tanggal cakupan. Angka pada laporan model disimpan dengan presisi penuh; tampilan aplikasi boleh membulatkan ton untuk kemudahan baca. Tidak ada target akurasi yang dijanjikan sebelum eksperimen berjalan.

## 6. Rancangan aplikasi web

Aplikasi memakai **Python + Streamlit** dengan empat bagian:

1. **Ringkasan:** cakupan 114 bulan, grafik dua deret, prediksi Juli 2026 dari model yang dilatih sampai Juni 2026, dan ringkasan kesalahan uji.
2. **Data:** sumber BPS, tabel dan grafik, statistik deskriptif, serta unduhan CSV hasil pengolahan.
3. **Evaluasi model:** tanggal split, kandidat lookback beserta MAE validasi, konfigurasi terpilih, MAE/RMSE/MAPE uji, grafik dan tabel aktual versus prediksi, serta unduhan laporan eksperimen.
4. **Eksperimen:** pengguna dapat menambahkan Juli 2026 dari berkas yang tersedia atau mengunggah CSV bulan baru yang berurutan, lalu memilih bongkar atau muat untuk dilatih ulang satu deret per klik. Hasil keduanya dapat diperoleh secara berurutan. Hasilnya hanya untuk sesi tersebut dan diberi label **eksperimen**, sehingga tidak mengganti hasil skripsi 114 bulan.

Pelatihan tidak dijalankan setiap kali pengunjung membuka halaman atau mengubah pilihan grafik. Hasil penelitian yang sudah dihitung disimpan sebagai artefak dan dibaca aplikasi. Eksperimen resmi yang memerlukan sepuluh pelatihan hanya dijalankan lewat CLI, bukan dari web. Unggahan diperiksa format kolom, urutan bulan, kekosongan, nilai positif, ukuran 1 MB, dan batas 24 bulan tambahan. Aplikasi hanya menerima satu pekerjaan pelatihan pada satu waktu. Kegagalan input menampilkan pesan yang dapat diperbaiki pengguna.

## 7. Arsitektur dan penayangan online

Alur utama: **CSV BPS → validasi dan tabel bulanan → dua eksperimen NeuralProphet → laporan hasil → aplikasi Streamlit**. Pelatihan ulang pada tab eksperimen membaca data tambahan, memakai lookback terpilih, dan menghasilkan prediksi baru tanpa menulis ulang laporan penelitian.

Target awal adalah [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) dari repositori GitHub dengan Python 3.12 dan daftar dependensi proyek. Setelah deploy, aplikasi dapat diakses lewat URL tanpa komputer lokal menyala. [Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) menidurkan aplikasi setelah 12 jam tanpa kunjungan dan memiliki batas sumber daya; fitur pelatihan ulang harus diuji pada layanan tersebut. Jika kebutuhan akhir benar-benar server aktif tanpa jeda atau pelatihan melebihi sumber daya gratis, pindahkan aplikasi yang sama ke hosting berbayar yang sesuai.

Kunci API BPS tidak diperlukan pada rancangan ini. Jika API ditambahkan kemudian, kunci harus disimpan sebagai secret platform, bukan di kode atau repositori.

## 8. Tahapan Waterfall dan hasil tiap tahap

| Tahap | Pekerjaan | Bukti/keluaran selesai |
| --- | --- | --- |
| Analisis kebutuhan | Tetapkan dua target, horizon, dataset, alur pengguna, metrik, dan batas penelitian. | Dokumen kebutuhan dan keputusan pada bagian 1–2 ini disetujui untuk dijadikan acuan. |
| Desain | Rancang format data, split, eksperimen model, navigasi web, format laporan, serta alur unggah dan pelatihan ulang. | Diagram/alur sistem dan spesifikasi pada bagian 3–7. |
| Implementasi | Buat pemroses CSV, pipeline model, penyimpanan hasil, dan antarmuka Streamlit. | Kode yang dapat dijalankan dan laporan model yang dihasilkan dari data beku. |
| Pengujian | Uji kualitas data, prediksi tanpa kebocoran waktu, metrik, input web yang valid/tidak valid, dan aplikasi online. | Hasil uji yang terdokumentasi, grafik prediksi, serta pemeriksaan bahwa hasil skripsi tidak berubah akibat eksperimen. |
| Pemeliharaan | Perbaiki bug dan dokumentasikan cara memperbarui data atau dependensi setelah sistem selesai. | Panduan menjalankan, memperbarui, dan menayangkan aplikasi. |

Waterfall digunakan untuk **pengembangan aplikasi web**. Pemilihan lookback berdasarkan validasi adalah bagian dari rancangan eksperimen penelitian, bukan pergantian metode pengembangan perangkat lunak.

## 9. Susunan laporan skripsi

| Bab | Isi yang harus konsisten dengan proyek |
| --- | --- |
| BAB I – Pendahuluan | Fenomena IATA dan BPS, statistik deskriptif dua deret, urgensi prediksi beserta kesalahannya, rumusan masalah dan tujuan, kebaruan yang proporsional, serta batasan data publik. |
| BAB II – Tinjauan pustaka | Kargo udara domestik, peramalan deret waktu, NeuralProphet dan tiga komponennya, horizon satu bulan, MAE/RMSE/MAPE, penelitian terkait, serta konsep aplikasi web dan Waterfall. Sitasi Triebe dkk. harus tepat terhadap Prophet. |
| BAB III – Metodologi | Sumber dan rentang 114 bulan, pembentukan dua deret, alur praproses, split 84/12/18, kandidat lookback, pemilihan validasi, prosedur prediksi satu langkah, evaluasi uji, dan rancangan/pengujian aplikasi. |
| BAB IV – Hasil dan pembahasan | Grafik/statistik data, hasil pemilihan lookback tiap deret, tabel dan grafik 18 prediksi uji, MAE/RMSE/MAPE, prediksi Juli 2026 dari 114 bulan, hasil implementasi web, hasil pengujian, serta pembahasan keterbatasan. |
| BAB V – Penutup | Jawaban atas rumusan masalah berdasarkan hasil nyata, keterbatasan data dan evaluasi, serta saran pengembangan. Tidak menyimpulkan akurasi atau manfaat institusional yang belum didukung pengujian. |

## 10. Urutan pekerjaan sampai selesai

1. **Kunci dataset dan rancangan:** simpan versi 114 bulan, hasil pemeriksaan data, definisi metrik, serta konfigurasi yang akan diuji. Bagian ini pada dasarnya sudah siap dan perlu ditinjau sebelum eksperimen final.
2. **Siapkan lingkungan model yang kompatibel:** Python 3.12, dependensi terpasang, lalu catat versi paket yang benar-benar digunakan. Jangan mengisi tabel hasil dengan angka sementara.
3. **Jalankan eksperimen resmi:** pilih lookback pada validasi, latih ulang, hitung 18 hasil uji per deret, dan hasilkan prediksi Juli 2026 beserta artefak laporan yang dapat diperiksa.
4. **Verifikasi hasil:** periksa jumlah baris, rumus metrik, tidak adanya kebocoran waktu, kewajaran prediksi, serta reproduksibilitas dengan seed dan data yang sama. Perbaiki implementasi jika pemeriksaan menemukan masalah, lalu jalankan ulang seluruh hasil yang terdampak.
5. **Selesaikan dan uji aplikasi:** tampilkan hasil resmi dari artefak, uji unggah data valid/tidak valid, jalankan pelatihan ulang, serta periksa bahwa hasil skripsi tidak berubah.
6. **Deploy dan uji daring:** unggah versi yang sudah diverifikasi ke repositori GitHub, deploy ke Streamlit Community Cloud, uji akses URL dan penggunaan sumber daya. Pilih host lain jika syarat selalu aktif atau pelatihan ulang tidak terpenuhi.
7. **Tulis dan cocokkan BAB I–V:** masukkan hanya angka hasil eksperimen terverifikasi, selaraskan tabel/grafik aplikasi dengan naskah, periksa sitasi, istilah, judul, serta simpulan akhir.

## 11. Pemeriksaan sebelum hasil dinyatakan final

- Dataset inti tepat 114 bulan, dua target lengkap, rentang akhir Juni 2026; Juli tidak masuk train, validasi, uji, atau pemilihan lookback.
- Tiap model hanya menerima deret targetnya sendiri; komponen tren, musiman tahunan, dan autoregresi aktif.
- Hasil validasi dihitung pada 12 bulan 2024; pilihan lookback dicatat per deret.
- Hasil uji dihitung pada tepat 18 bulan yang belum digunakan untuk memilih konfigurasi, dengan input hanya dari masa lalu pada setiap prediksi.
- MAE, RMSE, MAPE dihitung dari pasangan aktual/prediksi yang sama; tabel hasil dapat diaudit ulang.
- Aplikasi menampilkan sumber, satuan ton, periode, konfigurasi, dan perbedaan antara hasil skripsi dan eksperimen pengguna.
- Data unggahan yang salah ditolak dengan pesan jelas; pelatihan ulang tidak mengubah artefak penelitian.
- Aplikasi terbuka melalui URL online, grafik dan tabel terbaca, serta kebutuhan memori pelatihan ulang diuji pada host yang dipilih.
- Naskah konsisten memakai frasa **“bongkar dan muat”**, termasuk sampul dan lembar pengesahan; nama kategori BPS tetap hanya pada batasan/metodologi/data.

## 12. Status proyek saat rencana ini ditulis

**Sudah disiapkan dan diuji secara lokal:** pembaca dan validator CSV BPS, statistik deskriptif, dua eksperimen NeuralProphet, laporan hasil `artifacts/report.json` dan `HASIL_EKSPERIMEN.md`, aplikasi Streamlit empat bagian, serta dokumentasi. Pemeriksaan data memastikan 114 bulan hingga Juni 2026; file sumber memiliki Juli 2026 sebagai bulan ke-115. Pengujian memeriksa tanggal dan nilai aktual uji, menghitung ulang metrik, membuktikan batas prediksi satu langkah, serta menjalankan pelatihan ulang dengan Juli sebagai data tambahan. Aplikasi berhasil dirender bersama laporan tersimpan pada pengujian lokal.

**Sudah diunggah:** kode, data sumber, dan hasil eksperimen tersedia di [repositori GitHub](https://github.com/davsantoso/neuralprophet) pada branch `main`. Lingkungan lokal Python 3.12 dan dependensi sudah tersedia. Hasil metrik dan prediksi yang sudah dihitung tercantum di [HASIL_EKSPERIMEN.md](HASIL_EKSPERIMEN.md).

**Sudah dideploy:** aplikasi berada di [prediksi-kargo-domestik.streamlit.app](https://prediksi-kargo-domestik.streamlit.app/). Pemeriksaan lokal, perbaikan pembatasan pekerjaan CPU, serta jejak data dan laporan dicatat di [PENGUJIAN_DEPLOYMENT.md](PENGUJIAN_DEPLOYMENT.md) dan [JEJAK_PENELITIAN.md](JEJAK_PENELITIAN.md).

**Sudah diverifikasi daring:** permintaan anonim dengan sesi cookie mencapai halaman aplikasi dengan HTTP 200 di URL publik. Pengujian lokal empat tab, unggah data, dan satu pelatihan ulang berhasil. **Masih perlu diverifikasi di Cloud:** interaksi widget pada versi terbaru, durasi pelatihan ulang di server, serta Cloud logs saat peringatan CPU. Rinciannya ada di [PENGUJIAN_DEPLOYMENT.md](PENGUJIAN_DEPLOYMENT.md).

