import requests
import time
from flask import Flask
from threading import Thread

# --- KONFIGURACJA ---
TELEGRAM_BOT_TOKEN = '8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw'
TELEGRAM_CHAT_ID = '6327998362'
TIKROW_API_URL = 'https://commissions.tikrow.com/list?page=1&range=0&state=available&newList=true&perPage=10'

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
        print(f"Błąd Telegrama: {e}")

def check_jobs():
    try:
        response = requests.get(TIKROW_API_URL, headers=HEADERS)
        if response.status_code != 200:
            print(f"Błąd Tikrow: {response.status_code}")
            return

        jobs = response.json()
        for job in jobs.get('data', []):
            job_id = job.get('id')
            city = job.get('city')

            if city == 'Szczecin' and job_id not in seen_jobs:
                seen_jobs.add(job_id)
                company = job.get('company_name', 'Nieznana firma')
                rate = job.get('rate', 'Brak danych')
                msg = f"🚨 *Nowe zlecenie w Szczecinie!*\nFirma: {company}\nStawka: {rate} PLN"
                send_telegram_message(msg)

    except Exception as e:
        print(f"Błąd: {e}")

# Uruchomienie fałszywego serwera i głównej pętli
keep_alive()
print("Uruchamiam bota w chmurze...")
while True:
    check_jobs()
    time.sleep(15)
