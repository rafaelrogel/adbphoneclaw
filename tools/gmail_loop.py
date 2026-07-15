#!/usr/bin/env python3
"""gmail_loop.py - Verifica e-mails de rafael.rogel@revolut.com com assunto
iniciado em [p], executa o comando via OpenClaw agent (A1) e responde por
e-mail. Roda via cron a cada 10 min.

Regras de seguranca:
- So aceita remetente exato: rafael.rogel@revolut.com
- So processa assunto comecando com [p]
- Nao imprime senhas.
"""
import imaplib
import smtplib
import ssl
import email
import email.utils
import json
import os
import sys
import time
import shutil
import subprocess
import tempfile

GMAIL_USER = "rrogel@gmail.com"
APPKEY_FILE = "/home/rafael/.openclaw/secrets/gmail-rrogel-appkey"
ALLOWED_SENDER = "rafael.rogel@revolut.com"
SUBJECT_PREFIX = "[p]"
SESSION_KEY = "agent:main:email-rafael-rogel"
AGENT_TIMEOUT = 300

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "gmail_loop.state")
LOG_FILE = os.path.join(HERE, "gmail_loop.log")

OPENCLAW_BIN = shutil.which("openclaw") or "/home/rafael/.nvm/versions/node/v24.16.0/bin/openclaw"


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_processed():
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE) as f:
            return set(l.strip() for l in f if l.strip())
    except Exception:
        return set()


def save_processed(s):
    try:
        with open(STATE_FILE, "w") as f:
            for x in s:
                f.write(x + "\n")
    except Exception as e:
        log("erro ao salvar state: %s" % e)


def get_appkey():
    with open(APPKEY_FILE) as f:
        return f.read().strip()


def decode_part(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def fetch_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return decode_part(part)
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return decode_part(part)
    else:
        return decode_part(msg)
    return ""


def clean_body(text):
    lines = text.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith(">"):
            continue
        if s == "--":
            break
        if (s.startswith("Em ") or s.startswith("On ")) and ("escreveu:" in s or "wrote:" in s):
            break
        out.append(line)
    return "\n".join(out).strip()


def run_agent(prompt):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(prompt)
        tf_path = tf.name
    try:
        cmd = [OPENCLAW_BIN, "agent", "--session-key", SESSION_KEY,
               "--message-file", tf_path, "--json", "--thinking", "off"]
        # Garante node no PATH: cron roda com PATH minimo e openclaw e script node.
        env = dict(os.environ)
        node_bin = os.path.dirname(OPENCLAW_BIN)
        env["PATH"] = node_bin + ":" + env.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT, env=env)
        out = res.stdout
        try:
            data = json.loads(out)
            texts = []
            for p in data.get("result", {}).get("payloads", []):
                t = p.get("text")
                if t:
                    texts.append(t)
            reply = "\n\n".join(texts).strip()
            if reply:
                return reply
            log("agent sem texto. stderr=%s" % (res.stderr or "").strip()[:400])
            return "(sem resposta do agente)"
        except Exception:
            log("agent saida nao-JSON. stdout=%s stderr=%s" % (out.strip()[:200], (res.stderr or "").strip()[:200]))
            return "(sem resposta do agente)"
    except subprocess.TimeoutExpired:
        return "ERRO: agent timeout"
    except Exception as e:
        return "ERRO ao chamar agent: %s" % e
    finally:
        try:
            os.unlink(tf_path)
        except Exception:
            pass


def send_reply(to, subject, body):
    appkey = get_appkey()
    msg = email.message.EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as s:
        s.login(GMAIL_USER, appkey)
        s.send_message(msg)


def main():
    processed = load_processed()
    try:
        appkey = get_appkey()
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        mail.login(GMAIL_USER, appkey)
        mail.select("INBOX")
    except Exception as e:
        log("IMAP erro: %s" % e)
        return

    try:
        # Varre e-mails do remetente autorizado com assunto [p]. Nao depende de UNSEEN:
        # se o cliente leu antes do poll, ainda processamos (dedup via state file).
        typ, data = mail.search(None, "FROM", '"rafael.rogel@revolut.com"', "SUBJECT", '"[p]"')
        if typ != "OK" or not data or not data[0]:
            log("sem e-mails [p] de %s" % ALLOWED_SENDER)
            return
        ids = data[0].split()
        handled = 0
        for num in ids:
            try:
                typ, msg_data = mail.fetch(num, "(RFC822)")
                if typ != "OK":
                    continue
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                mid = msg.get("Message-ID")
                sender = email.utils.parseaddr(msg.get("From"))[1].lower()
                subject = msg.get("Subject") or ""
                if sender != ALLOWED_SENDER:
                    continue
                # Aceita tanto nova msg (assunto '[p] ...') quanto resposta ('Re: [p] ...'):
                # basta conter o marcador [p] em qualquer lugar do assunto.
                if SUBJECT_PREFIX not in subject:
                    continue
                if mid and mid in processed:
                    continue
                body = clean_body(fetch_body(msg))
                log("processando: subject=%r de=%s" % (subject, sender))
                reply = run_agent(body)
                try:
                    send_reply(ALLOWED_SENDER, "Re: " + subject, reply)
                    log("resposta enviada por e-mail para %s" % ALLOWED_SENDER)
                except Exception as e:
                    log("erro ao enviar resposta: %s" % e)
                if mid:
                    processed.add(mid)
                try:
                    mail.store(num, "+FLAGS", "\\Seen")
                except Exception:
                    pass
                handled += 1
            except Exception as e:
                log("erro ao processar msg %s: %s" % (num, e))
        if handled:
            save_processed(processed)
        log("ciclo ok (%d processado(s))" % handled)
    finally:
        try:
            mail.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
