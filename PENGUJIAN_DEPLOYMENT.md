# Catatan pengujian aplikasi

URL: https://prediksi-kargo-domestik.streamlit.app/  
Sumber deployment: `davsantoso/neuralprophet`, branch `main`, `app.py`.

## Pemeriksaan lokal, 1 Oktober 2026

| Alur | Hasil |
| --- | --- |
| Sembilan pengujian otomatis: alur UI, data, unggahan, jejak penelitian, laporan, batas waktu prediksi, dan pelatihan ulang Juli | Lulus pada Python 3.12 lokal; uji UI dapat diulang melalui `python -m unittest discover -s tests -p test_app.py -v`. |
| Render aplikasi dengan Streamlit AppTest | Empat tab muncul, tanpa exception. |
| Centang Juli 2026 | Menampilkan 115 observasi hingga 2026-07, tanpa exception dan tanpa memulai pelatihan. |
| Unggah CSV valid untuk Agustus 2026 setelah mencentang Juli | Diterima sebagai 116 observasi hingga 2026-08, tanpa exception. |
| CSV tidak berurutan, lebih dari 24 bulan, atau lebih dari 1 MB | Ditolak oleh pengujian validator. |
| Unggah CSV September 2026 langsung setelah Juli melalui antarmuka | Ditolak dengan pesan “Data tambahan harus dimulai dari 2026-08.”, tanpa exception. |
| Klik pelatihan ulang bongkar setelah mencentang Juli | Menghasilkan prediksi Agustus 2026 sebesar 10.592 ton, tanpa exception; durasi yang ditampilkan 5,4 detik pada komputer lokal. |

AppTest pada sandbox Windows menampilkan traceback pembersihan direktori sementara saat proses Python keluar, walaupun semua pemeriksaan antarmuka di atas selesai dan exit code proses 0. Ini tidak muncul pada proses aplikasi Linux di Cloud; penyebabnya adalah izin direktori sementara sandbox lokal.

## Pemeriksaan daring

Pada pemeriksaan awal, respons pertama URL adalah HTTP 303 menuju layanan autentikasi Streamlit. Pemeriksaan itu **tidak cukup untuk menyimpulkan aplikasi privat**. Pada 1 Oktober 2026, permintaan anonim dengan sesi cookie dalam memori mengikuti tiga pengalihan dan berakhir pada **HTTP 200**, host `prediksi-kargo-domestik.streamlit.app`, path `/`, berisi shell HTML aplikasi. Pengguna juga berhasil membuka dan melihat aplikasi melalui halaman browser lain. Akses publik ke halaman aplikasi dengan demikian terverifikasi; aksi widget langsung di Cloud belum dapat diotomatisasi dari lingkungan ini.

Pengguna melaporkan banner CPU throttle, termasuk ketika mencentang Juli. Centang Juli pada kode hanya membaca CSV; banner tersebut belum cukup untuk menentukan proses yang menghabiskan CPU. Teks Cloud logs dari panel **Manage app** saat kejadian belum tersedia. Pembatasan CPU satu deret per klik sudah diuji lokal, tetapi dampaknya pada Cloud belum terukur.

Setelah kode terbaru terpasang, periksa secara interaktif di Cloud: halaman utama, kedua grafik, tabel sumber, unduhan CSV/JSON, pergantian deret evaluasi, centang Juli, unggah CSV valid/tidak valid, satu pelatihan bongkar, satu pelatihan muat, serta pesan ketika pekerjaan lain sedang berlangsung. Catat durasi pelatihan dan Cloud logs. Jika satu pelatihan masih terkena throttle, pertahankan aplikasi baca hasil di Community Cloud dan pindahkan pekerjaan pelatihan interaktif ke host dengan CPU yang memadai.
