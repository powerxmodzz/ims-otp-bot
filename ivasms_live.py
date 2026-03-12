import time
import logging
import re
import os
import json
import threading
from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests

# ── Try to import socketio ──
try:
    import socketio as sio_lib
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

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

# Socket.IO endpoints to try
SOCKETIO_HOSTS = [
    "https://www.ivasms.com:2087",
    "https://www.ivasms.com",
    "http://www.ivasms.com:2087",
    "http://www.ivasms.com:3000",
    "http://www.ivasms.com:8080",
]

SOCKETIO_PATHS = [
    "/socket.io",
    "/ws",
    "/live",
    "/portal/live/socket.io",
]

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

    for _ in range(5):
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
                log.error(f"TG error {r.status_code}")
                return False
        except Exception as e:
            log.error(f"TG fail: {e}")
            time.sleep(3)
    return False

# ────────── LOGIN ──────────
_cookies = {}

def do_login():
    global _cookies
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
            # Save cookies for Socket.IO
            _cookies = dict(session.cookies)
            log.info(f"✅ Login OK! Cookies: {list(_cookies.keys())}")
            return True
        log.error("❌ Login failed!")
        return False
    except Exception as e:
        log.error(f"Login error: {e}")
        return False

# ────────── PROCESS INCOMING SMS ──────────
def process_sms(data):
    """Handle any incoming SMS data from Socket.IO"""
    log.info(f"📨 Raw Socket.IO data: {str(data)[:300]}")

    try:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                # Try to extract directly from string
                number_m = re.search(r'\b(\d{8,15})\b', data)
                otp      = extract_otp(data)
                if number_m and otp:
                    send_telegram("Unknown", number_m.group(1), detect_service(data), otp)
                return

        if isinstance(data, dict):
            number  = str(data.get("number") or data.get("phone") or data.get("msisdn") or "")
            message = str(data.get("message") or data.get("sms") or data.get("body") or data.get("msg") or "")
            country = str(data.get("country") or data.get("country_name") or "Unknown")
            service = str(data.get("sender") or data.get("service") or data.get("from") or "")
            number  = re.sub(r'\D', '', number)

            if not number or not message:
                # Try to find in nested structure
                log.info(f"  Dict keys: {list(data.keys())}")
                for k, v in data.items():
                    log.info(f"  {k}: {str(v)[:80]}")
                return

            otp = extract_otp(message)
            if not otp:
                log.info(f"  No OTP in: {message[:80]}")
                return

            if is_seen(number, otp):
                return

            srv = detect_service(service + " " + message)
            log.info(f"⚡ LIVE: +{number} | OTP={otp} | {srv}")
            send_telegram(country, number, srv, otp)

        elif isinstance(data, list):
            for item in data:
                process_sms(item)

    except Exception as e:
        log.error(f"process_sms error: {e} | data={str(data)[:200]}")

# ────────── SOCKET.IO CONNECTION ──────────
_sio_connected = False
_sio_client    = None

def try_socketio_connect(host, path):
    global _sio_connected, _sio_client

    log.info(f"🔌 Trying Socket.IO: {host}{path}")

    try:
        sio = sio_lib.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,
            reconnection_attempts=3,
            reconnection_delay=5,
        )

        @sio.event
        def connect():
            global _sio_connected
            _sio_connected = True
            log.info(f"✅ Socket.IO connected: {host}{path}")
            # Try common room join events
            for event in ["join", "subscribe", "auth", "login"]:
                try:
                    sio.emit(event, {"user": USERNAME, "cookies": _cookies})
                except:
                    pass

        @sio.event
        def disconnect():
            global _sio_connected
            _sio_connected = False
            log.warning(f"⚠ Socket.IO disconnected: {host}{path}")

        @sio.event
        def connect_error(data):
            log.error(f"❌ Socket.IO connect error: {data}")

        # Listen to ALL possible event names
        SMS_EVENTS = [
            "sms", "new_sms", "live_sms", "message", "otp",
            "receive", "incoming", "data", "update", "push",
            "sms_received", "new_message", "live", "broadcast",
        ]

        for event_name in SMS_EVENTS:
            def make_handler(name):
                @sio.on(name)
                def handler(data):
                    log.info(f"📡 Event '{name}': {str(data)[:200]}")
                    process_sms(data)
            make_handler(event_name)

        # Catch-all
        @sio.on("*")
        def catch_all(event, data):
            log.info(f"📡 Any event '{event}': {str(data)[:200]}")
            process_sms(data)

        # Build cookie header string
        cookie_str = "; ".join([f"{k}={v}" for k, v in _cookies.items()])

        sio.connect(
            host,
            socketio_path=path.lstrip("/"),
            headers={
                "Cookie":  cookie_str,
                "Referer": LIVE_URL,
                "Origin":  "https://www.ivasms.com",
            },
            transports=["websocket", "polling"],
            wait_timeout=10,
        )

        _sio_client = sio
        return sio

    except Exception as e:
        log.warning(f"  Failed {host}{path}: {type(e).__name__}: {str(e)[:100]}")
        return None

def start_socketio():
    """Try all host+path combinations"""
    if not HAS_SOCKETIO:
        log.error("❌ python-socketio not installed!")
        return None

    for host in SOCKETIO_HOSTS:
        for path in SOCKETIO_PATHS:
            sio = try_socketio_connect(host, path)
            if sio and _sio_connected:
                log.info(f"✅ Socket.IO working: {host}{path}")
                return sio
            time.sleep(1)

    log.warning("⚠ All Socket.IO attempts failed")
    return None

# ════════════════════════════════════════
#                MAIN
# ════════════════════════════════════════
log.info("=" * 55)
log.info("  IvaSMS LIVE OTP Bot — Socket.IO Mode")
log.info("=" * 55)

if not do_login():
    log.error("❌ Cannot login. Exiting.")
    exit(1)

if not HAS_SOCKETIO:
    log.error("❌ python-socketio package missing!")
    log.error("   Add 'python-socketio[client]' to requirements.txt")
    exit(1)

log.info(f"🔌 Starting Socket.IO connection...")
sio_client = start_socketio()

if sio_client and _sio_connected:
    log.info("✅ Socket.IO live — waiting for SMS events...")
    try:
        # Keep alive
        while True:
            if not _sio_connected:
                log.warning("🔄 Reconnecting Socket.IO...")
                sio_client = start_socketio()
            time.sleep(10)
    except KeyboardInterrupt:
        log.info("⛔ Stopped")
        if sio_client:
            sio_client.disconnect()
else:
    log.error("❌ Socket.IO could not connect to any endpoint.")
    log.error("   ivasms.com is blocking Railway datacenter IPs.")
    log.error("   Solution: Use Residential Proxy or run on Termux/Home server.")
    # Keep running so Railway doesn't crash-loop
    while True:
        log.info("💤 Waiting... (Socket.IO blocked by server)")
        time.sleep(60)
