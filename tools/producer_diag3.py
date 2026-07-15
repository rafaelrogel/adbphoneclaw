#!/usr/bin/env python3
"""Diagnostico 3: chega na tela de 2FA e reporta o metodo (toque vs codigo)."""
import json, os, subprocess, time
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") != 0:
    subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
os.environ["DISPLAY"] = XVFB_DISPLAY

creds = json.load(open("/home/rafael/.openclaw/secrets/producer_creds.json"))


def get_frame(page):
    try:
        return page.frame_locator("#credentials").frame
    except Exception:
        pass
    for sel in ["iframe", "iframe[name='credentials']"]:
        try:
            fr = page.frame_locator(sel).frame
            if fr is not None:
                return fr
        except Exception:
            pass
    return page


with sync_playwright() as p:
    b = p.chromium.launch(headless=False,
                          args=["--disable-blink-features=AutomationControlled",
                                "--no-first-run", "--no-default-browser-check"])
    ctx = b.new_context(viewport={"width": 1280, "height": 720},
                        user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"))
    pg = ctx.new_page()
    popup = [None]
    pg.on("popup", lambda pop: popup.__setitem__(0, pop))

    pg.goto("https://producer.ai/", timeout=30000)
    pg.wait_for_timeout(4000)
    pg.locator("button").filter(has_text="Login").first.click()
    pg.wait_for_timeout(2500)
    pg.locator("button").filter(has_text="Continue with Google").first.click()
    pg.wait_for_timeout(3500)
    target = popup[0] if popup[0] else pg
    target.wait_for_load_state("domcontentloaded")
    time.sleep(2)
    fr = get_frame(target)
    fr.locator('input[name="identifier"]').fill(creds["email"])
    time.sleep(0.5)
    fr.locator("#identifierNext button").first.click(timeout=5000)
    time.sleep(3000)
    fr.locator('input[type="password"]').fill(creds["password"])
    time.sleep(0.5)
    fr.locator("#passwordNext button").first.click(timeout=5000)
    time.sleep(4000)

    # estamos na tela de 2FA
    print("=== TELA 2FA ===")
    print("URL:", target.url)
    # texto visivel
    try:
        txt = fr.inner_text()
        print("TEXTO VISIVEL:\n", txt[:1500])
    except Exception as e:
        print("erro texto:", e)
    # procura campos de codigo
    for sel in ['input[type="tel"]', 'input[type="text"]', 'input[name="totpPin"]',
                'input[id="totpPin"]', 'input[inputmode="numeric"]', 'input[autocomplete="one-time-code"]']:
        try:
            el = fr.locator(sel).first
            if el.is_visible(timeout=1500):
                print("CAMPO CODIGO ENCONTRADO:", sel)
        except Exception:
            pass
    # procura botao "Enviar codigo" / "Get code" / "Text"/"Call"
    for sel in ["button"]:
        try:
            for el in fr.locator(sel).all():
                t = (el.inner_text() or "").strip()
                if t:
                    print("BTN:", t)
        except Exception:
            pass
    target.screenshot(path="/home/rafael/.openclaw/workspace/producer_2fa2.png")
    print("screenshot: producer_2fa2.png")
    b.close()
