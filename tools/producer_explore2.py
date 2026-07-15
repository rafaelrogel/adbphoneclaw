#!/usr/bin/env python3
"""Explora o composer do flowmusic (apos clicar Compose)."""
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
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
                        storage_state=STORAGE)
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/", timeout=30000)
    pg.wait_for_timeout(5000)

    print("Clicando Compose...")
    pg.locator("button").filter(has_text="Compose").first.click()
    pg.wait_for_timeout(4000)
    print("URL apos Compose:", pg.url)

    print("=== INPUTS ===")
    for el in pg.locator("input, textarea, select").all():
        try:
            tag = el.evaluate("e => e.tagName")
            typ = el.get_attribute("type") or ""
            ph = el.get_attribute("placeholder") or ""
            name = el.get_attribute("name") or ""
            aid = el.get_attribute("aria-label") or ""
            rid = el.get_attribute("role") or ""
            if ph or name or aid or tag in ("TEXTAREA", "SELECT") or typ in ("range", "number"):
                print(f"<{tag}> type={typ} name={name} placeholder='{ph}' aria='{aid}' role={rid}")
        except Exception:
            pass

    print("=== BOTOES ===")
    for el in pg.locator("button, [role=button]").all()[:60]:
        try:
            t = (el.inner_text() or "").strip()
            if t:
                print("BTN:", repr(t[:70]))
        except Exception:
            pass

    # procura controle de duracao: elementos com 'min' ou 'duration' ou 'length'
    print("=== DURACAO ===")
    for el in pg.locator("*").all():
        try:
            t = (el.inner_text() or "").strip()
            if t and ("min" in t.lower() or "duration" in t.lower() or "length" in t.lower()):
                if len(t) < 80:
                    print("TXT:", repr(t))
        except Exception:
            pass

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_compose.png", full_page=False)
    print("screenshot: producer_compose.png")
    b.close()
