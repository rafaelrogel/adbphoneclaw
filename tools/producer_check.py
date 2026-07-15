#!/usr/bin/env python3
"""Verifica se storage_state mantem login no flowmusic.app."""
import subprocess, time, os
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"

with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        storage_state=STORAGE,
    )
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/", timeout=30000)
    pg.wait_for_timeout(5000)
    print("URL:", pg.url)
    # login button visivel?
    login_visible = False
    try:
        if pg.locator("button").filter(has_text="Login").first.is_visible(timeout=2000):
            login_visible = True
    except Exception:
        pass
    print("Botao Login visivel:", login_visible)
    # procura indicadores de conta
    for sel in ["button:has-text('Account')", "img[alt*='avatar' i]",
                "[aria-label*='account' i]", "text=Logout", "text=Sign out"]:
        try:
            if pg.locator(sel).first.is_visible(timeout=1500):
                print("INDICADOR CONTA:", sel)
        except Exception:
            pass
    # cookies apos navegacao
    c = ctx.cookies()
    fm = [x["name"] for x in c if "flowmusic.app" in x["domain"]]
    print("flowmusic cookies apos nav:", fm)
    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_check.png")
    print("screenshot: producer_check.png")
    b.close()
