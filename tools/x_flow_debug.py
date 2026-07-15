#!/usr/bin/env python3
"""Debug flow: replicate login, dump state + screenshot at each stage."""
import asyncio, sys, base64, pathlib
sys.path.insert(0, "/home/rafael/.openclaw/workspace")
from browser_use import Browser, BrowserProfile

USER = sys.argv[1] if len(sys.argv) > 1 else "tantan873327"
PASS = sys.argv[2] if len(sys.argv) > 2 else "EspetadaDeFrango@1"

FILL = r"""(a)=>{const i=document.querySelector('input[name="'+a.name+'"]');if(!i)return 'NO';const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(i,a.value);i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));return 'OK';}"""
SUBMIT = r"""(a)=>{const i=document.querySelector('input[name="'+a.name+'"]');if(!i)return 'NO';const f=i.closest('form');if(f){f.requestSubmit();return 'SUB';}i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));return 'ENTER';}"""
ACCEPT = r"""()=>{const b=[...document.querySelectorAll('button')].find(x=>(x.innerText||'').includes('Accept all cookies'));if(b){b.click();return 'ACC';}return 'NOB';}"""
STATE = r"""()=>({
  url: location.href,
  hasUser: !!document.querySelector('input[name=username_or_email]'),
  hasPass: !!document.querySelector('input[name=password]'),
  hasCode: !!document.querySelector('input[name=verification_code]'),
  errors: [...document.querySelectorAll('[role=alert], [data-testid=error], div[class*=error]')].map(e=>(e.innerText||'').trim()).filter(Boolean).slice(0,5),
  bodyText: document.body.innerText.slice(0,400)
})"""

async def shoot(page, name):
    try:
        d = await page.screenshot()
        if isinstance(d, str):
            d = base64.b64decode(d)
        pathlib.Path(f"/home/rafael/.openclaw/workspace/tools/{name}.png").write_bytes(d)
        print(f"SHOT {name} OK", flush=True)
    except Exception as e:
        print(f"SHOT {name} FAIL {e}", flush=True)

async def main():
    prof = BrowserProfile(headless=True, chromium_sandbox=False,
                          args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"])
    b = Browser(browser_profile=prof)
    await b.start()
    page = await b.get_current_page()
    await page.goto("https://x.com/login")
    await asyncio.sleep(4)
    print("ACCEPT", await page.evaluate(ACCEPT), flush=True)
    await asyncio.sleep(1)
    print("S1_FILL", await page.evaluate(FILL, {"name":"username_or_email","value":USER}), flush=True)
    await asyncio.sleep(1)
    print("S1_SUB", await page.evaluate(SUBMIT, {"name":"username_or_email"}), flush=True)
    await asyncio.sleep(5)
    print("STATE1", await page.evaluate(STATE), flush=True)
    await shoot(page, "xflow_1")
    print("S2_FILL", await page.evaluate(FILL, {"name":"password","value":PASS}), flush=True)
    await asyncio.sleep(1)
    print("S2_SUB", await page.evaluate(SUBMIT, {"name":"password"}), flush=True)
    await asyncio.sleep(6)
    print("STATE2", await page.evaluate(STATE), flush=True)
    await shoot(page, "xflow_2")
    await b.stop()

if __name__ == "__main__":
    asyncio.run(main())
