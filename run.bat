@echo off
title SiSurvei - Sistem Informasi dan Manajemen Survei Terpadu
color 0b
echo ========================================================
echo         SISURVEI - PORTAL MANAJEMEN SURVEI TERPADU
echo ========================================================
echo.
echo Memeriksa database...
if not exist sisurvei.db (
    echo Menginisialisasi database dan memasukkan data awal...
    python seed_data.py
)
echo.
echo Menjalankan server aplikasi...
echo Buka browser dan akses: http://127.0.0.1:5000
echo Tekan CTRL + C untuk menghentikan server.
echo.
python app.py
pause
