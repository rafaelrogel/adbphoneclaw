#!/usr/bin/env python3
"""Gera com prompt forte 5min; detecta clip novo via API; reporta duracao+URL."""
import subprocess, time, os, json, re, base64
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
PROMPT = ("Instrumental ambient music. EXACTLY 5 minutes long (300 seconds, 5:00). "
          "Seamless continuous loop, no vocals, no drums, no percussion. "
          "Soft warm pads, gentle slow evolution, calm deep atmosphere.")

# JWT
ss = json.load(open(STORAGE))
raw0=raw1=""
for c in ss.get("cookies",[]):
    if c.get("name")=="sb-sb-auth-token.0": raw0=c["value"]
    elif c.get("name")=="sb-sb-auth-token.1": raw1=c["value"]
if raw0.startswith("base64-"): raw0=raw0[len("base64-"):]
b64=raw0+raw1; b64+='='*(-len(b64)%4)
jwt=json.loads(base64.b64decode(b64).decode())["access_token"]
H={"Authorization":f"Bearer {jwt}"}

def clips(ctx):
    r=ctx.request.get("https://www.flowmusic.app/__api/clips/auth-user?limit=30&offset=0&filter=generations&include_disliked=false",
                      headers=H, timeout=15000)
    return r.json().get("clips",[])

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
    before=set(c["id"] for c in clips(ctx))
    print("clips antes:", len(before))
    # gera
    pg.evaluate("""(() => { const btns=[...document.querySelectorAll('button')]; const b=btns.find(x=>{const l=(x.getAttribute('aria-label')||'').toLowerCase(); return l.includes('sound')&&l.includes('expand');}); if(b)b.click(); })()""")
    pg.wait_for_timeout(1000)
    pg.evaluate("""(val) => { const el=document.querySelector("textarea[aria-label='Sound description']"); const s=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set; s.call(el,val); el.dispatchEvent(new Event('input',{bubbles:true})); }""", PROMPT)
    pg.wait_for_timeout(800)
    pg.evaluate("""(() => { const g=[...document.querySelectorAll('button,[role=button]')].find(x=>(x.innerText||'').includes('Generate')); if(g)g.click(); })()""")
    print("Generate clicado. Polling clip novo...")
    new=None
    for i in range(60):  # ate 10 min
        time.sleep(10)
        cur=clips(ctx)
        new_ids=[c["id"] for c in cur if c["id"] not in before]
        if new_ids:
            new=cur[[c["id"] for c in cur].index(new_ids[0])]
            dur=new.get("duration",{})
            print(f"[{i*10}s] NOVO clip {new['id']} dur_status={dur.get('status')} valor={dur.get('value')}")
            if dur.get("status")=="completed":
                break
        elif i%3==0:
            print(f"[{i*10}s] ainda sem clip novo...")
    if new:
        js=json.dumps(new)
        urls=re.findall(r'https://storage\.googleapis\.com/producer-app-public/clips/[a-f0-9-]+\.(?:m4a|wav)', js)
        print("URLs:", urls)
        print("DURACAO (s):", new.get("duration",{}).get("value"))
    else:
        print("Nenhum clip novo detectado.")
    try: b.close()
    except Exception: pass
