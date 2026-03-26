import time
import json
import random
import cloudscraper
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask
from threading import Thread

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- KONFIGURACJA ---
TELEGRAM_BOT_TOKEN = '8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw'
TELEGRAM_CHAT_ID = '6327998362'

# JEDYNY URL (Metoda kolegi: 75 najnowszych wrzutek)
API_URL = "https://commissions.tikrow.com/list?range=30&state=available&newList=true&perPage=75&lat=53.379360370518434&lng=14.64955069417926"

TARGET_ADDRESSES = [
    "walecznych 64", "goleniowska 87", "botaniczna 29", "struga 18",
    "leszczynowa 23", "komfortowa 10", "pomarańczowa 9", "rydla 93",
    "26 kwietnia 91", "narutowicza 11", "piastów 22" 
]

seen_jobs = set()
current_token = None
scraper = cloudscraper.create_scraper()

app = Flask('')
@app.route('/')
def home(): return "Bot Czysty Snajper 75 Aktywny!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def get_token_selenium():
    """Automatyczne pobieranie tokena (Silnik Selenium)"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 Logowanie do Tikrow...", flush=True)
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://partner.tikrow.com/")
        
        wait = WebDriverWait(driver, 20)
        guest_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(translate(., 'GOŚĆ', 'gość'), 'gość')]")))
        driver.execute_script("arguments[0].click();", guest_button)
        
        for _ in range(15):
            raw_data = driver.execute_script("return localStorage.getItem('auth-storage');")
            if raw_data:
                data_json = json.loads(raw_data)
                token = data_json.get("state", {}).get("session", {}).get("access_token")
                if token: return token
            time.sleep(1)
        return None
    except Exception as e:
        print(f"⚠️ Błąd logowania: {e}", flush=True)
        return None
    finally:
        if driver: driver.quit()

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: scraper.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except: pass

def check_offers():
    global current_token, seen_jobs
    warsaw_tz = ZoneInfo("Europe/Warsaw")

    if not current_token:
        current_token = get_token_selenium()
        if not current_token:
            time.sleep(60); return

    headers = {
        "Authorization": f"Bearer {current_token}",
        "X-Instance": "1", "X-Version": "3.1.8", "Accept": "application/json"
    }

    try:
        res = scraper.get(API_URL, headers=headers, timeout=15)
        
        if res.status_code in [401, 403]:
            print("🔑 Token wygasł. Odświeżam...", flush=True)
            current_token = None; return
        
        if res.status_code == 429:
            print("⚠️ Błąd 429 (Limit). Czekam 90s...", flush=True)
            time.sleep(90); return

        data = res.json()
        items = data.get("_embedded", {}).get("commissions", [])
        
        for item in items:
            if item.get("taken"): continue
            
            oid = item.get("id")
            address = item.get("customer_address", "")
            address_lower = str(address).lower()
            
            # FILTR: Czy to ulica z Twojej listy?
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
                    
                    msg = (f"🎯 *NOWE ZLECENIE*\n\n"
                           f"🏢 *{company}*\n"
                           f"📍 {address}\n"
                           f"📅 {job_date}\n"
                           f"💼 {pos}\n\n"
                           f"🔗 [OTWÓRZ W APLIKACJI]({job_url})")
                    
                    send_msg(msg)
                    print(f"[{datetime.now(warsaw_tz).strftime('%H:%M:%S')}] ✅ Wysłano: {address}", flush=True)

    except Exception as e:
        print(f"⚠️ Błąd pętli: {e}", flush=True)

keep_alive()
print("🚀 START: Strategia Kolegi (Snajper 75 + Auto-Token)", flush=True)
while True:
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    if 6 <= now.hour <= 23:
        check_offers()
        # Bardzo krótka przerwa, bo robimy tylko 1 zapytanie
        time.sleep(random.randint(6, 10))
    else:
        time.sleep(300)
