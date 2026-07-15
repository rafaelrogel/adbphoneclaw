#!/usr/bin/env python3
"""Expande Details e procura controle de duracao no composer."""
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
    pg.goto("https://www.flowmusic.app/session?t=true", timeout=30000)
    pg.wait_for_timeout(5000)

    # expande Details
    print("Expandindo Details...")
    try:
        pg.locator('button[aria-label="Expand Details section"]').click(timeout=8000)
        pg.wait_for_timeout(3000)
        print("Details expandido.")
    except Exception as e:
        print("erro expandir Details:", e)

    # expande Sound tambem (ja pode estar)
    try:
        pg.locator('button[aria-label="Expand Sound section"]').click(timeout=5000)
        pg.wait_for_timeout(2000)
    except Exception:
        pass

    print("=== INPUTS/SELECTS/SLIDERS ===")
    for el in pg.locator("input, textarea, select").all():
        try:
            tag = el.evaluate("e => e.tagName")
            typ = el.get_attribute("type") or ""
            ph = el.get_attribute("placeholder") or ""
            name = el.get_attribute("name") or ""
            aid = el.get_attribute("aria-label") or ""
            if ph or name or aid or tag in ("TEXTAREA", "SELECT") or typ in ("range", "number", "checkbox"):
                print(f"<{tag}> type={typ} name={name} placeholder='{ph}' aria='{aid}'")
        except Exception:
            pass

    print("=== TEXTOS com duration/min/length/second/segundos ===")
    for el in pg.locator("*").all():
        try:
            t = (el.inner_text() or "").strip()
            if t and len(t) < 70 and any(k in t.lower() for k in
                ["duration", "min", "length", "second", "segundo", "duração", "minute"]):
                print("TXT:", repr(t))
        except Exception:
            pass

    # procura selects especificamente (opcoes de duracao)
    print("=== SELECTS ===")
    for sel in pg.locator("select").all():
        try:
            opts = [o.inner_text() for o in sel.locator("option").all()]
            print("SELECT opts:", opts)
        except Exception:
            pass

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_details.png", full_page=False)
    print("screenshot: producer_details.png")
    b.close()
