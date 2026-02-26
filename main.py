import requests
import time
from flask import Flask
from threading import Thread

# --- KONFIGURACJA ---
TELEGRAM_BOT_TOKEN = '8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw'
TELEGRAM_CHAT_ID = '6327998362'
TIKROW_API_URL = 'https://commissions.tikrow.com/list?page=1&range=0&state=available&newList=true&perPage=100'

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'authorization': 'Bearer 13ae865387079b51ef932e8aff5396bcaa61dd75',
    'origin': 'https://partner.tikrow.com',
    'referer': 'https://partner.tikrow.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'x-instance': '1',
    'x-version': '3.1.8'
}

seen_jobs = set()

# --- MODUŁ ZAPOBIEGAJĄCY USYPIANIU BOTA ---
app = Flask('')

@app.route('/')
def home():
    return "Bot monitorujacy Tikrow dziala i ma sie dobrze!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- LOGIKA BOTA ---
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Błąd Telegrama: {e}", flush=True)

def check_jobs():
    try:
        response = requests.get(TIKROW_API_URL, headers=HEADERS)
        if response.status_code != 200:
            print(f"Błąd Tikrow: {response.status_code}", flush=True)
            return

        jobs = response.json()
        
        # Bezpieczne pobranie listy zleceń
        if isinstance(jobs, list):
            data = jobs
        else:
            data = jobs.get('data', [])
        
        # LOGOWANIE: Wymuszenie wyświetlenia w konsoli Render
        print(f"[{time.strftime('%H:%M:%S')}] Pobrałem {len(data)} dostępnych zleceń w Polsce.", flush=True)
        
        # DIAGNOSTYKA: Wypisanie surowej struktury pierwszego zlecenia, żebyśmy zobaczyli z czym walczymy
        if len(data) > 0 and not hasattr(check_jobs, 'debug_printed'):
            print(f"STRUKTURA ZLECENIA: {data[0]}", flush=True)
            check_jobs.debug_printed = True
        
        for job in data:
            job_id = job.get('id')
            city = job.get('city', '')

            if city and 'szczecin' in str(city).lower():
                if job_id not in seen_jobs:
                    seen_jobs.add(job_id)
                    company = job.get('company_name', 'Nieznana firma')
                    rate = job.get('rate', 'Brak danych')
                    msg = f"🚨 *Nowe zlecenie w Szczecinie!*\nFirma: {company}\nStawka: {rate} PLN"
                    send_telegram_message(msg)
                    print(f"Wysłano powiadomienie: {company}", flush=True)

    except Exception as e:
        print(f"Błąd skryptu: {e}", flush=True)

# Uruchomienie fałszywego serwera i głównej pętli
keep_alive()
print("Uruchamiam bota w chmurze...", flush=True)
while True:
    check_jobs()
    time.sleep(15)
