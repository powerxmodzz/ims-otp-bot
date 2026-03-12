import time
import logging
import re
import os
import json
from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests

# ────────── LOGGING ──────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ────────── CONFIG ──────────
USERNAME         = os.getenv("IVASMS_USER", "powerxdeveloper@gmail.com")
PASSWORD         = os.getenv("IVASMS_PASS", "Khang1.com")
TELEGRAM_TOKEN   = os.getenv("TG_TOKEN",    "8784790380:AAGX5vI90BLUnSGATdhzVuH9YeBqBGEveWs")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID",  "-1003886766454")

LOGIN_URL = "https://www.ivasms.com/login"
LIVE_URL  = "https://www.ivasms.com/portal/live/my_sms"

POLL_INTERVAL = 3

# ────────── SESSION ──────────
session = cf_requests.Session(impersonate="chrome120")

# ────────── SEEN ──────────
seen_keys = set()

def is_seen(number, otp):
    k = f"{number}:{otp}"
    if k in seen_keys:
        return True
    seen_keys.add(k)
    return False

# ────────── OTP EXTRACT ──────────
def extract_otp(text):
    m = re.search(r'\b(\d{3}[-\s]\d{3})\b', text)
    if m: return m.group(1)
    m = re.search(r'\bG-(\d{4,8})\b', text)
    if m: return "G-" + m.group(1)
    m = re.search(
        r'(?:code|otp|pin|kode|codigo|codice|код|رمز|كود|verif|confirm|one.time|'
        r'einmal|dogrulama|passcode|password|senha|sifre|token|номер)'
        r'[^0-9]{0,20}(\d{4,8})',
        text, re.IGNORECASE
    )
    if m: return m.group(1)
    m = re.search(r'[:=]\s*(\d{4,8})\b', text)
    if m: return m.group(1)
    m = re.search(r'#(\d{4,8})\b', text)
    if m: return m.group(1)
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

def mask_number(n):
    n = re.sub(r'\D', '', str(n))
    return (n[:3] + "****" + n[-3:]) if len(n) >= 8 else n

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
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg,
                      "parse_mode": "HTML", "reply_markup": markup},
                timeout=15
            )
            if r.status_code == 200:
                _last_sent = time.time()
                log.info(f"🚀 Sent: OTP={otp} | +{masked} | {service} | {flag}")
                return True
            elif r.status_code == 429:
                wait = r.json().get("parameters", {}).get("retry_after", 10)
                time.sleep(wait + 2)
            else:
                log.error(f"TG error {r.status_code}: {r.text[:100]}")
                return False
        except Exception as e:
            log.error(f"TG fail: {e}")
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
            "_token": csrf, "email": USERNAME, "password": PASSWORD,
        }, headers={
            "Referer": LOGIN_URL, "Origin": "https://www.ivasms.com",
            "Content-Type": "application/x-www-form-urlencoded",
        }, timeout=30)

        if "logout" in r2.text.lower() or "dashboard" in r2.text.lower():
            log.info("✅ Login successful!")
            return True
        log.error("❌ Login failed!")
        return False
    except Exception as e:
        log.error(f"Login error: {e}")
        return False

# ────────── CSRF ──────────
_csrf_token = ""

def refresh_csrf():
    global _csrf_token
    try:
        resp = session.get(LIVE_URL, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")

        meta = soup.find("meta", {"name": "csrf-token"})
        if meta:
            _csrf_token = meta.get("content", "")
            return resp.text

        inp = soup.find("input", {"name": "_token"})
        if inp:
            _csrf_token = inp["value"]
            return resp.text

        for s in soup.find_all("script"):
            t = s.string or ""
            m = re.search(r"_token['\"]?\s*[,:]\s*['\"]([^'\"]{20,})['\"]", t)
            if m:
                _csrf_token = m.group(1)
                return resp.text

        return resp.text
    except Exception as e:
        log.error(f"CSRF error: {e}")
        return ""

# ────────── API PROBE ──────────
CANDIDATE_URLS = [
    "https://www.ivasms.com/portal/live/my_sms/data",
    "https://www.ivasms.com/portal/live/sms",
    "https://www.ivasms.com/portal/live/get",
    "https://www.ivasms.com/portal/live/data",
    "https://www.ivasms.com/portal/sms/live",
    "https://www.ivasms.com/api/live/sms",
    "https://www.ivasms.com/portal/live/my_sms/fetch",
    "https://www.ivasms.com/portal/live/fetch",
    "https://www.ivasms.com/portal/live/my_sms/json",
    "https://www.ivasms.com/portal/live/my_sms/list",
]

_working_url = None
_probe_done  = False

def probe_endpoints(page_html):
    global _working_url, _probe_done
    _probe_done = True

    # First scan JS for any URL hints
    soup = BeautifulSoup(page_html, "html.parser")
    found = []
    for script in soup.find_all("script"):
        t = script.string or ""
        for m in re.finditer(r'["\'](/portal/[^"\'?\s]{3,})["\']', t):
            u = "https://www.ivasms.com" + m.group(1)
            if u not in found:
                found.append(u)
                log.info(f"  JS URL found: {u}")

    # Add JS-found URLs to candidates
    all_urls = found + CANDIDATE_URLS

    hdrs = {
        "Referer":          LIVE_URL,
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN":     _csrf_token,
        "Accept":           "application/json, text/html, */*",
    }

    log.info(f"🔭 Probing {len(all_urls)} endpoints...")
    for url in all_urls:
        try:
            r = session.get(url, headers=hdrs, timeout=6)
            snippet = r.text[:120].replace('\n', ' ')
            log.info(f"  GET {url} → {r.status_code} | {len(r.text)}B | {snippet}")
            if r.status_code == 200 and len(r.text) > 20 and r.status_code != 404:
                _working_url = url
                log.info(f"✅ Working API: {url}")
                return
        except Exception as e:
            log.info(f"  {url} → {e}")

    log.warning("⚠ No direct API found — will rely on Socket.IO data or page fallback")

# ────────── PARSE JSON ──────────
def parse_json_sms(text):
    results = []
    try:
        data = json.loads(text)
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ["data", "sms", "messages", "records", "result", "items", "rows"]:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break

        log.info(f"📦 JSON items: {len(items)}")
        if items:
            log.info(f"  Keys: {list(items[0].keys())}")

        for item in items:
            number  = str(item.get("number") or item.get("phone") or item.get("msisdn") or "")
            message = str(item.get("message") or item.get("sms") or item.get("body") or item.get("text") or "")
            country = str(item.get("country") or item.get("country_name") or "Unknown")
            service = str(item.get("sender") or item.get("service") or item.get("from") or "")
            number  = re.sub(r'\D', '', number)
            if number and message:
                results.append((country, number, service or detect_service(message), message))
    except:
        pass
    return results

# ────────── MAIN FETCH ──────────
_poll_count    = 0
_login_attempts = 0

def fetch_live():
    global _poll_count, _login_attempts, _working_url, _probe_done

    _poll_count += 1
    page_html = refresh_csrf()

    if not page_html:
        return []

    # Check if session expired
    if "login" in page_html[:500].lower() and "logout" not in page_html.lower():
        if _login_attempts < 3:
            _login_attempts += 1
            log.warning("⚠ Session expired, re-logging...")
            if do_login():
                _login_attempts = 0
                page_html = refresh_csrf()
        else:
            log.error("❌ Too many login failures")
            return []

    # First time: probe API endpoints
    if not _probe_done:
        probe_endpoints(page_html)

    # Use working URL
    if _working_url:
        hdrs = {
            "Referer":          LIVE_URL,
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-TOKEN":     _csrf_token,
            "Accept":           "application/json, */*",
        }
        try:
            r = session.get(_working_url, headers=hdrs, timeout=10)
            if r.status_code == 200:
                results = parse_json_sms(r.text)
                if results:
                    return results
                # Try HTML parse on response
                return parse_html_fallback(r.text)
        except Exception as e:
            log.error(f"API fetch error: {e}")
            _working_url = None  # reset and re-probe next cycle

    # Fallback: direct page parse
    return parse_html_fallback(page_html)

def parse_html_fallback(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td")
        texts = [td.get_text(" ", strip=True) for td in tds if td.get_text(strip=True)]
        if not texts:
            continue
        full = " ".join(texts)
        nm = re.search(r'\b(\d{8,15})\b', full)
        if not nm:
            continue
        number  = nm.group(1)
        message = max(texts, key=len)
        results.append(("Unknown", number, detect_service(full), message))
        log.info(f"  HTML row: +{number} | {message[:50]}")

    return results

# ════════════════════════════════════════
#                MAIN
# ════════════════════════════════════════
log.info("=" * 55)
log.info("  IvaSMS LIVE OTP Bot — API Discovery Mode")
log.info("=" * 55)

if not do_login():
    log.error("❌ Cannot login. Exiting.")
    exit(1)

log.info(f"🟢 LIVE POLLING every {POLL_INTERVAL}s")
log.info("=" * 55)

new_count = 0

try:
    while True:
        try:
            entries = fetch_live()
            for country, number, service, message in entries:
                otp = extract_otp(message)
                if not otp:
                    continue
                if is_seen(number, otp):
                    continue
                srv = detect_service(service + " " + message)
                log.info(f"⚡ LIVE OTP: +{number} | OTP={otp} | {srv}")
                send_telegram(country, number, srv, otp)
                new_count += 1

            if _poll_count % 20 == 0:
                log.info(f"📊 {_poll_count} polls | {new_count} OTPs | url={_working_url}")

        except Exception as e:
            log.warning(f"Poll error: {e}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    log.info("⛔ Stopped")
