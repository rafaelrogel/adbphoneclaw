#!/usr/bin/env python3
"""Explore8: library/my-songs, clica musica recente, dump botoes download."""
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

    # lista musicas com href
    songs = pg.evaluate("""(() => {
        const out=[];
        document.querySelectorAll('a[href*="/session/"]').forEach(a=>{
            const t=(a.innerText||'').trim().replace(/\\s+/g,' ').slice(0,60);
            out.push({href:a.getAttribute('href'), t});
        });
        return out.slice(0,15);
    })()""")
    print("MUSICAS (primeiras):")
    for s in songs: print(" -", s['t'], "|", s['href'])

    if not songs:
        print("Nenhuma musica achada em my-songs.")
        pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_mysongs.png")
        b.close()
        raise SystemExit

    # clica primeira
    first = songs[0]['href']
    pg.goto("https://www.flowmusic.app" + first, timeout=30000)
    pg.wait_for_timeout(5000)
    print("Abriu:", pg.url)

    info = pg.evaluate("""(() => {
        const out={aria:[],texts:[],links:[],hits:[]};
        document.querySelectorAll('button,a,[role=button]').forEach(e=>{
            const t=(e.innerText||'').trim();
            const al=(e.getAttribute('aria-label')||'').trim();
            const href=e.getAttribute('href')||'';
            if(t && t.length<40) out.texts.push(t);
            if(al) out.aria.push(al);
            if(href && (href.includes('download')||href.includes('.mp3')||href.includes('.wav'))) out.links.push(href);
        });
        document.querySelectorAll('[title], svg title').forEach(e=>{
            const tt=(e.getAttribute('title')||e.textContent||'').trim().toLowerCase();
            if(tt && (tt.includes('download')||tt.includes('export')||tt.includes('save')||tt.includes('mp3')||tt.includes('wav')||tt.includes('share'))) out.hits.push(tt);
        });
        // pega todas as imagens/svg com classe que sugera download
        document.querySelectorAll('svg').forEach(s=>{
            const cls=(s.getAttribute('class')||'')+' '+(s.parentElement?.getAttribute('class')||'');
            if(/download|export|save|share|ellipsis|more|dots/i.test(cls)) out.svgcls=out.svgcls||[]; out.svgcls=(out.svgcls||[]); out.svgcls.push(cls.slice(0,60));
        });
        return out;
    })()""")
    print("ARIA:", info.get('aria', [])[:40])
    print("TEXTS:", info.get('texts', [])[:40])
    print("LINKS download:", info.get('links', []))
    print("HITS title:", info.get('hits', []))
    print("SVG classes:", list(set(info.get('svgcls', [])))[:30])

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_songpage2.png")
    print("screenshot: producer_songpage2.png")
    b.close()
