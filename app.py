import os
import io
import json
import csv
import socket
import zipfile
import shutil
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, jsonify, send_file, abort, session
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = 'sisurvei-super-secret-key-production-2026'

def get_local_ip():
    """Mendeteksi IP LAN / WiFi komputer agar bisa diakses oleh perangkat Android"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

# Konfigurasi Upload Foto Petugas & Profil Admin
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'petugas')
UPLOAD_FOLDER_PROFIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'profil')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_PROFIL, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_photo(file_obj, nip):
    if not file_obj or file_obj.filename == '':
        return None
    if allowed_file(file_obj.filename):
        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        clean_nip = secure_filename(str(nip).replace('-', '_'))
        filename = f"ptg_{clean_nip}_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file_obj.save(filepath)
        return f"uploads/petugas/{filename}"
    return None

def save_uploaded_admin_photo(file_obj, username):
    if not file_obj or file_obj.filename == '':
        return None
    if allowed_file(file_obj.filename):
        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        clean_user = secure_filename(str(username).replace('-', '_'))
        filename = f"admin_{clean_user}_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER_PROFIL, filename)
        file_obj.save(filepath)
        return f"uploads/profil/{filename}"
    return None

def log_activity(aksi, rincian=""):
    """Mencatat log aktivitas penting ke tabel audit_logs"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        uid = session.get('user_id')
        uname = session.get('user_name', 'System')
        role = session.get('admin_level') or session.get('user_role', 'guest')
        ip = request.remote_addr or '127.0.0.1'
        cursor.execute('''
            INSERT INTO audit_logs (user_id, user_name, role, aksi, rincian, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (uid, uname, role, aksi, rincian, ip))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUDIT LOG WARNING] {e}")

def super_admin_required(f):
    """Decorator khusus untuk melindungi menu khusus level Super Admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin' or session.get('admin_level') != 'super_admin':
            flash("Akses ditolak: Menu ini berstatus privat dan hanya dapat dikelola oleh level Super Admin.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_operator():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM petugas WHERE status = 'Aktif' ORDER BY id ASC")
    all_active = [dict(r) for r in cursor.fetchall()]
    
    op_id = session.get('operator_id')
    current_op = None
    if op_id:
        for p in all_active:
            if p['id'] == op_id:
                current_op = p
                break
                
    if not current_op and all_active:
        if session.get('user_role') == 'admin':
            current_op = all_active[0]
            session['operator_id'] = current_op['id']
        elif session.get('user_role') == 'operator':
            uid = session.get('user_id')
            for p in all_active:
                if p['id'] == uid:
                    current_op = p
                    session['operator_id'] = p['id']
                    break
                    
    conn.close()
    return current_op, all_active

# Context processor untuk informasi pengguna & IP Akses Android
@app.context_processor
def inject_auth_user():
    ip = get_local_ip()
    port = int(os.environ.get('PORT', 5005))
    admin_level = session.get('admin_level', 'admin')
    is_super = (session.get('user_role') == 'admin' and admin_level == 'super_admin')
    
    # Ambil pengaturan aplikasi dari DB
    app_meta = {
        'nama_aplikasi': 'SiSurvei - Portal Manajemen Survei Terpadu',
        'nama_instansi': 'Lembaga Riset & Pelayanan Publik',
        'email_resmi': 'layanan@survei.go.id',
        'telepon_resmi': '021-8889991',
        'alamat_kantor': 'Gedung Informasi & Statistik Lt. 4, Jakarta',
        'zona_waktu': 'Asia/Jakarta (WIB)'
    }
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT kunci, nilai FROM pengaturan")
        for row in c.fetchall():
            app_meta[row['kunci']] = row['nilai']
        conn.close()
    except Exception:
        pass

    return {
        'logged_user': {
            'role': session.get('user_role'),
            'admin_level': admin_level,
            'is_super_admin': is_super,
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'nip': session.get('nip'),
            'username': session.get('username'),
            'email': session.get('email'),
            'no_hp': session.get('user_hp'),
            'foto': session.get('user_foto')
        },
        'app_settings': app_meta,
        'network_ip': ip,
        'network_port': port,
        'android_access_url': f"http://{ip}:{port}"
    }

# ==========================================
# SISTEM OTENTIKASI & KONTROL AKSES (AUTH)
# ==========================================
@app.before_request
def check_authentication():
    # 1. Jalur statis dan assets
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return
        
    # 2. Endpoint otentikasi publik
    if request.endpoint in ('login', 'logout'):
        return
        
    # 3. Formulir pengisian survei responden publik
    if request.endpoint in ('survei_isi', 'survei_sukses') or request.path.startswith('/s/'):
        return
        
    # 4. Cek status login
    if 'user_role' not in session:
        flash("Silakan masuk terlebih dahulu untuk mengakses sistem SiSurvei.", "info")
        return redirect(url_for('login', next=request.path))
        
    # 5. Batasan hak akses Role Operator:
    # Petugas hanya boleh mengakses portal operator (/operator/*)
    if session.get('user_role') == 'operator':
        is_operator_path = (
            request.path.startswith('/operator') or 
            request.path.startswith('/api/responden') or
            (request.endpoint and request.endpoint.startswith('operator_'))
        )
        if not is_operator_path:
            flash("Akses ditolak: Akun Petugas Enumerator hanya memiliki akses ke Profil dan Tugas Survei.", "danger")
            return redirect(url_for('operator_tugas'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_role' in session:
        if session['user_role'] == 'admin':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('operator_tugas'))
            
    if request.method == 'POST':
        role = request.form.get('role', 'operator').strip()
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        next_url = request.form.get('next', '').strip()
        
        if not identifier or not password:
            flash("Mohon lengkapi NIP/Username dan Kata Sandi.", "warning")
            return render_template('auth/login.html')
            
        conn = get_db()
        cursor = conn.cursor()
        
        if role == 'admin':
            cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (identifier, identifier))
            user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                # Validasi status akun
                if 'status' in user.keys() and user['status'] == 'Nonaktif':
                    flash("Akun Administrator ini berstatus Nonaktif. Silakan hubungi Super Admin.", "danger")
                    return render_template('auth/login.html')

                session.clear()
                session['user_role'] = 'admin'
                session['admin_level'] = user['role'] if user['role'] in ('super_admin', 'admin') else 'admin'
                session['user_id'] = user['id']
                session['user_name'] = user['nama']
                session['username'] = user['username']
                session['email'] = user['email']
                session['user_hp'] = user['no_hp'] if 'no_hp' in user.keys() else ''
                session['user_foto'] = user['foto'] if 'foto' in user.keys() else None
                
                log_activity("Login Administrator", f"Pengguna {user['nama']} ({session['admin_level']}) berhasil login")
                flash(f"Selamat datang kembali, {user['nama']}! Anda aktif sebagai {session['admin_level'].replace('_', ' ').title()}.", "success")
                if next_url and next_url.startswith('/') and not next_url.startswith('/login'):
                    return redirect(next_url)
                return redirect(url_for('dashboard'))
            else:
                flash("Username/email atau kata sandi Administrator salah!", "danger")
                return render_template('auth/login.html')
        else:
            # Role: operator
            cursor.execute("SELECT * FROM petugas WHERE (nip = ? OR email = ?)", (identifier, identifier))
            petugas = cursor.fetchone()
            conn.close()
            
            if petugas:
                if petugas['status'] != 'Aktif':
                    flash("Akun petugas ini berstatus non-aktif. Silakan hubungi Administrator.", "danger")
                    return render_template('auth/login.html')
                    
                pwd_hash = petugas['password_hash']
                if pwd_hash and check_password_hash(pwd_hash, password):
                    session.clear()
                    session['user_role'] = 'operator'
                    session['operator_id'] = petugas['id']
                    session['user_id'] = petugas['id']
                    session['user_name'] = petugas['nama']
                    session['nip'] = petugas['nip']
                    session['wilayah'] = petugas['wilayah']
                    flash(f"Selamat datang, {petugas['nama']}! Semangat bertugas.", "success")
                    if next_url and next_url.startswith('/operator'):
                        return redirect(next_url)
                    return redirect(url_for('operator_tugas'))
                    
            flash("NIP atau kata sandi Petugas Enumerator tidak sesuai!", "danger")
            return render_template('auth/login.html')
            
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    nama = session.get('user_name', '')
    session.clear()
    if nama:
        flash(f"Sampai jumpa, {nama}. Anda telah berhasil keluar dari sistem.", "info")
    else:
        flash("Anda telah berhasil keluar dari sistem SiSurvei.", "info")
    return redirect(url_for('login'))

# Custom Jinja filters
@app.template_filter('from_json')
def from_json_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []

@app.template_filter('format_datetime')
def format_datetime_filter(value):
    if not value:
        return '-'
    try:
        dt = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return str(value)

@app.template_filter('format_date')
def format_date_filter(value):
    if not value:
        return '-'
    try:
        dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return dt.strftime("%d %b %Y")
    except Exception:
        return str(value)

# ==========================================
# 1. DASHBOARD UTAMA
# ==========================================
@app.route('/')
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    # KPI 1: Total Survei
    cursor.execute("SELECT COUNT(*) FROM survei")
    total_survei = cursor.fetchone()[0]
    
    # KPI 2: Survei Aktif
    cursor.execute("SELECT COUNT(*) FROM survei WHERE status = 'Aktif'")
    survei_aktif = cursor.fetchone()[0]
    
    # KPI 3: Total Responden
    cursor.execute("SELECT COUNT(*) FROM responden")
    total_responden = cursor.fetchone()[0]
    
    # KPI 4: Total Petugas Aktif
    cursor.execute("SELECT COUNT(*) FROM petugas WHERE status = 'Aktif'")
    petugas_aktif = cursor.fetchone()[0]
    
    # KPI 5: Rata-rata kepuasan (dari semua pertanyaan rating)
    cursor.execute("SELECT AVG(jawaban_angka) FROM jawaban WHERE jawaban_angka IS NOT NULL")
    avg_score = cursor.fetchone()[0]
    avg_score_formatted = round(avg_score, 2) if avg_score else 4.25
    
    # Tren Pengumpulan Respons 14 Hari Terakhir
    today = datetime.now().date()
    date_labels = []
    response_counts = []
    
    # Buat range 14 hari
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        d_label = d.strftime("%d %b")
        date_labels.append(d_label)
        
        cursor.execute("SELECT COUNT(*) FROM responden WHERE DATE(waktu_selesai) = ?", (d_str,))
        count = cursor.fetchone()[0]
        response_counts.append(count)
        
    # Distribusi Responden per Kategori Survei
    cursor.execute('''
        SELECT s.kategori, COUNT(r.id) as total
        FROM survei s
        LEFT JOIN responden r ON s.id = r.survei_id
        GROUP BY s.kategori
        ORDER BY total DESC
    ''')
    kategori_data = cursor.fetchall()
    cat_labels = [row['kategori'] for row in kategori_data]
    cat_counts = [row['total'] for row in kategori_data]
    
    # Kinerja Top 5 Petugas Survei
    cursor.execute('''
        SELECT p.nama, p.wilayah, COUNT(r.id) as total_input
        FROM petugas p
        LEFT JOIN responden r ON p.id = r.petugas_id
        WHERE p.status = 'Aktif'
        GROUP BY p.id
        ORDER BY total_input DESC
        LIMIT 5
    ''')
    top_petugas = cursor.fetchall()
    petugas_chart_names = [row['nama'].split(',')[0] for row in top_petugas]
    petugas_chart_counts = [row['total_input'] for row in top_petugas]
    
    # Daftar Survei Berjalan dengan Progress Capaian
    cursor.execute('''
        SELECT s.*, 
               COUNT(r.id) as total_masuk,
               (SELECT COUNT(*) FROM pertanyaan WHERE survei_id = s.id) as total_pertanyaan
        FROM survei s
        LEFT JOIN responden r ON s.id = r.survei_id
        GROUP BY s.id
        ORDER BY s.id DESC
    ''')
    survei_list = []
    for s in cursor.fetchall():
        s_dict = dict(s)
        target = s_dict['target_responden'] or 1
        persen = min(100, round((s_dict['total_masuk'] / target) * 100, 1))
        s_dict['persen_capaian'] = persen
        survei_list.append(s_dict)
        
    # 6 Respons Masuk Terbaru
    cursor.execute('''
        SELECT r.*, s.judul as judul_survei, s.kode_survei, p.nama as nama_petugas
        FROM responden r
        JOIN survei s ON r.survei_id = s.id
        LEFT JOIN petugas p ON r.petugas_id = p.id
        ORDER BY r.waktu_selesai DESC
        LIMIT 6
    ''')
    recent_responses = cursor.fetchall()
    
    conn.close()
    
    return render_template(
        'dashboard.html',
        total_survei=total_survei,
        survei_aktif=survei_aktif,
        total_responden=total_responden,
        petugas_aktif=petugas_aktif,
        avg_score=avg_score_formatted,
        date_labels=json.dumps(date_labels),
        response_counts=json.dumps(response_counts),
        cat_labels=json.dumps(cat_labels),
        cat_counts=json.dumps(cat_counts),
        petugas_chart_names=json.dumps(petugas_chart_names),
        petugas_chart_counts=json.dumps(petugas_chart_counts),
        survei_list=survei_list,
        recent_responses=recent_responses
    )

# ==========================================
# 2. MANAJEMEN SURVEI
# ==========================================
@app.route('/survei')
def survei_index():
    conn = get_db()
    cursor = conn.cursor()
    
    kategori = request.args.get('kategori', '')
    status = request.args.get('status', '')
    q = request.args.get('q', '').strip()
    
    query = '''
        SELECT s.*, 
               COUNT(DISTINCT r.id) as total_masuk,
               COUNT(DISTINCT sp.petugas_id) as total_petugas_assigned,
               COUNT(DISTINCT p.id) as total_pertanyaan
        FROM survei s
        LEFT JOIN responden r ON s.id = r.survei_id
        LEFT JOIN survei_petugas sp ON s.id = sp.survei_id
        LEFT JOIN pertanyaan p ON s.id = p.survei_id
        WHERE 1=1
    '''
    params = []
    if kategori:
        query += " AND s.kategori = ?"
        params.append(kategori)
    if status:
        query += " AND s.status = ?"
        params.append(status)
    if q:
        query += " AND (s.judul LIKE ? OR s.kode_survei LIKE ? OR s.deskripsi LIKE ?)"
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])
        
    query += " GROUP BY s.id ORDER BY s.id DESC"
    cursor.execute(query, params)
    survei_rows = cursor.fetchall()
    
    survei_list = []
    for row in survei_rows:
        item = dict(row)
        target = item['target_responden'] or 1
        item['persen_capaian'] = min(100, round((item['total_masuk'] / target) * 100, 1))
        survei_list.append(item)
        
    # Ambil list kategori unik untuk filter
    cursor.execute("SELECT DISTINCT kategori FROM survei WHERE kategori IS NOT NULL AND kategori != ''")
    kategori_list = [r['kategori'] for r in cursor.fetchall()]
    
    conn.close()
    return render_template('surveys/index.html', surveys=survei_list, kategori_list=kategori_list, filter_kategori=kategori, filter_status=status, filter_q=q)

@app.route('/survei/tambah', methods=['GET', 'POST'])
def survei_tambah():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        judul = request.form.get('judul', '').strip()
        kode_survei = request.form.get('kode_survei', '').strip().upper()
        kategori = request.form.get('kategori', 'Umum').strip()
        deskripsi = request.form.get('deskripsi', '').strip()
        target_responden = int(request.form.get('target_responden', 100))
        tanggal_mulai = request.form.get('tanggal_mulai') or None
        tanggal_selesai = request.form.get('tanggal_selesai') or None
        status = request.form.get('status', 'Aktif')
        is_public = 1 if request.form.get('is_public') else 0
        petugas_selected = request.form.getlist('petugas_ids')
        
        # Cek kode survei unik
        if not kode_survei:
            kode_survei = f"SRV-{datetime.now().strftime('%Y%m%d%H%M')}"
            
        cursor.execute("SELECT id FROM survei WHERE kode_survei = ?", (kode_survei,))
        if cursor.fetchone():
            flash(f"Kode survei '{kode_survei}' sudah digunakan! Silakan gunakan kode lain.", "danger")
            cursor.execute("SELECT * FROM petugas WHERE status = 'Aktif' ORDER BY nama ASC")
            all_petugas = cursor.fetchall()
            conn.close()
            return render_template('surveys/create.html', all_petugas=all_petugas)
            
        cursor.execute('''
            INSERT INTO survei (kode_survei, judul, deskripsi, kategori, target_responden, tanggal_mulai, tanggal_selesai, status, is_public)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (kode_survei, judul, deskripsi, kategori, target_responden, tanggal_mulai, tanggal_selesai, status, is_public))
        survei_id = cursor.lastrowid
        
        # Simpan penugasan petugas
        for p_id in petugas_selected:
            try:
                cursor.execute('''
                    INSERT INTO survei_petugas (survei_id, petugas_id, peran, target_individu)
                    VALUES (?, ?, 'Petugas Lapangan', ?)
                ''', (survei_id, int(p_id), max(10, target_responden // (len(petugas_selected) or 1))))
            except Exception:
                pass
                
        conn.commit()
        conn.close()
        flash(f"Survei '{judul}' berhasil dibuat! Sekarang Anda dapat merancang pertanyaan.", "success")
        return redirect(url_for('survei_builder', id=survei_id))
        
    cursor.execute("SELECT * FROM petugas WHERE status = 'Aktif' ORDER BY nama ASC")
    all_petugas = cursor.fetchall()
    
    # Auto-generate suggestion code
    suggested_code = f"SRV-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m%d%H')}"
    conn.close()
    return render_template('surveys/create.html', all_petugas=all_petugas, suggested_code=suggested_code)

@app.route('/survei/<int:id>/edit', methods=['GET', 'POST'])
def survei_edit(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM survei WHERE id = ?", (id,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        flash("Survei tidak ditemukan!", "danger")
        return redirect(url_for('survei_index'))
        
    if request.method == 'POST':
        judul = request.form.get('judul', '').strip()
        kode_survei = request.form.get('kode_survei', '').strip().upper()
        kategori = request.form.get('kategori', 'Umum').strip()
        deskripsi = request.form.get('deskripsi', '').strip()
        target_responden = int(request.form.get('target_responden', 100))
        tanggal_mulai = request.form.get('tanggal_mulai') or None
        tanggal_selesai = request.form.get('tanggal_selesai') or None
        status = request.form.get('status', 'Aktif')
        is_public = 1 if request.form.get('is_public') else 0
        petugas_selected = [int(p) for p in request.form.getlist('petugas_ids')]
        
        # Cek kode survei jika diubah
        cursor.execute("SELECT id FROM survei WHERE kode_survei = ? AND id != ?", (kode_survei, id))
        if cursor.fetchone():
            flash(f"Kode survei '{kode_survei}' telah digunakan oleh survei lain!", "danger")
            conn.close()
            return redirect(url_for('survei_edit', id=id))
            
        cursor.execute('''
            UPDATE survei 
            SET kode_survei = ?, judul = ?, deskripsi = ?, kategori = ?, target_responden = ?,
                tanggal_mulai = ?, tanggal_selesai = ?, status = ?, is_public = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (kode_survei, judul, deskripsi, kategori, target_responden, tanggal_mulai, tanggal_selesai, status, is_public, id))
        
        # Update penugasan petugas
        cursor.execute("DELETE FROM survei_petugas WHERE survei_id = ?", (id,))
        for p_id in petugas_selected:
            cursor.execute('''
                INSERT INTO survei_petugas (survei_id, petugas_id, peran, target_individu)
                VALUES (?, ?, 'Petugas Lapangan', ?)
            ''', (id, p_id, max(10, target_responden // (len(petugas_selected) or 1))))
            
        conn.commit()
        conn.close()
        flash("Perubahan data survei berhasil disimpan!", "success")
        return redirect(url_for('survei_index'))
        
    cursor.execute("SELECT * FROM petugas ORDER BY status ASC, nama ASC")
    all_petugas = cursor.fetchall()
    
    cursor.execute("SELECT petugas_id FROM survei_petugas WHERE survei_id = ?", (id,))
    assigned_petugas_ids = [r['petugas_id'] for r in cursor.fetchall()]
    
    conn.close()
    return render_template('surveys/edit.html', survei=survei, all_petugas=all_petugas, assigned_petugas_ids=assigned_petugas_ids)

@app.route('/survei/<int:id>/hapus', methods=['POST'])
def survei_hapus(id):
    if session.get('admin_level') != 'super_admin':
        flash("Akses ditolak: Hanya Super Admin yang berwenang menghapus kegiatan survei secara permanen.", "danger")
        return redirect(url_for('survei_index'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT judul FROM survei WHERE id = ?", (id,))
    s = cursor.fetchone()
    if s:
        judul = s['judul']
        cursor.execute("DELETE FROM survei WHERE id = ?", (id,))
        conn.commit()
        log_activity("Hapus Survei", f"Super Admin menghapus survei: '{judul}' (ID #{id})")
        flash(f"Survei '{judul}' beserta seluruh pertanyaan dan responsnya berhasil dihapus.", "success")
    conn.close()
    return redirect(url_for('survei_index'))

@app.route('/survei/<int:id>/toggle-status', methods=['POST'])
def survei_toggle_status(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM survei WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row:
        new_status = 'Selesai' if row['status'] == 'Aktif' else 'Aktif'
        cursor.execute("UPDATE survei SET status = ? WHERE id = ?", (new_status, id))
        conn.commit()
        flash(f"Status survei berhasil diubah menjadi: {new_status}", "info")
    conn.close()
    return redirect(request.referrer or url_for('survei_index'))

# ==========================================
# 3. QUESTION BUILDER (PERANCANG PERTANYAAN)
# ==========================================
@app.route('/survei/<int:id>/builder')
def survei_builder(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survei WHERE id = ?", (id,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        flash("Survei tidak ditemukan!", "danger")
        return redirect(url_for('survei_index'))
        
    cursor.execute("SELECT * FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC, id ASC", (id,))
    pertanyaan_rows = cursor.fetchall()
    
    questions = []
    for q in pertanyaan_rows:
        item = dict(q)
        item['pilihan_opsi_list'] = json.loads(item['pilihan_opsi']) if item['pilihan_opsi'] else []
        questions.append(item)
        
    conn.close()
    return render_template('surveys/builder.html', survei=survei, questions=questions)

@app.route('/api/survei/<int:id>/pertanyaan', methods=['POST'])
def api_tambah_pertanyaan(id):
    conn = get_db()
    cursor = conn.cursor()
    data = request.get_json() or {}
    
    teks = data.get('teks_pertanyaan', '').strip()
    tipe = data.get('tipe_pertanyaan', 'short_text')
    opsi = data.get('pilihan_opsi', [])
    is_required = 1 if data.get('is_required', True) else 0
    panduan = data.get('panduan', '').strip()
    rating_max = int(data.get('rating_max', 5))
    
    if not teks:
        conn.close()
        return jsonify({'success': False, 'message': 'Teks pertanyaan wajib diisi!'}), 400
        
    # Ambil urutan terakhir
    cursor.execute("SELECT MAX(urutan) FROM pertanyaan WHERE survei_id = ?", (id,))
    max_urutan = cursor.fetchone()[0] or 0
    urutan = max_urutan + 1
    
    opsi_json = json.dumps(opsi, ensure_ascii=False) if opsi and tipe in ['radio', 'checkbox', 'dropdown'] else None
    
    cursor.execute('''
        INSERT INTO pertanyaan (survei_id, teks_pertanyaan, tipe_pertanyaan, pilihan_opsi, is_required, urutan, panduan, rating_max)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id, teks, tipe, opsi_json, is_required, urutan, panduan, rating_max))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Pertanyaan berhasil ditambahkan!',
        'id': new_id,
        'urutan': urutan
    })

@app.route('/api/pertanyaan/<int:id>/update', methods=['POST'])
def api_update_pertanyaan(id):
    conn = get_db()
    cursor = conn.cursor()
    data = request.get_json() or {}
    
    teks = data.get('teks_pertanyaan', '').strip()
    tipe = data.get('tipe_pertanyaan', 'short_text')
    opsi = data.get('pilihan_opsi', [])
    is_required = 1 if data.get('is_required', True) else 0
    panduan = data.get('panduan', '').strip()
    rating_max = int(data.get('rating_max', 5))
    
    if not teks:
        conn.close()
        return jsonify({'success': False, 'message': 'Teks pertanyaan tidak boleh kosong!'}), 400
        
    opsi_json = json.dumps(opsi, ensure_ascii=False) if opsi and tipe in ['radio', 'checkbox', 'dropdown'] else None
    
    cursor.execute('''
        UPDATE pertanyaan
        SET teks_pertanyaan = ?, tipe_pertanyaan = ?, pilihan_opsi = ?, is_required = ?, panduan = ?, rating_max = ?
        WHERE id = ?
    ''', (teks, tipe, opsi_json, is_required, panduan, rating_max, id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Pertanyaan berhasil diperbarui!'})

@app.route('/api/pertanyaan/<int:id>/hapus', methods=['POST'])
def api_hapus_pertanyaan(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pertanyaan WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Pertanyaan berhasil dihapus!'})

@app.route('/api/survei/<int:id>/reorder', methods=['POST'])
def api_reorder_pertanyaan(id):
    conn = get_db()
    cursor = conn.cursor()
    data = request.get_json() or {}
    order_list = data.get('order', []) # list of question IDs in order
    
    for idx, q_id in enumerate(order_list):
        cursor.execute("UPDATE pertanyaan SET urutan = ? WHERE id = ? AND survei_id = ?", (idx + 1, q_id, id))
        
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Urutan berhasil disimpan!'})

# ==========================================
# 4. FORMULIR PENGISIAN SURVEI (PUBLIK & PETUGAS)
# ==========================================
@app.route('/s/<kode_survei>', methods=['GET', 'POST'])
def survei_isi(kode_survei):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM survei WHERE kode_survei = ?", (kode_survei,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        abort(404)
        
    if survei['status'] != 'Aktif':
        conn.close()
        return render_template('surveys/closed.html', survei=survei)
        
    # Ambil pertanyaan
    cursor.execute("SELECT * FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC, id ASC", (survei['id'],))
    pertanyaan_rows = cursor.fetchall()
    
    questions = []
    for q in pertanyaan_rows:
        item = dict(q)
        item['pilihan_opsi_list'] = json.loads(item['pilihan_opsi']) if item['pilihan_opsi'] else []
        questions.append(item)
        
    # Ambil petugas yang ditugaskan untuk pilihan enumerator
    cursor.execute('''
        SELECT p.*, sp.peran
        FROM survei_petugas sp
        JOIN petugas p ON sp.petugas_id = p.id
        WHERE sp.survei_id = ? AND p.status = 'Aktif'
        ORDER BY p.nama ASC
    ''', (survei['id'],))
    petugas_list = cursor.fetchall()
    
    if request.method == 'POST':
        # Data Identitas Responden
        nama_responden = request.form.get('nama_responden', '').strip() or 'Anonim'
        kontak_responden = request.form.get('kontak_responden', '').strip()
        usia = request.form.get('usia') or None
        if usia:
            try:
                usia = int(usia)
            except ValueError:
                usia = None
        jenis_kelamin = request.form.get('jenis_kelamin', 'Rahasia')
        pendidikan_terakhir = request.form.get('pendidikan_terakhir', '').strip() or None
        titik_koordinat = request.form.get('titik_koordinat', '').strip() or request.form.get('alamat_wilayah', '').strip() or None
        alamat_wilayah = request.form.get('alamat_wilayah', '').strip() or titik_koordinat
        
        # Petugas penginput
        petugas_id = request.form.get('petugas_id')
        petugas_id = int(petugas_id) if petugas_id and petugas_id.isdigit() else None
        
        ip_addr = request.remote_addr or '127.0.0.1'
        
        cursor.execute('''
            INSERT INTO responden (survei_id, petugas_id, nama_responden, kontak_responden, usia, jenis_kelamin, pendidikan_terakhir, titik_koordinat, alamat_wilayah, ip_address, waktu_selesai)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (survei['id'], petugas_id, nama_responden, kontak_responden, usia, jenis_kelamin, pendidikan_terakhir, titik_koordinat, alamat_wilayah, ip_addr))
        responden_id = cursor.lastrowid
        
        # Simpan setiap jawaban
        for q in questions:
            q_id = q['id']
            q_tipe = q['tipe_pertanyaan']
            field_name = f"q_{q_id}"
            
            jawaban_teks = None
            jawaban_angka = None
            
            if q_tipe == 'checkbox':
                checked_vals = request.form.getlist(f"{field_name}[]")
                if checked_vals:
                    jawaban_teks = json.dumps(checked_vals, ensure_ascii=False)
            elif q_tipe in ['rating', 'number']:
                val = request.form.get(field_name)
                if val is not None and val != '':
                    jawaban_teks = str(val).strip()
                    try:
                        jawaban_angka = float(val)
                    except ValueError:
                        jawaban_angka = None
            else:
                val = request.form.get(field_name)
                if val is not None and val != '':
                    jawaban_teks = str(val).strip()
                    
            cursor.execute('''
                INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka)
                VALUES (?, ?, ?, ?)
            ''', (responden_id, q_id, jawaban_teks, jawaban_angka))
            
        conn.commit()
        conn.close()
        return redirect(url_for('survei_sukses', kode_survei=kode_survei, resp_id=responden_id))
        
    conn.close()
    return render_template('surveys/fill.html', survei=survei, questions=questions, petugas_list=petugas_list)

@app.route('/s/<kode_survei>/sukses')
def survei_sukses(kode_survei):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survei WHERE kode_survei = ?", (kode_survei,))
    survei = cursor.fetchone()
    resp_id = request.args.get('resp_id')
    conn.close()
    return render_template('surveys/thank_you.html', survei=survei, resp_id=resp_id)

# ==========================================
# 5. DASHBOARD HASIL & ANALISIS SURVEI
# ==========================================
@app.route('/survei/<int:id>/hasil')
def survei_hasil(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM survei WHERE id = ?", (id,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        flash("Survei tidak ditemukan!", "danger")
        return redirect(url_for('survei_index'))
        
    # Filter parameter
    filter_petugas = request.args.get('petugas_id')
    filter_jk = request.args.get('jk')
    filter_start = request.args.get('start_date')
    filter_end = request.args.get('end_date')
    
    resp_query = "SELECT r.*, p.nama as nama_petugas FROM responden r LEFT JOIN petugas p ON r.petugas_id = p.id WHERE r.survei_id = ?"
    resp_params = [id]
    
    if filter_petugas:
        if filter_petugas == 'mandiri':
            resp_query += " AND r.petugas_id IS NULL"
        else:
            resp_query += " AND r.petugas_id = ?"
            resp_params.append(filter_petugas)
    if filter_jk:
        resp_query += " AND r.jenis_kelamin = ?"
        resp_params.append(filter_jk)
    if filter_start:
        resp_query += " AND DATE(r.waktu_selesai) >= ?"
        resp_params.append(filter_start)
    if filter_end:
        resp_query += " AND DATE(r.waktu_selesai) <= ?"
        resp_params.append(filter_end)
        
    resp_query += " ORDER BY r.waktu_selesai DESC"
    cursor.execute(resp_query, resp_params)
    all_respondents = cursor.fetchall()
    
    total_responden_count = len(all_respondents)
    target = survei['target_responden'] or 1
    persen_capaian = min(100, round((total_responden_count / target) * 100, 1))
    
    # Ambil semua pertanyaan
    cursor.execute("SELECT * FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC, id ASC", (id,))
    pertanyaan_rows = cursor.fetchall()
    
    # Kumpulkan analisis data per pertanyaan
    analytics = []
    
    # Dapatkan respondent IDs yang terpilih sesuai filter
    selected_resp_ids = [r['id'] for r in all_respondents]
    id_placeholders = ','.join(['?'] * len(selected_resp_ids)) if selected_resp_ids else '0'
    
    for q in pertanyaan_rows:
        q_dict = dict(q)
        q_id = q_dict['id']
        q_tipe = q_dict['tipe_pertanyaan']
        q_dict['pilihan_opsi_list'] = json.loads(q_dict['pilihan_opsi']) if q_dict['pilihan_opsi'] else []
        
        # Ambil jawaban yang relevan
        if selected_resp_ids:
            cursor.execute(f'''
                SELECT j.jawaban_teks, j.jawaban_angka, r.nama_responden, r.waktu_selesai
                FROM jawaban j
                JOIN responden r ON j.responden_id = r.id
                WHERE j.pertanyaan_id = ? AND j.responden_id IN ({id_placeholders})
                  AND j.jawaban_teks IS NOT NULL AND j.jawaban_teks != ''
            ''', [q_id] + selected_resp_ids)
            answers = cursor.fetchall()
        else:
            answers = []
            
        total_jawaban = len(answers)
        q_dict['total_jawaban'] = total_jawaban
        
        if q_tipe in ['radio', 'dropdown']:
            # Hitung frekuensi tiap opsi
            freq = {opt: 0 for opt in q_dict['pilihan_opsi_list']}
            for ans in answers:
                val = ans['jawaban_teks']
                if val in freq:
                    freq[val] += 1
                else:
                    freq[val] = freq.get(val, 0) + 1
            labels = list(freq.keys())
            counts = [freq[l] for l in labels]
            q_dict['chart_labels'] = json.dumps(labels)
            q_dict['chart_counts'] = json.dumps(counts)
            q_dict['freq_table'] = [{'label': l, 'count': freq[l], 'percent': round((freq[l]/total_jawaban*100), 1) if total_jawaban else 0} for l in labels]
            
        elif q_tipe == 'checkbox':
            # Jawaban disimpan sebagai JSON array of strings
            freq = {opt: 0 for opt in q_dict['pilihan_opsi_list']}
            for ans in answers:
                try:
                    chosen = json.loads(ans['jawaban_teks'])
                    if isinstance(chosen, list):
                        for c in chosen:
                            if c in freq:
                                freq[c] += 1
                            else:
                                freq[c] = freq.get(c, 0) + 1
                except Exception:
                    pass
            labels = list(freq.keys())
            counts = [freq[l] for l in labels]
            q_dict['chart_labels'] = json.dumps(labels)
            q_dict['chart_counts'] = json.dumps(counts)
            q_dict['freq_table'] = [{'label': l, 'count': freq[l], 'percent': round((freq[l]/total_jawaban*100), 1) if total_jawaban else 0} for l in labels]
            
        elif q_tipe == 'rating':
            # Rata-rata & distribusi skor 1 sampai rating_max
            max_r = q_dict.get('rating_max', 5) or 5
            score_counts = {str(i): 0 for i in range(1, max_r + 1)}
            scores = []
            for ans in answers:
                if ans['jawaban_angka'] is not None:
                    val = int(round(ans['jawaban_angka']))
                    scores.append(ans['jawaban_angka'])
                    s_str = str(val)
                    if s_str in score_counts:
                        score_counts[s_str] += 1
                        
            avg_score = round(sum(scores) / len(scores), 2) if scores else 0
            labels = [f"★ {i}" for i in range(1, max_r + 1)]
            counts = [score_counts[str(i)] for i in range(1, max_r + 1)]
            q_dict['avg_score'] = avg_score
            q_dict['chart_labels'] = json.dumps(labels)
            q_dict['chart_counts'] = json.dumps(counts)
            
        elif q_tipe == 'number':
            nums = [ans['jawaban_angka'] for ans in answers if ans['jawaban_angka'] is not None]
            if nums:
                q_dict['num_avg'] = round(sum(nums)/len(nums), 1)
                q_dict['num_min'] = round(min(nums), 1)
                q_dict['num_max'] = round(max(nums), 1)
            else:
                q_dict['num_avg'] = q_dict['num_min'] = q_dict['num_max'] = 0
                
        elif q_tipe in ['short_text', 'long_text', 'date']:
            # Tampilkan sampel respon teks terbaru
            sample_answers = []
            for ans in answers[:15]:
                sample_answers.append({
                    'nama': ans['nama_responden'] or 'Anonim',
                    'teks': ans['jawaban_teks'],
                    'waktu': ans['waktu_selesai']
                })
            q_dict['sample_answers'] = sample_answers
            
        analytics.append(q_dict)
        
    # List Petugas yang ditugaskan di survei ini untuk filter dropdown
    cursor.execute('''
        SELECT p.id, p.nama, p.wilayah
        FROM survei_petugas sp
        JOIN petugas p ON sp.petugas_id = p.id
        WHERE sp.survei_id = ?
        ORDER BY p.nama ASC
    ''', (id,))
    petugas_filter_options = cursor.fetchall()
    
    conn.close()
    
    return render_template(
        'surveys/results.html',
        survei=survei,
        total_responden=total_responden_count,
        persen_capaian=persen_capaian,
        analytics=analytics,
        respondents=all_respondents,
        petugas_options=petugas_filter_options,
        filter_petugas=filter_petugas,
        filter_jk=filter_jk,
        filter_start=filter_start,
        filter_end=filter_end
    )

# Modal detail jawaban satu responden
@app.route('/api/responden/<int:resp_id>/detail')
def api_responden_detail(resp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, s.judul as judul_survei, p.nama as nama_petugas, p.nip as nip_petugas
        FROM responden r
        JOIN survei s ON r.survei_id = s.id
        LEFT JOIN petugas p ON r.petugas_id = p.id
        WHERE r.id = ?
    ''', (resp_id,))
    r_data = cursor.fetchone()
    if not r_data:
        conn.close()
        return jsonify({'success': False, 'message': 'Responden tidak ditemukan'}), 404
        
    cursor.execute('''
        SELECT p.teks_pertanyaan, p.tipe_pertanyaan, p.rating_max, j.jawaban_teks, j.jawaban_angka
        FROM pertanyaan p
        LEFT JOIN jawaban j ON p.id = j.pertanyaan_id AND j.responden_id = ?
        WHERE p.survei_id = ?
        ORDER BY p.urutan ASC, p.id ASC
    ''', (resp_id, r_data['survei_id']))
    jawaban_rows = cursor.fetchall()
    
    qa_list = []
    for row in jawaban_rows:
        item = dict(row)
        if item['tipe_pertanyaan'] == 'checkbox' and item['jawaban_teks']:
            try:
                item['jawaban_teks_parsed'] = json.loads(item['jawaban_teks'])
            except Exception:
                item['jawaban_teks_parsed'] = [item['jawaban_teks']]
        else:
            item['jawaban_teks_parsed'] = item['jawaban_teks']
        qa_list.append(item)
        
    conn.close()
    return jsonify({
        'success': True,
        'responden': dict(r_data),
        'answers': qa_list
    })

# ==========================================
# 6. EKSPOR DATA HASIL SURVEI (EXCEL & CSV)
# ==========================================
@app.route('/survei/<int:id>/export/excel')
def survei_export_excel(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM survei WHERE id = ?", (id,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        flash("Survei tidak ditemukan!", "danger")
        return redirect(url_for('survei_index'))
        
    cursor.execute("SELECT * FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC, id ASC", (id,))
    pertanyaan_list = cursor.fetchall()
    
    cursor.execute('''
        SELECT r.*, p.nama as nama_petugas
        FROM responden r
        LEFT JOIN petugas p ON r.petugas_id = p.id
        WHERE r.survei_id = ?
        ORDER BY r.waktu_selesai ASC
    ''', (id,))
    responden_list = cursor.fetchall()
    
    # Ambil semua jawaban
    cursor.execute('''
        SELECT j.responden_id, j.pertanyaan_id, j.jawaban_teks
        FROM jawaban j
        JOIN responden r ON j.responden_id = r.id
        WHERE r.survei_id = ?
    ''', (id,))
    jawaban_map = {}
    for j in cursor.fetchall():
        jawaban_map[(j['responden_id'], j['pertanyaan_id'])] = j['jawaban_teks']
        
    conn.close()
    
    # Gunakan openpyxl untuk membuat file Excel yang rapi
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hasil Survei"
    
    # Header styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )
    
    # Metadata judul di baris 1-3
    ws.merge_cells("A1:G1")
    ws["A1"] = f"{survei['judul']} ({survei['kode_survei']})"
    ws["A1"].font = Font(size=14, bold=True, color="1E3A8A")
    
    ws.merge_cells("A2:G2")
    ws["A2"] = f"Kategori: {survei['kategori']} | Total Responden: {len(responden_list)} | Waktu Unduh: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    ws["A2"].font = Font(size=10, italic=True, color="4B5563")
    
    # Headers baris 4
    headers = ["No", "ID Responden", "Waktu Pengisian", "Nama Responden", "No HP/Kontak", "Usia", "Jenis Kelamin", "Pendidikan Terakhir", "Titik Koordinat / Lokasi", "Petugas Penginput"]
    for q in pertanyaan_list:
        headers.append(f"Q{q['urutan']}: {q['teks_pertanyaan']}")
        
    ws.row_dimensions[4].height = 28
    for col_num, h_text in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = h_text
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        
    # Isi Data Responden
    for row_idx, r in enumerate(responden_list, 5):
        row_cells = [
            row_idx - 4,
            f"R-{r['id']:04d}",
            str(r['waktu_selesai'])[:19],
            r['nama_responden'] or 'Anonim',
            r['kontak_responden'] or '-',
            r['usia'] if r['usia'] else '-',
            r['jenis_kelamin'] or '-',
            r['pendidikan_terakhir'] or '-',
            r['titik_koordinat'] or r['alamat_wilayah'] or '-',
            r['nama_petugas'] or 'Mandiri (Publik)'
        ]
        
        # Jawaban tiap pertanyaan
        for q in pertanyaan_list:
            ans_val = jawaban_map.get((r['id'], q['id']), '-')
            if q['tipe_pertanyaan'] == 'checkbox' and ans_val and ans_val != '-':
                try:
                    c_list = json.loads(ans_val)
                    ans_val = ", ".join(c_list)
                except Exception:
                    pass
            row_cells.append(ans_val if ans_val is not None else '-')
            
        for col_num, val in enumerate(row_cells, 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.value = val
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            
    # Auto adjust column widths
    from openpyxl.utils import get_column_letter
    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(str(headers[col_idx - 1]))
        for row_idx in range(5, 5 + len(responden_list)):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = min(40, max(12, max_len + 3))
        
    out_stream = io.BytesIO()
    wb.save(out_stream)
    out_stream.seek(0)
    
    filename = f"Hasil_Survei_{survei['kode_survei']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        out_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route('/survei/<int:id>/export/csv')
def survei_export_csv(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM survei WHERE id = ?", (id,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        flash("Survei tidak ditemukan!", "danger")
        return redirect(url_for('survei_index'))
        
    cursor.execute("SELECT * FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC, id ASC", (id,))
    pertanyaan_list = cursor.fetchall()
    
    cursor.execute('''
        SELECT r.*, p.nama as nama_petugas
        FROM responden r
        LEFT JOIN petugas p ON r.petugas_id = p.id
        WHERE r.survei_id = ?
        ORDER BY r.waktu_selesai ASC
    ''', (id,))
    responden_list = cursor.fetchall()
    
    cursor.execute('''
        SELECT j.responden_id, j.pertanyaan_id, j.jawaban_teks
        FROM jawaban j
        JOIN responden r ON j.responden_id = r.id
        WHERE r.survei_id = ?
    ''', (id,))
    jawaban_map = {(j['responden_id'], j['pertanyaan_id']): j['jawaban_teks'] for j in cursor.fetchall()}
    conn.close()
    
    out_stream = io.StringIO()
    writer = csv.writer(out_stream)
    
    headers = ["No", "ID Responden", "Waktu Pengisian", "Nama Responden", "Kontak", "Usia", "Jenis Kelamin", "Pendidikan Terakhir", "Titik Koordinat / Lokasi", "Petugas Penginput"]
    for q in pertanyaan_list:
        headers.append(f"Q{q['urutan']}: {q['teks_pertanyaan']}")
    writer.writerow(headers)
    
    for idx, r in enumerate(responden_list, 1):
        row = [
            idx,
            f"R-{r['id']:04d}",
            str(r['waktu_selesai']),
            r['nama_responden'] or 'Anonim',
            r['kontak_responden'] or '',
            r['usia'] or '',
            r['jenis_kelamin'] or '',
            r['pendidikan_terakhir'] or '',
            r['titik_koordinat'] or r['alamat_wilayah'] or '',
            r['nama_petugas'] or 'Mandiri'
        ]
        for q in pertanyaan_list:
            ans_val = jawaban_map.get((r['id'], q['id']), '')
            if q['tipe_pertanyaan'] == 'checkbox' and ans_val:
                try:
                    c_list = json.loads(ans_val)
                    ans_val = "; ".join(c_list)
                except Exception:
                    pass
            row.append(ans_val if ans_val is not None else '')
        writer.writerow(row)
        
    mem_bytes = io.BytesIO()
    mem_bytes.write(out_stream.getvalue().encode('utf-8-sig'))
    mem_bytes.seek(0)
    
    filename = f"Hasil_Survei_{survei['kode_survei']}_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(mem_bytes, mimetype="text/csv", as_attachment=True, download_name=filename)

# ==========================================
# 7. PENGELOLAAN DATA PETUGAS SURVEI
# ==========================================
@app.route('/petugas')
def petugas_index():
    conn = get_db()
    cursor = conn.cursor()
    
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    
    query = '''
        SELECT p.*,
               COUNT(DISTINCT sp.survei_id) as total_survei_assigned,
               COUNT(DISTINCT r.id) as total_respon_diinput
        FROM petugas p
        LEFT JOIN survei_petugas sp ON p.id = sp.petugas_id
        LEFT JOIN responden r ON p.id = r.petugas_id
        WHERE 1=1
    '''
    params = []
    if status:
        query += " AND p.status = ?"
        params.append(status)
    if q:
        query += " AND (p.nama LIKE ? OR p.nip LIKE ? OR p.wilayah LIKE ? OR p.jabatan LIKE ?)"
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])
        
    query += " GROUP BY p.id ORDER BY p.status ASC, p.nama ASC"
    cursor.execute(query, params)
    petugas_list = [dict(r) for r in cursor.fetchall()]
    
    # Ambil list wilayah unik untuk filter
    cursor.execute("SELECT DISTINCT wilayah FROM petugas WHERE wilayah IS NOT NULL AND wilayah != ''")
    wilayah_list = [r['wilayah'] for r in cursor.fetchall()]
    
    conn.close()
    return render_template('petugas/index.html', petugas_list=petugas_list, wilayah_list=wilayah_list, filter_status=status, filter_q=q)

@app.route('/petugas/tambah', methods=['POST'])
def petugas_tambah():
    conn = get_db()
    cursor = conn.cursor()
    
    nip = request.form.get('nip', '').strip()
    nama = request.form.get('nama', '').strip()
    email = request.form.get('email', '').strip()
    no_hp = request.form.get('no_hp', '').strip()
    wilayah = request.form.get('wilayah', '').strip()
    jabatan = request.form.get('jabatan', 'Petugas Lapangan').strip()
    status = request.form.get('status', 'Aktif')
    
    if not nip or not nama:
        flash("NIP dan Nama Petugas wajib diisi!", "danger")
        conn.close()
        return redirect(url_for('petugas_index'))
        
    # Cek NIP unik
    cursor.execute("SELECT id FROM petugas WHERE nip = ?", (nip,))
    if cursor.fetchone():
        flash(f"NIP '{nip}' sudah terdaftar! Gunakan NIP yang berbeda.", "danger")
        conn.close()
        return redirect(url_for('petugas_index'))
        
    foto_file = request.files.get('foto_file')
    foto_url = request.form.get('foto_url', '').strip()
    foto = save_uploaded_photo(foto_file, nip) or (foto_url if foto_url else None)

    password = request.form.get('password', '').strip() or 'password123'
    password_hash = generate_password_hash(password)

    cursor.execute('''
        INSERT INTO petugas (nip, nama, email, no_hp, wilayah, jabatan, status, foto, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nip, nama, email, no_hp, wilayah, jabatan, status, foto, password_hash))
    conn.commit()
    conn.close()
    flash(f"Petugas '{nama}' berhasil ditambahkan ke sistem! (Kata sandi default: {password})", "success")
    return redirect(url_for('petugas_index'))

@app.route('/petugas/<int:id>/edit', methods=['POST'])
def petugas_edit(id):
    conn = get_db()
    cursor = conn.cursor()
    
    nip = request.form.get('nip', '').strip()
    nama = request.form.get('nama', '').strip()
    email = request.form.get('email', '').strip()
    no_hp = request.form.get('no_hp', '').strip()
    wilayah = request.form.get('wilayah', '').strip()
    jabatan = request.form.get('jabatan', 'Petugas Lapangan').strip()
    status = request.form.get('status', 'Aktif')
    password = request.form.get('password', '').strip()
    
    cursor.execute("SELECT id FROM petugas WHERE nip = ? AND id != ?", (nip, id))
    if cursor.fetchone():
        flash(f"NIP '{nip}' telah digunakan petugas lain!", "danger")
        conn.close()
        return redirect(url_for('petugas_index'))
        
    foto_file = request.files.get('foto_file')
    foto_url = request.form.get('foto_url', '').strip()
    new_foto = save_uploaded_photo(foto_file, nip) or (foto_url if foto_url else None)

    if new_foto:
        cursor.execute('''
            UPDATE petugas
            SET nip = ?, nama = ?, email = ?, no_hp = ?, wilayah = ?, jabatan = ?, status = ?, foto = ?
            WHERE id = ?
        ''', (nip, nama, email, no_hp, wilayah, jabatan, status, new_foto, id))
    else:
        cursor.execute('''
            UPDATE petugas
            SET nip = ?, nama = ?, email = ?, no_hp = ?, wilayah = ?, jabatan = ?, status = ?
            WHERE id = ?
        ''', (nip, nama, email, no_hp, wilayah, jabatan, status, id))
        
    if password:
        cursor.execute("UPDATE petugas SET password_hash = ? WHERE id = ?", (generate_password_hash(password), id))
        
    conn.commit()
    conn.close()
    flash(f"Data petugas '{nama}' berhasil diperbarui!", "success")
    return redirect(url_for('petugas_index'))

@app.route('/petugas/<int:id>/hapus', methods=['POST'])
def petugas_hapus(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nama FROM petugas WHERE id = ?", (id,))
    p = cursor.fetchone()
    if p:
        nama = p['nama']
        cursor.execute("DELETE FROM petugas WHERE id = ?", (id,))
        conn.commit()
        flash(f"Data petugas '{nama}' berhasil dihapus.", "success")
    conn.close()
    return redirect(url_for('petugas_index'))

@app.route('/petugas/<int:id>')
def petugas_detail(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM petugas WHERE id = ?", (id,))
    petugas = cursor.fetchone()
    if not petugas:
        conn.close()
        flash("Petugas tidak ditemukan!", "danger")
        return redirect(url_for('petugas_index'))
        
    # Survei yang ditugaskan ke petugas ini
    cursor.execute('''
        SELECT s.*, sp.peran, sp.target_individu,
               (SELECT COUNT(*) FROM responden WHERE survei_id = s.id AND petugas_id = ?) as respons_petugas
        FROM survei_petugas sp
        JOIN survei s ON sp.survei_id = s.id
        WHERE sp.petugas_id = ?
        ORDER BY s.id DESC
    ''', (id, id))
    assigned_surveys = cursor.fetchall()
    
    # Riwayat responden yang diinput oleh petugas ini
    cursor.execute('''
        SELECT r.*, s.judul as judul_survei, s.kode_survei
        FROM responden r
        JOIN survei s ON r.survei_id = s.id
        WHERE r.petugas_id = ?
        ORDER BY r.waktu_selesai DESC
        LIMIT 20
    ''', (id,))
    input_history = cursor.fetchall()
    
    # Total statistik
    cursor.execute("SELECT COUNT(*) FROM responden WHERE petugas_id = ?", (id,))
    total_respon_diinput = cursor.fetchone()[0]
    
    conn.close()
    return render_template(
        'petugas/detail.html',
        petugas=petugas,
        assigned_surveys=assigned_surveys,
        input_history=input_history,
        total_respon_diinput=total_respon_diinput
    )

# ==========================================
# 8. MASTER SEMUA RESPONS
# ==========================================
@app.route('/respons')
def respons_index():
    conn = get_db()
    cursor = conn.cursor()
    
    filter_survei = request.args.get('survei_id')
    filter_petugas = request.args.get('petugas_id')
    filter_q = request.args.get('q', '').strip()
    
    query = '''
        SELECT r.*, s.judul as judul_survei, s.kode_survei, p.nama as nama_petugas
        FROM responden r
        JOIN survei s ON r.survei_id = s.id
        LEFT JOIN petugas p ON r.petugas_id = p.id
        WHERE 1=1
    '''
    params = []
    if filter_survei:
        query += " AND r.survei_id = ?"
        params.append(filter_survei)
    if filter_petugas:
        if filter_petugas == 'mandiri':
            query += " AND r.petugas_id IS NULL"
        else:
            query += " AND r.petugas_id = ?"
            params.append(filter_petugas)
    if filter_q:
        query += " AND (r.nama_responden LIKE ? OR r.alamat_wilayah LIKE ? OR r.kontak_responden LIKE ?)"
        wildcard = f"%{filter_q}%"
        params.extend([wildcard, wildcard, wildcard])
        
    query += " ORDER BY r.waktu_selesai DESC LIMIT 100"
    cursor.execute(query, params)
    responses = cursor.fetchall()
    
    # Pilihan survei & petugas untuk filter
    cursor.execute("SELECT id, judul, kode_survei FROM survei ORDER BY judul ASC")
    all_survei = cursor.fetchall()
    
    cursor.execute("SELECT id, nama FROM petugas ORDER BY nama ASC")
    all_petugas = cursor.fetchall()
    
    conn.close()
    return render_template('responses/index.html', responses=responses, all_survei=all_survei, all_petugas=all_petugas, filter_survei=filter_survei, filter_petugas=filter_petugas, filter_q=filter_q)

@app.route('/respons/<int:id>/hapus', methods=['POST'])
def respons_hapus(id):
    if session.get('admin_level') != 'super_admin':
        flash("Akses ditolak: Hanya Super Admin yang berwenang menghapus lembar data responden.", "danger")
        return redirect(request.referrer or url_for('respons_index'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM responden WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    log_activity("Hapus Respon", f"Super Admin menghapus data responden ID #{id}")
    flash("Data responden berhasil dihapus.", "success")
    return redirect(request.referrer or url_for('respons_index'))

# ==========================================
# 9. PORTAL LEVEL OPERATOR / ENUMERATOR
# ==========================================
@app.route('/operator')
def operator_home():
    return redirect(url_for('operator_tugas'))

@app.route('/operator/switch/<int:id>')
def operator_switch(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM petugas WHERE id = ?", (id,))
    p = cursor.fetchone()
    conn.close()
    if p:
        session['operator_id'] = id
        flash(f"Beralih akun ke petugas: {p['nama']}", "info")
    return redirect(url_for('operator_tugas'))

@app.route('/operator/tugas')
def operator_tugas():
    current_op, all_active = get_current_operator()
    if not current_op:
        flash("Belum ada data petugas aktif di sistem.", "warning")
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, sp.peran, sp.target_individu,
               (SELECT COUNT(*) FROM responden WHERE survei_id = s.id AND petugas_id = ?) as realisasi_sampel,
               (SELECT COUNT(*) FROM responden WHERE survei_id = s.id) as total_masuk_survei
        FROM survei_petugas sp
        JOIN survei s ON sp.survei_id = s.id
        WHERE sp.petugas_id = ?
        ORDER BY s.id DESC
    ''', (current_op['id'], current_op['id']))
    
    tasks = []
    total_target = 0
    total_realisasi = 0
    
    for row in cursor.fetchall():
        t = dict(row)
        target_ind = t['target_individu'] or 25
        realisasi = t['realisasi_sampel'] or 0
        t['sisa_sampel'] = max(0, target_ind - realisasi)
        t['persen_sampel'] = min(100, round((realisasi / target_ind) * 100, 1))
        
        # Ambil riwayat responden yang diinput petugas ini untuk survei ini
        cursor.execute('''
            SELECT id, nama_responden, usia, jenis_kelamin, alamat_wilayah, waktu_selesai
            FROM responden
            WHERE survei_id = ? AND petugas_id = ?
            ORDER BY waktu_selesai DESC LIMIT 20
        ''', (t['id'], current_op['id']))
        t['my_responses'] = [dict(r) for r in cursor.fetchall()]
        
        total_target += target_ind
        total_realisasi += realisasi
        tasks.append(t)
        
    sisa_total = max(0, total_target - total_realisasi)
    conn.close()
    
    return render_template(
        'operator/tugas.html',
        current_operator=current_op,
        all_active_petugas=all_active,
        tasks=tasks,
        total_target_sampel=total_target,
        total_realisasi_sampel=total_realisasi,
        sisa_target_sampel=sisa_total
    )

@app.route('/operator/profil', methods=['GET', 'POST'])
def operator_profil():
    current_op, all_active = get_current_operator()
    if not current_op:
        flash("Petugas tidak ditemukan!", "danger")
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        email = request.form.get('email', '').strip()
        wilayah = request.form.get('wilayah', '').strip()
        foto_url = request.form.get('foto_url', '').strip()
        foto_file = request.files.get('foto_file')
        
        new_foto = save_uploaded_photo(foto_file, current_op['nip']) or (foto_url if foto_url else None)
        
        if new_foto:
            cursor.execute('''
                UPDATE petugas
                SET nama = ?, no_hp = ?, email = ?, wilayah = ?, foto = ?
                WHERE id = ?
            ''', (nama, no_hp, email, wilayah, new_foto, current_op['id']))
        else:
            cursor.execute('''
                UPDATE petugas
                SET nama = ?, no_hp = ?, email = ?, wilayah = ?
                WHERE id = ?
            ''', (nama, no_hp, email, wilayah, current_op['id']))
            
        password_baru = request.form.get('password_baru', '').strip()
        if password_baru:
            cursor.execute("UPDATE petugas SET password_hash = ? WHERE id = ?", (generate_password_hash(password_baru), current_op['id']))
            
        conn.commit()
        conn.close()
        
        # Perbarui nama di sesi jika berubah
        session['user_name'] = nama
        flash("Profil dan foto petugas berhasil diperbarui!", "success")
        return redirect(url_for('operator_profil'))
        
    # Statistik kumulatif
    cursor.execute('''
        SELECT COUNT(DISTINCT sp.survei_id) as total_survei,
               COALESCE(SUM(sp.target_individu), 0) as total_target,
               (SELECT COUNT(*) FROM responden WHERE petugas_id = ?) as total_realisasi
        FROM survei_petugas sp
        WHERE sp.petugas_id = ?
    ''', (current_op['id'], current_op['id']))
    stat = cursor.fetchone()
    total_survei = stat['total_survei'] if stat else 0
    total_target = stat['total_target'] if stat else 0
    total_realisasi = stat['total_realisasi'] if stat else 0
    persen = min(100, round((total_realisasi / (total_target or 1)) * 100, 1))
    
    conn.close()
    return render_template(
        'operator/profil.html',
        current_operator=current_op,
        all_active_petugas=all_active,
        total_survei=total_survei,
        total_target_sampel=total_target,
        total_realisasi=total_realisasi,
        persen_kumulatif=persen
    )

@app.route('/operator/survei/<int:survei_id>/isi', methods=['GET', 'POST'])
def operator_survei_isi(survei_id):
    current_op, all_active = get_current_operator()
    if not current_op:
        flash("Petugas tidak aktif.", "warning")
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM survei WHERE id = ?", (survei_id,))
    survei = cursor.fetchone()
    if not survei:
        conn.close()
        abort(404)
        
    if survei['status'] != 'Aktif':
        conn.close()
        flash("Survei ini sedang tidak aktif/ditutup.", "warning")
        return redirect(url_for('operator_tugas'))
        
    # Ambil data penugasan
    cursor.execute("SELECT * FROM survei_petugas WHERE survei_id = ? AND petugas_id = ?", (survei_id, current_op['id']))
    penugasan_row = cursor.fetchone()
    if not penugasan_row:
        cursor.execute("INSERT INTO survei_petugas (survei_id, petugas_id, peran, target_individu) VALUES (?, ?, 'Petugas Lapangan', 25)", (survei_id, current_op['id']))
        conn.commit()
        penugasan = {'peran': 'Petugas Lapangan', 'target_individu': 25}
    else:
        penugasan = dict(penugasan_row)
        
    # Realisasi count
    cursor.execute("SELECT COUNT(*) FROM responden WHERE survei_id = ? AND petugas_id = ?", (survei_id, current_op['id']))
    realisasi_count = cursor.fetchone()[0]
    target_ind = penugasan.get('target_individu', 25) or 25
    persen_sampel = min(100, round((realisasi_count / target_ind) * 100, 1))
    
    # Pertanyaan
    cursor.execute("SELECT * FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC, id ASC", (survei_id,))
    questions = []
    for q in cursor.fetchall():
        item = dict(q)
        item['pilihan_opsi_list'] = json.loads(item['pilihan_opsi']) if item['pilihan_opsi'] else []
        questions.append(item)
        
    if request.method == 'POST':
        nama_responden = request.form.get('nama_responden', '').strip() or 'Anonim'
        kontak_responden = request.form.get('kontak_responden', '').strip()
        usia = request.form.get('usia')
        usia = int(usia) if usia and usia.isdigit() else None
        jenis_kelamin = request.form.get('jenis_kelamin', 'Rahasia')
        pendidikan_terakhir = request.form.get('pendidikan_terakhir', '').strip() or None
        titik_koordinat = request.form.get('titik_koordinat', '').strip() or request.form.get('alamat_wilayah', '').strip() or None
        alamat_wilayah = request.form.get('alamat_wilayah', '').strip() or titik_koordinat
        
        cursor.execute('''
            INSERT INTO responden (survei_id, petugas_id, nama_responden, kontak_responden, usia, jenis_kelamin, pendidikan_terakhir, titik_koordinat, alamat_wilayah, ip_address, waktu_selesai)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (survei_id, current_op['id'], nama_responden, kontak_responden, usia, jenis_kelamin, pendidikan_terakhir, titik_koordinat, alamat_wilayah, request.remote_addr or '127.0.0.1'))
        resp_id = cursor.lastrowid
        
        for q in questions:
            q_id = q['id']
            q_tipe = q['tipe_pertanyaan']
            field_name = f"q_{q_id}"
            
            jawaban_teks = None
            jawaban_angka = None
            
            if q_tipe == 'checkbox':
                checked = request.form.getlist(f"{field_name}[]")
                if checked:
                    jawaban_teks = json.dumps(checked, ensure_ascii=False)
            elif q_tipe in ['rating', 'number']:
                val = request.form.get(field_name)
                if val is not None and val != '':
                    jawaban_teks = str(val).strip()
                    try:
                        jawaban_angka = float(val)
                    except ValueError:
                        jawaban_angka = None
            else:
                val = request.form.get(field_name)
                if val is not None and val != '':
                    jawaban_teks = str(val).strip()
                    
            cursor.execute("INSERT INTO jawaban (responden_id, pertanyaan_id, jawaban_teks, jawaban_angka) VALUES (?, ?, ?, ?)",
                           (resp_id, q_id, jawaban_teks, jawaban_angka))
                           
        conn.commit()
        conn.close()
        return redirect(url_for('operator_survei_sukses', survei_id=survei_id, resp_id=resp_id))
        
    conn.close()
    return render_template(
        'operator/isi.html',
        survei=dict(survei),
        penugasan=penugasan,
        current_operator=current_op,
        all_active_petugas=all_active,
        realisasi_count=realisasi_count,
        persen_sampel=persen_sampel,
        questions=questions
    )

@app.route('/operator/survei/<int:survei_id>/sukses')
def operator_survei_sukses(survei_id):
    current_op, all_active = get_current_operator()
    if not current_op:
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survei WHERE id = ?", (survei_id,))
    survei = cursor.fetchone()
    
    cursor.execute("SELECT * FROM survei_petugas WHERE survei_id = ? AND petugas_id = ?", (survei_id, current_op['id']))
    penugasan_row = cursor.fetchone()
    penugasan = dict(penugasan_row) if penugasan_row else {'target_individu': 25}
    
    cursor.execute("SELECT COUNT(*) FROM responden WHERE survei_id = ? AND petugas_id = ?", (survei_id, current_op['id']))
    realisasi_count = cursor.fetchone()[0]
    target_ind = penugasan.get('target_individu', 25) or 25
    sisa_sampel = max(0, target_ind - realisasi_count)
    persen_sampel = min(100, round((realisasi_count / target_ind) * 100, 1))
    
    resp_id = request.args.get('resp_id')
    conn.close()
    
    return render_template(
        'operator/sukses.html',
        survei=dict(survei),
        penugasan=penugasan,
        current_operator=current_op,
        all_active_petugas=all_active,
        realisasi_count=realisasi_count,
        sisa_sampel=sisa_sampel,
        persen_sampel=persen_sampel,
        resp_id=resp_id
    )

# ==========================================
# 10. MODUL MANAJEMEN PROFIL & HAK AKSES ADMIN
# ==========================================

@app.route('/admin/profil', methods=['GET', 'POST'])
def admin_profil():
    if session.get('user_role') != 'admin':
        flash("Hanya akun Administrator yang dapat mengakses halaman ini.", "danger")
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    cursor = conn.cursor()
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            nama = request.form.get('nama', '').strip()
            email = request.form.get('email', '').strip()
            no_hp = request.form.get('no_hp', '').strip()
            foto_type = request.form.get('foto_type', 'keep')
            
            if not nama or not email:
                flash("Nama lengkap dan email tidak boleh kosong.", "danger")
                conn.close()
                return redirect(url_for('admin_profil'))
                
            # Cek duplikasi email dengan user lain
            cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
            if cursor.fetchone():
                flash("Email tersebut sudah digunakan oleh akun lain.", "danger")
                conn.close()
                return redirect(url_for('admin_profil'))
                
            new_foto = None
            if foto_type == 'upload' and 'foto_file' in request.files:
                uploaded = save_uploaded_admin_photo(request.files['foto_file'], session.get('username'))
                if uploaded:
                    new_foto = uploaded
            elif foto_type == 'url':
                url_val = request.form.get('foto_url', '').strip()
                if url_val:
                    new_foto = url_val
            elif foto_type == 'remove':
                new_foto = ''
                
            if new_foto is not None:
                cursor.execute('''
                    UPDATE users 
                    SET nama = ?, email = ?, no_hp = ?, foto = ?
                    WHERE id = ?
                ''', (nama, email, no_hp, new_foto if new_foto != '' else None, user_id))
                session['user_foto'] = new_foto if new_foto != '' else None
            else:
                cursor.execute('''
                    UPDATE users 
                    SET nama = ?, email = ?, no_hp = ?
                    WHERE id = ?
                ''', (nama, email, no_hp, user_id))
                
            conn.commit()
            session['user_name'] = nama
            session['email'] = email
            session['user_hp'] = no_hp
            
            log_activity("Update Profil Pribadi", f"Admin '{session.get('username')}' memperbarui identitas dirinya")
            flash("Profil Anda berhasil diperbarui dengan sukses!", "success")
            conn.close()
            return redirect(url_for('admin_profil'))
            
        elif action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')
            
            cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
            user_row = cursor.fetchone()
            
            if not user_row or not check_password_hash(user_row['password_hash'], current_pwd):
                flash("Kata sandi saat ini yang Anda masukkan salah!", "danger")
                conn.close()
                return redirect(url_for('admin_profil'))
                
            if len(new_pwd) < 6:
                flash("Kata sandi baru minimal harus 6 karakter.", "danger")
                conn.close()
                return redirect(url_for('admin_profil'))
                
            if new_pwd != confirm_pwd:
                flash("Konfirmasi kata sandi baru tidak cocok. Silakan ulangi.", "danger")
                conn.close()
                return redirect(url_for('admin_profil'))
                
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_pwd), user_id))
            conn.commit()
            
            log_activity("Ganti Kata Sandi", f"Admin '{session.get('username')}' memperbarui kata sandi pribadinya")
            flash("Kata sandi Anda berhasil diperbarui dengan aman!", "success")
            conn.close()
            return redirect(url_for('admin_profil'))
            
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    # Statistik untuk widget profil
    cursor.execute("SELECT COUNT(*) FROM survei")
    total_survei = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM petugas WHERE status = 'Aktif'")
    total_petugas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM responden")
    total_respon = cursor.fetchone()[0]
    
    conn.close()
    return render_template(
        'admin/profil.html',
        admin=user,
        total_survei=total_survei,
        total_petugas=total_petugas,
        total_respon=total_respon
    )

@app.route('/admin/users', methods=['GET', 'POST'])
@super_admin_required
def admin_users():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        nama = request.form.get('nama', '').strip()
        email = request.form.get('email', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        role = request.form.get('role', 'admin').strip()
        status = request.form.get('status', 'Aktif').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not nama or not password:
            flash("Username, nama lengkap, dan kata sandi wajib diisi.", "danger")
            conn.close()
            return redirect(url_for('admin_users'))
            
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            flash(f"Username '{username}' atau email '{email}' sudah terdaftar dalam sistem.", "danger")
            conn.close()
            return redirect(url_for('admin_users'))
            
        if role not in ('super_admin', 'admin'):
            role = 'admin'
            
        pwd_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, nama, email, no_hp, role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, pwd_hash, nama, email, no_hp, role, status))
        conn.commit()
        
        role_label = 'Super Admin' if role == 'super_admin' else 'Admin Staf'
        log_activity("Tambah Admin", f"Super Admin mendaftarkan akun baru: {nama} ({username}) dengan peran {role_label}")
        flash(f"Akun baru '{nama}' berhasil didaftarkan sebagai {role_label}!", "success")
        conn.close()
        return redirect(url_for('admin_users'))
        
    cursor.execute("SELECT * FROM users ORDER BY CASE WHEN role = 'super_admin' THEN 1 ELSE 2 END, id ASC")
    users = cursor.fetchall()
    
    total_admin = len(users)
    total_super = sum(1 for u in users if u['role'] == 'super_admin')
    total_staf = sum(1 for u in users if u['role'] == 'admin')
    total_aktif = sum(1 for u in users if u['status'] == 'Aktif')
    
    conn.close()
    return render_template(
        'admin/users.html',
        users=users,
        total_admin=total_admin,
        total_super=total_super,
        total_staf=total_staf,
        total_aktif=total_aktif
    )

@app.route('/admin/users/<int:id>/edit', methods=['POST'])
@super_admin_required
def admin_users_edit(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        flash("Pengguna admin tidak ditemukan.", "danger")
        return redirect(url_for('admin_users'))
        
    nama = request.form.get('nama', '').strip()
    email = request.form.get('email', '').strip()
    no_hp = request.form.get('no_hp', '').strip()
    role = request.form.get('role', target['role']).strip()
    status = request.form.get('status', target['status']).strip()
    
    # Proteksi: Super admin yang sedang login tidak dapat men-downgrade atau menonaktifkan dirinya sendiri
    if id == session.get('user_id'):
        role = 'super_admin'
        status = 'Aktif'
        
    # Cek keunikan email
    cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, id))
    if cursor.fetchone():
        flash("Email sudah digunakan oleh akun admin lainnya.", "danger")
        conn.close()
        return redirect(url_for('admin_users'))
        
    cursor.execute('''
        UPDATE users 
        SET nama = ?, email = ?, no_hp = ?, role = ?, status = ?
        WHERE id = ?
    ''', (nama, email, no_hp, role, status, id))
    conn.commit()
    
    log_activity("Edit Admin", f"Super Admin memperbarui data akun {target['username']} (ID #{id})")
    flash(f"Data akun '{nama}' berhasil diperbarui.", "success")
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:id>/reset-password', methods=['POST'])
@super_admin_required
def admin_users_reset_password(id):
    new_pwd = request.form.get('new_password', '').strip()
    if not new_pwd or len(new_pwd) < 6:
        flash("Kata sandi baru minimal harus 6 karakter.", "danger")
        return redirect(url_for('admin_users'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, nama FROM users WHERE id = ?", (id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        flash("Akun admin tidak ditemukan.", "danger")
        return redirect(url_for('admin_users'))
        
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_pwd), id))
    conn.commit()
    conn.close()
    
    log_activity("Reset Password Admin", f"Super Admin mereset password akun '{target['username']}' (ID #{id})")
    flash(f"Kata sandi untuk akun '{target['nama']}' berhasil direset.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:id>/hapus', methods=['POST'])
@super_admin_required
def admin_users_hapus(id):
    if id == session.get('user_id'):
        flash("Aksi ditolak: Anda tidak dapat menghapus akun Anda sendiri!", "danger")
        return redirect(url_for('admin_users'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        flash("Akun admin tidak ditemukan.", "danger")
        return redirect(url_for('admin_users'))
        
    # Pastikan tidak menghapus Super Admin terakhir
    if target['role'] == 'super_admin':
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin' AND status = 'Aktif'")
        count_super = cursor.fetchone()[0]
        if count_super <= 1:
            conn.close()
            flash("Aksi ditolak: Sistem harus memiliki minimal 1 Super Admin aktif!", "danger")
            return redirect(url_for('admin_users'))
            
    cursor.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    log_activity("Hapus Admin", f"Super Admin menghapus akun '{target['username']}' (ID #{id})")
    flash(f"Akun admin '{target['nama']}' ({target['username']}) berhasil dihapus.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/pengaturan', methods=['GET', 'POST'])
@super_admin_required
def admin_pengaturan():
    conn = get_db()
    cursor = conn.cursor()
    
    setting_keys = ['nama_aplikasi', 'nama_instansi', 'email_resmi', 'telepon_resmi', 'alamat_kantor', 'zona_waktu']
    
    if request.method == 'POST':
        for key in setting_keys:
            val = request.form.get(key, '').strip()
            cursor.execute("INSERT INTO pengaturan (kunci, nilai, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(kunci) DO UPDATE SET nilai = excluded.nilai, updated_at = CURRENT_TIMESTAMP", (key, val))
        conn.commit()
        
        log_activity("Pengaturan Sistem", "Super Admin memperbarui konfigurasi parameter global sistem")
        flash("Pengaturan sistem dan identitas instansi berhasil disimpan!", "success")
        conn.close()
        return redirect(url_for('admin_pengaturan'))
        
    cursor.execute("SELECT kunci, nilai, kategori FROM pengaturan")
    rows = cursor.fetchall()
    settings = {r['kunci']: r['nilai'] for r in rows}
    conn.close()
    return render_template('admin/pengaturan.html', settings=settings)

@app.route('/admin/logs')
@super_admin_required
def admin_logs():
    conn = get_db()
    cursor = conn.cursor()
    
    filter_role = request.args.get('role', '').strip()
    filter_q = request.args.get('q', '').strip()
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if filter_role:
        query += " AND role = ?"
        params.append(filter_role)
    if filter_q:
        query += " AND (aksi LIKE ? OR rincian LIKE ? OR user_name LIKE ?)"
        term = f"%{filter_q}%"
        params.extend([term, term, term])
        
    query += " ORDER BY id DESC LIMIT 150"
    
    cursor.execute(query, params)
    logs = cursor.fetchall()
    
    # Hitung statistik singkat
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    total_logs = cursor.fetchone()[0]
    
    conn.close()
    return render_template('admin/logs.html', logs=logs, total_logs=total_logs, filter_role=filter_role, filter_q=filter_q)

# ==========================================
# 11. MODUL BACKUP DATA LENGKAP & PEMULIHAN ASET (SUPER ADMIN)
# ==========================================

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def build_full_backup_zip():
    """Menghasilkan file zip lengkap berisi database, dump sql, aset upload, dan manifest sistem"""
    buf = io.BytesIO()
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sisurvei.db')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM survei")
    total_survei = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pertanyaan")
    total_pertanyaan = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM petugas")
    total_petugas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM responden")
    total_responden = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jawaban")
    total_jawaban = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # Generate SQL dump
    sql_dump_str = '\n'.join(conn.iterdump())
    conn.close()
    
    manifest = {
        'nama_aplikasi': 'SiSurvei - Sistem Informasi & Manajemen Survei Terpadu',
        'versi_backup': '2.6 PRO',
        'waktu_backup': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dibuat_oleh': f"{session.get('user_name', 'Super Admin')} (@{session.get('username', 'admin')})",
        'ringkasan_data': {
            'total_kegiatan_survei': total_survei,
            'total_pertanyaan': total_pertanyaan,
            'total_petugas': total_petugas,
            'total_responden': total_responden,
            'total_jawaban_kuisioner': total_jawaban,
            'total_akun_admin': total_users
        }
    }
    
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Database binary
        if os.path.exists(db_file_path):
            zf.write(db_file_path, arcname='database/sisurvei.db')
            
        # 2. SQL Dump script
        zf.writestr('database/sisurvei_dump.sql', sql_dump_str)
        
        # 3. Manifest info
        zf.writestr('backup_manifest.json', json.dumps(manifest, indent=2))
        
        # 4. Aset Uploads (Foto Petugas & Avatar Admin)
        static_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        if os.path.exists(static_uploads):
            for root, dirs, files in os.walk(static_uploads):
                for f in files:
                    file_full = os.path.join(root, f)
                    rel_path = os.path.relpath(file_full, os.path.dirname(os.path.abspath(__file__)))
                    zf.write(file_full, arcname=rel_path)
                    
    buf.seek(0)
    return buf, timestamp_str

def build_master_excel_backup():
    """Menghasilkan master workbook Excel berisikan seluruh tabel aset SiSurvei dengan multi-sheet berformat rapi"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    conn = get_db()
    cursor = conn.cursor()

    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    def style_sheet(ws, title, columns, rows_data):
        ws.title = title
        ws.views.sheetView[0].showGridLines = True
        
        ws.append(columns)
        for col_idx in range(1, len(columns) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = thin_border
            ws.row_dimensions[1].height = 26

        for r_idx, r_data in enumerate(rows_data, start=2):
            ws.append(list(r_data))
            for c_idx in range(1, len(r_data) + 1):
                c_cell = ws.cell(row=r_idx, column=c_idx)
                c_cell.font = Font(name='Calibri', size=10)
                c_cell.border = thin_border
                c_cell.alignment = Alignment(vertical='center')

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(50, max(max_len + 4, 12))

    # Sheet 1: Kegiatan Survei
    cursor.execute("SELECT id, kode_survei, judul, kategori, target_responden, tanggal_mulai, tanggal_selesai, status, is_public, created_at FROM survei ORDER BY id ASC")
    style_sheet(wb.create_sheet(), 'Kegiatan Survei', 
        ['ID', 'Kode Survei', 'Judul Survei', 'Kategori', 'Target Responden', 'Tgl Mulai', 'Tgl Selesai', 'Status', 'Publik (1/0)', 'Dibuat Pada'],
        cursor.fetchall()
    )

    # Sheet 2: Instrumen Pertanyaan
    cursor.execute('''
        SELECT p.id, p.survei_id, s.judul, p.urutan, p.teks_pertanyaan, p.tipe_pertanyaan, p.pilihan_opsi, p.is_required, p.rating_max
        FROM pertanyaan p
        LEFT JOIN survei s ON p.survei_id = s.id
        ORDER BY p.survei_id ASC, p.urutan ASC
    ''')
    style_sheet(wb.create_sheet(), 'Instrumen Pertanyaan',
        ['ID', 'Survei ID', 'Judul Survei', 'No. Urut', 'Teks Pertanyaan', 'Tipe Pertanyaan', 'Pilihan Opsi', 'Wajib Diisi (1/0)', 'Rating Maks'],
        cursor.fetchall()
    )

    # Sheet 3: Data Petugas
    cursor.execute("SELECT id, nip, nama, email, no_hp, wilayah, jabatan, status, foto, created_at FROM petugas ORDER BY id ASC")
    style_sheet(wb.create_sheet(), 'Data Petugas',
        ['ID', 'NIP', 'Nama Lengkap', 'Email', 'No HP/WA', 'Wilayah Penugasan', 'Jabatan', 'Status', 'Foto Path', 'Terdaftar Pada'],
        cursor.fetchall()
    )

    # Sheet 4: Data Responden
    cursor.execute('''
        SELECT r.id, r.survei_id, s.judul, r.petugas_id, COALESCE(p.nama, 'Mandiri / Publik'),
               r.nama_responden, r.kontak_responden, r.usia, r.jenis_kelamin, r.pendidikan_terakhir,
               r.alamat_wilayah, r.titik_koordinat, r.waktu_selesai
        FROM responden r
        LEFT JOIN survei s ON r.survei_id = s.id
        LEFT JOIN petugas p ON r.petugas_id = p.id
        ORDER BY r.id ASC
    ''')
    style_sheet(wb.create_sheet(), 'Data Responden',
        ['ID Responden', 'Survei ID', 'Judul Survei', 'Petugas ID', 'Enumerator', 'Nama Responden', 'No Kontak', 'Usia', 'Jenis Kelamin', 'Pendidikan Terakhir', 'Alamat/Wilayah', 'Titik Koordinat GPS', 'Waktu Submit'],
        cursor.fetchall()
    )

    # Sheet 5: Seluruh Jawaban Responden
    cursor.execute('''
        SELECT j.id, j.responden_id, r.nama_responden, j.pertanyaan_id, p.teks_pertanyaan,
               COALESCE(j.jawaban_teks, CAST(j.jawaban_angka AS TEXT))
        FROM jawaban j
        LEFT JOIN responden r ON j.responden_id = r.id
        LEFT JOIN pertanyaan p ON j.pertanyaan_id = p.id
        ORDER BY j.responden_id ASC, j.pertanyaan_id ASC
    ''')
    style_sheet(wb.create_sheet(), 'Jawaban Responden',
        ['ID Jawaban', 'Responden ID', 'Nama Responden', 'Pertanyaan ID', 'Teks Pertanyaan', 'Jawaban Tercatat'],
        cursor.fetchall()
    )

    # Sheet 6: Pengaturan & Identitas Instansi
    cursor.execute("SELECT kunci, nilai, kategori, updated_at FROM pengaturan ORDER BY kategori ASC, kunci ASC")
    style_sheet(wb.create_sheet(), 'Pengaturan Sistem',
        ['Kunci Parameter', 'Nilai / Konfigurasi', 'Kategori', 'Terakhir Diperbarui'],
        cursor.fetchall()
    )

    # Sheet 7: Pengguna Admin
    cursor.execute("SELECT id, username, nama, email, no_hp, role, status, created_at FROM users ORDER BY id ASC")
    style_sheet(wb.create_sheet(), 'Akun Admin',
        ['ID', 'Username', 'Nama Lengkap', 'Email', 'No HP/WA', 'Peran (Role)', 'Status', 'Dibuat Pada'],
        cursor.fetchall()
    )

    conn.close()

    excel_buf = io.BytesIO()
    wb.save(excel_buf)
    excel_buf.seek(0)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    return excel_buf, timestamp_str

@app.route('/admin/backup')
@super_admin_required
def admin_backup():
    conn = get_db()
    cursor = conn.cursor()
    
    # Statistik sistem
    cursor.execute("SELECT COUNT(*) FROM survei")
    total_survei = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM pertanyaan")
    total_pertanyaan = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM petugas")
    total_petugas = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM responden")
    total_responden = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jawaban")
    total_jawaban = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()
    
    # Ukuran file database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sisurvei.db')
    db_size_kb = round(os.path.getsize(db_path) / 1024, 1) if os.path.exists(db_path) else 0
    
    # Hitung jumlah file upload
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    total_uploads = 0
    uploads_size_kb = 0
    if os.path.exists(uploads_dir):
        for root, dirs, files in os.walk(uploads_dir):
            total_uploads += len(files)
            for f in files:
                uploads_size_kb += os.path.getsize(os.path.join(root, f)) / 1024
    uploads_size_kb = round(uploads_size_kb, 1)
    
    # Daftar file backup yang ada di server
    backup_files = []
    if os.path.exists(BACKUP_DIR):
        for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
            fpath = os.path.join(BACKUP_DIR, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                backup_files.append({
                    'filename': fname,
                    'size_kb': round(stat.st_size / 1024, 1),
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_zip': fname.endswith('.zip'),
                    'is_db': fname.endswith('.db')
                })
                
    return render_template(
        'admin/backup.html',
        total_survei=total_survei,
        total_pertanyaan=total_pertanyaan,
        total_petugas=total_petugas,
        total_responden=total_responden,
        total_jawaban=total_jawaban,
        total_users=total_users,
        total_uploads=total_uploads,
        db_size_kb=db_size_kb,
        uploads_size_kb=uploads_size_kb,
        backup_files=backup_files
    )

@app.route('/admin/backup/download/<string:fmt>')
@super_admin_required
def admin_backup_download(fmt):
    if fmt == 'zip':
        buf, timestamp_str = build_full_backup_zip()
        filename = f"SiSurvei_Full_Backup_{timestamp_str}.zip"
        log_activity("Unduh Backup ZIP", f"Super Admin mengunduh paket arsip lengkap sistem (.zip)")
        return send_file(
            buf,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    elif fmt == 'excel':
        buf, timestamp_str = build_master_excel_backup()
        filename = f"SiSurvei_Master_Data_{timestamp_str}.xlsx"
        log_activity("Unduh Backup Excel", f"Super Admin mengunduh rekapitulasi data master Excel (.xlsx)")
        return send_file(
            buf,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    elif fmt == 'db':
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sisurvei.db')
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sisurvei_raw_{timestamp_str}.db"
        log_activity("Unduh Backup DB", f"Super Admin mengunduh salinan database mentah SQLite (.db)")
        return send_file(
            db_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    elif fmt == 'sql':
        conn = get_db()
        sql_dump = '\n'.join(conn.iterdump())
        conn.close()
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        buf = io.BytesIO(sql_dump.encode('utf-8'))
        filename = f"sisurvei_dump_{timestamp_str}.sql"
        log_activity("Unduh Backup SQL", f"Super Admin mengunduh script ekspor SQL dump (.sql)")
        return send_file(
            buf,
            mimetype='application/sql',
            as_attachment=True,
            download_name=filename
        )
    else:
        flash("Format unduhan backup tidak valid.", "danger")
        return redirect(url_for('admin_backup'))

@app.route('/admin/backup/create', methods=['POST'])
@super_admin_required
def admin_backup_create_snapshot():
    buf, timestamp_str = build_full_backup_zip()
    filename = f"snapshot_sisurvei_{timestamp_str}.zip"
    filepath = os.path.join(BACKUP_DIR, filename)
    
    with open(filepath, 'wb') as f:
        f.write(buf.getbuffer())
        
    log_activity("Buat Snapshot Backup", f"Super Admin membuat snapshot arsip baru di server: {filename}")
    flash(f"Snapshot cadangan lengkap berhasil disimpan di server: '{filename}'.", "success")
    return redirect(url_for('admin_backup'))

@app.route('/admin/backup/file/<string:filename>')
@super_admin_required
def admin_backup_download_file(filename):
    clean_name = secure_filename(filename)
    filepath = os.path.join(BACKUP_DIR, clean_name)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=clean_name)
    flash("File backup tidak ditemukan di server.", "danger")
    return redirect(url_for('admin_backup'))

@app.route('/admin/backup/delete/<string:filename>', methods=['POST'])
@super_admin_required
def admin_backup_delete_file(filename):
    clean_name = secure_filename(filename)
    filepath = os.path.join(BACKUP_DIR, clean_name)
    if os.path.exists(filepath):
        os.remove(filepath)
        log_activity("Hapus File Backup", f"Super Admin menghapus arsip cadangan: {clean_name}")
        flash(f"File arsip backup '{clean_name}' berhasil dihapus dari server.", "success")
    else:
        flash("File backup tidak ditemukan.", "danger")
    return redirect(url_for('admin_backup'))

@app.route('/admin/backup/restore', methods=['POST'])
@super_admin_required
def admin_backup_restore():
    if 'backup_file' not in request.files:
        flash("Tidak ada file cadangan yang dipilih.", "danger")
        return redirect(url_for('admin_backup'))
        
    file = request.files['backup_file']
    if not file or file.filename == '':
        flash("Silakan pilih file cadangan database (.db atau .sql).", "danger")
        return redirect(url_for('admin_backup'))
        
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    if ext not in ('db', 'sql'):
        flash("Format file pemulihan tidak didukung. Harap unggah file .db atau .sql.", "danger")
        return redirect(url_for('admin_backup'))
        
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sisurvei.db')
    emergency_snapshot = os.path.join(BACKUP_DIR, f"emergency_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    
    if os.path.exists(db_path):
        shutil.copy2(db_path, emergency_snapshot)
        
    try:
        if ext == 'db':
            file.save(db_path)
        elif ext == 'sql':
            sql_content = file.read().decode('utf-8', errors='ignore')
            conn = get_db()
            conn.executescript(sql_content)
            conn.commit()
            conn.close()
            
        log_activity("Restore Database", f"Super Admin memulihkan data sistem dari file: {filename}")
        flash(f"Basis data dan aset sistem berhasil dipulihkan dari '{filename}'. Cadangan pengaman pra-pemulihan otomatis tersimpan.", "success")
    except Exception as e:
        if os.path.exists(emergency_snapshot):
            shutil.copy2(emergency_snapshot, db_path)
        flash(f"Gagal memulihkan database: {str(e)}. Sistem telah dikembalikan ke kondisi sebelumnya.", "danger")
        
    return redirect(url_for('admin_backup'))



if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5005))
    local_ip = get_local_ip()
    print("================================================================")
    print(" SiSurvei Server Siap Melayani Survei Lapangan & Administrator")
    print(f" [PC] Akses Komputer Lokal : http://127.0.0.1:{port}")
    print(f" [HP] Akses HP Android     : http://{local_ip}:{port}")
    print("================================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
