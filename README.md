# 📊 SiSurvei - Sistem Informasi & Manajemen Kegiatan Survei Terpadu

Aplikasi web modern, responsif, dan komprehensif untuk mengelola seluruh siklus kegiatan survei lapangan maupun survei publik: mulai dari pembuatan instrumen survei, perancangan aneka tipe pertanyaan secara visual (drag-and-drop & inline editor), pengelolaan data petugas/enumerator lapangan, pengisian kuisioner oleh responden atau petugas dengan sensor GPS titik koordinat dan peta interaktif, portal khusus petugas yang kompatibel dengan HP Android, hingga dashboard hasil survei interaktif dengan visualisasi data otomatis dan ekspor laporan ke Excel/CSV.

---

## 🌟 Fitur Utama

### 1. Manajemen Kegiatan Survei (Multi-Survey)
- **Buat Berbagai Macam Survei**: Mendukung berbagai sektor/kategori seperti *Pelayanan Publik, Infrastruktur & Lingkungan, Kesehatan Masyarakat, Ekonomi & UMKM, Pendidikan, Kepuasan Pelanggan, dll.*
- **Kode Survei Unik**: Setiap survei memiliki kode unik (misal: `SRV-2026-001`) yang menjadi tautan pengisian publik.
- **Monitoring Capaian Target**: Real-time progress bar persentase target responden yang telah tercapai vs target yang ditetapkan.
- **Status Siklus Survei**: Status *Draft*, *Aktif*, dan *Selesai* dengan tombol switch/toggle cepat.
- **Penugasan Tim Petugas**: Setiap survei dapat ditugaskan ke satu atau banyak petugas lapangan spesifik.

### 2. Perancang Kuisioner Dinamis (8 Ragam Tipe Pertanyaan)
Dilengkapi antarmuka **Survey Question Builder** visual dengan 8 ragam tipe pertanyaan:
1. **Teks Singkat (*Short Text*)**: Untuk jawaban pendek seperti nama, wilayah, instansi, dsb.
2. **Paragraf / Uraian (*Long Text*)**: Untuk kritik, saran, atau masukan kualitatif bebas.
3. **Pilihan Ganda (*Single Choice / Radio*)**: Pilihan satu opsi tunggal dengan opsi dinamis.
4. **Kotak Centang (*Multiple Choices / Checkbox*)**: Pilihan banyak opsi sekaligus (multi-select).
5. **Skala Penilaian (*Star Rating 1-5 atau 1-10*)**: Interaktif dengan hover bintang emas dan label kepuasan.
6. **Menu Pilihan Dropdown**: Dropdown ringkas untuk opsi kategori atau wilayah.
7. **Angka / Numerik (*Number*)**: Untuk besaran waktu tunggu, nominal, jumlah gelas air, dsb.
8. **Tanggal (*Date*)**: Pemilih kalender standar.
- **Pengaturan Tambahan**: Switch *Pertanyaan Wajib Diisi (Mandatory)*, panduan instruksi pengisian (*helper text*), dan pengaturan urutan naik/turun (*reorder*).

### 3. Pengelolaan Data Petugas Lapangan (Enumerator & Koordinator)
- **Data Profil Petugas**: NIP/ID Petugas, Nama Lengkap, Nomor WhatsApp, Email, Wilayah Penugasan, Jabatan, dan Status Keaktifan.
- **Tracking Kinerja Petugas**: Melacak jumlah survei yang ditugaskan dan jumlah kuisioner yang berhasil dikumpulkan oleh masing-masing petugas.
- **Profil Detail Petugas**: Menampilkan rincian performa per kegiatan survei, tombol kontak langsung ke WhatsApp/Email, dan riwayat 20 responden terakhir yang diinput.
- **Manajemen CRUD Petugas**: Tambah petugas baru, edit data, dan hapus petugas dengan validasi NIP unik.

### 4. Formulir Pengisian Kuisioner yang Interaktif & Ramah Pengguna
- **Tautan Publik Ramah Seluler (*Mobile Friendly*)**: Tampilan bersih, elegan, dan tanpa distraksi di URL `/s/<kode_survei>`.
- **Mode Pengisian Ganda**:
  - *Responden Mandiri*: Warga/responden mengisi kuisioner secara mandiri melalui browser.
  - *Petugas Lapangan (Enumerator)*: Petugas melakukan wawancara langsung dan memilih namanya dari daftar petugas yang ditugaskan.
- **Indikator Progres (*Live Progress Bar*)**: Bar progres di bagian atas yang menghitung persentase pertanyaan yang sudah dijawab secara *real-time*.
- **Komponen Rating Bintang Interaktif**: Animasi klik dan hover bintang untuk pertanyaan rating.
- **Halaman Sukses**: Memberikan nomor referensi unik kuisioner (`#RESP-xxxxx`) serta opsi isi ulang.

### 5. Dashboard Hasil & Analisis Survei Terpadu
- **Executive Summary Dashboard (`/`)**:
  - KPI Cards: Total Survei, Survei Aktif, Total Responden Terkumpul, Total Petugas Aktif, Rata-rata Skor Kepuasan.
  - Grafik Tren Pengumpulan Respon Harian (14 Hari Terakhir) menggunakan Chart.js.
  - Grafik Distribusi Responden per Kategori Survei (Doughnut Chart).
  - Peringkat Kinerja Top 5 Petugas Survei (Horizontal Bar Chart).
  - Monitoring Capaian Survei Berjalan & Feed Respon Terkini.
- **Dashboard Hasil Spesifik per Survei (`/survei/<id>/hasil`)**:
  - Filter analitik berdasarkan nama Petugas Penginput, Jenis Kelamin, dan Rentang Tanggal.
  - **Visualisasi Otomatis per Pertanyaan**:
    - Pie / Donut Chart untuk pertanyaan Pilihan Ganda & Dropdown beserta tabel persentase.
    - Horizontal Bar Chart untuk pertanyaan Kotak Centang (Checkbox).
    - Skor Rata-rata Bintang dan Grafik Distribusi Suara untuk pertanyaan Rating.
    - Metrik Ringkasan Nilai (Rata-rata, Minimum, Maksimum) untuk pertanyaan Angka.
    - Kartu umpan respon kualitatif untuk pertanyaan Teks & Paragraf.
  - **Tabel Data Mentah Responden**: Filterable & modal penampil seluruh lembar jawaban asli responden.
  - **Ekspor Data Sekali Klik**:
    - Unduh laporan dalam format **Microsoft Excel (`.xlsx`)** lengkap dengan styling header dan seluruh kolom jawaban.
    - Unduh dalam format **CSV (`.csv`)**.

---

## 🚀 Panduan Menjalankan Aplikasi

Aplikasi dibangun menggunakan **Python 3** dan **Flask** dengan basis data **SQLite** bawaan.

### 1. Jalankan melalui Script Batch (Windows):
Cukup klik dua kali pada file:
```
c:\sisurvei\run.bat
```

### 2. Atau Jalankan melalui Terminal / PowerShell:
```powershell
# Pindah ke direktori proyek
cd c:\sisurvei

# Inisialisasi basis data & data simulasi (jika belum)
python seed_data.py

# Jalankan server web
python app.py
```

Setelah server aktif, buka browser Anda di:
👉 **[http://127.0.0.1:5005](http://127.0.0.1:5005)**

---

## 📁 Struktur Direktori Proyek

```
c:\sisurvei\
├── app.py                      # Server Flask utama (routing, API, ekspor, analitik)
├── database.py                 # Skema basis data SQLite & inisialisasi tabel
├── seed_data.py                # Data awal realistis (petugas, aneka survei, responden, jawaban)
├── test_app.py                 # Pengujian otomatis integrasi (14 skenario tes lolos 100%)
├── run.bat                     # Script launcher sekali klik untuk Windows
├── README.md                   # Dokumentasi lengkap sistem
├── sisurvei.db                 # Database SQLite lokal (dibuat otomatis)
├── templates/                  # Template HTML (Jinja2 + Tailwind CSS + FontAwesome + Chart.js)
│   ├── base.html               # Layout induk aplikasi (sidebar navigasi, navbar, flash alerts)
│   ├── dashboard.html          # Dashboard utama (KPI cards, tren chart, top petugas, capaian)
│   ├── surveys/
│   │   ├── index.html          # Daftar kegiatan survei, status badge, progress bar, aksi
│   │   ├── create.html         # Form pendaftaran survei baru & penugasan petugas
│   │   ├── edit.html           # Form edit metadata survei & penugasan tim
│   │   ├── builder.html        # Perancang pertanyaan visual dinamis (8 tipe pertanyaan)
│   │   ├── fill.html           # Form pengisian kuisioner publik/lapangan interaktif
│   │   ├── thank_you.html      # Halaman konfirmasi sukses setelah submit
│   │   ├── closed.html         # Halaman jika survei berstatus tidak aktif/ditutup
│   │   └── results.html        # Dashboard hasil & analisis survei (grafik per soal & ekspor)
│   ├── petugas/
│   │   ├── index.html          # Direktori petugas survei & modal tambah/edit
│   │   └── detail.html         # Profil petugas, metrik kinerja, dan riwayat penginputan
│   └── responses/
│       └── index.html          # Repositori seluruh kuisioner responden lintas survei
└── static/                     # Aset statis pendukung
```

---

### 6. 📱 Portal Level Operator / Petugas Enumerator (`/operator`)
Khusus dirancang untuk petugas lapangan dengan antarmuka yang simpel, fokus, dan hanya menampilkan **2 menu utama**:
- **Menu 1: Profil Petugas Enumerator (`/operator/profil`)**:
  - Menampilkan foto profil petugas, NIP, Nama Lengkap, Jabatan, Wilayah Penugasan, dan Status.
  - Kartu statistik kumulatif: Total Survei Ditugaskan, Total Target Sampel, Total Sampel Selesai, dan Persentase Capaian Kumulatif.
  - Form untuk memperbarui data diri, nomor WhatsApp, email, wilayah, dan fitur unggah foto profil (mendukung upload file gambar atau URL foto).
- **Menu 2: Halaman Tugas Survei (`/operator/tugas`)**:
  - Menampilkan data keikutsertaan sebagai petugas sesuai kelompok tugas survei (misal: *Koordinator Lapangan*, *Petugas Lapangan / Enumerator*, *Verifikator*).
  - **Kuota Sampel yang Ditentukan**: Menampilkan target sampel individu (misal 25 responden), realisasi sampel yang telah dikerjakan, sisa sampel yang belum tuntas, dan progress bar capaian.
  - **Tombol Utama: "Buka Form Kuisioner / Mulai Input Sampel"**: Langsung membuka kuisioner survei tersebut dengan identitas petugas terkunci secara otomatis.
  - **Kuisioner Khusus Operator (`/operator/survei/<id>/isi`)**: Menampilkan banner penugasan dan pelacak nomor sampel ("Sedang Menginput: Sampel ke-X dari Y target").
  - **Selesai Input Sampel**: Halaman konfirmasi capaian sampel dengan tombol **"Lanjut Input Sampel Berikutnya"** untuk mempercepat proses pencatatan data lapangan.
  - Fitur penukar akun (*Account Switcher*) untuk berpindah profil petugas dengan mudah saat demonstrasi maupun penggunaan bersama.

---

## 📁 Struktur Direktori Proyek

```
c:\sisurvei\
├── app.py                      # Server Flask utama (routing, API, ekspor, analitik, portal operator)
├── database.py                 # Skema basis data SQLite & migration kolom foto
├── seed_data.py                # Data awal realistis (petugas berfoto, aneka survei, responden, jawaban)
├── test_app.py                 # Pengujian otomatis integrasi (20 skenario tes lolos 100%)
├── run.bat                     # Script launcher sekali klik untuk Windows
├── README.md                   # Dokumentasi lengkap sistem
├── sisurvei.db                 # Database SQLite lokal (dibuat otomatis)
├── static/
│   └── uploads/petugas/        # Direktori penyimpanan file upload foto petugas
├── templates/                  # Template HTML (Jinja2 + Tailwind CSS + FontAwesome + Chart.js)
│   ├── base.html               # Layout induk Admin (sidebar, navbar, modal)
│   ├── dashboard.html          # Dashboard eksekutif utama & visualisasi grafik
│   ├── operator/               # Template Khusus Level Operator / Enumerator
│   │   ├── base.html           # Layout khusus operator (hanya menu Profil & Tugas Survei)
│   │   ├── tugas.html          # Halaman tugas survei, kelompok tugas, kuota sampel & progress
│   │   ├── profil.html         # Profil petugas enumerator & form update data/foto
│   │   ├── isi.html            # Form pengisian kuisioner dengan pelacak target sampel
│   │   └── sukses.html         # Halaman sukses submit sampel dengan tombol lanjut input
│   ├── surveys/
│   │   ├── index.html          # Daftar kegiatan survei, status badge, progress bar, aksi
│   │   ├── create.html         # Form pendaftaran survei baru & penugasan petugas
│   │   ├── edit.html           # Form edit metadata survei & penugasan tim
│   │   ├── builder.html        # Perancang pertanyaan visual dinamis (8 tipe pertanyaan)
│   │   ├── fill.html           # Form pengisian kuisioner publik/lapangan interaktif
│   │   ├── thank_you.html      # Halaman konfirmasi sukses setelah submit publik
│   │   ├── closed.html         # Halaman jika survei berstatus tidak aktif/ditutup
│   │   └── results.html        # Dashboard hasil & analisis survei (grafik per soal & ekspor)
│   ├── petugas/
│   │   ├── index.html          # Direktori petugas survei (dengan foto) & modal tambah/edit
│   │   └── detail.html         # Profil petugas, foto, metrik kinerja, dan riwayat penginputan
│   └── responses/
│       └── index.html          # Repositori seluruh kuisioner responden lintas survei
└── static/                     # Aset statis pendukung
```

---

## 🧪 Hasil Pengujian Sistem
Seluruh fungsionalitas telah diverifikasi melalui pengujian otomatis integrasi (27 skenario pengujian lolos 100%):
- ✅ Dashboard Utama & Kalkulasi Metrik Agregat
- ✅ Listing Survei, Filter Kategori & Status
- ✅ Question Builder & 8 Ragam Tipe Pertanyaan
- ✅ REST API Builder (Tambah, Ubah, Urutkan, Hapus Pertanyaan)
- ✅ Pengisian Kuisioner Publik & Lapangan
- ✅ Dashboard Hasil & Visualisasi Chart.js
- ✅ Pengelolaan Data Petugas (dengan Variabel Foto Profil & Upload)
- ✅ Ekspor Laporan Excel (`.xlsx`) & CSV (`.csv`) menyertakan Pendidikan & Titik Koordinat
- ✅ Modal Penampil Lembar Jawaban Lengkap Responden dengan tautan Google Maps
- ✅ Portal Level Operator: Hanya Menu Profil & Tugas Survei
- ✅ Data Keikutsertaan Kelompok Tugas Survei & Kuota Sampel yang Ditentukan
- ✅ Form Kuisioner Khusus Operator dengan Pelacak Nomor Sampel Terkunci
- ✅ Alur Lanjut Input Sampel Berikutnya bagi Enumerator Lapangan
- ✅ Sistem Autentikasi & Login Dual Role (Admin & Petugas Enumerator)
- ✅ Input Titik Koordinat GPS Otomatis & Peta Interaktif Leaflet
- ✅ Variabel Pendidikan Terakhir pada Profil Responden
- ✅ Kompatibilitas Penuh HP Android (PWA Manifest, Safe Area, Scan QR Code Login)
