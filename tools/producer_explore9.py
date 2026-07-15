#!/usr/bin/env python3
"""Explore9: clica Share e Fullscreen, monitora download em cada."""
import subprocess, time, os
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
SESSION = "/session/bca9013e-1cb9-40ca-af42-51956213fd3f"

def click_and_watch(pg, label, js_find, out):
    print(f"\n--- {label} ---")
    try:
        with pg.expect_download(timeout=4000) as dl_info:
            pg.evaluate(js_find)
        dl = dl_info.value
        print(f"  >> DOWNLOAD disparado! {dl.suggested_filename}")
        path = os.path.join(out, label.replace(" ","_")+"_"+ (dl.suggested_filename or "x"))
        dl.save_as(path)
        print(f"  >> SALVO {path}")
    except Exception as e:
        print(f"  sem download ({type(e).__name__})")
    pg.wait_for_timeout(1500)

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE, accept_downloads=True)
    pg = ctx.new_page()
    out = "/home/rafael/.openclaw/workspace/output"
    os.makedirs(out, exist_ok=True)
    pg.goto("https://www.flowmusic.app" + SESSION, timeout=30000)
    pg.wait_for_timeout(5000)

    # 1) Share session
    click_and_watch(pg, "share", """(() => {
        const btns=[...document.querySelectorAll('button,[role=button]')];
        const s=btns.find(x=>(x.getAttribute('aria-label')||'').toLowerCase().includes('share'));
        if(s) s.click();
    })()""", out)
    # dump modal apos share
    modal = pg.evaluate("""(() => {
        const m=document.querySelector('[role=dialog],[class*=modal],[class*=Dialog]');
        return m? m.innerText.slice(0,300):'sem modal';
    })()""")
    print("Modal share texto:", modal)
    # fecha modal
    pg.keyboard.press("Escape"); pg.wait_for_timeout(1000)

    # 2) Fullscreen player
    click_and_watch(pg, "fullscreen", """(() => {
        const btns=[...document.querySelectorAll('button,[role=button]')];
        const f=btns.find(x=>{const c=(x.getAttribute('class')||''); return c.includes('maximize');});
        if(f) f.click();
    })()""", out)
    # dump apos fullscreen
    info = pg.evaluate("""(() => {
        const out={aria:[],texts:[]};
        document.querySelectorAll('button,[role=button]').forEach(e=>{
            const t=(e.innerText||'').trim(); const al=(e.getAttribute('aria-label')||'').trim();
            if(t&&t.length<30)out.texts.push(t); if(al)out.aria.push(al);
        });
        return out;
    })()""")
    print("Apos fullscreen ARIA:", info.get('aria',[])[:30])
    print("Apos fullscreen TEXTS:", info.get('texts',[])[:30])

    # tenta clicar qualquer botao com 'download'/'export'/'save'/'more' no fullscreen
    click_and_watch(pg, "fullscreen_btns", """(() => {
        const els=[...document.querySelectorAll('button,a,[role=button]')];
        const e=els.find(x=>{const low=((x.innerText||'')+' '+(x.getAttribute('aria-label')||'')).toLowerCase();
            return /download|export|save|baixar|more|ellipsis|\\.\\.\\./.test(low);});
        if(e){e.click();return true;} return false;
    })()""", out)

    pg.screenshot(path=f"{out}/explore9.png")
    b.close()
