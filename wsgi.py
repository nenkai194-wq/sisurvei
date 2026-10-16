"""
WSGI Entry Point untuk Production Server Hosting (cPanel / Gunicorn / Nginx / Docker / PaaS).
"""
import os
from app import app, init_db, start_auto_backup_daemon

# Inisialisasi basis data dan modul cadangan otomatis di lingkungan produksi
init_db()
start_auto_backup_daemon()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port)
