#!/usr/bin/env python3
"""Drive Google One grant: Remix -> Grant access -> choose account -> wait 2FA -> check Remix dialog."""
import tools.producer_common as C, json, time, sys

s = C.ProducerSession()
clips = s.list_clips(limit=10)
CLIP = clips[0]["id"]
conv = clips[0]["operation"].get("conversation_id")
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

def body():
    return s.page.evaluate("()=>document.body.innerText.replace(/\\n+/g,' | ').slice(0,300)")

# Remix
s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('Remix')); if(e)e.click(); }""")
s.page.wait_for_timeout(2500)
# Grant access
s.page.evaluate("""() => { const els=[...document.querySelectorAll('button,[role=button]')];
  const g=els.find(x=>(x.innerText||'').trim()==='Grant access'); if(g){g.click(); return true;} return false; }""")
s.page.wait_for_timeout(3000)
print("after grant:", body())

# choose account rrogel@gmail.com
clicked_acct = s.page.evaluate("""() => {
  const els=[...document.querySelectorAll('div,[role=button],button')];
  const a=els.find(x=>(x.innerText||'').includes('rrogel@gmail.com'));
  if(a){ a.click(); return true; } return false; }""")
print("account clicked:", clicked_acct)
s.page.wait_for_timeout(3000)
print("after account:", body())

# poll for 2FA / remix dialog
for i in range(36):  # up to 6 min
    time.sleep(10)
    b = body()
    if "Enter code" in b or "verification code" in b or "tap" in b or "phone" in b.lower():
        print(f"[{i*10}s] 2FA likely needed. Body: {b[:200]}")
        break
    if "Extend" in b or "Remix" in b or "duration" in b.lower():
        print(f"[{i*10}s] remix/extend UI? Body: {b[:200]}")
        break
    if "Google Flow Music" in b and "Grant access" not in b and "Choose an account" not in b:
        print(f"[{i*10}s] back on app? Body: {b[:200]}")
        break
    if i % 3 == 0:
        print(f"[{i*10}s] waiting... {b[:120]}")

# final dump of buttons
info = s.page.evaluate("""() => { const out={texts:[],buttons:[]};
  document.querySelectorAll('button,[role=button],input,select,[role=option]').forEach(e=>{
    const t=(e.innerText||'').trim().replace(/\\s+/g,' '); const al=e.getAttribute('aria-label')||'';
    if(t&&t.length<60)out.texts.push(t.slice(0,60)); if(al)out.buttons.push(al.slice(0,60)); });
  out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,500); return out; }""")
print("FINAL TEXTS:", info['texts'][:30])
print("FINAL BUTTONS:", info['buttons'][:30])
print("FINAL BODY:", info['body'][:400])
s.close()
