#!/usr/bin/env python3
"""Explore7: abre musica recente, mapeia botoes (download/export/share)."""
import subprocess, time, os, json
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

    # clica na primeira musica da lista (lateral)
    # acha elementos com texto de musica e clica
    clicked = pg.evaluate("""(() => {
        // procura itens de musica (links/buttons com titulo)
        const items=[...document.querySelectorAll('a,button')].filter(e=>{
            const t=(e.innerText||'').trim();
            return t.length>3 && t.length<60 && !/^(Songs|Playlists|Spaces|New session)$/.test(t);
        });
        if(items.length){ items[0].click(); return items[0].innerText.trim().slice(0,40); }
        return 'nenhum';
    })()""")
    print("Clicou item:", clicked)
    pg.wait_for_timeout(4000)
    print("URL agora:", pg.url)

    # dump botoes da pagina da musica
    info = pg.evaluate("""(() => {
        const out={aria:[],texts:[],links:[]};
        document.querySelectorAll('button,a,[role=button]').forEach(e=>{
            const t=(e.innerText||'').trim();
            const al=(e.getAttribute('aria-label')||'').trim();
            const href=e.getAttribute('href')||'';
            if(t && t.length<40) out.texts.push(t);
            if(al) out.aria.push(al);
            if(href) out.links.push(href.slice(0,80));
        });
        // procura svg com title download/export
        document.querySelectorAll('svg title, [title]').forEach(e=>{
            const tt=(e.getAttribute('title')||e.textContent||'').trim().toLowerCase();
            if(tt && (tt.includes('download')||tt.includes('export')||tt.includes('save')||tt.includes('mp3')||tt.includes('wav'))) out.hit=tt;
        });
        return out;
    })()""")
    print("ARIA:", info.get('aria', [])[:40])
    print("TEXTS:", info.get('texts', [])[:40])
    print("LINKS:", info.get('links', [])[:20])
    if info.get('hit'): print("HIT svg/title:", info['hit'])

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_songpage.png")
    print("screenshot: producer_songpage.png")
    b.close()
