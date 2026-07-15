#!/usr/bin/env python3
"""Envia email via conta Zoho registrada (appkey em arquivo seguro).
Nao imprime senhas. Uso: python3 send_email.py <destino> <arquivo> [assunto]
"""
import smtplib, ssl, sys, os
from email.message import EmailMessage

SECRET = "/home/rafael/.openclaw/secrets/zoho-zappelin-appkey"
SENDER = "contato@zappelin.com.br"
SMTP_HOST = "smtp.zoho.com"


def send(to, attach, subject):
    pw = open(SECRET).read().strip()
    msg = EmailMessage()
    msg["From"] = SENDER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(
        "Segue o codigo do bug bounty hunter (secret_hunter.py).\n\nA1 // Rafael")
    with open(attach, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="text", subtype="x-python",
                       filename=os.path.basename(attach))
    last_err = None
    for port, ssl_mode in [(587, "starttls"), (465, "ssl")]:
        try:
            if ssl_mode == "ssl":
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(SMTP_HOST, port, context=ctx, timeout=15) as s:
                    s.login(SENDER, pw)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, port, timeout=15) as s:
                    s.starttls(context=ssl.create_default_context())
                    s.login(SENDER, pw)
                    s.send_message(msg)
            print(f"ENVIADO {SENDER} -> {to} via smtp.zoho.com:{port}")
            return 0
        except Exception as e:
            last_err = e
            print(f"tentativa {port}/{ssl_mode} falhou: {e!r}")
    print("NAO ENVIADO:", last_err)
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: send_email.py <destino> <arquivo> [assunto]")
        sys.exit(2)
    to = sys.argv[1]
    attach = sys.argv[2]
    subject = sys.argv[3] if len(sys.argv) > 3 else "Bug bounty hunter - secret_hunter.py"
    sys.exit(send(to, attach, subject))
