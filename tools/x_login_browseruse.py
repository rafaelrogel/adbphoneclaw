#!/usr/bin/env python3
"""Login to X.com via browser_use (headless Chromium) and extract auth_token+ct0
cookies into the last30days.env as AUTH_TOKEN / CT0.

Reads from env:
  X_USER   - X handle / email / phone
  X_PASS   - X password
  X_2FA    - optional verification code (if X asks after password)

Usage (background):
  cd ~/.openclaw/workspace
  X_USER=... X_PASS=... X_2FA=... \
    nohup venv_producer/bin/python3 tools/x_login_browseruse.py > tools/x_login.log 2>&1 &
"""
import os, asyncio, pathlib

ENV_FILE = os.path.expanduser("~/.openclaw/workspace/.secrets/last30days.env")
USER = os.environ.get("X_USER", "").lstrip("@")
PASS = os.environ.get("X_PASS", "")
CODE = os.environ.get("X_2FA", "")

from browser_use import Browser, BrowserProfile

FILL = r"""(args) => {
  const inp = document.querySelector('input[name="'+args.name+'"]');
  if (!inp) return 'NO_INPUT:'+args.name;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(inp, args.value);
  inp.dispatchEvent(new Event('input', {bubbles:true}));
  inp.dispatchEvent(new Event('change', {bubbles:true}));
  return 'FILLED:'+args.name;
}"""

SUBMIT = r"""(args) => {
  const inp = document.querySelector('input[name="'+args.name+'"]');
  if (!inp) return 'NO_INPUT:'+args.name;
  const f = inp.closest('form');
  if (f) { f.requestSubmit(); return 'SUBMITTED'; }
  inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
  return 'ENTER';
}"""

ACCEPT = r"""() => {
  const b = [...document.querySelectorAll('button')].find(x => (x.innerText||'').includes('Accept all cookies'));
  if (b) { b.click(); return 'ACCEPTED'; }
  return 'NO_BANNER';
}"""

HAS = r"""(name) => !!document.querySelector('input[name="'+name+'"]')"""
URL_ = r"""() => location.href"""


async def main():
    if not USER or not PASS:
        print("MISSING_CREDS", flush=True)
        return

    prof = BrowserProfile(headless=True, chromium_sandbox=False,
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    b = Browser(browser_profile=prof)
    await b.start()
    page = await b.get_current_page()
    print("STARTED", flush=True)

    try:
        await page.goto("https://x.com/login")
        await asyncio.sleep(4)
        print("AT", await page.evaluate(URL_), flush=True)

        print("COOKIES_BANNER", await page.evaluate(ACCEPT), flush=True)
        await asyncio.sleep(1)

        # Step 1: username
        print("S1", await page.evaluate(FILL, {"name": "username_or_email", "value": USER}), flush=True)
        await asyncio.sleep(1)
        print("S1_SUBMIT", await page.evaluate(SUBMIT, {"name": "username_or_email"}), flush=True)
        await asyncio.sleep(5)

        # Step 2: password (field may already be visible)
        if await page.evaluate(HAS, "password"):
            print("S2", await page.evaluate(FILL, {"name": "password", "value": PASS}), flush=True)
            await asyncio.sleep(1)
            print("S2_SUBMIT", await page.evaluate(SUBMIT, {"name": "password"}), flush=True)
            await asyncio.sleep(6)

        # 2FA?
        if await page.evaluate(HAS, "verification_code") and CODE:
            print("S3_2FA", await page.evaluate(FILL, {"name": "verification_code", "value": CODE}), flush=True)
            await asyncio.sleep(1)
            print("S3_SUBMIT", await page.evaluate(SUBMIT, {"name": "verification_code"}), flush=True)
            await asyncio.sleep(6)

        # Poll cookies
        got = None
        for _ in range(12):
            cookies = await b.cookies()
            auth = next((c for c in cookies if c.get("name") == "auth_token"), None)
            ct0 = next((c for c in cookies if c.get("name") == "ct0"), None)
            if auth and ct0:
                got = (auth["value"], ct0["value"])
                break
            await asyncio.sleep(2)

        if not got:
            print("NO_COOKIES url=", await page.evaluate(URL_), flush=True)
            try:
                pathlib.Path("/home/rafael/.openclaw/workspace/tools/x_login_debug.png").write_bytes(
                    await page.screenshot())
                print("DEBUG_SHOT_OK", flush=True)
            except Exception as e:
                print("DEBUG_SHOT_FAIL", e, flush=True)
            print("RESULT_FAIL", flush=True)
            return

        write_env(got[0], got[1])
        print("RESULT_OK auth_len=", len(got[0]), "ct0_len=", len(got[1]), flush=True)
    finally:
        try:
            await b.stop()
        except Exception:
            pass


def write_env(auth_val, ct0_val):
    lines = []
    seen = {"AUTH_TOKEN": False, "CT0": False}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                s = line.rstrip("\n")
                if s.startswith("AUTH_TOKEN="):
                    lines.append(f"AUTH_TOKEN=***")
                    seen["AUTH_TOKEN"] = True
                elif s.startswith("CT0="):
                    lines.append(f"CT0={ct0_val}")
                    seen["CT0"] = True
                else:
                    lines.append(s)
    if not seen["AUTH_TOKEN"]:
        lines.append(f"AUTH_TOKEN=***")
    if not seen["CT0"]:
        lines.append(f"CT0={ct0_val}")
    if not any(l.startswith("OPENROUTER_API_KEY=") for l in lines):
        lines.append("OPENROUTER_API_KEY=***")
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(ENV_FILE, 0o600)


if __name__ == "__main__":
    asyncio.run(main())
