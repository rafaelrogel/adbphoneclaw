#!/usr/bin/env python3
import sys, time, json, os
from playwright.sync_api import sync_playwright

LOG = "/home/rafael/.openclaw/workspace/tools/fetch_redpill.log"
def log(*a):
    with open(LOG, "a") as f:
        f.write(" ".join(str(x) for x in a) + "\n")
    print(*a, flush=True)

URL = "https://renato38.com.br/"
THROW_EMAIL = "a1.redpill3.fetch@gmail.com"
THROW_NAME = "A1 Assistente"

captured = {}

def on_response(response):
    try:
        if "create_lead" in response.url:
            log("RESP create_lead status", response.status)
            body = response.json()
            log("RESP JSON keys:", list(body.keys()))
            du = body.get("downloadUrl") or body.get("url") or body.get("download_url")
            if du:
                captured["url"] = du
                log("DOWNLOAD_URL_FOUND:", du)
    except Exception as e:
        log("on_response err", e)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(locale="pt-BR")
    page = ctx.new_page()
    page.on("response", on_response)
    log("goto", URL)
    try:
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        log("goto warn", e)
    try:
        page.wait_for_selector('input[type="email"]', timeout=30000)
        log("email input present")
    except Exception as e:
        log("email input wait err", e)
    page.wait_for_timeout(3000)
    # scroll to lead form
    try:
        page.eval_on_selector("#lead-form", "el => el.scrollIntoView()")
    except Exception as e:
        log("scroll err", e)
    page.wait_for_timeout(1500)

    # fill name
    try:
        page.fill('input[name="name"]', THROW_NAME, timeout=10000)
        log("filled name")
    except Exception as e:
        log("name fill err", e)
    # fill email
    try:
        page.fill('input[type="email"]', THROW_EMAIL, timeout=10000)
        log("filled email")
    except Exception as e:
        log("email fill err", e)
    # lgpd consent checkbox
    try:
        cb = page.query_selector('input[name="lgpdConsent"]')
        if cb:
            if not cb.is_checked():
                cb.check()
            log("lgpdConsent checked")
        else:
            # MUI checkbox fallback
            page.click('[role="checkbox"]', timeout=8000)
            log("clicked role=checkbox")
    except Exception as e:
        log("consent err", e)

    page.wait_for_timeout(1000)
    # click submit button by text
    try:
        page.click('button:has-text("Baixar E-book Grátis")', timeout=10000)
        log("clicked submit")
    except Exception as e:
        log("submit click err", e)
        try:
            page.click('button[type="submit"]', timeout=8000)
            log("clicked submit(type)")
        except Exception as e2:
            log("submit2 err", e2)

    # wait for capture
    for _ in range(40):
        if captured.get("url"):
            break
        page.wait_for_timeout(1000)
    log("captured url:", captured.get("url"))

    du = captured.get("url")
    if du:
        out = "/tmp/bitcoin_red_pill_3.pdf"
        try:
            r = page.goto(du, timeout=60000)
            content = page.content()
            # try to download via request
            import urllib.request
            req = urllib.request.Request(du, headers={"User-Agent":"Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=60).read()
            # detect pdf by header %PDF
            if data[:4] == b"%PDF":
                out = "/tmp/bitcoin_red_pill_3.pdf"
            else:
                out = "/tmp/bitcoin_red_pill_3.bin"
            with open(out, "wb") as f:
                f.write(data)
            log("SAVED", out, len(data), "bytes")
            captured["file"] = out
        except Exception as e:
            log("download err", e)
    else:
        log("NO DOWNLOAD URL captured")

    browser.close()
log("DONE", json.dumps(captured))
