import requests
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask
from threading import Thread

# --- KONFIGURACJA ---
TELEGRAM_BOT_TOKEN = '8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw'
TELEGRAM_CHAT_ID = '6327998362'

# ZMIANA: Zwiększono range z 15 na 30, aby sprawdzić, czy Tikrow ukrywało zlecenia na obrzeżach.
TIKROW_BASE_URL = 'https://commissions.tikrow.com/list?range=30&state=available&newList=true&perPage=10&lat=53.379360370518434&lng=14.64955069417926'

# Lista Twoich wybranych adresów (twardy filtr)
TARGET_ADDRESSES = [
    "walecznych 64",
    "goleniowska 87",
    "botaniczna 29",
    "struga 18",
    "leszczynowa 23",
    "komfortowa 10",
    "pomarańczowa 9",
    "rydla 93",
    "26 kwietnia 91",
    "narutowicza 11",
    "piastów 22" 
]

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
token_dead_notified = False

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
    global token_dead_notified
    all_available_now = []
    
    # Pętla skanująca do 20 stron (200 zleceń), jeśli będzie taka potrzeba
    for page in range(1, 21):
        try:
            url = f"{TIKROW_BASE_URL}&page={page}"
            response = requests.get(url, headers=HEADERS)
            
            if response.status_code == 401:
                if not token_dead_notified:
                    msg = "⚠️ *CRITICAL ERROR*\nTwój token Bearer stracił ważność! Bot jest teraz całkowicie ślepy.\nWejdź w przeglądarkę, skopiuj nowy token i podmień go w pliku na GitHubie."
                    send_telegram_message(msg)
                    token_dead_notified = True
                print("Błąd 401: Token wygasł. Oczekuję na aktualizację kodu.", flush=True)
                return
            elif response.status_code != 200:
                print(f"Błąd Tikrow na stronie {page}: {response.status_code}", flush=True)
                continue

            token_dead_notified = False
            jobs = response.json()
            
            try:
                data = jobs['_embedded']['commissions']
            except KeyError:
                break # Brak klucza danych - przerywamy pętlę
                
            # Inteligentny hamulec - przerywa pętlę, gdy lista na stronie jest już pusta
            if not data:
                break
                
            available_on_page = [job for job in data if job.get('taken') is False]
            all_available_now.extend(available_on_page)
            
            # Bezpiecznik: 1 sekunda przerwy między każdą ze stron
            time.sleep(1.0)
            
        except Exception as e:
            print(f"Błąd pobierania strony {page}: {e}", flush=True)
            
    warsaw_time = datetime.now(ZoneInfo("Europe/Warsaw")).strftime('%H:%M:%S')
    print(f"[{warsaw_time}] Przeskanowałem lokalnie {len(all_available_now)} wolnych zleceń z obszaru 30 km.", flush=True)
    
    for job in all_available_now:
        job_id = job.get('id')
        city = job.get('customer_city', '')
        address = job.get('customer_address', '')

        print(f"   -> Radar wykrył: {city}, {address}", flush=True)

        address_lower = str(address).lower()
        is_interesting = any(target in address_lower for target in TARGET_ADDRESSES)
        
        if is_interesting:
            if job_id not in seen_jobs:
                seen_jobs.add(job_id)
                
                company = job.get('customer', 'Nieznana firma')
                position = job.get('position', 'Praca')
                rate_total = job.get('rate_total', 'Brak danych')
                
                start_date_ts = job.get('start_date')
                
                # ZMIANA: Naprawiono błąd wcięć w tym bloku, który powodował awarię skryptu
                if start_date_ts:
                    dt = datetime.fromtimestamp(start_date_ts, ZoneInfo("Europe/Warsaw"))
                    dni_tygodnia = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
                    dzien_tygodnia = dni_tygodnia[dt.weekday()]
                    job_date = dt.strftime(f'%d.%m.%Y ({dzien_tygodnia}), godz. %H:%M')
                else:
                    job_date = 'Brak danych'
                
                job_url = f"https://partner.tikrow.com/user-commissions/{job_id}/details"
                
                msg = f"🚨 *Nowe zlecenie!*\n📅 *Kiedy:* {job_date}\nStanowisko: {position}\nFirma: {company}\nAdres: {address}\nZarobek: {rate_total} PLN\n\n🔗 [Kliknij tutaj, aby otworzyć zlecenie]({job_url})"
                
                send_telegram_message(msg)
                print(f"Wysłano powiadomienie: {company} - {address} ({job_date})", flush=True)

# Uruchomienie fałszywego serwera i głównej pętli
keep_alive()
print("Uruchamiam bota (Test zasięgu 30km, dynamiczne skanowanie)...", flush=True)

while True:
    warsaw_time = datetime.now(ZoneInfo("Europe/Warsaw"))
    current_hour = warsaw_time.hour

    if 0 <= current_hour < 6:
        print(f"[{warsaw_time.strftime('%H:%M:%S')}] Przerwa nocna. Bot idzie spać. Następne sprawdzenie o 06:00.", flush=True)
        time.sleep(300)
        continue

    check_jobs()
    wait_time = random.randint(10, 25)
    print(f"Czekam {wait_time} sekund do następnego sprawdzenia...", flush=True)
    time.sleep(wait_time)
