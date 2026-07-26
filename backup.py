import os
import json
import base64
import requests
from datetime import datetime

HOTEL_URL = os.environ.get('HOTEL_URL', 'https://hotel-iguazu.onrender.com')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_BACKUP_REPO', 'luispalacios4523-svg/hotel-backups')

def run_backup():
    print(f"Iniciando backup desde {HOTEL_URL}...")
    resp = requests.get(f'{HOTEL_URL}/api/load', timeout=60)
    resp.raise_for_status()
    data = resp.json()

    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'backup-{today}.json'
    content = json.dumps(data, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }

    existing = requests.get(url, headers=headers)
    payload = {
        'message': f'Backup automatico {today}',
        'content': encoded
    }
    if existing.status_code == 200:
        payload['sha'] = existing.json()['sha']

    result = requests.put(url, headers=headers, json=payload)
    result.raise_for_status()
    print(f'Backup {filename} guardado exitosamente en GitHub.')

if __name__ == '__main__':
    run_backup()
