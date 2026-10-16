import sqlite3
import json
import random
from datetime import datetime, timedelta
from database import get_db, init_db

def seed():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # Bersihkan data lama jika ada
    cursor.execute("DELETE FROM jawaban")
    cursor.execute("DELETE FROM responden")
    cursor.execute("DELETE FROM pertanyaan")
    cursor.execute("DELETE FROM survei_petugas")
    cursor.execute("DELETE FROM survei")
    cursor.execute("DELETE FROM petugas")
    
    # 1. Seed Petugas (dengan Foto Profil)
    petugas_data = [
        ("PTG-001", "Budi Santoso, S.Kom", "budi.santoso@survei.go.id", "081234567891", "Jakarta Pusat", "Koordinator Wilayah", "Aktif", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&auto=format&fit=crop&q=80"),
        ("PTG-002", "Siti Aminah, S.Sos", "siti.aminah@survei.go.id", "081298765432", "Bandung", "Petugas Lapangan", "Aktif", "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300&auto=format&fit=crop&q=80"),
        ("PTG-003", "Ahmad Fauzi, S.Stat", "ahmad.fauzi@survei.go.id", "081345678901", "Surabaya", "Petugas Lapangan", "Aktif", "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=300&auto=format&fit=crop&q=80"),
        ("PTG-004", "Rina Kartika, M.Si", "rina.kartika@survei.go.id", "081398765432", "Semarang", "Enumerator Senior", "Aktif", "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=300&auto=format&fit=crop&q=80"),
        ("PTG-005", "Dedi Kurniawan, S.AP", "dedi.kurniawan@survei.go.id", "085212345678", "Medan", "Petugas Lapangan", "Aktif", "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&auto=format&fit=crop&q=80"),
        ("PTG-006", "Ni Putu Ayu Sri, S.Tr.Stat", "putu.ayu@survei.go.id", "087812345678", "Denpasar, Bali", "Petugas Lapangan", "Aktif", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop&q=80"),
        ("PTG-007", "Hendra Wijaya", "hendra.w@survei.go.id", "085712345678", "Yogyakarta", "Petugas Lapangan", "Nonaktif", "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=300&auto=format&fit=crop&q=80"),
    ]
    
    petugas_ids = []
    for p in petugas_data:
        cursor.execute('''
            INSERT INTO petugas (nip, nama, email, no_hp, wilayah, jabatan, status, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', p)
        petugas_ids.append(cursor.lastrowid)
        
    print(f"[*] Berhasil menambahkan {len(petugas_ids)} data petugas.")
    
    # 2. Seed Survei
    survei_data = [
        (
            "SRV-2026-001",
            "Survei Kepuasan Masyarakat (IKM) Pelayanan Publik 2026",
            "Pengukuran tingkat kepuasan masyarakat terhadap standar pelayanan terpadu, kecepatan layanan, sarana prasarana, dan integritas petugas di loket pelayanan publik.",
            "Pelayanan Publik",
            100,
            "2026-02-01",
            "2026-04-30",
            "Aktif",
            1
        ),
        (
            "SRV-2026-002",
            "Survei Kebutuhan Fasilitas & Infrastruktur Wilayah",
            "Penjaringan aspirasi masyarakat terkait prioritas pembangunan infrastruktur jalan lingkungan, penanganan drainase, penerangan umum, dan ruang terbuka hijau.",
            "Infrastruktur & Lingkungan",
            80,
            "2026-02-15",
            "2026-05-15",
            "Aktif",
            1
        ),
        (
            "SRV-2026-003",
            "Survei Pola Hidup Sehat & Kebugaran Warga",
            "Pemetaan kebiasaan berolahraga, konsumsi air bersih, gizi seimbang, dan pemanfaatan fasilitas olahraga umum oleh warga.",
            "Kesehatan Masyarakat",
            60,
            "2026-01-10",
            "2026-03-31",
            "Aktif",
            1
        ),
        (
            "SRV-2026-004",
            "Survei Kesiapan Digitalisasi UMKM 2026",
            "Penilaian tingkat kesiapan pelaku usaha mikro dan kecil dalam mengadopsi pembayaran nontunai (QRIS), pemasaran online, dan pembukuan digital.",
            "Ekonomi & UMKM",
            50,
            "2026-03-01",
            "2026-06-30",
            "Draft",
            1
        )
    ]
    
    survei_ids = []
    for s in survei_data:
        cursor.execute('''
            INSERT INTO survei (kode_survei, judul, deskripsi, kategori, target_responden, tanggal_mulai, tanggal_selesai, status, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', s)
        survei_ids.append(cursor.lastrowid)
        
    print(f"[*] Berhasil menambahkan {len(survei_ids)} data survei.")
    
    # 3. Relasi Penugasan Survei - Petugas
    assignments = [
        # Survei 1 (IKM) ditugaskan ke Petugas 1, 2, 3, 4
        (survei_ids[0], petugas_ids[0], "Koordinator Lapangan", 30),
        (survei_ids[0], petugas_ids[1], "Petugas Lapangan", 25),
        (survei_ids[0], petugas_ids[2], "Petugas Lapangan", 25),
        (survei_ids[0], petugas_ids[3], "Petugas Lapangan", 20),
        
        # Survei 2 (Infrastruktur) ditugaskan ke Petugas 1, 3, 5
        (survei_ids[1], petugas_ids[0], "Koordinator Lapangan", 30),
        (survei_ids[1], petugas_ids[2], "Petugas Lapangan", 25),
        (survei_ids[1], petugas_ids[4], "Petugas Lapangan", 25),
        
        # Survei 3 (Kesehatan) ditugaskan ke Petugas 2, 5, 6
        (survei_ids[2], petugas_ids[1], "Petugas Lapangan", 20),
        (survei_ids[2], petugas_ids[4], "Petugas Lapangan", 20),
        (survei_ids[2], petugas_ids[5], "Koordinator Lapangan", 20),
        
        # Survei 4 (UMKM) ditugaskan ke Petugas 3, 6
        (survei_ids[3], petugas_ids[2], "Petugas Lapangan", 25),
        (survei_ids[3], petugas_ids[5], "Petugas Lapangan", 25),
    ]
    
    for a in assignments:
        cursor.execute('''
            INSERT INTO survei_petugas (survei_id, petugas_id, peran, target_individu)
            VALUES (?, ?, ?, ?)
        ''', a)
        
    print(f"[*] Berhasil menambahkan {len(assignments)} data penugasan survei.")
    
    # 4. Pertanyaan untuk Survei 1: IKM Pelayanan Publik
    pertanyaan_s1 = [
        {
            "teks": "Jenis layanan publik apa yang paling sering Anda urus di loket pelayanan ini?",
            "tipe": "radio",
            "opsi": ["Administrasi Kependudukan (KTP/KK/Akta)", "Perizinan & Legalitas Usaha", "Layanan Kesehatan & BPJS", "Pendidikan & Beasiswa", "Perpajakan & Retribusi"],
            "required": 1,
            "urutan": 1,
            "panduan": "Pilih salah satu layanan yang menjadi fokus kunjungan Anda hari ini."
        },
        {
            "teks": "Tingkat keramahan, kesopanan, dan kepedulian petugas loket pelayanan",
            "tipe": "rating",
            "opsi": None,
            "required": 1,
            "urutan": 2,
            "panduan": "Beri nilai dari 1 (Sangat Tidak Ramah) hingga 5 (Sangat Ramah & Membantu).",
            "rating_max": 5
        },
        {
            "teks": "Kecepatan dan ketepatan waktu penyelesaian berkas/layanan",
            "tipe": "rating",
            "opsi": None,
            "required": 1,
            "urutan": 3,
            "panduan": "Beri nilai 1 sampai 5 sesuai kesesuaian dengan Standar Pelayanan Minimal.",
            "rating_max": 5
        },
        {
            "teks": "Kenyamanan fasilitas ruang tunggu, kebersihan, dan pendingin ruangan",
            "tipe": "rating",
            "opsi": None,
            "required": 1,
            "urutan": 4,
            "panduan": "Beri nilai 1 sampai 5 untuk kenyamanan sarana dan prasarana umum.",
            "rating_max": 5
        },
        {
            "teks": "Apakah biaya pengurusan layanan sudah transparan dan bebas dari pungutan liar (pungli)?",
            "tipe": "radio",
            "opsi": ["Sesuai Tarif Resmi & Sangat Transparan", "Gratis Tanpa Biaya Tambahan", "Ada Ketidakjelasan Tarif", "Dikenakan Biaya Tak Resmi"],
            "required": 1,
            "urutan": 5,
            "panduan": "Jawaban Anda dijamin kerahasiaannya."
        },
        {
            "teks": "Fasilitas penunjang apa yang menurut Anda mendesak untuk ditingkatkan?",
            "tipe": "checkbox",
            "opsi": ["Sistem Antrean Online & Notifikasi WA", "Akses Khusus Disabilitas & Lansia", "Ketersediaan Air Minum & Charger Gratis", "Area Parkir Kendaraan yang Luas", "Toilet yang Lebih Bersih & Higienis", "Koneksi Wi-Fi Publik Cepat"],
            "required": 0,
            "urutan": 6,
            "panduan": "Anda dapat mencentang lebih dari satu pilihan."
        },
        {
            "teks": "Kanal pendaftaran atau pengaduan mana yang paling Anda sukai?",
            "tipe": "dropdown",
            "opsi": ["Aplikasi Mobile Resmi", "Website Portal Layanan Terpadu", "WhatsApp Chatbot Otomatis", "Datang Langsung ke Meja Informasi", "Call Center / Hotline Bebas Pulsa"],
            "required": 1,
            "urutan": 7,
            "panduan": "Pilih satu kanal komunikasi yang paling praktis bagi Anda."
        },
        {
            "teks": "Berapa lama rata-rata waktu tunggu Anda (dalam menit) sebelum dipanggil petugas?",
            "tipe": "number",
            "opsi": None,
            "required": 1,
            "urutan": 8,
            "panduan": "Masukkan estimasi dalam satuan menit (contoh: 15)."
        },
        {
            "teks": "Kritik, apresiasi, atau saran konkret untuk peningkatan mutu pelayanan ke depan",
            "tipe": "long_text",
            "opsi": None,
            "required": 0,
            "urutan": 9,
            "panduan": "Tuliskan pengalaman atau masukan Anda secara bebas."
        }
    ]
    
    p_s1_ids = []
    for q in pertanyaan_s1:
        cursor.execute('''
            INSERT INTO pertanyaan (survei_id, teks_pertanyaan, tipe_pertanyaan, pilihan_opsi, is_required, urutan, panduan, rating_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            survei_ids[0],
            q["teks"],
            q["tipe"],
            json.dumps(q["opsi"], ensure_ascii=False) if q["opsi"] else None,
            q["required"],
            q["urutan"],
            q["panduan"],
            q.get("rating_max", 5)
        ))
        p_s1_ids.append((cursor.lastrowid, q))
        
    # 5. Pertanyaan untuk Survei 2: Infrastruktur Wilayah
    pertanyaan_s2 = [
        {
            "teks": "Pilihan sektor infrastruktur apa yang menjadi prioritas perbaikan paling mendesak di lingkungan Anda?",
            "tipe": "checkbox",
            "opsi": ["Perbaikan Jalan Aspal & Paving Berlubang", "Normalisasi Saluran Air & Drainase Banjir", "Pemasangan Lampu Penerangan Jalan Umum (PJU)", "Pengelolaan & Pengangkutan Sampah Rutin", "Penyediaan Ruang Terbuka Hijau & Taman Warga", "Penyediaan Air Bersih PDAM"],
            "required": 1,
            "urutan": 1,
            "panduan": "Pilih 1 atau lebih permasalahan infrastruktur utama."
        },
        {
            "teks": "Seberapa puas Anda dengan kondisi drainase lingkungan saat musim penghujan?",
            "tipe": "rating",
            "opsi": None,
            "required": 1,
            "urutan": 2,
            "panduan": "1 = Sangat Sering Tergenang/Banjir, 5 = Sangat Lancar & Tidak Ada Genangan.",
            "rating_max": 5
        },
        {
            "teks": "Bagaimana kelancaran pengangkutan sampah di pemukiman Anda saat ini?",
            "tipe": "radio",
            "opsi": ["Sangat Rutin (Tiap Hari)", "Cukup Rutin (2-3 Hari Sekali)", "Jarang (1 Kali Seminggu)", "Sering Terlambat / Menumpuk"],
            "required": 1,
            "urutan": 3,
            "panduan": "Pilih kondisi riil di lingkungan RT/RW Anda."
        },
        {
            "teks": "Nama rukun warga (RW) atau nama jalan tempat tinggal Anda",
            "tipe": "short_text",
            "opsi": None,
            "required": 1,
            "urutan": 4,
            "panduan": "Contoh: RW 05 Kelurahan Menteng"
        },
        {
            "teks": "Usulan tertulis perbaikan infrastruktur prioritas untuk Musrenbang tahun ini",
            "tipe": "long_text",
            "opsi": None,
            "required": 0,
            "urutan": 5,
            "panduan": "Jelaskan lokasi spesifik dan jenis pekerjaan yang dibutuhkan."
        }
    ]
    
    p_s2_ids = []
    for q in pertanyaan_s2:
        cursor.execute('''
            INSERT INTO pertanyaan (survei_id, teks_pertanyaan, tipe_pertanyaan, pilihan_opsi, is_required, urutan, panduan, rating_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            survei_ids[1],
            q["teks"],
            q["tipe"],
            json.dumps(q["opsi"], ensure_ascii=False) if q["opsi"] else None,
            q["required"],
            q["urutan"],
            q["panduan"],
            q.get("rating_max", 5)
        ))
        p_s2_ids.append((cursor.lastrowid, q))

    # 6. Pertanyaan untuk Survei 3: Pola Hidup Sehat
    pertanyaan_s3 = [
        {
            "teks": "Berapa kali frekuensi Anda berolahraga dalam seminggu?",
            "tipe": "radio",
            "opsi": ["Hampir Setiap Hari (5-7 kali)", "Rutin (3-4 kali)", "Jarang (1-2 kali)", "Tidak Pernah Olahraga"],
            "required": 1,
            "urutan": 1,
            "panduan": "Pilih kebiasaan Anda dalam sebulan terakhir."
        },
        {
            "teks": "Jenis olahraga apa saja yang biasa Anda lakukan?",
            "tipe": "checkbox",
            "opsi": ["Jalan Santai / Jogging", "Bersepeda", "Senam Aerobik / Zumba", "Badminton / Bulu Tangkis", "Futsal / Sepak Bola", "Berenang", "Fitness / Angkat Beban"],
            "required": 1,
            "urutan": 2,
            "panduan": "Centang semua olahraga yang Anda gemari."
        },
        {
            "teks": "Berapa rata-rata jumlah gelas air putih yang Anda minum setiap hari?",
            "tipe": "number",
            "opsi": None,
            "required": 1,
            "urutan": 3,
            "panduan": "Ketik jumlah dalam angka (misal: 8)."
        },
        {
            "teks": "Tingkat kualitas dan kecukupan waktu istirahat/tidur harian Anda",
            "tipe": "rating",
            "opsi": None,
            "required": 1,
            "urutan": 4,
            "panduan": "1 = Sangat Kurang / Kurang Segar, 5 = Sangat Cukup & Bugar.",
            "rating_max": 5
        },
        {
            "teks": "Komentar atau saran ketersediaan fasilitas olahraga terbuka di lingkungan Anda",
            "tipe": "long_text",
            "opsi": None,
            "required": 0,
            "urutan": 5,
            "panduan": "Tuliskan saran tempat olahraga umum."
        }
    ]
    for q in pertanyaan_s3:
        cursor.execute('''
            INSERT INTO pertanyaan (survei_id, teks_pertanyaan, tipe_pertanyaan, pilihan_opsi, is_required, urutan, panduan, rating_max)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            survei_ids[2],
            q["teks"],
            q["tipe"],
            json.dumps(q["opsi"], ensure_ascii=False) if q["opsi"] else None,
            q["required"],
            q["urutan"],
            q["panduan"],
            q.get("rating_max", 5)
        ))

    print(f"[*] Berhasil menambahkan pertanyaan survei.")
    
    # 7. Seed Responden & Jawaban untuk Survei 1 (IKM Pelayanan Publik)
    # Buat sekitar 45 responden realistis
    nama_list = [
        ("Agus Setiawan", "Laki-laki", 34, "Jakarta Pusat"),
        ("Dewi Lestari", "Perempuan", 28, "Jakarta Timur"),
        ("Rian Pratama", "Laki-laki", 42, "Bandung"),
        ("Nurul Hidayah", "Perempuan", 31, "Jakarta Selatan"),
        ("Bambang Trihatmojo", "Laki-laki", 50, "Surabaya"),
        ("Eka Rahmawati", "Perempuan", 25, "Jakarta Barat"),
        ("Fajar Nugroho", "Laki-laki", 38, "Semarang"),
        ("Lina Marlina", "Perempuan", 29, "Bandung"),
        ("Hendri Saputra", "Laki-laki", 45, "Medan"),
        ("Citra Kusuma", "Perempuan", 33, "Yogyakarta"),
        ("Bayu Permana", "Laki-laki", 27, "Surabaya"),
        ("Ratna Sari", "Perempuan", 36, "Jakarta Pusat"),
        ("Doni Firmansyah", "Laki-laki", 39, "Bandung"),
        ("Indah Permatasari", "Perempuan", 24, "Jakarta Selatan"),
        ("Wawan Hermawan", "Laki-laki", 48, "Semarang"),
        ("Maya Anggraini", "Perempuan", 30, "Surabaya"),
        ("Rizky Maulana", "Laki-laki", 26, "Jakarta Pusat"),
        ("Tia Febriani", "Perempuan", 35, "Bandung"),
        ("Joko Susilo", "Laki-laki", 52, "Surabaya"),
        ("Nadia Utami", "Perempuan", 23, "Jakarta Timur"),
        ("Dian Sastro", "Perempuan", 40, "Jakarta Pusat"),
        ("Arief Wicaksono", "Laki-laki", 37, "Semarang"),
        ("Gita Gutawa", "Perempuan", 26, "Medan"),
        ("Hadi Pranoto", "Laki-laki", 49, "Bandung"),
        ("Irma Suryani", "Perempuan", 32, "Surabaya"),
        ("Kevin Sanjaya", "Laki-laki", 28, "Jakarta Barat"),
        ("Lukman Hakim", "Laki-laki", 44, "Medan"),
        ("Melati Putri", "Perempuan", 22, "Denpasar"),
        ("Nanang Qosim", "Laki-laki", 46, "Semarang"),
        ("Olivia Gunawan", "Perempuan", 31, "Jakarta Selatan"),
        ("Panji Gumilang", "Laki-laki", 55, "Bandung"),
        ("Qori Sandioriva", "Perempuan", 29, "Jakarta Pusat"),
        ("Rahmat Hidayat", "Laki-laki", 33, "Surabaya"),
        ("Sari Wardani", "Perempuan", 38, "Medan"),
        ("Taufik Hidayat", "Laki-laki", 41, "Bandung"),
        ("Umar Bakri", "Laki-laki", 47, "Jakarta Utara"),
        ("Vivi Sumanti", "Perempuan", 27, "Denpasar"),
        ("Wahyu Hidayat", "Laki-laki", 36, "Semarang"),
        ("Yuni Shara", "Perempuan", 51, "Surabaya"),
        ("Zainal Abidin", "Laki-laki", 43, "Jakarta Pusat"),
        ("Anisa Rahma", "Perempuan", 25, "Bandung"),
        ("Bagus Prasetyo", "Laki-laki", 30, "Surabaya"),
        ("Cici Paramida", "Perempuan", 48, "Jakarta Timur"),
        ("Danang Sutrisno", "Laki-laki", 35, "Semarang"),
        ("Elly Sugigi", "Perempuan", 46, "Jakarta Pusat")
    ]
    
    komentar_s1 = [
        "Petugas sangat ramah dan proses cetak KTP elektronik cepat sekali selesai.",
        "Ruang tunggu sudah cukup nyaman dan dingin, namun antrean di jam 10 pagi masih lumayan padat.",
        "Pelayanan mantap, tidak ada biaya tambahan apapun, semua sesuai tarif resmi Rp 0.",
        "Mohon ditambah mesin antrean otomatis dan nomor panggilan dengan speaker yang lebih jelas.",
        "Sangat terbantu oleh keramahan petugas customer service di depan pintu masuk.",
        "Proses pengurusan KK baru sekarang sudah jauh lebih cepat dibanding tahun lalu. Pertahankan!",
        "Perlu ada jalur prioritas khusus untuk lansia dan ibu hamil yang membawa balita.",
        "Aplikasi mobile perlu ditingkatkan kestabilannya saat jam kerja.",
        "Petugas sigap menjelaskan persyaratan tanpa berbelit-belit. Sangat puas.",
        "Fasilitas toilet perlu dijaga kebersihannya di siang hari menjelang istirahat.",
        "Sangat transparan, tidak ada calo sama sekali. Maju terus pelayanan publik kita!",
        "Waktu tunggu sudah lumayan cepat, sekitar 15 menit sudah dipanggil ke loket.",
        "Terima kasih atas pelayanannya yang humanis dan bersahabat.",
        "Sistem pendaftaran online sangat membantu sehingga tidak perlu antre dari subuh.",
        "Pelayanan sudah bagus, tinggal ketersediaan formulir cetak diperbanyak."
    ]

    base_time = datetime.now() - timedelta(days=25)
    
    # Petugas yang aktif menginput survei 1: Budi (id 1), Siti (id 2), Ahmad (id 3), Rina (id 4), plus sebagian via Link Mandiri (None)
    petugas_pool_s1 = [petugas_ids[0]] * 14 + [petugas_ids[1]] * 11 + [petugas_ids[2]] * 10 + [petugas_ids[3]] * 7 + [None] * 8
    random.shuffle(petugas_pool_s1)
    
    for idx, (nama, jk, usia, wilayah) in enumerate(nama_list):
        p_id = petugas_pool_s1[idx % len(petugas_pool_s1)]
        created_time = base_time + timedelta(days=idx*0.5, hours=random.randint(8, 16), minutes=random.randint(5, 55))
        
        cursor.execute('''
            INSERT INTO responden (survei_id, petugas_id, nama_responden, kontak_responden, usia, jenis_kelamin, alamat_wilayah, ip_address, waktu_selesai)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            survei_ids[0],
            p_id,
            nama,
            f"08{random.randint(11, 99)}{random.randint(1000, 9999)}{random.randint(100, 999)}",
            usia,
            jk,
            wilayah,
            f"192.168.1.{random.randint(10, 200)}",
            created_time.strftime("%Y-%m-%d %H:%M:%S")
        ))
        resp_id = cursor.lastrowid
        
        # Insert Answers for Survei 1
        # Q1: Jenis layanan
        opsi_layanan = ["Administrasi Kependudukan (KTP/KK/Akta)", "Perizinan & Legalitas Usaha", "Layanan Kesehatan & BPJS", "Pendidikan & Beasiswa", "Perpajakan & Retribusi"]
        weights_layanan = [40, 20, 25, 10, 5]
        j_layanan = random.choices(opsi_layanan, weights=weights_layanan)[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[0][0], j_layanan, None))
        
        # Q2: Rating Keramahan (1-5, mostly 4 and 5)
        r_ramah = random.choices([3, 4, 5], weights=[10, 45, 45])[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[1][0], str(r_ramah), float(r_ramah)))
        
        # Q3: Rating Kecepatan (1-5, mostly 3, 4, 5)
        r_cepat = random.choices([2, 3, 4, 5], weights=[5, 15, 50, 30])[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[2][0], str(r_cepat), float(r_cepat)))
        
        # Q4: Rating Kenyamanan Ruang Tunggu (1-5)
        r_nyaman = random.choices([3, 4, 5], weights=[15, 55, 30])[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[3][0], str(r_nyaman), float(r_nyaman)))
        
        # Q5: Biaya Resmi / Pungli
        opsi_biaya = ["Sesuai Tarif Resmi & Sangat Transparan", "Gratis Tanpa Biaya Tambahan", "Ada Ketidakjelasan Tarif", "Dikenakan Biaya Tak Resmi"]
        j_biaya = random.choices(opsi_biaya, weights=[65, 30, 4, 1])[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[4][0], j_biaya, None))
        
        # Q6: Fasilitas Penunjang (Checkbox - multi select)
        fasilitas_opts = ["Sistem Antrean Online & Notifikasi WA", "Akses Khusus Disabilitas & Lansia", "Ketersediaan Air Minum & Charger Gratis", "Area Parkir Kendaraan yang Luas", "Toilet yang Lebih Bersih & Higienis", "Koneksi Wi-Fi Publik Cepat"]
        k = random.randint(1, 3)
        j_fasilitas = random.sample(fasilitas_opts, k)
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[5][0], json.dumps(j_fasilitas, ensure_ascii=False), None))
        
        # Q7: Kanal Pendaftaran (Dropdown)
        opsi_kanal = ["Aplikasi Mobile Resmi", "Website Portal Layanan Terpadu", "WhatsApp Chatbot Otomatis", "Datang Langsung ke Meja Informasi", "Call Center / Hotline Bebas Pulsa"]
        j_kanal = random.choices(opsi_kanal, weights=[35, 30, 20, 12, 3])[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[6][0], j_kanal, None))
        
        # Q8: Waktu Tunggu (Number)
        menit_tunggu = random.choices([10, 15, 20, 25, 30, 45], weights=[20, 35, 25, 10, 7, 3])[0]
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s1_ids[7][0], str(menit_tunggu), float(menit_tunggu)))
        
        # Q9: Masukan / Kritik (Text)
        if random.random() < 0.7:
            j_teks = random.choice(komentar_s1)
            cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                           (resp_id, p_s1_ids[8][0], j_teks, None))

    # 8. Seed Responden untuk Survei 2 (Infrastruktur)
    warga_s2 = [
        ("Pak RT Suharsono", "Laki-laki", 54, "Kelurahan Cikini, RW 03", petugas_ids[0]),
        ("Ibu Maria Ulfah", "Perempuan", 42, "Kelurahan Menteng, RW 05", petugas_ids[2]),
        ("Pak Slamet", "Laki-laki", 60, "Kelurahan Gondangdia, RW 02", petugas_ids[4]),
        ("Dian Anggoro", "Laki-laki", 35, "Kelurahan Pegangsaan, RW 08", petugas_ids[0]),
        ("Rina Wulandari", "Perempuan", 29, "Kelurahan Cikini, RW 01", petugas_ids[2]),
        ("Gunawan Wibisono", "Laki-laki", 47, "Kelurahan Menteng, RW 04", petugas_ids[4]),
        ("Tuti Alawiyah", "Perempuan", 52, "Kelurahan Gambir, RW 06", None),
        ("Hartono", "Laki-laki", 39, "Kelurahan Cikini, RW 02", petugas_ids[0]),
        ("Sri Rejeki", "Perempuan", 44, "Kelurahan Kebon Sirih, RW 03", petugas_ids[2]),
        ("Ferry Irawan", "Laki-laki", 31, "Kelurahan Menteng, RW 07", None),
    ]
    
    usulan_infra = [
        "Perbaikan gorong-gorong di persimpangan jalan utama agar saat hujan lebat air tidak meluap ke badan jalan.",
        "Penambahan 5 titik lampu jalan LED di gang pemukiman yang masih gelap saat malam.",
        "Pengaspalan ulang jalan lingkungan sepanjang 300 meter yang rusak setelah proyek galian.",
        "Penyediaan tempat pemilahan sampah organik dan anorganik terpilah di pos RW.",
        "Pembuatan zebra cross dan pita kejut di depan sekolah dasar demi keselamatan anak sekolah."
    ]
    
    for idx, (nama, jk, usia, alamat, p_id) in enumerate(warga_s2):
        created_time = base_time + timedelta(days=idx*1.2, hours=random.randint(9, 15))
        cursor.execute('''
            INSERT INTO responden (survei_id, petugas_id, nama_responden, kontak_responden, usia, jenis_kelamin, alamat_wilayah, ip_address, waktu_selesai)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            survei_ids[1],
            p_id,
            nama,
            f"0812{random.randint(1000000, 9999999)}",
            usia,
            jk,
            alamat,
            f"192.168.1.{random.randint(20, 150)}",
            created_time.strftime("%Y-%m-%d %H:%M:%S")
        ))
        resp_id = cursor.lastrowid
        
        # Q1 Checkbox Prioritas
        opts = ["Perbaikan Jalan Aspal & Paving Berlubang", "Normalisasi Saluran Air & Drainase Banjir", "Pemasangan Lampu Penerangan Jalan Umum (PJU)", "Pengelolaan & Pengangkutan Sampah Rutin", "Penyediaan Ruang Terbuka Hijau & Taman Warga"]
        j_prio = random.sample(opts, random.randint(1, 3))
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s2_ids[0][0], json.dumps(j_prio, ensure_ascii=False), None))
        
        # Q2 Rating Drainase (1-5)
        r_drain = random.choice([2, 3, 3, 4, 4])
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s2_ids[1][0], str(r_drain), float(r_drain)))
        
        # Q3 Radio Sampah
        j_sampah = random.choice(["Sangat Rutin (Tiap Hari)", "Cukup Rutin (2-3 Hari Sekali)", "Jarang (1 Kali Seminggu)"])
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s2_ids[2][0], j_sampah, None))
        
        # Q4 Short text
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s2_ids[3][0], alamat, None))
        
        # Q5 Long text
        cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                       (resp_id, p_s2_ids[4][0], random.choice(usulan_infra), None))

    conn.commit()
    conn.close()
    print("[OK] Seeding data berhasil diselesaikan dengan sukses!")

if __name__ == '__main__':
    seed()
