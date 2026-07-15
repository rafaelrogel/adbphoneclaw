#!/usr/bin/env python3
"""producer_login.py v4 - Login flowmusic.app via modal 'Continue with Google'
Corrige: escopo de popup (lista), campos de email/senha em iframe do Google.
Pre-requisito: secrets/producer_creds.json {"email":"...","password":"***"}
Apos login, creds DELETADOS. Sessao -> secrets/producer_storage_state.json.
"""
import json, os, subprocess, sys, time
from playwright.sync_api import sync_playwright

CREDS_FILE = "/home/rafael/.openclaw/secrets/producer_creds.json"
STORAGE_FILE = "/home/rafael/.openclaw/secrets/producer_storage_state.json"
XVFB_DISPLAY = ":99"


def start_xvfb():
    if os.system(f"xdpyinfo -display {XVFB_DISPLAY} >/dev/null 2>&1") == 0:
        os.environ["DISPLAY"] = XVFB_DISPLAY
        return None
    proc = subprocess.Popen(["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.environ["DISPLAY"] = XVFB_DISPLAY
    time.sleep(1)
    return proc


def get_frame(page):
    """Retorna frame principal ou iframe do Google signin, se houver."""
    try:
        fr = page.frame_locator("#credentials").frame
        return fr
    except Exception:
        pass
    # tenta qualquer iframe visivel
    for sel in ["iframe", "iframe[name='credentials']"]:
        try:
            fr = page.frame_locator(sel).frame
            if fr is not None:
                return fr
        except Exception:
            pass
    return page


def fill_google(page, email, password):
    if "accounts.google.com" not in page.url:
        return False
    print(f"[google] {page.url}")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)
    fr = get_frame(page)

    # EMAIL
    for sel in ['input[type="email"]', 'input[name="identifier"]',
                'input#identifierId', 'input[type="text"]']:
        try:
            el = fr.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(email)
                print("email preenchido via", sel); break
        except Exception:
            continue
    else:
        print("NAO ACHOU campo de email"); return False
    time.sleep(0.6)
    for sel in ["#identifierNext button", "button:has-text('Next')"]:
        try:
            fr.locator(sel).first.click(timeout=3000); break
        except Exception:
            continue
    time.sleep(3)

    # SENHA
    for sel in ['input[type="password"]', 'input[name="password"]', 'input[type="text"]']:
        try:
            el = fr.locator(sel).first
            if el.is_visible(timeout=3000):
                el.fill(password)
                print("senha preenchida via", sel); break
        except Exception:
            continue
    else:
        print("NAO ACHOU campo de senha"); return False
    time.sleep(0.6)
    for sel in ["#passwordNext button", "button:has-text('Next')"]:
        try:
            fr.locator(sel).first.click(timeout=3000); break
        except Exception:
            continue
    time.sleep(3)
    return True


def main():
    if not os.path.exists(CREDS_FILE):
        print(f"ERRO: {CREDS_FILE} ausente"); sys.exit(1)
    creds = json.load(open(CREDS_FILE))
    email, password = creds["email"], creds["password"]
    xvfb = start_xvfb()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
            )
            page = ctx.new_page()
            popup_holder = [None]
            page.on("popup", lambda pop: (popup_holder.__setitem__(0, pop),
                                          print("[popup]", pop.url)))

            print("Abrindo producer.ai...")
            page.goto("https://producer.ai/", timeout=30000)
            page.wait_for_timeout(5000)

            print("Clica Login (button)...")
            page.locator("button").filter(has_text="Login").first.click()
            page.wait_for_timeout(3000)

            print("Clica 'Continue with Google'...")
            page.locator("button").filter(has_text="Continue with Google").first.click()
            page.wait_for_timeout(4000)

            target = popup_holder[0] if popup_holder[0] is not None else page
            if popup_holder[0] is not None:
                target.wait_for_load_state("domcontentloaded")
            print("Target OAuth URL:", target.url)

            saved = False
            if fill_google(target, email, password):
                print("Pos-password: aguardando 2FA + consent (ate 600s)...")
                try:
                    target.screenshot(path="/home/rafael/.openclaw/workspace/producer_2fa.png")
                    print("SCREENSHOT 2FA: producer_2fa.png")
                except Exception as e:
                    print("erro screenshot 2fa:", e)
                need_code_sent = False
                for _ in range(200):
                    time.sleep(2)
                    u = target.url
                    if "rejected" in u or ("signin/challenge" in u and "denied" in u):
                        print("Google REJEITOU. URL:", u); break
                    # redirect REAL pra flowmusic (sem accounts.google.com) => salva JA
                    if "accounts.google.com" not in u and "flowmusic.app" in u:
                        print("OAuth concluido (redirect flowmusic):", u)
                        try:
                            ctx.storage_state(path=STORAGE_FILE)
                            os.chmod(STORAGE_FILE, 0o600)
                            saved = True
                            print("LOGIN_CONCLUIDO ->", STORAGE_FILE)
                        except Exception as e:
                            print("erro salvar storage:", e)
                        break
                    # consent screen?
                    if "consent" in u and "accounts.google.com" in u:
                        for btn in ["button:has-text('Allow')", "button:has-text('Continue')",
                                    "button:has-text('Permitir')", "#submit_approve",
                                    "button:has-text('Concordo')"]:
                            try:
                                b = target.locator(btn).first
                                if b.is_visible(timeout=1000):
                                    print("Clicando consent:", btn)
                                    b.click(); time.sleep(2); break
                            except Exception:
                                pass
                        continue
                    # 2FA por codigo?
                    code_input = None
                    for sel in ['input[type="tel"]', 'input[name="totpPin"]',
                                'input[id="totpPin"]', 'input[inputmode="numeric"]',
                                'input[autocomplete="one-time-code"]']:
                        try:
                            el = target.locator(sel).first
                            if el.is_visible(timeout=600):
                                code_input = el; break
                        except Exception:
                            pass
                    if code_input is not None:
                        codef = "/tmp/producer_code.txt"
                        if os.path.exists(codef):
                            code = open(codef).read().strip()
                            print("Preenchendo codigo 2FA:", code)
                            code_input.fill(code)
                            time.sleep(1)
                            try:
                                target.locator("button:has-text('Next'), button:has-text('Verify'), button:has-text('Confirm')").first.click()
                            except Exception:
                                pass
                            os.unlink(codef)
                        elif not need_code_sent:
                            need_code_sent = True
                            print("NEED_CODE: 2FA por codigo. Envia codigo.")
                            target.screenshot(path="/home/rafael/.openclaw/workspace/producer_2fa_code.png")
                        continue
                    # else: 2FA por toque, aguarda aprovacao no celular
                # fim loop
                if popup_holder[0] is not None:
                    try: popup_holder[0].close()
                    except Exception: pass
                page.wait_for_timeout(1500)
            else:
                print("OAuth nao preenchido. URL:", target.url)
                page.screenshot(path="/home/rafael/.openclaw/workspace/producer_oauth_fail.png")

            if not saved:
                print("LOGIN_FALHOU (nao houve redirect valido).")
                page.screenshot(path="/home/rafael/.openclaw/workspace/producer_login_fail.png")
            else:
                print("SESSAO SALVA.")

            browser.close()
    finally:
        try: os.unlink(CREDS_FILE); print("Creds removidos")
        except Exception: pass
        if xvfb: xvfb.terminate()


if __name__ == "__main__":
    main()
