#!/usr/bin/env python3
"""Google One grant via Playwright locators: click account, handle Continue, reach 2FA."""
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
s.page.wait_for_timeout(3500)
print("after grant:", body())

def click_text(txt, timeout=5000):
    try:
        s.page.get_by_text(txt, exact=False).first.click(timeout=timeout)
        return True
    except Exception as e:
        return f"err:{e}"

# click the account
r = click_text("rrogel@gmail.com")
print("click account:", r)
s.page.wait_for_timeout(3500)
print("after account:", body())

# maybe a Continue/Next button
for label in ["Continue", "Next", "Avançar", "Próximo"]:
    r2 = click_text(label, timeout=3000)
    if r2 is True:
        print("clicked", label)
        s.page.wait_for_timeout(3000)
        break

# poll for 2FA / completion
for i in range(48):
    time.sleep(10)
    b = body()
    if "Enter code" in b or "verification code" in b or "Enter the code" in b or "digite o código" in b.lower():
        print(f"[{i*10}s] 2FA CODE SCREEN. {b[:150]}")
        break
    if "Grant access" not in b and "Choose an account" not in b and ("Google Flow Music" in b or "Remix" in b or "Extend" in b or "Deny" in b or "Allow" in b):
        print(f"[{i*10}s] advanced. {b[:150]}")
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
