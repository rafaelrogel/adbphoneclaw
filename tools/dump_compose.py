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
    # expande Lyrics, Sound, Details
    pg.evaluate("""(() => {
        document.querySelectorAll('button').forEach(b=>{
            const l=(b.getAttribute('aria-label')||'').toLowerCase();
            if((l.includes('lyrics')||l.includes('sound')||l.includes('details'))&&l.includes('expand')) b.click();
        });
    })()""")
    pg.wait_for_timeout(2000)
    html = pg.content()
    open("/home/rafael/.openclaw/workspace/tools/compose.html","w").write(html)
    print("HTML len:", len(html))
    try: b.close()
    except Exception: pass
