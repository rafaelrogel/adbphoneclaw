#!/usr/bin/env python3
"""Debug2: dump X login buttons with aria-label + submit buttons."""
import asyncio, sys
sys.path.insert(0, "/home/rafael/.openclaw/workspace")
from browser_use import Browser, BrowserProfile

JS = r"""() => {
  const btns = [...document.querySelectorAll('button, [role=button], input[type=submit]')].map(b => ({
    tag: b.tagName,
    text: (b.innerText||'').trim().slice(0,40),
    aria: b.getAttribute('aria-label'),
    type: b.getAttribute('type'),
    cls: (b.className||'').toString().slice(0,50)
  }));
  const forms = [...document.querySelectorAll('form')].map(f => ({action: f.getAttribute('action'), id: f.id}));
  return {url: location.href, btns, forms};
}"""

async def main():
    prof = BrowserProfile(headless=True, chromium_sandbox=False,
                          args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"])
    b = Browser(browser_profile=prof)
    await b.start()
    page = await b.get_current_page()
    await page.goto("https://x.com/login")
    await asyncio.sleep(6)
    info = await page.evaluate(JS)
    print("INFO", info, flush=True)
    await b.stop()

if __name__ == "__main__":
    asyncio.run(main())
