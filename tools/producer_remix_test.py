#!/usr/bin/env python3
"""Test if Remix/Extend now works (Google One granted). Click Remix, then Grant access."""
import tools.producer_common as C, json, time

s = C.ProducerSession()
clips = s.list_clips(limit=10)
# use a recent clip
CLIP = clips[0]["id"]
conv = clips[0]["operation"].get("conversation_id")
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

# click Remix
s.page.evaluate("""() => { const e=[...document.querySelectorAll('button,[role=button]')]
  .find(x=>(x.getAttribute('aria-label')||'').includes('Remix')); if(e)e.click(); }""")
s.page.wait_for_timeout(2500)
body1 = s.page.evaluate("()=>document.body.innerText.replace(/\\n+/g,' | ').slice(0,200)")
print("AFTER REMIX:", body1)

# if Grant dialog, click "Grant access"
granted = s.page.evaluate("""() => { const els=[...document.querySelectorAll('button,[role=button]')];
  const g=els.find(x=>(x.innerText||'').trim()==='Grant access'); if(g){g.click(); return true;} return false; }""")
print("Grant access clicked:", granted)
s.page.wait_for_timeout(4000)

def dump(tag):
    info = s.page.evaluate("""() => {
       const out={texts:[],buttons:[]};
       document.querySelectorAll('button,[role=button],input,select,[role=option]').forEach(e=>{
          const t=(e.innerText||'').trim().replace(/\\s+/g,' ');
          const al=e.getAttribute('aria-label')||'';
          if(t && t.length<60) out.texts.push(t.slice(0,60));
          if(al) out.buttons.push(al.slice(0,60));
       });
       out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,600);
       return out;
    }""")
    print(f"--- {tag} ---")
    print("TEXTS:", info['texts'][:40])
    print("BUTTONS:", info['buttons'][:40])
    print("BODY:", info['body'][:500])

dump("AFTER GRANT")
s.close()
