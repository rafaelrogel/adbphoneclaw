#!/usr/bin/env python3
"""Abre producer.ai, tira screenshot e imprime a URL final. (teste de alcance)"""
import sys
from playwright.sync_api import sync_playwright

URL = "https://producer.ai/"
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/producer_open.png"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page()
    pg.goto(URL, timeout=30000)
    pg.wait_for_timeout(3500)
    pg.screenshot(path=out, full_page=False)
    print("URL_FINAL:", pg.url)
    b.close()
