#!/usr/bin/env python3
"""Shared helpers for Flow Music automation: browser launch + fresh JWT from live context."""
import os, json, base64, subprocess, time
from playwright.sync_api import sync_playwright

XVFB_DISPLAY = ":99"
STORAGE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.37")


def ensure_xvfb():
    # Headless Chromium does not need a display; this is a no-op to avoid
    # starting Xvfb / running pkill. Kept for API compatibility.
    return


def decode_jwt_from_cookie(raw0, raw1):
    if raw0.startswith("base64-"):
        raw0 = raw0[len("base64-"):]
    b64 = raw0 + raw1
    b64 += "=" * (-len(b64) % 4)
    return json.loads(base64.b64decode(b64).decode())


def fresh_jwt(context):
    """Read a fresh JWT from the live browser context cookies (after page load/refresh)."""
    cookies = context.cookies()
    raw0 = raw1 = ""
    for c in cookies:
        if c.get("name") == "sb-sb-auth-token.0":
            raw0 = c["value"]
        elif c.get("name") == "sb-sb-auth-token.1":
            raw1 = c["value"]
    if not raw0:
        return None
    try:
        return decode_jwt_from_cookie(raw0, raw1).get("access_token")
    except Exception:
        return None


def launch():
    """Launch browser, load app to refresh token, return (browser, context, page, get_jwt_fn)."""
    ensure_xvfb()
    b = None
    # reuse a single playwright instance via context manager pattern in caller;
    # here we return raw objects and let caller manage lifecycle with sync_playwright
    raise NotImplementedError("use launch_cm")


def launch_cm():
    """Context-manager friendly: yields (context, page, fresh_jwt_fn). Caller wraps in `with sync_playwright()`."""
    ensure_xvfb()
    # placeholder; real impl below in make_session
    raise NotImplementedError


def make_session():
    """Returns a sync_playwright context. Usage:
        with sync_playwright() as p:
            b, ctx, pg, jwt_fn = make_session(p)
    """
    ensure_xvfb()
    b = None  # set by caller
    return None


# ---- The practical API used by scripts ----
class ProducerSession:
    def __init__(self):
        self.p = sync_playwright().start()
        ensure_xvfb()
        self.browser = self.p.chromium.launch(
            headless=True,  # persistent session: no OAuth needed, so headless is fine
            args=["--disable-blink-features=AutomationControlled",
                  "--no-first-run", "--no-default-browser-check",
                  "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 900}, user_agent=UA,
            storage_state=STORAGE)
        self.page = self.context.new_page()
        self.page.goto("https://www.flowmusic.app/session?t=true", timeout=60000)
        self.page.wait_for_timeout(4000)
        # trigger token refresh
        self.page.evaluate("() => { try { return !!window; } catch(e){} }")

    def jwt(self):
        return fresh_jwt(self.context)

    def api_get(self, path, params=None):
        import urllib.parse
        url = "https://www.flowmusic.app" + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Authorization": f"Bearer {self.jwt()}"}
        r = self.context.request.get(url, headers=headers, timeout=20000)
        return r

    def api_post(self, path, json_body=None):
        url = "https://www.flowmusic.app" + path
        headers = {"Authorization": f"Bearer {self.jwt()}",
                   "Content-Type": "application/json"}
        r = self.context.request.post(url, headers=headers,
                                      data=json.dumps(json_body or {}), timeout=20000)
        return r

    def list_clips(self, limit=30):
        r = self.api_get("/__api/clips/auth-user",
                         {"limit": limit, "offset": 0, "filter": "generations",
                          "include_disliked": "false"})
        try:
            return r.json().get("clips", [])
        except Exception:
            return []

    def close(self):
        try:
            self.browser.close()
        except Exception:
            pass
        try:
            self.p.stop()
        except Exception:
            pass
