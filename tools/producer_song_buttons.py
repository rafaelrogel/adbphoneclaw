#!/usr/bin/env python3
import tools.producer_common as C, json
s = C.ProducerSession()
CLIP = "0a593956-a491-41c5-9cbc-4560ae0fb603"
# open the conversation/song page for the recent clip
# find its conversation_id
clips = s.list_clips(limit=30)
conv = None
for c in clips:
    if c['id'] == CLIP:
        conv = c['operation'].get('conversation_id')
        break
print("conversation_id:", conv)
url = "https://www.flowmusic.app/session/" + conv if conv else "https://www.flowmusic.app/library/my-songs"
s.page.goto(url, timeout=60000)
s.page.wait_for_timeout(5000)
btns = s.page.evaluate("""() => {
  const out=[];
  document.querySelectorAll('button,[role=button],a[href]').forEach(e=>{
    const t=(e.innerText||'').trim().replace(/\\s+/g,' ');
    const al=e.getAttribute('aria-label')||'';
    const ic=[...e.querySelectorAll('svg')].map(s=>s.getAttribute('class')||'').join(' ');
    const cls=e.getAttribute('class')||'';
    if(t || al) out.push({t:t.slice(0,40), al:al.slice(0,40), ic:ic.slice(0,50)});
  });
  return out;
}""")
for b in btns:
    print(b)
s.close()
