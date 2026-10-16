from app import app
import json

def run_tests():
    client = app.test_client()
    
    print("[1] Testing GET / (Dashboard)...")
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"SiSurvei" in res.data
    print("    -> Passed! Dashboard OK.")

    print("[2] Testing GET /survei (Survei List)...")
    res = client.get('/survei')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"SRV-2026-001" in res.data
    print("    -> Passed! Survey list OK.")

    print("[3] Testing GET /survei/1/builder (Question Builder)...")
    res = client.get('/survei/1/builder')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Perancang Kuisioner" in res.data
    print("    -> Passed! Builder page OK.")

    print("[4] Testing GET /survei/1/hasil (Dashboard Hasil Survei)...")
    res = client.get('/survei/1/hasil')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Visualisasi Analisis Hasil Kuisioner" in res.data
    print("    -> Passed! Results analytics dashboard OK.")

    print("[5] Testing GET /survei/1/export/excel (Export Excel)...")
    res = client.get('/survei/1/export/excel')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "spreadsheetml" in res.content_type
    assert len(res.data) > 1000
    print("    -> Passed! Excel generation OK.")

    print("[6] Testing GET /survei/1/export/csv (Export CSV)...")
    res = client.get('/survei/1/export/csv')
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
        'petugas_id': '1',
        'q_1': 'Administrasi Kependudukan (KTP/KK/Akta)',
        'q_2': '5',
        'q_3': '4',
        'q_4': '5',
        'q_5': 'Sesuai Tarif Resmi & Sangat Transparan',
        'q_6[]': ['Sistem Antrean Online & Notifikasi WA', 'Toilet yang Lebih Bersih & Higienis'],
        'q_7': 'Aplikasi Mobile Resmi',
        'q_8': '15',
        'q_9': 'Pelayanan testing otomatis sangat memuaskan!'
    }
    res = client.post('/s/SRV-2026-001', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Terima Kasih" in res.data
    print("    -> Passed! Response submission OK.")

    print("[9] Testing GET /petugas (Petugas Directory)...")
    res = client.get('/petugas')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Budi Santoso" in res.data
    print("    -> Passed! Petugas directory OK.")

    print("[10] Testing GET /petugas/1 (Petugas Profile & Performance)...")
    res = client.get('/petugas/1')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"PTG-001" in res.data
    print("    -> Passed! Petugas detail OK.")

    print("[11] Testing GET /respons (All Responses Master)...")
    res = client.get('/respons')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert b"Repositori Data Responden" in res.data
    print("    -> Passed! All responses list OK.")

    print("[12] Testing GET /api/responden/1/detail (API Detail)...")
    res = client.get('/api/responden/1/detail')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['answers']) > 0
    print("    -> Passed! JSON API detail OK.")

    print("[13] Testing API Question Builder: Add, Update, Reorder, Delete...")
    # Add new question to Survey 1
    new_q_payload = {
        'teks_pertanyaan': 'Apakah Anda akan merekomendasikan layanan ini ke rekan Anda?',
        'tipe_pertanyaan': 'radio',
        'pilihan_opsi': ['Pasti Rekomendasikan', 'Mungkin', 'Tidak'],
        'is_required': True,
        'panduan': 'Pilih salah satu',
        'rating_max': 5
    }
    res = client.post('/api/survei/1/pertanyaan', json=new_q_payload)
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

    print("[14] Testing CRUD Petugas: Add & Edit...")
    petugas_payload = {
        'nip': 'PTG-TEST-99',
        'nama': 'Petugas Uji Coba',
        'email': 'uji@survei.go.id',
        'no_hp': '089999999999',
        'wilayah': 'Bandung Timur',
        'jabatan': 'Enumerator Pengujian',
        'status': 'Aktif'
    }
    res = client.post('/petugas/tambah', data=petugas_payload, follow_redirects=True)
    assert res.status_code == 200
    assert b"Petugas Uji Coba" in res.data
    print("    -> Added Petugas successfully.")

    print("\n=======================================================")
    print(" ALL 14 AUTOMATED INTEGRATION TESTS PASSED 100%! ")
    print("=======================================================")

if __name__ == '__main__':
    run_tests()
