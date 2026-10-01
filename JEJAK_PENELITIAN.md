# Jejak penelitian dan reproduksi hasil

## Snapshot data

Sumber adalah [tabel statistik BPS tentang bongkar dan muat barang angkutan udara dalam negeri di lima bandara utama](https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html). Penelitian memakai baris berlabel **Soekarno Hatta-Jakarta**, satuan ton per bulan. Sepuluh CSV tahunan di `data/` disimpan sebagai snapshot eksperimen resmi. Aplikasi memanggil API BPS untuk tampilan data terkini dan eksperimen pengguna; respons itu tidak mengganti snapshot maupun laporan resmi.

Tanggal pengunduhan awal CSV tidak tercatat, sehingga tidak dinyatakan sebagai tanggal yang pasti. Sidik jari SHA-256 setiap CSV mentah dicatat di [`artifacts/provenance.json`](artifacts/provenance.json). Berkas 2026 memuat Juli, tetapi dataset penelitian dipotong pada **Juni 2026**: tepat 114 bulan dari Januari 2017. Data setelah batas ini hanya dapat digunakan dalam eksperimen pengguna yang dipisahkan dari hasil resmi.

## Rantai hasil

`audit_provenance.py` membaca ulang CSV, membentuk tabel kanonis `ds,bongkar,muat`, mencatat SHA-256 tabel 114 bulan dan `artifacts/report.json`, memeriksa 18 aktual uji per deret terhadap CSV, serta mencatat versi Python dan paket utama. Manifest juga menyimpan split, kandidat dan pilihan lookback, seed, epoch, learning rate, serta horizon prediksi. Ini memungkinkan pemeriksa mendeteksi bila sumber, hasil, atau lingkungan berubah.

Artefak tambahan [`artifacts/diagnostics.json`](artifacts/diagnostics.json) mencatat SHA-256 snapshot kanonis dan laporan resmi, galat bulanan, dua aturan prediksi sederhana pada 18 bulan uji, serta lima hasil pelatihan per deret dengan seed berbeda. Lookback 6 dan 3 bulan tetap mengikuti validasi resmi seed 42. `python diagnose.py` menghitungnya ulang secara offline; artefak resmi `artifacts/report.json` tidak ditulis ulang.

Jalankan dalam lingkungan Python 3.12 yang digunakan untuk eksperimen:

```powershell
python audit_provenance.py
python -m unittest discover -s tests -v
```

Jika BPS merevisi data atau eksperimen resmi sengaja dijalankan ulang, periksa perbedaannya terlebih dahulu, jalankan `python train.py`, lalu `python export_results.py` dan `python audit_provenance.py --write`. Perubahan hasil harus dijelaskan di naskah; jangan mengganti laporan lama secara diam-diam. Perbedaan versi paket dapat mengubah angka pelatihan walaupun seed tetap sama.

## Batas interpretasi

Metrik uji berasal dari Januari 2025–Juni 2026, 18 prediksi satu bulan ke depan per deret, dengan nilai aktual bulan sebelumnya tersedia sebagai riwayat. Prediksi Juli 2026 dibuat dari data hingga Juni 2026; adanya angka aktual Juli dalam snapshot tidak menjadikannya data latih atau uji resmi. Klaim penelitian dibatasi pada kategori dan periode tersebut.
