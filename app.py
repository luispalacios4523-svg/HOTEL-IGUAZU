from flask import Flask, request, jsonify, send_file
import json
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import pg8000.native

    def get_db():
        # pg8000 acepta la URL directamente parseandola
        import urllib.parse
        r = urllib.parse.urlparse(DATABASE_URL)
        conn = pg8000.native.Connection(
            host=r.hostname,
            port=r.port or 5432,
            database=r.path.lstrip('/'),
            user=r.username,
            password=r.password,
            ssl_context=True
        )
        return conn

    def init_db():
        conn = get_db()
        conn.run('''CREATE TABLE IF NOT EXISTS store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )''')
        conn.close()

    def db_load_all():
        conn = get_db()
        try:
            rows = conn.run('SELECT key, value FROM store')
        finally:
            try:
                conn.close()
            except Exception:
                pass
        result = {}
        for key, value in rows:
            try:
                result[key] = json.loads(value)
            except Exception:
                result[key] = value
        return result

    def db_save(data):
        # Todo o nada: si algo falla a mitad, Postgres descarta los cambios
        # y los datos quedan como estaban. Nunca se guarda "una parte".
        conn = get_db()
        try:
            conn.run('BEGIN')
            for key, value in data.items():
                conn.run(
                    'INSERT INTO store (key, value) VALUES (:key, :value) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value',
                    key=key, value=json.dumps(value, ensure_ascii=False)
                )
            conn.run('COMMIT')
        finally:
            # Se cierra siempre, aunque el proceso muera por timeout
            try:
                conn.close()
            except Exception:
                pass

else:
    import sqlite3

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

    def db_load_all():
        conn = get_db()
        rows = conn.execute('SELECT key, value FROM store').fetchall()
        conn.close()
        result = {}
        for row in rows:
            try:
                result[row['key']] = json.loads(row['value'])
            except Exception:
                result[row['key']] = row['value']
        return result

    def db_save(data):
        conn = get_db()
        for key, value in data.items():
            conn.execute(
                'INSERT OR REPLACE INTO store (key, value) VALUES (?, ?)',
                (key, json.dumps(value, ensure_ascii=False))
            )
        conn.commit()
        conn.close()


def _cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/health')
def health():
    # Chequeo liviano para Render. NO consulta la base de datos a proposito:
    # su unico trabajo es probar que el worker puede responder. Si el worker
    # esta atascado, esto no contesta y Render reinicia el servicio solo.
    return 'ok', 200

@app.route('/')
def index():
    return send_file('hotel_manager.html')

@app.route('/api/efectivo')
def efectivo():
    val = db_load_all().get('efectivo_actual', 0)
    r = jsonify({'efectivo': val})
    return _cors(r)

@app.route('/api/load')
def load():
    return jsonify(db_load_all())

@app.route('/api/save', methods=['POST'])
def save():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'error': 'No data'}), 400
    db_save(data)
    return jsonify({'ok': True})

@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.json
    if not data:
        return jsonify({'ok': False, 'error': 'No data'}), 400

    mapping = {
        'reg':             'hotel_reg',
        'gastos':          'hotel_gastos',
        'gastosDetalle':   'hotel_gastosdet',
        'productos':       'hotel_productos',
        'historialVentas': 'hotel_historial',
        'historialesEst':  'hotel_estadias',
        'saldoInicial':    'hotel_saldo',
        'comprasTienda':   'hotel_compras',
    }
    to_save = {}
    for bk_key, db_key in mapping.items():
        if bk_key in data:
            to_save[db_key] = data[bk_key]
    db_save(to_save)
    return jsonify({'ok': True})


init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
