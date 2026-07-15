#!/usr/bin/env python3
"""Diagnostico 2: conteudo do modal de Login."""
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
    pg.goto("https://producer.ai/", timeout=30000)
    pg.wait_for_timeout(5000)

    # clica o BUTTON (nao o link)
    pg.locator("button").filter(has_text="Login").first.click()
    pg.wait_for_timeout(3000)

    # modal
    modal = pg.locator("[role=dialog]").first
    # dump de botoes/links/inputs dentro do modal
    print("=== elementos dentro do modal ===")
    for sel in ["button", "a", "input"]:
        els = modal.locator(sel).all()
        for el in els:
            try:
                tag = sel
                text = (el.inner_text() or "").strip()
                href = el.get_attribute("href")
                itype = el.get_attribute("type")
                name = el.get_attribute("name")
                print(f"<{tag}> text='{text}' type={itype} name={name} href={href}")
            except Exception as e:
                print("  erro el:", e)

    pg.screenshot(path="/home/rafael/.openclaw/workspace/producer_modal.png")
    print("screenshot: producer_modal.png")
    b.close()
