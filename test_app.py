from app import app
from database import get_db, init_db
import json

def run_tests():
    init_db()
    client = app.test_client()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM survei ORDER BY id ASC LIMIT 1")
    s_id = c.fetchone()[0]
    
    c.execute("SELECT id FROM petugas ORDER BY id ASC LIMIT 1")
    p_id = c.fetchone()[0]
    
    c.execute("SELECT id FROM responden ORDER BY id ASC LIMIT 1")
    r_id = c.fetchone()[0]
    
    c.execute("SELECT id FROM pertanyaan WHERE survei_id = ? ORDER BY urutan ASC", (s_id,))
    pertanyaan_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    print("\n--- PHASE 1: TESTING ROUTE PROTECTION & PUBLIC ACCESS ---")
    
    print("[1] Testing GET / without login (Should redirect to /login)...")
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302, f"Expected 302, got {res.status_code}"
    assert '/login' in res.headers['Location']
    print("    -> Passed! Unauthenticated access redirected to /login.")

    print("[2] Testing GET /petugas without login (Should redirect to /login)...")
    res = client.get('/petugas', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.headers['Location']
    print("    -> Passed! Admin route protected.")

    print("[3] Testing GET /operator/tugas without login (Should redirect to /login)...")
    res = client.get('/operator/tugas', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.headers['Location']
    print("    -> Passed! Operator route protected.")

    print("[4] Testing GET /login (Login Page UI)...")
    res = client.get('/login')
    assert res.status_code == 200
    assert b"SiSurvei" in res.data
    assert b"Petugas / Enumerator" in res.data
    assert b"Administrator" in res.data
    assert b"1-Click Demo Login" in res.data
    print("    -> Passed! Login UI loads with dual role tabs.")

    print("[5] Testing GET /s/SRV-2026-001 (Public Respondent Form without login)...")
    res = client.get('/s/SRV-2026-001')
    assert res.status_code == 200
    assert b"Kuisioner" in res.data
    print("    -> Passed! Public respondent questionnaire accessible without login.")

    print("[6] Testing POST /s/SRV-2026-001 (Public Respondent Submission)...")
    post_data = {
        'nama_responden': 'Responden Tester Publik',
        'kontak_responden': '081234567890',
        'usia': '29',
        'jenis_kelamin': 'Laki-laki',
        'pendidikan_terakhir': 'Sarjana (S1)',
        'titik_koordinat': '-6.175392, 106.827153',
        'alamat_wilayah': 'Jakarta Pusat',
        'petugas_id': str(p_id),
    }
    for q_idx, qid in enumerate(pertanyaan_ids):
        if q_idx == 0:
            post_data[f'q_{qid}'] = 'Administrasi Kependudukan (KTP/KK/Akta)'
        elif q_idx in [1, 2, 3]:
            post_data[f'q_{qid}'] = '5'
        elif q_idx == 4:
            post_data[f'q_{qid}'] = 'Sesuai Tarif Resmi & Sangat Transparan'
        elif q_idx == 5:
            post_data[f'q_{qid}[]'] = ['Sistem Antrean Online & Notifikasi WA']
        elif q_idx == 6:
            post_data[f'q_{qid}'] = 'Aplikasi Mobile Resmi'
        elif q_idx == 7:
            post_data[f'q_{qid}'] = '15'
        else:
            post_data[f'q_{qid}'] = 'Pelayanan testing otomatis sangat memuaskan!'
            
    res = client.post('/s/SRV-2026-001', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Terima Kasih" in res.data
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT pendidikan_terakhir, titik_koordinat FROM responden WHERE nama_responden = 'Responden Tester Publik' ORDER BY id DESC LIMIT 1")
    row_p = c.fetchone()
    conn.close()
    assert row_p and row_p[0] == 'Sarjana (S1)', f"Expected 'Sarjana (S1)', got {row_p}"
    assert row_p[1] == '-6.175392, 106.827153', f"Expected '-6.175392, 106.827153', got {row_p[1]}"
    print("    -> Passed! Public respondent response submitted, pendidikan_terakhir and titik_koordinat persisted correctly.")

    print("\n--- PHASE 2: TESTING AUTHENTICATION (ADMIN & OPERATOR) ---")

    print("[7] Testing POST /login with Invalid Admin Credentials...")
    res = client.post('/login', data={'role': 'admin', 'identifier': 'admin', 'password': 'wrongpassword'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"salah" in res.data or b"tidak sesuai" in res.data
    print("    -> Passed! Invalid admin login rejected.")

    print("[8] Testing POST /login with Invalid Operator Credentials...")
    res = client.post('/login', data={'role': 'operator', 'identifier': 'PTG-001', 'password': 'wrongpassword'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"tidak sesuai" in res.data or b"salah" in res.data
    print("    -> Passed! Invalid operator login rejected.")

    print("[9] Testing POST /login with Valid Admin Credentials...")
    res = client.post('/login', data={'role': 'admin', 'identifier': 'admin', 'password': 'admin123'}, follow_redirects=False)
    assert res.status_code == 302
    assert res.headers['Location'] == '/' or res.headers['Location'].endswith('/')
    print("    -> Passed! Admin login succeeded, redirected to dashboard.")

    print("\n--- PHASE 3: TESTING ADMIN PRIVILEGES ---")

    print("[10] Testing GET / as Authenticated Admin...")
    res = client.get('/')
    assert res.status_code == 200
    assert b"Ringkasan Eksekutif" in res.data
    assert b"Administrator Utama" in res.data
    print("    -> Passed! Admin dashboard rendered with admin identity.")

    print("[11] Testing GET /survei as Authenticated Admin...")
    res = client.get('/survei')
    assert res.status_code == 200
    assert b"SRV-2026-001" in res.data
    print("    -> Passed! Survei list OK.")

    print(f"[12] Testing GET /survei/{s_id}/builder as Authenticated Admin...")
    res = client.get(f'/survei/{s_id}/builder')
    assert res.status_code == 200
    assert b"Perancang Kuisioner" in res.data
    print("    -> Passed! Builder page OK.")

    print(f"[13] Testing GET /survei/{s_id}/hasil as Authenticated Admin...")
    res = client.get(f'/survei/{s_id}/hasil')
    assert res.status_code == 200
    assert b"Visualisasi Analisis Hasil Kuisioner" in res.data
    print("    -> Passed! Results analytics OK.")

    print(f"[14] Testing GET /survei/{s_id}/export/excel and /export/csv as Authenticated Admin...")
    res = client.get(f'/survei/{s_id}/export/excel')
    assert res.status_code == 200
    assert "spreadsheetml" in res.content_type
    
    res_csv = client.get(f'/survei/{s_id}/export/csv')
    assert res_csv.status_code == 200
    assert "Pendidikan Terakhir" in res_csv.data.decode('utf-8')
    print("    -> Passed! Excel & CSV exports OK and include 'Pendidikan Terakhir'.")

    print("[15] Testing GET /petugas as Authenticated Admin...")
    res = client.get('/petugas')
    assert res.status_code == 200
    assert b"Budi Santoso" in res.data
    print("    -> Passed! Petugas list OK.")

    print("[16] Testing GET /respons as Authenticated Admin...")
    res = client.get('/respons')
    assert res.status_code == 200
    assert b"Repositori Data Responden" in res.data
    print("    -> Passed! Responses repository OK.")

    print("\n--- PHASE 4: TESTING LOGOUT & OPERATOR LOGIN ---")

    print("[17] Testing GET /logout...")
    res = client.get('/logout', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.headers['Location']
    print("    -> Passed! Logout redirects to /login.")

    print("[18] Testing GET / after Logout (Should be blocked)...")
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.headers['Location']
    print("    -> Passed! Session cleared, access blocked.")

    print("[19] Testing POST /login with Valid Operator Credentials (PTG-001)...")
    res = client.post('/login', data={'role': 'operator', 'identifier': 'PTG-001', 'password': 'password123'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/operator/tugas' in res.headers['Location']
    print("    -> Passed! Operator login succeeded, redirected to /operator/tugas.")

    print("[20] Testing GET /operator/tugas as Authenticated Operator...")
    res = client.get('/operator/tugas')
    assert res.status_code == 200
    assert b"Tugas Survei Saya" in res.data
    assert b"Budi Santoso" in res.data
    assert b"PTG-001" in res.data
    print("    -> Passed! Operator tugas page loads with correct operator.")

    print("[21] Testing GET /operator/profil as Authenticated Operator...")
    res = client.get('/operator/profil')
    assert res.status_code == 200
    assert b"Profil Petugas" in res.data
    assert b"Perbarui Informasi Data Diri" in res.data
    print("    -> Passed! Operator profile page OK.")

    print("\n--- PHASE 5: TESTING ROLE RESTRICTIONS (OPERATOR BOUNDARIES) ---")

    print("[22] Testing Operator attempting to access Admin route / (Dashboard)...")
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/operator/tugas' in res.headers['Location']
    print("    -> Passed! Operator blocked from /, redirected to /operator/tugas.")

    print("[23] Testing Operator attempting to access Admin route /petugas...")
    res = client.get('/petugas', follow_redirects=False)
    assert res.status_code == 302
    assert '/operator/tugas' in res.headers['Location']
    print("    -> Passed! Operator blocked from /petugas.")

    print("[24] Testing Operator attempting to access Admin route /survei/tambah...")
    res = client.get('/survei/tambah', follow_redirects=False)
    assert res.status_code == 302
    assert '/operator/tugas' in res.headers['Location']
    print("    -> Passed! Operator blocked from /survei/tambah.")

    print("\n--- PHASE 6: TESTING OPERATOR FIELD SURVEY SUBMISSION ---")

    print(f"[25] Testing GET /operator/survei/{s_id}/isi as Authenticated Operator...")
    res = client.get(f'/operator/survei/{s_id}/isi')
    assert res.status_code == 200
    assert b"Target Sampel Anda" in res.data
    print("    -> Passed! Field survey form OK.")

    print(f"[26] Testing POST /operator/survei/{s_id}/isi (Operator Input Sample with pendidikan_terakhir)...")
    sample_data = {
        'nama_responden': 'Warga Uji Coba Enumerator #99',
        'kontak_responden': '081399887766',
        'usia': '35',
        'jenis_kelamin': 'Perempuan',
        'pendidikan_terakhir': 'Diploma (D1 - D4)',
        'titik_koordinat': '-6.208763, 106.845599',
        'alamat_wilayah': 'Kelurahan Menteng RT 05',
    }
    for q_idx, qid in enumerate(pertanyaan_ids):
        if q_idx == 0:
            sample_data[f'q_{qid}'] = 'Administrasi Kependudukan (KTP/KK/Akta)'
        elif q_idx in [1, 2, 3]:
            sample_data[f'q_{qid}'] = '5'
        elif q_idx == 4:
            sample_data[f'q_{qid}'] = 'Sesuai Tarif Resmi & Sangat Transparan'
        elif q_idx == 5:
            sample_data[f'q_{qid}[]'] = ['Sistem Antrean Online & Notifikasi WA']
        elif q_idx == 6:
            sample_data[f'q_{qid}'] = 'Aplikasi Mobile Resmi'
        elif q_idx == 7:
            sample_data[f'q_{qid}'] = '10'
        else:
            sample_data[f'q_{qid}'] = 'Pelayanan enumerator sangat ramah dan efisien.'

    res = client.post(f'/operator/survei/{s_id}/isi', data=sample_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Sampel Berhasil Disimpan" in res.data
    assert b"Lanjut Input Sampel Berikutnya" in res.data
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, pendidikan_terakhir, titik_koordinat FROM responden WHERE nama_responden = 'Warga Uji Coba Enumerator #99' ORDER BY id DESC LIMIT 1")
    op_row = c.fetchone()
    conn.close()
    assert op_row and op_row[1] == 'Diploma (D1 - D4)', f"Expected 'Diploma (D1 - D4)', got {op_row}"
    assert op_row[2] == '-6.208763, 106.845599', f"Expected '-6.208763, 106.845599', got {op_row[2]}"
    new_resp_id = op_row[0]
    print("    -> Passed! Operator survey sample saved with pendidikan_terakhir and titik_koordinat.")

    print(f"[27] Testing GET /api/responden/{new_resp_id}/detail as Authenticated Operator...")
    res = client.get(f'/api/responden/{new_resp_id}/detail')
    assert res.status_code == 200
    detail_data = json.loads(res.data)
    assert detail_data['success'] is True
    assert detail_data['responden']['pendidikan_terakhir'] == 'Diploma (D1 - D4)'
    assert detail_data['responden']['titik_koordinat'] == '-6.208763, 106.845599'
    print("    -> Passed! Operator can fetch respondent detail modal data; pendidikan_terakhir and titik_koordinat verified.")

    print("\n=======================================================")
    print(" ALL 27 AUTOMATED INTEGRATION TESTS PASSED 100%! ")
    print("=======================================================\n")

if __name__ == '__main__':
    run_tests()
