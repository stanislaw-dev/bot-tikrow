import time
import random
import cloudscraper
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask
from threading import Thread

# --- KONFIGURACJA ---
TELEGRAM_BOT_TOKEN = '8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw'
TELEGRAM_CHAT_ID = '6327998362'

# Tutaj wpisujesz token ręcznie (Selenium by tu nie ruszyło na 512MB)
BEARER_TOKEN = '13ae865387079b51ef932e8aff5396bcaa61dd75'

# Strategia kolegi: 75 najnowszych wrzutek
API_URL = "https://commissions.tikrow.com/list?range=30&state=available&newList=true&perPage=75&lat=53.379360370518434&lng=14.64955069417926"

TARGET_ADDRESSES = [
    "walecznych 64", "goleniowska 87", "botaniczna 29", "struga 18",
    "leszczynowa 23", "komfortowa 10", "pomarańczowa 9", "rydla 93",
    "26 kwietnia 91", "narutowicza 11", "piastów 22" 
]

seen_jobs = set()
scraper = cloudscraper.create_scraper()

app = Flask('')
@app.route('/')
def home(): return "Bot Snajper 75 (Free Tier Optimized) działa!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: scraper.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except: pass

def check_offers():
    global seen_jobs
    warsaw_tz = ZoneInfo("Europe/Warsaw")

    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "X-Instance": "1", "X-Version": "3.1.8", "Accept": "application/json"
    }

    try:
        res = scraper.get(API_URL, headers=headers, timeout=10)
        
        if res.status_code in [401, 403]:
            print("🔑 TOKEN EXPIRED! Zmień go w kodzie.", flush=True)
            return
        
        if res.status_code == 429:
            time.sleep(90); return

        data = res.json()
        items = data.get("_embedded", {}).get('commissions', [])
        
        for item in items:
            if item.get("taken"): continue
            
            oid = item.get("id")
            address = item.get("customer_address", "")
            address_lower = str(address).lower()
            
            if any(target in address_lower for target in TARGET_ADDRESSES):
                if oid not in seen_jobs:
                    seen_jobs.add(oid)
                    
                    company = item.get("customer", "Tikrow")
                    pos = item.get("position", "Zlecenie")
                    start_ts = item.get("start_date")
                    
                    dt = datetime.fromtimestamp(start_ts, warsaw_tz)
                    dni = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
                    job_date = dt.strftime(f"%d.%m ({dni[dt.weekday()]}), %H:%M")
                    
                    job_url = f"https://partner.tikrow.com/user-commissions/{oid}/details"
                    
                    msg = (f"🎯 *SZYBKI STRZAŁ*\n\n"
                           f"🏢 *{company}*\n"
                           f"📍 {address}\n"
                           f"📅 {job_date}\n"
                           f"💼 {pos}\n\n"
                           f"🔗 [OTWÓRZ ZLECENIE]({job_url})")
                    
                    send_msg(msg)
                    print(f"[{datetime.now(warsaw_tz).strftime('%H:%M:%S')}] ✅ Wysłano: {address}", flush=True)

    except Exception as e:
        print(f"⚠️ Błąd: {e}", flush=True)

keep_alive()
print("🚀 START: Snajper 75 (Lekki silnik)", flush=True)
while True:
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    if 6 <= now.hour <= 23:
        check_offers()
        time.sleep(random.randint(10, 15))
    else:
        time.sleep(300)
