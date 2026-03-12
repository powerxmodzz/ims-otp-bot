import time
import logging
import re
import os
from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests
from collections import deque

# ────────── LOGGING ──────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ────────── CONFIG ──────────
USERNAME         = os.getenv("IVASMS_USER", "powerxdeveloper@gmail.com")
PASSWORD         = os.getenv("IVASMS_PASS", "Khang1.com")
TELEGRAM_TOKEN   = os.getenv("TG_TOKEN",    "8784790380:AAGX5vI90BLUnSGATdhzVuH9YeBqBGEveWs")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID",  "-1003886766454")

LOGIN_URL    = "https://www.ivasms.com/login"
LIVE_URL     = "https://www.ivasms.com/portal/live/my_sms"

POLL_INTERVAL = 3  # seconds

# ────────── SESSION ──────────
session = cf_requests.Session(impersonate="chrome120")

# ────────── SEEN (memory only) ──────────
seen_keys = set()

def make_key(number, otp):
    return f"{number}:{otp}"

def is_seen(number, otp):
    k = make_key(number, otp)
    if k in seen_keys:
        return True
    seen_keys.add(k)
    return False

# ────────── OTP EXTRACT ──────────
def extract_otp(text):
    # Format: 598-909 or 123 456
    m = re.search(r'\b(\d{3}[-\s]\d{3})\b', text)
    if m: return m.group(1)
    # Google: G-123456
    m = re.search(r'\bG-(\d{4,8})\b', text)
    if m: return "G-" + m.group(1)
    # OTP keywords
    m = re.search(
        r'(?:code|otp|pin|kode|codigo|codice|код|رمز|كود|verif|confirm|one.time|'
        r'einmal|dogrulama|passcode|password|senha|sifre|token|номер)'
        r'[^0-9]{0,20}(\d{4,8})',
        text, re.IGNORECASE
    )
    if m: return m.group(1)
    # colon/equals: "is: 1234"
    m = re.search(r'[:=]\s*(\d{4,8})\b', text)
    if m: return m.group(1)
    # hashtag: #123456
    m = re.search(r'#(\d{4,8})\b', text)
    if m: return m.group(1)
    # standalone 4-8 digits
    for match in re.findall(r'\b(\d{4,8})\b', text):
        if not re.match(r'^(19|20)\d{2}$', match):
            return match
    return None

# ────────── SERVICE DETECT ──────────
SERVICES = [
    "whatsapp","telegram","facebook","instagram","google","microsoft",
    "apple","paypal","binance","uber","amazon","netflix","tiktok",
    "twitter","snapchat","bybit","okx","kucoin","discord","linkedin",
    "signal","viber","line","wechat","yahoo","outlook","coinbase",
    "kraken","huobi","gate","mexc","bitget","crypto","trust","metamask",
    "airbnb","grab","lyft","shopee","lazada","alibaba","ebay","steam",
    "riot","epic","roblox","revolut","wise","skrill","stripe","cashapp",
    "venmo","zoom","slack","teams","dropbox","spotify","tinder","bumble",
]

def detect_service(text):
    tl = text.lower()
    for s in SERVICES:
        if s in tl:
            return s.title()
    return "Unknown"

# ────────── NUMBER MASK ──────────
def mask_number(n):
    n = re.sub(r'\D', '', str(n))
    return (n[:3] + "****" + n[-3:]) if len(n) >= 8 else n

# ────────── COUNTRY FLAGS ──────────
FLAGS = {
    "afghanistan":"🇦🇫","albania":"🇦🇱","algeria":"🇩🇿","argentina":"🇦🇷",
    "armenia":"🇦🇲","australia":"🇦🇺","austria":"🇦🇹","azerbaijan":"🇦🇿",
    "bahrain":"🇧🇭","bangladesh":"🇧🇩","belarus":"🇧🇾","belgium":"🇧🇪",
    "bolivia":"🇧🇴","brazil":"🇧🇷","bulgaria":"🇧🇬","cambodia":"🇰🇭",
    "canada":"🇨🇦","chile":"🇨🇱","china":"🇨🇳","colombia":"🇨🇴",
    "croatia":"🇭🇷","czech":"🇨🇿","denmark":"🇩🇰","egypt":"🇪🇬",
    "ethiopia":"🇪🇹","finland":"🇫🇮","france":"🇫🇷","germany":"🇩🇪",
    "ghana":"🇬🇭","greece":"🇬🇷","hungary":"🇭🇺","india":"🇮🇳",
    "indonesia":"🇮🇩","iran":"🇮🇷","iraq":"🇮🇶","ireland":"🇮🇪",
    "israel":"🇮🇱","italy":"🇮🇹","japan":"🇯🇵","jordan":"🇯🇴",
    "kazakhstan":"🇰🇿","kenya":"🇰🇪","kuwait":"🇰🇼","malaysia":"🇲🇾",
    "mexico":"🇲🇽","morocco":"🇲🇦","myanmar":"🇲🇲","nepal":"🇳🇵",
    "netherlands":"🇳🇱","nigeria":"🇳🇬","norway":"🇳🇴","oman":"🇴🇲",
    "pakistan":"🇵🇰","palestine":"🇵🇸","peru":"🇵🇪","philippines":"🇵🇭",
    "poland":"🇵🇱","portugal":"🇵🇹","qatar":"🇶🇦","romania":"🇷🇴",
    "russia":"🇷🇺","saudi arabia":"🇸🇦","senegal":"🇸🇳","serbia":"🇷🇸",
    "singapore":"🇸🇬","somalia":"🇸🇴","south africa":"🇿🇦","south korea":"🇰🇷",
    "spain":"🇪🇸","sri lanka":"🇱🇰","sweden":"🇸🇪","switzerland":"🇨🇭",
    "taiwan":"🇹🇼","thailand":"🇹🇭","tunisia":"🇹🇳","turkey":"🇹🇷",
    "ukraine":"🇺🇦","uae":"🇦🇪","united arab":"🇦🇪","uk":"🇬🇧",
    "united kingdom":"🇬🇧","usa":"🇺🇸","united states":"🇺🇸",
    "uzbekistan":"🇺🇿","venezuela":"🇻🇪","vietnam":"🇻🇳","yemen":"🇾🇪",
}

def get_flag(country):
    c = country.lower().strip()
    if c in FLAGS: return FLAGS[c]
    for k, v in FLAGS.items():
        if k in c: return v
    return "🌍"

# ────────── TELEGRAM SEND ──────────
_last_sent = 0

def send_telegram(country, number, service, otp):
    global _last_sent

    # Rate limit: min 0.5s between messages
    diff = time.time() - _last_sent
    if diff < 0.5:
        time.sleep(0.5 - diff)

    flag   = get_flag(country)
    masked = mask_number(number)
    iso    = re.sub(r'[^A-Z]', '', country.upper())[:2] or "XX"

    msg = (
        f"<b>┊°°°✅ 𝐋𝐈𝐕𝐄 𝐎𝐓𝐏 ✅°°°┊</b>\n"
        f"<blockquote>"
        f"{flag} <b>#{iso}</b>  <code>+{masked}</code>\n"
        f"🟢 <b>#CLI</b>  {service.upper()}"
        f"</blockquote>"
    )
    markup = {
        "inline_keyboard": [
            [{"text": f"🔑  {otp}  🔑", "copy_text": {"text": otp}}],
            [{"text": "📞 NUMBERS", "url": "https://t.me/dp_numbers"},
             {"text": "🔰 BACKUP",  "url": "https://t.me/powerotpbackup"}]
        ]
    }

    for attempt in range(5):
        try:
            r = cf_requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id":      TELEGRAM_CHAT_ID,
                    "text":         msg,
                    "parse_mode":   "HTML",
                    "reply_markup": markup
                },
                timeout=15
            )
            if r.status_code == 200:
                _last_sent = time.time()
                log.info(f"🚀 Sent: OTP={otp} | +{masked} | {service} | {flag}")
                return True
            elif r.status_code == 429:
                wait = r.json().get("parameters", {}).get("retry_after", 10)
                log.warning(f"⏳ TG rate limit, waiting {wait}s")
                time.sleep(wait + 2)
            else:
                log.error(f"TG error {r.status_code}: {r.text[:200]}")
                return False
        except Exception as e:
            log.error(f"TG exception: {e}")
            time.sleep(3)
    return False

# ────────── LOGIN ──────────
def do_login():
    log.info("🌐 Logging in...")
    try:
        resp = session.get(LOGIN_URL, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        csrf_inp = soup.find("input", {"name": "_token"})
        csrf     = csrf_inp["value"] if csrf_inp else ""

        r2 = session.post(LOGIN_URL, data={
            "_token":   csrf,
            "email":    USERNAME,
            "password": PASSWORD,
        }, headers={
            "Referer":      LOGIN_URL,
            "Origin":       "https://www.ivasms.com",
            "Content-Type": "application/x-www-form-urlencoded",
        }, timeout=30)

        if "logout" in r2.text.lower() or "dashboard" in r2.text.lower():
            log.info("✅ Login successful!")
            return True
        else:
            log.error("❌ Login failed!")
            return False
    except Exception as e:
        log.error(f"Login error: {e}")
        return False

# ────────── PARSE LIVE PAGE ──────────
_debug_done = False  # sirf ek baar HTML dump karein

def parse_live_page(html):
    global _debug_done
    soup = BeautifulSoup(html, "html.parser")
    results = []

    rows = soup.select("table tbody tr")
    log.info(f"🔍 Live page: {len(html)} bytes | rows={len(rows)}")

    # ── DEBUG: pehli baar full row structure log karo ──
    if not _debug_done and rows:
        _debug_done = True
        log.info("═" * 60)
        log.info("🛠 DEBUG — First 3 rows structure:")
        for i, tr in enumerate(rows[:3]):
            tds = tr.find_all("td")
            log.info(f"  ROW {i+1} ({len(tds)} cols):")
            for j, td in enumerate(tds):
                log.info(f"    TD[{j}]: '{td.get_text(' ', strip=True)[:80]}'")
        log.info("═" * 60)

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        texts = [td.get_text(" ", strip=True) for td in tds]

        number  = None
        country = ""
        service = ""
        message = ""

        for i, txt in enumerate(texts):
            nm = re.search(r'\b(\d{8,15})\b', txt)
            if nm and not number:
                number  = nm.group(1)
                country = re.sub(r'\d+', '', txt).strip()
                if not country and i > 0:
                    country = re.sub(r'\d+', '', texts[i-1]).strip()

        message = max(texts, key=len) if texts else ""

        for txt in texts:
            if txt and not re.search(r'\d{6,}', txt) and len(txt) < 50 and txt != message:
                service = txt
                break

        if not service:
            service = detect_service(message)

        if number and message and len(message) > 3:
            results.append((country or "Unknown", number, service, message))
            log.info(f"  ✅ Found: +{number} | {service} | {message[:50]}")
        else:
            log.info(f"  ⚠ Skip row: number={number} | msg_len={len(message)}")

    return results

# ────────── FETCH LIVE PAGE ──────────
_login_attempts = 0

def fetch_live():
    global _login_attempts
    try:
        resp = session.get(LIVE_URL, timeout=20)

        # If redirected to login, re-login
        if "login" in resp.url or "logout" not in resp.text.lower():
            if _login_attempts < 3:
                _login_attempts += 1
                log.warning("⚠️ Session expired, re-logging in...")
                if do_login():
                    _login_attempts = 0
                    resp = session.get(LIVE_URL, timeout=20)
                else:
                    return []
            else:
                log.error("❌ Too many login failures")
                return []

        _login_attempts = 0
        return parse_live_page(resp.text)

    except Exception as e:
        log.error(f"Fetch error: {e}")
        return []

# ════════════════════════════════════════
#                 MAIN
# ════════════════════════════════════════
log.info("=" * 50)
log.info("  IvaSMS LIVE OTP Bot — Starting...")
log.info("=" * 50)

if not do_login():
    log.error("❌ Cannot login. Exiting.")
    exit(1)

log.info(f"🟢 LIVE POLLING every {POLL_INTERVAL}s — URL: {LIVE_URL}")
log.info("=" * 50)

new_count = 0
poll_count = 0

try:
    while True:
        poll_count += 1
        entries = fetch_live()

        for country, number, service, message in entries:
            otp = extract_otp(message)
            if not otp:
                continue
            if is_seen(number, otp):
                continue

            detected_service = detect_service(service + " " + message)
            log.info(f"⚡ NEW LIVE OTP: +{number} | OTP={otp} | {detected_service}")
            send_telegram(country, number, detected_service, otp)
            new_count += 1

        if poll_count % 20 == 0:
            log.info(f"📊 Status: {poll_count} polls | {new_count} OTPs sent | seen={len(seen_keys)}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    log.info("⛔ Stopped by user")
