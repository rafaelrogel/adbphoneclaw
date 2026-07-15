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
with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run","--no-default-browser-check"])
    ctx = b.new_context(viewport={"width":1440,"height":900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/session?t=true", timeout=30000)
    pg.wait_for_timeout(4000)
    pg.evaluate("""(() => { const btns=[...document.querySelectorAll('button')]; const b=btns.find(x=>{const l=(x.getAttribute('aria-label')||'').toLowerCase(); return l.includes('details')&&l.includes('expand');}); if(b)b.click(); })()""")
    pg.wait_for_timeout(1000)
    clicked = pg.evaluate("""(() => {
        const btns=[...document.querySelectorAll('button')];
        const b=btns.find(x=>x.getAttribute('aria-haspopup')==='dialog' && (x.getAttribute('data-state')==='closed'));
        if(b){ b.click(); return true; } return false;
    })()""")
    print("clicou dialog btn:", clicked)
    pg.wait_for_timeout(1500)
    open("/home/rafael/.openclaw/workspace/tools/details_dialog.html","w").write(pg.content())
    print("html salvo")
    try: b.close()
    except Exception: pass
