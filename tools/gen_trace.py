#!/usr/bin/env python3
"""Captura POST /__api/producer/tool-call: body req + resp, salva p/ analise."""
import subprocess, time, os, json, gzip, io
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
PROMPT = "Instrumental. About 5 minutes. Soft twilight ambient, warm pads, gentle slow swell. Seamless loop, no vocals, no drums."

def try_decode(b):
    for name,fn in [("utf8",lambda x:x.decode('utf-8','replace')),
                    ("gzip",lambda x:gzip.decompress(x).decode('utf-8','replace'))]:
        try:
            return name, fn(b)
        except Exception:
            pass
    return "hex", b[:200].hex()

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run","--no-default-browser-check"])
    ctx = b.new_context(viewport={"width":1440,"height":900},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    def on_req(req):
        if "/__api/producer/tool-call" in req.url:
            try: body=req.body() or b""
            except Exception: body=b""
            n,d=try_decode(body)
            print("REQ tool-call ("+n+"):", d[:800])
            with open("/home/rafael/.openclaw/workspace/tools/toolcall_req.bin","wb") as f: f.write(body)
    def on_resp(resp):
        if "/__api/producer/tool-call" in resp.url:
            try: body=resp.body()
            except Exception: body=b""
            n,d=try_decode(body)
            print("RESP tool-call ("+n+"):", d[:800])
            with open("/home/rafael/.openclaw/workspace/tools/toolcall_resp.bin","wb") as f: f.write(body)
    pg.on("request", on_req)
    pg.on("response", on_resp)
    pg.goto("https://www.flowmusic.app/session?t=true", timeout=30000)
    pg.wait_for_timeout(4000)
    pg.evaluate("""(() => { const btns=[...document.querySelectorAll('button')]; const b=btns.find(x=>{const l=(x.getAttribute('aria-label')||'').toLowerCase(); return l.includes('sound')&&l.includes('expand');}); if(b)b.click(); })()""")
    pg.wait_for_timeout(1000)
    pg.evaluate("""(val) => { const el=document.querySelector("textarea[aria-label='Sound description']"); const s=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set; s.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true})); }""", PROMPT)
    pg.wait_for_timeout(800)
    pg.evaluate("""(() => { const g=[...document.querySelectorAll('button,[role=button]')].find(x=>(x.innerText||'').includes('Generate')); if(g)g.click(); })()""")
    print("Generate clicado. Aguardando 20s...")
    time.sleep(20)
    try: b.close()
    except Exception: pass
