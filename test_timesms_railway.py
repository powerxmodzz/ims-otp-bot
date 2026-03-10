import re, time
from bs4 import BeautifulSoup
from curl_cffi import requests as req

USERNAME = "BkOTPZone"
PASSWORD = "pass@BKM581"
LOGIN_URL  = "http://www.timesms.net/login"
REPORT_URL = "http://www.timesms.net/agent/SMSCDRStats"

session = req.Session(impersonate="chrome120")

print("GET login page...")
r1 = session.get(LOGIN_URL, timeout=20)
print(f"Status: {r1.status_code} | Cookies: {dict(session.cookies)}")

soup = BeautifulSoup(r1.text, "html.parser")

# Captcha solve
captcha_text = ""
for tag in soup.find_all(string=re.compile(r'\d+\s*[+\-]\s*\d+')):
    captcha_text = str(tag).strip()
    break
m = re.search(r'(\d+)\s*([+\-])\s*(\d+)', captcha_text)
answer = 0
if m:
    a,op,b = int(m.group(1)),m.group(2),int(m.group(3))
    answer = a+b if op=='+' else a-b
    print(f"Captcha: {a}{op}{b} = {answer}")

print(f"POST login...")
r2 = session.post(LOGIN_URL,
    data={"username": USERNAME, "password": PASSWORD, "capt": str(answer)},
    headers={
        "Referer": LOGIN_URL,
        "Origin": "http://www.timesms.net",
        "Content-Type": "application/x-www-form-urlencoded",
    },
    timeout=20, allow_redirects=True)

print(f"Status: {r2.status_code} | URL: {r2.url}")
print(f"Cookies: {dict(session.cookies)}")
print(f"Set-Cookie: {r2.headers.get('Set-Cookie','none')}")

if "login" not in r2.url.lower() or "logout" in r2.text.lower():
    print("LOGIN OK!")
else:
    print("FAILED - checking response...")
    # Check JS redirect
    js_redirect = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", r2.text)
    meta_redirect = re.search(r'<meta[^>]+url=([^\s"\']+)', r2.text, re.IGNORECASE)
    if js_redirect:
        print(f"JS redirect to: {js_redirect.group(1)}")
    if meta_redirect:
        print(f"Meta redirect to: {meta_redirect.group(1)}")
    print(r2.text[:300])

time.sleep(1)
print("\nReport page...")
r3 = session.get(REPORT_URL, timeout=20)
print(f"Status: {r3.status_code} | URL: {r3.url}")

soup3 = BeautifulSoup(r3.text, "html.parser")
table = soup3.find("table")
if table:
    rows = table.select("tbody tr")
    print(f"Table rows: {len(rows)}")
    for i,tr in enumerate(rows[:3]):
        texts = [td.get_text(" ",strip=True)[:40] for td in tr.find_all("td")]
        print(f"Row{i+1}: {texts}")
else:
    print("No table")
    print(soup3.get_text()[:300])

print("DONE!")
