from app import app
from database import get_db
import json

def run_tests():
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
    
    print("[1] Testing GET / (Dashboard)...")
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Si" in res.data and b"Survei" in res.data
    print("    -> Passed! Dashboard OK.")

    print("[2] Testing GET /survei (Survei List)...")
    res = client.get('/survei')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"SRV-2026-001" in res.data
    print("    -> Passed! Survey list OK.")

    print(f"[3] Testing GET /survei/{s_id}/builder (Question Builder)...")
    res = client.get(f'/survei/{s_id}/builder')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Perancang Kuisioner" in res.data
    print("    -> Passed! Builder page OK.")

    print(f"[4] Testing GET /survei/{s_id}/hasil (Dashboard Hasil Survei)...")
    res = client.get(f'/survei/{s_id}/hasil')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Visualisasi Analisis Hasil Kuisioner" in res.data
    print("    -> Passed! Results analytics dashboard OK.")

    print(f"[5] Testing GET /survei/{s_id}/export/excel (Export Excel)...")
    res = client.get(f'/survei/{s_id}/export/excel')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "spreadsheetml" in res.content_type
    assert len(res.data) > 1000
    print("    -> Passed! Excel generation OK.")

    print(f"[6] Testing GET /survei/{s_id}/export/csv (Export CSV)...")
    res = client.get(f'/survei/{s_id}/export/csv')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "text/csv" in res.content_type
    print("    -> Passed! CSV generation OK.")

    print("[7] Testing GET /s/SRV-2026-001 (Survey Fill Form)...")
    res = client.get('/s/SRV-2026-001')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Kuisioner" in res.data
    print("    -> Passed! Fill form OK.")

    print("[8] Testing POST /s/SRV-2026-001 (Submitting response)...")
    post_data = {
        'nama_responden': 'Responden Tester Otomatis',
        'kontak_responden': '081234567890',
        'usia': '30',
        'jenis_kelamin': 'Laki-laki',
        'alamat_wilayah': 'Jakarta Pusat',
        'input_mode': 'petugas',
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
    print("    -> Passed! Response submission OK.")

    print("[9] Testing GET /petugas (Petugas Directory)...")
    res = client.get('/petugas')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Budi Santoso" in res.data
    print("    -> Passed! Petugas directory OK.")

    print(f"[10] Testing GET /petugas/{p_id} (Petugas Profile & Performance)...")
    res = client.get(f'/petugas/{p_id}')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"PTG-001" in res.data
    print("    -> Passed! Petugas detail OK.")

    print("[11] Testing GET /respons (All Responses Master)...")
    res = client.get('/respons')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Repositori Data Responden" in res.data
    print("    -> Passed! All responses list OK.")

    print(f"[12] Testing GET /api/responden/{r_id}/detail (API Detail)...")
    res = client.get(f'/api/responden/{r_id}/detail')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['answers']) > 0
    print("    -> Passed! JSON API detail OK.")

    print(f"[13] Testing API Question Builder on Survey {s_id}: Add, Update, Delete...")
    new_q_payload = {
        'teks_pertanyaan': 'Apakah Anda akan merekomendasikan layanan ini ke rekan Anda?',
        'tipe_pertanyaan': 'radio',
        'pilihan_opsi': ['Pasti Rekomendasikan', 'Mungkin', 'Tidak'],
        'is_required': True,
        'panduan': 'Pilih salah satu',
        'rating_max': 5
    }
    res = client.post(f'/api/survei/{s_id}/pertanyaan', json=new_q_payload)
    assert res.status_code == 200
    res_data = json.loads(res.data)
    assert res_data['success'] is True
    new_q_id = res_data['id']
    print(f"    -> Added Question ID {new_q_id} successfully.")

    # Update question
    update_payload = {
        'teks_pertanyaan': 'Apakah Anda akan merekomendasikan layanan ini ke keluarga/rekan Anda? (Updated)',
        'tipe_pertanyaan': 'radio',
        'pilihan_opsi': ['Sangat Merekomendasikan', 'Cukup Merekomendasikan', 'Tidak'],
        'is_required': True,
        'panduan': 'Pilih salah satu jawaban',
        'rating_max': 5
    }
    res = client.post(f'/api/pertanyaan/{new_q_id}/update', json=update_payload)
    assert res.status_code == 200
    assert json.loads(res.data)['success'] is True
    print(f"    -> Updated Question ID {new_q_id} successfully.")

    # Delete question
    res = client.post(f'/api/pertanyaan/{new_q_id}/hapus')
    assert res.status_code == 200
    assert json.loads(res.data)['success'] is True
    print(f"    -> Deleted Question ID {new_q_id} successfully.")

    print("[14] Testing CRUD Petugas: Add with Photo...")
    petugas_payload = {
        'nip': 'PTG-TEST-99',
        'nama': 'Petugas Uji Coba',
        'email': 'uji@survei.go.id',
        'no_hp': '089999999999',
        'wilayah': 'Bandung Timur',
        'jabatan': 'Enumerator Pengujian',
        'status': 'Aktif',
        'foto_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300'
    }
    res = client.post('/petugas/tambah', data=petugas_payload, follow_redirects=True)
    assert res.status_code == 200
    assert b"Petugas Uji Coba" in res.data
    print("    -> Added Petugas successfully.")

    print("[15] Testing GET /operator (Operator Redirect)...")
    res = client.get('/operator', follow_redirects=True)
    assert res.status_code == 200
    assert b"Tugas Survei Saya" in res.data
    print("    -> Passed! Operator portal redirect OK.")

    print("[16] Testing GET /operator/tugas (Operator Tasks Page)...")
    res = client.get('/operator/tugas')
    assert res.status_code == 200
    assert b"Daftar Keikutsertaan Penugasan Survei" in res.data
    assert b"Target Sampel" in res.data
    assert b"Buka Form Kuisioner" in res.data
    print("    -> Passed! Operator tasks page OK.")

    print("[17] Testing GET /operator/profil (Operator Profile)...")
    res = client.get('/operator/profil')
    assert res.status_code == 200
    assert b"Profil Petugas" in res.data
    assert b"Perbarui Informasi Data Diri" in res.data
    print("    -> Passed! Operator profile page OK.")

    print("[18] Testing POST /operator/profil (Update Profile)...")
    profile_data = {
        'nama': 'Budi Santoso, S.Kom, M.T.',
        'no_hp': '081299998888',
        'email': 'budi.santoso@survei.go.id',
        'wilayah': 'Jakarta Pusat & Barat',
        'foto_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300'
    }
    res = client.post('/operator/profil', data=profile_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Budi Santoso, S.Kom, M.T." in res.data
    print("    -> Passed! Operator profile update OK.")

    print(f"[19] Testing GET /operator/survei/{s_id}/isi (Operator Survey Filling Form)...")
    res = client.get(f'/operator/survei/{s_id}/isi')
    assert res.status_code == 200
    assert b"Target Sampel Anda" in res.data
    assert b"Sedang Menginput: Sampel ke-" in res.data
    print("    -> Passed! Operator survey filling form OK.")

    print(f"[20] Testing POST /operator/survei/{s_id}/isi (Operator Submit Sample)...")
    sample_data = {
        'nama_responden': 'Warga Sampel Lapangan #1',
        'kontak_responden': '081300000000',
        'usia': '42',
        'jenis_kelamin': 'Perempuan',
        'alamat_wilayah': 'Kelurahan Menteng RT 01',
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
            sample_data[f'q_{qid}'] = 'Pelayanan lapangan oleh enumerator sangat memuaskan dan cepat.'

    res = client.post(f'/operator/survei/{s_id}/isi', data=sample_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Sampel Berhasil Disimpan" in res.data
    assert b"Lanjut Input Sampel Berikutnya" in res.data
    print("    -> Passed! Operator sample submission and next trigger OK.")

    print("\n=======================================================")
    print(" ALL 20 AUTOMATED INTEGRATION TESTS PASSED 100%! ")
    print("=======================================================")

if __name__ == '__main__':
    run_tests()
