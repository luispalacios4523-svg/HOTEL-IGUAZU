from flask import Flask, request, jsonify, send_file
import sqlite3
import json
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
DB = 'hotel.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS store (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_file('hotel_manager.html')

@app.route('/api/load')
def load():
    conn = get_db()
    rows = conn.execute('SELECT key, value FROM store').fetchall()
    conn.close()
    result = {}
    for row in rows:
        try:
            result[row['key']] = json.loads(row['value'])
        except Exception:
            result[row['key']] = row['value']
    return jsonify(result)

@app.route('/api/save', methods=['POST'])
def save():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'error': 'No data'}), 400
    conn = get_db()
    for key, value in data.items():
        conn.execute(
            'INSERT OR REPLACE INTO store (key, value) VALUES (?, ?)',
            (key, json.dumps(value, ensure_ascii=False))
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'error': 'No data'}), 400

    # Mapeo del formato de backup a las claves de la BD
    mapping = {
        'reg':           'hotel_reg',
        'gastos':        'hotel_gastos',
        'gastosDetalle': 'hotel_gastosdet',
        'productos':     'hotel_productos',
        'historialVentas': 'hotel_historial',
        'historialesEst':  'hotel_estadias',
        'saldoInicial':  'hotel_saldo',
        'comprasTienda': 'hotel_compras',
    }
    conn = get_db()
    for bk_key, db_key in mapping.items():
        if bk_key in data:
            conn.execute(
                'INSERT OR REPLACE INTO store (key, value) VALUES (?, ?)',
                (db_key, json.dumps(data[bk_key], ensure_ascii=False))
            )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
