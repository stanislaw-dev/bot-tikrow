import requests
import time
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask
from threading import Thread

# --- KONFIGURACJA ---
TELEGRAM_BOT_TOKEN = '8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw'
TELEGRAM_CHAT_ID = '6327998362'

# URL dla Snajpera (szeroka sieć na starcie)
SNIPER_URL = 'https://commissions.tikrow.com/list?range=30&state=available&newList=true&perPage=40&lat=53.379360370518434&lng=14.64955069417926'

# URL dla Wartownika (Twoje sztywne 10 zleceń na stronę)
DAILY_BASE_URL = 'https://commissions.tikrow.com/list?range=30&state=available&newList=true&perPage=10&lat=53.379360370518434&lng=14.64955069417926'

TARGET_ADDRESSES = [
    "walecznych 64", "goleniowska 87", "botaniczna 29", "struga 18",
    "leszczynowa 23", "komfortowa 10", "pomarańczowa 9", "rydla 93",
    "26 kwietnia 91", "narutowicza 11", "piastów 22" 
]

HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'authorization': 'Bearer 13ae865387079b51ef932e8aff5396bcaa61dd75',
    'origin': 'https://partner.tikrow.com',
    'referer': 'https://partner.tikrow.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'x-instance': '1', 'x-version': '3.1.8'
}

seen_jobs = set()
token_dead_notified = False
# Zaczynamy od 1, aby matryca wyliczała cykle: 1, 2, 3 (krótkie), 4 (długi)
cycle_counter = 1 

session = requests.Session()
session.headers.update(HEADERS)

app = Flask('')
@app.route('/')
def home(): return "Bot hybrydowy (Snajper + Wartownik 3:1) działa!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: session.post(url, json=payload, timeout=5)
    except Exception as e: print(f"Błąd Telegrama: {e}", flush=True)

def process_jobs(data, warsaw_tz, tag=""):
    for job in data:
        if job.get('taken'): continue
        
        job_id = job.get('id')
        city = job.get('customer_city', '')
        address = job.get('customer_address', '')
        
        if job_id not in seen_jobs:
            print(f"   -> Radar wykrył: {city}, {address}", flush=True)
            
        address_lower = str(address).lower()
        if any(target in address_lower for target in TARGET_ADDRESSES):
            if job_id not in seen_jobs:
                seen_jobs.add(job_id)
                
                company = job.get('customer', 'Nieznana firma')
                position = job.get('position', 'Praca')
                start_date_ts = job.get('start_date')
                
                if start_date_ts:
                    dt = datetime.fromtimestamp(start_date_ts, warsaw_tz)
                    dni = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
                    job_date = dt.strftime(f'%d.%m.%Y ({dni[dt.weekday()]}), godz. %H:%M')
                else:
                    job_date = 'Brak danych'
                
                job_url = f"https://partner.tikrow.com/user-commissions/{job_id}/details"
                msg = f"{tag}🏢 *Firma:* {company}\n📅 *Kiedy:* {job_date}\n📍 *Adres:* {address}\n💼 *Stanowisko:* {position}\n\n🔗 [Kliknij tutaj, aby otworzyć zlecenie]({job_url})"
                
                send_telegram_message(msg)
                print(f"Wysłano powiadomienie: {company} - {address} ({job_date})", flush=True)

def check_jobs():
    global token_dead_notified, cycle_counter
    warsaw_tz = ZoneInfo("Europe/Warsaw")
    today = datetime.now(warsaw_tz)
    
    # --- ETAP 1: GLOBALNY SNAJPER ---
    try:
        resp = session.get(SNIPER_URL, timeout=7)
        if resp.status_code == 429:
            time.sleep(90); return
        if resp.status_code == 200:
            sniper_data = resp.json().get('_embedded', {}).get('commissions', [])
            process_jobs(sniper_data, warsaw_tz, tag="🎯 *SNAJPER*\n")
    except Exception as e:
        print(f"Błąd Snajpera: {e}", flush=True)

    # --- ETAP 2: SZCZEGÓŁOWY WARTOWNIK (Matryca 3:1) ---
    if cycle_counter % 4 == 0:
        days_to_check = 30
        mode_label = "Zakres: 30 dni"
    else:
        days_to_check = 10
        mode_label = "Zakres: 10 dni"
    
    cycle_counter += 1
    total_daily_jobs = 0
    
    for day_offset in range(days_to_check):
        target_date = (today + timedelta(days=day_offset)).strftime('%Y-%m-%d')
        
        for page in range(1, 21): 
            try:
                url = f"{DAILY_BASE_URL}&dateFrom={target_date}+00%3A00%3A00&dateTo={target_date}+23%3A59%3A59&page={page}"
                response = session.get(url, timeout=7)
                
                if response.status_code == 429:
                    send_telegram_message("⚠️ *LIMIT PRZEKROCZONY (429)*\nTikrow nałożył blokadę. Ostudzam łącze na 90 sekund.")
                    print(f"[{datetime.now(warsaw_tz).strftime('%H:%M:%S')}] Błąd 429. Zasypiam na 90s...", flush=True)
                    time.sleep(90)
                    return 

                if response.status_code == 401:
                    if not token_dead_notified:
                        send_telegram_message("⚠️ *CRITICAL ERROR*\nTwój token Bearer stracił ważność!\nPodmień go w pliku na GitHubie.")
                        token_dead_notified = True
                    print("Błąd 401: Token wygasł.", flush=True)
                    return
                elif response.status_code != 200:
                    continue
                
                token_dead_notified = False
                jobs = response.json()
                
                try: data = jobs['_embedded']['commissions']
                except KeyError: break 
                
                if not data: break 
                
                process_jobs(data, warsaw_tz, tag="")
                total_daily_jobs += len([j for j in data if not j.get('taken')])
                
                # --- HAMULEC LOGICZNY ---
                # Jeśli serwer odesłał mniej niż 10 zleceń na stronie, nie ma sensu szukać kolejnej
                if len(data) < 10:
                    break
                
                time.sleep(random.uniform(0.55, 0.65))
                
            except Exception as e:
                print(f"Błąd na str {page} ({target_date}): {e}", flush=True)
                break
                
    warsaw_time = datetime.now(warsaw_tz).strftime('%H:%M:%S')
    print(f"[{warsaw_time}] Tryb: {mode_label} | Przetworzono zlecenia dzienne: {total_daily_jobs}", flush=True)

keep_alive()
print("Uruchamiam bota (Snajper + Matryca 3:1 + 10 zleceń/stronę)...", flush=True)

while True:
    warsaw_time = datetime.now(ZoneInfo("Europe/Warsaw"))
    if 0 <= warsaw_time.hour < 6:
        time.sleep(300)
        continue

    check_jobs()
    time.sleep(random.randint(3, 5))
