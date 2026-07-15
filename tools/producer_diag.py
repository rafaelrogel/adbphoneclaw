#!/usr/bin/env python3
"""Diagnostico: o que o botao Login faz?"""
import subprocess, time, os
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    ctx = b.new_context(viewport={"width": 1280, "height": 720})
    pg = ctx.new_page()
    popups = []
    pg.on("popup", lambda pop: (popups.append(pop), print("[popup]", pop.url)))

    pg.goto("https://producer.ai/", timeout=30000)
    pg.wait_for_timeout(6000)

    # inspeciona todos os elementos com 'login' no texto
    print("=== elementos Login ===")
    els = pg.locator("button, a").filter(has_text="Login").all()
    for i, el in enumerate(els):
        try:
            tag = el.evaluate("e => e.tagName")
            href = el.get_attribute("href")
            onclick = el.get_attribute("onclick")
            text = el.inner_text()
            print(f"[{i}] <{tag}> text='{text}' href={href} onclick={onclick}")
        except Exception as e:
            print(f"[{i}] erro: {e}")

    # clica o primeiro e observa
    print("=== clique Login ===")
    els[0].click()
    pg.wait_for_timeout(6000)
    print("popups apos clique:", [pp.url for pp in popups])
    print("URL main apos clique:", pg.url)
    # procura modal/dialog
    for sel in ["dialog", "[role=dialog]", ".modal", "[class*='modal' i]", "[class*='overlay' i]"]:
        try:
            if pg.locator(sel).first.is_visible(timeout=1000):
                print("MODAL visivel:", sel)
        except Exception:
            pass
    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_diag_after.png")
    print("screenshot: producer_diag_after.png")
    b.close()
