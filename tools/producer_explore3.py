#!/usr/bin/env python3
"""Explora abas Details/Sound do composer e acha controle de duracao."""
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

    for tab in ["Details", "Sound"]:
        print(f"\n===== ABA {tab} =====")
        try:
            pg.locator("button, [role=tab]").filter(has_text=tab).first.click()
            pg.wait_for_timeout(3000)
        except Exception as e:
            print("erro clicar aba", tab, e)
        # inputs/selects/sliders
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
        # textos curtos com min/duration/length/segundos
        for el in pg.locator("*").all():
            try:
                t = (el.inner_text() or "").strip()
                if t and len(t) < 60 and any(k in t.lower() for k in ["min", "duration", "length", "second", "segundo", "duração"]):
                    print("TXT:", repr(t))
            except Exception:
                pass
        pg.screenshot(path=f"/home/rafael/.openclaw/workspace/producer_tab_{tab.lower()}.png")
        print(f"screenshot: producer_tab_{tab.lower()}.png")

    b.close()
