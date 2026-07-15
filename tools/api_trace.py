#!/usr/bin/env python3
"""Trace todas chamadas /__api durante load da sessao; captura URL audio no response."""
import subprocess, time, os, re, json
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
SID = "bca9013e-1cb9-40ca-af42-51956213fd3f"

calls = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    def on_req(req):
        u=req.url
        if "/__api/" in u:
            calls.append({"method":req.method,"url":u,"resp":None})
    def on_resp(resp):
        u=resp.url
        if "/__api/" in u:
            try: body=resp.text()
            except Exception: body=""
            for c in calls:
                if c["url"]==u and c["resp"] is None:
                    c["resp"]=(resp.status, body); break
            # procura audio no body
            urls=re.findall(r'https?://[^\s"\',}]+', body)
            audio=[x for x in urls if re.search(r'\.(mp3|wav|ogg|m4a|flac)|audio|/file|storage\.googleapis|supabase', x, re.I)]
            if audio:
                print("AUDIO in", u[:80], "->", audio[:5])
    pg.on("request", on_req)
    pg.on("response", on_resp)
    pg.goto("https://www.flowmusic.app/library/my-songs", timeout=30000)
    pg.wait_for_timeout(8000)

print(f"\n=== {len(calls)} /__api calls ===")
for c in calls:
    st, body = c["resp"] or ("?","")
    print(f"{c['method']:4} {c['url'].replace('https://www.flowmusic.app','')[:90]} -> {st}")
    if body:
        print("    body[:200]:", body[:200].replace("\n"," "))
try: b.close()
except Exception: pass
