#!/usr/bin/env python3
"""Expande Details via JS e dumpar conteudo (procura duracao)."""
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

    # clica via JS
    print("JS click Expand Details...")
    try:
        pg.evaluate("""(() => {
            const btns = [...document.querySelectorAll('button')];
            const b = btns.find(x => (x.getAttribute('aria-label')||'').includes('Details'));
            if (b) { b.click(); return 'clicado: '+b.getAttribute('aria-label'); }
            return 'nao achou';
        })()""")
        pg.wait_for_timeout(3000)
        print("feito.")
    except Exception as e:
        print("erro JS click:", e)

    # agora dumpa texto de toda a pagina (via evaluate body.innerText)
    try:
        txt = pg.evaluate("document.body.innerText")
        # filtra linhas com palavras-chave
        for line in txt.split("\\n"):
            l = line.strip()
            if l and any(k in l.lower() for k in ["duration","min","length","second","segundo","duração","minute","sec"]):
                print("TXT:", repr(l[:80]))
    except Exception as e:
        print("erro innerText:", e)

    # procura elementos clicaveis com essas palavras (combobox/slider/etc)
    print("=== elementos com duration/min perto ===")
    try:
        html = pg.evaluate("""(() => {
            const out = [];
            document.querySelectorAll('*').forEach(e => {
                const t = (e.innerText||'').trim();
                if (t && t.length < 60 && /duration|min|length|second|minute|segundo|duração/i.test(t)) {
                    out.push(e.tagName + '|' + (e.getAttribute('role')||'') + '|' + t + '|cls=' + (e.className||'').slice(0,40));
                }
            });
            return out.slice(0,40);
        })()""")
        for h in html:
            print("EL:", h)
    except Exception as e:
        print("erro html scan:", e)

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_details2.png")
    print("screenshot: producer_details2.png")
    b.close()
