#!/usr/bin/env python3
"""Email notification checker for wacli-managed accounts.

Only reports emails not seen in a previous run (UID-based seen-state).
"""
import imaplib
import ssl
import json
import email
from datetime import datetime, timedelta

RULES_FILE = "/home/rafael/.openclaw/workspace/skills/email-notifications/rules.json"
STATE_FILE = "/home/rafael/.openclaw/workspace/skills/email-notifications/state.json"
SECRETS = {
    "contato@zappelin.com.br": ("/home/rafael/.openclaw/secrets/zoho-zappelin-appkey", "imap.zoho.com"),
    "rrogel@gmail.com": ("/home/rafael/.openclaw/secrets/gmail-rrogel-appkey", "imap.gmail.com"),
}

def decode_header(h):
    if not h:
        return ""
    try:
        from email.header import decode_header as dh
        parts = []
        for part, enc in dh(h):
            if isinstance(part, bytes):
                parts.append(part.decode(enc or "utf-8", errors="ignore"))
            else:
                parts.append(part)
        return "".join(parts)
    except:
        return h

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check_account(account, password, server, rules_entry, seen):
    ctx = ssl.create_default_context()
    mail = imaplib.IMAP4_SSL(server, 993, ssl_context=ctx)
    mail.login(account, password)
    mail.select("INBOX")
    status, data = mail.uid("search", None, "ALL")
    uids = [u.decode() for u in data[0].split()]
    # Limit work: only consider the most recent 30 UIDs
    recent = uids[-30:] if len(uids) > 30 else uids
    notify_mode = rules_entry.get("notify", "all")
    rules = rules_entry.get("rules", {})
    senders_filter = [s.lower() for s in rules.get("senders", [])]
    urgent_kw = [k.lower() for k in rules.get("urgent_keywords", [])]

    notifications = []
    newly_seen = set()
    for uid in recent:
        newly_seen.add(uid)
        if uid in seen:
            continue  # already reported previously
        status, msg_data = mail.uid("fetch", uid, "(RFC822)")
        if not msg_data or msg_data[0] is None:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        sender = decode_header(msg.get("From", ""))
        subject = decode_header(msg.get("Subject", ""))
        sender_l = sender.lower()
        subject_l = subject.lower()

        should_notify = False
        reason = ""
        if notify_mode == "all":
            should_notify = True
            reason = "todos"
        else:
            if any(s in sender_l for s in senders_filter):
                should_notify = True
                reason = f"sender match ({[s for s in senders_filter if s in sender_l]})"
            elif any(k in subject_l for k in urgent_kw):
                should_notify = True
                reason = "urgente"

        if should_notify:
            notifications.append({
                "account": account,
                "from": sender[:60],
                "subject": subject[:80],
                "reason": reason,
            })
    mail.close()
    mail.logout()
    return notifications, newly_seen

def main():
    rules = json.load(open(RULES_FILE))
    state = load_state()
    seen_by_account = state.get("seen", {})
    all_notifications = []
    updated_seen = {}
    for account, entry in rules["accounts"].items():
        if account not in SECRETS:
            continue
        secret_path, server = SECRETS[account]
        prev_seen = set(seen_by_account.get(account, []))
        try:
            password = open(secret_path).read().strip()
            notifs, newly_seen = check_account(account, password, server, entry, prev_seen)
            all_notifications.extend(notifs)
            # keep seen set bounded to last 200 UIDs
            merged = (prev_seen | newly_seen)
            updated_seen[account] = sorted(merged, key=lambda x: int(x))[-200:]
        except Exception as e:
            print(f"ERRO {account}: {str(e)[:100]}")

    if all_notifications:
        print(f"🔔 {len(all_notifications)} email(s) NOVO(s) desde última checagem:")
        for n in all_notifications:
            print(f"  [{n['account']}] {n['from']}")
            print(f"    📌 {n['subject']}")
            print(f"    ➡️ {n['reason']}")
    else:
        print("Nenhum email novo desde última checagem.")

    state["seen"] = updated_seen
    save_state(state)

if __name__ == "__main__":
    main()
