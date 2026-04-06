import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import cloudscraper
from unidecode import unidecode
from flask import Flask
import threading

# ==========================================
# KONFIGURACJA
# ==========================================
TELEGRAM_TOKEN = "8603328307:AAGCdHPSlh-a39UzYiQTKwE4UTMUxACBTsw"
MY_CHAT_ID = "6327998362"
BEARER_TOKEN = "6a31ad15947306ca97601ddef5913326de268e51"

LAT = 53.379360370518434
LNG = 14.64955069417926
API_URL = f"https://commissions.tikrow.com/list?page=1&range=30&state=available&newList=true&perPage=75&lat={LAT}&lng={LNG}"

scraper = cloudscraper.create_scraper()
seen_ids = set()
warsaw_tz = ZoneInfo("Europe/Warsaw")

DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

# --- SERWER DLA CHMURY (RENDER/RAILWAY) ---
app = Flask('')
@app.route('/')
def home(): return "Szybki Bot Tikrow (Hybrydowy Filtr) działa!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive(): threading.Thread(target=run, daemon=True).start()

# --- FUNKCJE POMOCNICZE ---
def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: scraper.post(url, data={"chat_id": MY_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except: pass

def normalize_text(text: str) -> str:
    """Uniwersalna funkcja czyszcząca tekst z polskich znaków i dużych liter"""
    if not text: return ""
    return unidecode(str(text)).lower().strip()

def format_ts(ts, only_time=False):
    try:
        dt = datetime.fromtimestamp(int(ts), warsaw_tz)
        if only_time: return dt.strftime("%H:%M")
        dzien_pl = DNI_PL.get(dt.strftime("%A"), dt.strftime("%A"))
        return f"{dt.strftime('%d.%m')} ({dzien_pl})"
    except: return "??"

# --- GŁÓWNA LOGIKA ---
def check_offers():
    now_time = datetime.now(warsaw_tz)
    
    if 0 <= now_time.hour < 6:
        time.sleep(60)
        return

    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "X-Instance": "1",
        "X-Version": "3.1.8",
        "Accept": "application/json"
    }

    try:
        res = scraper.get(API_URL, headers=headers, timeout=15)
        
        if res.status_code == 401:
            print(f"[{datetime.now(warsaw_tz).strftime('%H:%M:%S')}] 🔑 Token wygasł!")
            return
            
        if res.status_code != 200:
            return

        data = res.json()
        items = data.get("_embedded", {}).get("commissions", [])
        
        count_new = 0
        for item in items:
            oid = item.get("id")
            
            if oid and oid not in seen_ids:
                seen_ids.add(oid)
                
                # Pobieramy dane zlecenia
                address = item.get("customer_address", "")
                city = item.get("customer_city", "")
                position = item.get("position", "")
                
                # Czyścimy dane z ogonków (ł, ś, ą) i wielkich liter do łatwego porównania
                norm_addr = normalize_text(address)
                norm_city = normalize_text(city)
                norm_pos = normalize_text(position)
                
                # ==========================================
                # BRAMKI LOGICZNE (NOWY FILTR)
                # ==========================================
                is_walecznych = "walecznych 64" in norm_addr
                is_szczecin = "szczecin" in norm_city
                is_kasy = "kasy samoobslugowe" in norm_pos
                
                # Zezwól na powiadomienie JEŚLI to Walecznych LUB (to Szczecin i praca na kasach)
                if is_walecznych or (is_szczecin and is_kasy):
                    count_new += 1
                    
                    firm = item.get("customer", "Tikrow")
                    full_address = f"{city}, {address}" if city.lower() not in address.lower() else address
                    start_ts = item.get("start_date")
                    end_ts = item.get("end_date")
                    rate = item.get("rate_total", "?")
                    
                    job_url = f"https://partner.tikrow.com/user-commissions/{oid}/details"
                    
                    msg = (f"🚀 *NOWA OFERTA*\n\n"
                           f"📋 *{position}*\n"
                           f"🏢 {firm}\n"
                           f"📍 {full_address}\n"
                           f"📅 *{format_ts(start_ts)}*\n"
                           f"⏰ *{format_ts(start_ts, True)} - {format_ts(end_ts, True)}*\n"
                           f"💰 *{rate} zł*\n\n"
                           f"🔗 [SZCZEGÓŁY]({job_url})")
                    
                    send_msg(msg)

        now_str = datetime.now(warsaw_tz).strftime('%H:%M:%S')
        if count_new > 0:
            print(f"[{now_str}] 🚀 Wysłano {count_new} ofert (Filtr: Walecznych / Kasy)!")
        else:
            print(f"[{now_str}] 🆗 System OK. Sprawdzono {len(items)} ofert z okolicy.")
                
    except Exception as e:
        print(f"[{datetime.now(warsaw_tz).strftime('%H:%M:%S')}] ⚠️ Błąd: {e}")

# --- START ---
if __name__ == "__main__":
    print("🚀 TIKROW BOT (Hybrydowy Filtr Stanowisk) - URUCHOMIONY")
    keep_alive()
    
    while True:
        check_offers()
        time.sleep(5)
