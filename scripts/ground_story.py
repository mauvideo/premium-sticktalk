#!/usr/bin/env python3
"""Research-first story planning for arbitrary Vox documentary topics."""
from __future__ import annotations
import argparse, json, re, unicodedata, urllib.parse, urllib.request
from pathlib import Path
API="https://vi.wikipedia.org/w/api.php"; USER_AGENT="premium-sticktalk/4.4 (research-first-story-engine)"
BANNED_FILLER=("mỗi bước nhỏ","đừng bỏ cuộc","động lực","khẩu hiệu","nút thắt","câu hỏi đúng","hành động rõ ràng","phản ứng quen thuộc","tình huống rất cụ thể","một lựa chọn đang","đổi hướng đúng chỗ")
GENERIC_PREFIXES=("lịch sử","cuộc đời","tiểu sử","sự nghiệp","câu chuyện về","tìm hiểu về","video về","kể về","giới thiệu về","phim về")
GENERIC_CONNECTORS=("và hành trình","và câu chuyện","và quá trình","và sự nghiệp","và những","qua các","từ khi","đến khi")
STOP_WORDS={"lịch","sử","cuộc","đời","tiểu","sự","nghiệp","câu","chuyện","tìm","hiểu","video","phim","về","của","và","theo","hành","trình","tạo","nên","quá","trình","những","qua","các","đến","khi","từ","vì","sao","con","tàu","không","thể","lại","ngay","chuyến","đầu","tiên"}
def _get(params):
 q=urllib.parse.urlencode({**params,"format":"json","origin":"*"}); r=urllib.request.Request(f"{API}?{q}",headers={"User-Agent":USER_AGENT});
 with urllib.request.urlopen(r,timeout=25) as x:return json.load(x)
def _normalize(v): return " ".join(re.findall(r"[\wÀ-ỹĐđ]+",unicodedata.normalize("NFKC",v).casefold()))
def _tokens(v): return [t for t in _normalize(v).split() if len(t)>1]
def subject_from_prompt(topic):
 s=re.sub(r"\s+"," ",topic).strip(" .,:;-_\"'“”")
 changed=True
 while changed:
  changed=False; low=s.casefold()
  for p in GENERIC_PREFIXES:
   m=p+" "
   if low.startswith(m): s=s[len(m):].strip(" .,:;-_\"'“”"); changed=True; break
 low=s.casefold(); cuts=[low.find(m) for m in GENERIC_CONNECTORS if low.find(m)>0]
 if cuts:s=s[:min(cuts)].strip(" .,:;-_\"'“”")
 # Descriptive title: resolve the leading named entity before ':' as encyclopedia subject.
 # Example: Titanic: Vì sao... -> Titanic. This remains generic for arbitrary topics.
 if ":" in s:
  lead=s.split(":",1)[0].strip(" .,:;-_\"'“”")
  if lead:s=lead
 if not s: raise RuntimeError(f"Không xác định được chủ thể chính từ yêu cầu: {topic}")
 return s
def _candidate_score(title,subject,i):
 tn,sn=_normalize(title),_normalize(subject); st=[t for t in _tokens(subject) if t not in STOP_WORDS]; tt=set(_tokens(title)); ov=sum(t in tt for t in st); score=ov*20
 if tn==sn:score+=100
 elif sn in tn:score+=45
 if st and ov==len(st):score+=35
 return (-score,i)
def _validate_resolution(topic,subject,canonical):
 st=[t for t in _tokens(subject) if t not in STOP_WORDS]; ct=set(_tokens(canonical)); ov=[t for t in st if t in ct]
 if not st:return
 minimum=1 if len(st)<=2 else max(2,(len(st)+1)//2)
 if len(ov)<minimum:raise RuntimeError(f"Wikipedia đã trả về sai chủ đề. Yêu cầu='{topic}', chủ thể='{subject}', kết quả='{canonical}'.")
def research_topic(topic):
 subject=subject_from_prompt(topic); variants=[f'intitle:"{subject}"',f'"{subject}"',subject]; combined=[]; seen=set()
 for qt in variants:
  search=_get({"action":"query","list":"search","srsearch":qt,"srlimit":10,"utf8":1})
  for item in search.get("query",{}).get("search",[]):
   title=str(item.get("title") or "").strip()
   if title and title not in seen:seen.add(title);combined.append(item)
  if any(_normalize(x.get("title",""))==_normalize(subject) for x in combined):break
 if not combined:raise RuntimeError(f"Không tìm thấy nguồn nghiên cứu cho chủ đề: {topic}")
 ranked=sorted(enumerate(combined),key=lambda p:_candidate_score(str(p[1].get("title") or ""),subject,p[0])); title=str(ranked[0][1]["title"])
 page=_get({"action":"query","prop":"extracts|pageimages|info|categories","titles":title,"explaintext":1,"exsectionformat":"plain","piprop":"original|thumbnail","pithumbsize":1600,"inprop":"url","cllimit":30,"redirects":1}); data=next(iter(page.get("query",{}).get("pages",{}).values()),{}); canonical=str(data.get("title") or title); _validate_resolution(topic,subject,canonical)
 extract=re.sub(r"\s+"," ",str(data.get("extract") or "")).strip()
 if len(extract)<180:raise RuntimeError(f"Nguồn nghiên cứu quá ít dữ liệu cho chủ đề: {topic}")
 cats=[str(x.get("title","")).replace("Thể loại:","") for x in data.get("categories",[])]; image=data.get("original") or data.get("thumbnail") or {}
 return {"topicInput":topic,"resolvedSubject":subject,"canonicalTitle":canonical,"sourceUrl":str(data.get("fullurl") or ""),"provider":"vi.wikipedia.org","extract":extract,"categories":cats,"leadImageUrl":str(image.get("source") or "")}
def split_sentences(text):return [s.strip() for s in re.split(r"(?<=[.!?])\s+",text) if len(s.strip())>35]
def sentence_score(s,subject):
 n=_normalize(s); score=8 if _normalize(subject) in n else 0
 if re.search(r"\b(18|19|20)\d{2}\b",s):score+=5
 if any(w in n for w in ("sinh","thành lập","ra mắt","chiến dịch","phát triển","được bổ nhiệm","sáng lập","thành công","qua đời","phát minh","xây dựng")):score+=4
 if any(f in n for f in BANNED_FILLER):score-=20
 return score
def _year(s):
 m=re.search(r"\b(18|19|20)\d{2}\b",s);return int(m.group()) if m else None
def _historical_scope(t):
 n=_normalize(t);return any(p in n for p in ("lich su","cuoc doi","tieu su","su nghiep","hanh trinh"))
def _balanced_facts(sentences,subject,topic,limit=18):
 c=[s for s in sentences if sentence_score(s,subject)>=0]
 if not c:return sentences[:limit]
 if not _historical_scope(topic):return sorted(c,key=lambda s:sentence_score(s,subject),reverse=True)[:limit]
 dated=[(i,s,_year(s)) for i,s in enumerate(c) if _year(s) is not None]; und=[(i,s) for i,s in enumerate(c) if _year(s) is None];dated.sort(key=lambda x:(x[2] or 9999,x[0]));chosen=[]
 if dated:
  slots=min(max(6,limit-4),len(dated))
  for n in range(slots):
   s=dated[round(n*(len(dated)-1)/max(1,slots-1))][1]
   if s not in chosen:chosen.append(s)
 for _,s in und:
  if len(chosen)>=limit:break
  if s not in chosen and sentence_score(s,subject)>=4:chosen.append(s)
 end_terms=("qua đời","từ trần","quốc tang","tang lễ","an táng","lễ viếng");out=[];ec=0
 for s in chosen:
  if any(x in _normalize(s) for x in end_terms):
   if ec>=1:continue
   ec+=1
  out.append(s)
 return out[:limit]
def _entities(s,canonical):
 e=[canonical]
 for n in re.findall(r"\b[A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+){0,4}",s):
  if n not in e and len(n)>3:e.append(n)
 return e[:6]
def _places(s):return list(dict.fromkeys(re.findall(r"(?:tại|ở|đến|từ)\s+([A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+){0,3})",s)))[:4]
def _scene_visual_plan(s,canonical,index):
 year=str(_year(s) or "");places=_places(s);entities=_entities(s,canonical);event=re.sub(r"\s+"," ",s).strip()[:150];queries=[canonical,f'"{canonical}" {year}'.strip(),f'"{canonical}" {event[:70]}'.strip()]
 if places:queries.append(f'"{canonical}" {places[0]}')
 queries.append(f'{event[:90]} historical photo')
 return {"mainCharacter":canonical,"event":event,"time":year,"location":places[0] if places else "","entities":entities,"assetQueries":list(dict.fromkeys(q for q in queries if q.strip())),"icons":["timeline","document"] if year else ["document","map"],"dataLayers":[year] if year else [],"secondaryObjects":entities[1:3],"paperElements":["newspaper","grid"],"background":"paper-grid","camera":["push-in","pan-left","pan-right","parallax"][index%4],"transition":"paper-swipe","highlight":year or canonical}
def build_story(story,topic):
 research=research_topic(topic);subject=research["canonicalTitle"];sentences=split_sentences(research["extract"]);facts=_balanced_facts(sentences,subject,topic,limit=max(16,len(story.get("scenes",[]))*2))
 if len(facts)<4:raise RuntimeError(f"Nguồn nghiên cứu không đủ dữ kiện riêng cho chủ đề: {topic}")
 scenes=story.get("scenes") or []
 if not scenes:raise RuntimeError("Kịch bản không có scene để biên tập.")
 story["title"]=topic.strip(" \"'“”");story["research"]=research;story["resolvedSubject"]=subject;story["researchFacts"]=facts
 for i,scene in enumerate(scenes):
  fact=facts[min(i,len(facts)-1)];scene["narration"]=fact;scene["headline"]=subject if i==0 else (str(_year(fact) or "") or subject);scene["keywords"]=list(dict.fromkeys([subject,*_places(fact),str(_year(fact) or "")]))[:5];scene["visualPlan"]=_scene_visual_plan(fact,subject,i)
 return story
def main():
 p=argparse.ArgumentParser();p.add_argument("story");p.add_argument("--topic",required=True);p.add_argument("--output");a=p.parse_args();path=Path(a.story);story=json.loads(path.read_text(encoding="utf-8"));story=build_story(story,a.topic);out=Path(a.output) if a.output else path;out.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding="utf-8");Path("assets/research.json").write_text(json.dumps(story["research"],ensure_ascii=False,indent=2),encoding="utf-8");print(f"Đã nghiên cứu và lập kịch bản theo chủ đề: {story['resolvedSubject']}")
if __name__=="__main__":main()
