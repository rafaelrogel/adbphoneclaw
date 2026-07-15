#!/usr/bin/env python3
"""Capture ALL responses during play, find audio binary."""
import subprocess, time, os, re, json
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
OUT = "/home/rafael/.openclaw/workspace/output"
os.makedirs(OUT, exist_ok=True)
SESSION = "/session/bca9013e-1cb9-40ca-af42-51956213fd3f"

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()

    all_resp = []
    def on_resp(resp):
        try:
            ct = resp.headers.get("content-type", "")
            cl = resp.headers.get("content-length", "")
            url = resp.url
            # foca em coisas grandes ou com palavra audio/track/song/file
            if ("audio" in ct or "video" in ct or "octet" in ct or
                re.search(r"\.(mp3|wav|ogg|m4a|flac|bin|zip)", url, re.I) or
                any(k in url.lower() for k in ["track","song","audio","file","media","download","render","stem"])):
                all_resp.append((url, ct, cl))
                print("RESP:", ct, "len="+str(cl), url[:140])
        except Exception:
            pass
    pg.on("response", on_resp)

    pg.goto("https://www.flowmusic.app" + SESSION, timeout=30000)
    pg.wait_for_timeout(5000)
    pg.evaluate("""(() => {
        const btns=[...document.querySelectorAll('button,[role=button]')];
        const pl=btns.find(x=>(x.getAttribute('aria-label')||'').toLowerCase().includes('play') || (x.innerText||'').includes('Play'));
        if(pl) pl.click();
    })()""")
    print("Play clicado. Capturando 12s...")
    time.sleep(12)

    print(f"\n=== {len(all_resp)} responses relevantes ===")
    # tenta baixar o maior (ou que parece audio)
    cand = None
    for url, ct, cl in all_resp:
        if "audio" in ct or "octet" in ct or re.search(r"\.(mp3|wav|m4a|flac)", url, re.I):
            cand = (url, ct)
            break
    if cand:
        url, ct = cand
        print("Baixando candidato:", url[:120])
        try:
            r = ctx.request.get(url)
            data = r.body()
            ext = ".mp3" if "mp3" in (ct+url).lower() else (".wav" if "wav" in (ct+url).lower() else ".bin")
            path = os.path.join(OUT, "captured1"+ext)
            with open(path,"wb") as f: f.write(data)
            print("SALVO:", path, len(data))
            import subprocess as sp
            rr = sp.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",path],capture_output=True,text=True)
            print("DURACAO:", rr.stdout.strip())
        except Exception as e:
            print("erro:", e)
    else:
        print("Nenhum candidato. Todas as URLs (debug):")
        for url, ct, cl in all_resp[:40]:
            print("  ", ct, url[:100])
    b.close()
