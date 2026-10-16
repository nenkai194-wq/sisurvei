import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sisurvei.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Tabel Petugas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS petugas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nip TEXT UNIQUE NOT NULL,
            nama TEXT NOT NULL,
            email TEXT,
            no_hp TEXT,
            wilayah TEXT,
            jabatan TEXT DEFAULT 'Petugas Lapangan',
            status TEXT DEFAULT 'Aktif',
            foto TEXT,
            password_hash TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration check untuk foto dan password jika tabel sudah ada sebelumnya
    cursor.execute("PRAGMA table_info(petugas)")
    col_names = [r[1] for r in cursor.fetchall()]
    if 'foto' not in col_names:
        cursor.execute("ALTER TABLE petugas ADD COLUMN foto TEXT")
    if 'password_hash' not in col_names:
        cursor.execute("ALTER TABLE petugas ADD COLUMN password_hash TEXT")
    
    # 2. Tabel Users (Admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nama TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'admin',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Tabel Survei
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survei (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_survei TEXT UNIQUE NOT NULL,
            judul TEXT NOT NULL,
            deskripsi TEXT,
            kategori TEXT DEFAULT 'Umum',
            target_responden INTEGER DEFAULT 100,
            tanggal_mulai DATE,
            tanggal_selesai DATE,
            status TEXT DEFAULT 'Aktif',
            is_public INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Tabel Relasi Survei - Petugas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survei_petugas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survei_id INTEGER NOT NULL,
            petugas_id INTEGER NOT NULL,
            peran TEXT DEFAULT 'Petugas Lapangan',
            target_individu INTEGER DEFAULT 25,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (survei_id) REFERENCES survei(id) ON DELETE CASCADE,
            FOREIGN KEY (petugas_id) REFERENCES petugas(id) ON DELETE CASCADE,
            UNIQUE(survei_id, petugas_id)
        )
    ''')
    
    # 4. Tabel Pertanyaan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pertanyaan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survei_id INTEGER NOT NULL,
            teks_pertanyaan TEXT NOT NULL,
            tipe_pertanyaan TEXT NOT NULL,
            pilihan_opsi TEXT,
            is_required INTEGER DEFAULT 1,
            urutan INTEGER DEFAULT 1,
            panduan TEXT,
            rating_max INTEGER DEFAULT 5,
            FOREIGN KEY (survei_id) REFERENCES survei(id) ON DELETE CASCADE
        )
    ''')
    
    # 5. Tabel Responden (Sesi Pengisian)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responden (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survei_id INTEGER NOT NULL,
            petugas_id INTEGER,
            nama_responden TEXT,
            kontak_responden TEXT,
            usia INTEGER,
            jenis_kelamin TEXT,
            pendidikan_terakhir TEXT,
            titik_koordinat TEXT,
            alamat_wilayah TEXT,
            ip_address TEXT,
            waktu_mulai DATETIME,
            waktu_selesai DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (survei_id) REFERENCES survei(id) ON DELETE CASCADE,
            FOREIGN KEY (petugas_id) REFERENCES petugas(id) ON DELETE SET NULL
        )
    ''')

    # Migration check untuk pendidikan_terakhir dan titik_koordinat jika tabel responden sudah ada
    cursor.execute("PRAGMA table_info(responden)")
    resp_cols = [r[1] for r in cursor.fetchall()]
    if 'pendidikan_terakhir' not in resp_cols:
        cursor.execute("ALTER TABLE responden ADD COLUMN pendidikan_terakhir TEXT")
    if 'titik_koordinat' not in resp_cols:
        cursor.execute("ALTER TABLE responden ADD COLUMN titik_koordinat TEXT")
    
    # 6. Tabel Jawaban
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jawaban (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            responden_id INTEGER NOT NULL,
            pertanyaan_id INTEGER NOT NULL,
            jawaban_teks TEXT,
            jawaban_angka REAL,
            FOREIGN KEY (responden_id) REFERENCES responden(id) ON DELETE CASCADE,
            FOREIGN KEY (pertanyaan_id) REFERENCES pertanyaan(id) ON DELETE CASCADE
        )
    ''')
    
    # Migration check untuk tabel users (no_hp, foto, status)
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [r[1] for r in cursor.fetchall()]
    if 'no_hp' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN no_hp TEXT")
    if 'foto' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN foto TEXT")
    if 'status' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Aktif'")

    # 7. Tabel Pengaturan Sistem
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pengaturan (
            kunci TEXT PRIMARY KEY,
            nilai TEXT,
            kategori TEXT DEFAULT 'Umum',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 8. Tabel Log Aktivitas (Audit Trail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            role TEXT,
            aksi TEXT NOT NULL,
            rincian TEXT,
            ip_address TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed Default Settings jika belum ada
    default_settings = [
        ('nama_aplikasi', 'SiSurvei - Portal Manajemen Survei Terpadu', 'Umum'),
        ('nama_instansi', 'Lembaga Riset & Pelayanan Publik Terpadu', 'Umum'),
        ('email_resmi', 'layanan@survei.go.id', 'Kontak'),
        ('telepon_resmi', '021-8889991', 'Kontak'),
        ('alamat_kantor', 'Gedung Informasi & Statistik Lt. 4, Jakarta', 'Kontak'),
        ('zona_waktu', 'Asia/Jakarta (WIB)', 'Sistem'),
    ]
    for k, v, kat in default_settings:
        cursor.execute("INSERT OR IGNORE INTO pengaturan (kunci, nilai, kategori) VALUES (?, ?, ?)", (k, v, kat))
    
    # 9. Seed Default Super Admin & Staf Admin serta update role
    from werkzeug.security import generate_password_hash

    # Pastikan akun utama admin berlevel super_admin
    cursor.execute("SELECT id, role FROM users WHERE username = 'admin'")
    row_admin = cursor.fetchone()
    if not row_admin:
        cursor.execute('''
            INSERT INTO users (username, password_hash, nama, email, role, no_hp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', generate_password_hash('admin123'), 'Administrator Utama', 'admin@survei.go.id', 'super_admin', '081234567890', 'Aktif'))
    else:
        # Jika masih bertipe admin biasa, jadikan super_admin
        if row_admin['role'] != 'super_admin':
            cursor.execute("UPDATE users SET role = 'super_admin' WHERE id = ?", (row_admin['id'],))

    # Seed akun Admin biasa (Staf Operasional) jika belum ada
    cursor.execute("SELECT id FROM users WHERE username = 'admin_staf'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password_hash, nama, email, role, no_hp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin_staf', generate_password_hash('admin123'), 'Staf Operasional Survei', 'staf@survei.go.id', 'admin', '081399887766', 'Aktif'))

    cursor.execute("UPDATE petugas SET password_hash = ? WHERE password_hash IS NULL OR password_hash = ''",
                   (generate_password_hash('password123'),))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
