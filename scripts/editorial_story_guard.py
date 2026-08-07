#!/usr/bin/env python3
"""Editorial guard for broad documentary prompts.

Prevents a broad request such as "lịch sử X" / "cuộc đời X" from collapsing
into one late-life subtopic. This module is topic-agnostic: it works from the
current story's canonical subject and Wikipedia source, never a hard-coded name.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API='https://vi.wikipedia.org/w/api.php'
UA='premium-sticktalk/7.0 (editorial-story-guard)'
BROAD_PREFIXES=('lịch sử','cuộc đời','tiểu sử','sự nghiệp','câu chuyện về','tìm hiểu về')
LATE_WORDS=('qua đời','từ trần','tang lễ','quốc tang','an táng','mai táng','lễ viếng')


def get_page(title:str)->str:
    q=urllib.parse.urlencode({'action':'query','format':'json','origin':'*','prop':'extracts','titles':title,'explaintext':1,'exsectionformat':'plain','redirects':1})
    req=urllib.request.Request(f'{API}?{q}',headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=25) as r:
        data=json.load(r)
    page=next(iter(data.get('query',{}).get('pages',{}).values()),{})
    return re.sub(r'\s+',' ',str(page.get('extract') or '')).strip()


def sentences(text:str)->list[str]:
    out=[]
    for s in re.split(r'(?<=[.!?])\s+',text):
        s=s.strip()
        if 45<=len(s)<=320 and s not in out:
            out.append(s)
    return out


def year(s:str)->int|None:
    m=re.search(r'\b(18|19|20)\d{2}\b',s)
    return int(m.group()) if m else None


def select_chronology(items:list[str],count:int)->list[str]:
    dated=[(year(s),i,s) for i,s in enumerate(items) if year(s)]
    dated.sort(key=lambda x:(x[0],x[1]))
    if not dated:
        step=max(1,len(items)//max(1,count))
        return items[::step][:count]
    # Divide the entire dated history into equal editorial bands. This gives
    # birth/early period, development, turning points and later legacy a fair
    # chance instead of ranking only the most keyword-dense sentences.
    picked=[]
    for n in range(count):
        idx=round(n*(len(dated)-1)/max(1,count-1))
        s=dated[idx][2]
        if s not in picked: picked.append(s)
    for _,_,s in dated:
        if len(picked)>=count: break
        if s not in picked: picked.append(s)
    return picked[:count]


def main(path:Path,topic:str):
    story=json.loads(path.read_text(encoding='utf-8'))
    scenes=story.get('scenes') or story.get('canh') or []
    if not scenes: return
    broad=topic.casefold().strip().startswith(BROAD_PREFIXES)
    if not broad: return
    research=story.get('research') or {}
    canonical=str(research.get('canonicalTitle') or story.get('title') or '').strip()
    if not canonical: return
    text=get_page(canonical)
    pool=sentences(text)
    facts=select_chronology(pool,len(scenes))
    if len(facts)<len(scenes):
        print('EDITORIAL GUARD: nguồn chưa đủ để thay toàn bộ cảnh; giữ kịch bản hiện tại.')
        return
    # A broad biography/history must not be dominated by death/funeral facts.
    late=sum(any(w in f.casefold() for w in LATE_WORDS) for f in facts)
    max_late=max(1,len(scenes)//5)
    if late>max_late:
        replacements=[s for s in pool if not any(w in s.casefold() for w in LATE_WORDS) and s not in facts]
        for i in range(len(facts)-1,-1,-1):
            if late<=max_late: break
            if any(w in facts[i].casefold() for w in LATE_WORDS) and replacements:
                facts[i]=replacements.pop(0); late-=1
    for i,(scene,fact) in enumerate(zip(scenes,facts)):
        y=re.search(r'\b(?:18|19|20)\d{2}\b',fact)
        yv=y.group() if y else ''
        narration=re.sub(r'\s+',' ',fact).strip()
        if len(narration)>210:
            narration=narration[:207].rsplit(' ',1)[0]+'...'
        scene['narration']=scene['loi_dan']=narration
        scene['newFact']=scene['event']=fact
        scene['timeMarker']=yv
        scene['headline']=(f'{yv} · {canonical}' if yv else canonical)
        scene['text']=scene['headline']
        scene['mainSubject']=canonical
        scene['keywords']=[canonical]+([yv] if yv else [])
        scene['visualEvidence']=[fact]
        plan=scene.setdefault('entityVisualPlan',{})
        plan.update({
            'mainSubject':canonical,
            'identityRequired':bool(research.get('entityType')=='person' and i==0),
            'event':fact,'timePeriod':yv,'visualEvidence':[fact],
            'searchQueries':[f'"{canonical}" {yv}'.strip(),f'"{canonical}" historical photo',fact[:120]],
            'iconQueries':[f'{yv or "timeline"} timeline icon',f'{canonical} documentary icon'],
        })
    story.setdefault('research',{})['editorialIntent']='broad-history' if 'lịch sử' in topic.casefold() else 'broad-biography'
    story['research']['editorialGuard']='chronological-coverage-v1'
    path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'EDITORIAL GUARD: {canonical} — {len(scenes)} cảnh phủ theo tiến trình, late-life scenes={late}/{len(scenes)}')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--story',default='assets/story.json'); ap.add_argument('--topic',required=True)
    a=ap.parse_args(); main(Path(a.story),a.topic)
