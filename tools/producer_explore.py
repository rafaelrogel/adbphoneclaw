#!/usr/bin/env python3
"""Explora UI do flowmusic.app (sessao logada) para achar prompt/duracao/gerar/download."""
import subprocess, time, os, json
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
        viewport={"width": 1440, "height": 900},
        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        storage_state=STORAGE,
    )
    pg = ctx.new_page()
    pg.goto("https://www.flowmusic.app/", timeout=30000)
    pg.wait_for_timeout(6000)

    print("=== TITLE:", pg.title())
    print("=== URL:", pg.url)

    # inputs
    print("=== INPUTS ===")
    for el in pg.locator("input, textarea").all():
        try:
            tag = el.evaluate("e => e.tagName")
            typ = el.get_attribute("type") or ""
            ph = el.get_attribute("placeholder") or ""
            name = el.get_attribute("name") or ""
            aid = el.get_attribute("aria-label") or ""
            if ph or name or aid or tag == "TEXTAREA":
                print(f"<{tag}> type={typ} name={name} placeholder='{ph}' aria={aid}")
        except Exception:
            pass

    # botoes (primeiros 40)
    print("=== BOTOES ===")
    for el in pg.locator("button").all()[:50]:
        try:
            t = (el.inner_text() or "").strip()
            if t:
                print("BTN:", repr(t[:60]))
        except Exception:
            pass

    # elementos com palavras-chave
    print("=== PALAVRAS-CHAVE (duration/length/minutes/generate/create/download) ===")
    html = pg.content()
    import re
    for kw in ["duration", "length", "minute", "generate", "create", "download",
               "duração", "gerar", "criar", "baixar", "export", "mp3", "seconds", "segundo"]:
        if kw.lower() in html.lower():
            print("KW:", kw)

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_ui.png", full_page=False)
    print("screenshot: producer_ui.png")
    b.close()
