#!/usr/bin/env python3
"""Dumpar conteudo da secao Details (apos expandir via JS)."""
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
    pg.goto("https://www.flowmusic.app/session?t=true", timeout=30000)
    pg.wait_for_timeout(5000)
    pg.evaluate("""(() => {
        const btns=[...document.querySelectorAll('button')];
        const b=btns.find(x=>(x.getAttribute('aria-label')||'').includes('Details'));
        if(b) b.click();
    })()""")
    pg.wait_for_timeout(3000)

    # acha a secao Details e dumpar texto
    txt = pg.evaluate("""(() => {
        const secs=[...document.querySelectorAll('section,div')];
        for (const s of secs) {
            const lbl = (s.getAttribute('aria-label')||'').toLowerCase();
            if (lbl.includes('details')) {
                return s.innerText;
            }
        }
        return 'secao details nao achada';
    })()""")
    print("=== DETAILS SECTION TEXT ===")
    print(txt[:2000])

    # tambem dumpa todos os inputs/selects agora visiveis
    print("=== INPUTS/SELECTS ===")
    for el in pg.locator("input,select,textarea").all():
        try:
            tag = el.evaluate("e=>e.tagName")
            ph = el.get_attribute("placeholder") or ""
            aid = el.get_attribute("aria-label") or ""
            typ = el.get_attribute("type") or ""
            if ph or aid or tag=="SELECT" or typ in ("range","number"):
                print(f"<{tag}> type={typ} placeholder='{ph}' aria='{aid}'")
        except Exception:
            pass

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_details3.png")
    print("screenshot: producer_details3.png")
    b.close()
