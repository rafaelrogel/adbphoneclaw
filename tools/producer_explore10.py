#!/usr/bin/env python3
"""Explore10: dump HTML do card de musica na biblioteca + procura download em hover."""
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
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/library/my-songs", timeout=30000)
    pg.wait_for_timeout(5000)

    # acha primeiro card de musica (link /session/) e seu container pai
    info = pg.evaluate("""(() => {
        const a=document.querySelector('a[href*="/session/"]');
        if(!a) return {err:'no link'};
        // sobe ate achar container com varios filhos (card)
        let el=a;
        for(let i=0;i<6;i++){ el=el.parentElement; if(el && el.querySelectorAll('button,svg,a').length>2) break; }
        const card=el||a;
        // lista botoes no card
        const btns=[...card.querySelectorAll('button,[role=button],a')].map(e=>({
            tag:e.tagName, aria:e.getAttribute('aria-label')||'', cls:(e.getAttribute('class')||'').slice(0,70), text:(e.innerText||'').trim().slice(0,20)
        }));
        return {html: card.outerHTML.slice(0,1500), btns};
    })()""")
    print("CARD HTML (primeiros 1500):")
    print(info.get('html',''))
    print("\nBOTOES NO CARD:")
    for b_ in info.get('btns',[]):
        print(" ", b_)

    # hover no card e re-scan botoes
    try:
        a0 = pg.locator('a[href*="/session/"]').first
        a0.hover()
        pg.wait_for_timeout(1500)
        info2 = pg.evaluate("""(() => {
            const a=document.querySelector('a[href*="/session/"]');
            let el=a; for(let i=0;i<6;i++){ el=el.parentElement; if(el && el.querySelectorAll('button,svg,a').length>2) break; }
            const card=el||a;
            return [...card.querySelectorAll('button,[role=button],a')].map(e=>({aria:e.getAttribute('aria-label')||'', cls:(e.getAttribute('class')||'').slice(0,50), text:(e.innerText||'').trim().slice(0,20)}));
        })()""")
        print("\nBOTOES APOS HOVER:")
        for b_ in info2: print(" ", b_)
    except Exception as e:
        print("hover err:", e)

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_library.png")
    b.close()
