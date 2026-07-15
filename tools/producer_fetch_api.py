#!/usr/bin/env python3
"""Extrai JWT do storage_state, chama __api com Bearer, acha URL audio."""
import subprocess, time, os, json, re, base64
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
SID = "bca9013e-1cb9-40ca-af42-51956213fd3f"

# extrai JWT (cookie sb-sb-auth-token.0/.1 = 'base64-'+b64, dividido)
ss = json.load(open(STORAGE))
raw0 = raw1 = ""
for c in ss.get("cookies", []):
    n = c.get("name", "")
    if n == "sb-sb-auth-token.0":
        raw0 = c["value"]
    elif n == "sb-sb-auth-token.1":
        raw1 = c["value"]
if raw0.startswith("base64-"):
    raw0 = raw0[len("base64-"):]
b64 = raw0 + raw1
b64 += '=' * (-len(b64) % 4)
try:
    decoded = json.loads(base64.b64decode(b64).decode())
    jwt = decoded.get("access_token")
    print("decoded keys:", list(decoded.keys())[:10])
except Exception as e:
    print("decode err:", e); jwt = None
print("JWT len:", len(jwt) if jwt else 0)

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/session/"+SID, timeout=30000)
    pg.wait_for_timeout(4000)

    headers = {"Authorization": f"Bearer {jwt}"} if jwt else {}
    ep = f"/__api/conversations/{SID}"
    r = ctx.request.get("https://www.flowmusic.app"+ep, headers=headers, timeout=15000)
    body = r.text()
    print(f"\n### {ep} -> {r.status} ({len(body)} bytes)")
    urls = re.findall(r'https?://[^\s"\']+', body)
    audio_like = [u for u in urls if re.search(r'\.(mp3|wav|ogg|m4a|flac)|audio|storage|supabase|googleapis|/file', u, re.I)]
    print("audio-like urls:", audio_like[:15])
    print("ALL urls (first 20):", urls[:20])
    print("preview:", body[:600].replace("\n"," "))
    try: b.close()
    except Exception: pass
