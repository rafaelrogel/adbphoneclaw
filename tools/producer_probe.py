#!/usr/bin/env python3
"""Probe Remix/More-options after Google One grant. Find Extend/duration."""
import tools.producer_common as C, json, time

s = C.ProducerSession()
clips = s.list_clips(limit=10)
conv = clips[0]["operation"].get("conversation_id")
s.page.goto("https://www.flowmusic.app/session/" + conv, timeout=60000)
s.page.wait_for_timeout(5000)

def dump(tag):
    info = s.page.evaluate("""function(){
      var out={texts:[],buttons:[],pop:''};
      document.querySelectorAll('button,[role=button],input,select,[role=option],textarea,[role=radio],[role=slider]').forEach(function(e){
        var t=(e.innerText||'').trim().replace(/\\s+/g,' ');
        var al=e.getAttribute('aria-label')||'';
        var ph=e.getAttribute('placeholder')||'';
        if(t&&t.length<60){out.texts.push(t.slice(0,60));}
        if(al||ph){out.buttons.push((al+(ph?('|ph:'+ph):'')).slice(0,60));}
      });
      var pop=document.querySelector('[role=dialog],[role=menu],[role=listbox]');
      out.body=document.body.innerText.replace(/\\n+/g,' | ').slice(0,900);
      if(pop){out.pop=pop.innerText.replace(/\\n+/g,' | ').slice(0,300);}
      return out;
    }""")
    print("=== " + tag + " ===")
    print("TEXTS:", info['texts'][:60])
    print("BTNS:", info['buttons'][:60])
    print("POPUP:", info['pop'])
    print("BODY:", info['body'][:700])

# 1) More options (ellipsis)
s.page.evaluate("""function(){
  var arr=document.querySelectorAll('button,[role=button]');
  for(var i=0;i<arr.length;i++){ if((arr[i].getAttribute('aria-label')||'').indexOf('More options')>=0){arr[i].click();return;} }
}""")
s.page.wait_for_timeout(2500)
dump("after-more-options")

# click any extend/length option if present
s.page.evaluate("""function(){
  var arr=document.querySelectorAll('button,[role=button],[role=menuitem],[role=option]');
  for(var i=0;i<arr.length;i++){
    var t=arr[i].innerText||arr[i].getAttribute('aria-label')||'';
    if(/extend|make longer|5:00|5 min|lengthen|duration/i.test(t)){arr[i].click();return true;}
  }
  return false;
}""")
s.page.wait_for_timeout(2000)
dump("after-extend-click")

# 2) Remix -> poll for new clip
before = set(c['id'] for c in s.list_clips(limit=20))
s.page.evaluate("""function(){
  var arr=document.querySelectorAll('button,[role=button]');
  for(var i=0;i<arr.length;i++){ if((arr[i].getAttribute('aria-label')||'').indexOf('Remix')>=0){arr[i].click();return;} }
}""")
print("remix clicked, polling API for new clip...")
newclip=None
for i in range(40):
    time.sleep(5)
    cur = s.list_clips(limit=20)
    diff = set(c['id'] for c in cur) - before
    if diff:
        newclip = cur[0]
        print("[" + str(i*5) + "s] NEW CLIP " + newclip['id'] + " dur=" + str(newclip.get('duration')))
        break
    if i%4==0:
        print("[" + str(i*5) + "s] waiting new clip...")
if newclip:
    full = s.api_get("/__api/clips/" + newclip['id'])
    print("NEW CLIP DURATION:", full.get('duration'), "operation:", (full.get('operation') or {}).get('sound_prompt'))
s.close()
