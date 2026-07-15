#!/usr/bin/env python3
import tools.producer_common as C, json, time

s = C.ProducerSession()
CLIP = "0a593956-a491-41c5-9cbc-4560ae0fb603"
clips = s.list_clips(limit=30)
conv = next((c['operation'].get('conversation_id') for c in clips if c['id'] == CLIP), None)
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

def click_and_dump(label, aria_substr):
    print(f"\n===== {label} =====")
    clicked = s.page.evaluate("""(sub) => {
       const els=[...document.querySelectorAll('button,[role=button]')];
       const e=els.find(x=>(x.getAttribute('aria-label')||'').includes(sub));
       if(e){ e.click(); return true; } return false;
    }""", aria_substr)
    print("clicked:", clicked)
    s.page.wait_for_timeout(2500)
    # dump visible dialog/menu text and buttons
    info = s.page.evaluate("""() => {
       const out={texts:[], buttons:[]};
       // look for dialog/menu/popover
       const roots=[...document.querySelectorAll('[role=dialog],[role=menu],[role=listbox],[data-state=open]')];
       let scope=document;
       // prefer the most recently opened popover: pick element containing 'Remix' or 'Extend' or 'duration'
       for(const r of roots){ if(r.innerText && /remix|extend|duration|length|minute|longer|version/i.test(r.innerText)){ scope=r; break; } }
       scope.querySelectorAll('button,[role=button],a,input,select,[role=option]').forEach(e=>{
          const t=(e.innerText||'').trim().replace(/\\s+/g,' ');
          const al=e.getAttribute('aria-label')||'';
          if(t) out.texts.push(t.slice(0,50));
          if(al && (e.tagName==='BUTTON'||e.getAttribute('role')==='button')) out.buttons.push(al.slice(0,50));
       });
       out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,600);
       return out;
    }""")
    print("TEXTS:", info['texts'][:40])
    print("BUTTONS:", info['buttons'][:40])
    print("BODY:", info['body'][:400])
    s.page.keyboard.press("Escape")
    s.page.wait_for_timeout(800)

click_and_dump("REMIX", "Remix")
click_and_dump("MORE OPTIONS", "More options")

s.close()
