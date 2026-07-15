#!/usr/bin/env python3
"""Google One grant: reach 2FA step. Click account's clickable ancestor, wait for approval."""
import tools.producer_common as C, json, time

s = C.ProducerSession()
clips = s.list_clips(limit=10)
CLIP = clips[0]["id"]
conv = clips[0]["operation"].get("conversation_id")
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

def body():
    return s.page.evaluate("()=>document.body.innerText.replace(/\\n+/g,' | ').slice(0,250)")

# Remix -> Grant access
s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('Remix')); if(e)e.click(); }""")
s.page.wait_for_timeout(2500)
s.page.evaluate("""() => { const els=[...document.querySelectorAll('button,[role=button]')];
  const g=els.find(x=>(x.innerText||'').trim()==='Grant access'); if(g){g.click();} }""")
s.page.wait_for_timeout(3000)

# On chooser: click the clickable ancestor of the rrogel@gmail.com text
clicked = s.page.evaluate("""() => {
  const all=[...document.querySelectorAll('*')];
  const mail=all.find(e=>(e.innerText||'').includes('rrogel@gmail.com'));
  if(!mail) return 'no-mail';
  let el=mail;
  for(let i=0;i<6;i++){ el=el.parentElement; if(!el) break;
    const r=el.getAttribute&&el.getAttribute('role'); const on=el.getAttribute&&el.getAttribute('onclick');
    if(r==='button'||on!==null){ el.click(); return 'clicked role='+r; } }
  mail.click(); return 'clicked-mail-direct';
}""")
print("account click result:", clicked)
s.page.wait_for_timeout(4000)
print("after account:", body())

# poll for 2FA / completion
for i in range(48):  # up to 8 min
    time.sleep(10)
    b = body()
    if "Enter code" in b or "verification code" in b or "tap" in b or "Enter the code" in b:
        print(f"[{i*10}s] 2FA code screen. {b[:150]}")
        # might need to choose SMS vs phone; just report
        break
    if "Grant access" not in b and "Choose an account" not in b and ("Google Flow Music" in b or "Remix" in b or "Extend" in b):
        print(f"[{i*10}s] advanced past auth. {b[:150]}")
        break
    if i % 3 == 0:
        print(f"[{i*10}s] ... {b[:120]}")

info = s.page.evaluate("""() => { const out={texts:[],buttons:[]};
  document.querySelectorAll('button,[role=button],input,select').forEach(e=>{
    const t=(e.innerText||'').trim().replace(/\\s+/g,' '); const al=e.getAttribute('aria-label')||'';
    if(t&&t.length<60)out.texts.push(t.slice(0,60)); if(al)out.buttons.push(al.slice(0,60)); });
  out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,500); return out; }""")
print("FINAL TEXTS:", info['texts'][:30])
print("FINAL BUTTONS:", info['buttons'][:30])
print("FINAL BODY:", info['body'][:400])
s.close()
