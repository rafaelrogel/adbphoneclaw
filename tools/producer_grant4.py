#!/usr/bin/env python3
"""Full Google One grant state-machine: grant dialog -> account -> Continue -> consent -> 2FA or Remix."""
import tools.producer_common as C, json, time

s = C.ProducerSession()
clips = s.list_clips(limit=10)
CLIP = clips[0]["id"]
conv = clips[0]["operation"].get("conversation_id")
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

def body():
    return s.page.evaluate("()=>document.body.innerText.replace(/\\n+/g,' | ').slice(0,280)")

def click_btn(txt, timeout=4000):
    try:
        s.page.get_by_role("button", name=txt, exact=False).first.click(timeout=timeout)
        return True
    except Exception:
        return False

# kick off Remix -> Grant access dialog
s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('Remix')); if(e)e.click(); }""")
s.page.wait_for_timeout(2500)

state = "start"
for i in range(60):  # up to 10 min
    time.sleep(8)
    b = body()
    if "Grant access to your Google One" in b:
        if click_btn("Grant access"):
            print(f"[{i*8}s] clicked Grant access BUTTON"); state="grant"
        s.page.wait_for_timeout(1500); continue
    if "Choose an account" in b and "rrogel@gmail.com" in b:
        if click_btn("rrogel@gmail.com") or s.page.get_by_text("rrogel@gmail.com").first.click(timeout=3000):
            print(f"[{i*8}s] clicked account"); state="acct"
        s.page.wait_for_timeout(1500); continue
    if "signing back in" in b:
        if click_btn("Continue"):
            print(f"[{i*8}s] clicked Continue (sign-in)"); state="signin"
        s.page.wait_for_timeout(1500); continue
    if "wants access" in b or "Google Flow Music wants access" in b:
        if click_btn("Continue"):
            print(f"[{i*8}s] clicked Continue (consent)"); state="consent"
        s.page.wait_for_timeout(1500); continue
    if "Enter code" in b or "verification code" in b or "digite o código" in b.lower() or "Enter the code" in b:
        print(f"[{i*8}s] *** 2FA CODE SCREEN *** {b[:150]}")
        state="2fa"; break
    if "Extend" in b or ("Remix" in b and "Grant access" not in b) or "Make longer" in b or "duration" in b.lower():
        print(f"[{i*8}s] *** REMIX/EXTEND UI *** {b[:150]}")
        state="remix"; break
    if i % 4 == 0:
        print(f"[{i*8}s] state={state} ... {b[:110]}")

info = s.page.evaluate("""() => { const out={texts:[],buttons:[]};
  document.querySelectorAll('button,[role=button],input,select,[role=option]').forEach(e=>{
    const t=(e.innerText||'').trim().replace(/\\s+/g,' '); const al=e.getAttribute('aria-label')||'';
    if(t&&t.length<60)out.texts.push(t.slice(0,60)); if(al)out.buttons.push(al.slice(0,60)); });
  out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,600); return out; }""")
print("FINAL STATE:", state)
print("FINAL TEXTS:", info['texts'][:40])
print("FINAL BUTTONS:", info['buttons'][:40])
print("FINAL BODY:", info['body'][:500])
s.close()
