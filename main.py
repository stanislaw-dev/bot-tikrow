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

TIKROW_BASE_URL = 'https://commissions.tikrow.com/list?range=30&state=available&newList=true&perPage=10&lat=53.379360370518434&lng=14.64955069417926'

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
cycle_counter = 0 

app = Flask('')
@app.route('/')
def home(): return "Bot Tikrow: Tryb Wartownik 3:1 (0.6s) Aktywny!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except Exception as e: print(f"Błąd Telegrama: {e}", flush=True)

def check_jobs():
    global token_dead_notified, cycle_counter
    all_available_now = []
    warsaw_tz = ZoneInfo("Europe/Warsaw")
    today = datetime.now(warsaw_tz)
    
    # ZMIANA: Skala 3:1 (co 3 cykle pełny skan 30 dni)
    if cycle_counter % 3 == 0:
        days_to_check = 30
        mode_label = "GŁĘBOKI (30 dni)"
    else:
        days_to_check = 10
        mode_label = "SZYBKI (10 dni)"
    
    cycle_counter += 1
    start_time = time.time()
    
    for day_offset in range(days_to_check):
        target_date = (today + timedelta(days=day_offset)).strftime('%Y-%m-%d')
        
        for page in range(1, 11): 
            try:
                url = f"{TIKROW_BASE_URL}&dateFrom={target_date}+00%3A00%3A00&dateTo={target_date}+23%3A59%3A59&page={page}"
                response = requests.get(url, headers=HEADERS, timeout=7)
                
                if response.status_code == 401:
                    if not token_dead_notified:
                        send_telegram_message("⚠️ *TOKEN WYGASŁ!* Zmień Bearer na GitHubie.")
                        token_dead_notified = True
                    return
                
                token_dead_notified = False
                jobs = response.json()
                data = jobs.get('_embedded', {}).get('commissions', [])
                
                if not data: break 
                
                all_available_now.extend([j for j in data if not j.get('taken')])
                
                # Bezpieczne 0,6s z lekkim rozrzutem (jitter)
                time.sleep(random.uniform(0.55, 0.65))
                
            except Exception as e:
                print(f"Błąd sieciowy: {e}", flush=True)
                break
                
    unique_jobs = {job['id']: job for job in all_available_now}.values()
    duration = round(time.time() - start_time, 1)
    warsaw_now = datetime.now(warsaw_tz).strftime('%H:%M:%S')
    
    print(f"[{warsaw_now}] Tryb: {mode_label} | Czas: {duration}s | Znaleziono: {len(unique_jobs)}", flush=True)
    
    for job in unique_jobs:
        job_id = job.get('id')
        address = job.get('customer_address', '')
        if any(target in str(address).lower() for target in TARGET_ADDRESSES):
            if job_id not in seen_jobs:
                seen_jobs.add(job_id)
                company = job.get('customer', 'Firma')
                rate = job.get('rate_total', '?')
                start_ts = job.get('start_date')
                dt = datetime.fromtimestamp(start_ts, warsaw_tz)
                job_date = dt.strftime('%d.%m (%a), %H:%M')
                
                job_url = f"https://partner.tikrow.com/user-commissions/{job_id}/details"
                msg = f"🚨 *RADAR WYKRYŁ:* {company}\n📅 {job_date}\n📍 {address}\n💰 {rate} PLN\n\n🔗 [REZERWUJ TUTAJ]({job_url})"
                send_telegram_message(msg)

keep_alive()
while True:
    warsaw_time = datetime.now(ZoneInfo("Europe/Warsaw"))
    if 0 <= warsaw_time.hour < 6:
        time.sleep(300)
        continue

    check_jobs()
    # Mała pauza między rundami
    time.sleep(random.randint(3, 5))
