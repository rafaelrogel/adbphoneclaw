#!/usr/bin/env python3
import subprocess, time, os
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
SID = "bca9013e-1cb9-40ca-af42-51956213fd3f"
with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run","--no-default-browser-check"])
    ctx = b.new_context(viewport={"width":1440,"height":900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/session/"+SID, timeout=30000)
    pg.wait_for_timeout(5000)
    # clica botao com lucide-sparkles
    res = pg.evaluate("""(() => {
        const svg=[...document.querySelectorAll('svg.lucide-sparkles')];
        if(svg.length){ const btn=svg[0].closest('button,[role=button]')||svg[0].parentElement; btn.click(); return 'clicou sparkles'; }
        return 'sem sparkles';
    })()""")
    print("acao:", res)
    pg.wait_for_timeout(2000)
    txt = pg.evaluate("() => document.body.innerText")
    # procura palavras-chave
    for kw in ["Extend","extend","5 Minute","5 minute","Remix","Variation","Length","Duration","Make longer","Loop"]:
        if kw in txt:
            print("TEXTO contem:", kw)
    print("body texto (300 chars):", txt[:300].replace("\n"," | "))
    open("/home/rafael/.openclaw/workspace/tools/sparkle.html","w").write(pg.content())
    try: b.close()
    except Exception: pass
