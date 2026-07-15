#!/usr/bin/env python3
"""Loga TODAS as responses durante play; acha binario de audio pelo tamanho."""
import subprocess, time, os, re
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
OUT = "/home/rafael/.openclaw/workspace/output"
os.makedirs(OUT, exist_ok=True)
SESSION = "/session/bca9013e-1cb9-40ca-af42-51956213fd3f"

resps = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    def on_resp(resp):
        try:
            cl = int(resp.headers.get("content-length") or 0)
            ct = resp.headers.get("content-type","")
            url = resp.url
            resps.append((cl, ct, url))
        except Exception:
            pass
    pg.on("response", on_resp)
    pg.goto("https://www.flowmusic.app" + SESSION, timeout=30000)
    pg.wait_for_timeout(5000)
    pg.evaluate("""(() => { const b=[...document.querySelectorAll('button,[role=button]')]; const p=b.find(x=>(x.getAttribute('aria-label')||'').toLowerCase().includes('play')||(x.innerText||'').includes('Play')); if(p)p.click(); })()""")
    print("Play. Capturando 15s...")
    time.sleep(15)

print(f"=== {len(resps)} responses ===")
# ordena por tamanho desc
resps.sort(reverse=True)
for cl,ct,url in resps[:25]:
    print(f"{cl:>9}  {ct[:30]:30}  {url[:100]}")
# salva tudo
with open("/home/rafael/.openclaw/workspace/tools/all_resp.txt","w") as f:
    for cl,ct,url in resps:
        f.write(f"{cl}\t{ct}\t{url}\n")
print("salvo tools/all_resp.txt")
b.close()
