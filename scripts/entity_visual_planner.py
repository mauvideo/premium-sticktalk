#!/usr/bin/env python3
"""Topic-agnostic entity, event and evidence planner.

The research stage is the single source of truth for the visual subject. Story
metadata may suggest secondary entities, but it may never replace the resolved
Wikipedia subject (this prevents labels such as 'Nhạc chủ đề' from becoming the
main visual identity).
"""
from __future__ import annotations
import argparse, json, re, unicodedata
from pathlib import Path
try:
    from .visual_planner import apply_visual_plans
except ImportError:
    from visual_planner import apply_visual_plans
YEAR=re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b"); NAME=re.compile(r"\b(?:[A-ZÀ-ỸĐ][\wÀ-ỹĐđ]+(?:\s+|$)){2,6}")
PLACE_WORDS={"tại","ở","từ","đến","thành phố","tỉnh","nước","in","at","from","to"}
def _clean(v):return " ".join(str(v or "").strip().split())
def _norm(v):return unicodedata.normalize("NFKC",_clean(v)).casefold()
def _unique(values):
 out=[];seen=set()
 for value in values:
  value=_clean(value).strip(" ,.;:–—-");key=_norm(value)
  if value and key not in seen:seen.add(key);out.append(value)
 return out
def _names(text):return _unique(m.group(0) for m in NAME.finditer(text))
def _topic_subject(topic):
 s=re.sub(r"^(?:cuộc đời|tiểu sử|lịch sử|hành trình|câu chuyện)\s+","",topic,flags=re.I)
 if ":" in s:s=s.split(":",1)[0]
 for marker in (" và hành trình "," và câu chuyện "," và sự nghiệp "):
  p=s.casefold().find(marker)
  if p>0:s=s[:p];break
 return _clean(s) or _clean(topic)
def classify_main_entity(subject,supplied_type="",categories=None):
 cats=" ".join(categories or []).casefold()
 # Encyclopedia evidence wins over generated story metadata.
 if any(k in cats for k in ("tàu","ship","ocean liner","aircraft","máy bay","phương tiện","sản phẩm")):return "object"
 if any(k in cats for k in ("công ty","company","tập đoàn","organization","tổ chức")):return "organization"
 if any(k in cats for k in ("trận","chiến dịch","sự kiện","disaster","thảm họa")):return "event"
 if any(k in cats for k in ("sinh năm","mất năm","người mỹ","người việt","doanh nhân","nhà sáng lập","nhân vật")):return "person"
 if supplied_type in {"person","event","organization","place","concept","object","company"}:return "organization" if supplied_type=="company" else supplied_type
 lower=subject.casefold()
 if re.match(r"^(?:vì sao|tại sao|cách|how|why)\b",lower):return "concept"
 words=subject.split();caps=sum(bool(re.match(r"^[A-ZÀ-ỸĐ]",w)) for w in words)
 if 2<=len(words)<=5 and caps>=max(2,len(words)-1):return "person"
 return "concept"
def build_search_queries(subject,event="",location="",objects=None,entity_type="concept"):
 objects=objects or []
 if entity_type=="person":q=[subject,f"{subject} portrait",f"{subject} archival photo",f"{subject} historical photograph"]
 elif entity_type=="object":q=[subject,f"{subject} historical photo",f"{subject} archive",f"{subject} exterior"]
 elif entity_type in {"organization","company"}:q=[subject,f"{subject} headquarters",f"{subject} historical photo",f"{subject} product"]
 else:q=[subject,f"{subject} historical photo",f"{subject} documentary photograph"]
 if event:q += [event,f"{event} historical photo"]
 if location:q += [location,f"{location} historical photo"]
 q += list(objects[:2]);return _unique(q)[:10]
def plan_entities(story,topic=None):
 topic=_clean(topic or story.get("topic") or story.get("title") or story.get("tieu_de"));scenes=story.get("scenes") or [];research=story.get("research") or {};supplied=story.get("entities") or {}
 # CRITICAL: researched canonical subject comes first. Generated `entities.mainEntity`
 # is only a fallback and cannot hijack the visual pipeline.
 subject=_clean(research.get("canonicalTitle") or research.get("resolvedSubject") or story.get("resolvedSubject") or supplied.get("mainEntity") or _topic_subject(topic))
 supplied_type=_clean(research.get("entityType") or story.get("resolvedEntityType") or supplied.get("mainEntityType"))
 entity_type=classify_main_entity(subject,supplied_type,research.get("categories") or [])
 text=" ".join([topic]+[_clean(s.get("narration") or s.get("loi_dan") or s.get("text")) for s in scenes]);candidates=[n for n in _names(text) if _norm(n) not in {_norm(topic),_norm(subject)}];years=_unique(YEAR.findall(text));locations=_unique(supplied.get("locations",[]))
 for marker in PLACE_WORDS:locations += _unique(re.findall(rf"\b{re.escape(marker)}\s+([A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+){{0,3}})",text))
 locations=_unique(locations);events=_unique(supplied.get("events",[]))
 for scene in scenes:events.append(_clean(scene.get("event") or scene.get("headline") or scene.get("sceneRole")))
 events=_unique(events);objects=_unique(supplied.get("visualObjects",[])) or ["tài liệu gốc","mốc thời gian","ảnh bối cảnh"]
 plan={"mainEntity":subject,"mainEntityType":entity_type,"secondaryEntities":_unique(candidates+supplied.get("secondaryEntities",[]))[:12],"locations":locations,"timePeriods":_unique(supplied.get("timePeriods",[])+years),"organizations":_unique(supplied.get("organizations",[])),"events":events,"visualObjects":objects,"mapsNeeded":[f"Bản đồ {p}" for p in locations[:3]],"chartsNeeded":["Dòng thời gian"] if years else [],"archivalSearchTerms":build_search_queries(subject,events[0] if events else "",locations[0] if locations else "",objects,entity_type)}
 for i,scene in enumerate(scenes):
  narration=_clean(scene.get("narration") or scene.get("loi_dan") or scene.get("text"));scene_years=YEAR.findall(narration);location=next((p for p in locations if _norm(p) in _norm(narration)),"");event=_clean(scene.get("event") or scene.get("headline") or narration[:120]);roles=["paper-background","texture","main-subject","context-evidence","data-map-icon","annotation","typography"]
  scene["entityVisualPlan"]={"mainSubject":subject,"mainSubjectType":entity_type,"identityRequired":entity_type=="person","supportingSubjects":_unique(_names(narration)+plan["secondaryEntities"])[:4],"location":location,"timePeriod":scene_years[0] if scene_years else "","event":event,"visualEvidence":_unique([event,location]+objects)[:4],"searchQueries":build_search_queries(subject,event,location,objects,entity_type),"assetRoles":roles};scene["assetRoles"]=roles
 story["entityVisualPlan"]=plan;story["resolvedEntityType"]=entity_type;story["topic"]=topic;apply_visual_plans(story);return story
def main():
 p=argparse.ArgumentParser();p.add_argument("--story",default="assets/story.json");p.add_argument("--topic");a=p.parse_args();path=Path(a.story);story=plan_entities(json.loads(path.read_text(encoding="utf-8")),a.topic);path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding="utf-8");print(f"VISUAL ENTITY: {story['entityVisualPlan']['mainEntity']} ({story['resolvedEntityType']})")
if __name__=="__main__":main()
