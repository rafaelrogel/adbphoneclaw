#!/usr/bin/env python3
"""Lista clips do usuario; acha o da musica de teste e URL de audio."""
import subprocess, time, os, json, re, base64
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1440x900x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"

# JWT
ss = json.load(open(STORAGE))
raw0 = raw1 = ""
for c in ss.get("cookies", []):
    if c.get("name")=="sb-sb-auth-token.0": raw0=c["value"]
    elif c.get("name")=="sb-sb-auth-token.1": raw1=c["value"]
if raw0.startswith("base64-"): raw0=raw0[len("base64-"):]
b64=raw0+raw1; b64+='='*(-len(b64)%4)
dec=json.loads(base64.b64decode(b64).decode())
jwt=dec["access_token"]

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run","--no-default-browser-check"])
    ctx = b.new_context(storage_state=STORAGE,
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37"))
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/library/my-songs", timeout=30000)
    pg.wait_for_timeout(3000)
    headers={"Authorization":f"Bearer {jwt}"}
    r=ctx.request.get("https://www.flowmusic.app/__api/clips/auth-user?limit=20&offset=0&filter=generations&include_disliked=false",
                      headers=headers, timeout=15000)
    data=r.json()
    clips=data.get("clips",[])
    print(f"=== {len(clips)} clips ===")
    for cl in clips:
        cid=cl.get("id")
        dur=cl.get("duration")
        ca=cl.get("created_at") or cl.get("inserted_at") or cl.get("generated_at")
        txt=cl.get("prompt") or cl.get("text") or cl.get("title") or ""
        js=json.dumps(cl)
        urls=re.findall(r'https://storage\.googleapis\.com/producer-app-public/clips/[a-f0-9-]+\.(?:m4a|wav)', js)
        print(f"id={cid} ca={ca} dur={dur.get('value') if isinstance(dur,dict) else dur} txt={str(txt)[:40]}")
    # ordena por created_at desc
    def keyf(c):
        for k in ("created_at","inserted_at","generated_at"):
            if c.get(k): return c[k]
        return ""
    clips_sorted=sorted(clips,key=keyf,reverse=True)
    print("\nMAIS RECENTE:")
    for cl in clips_sorted[:3]:
        print(" ", cl.get("id"), keyf(cl), cl.get("duration"))
    try: b.close()
    except Exception: pass
