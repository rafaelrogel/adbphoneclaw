#!/usr/bin/env python3
"""Loga todas as requests ao carregar sessao -> acha backend (supabase/api)."""
import subprocess, time, os, re
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
SESSION = "/session/bca9013e-1cb9-40ca-af42-51956213fd3f"

reqs = []
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
        u = req.url
        if any(k in u for k in ["supabase","/api/","rest/v1","storage","edge","functions",".co/"]):
            reqs.append(u)
            print("REQ:", u[:160])
    pg.on("request", on_req)
    pg.goto("https://www.flowmusic.app" + SESSION, timeout=30000)
    pg.wait_for_timeout(7000)
    # tambem roda um play
    pg.evaluate("""(() => { const b=[...document.querySelectorAll('button,[role=button]')]; const p=b.find(x=>(x.getAttribute('aria-label')||'').toLowerCase().includes('play')||(x.innerText||'').includes('Play')); if(p)p.click(); })()""")
    pg.wait_for_timeout(5000)

print(f"\n=== {len(reqs)} backend requests ===")
# salva pra analise
with open("/home/rafael/.openclaw/workspace/tools/api_reqs.txt","w") as f:
    for r in reqs: f.write(r+"\n")
print("salvo tools/api_reqs.txt")
b.close()
