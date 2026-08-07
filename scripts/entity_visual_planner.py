#!/usr/bin/env python3
"""Topic-agnostic entity, event and evidence planner.

Commercial pipeline contract:
- research.canonicalTitle / resolvedSubject is the single source of truth;
- research.entityType is authoritative;
- scene.visualQueries from the AI-grounded script are authoritative for image search;
- later stages never reinterpret the topic into a different subject.
"""
from __future__ import annotations
import argparse, json, re, unicodedata
from pathlib import Path
try:
    from .visual_planner import apply_visual_plans
except ImportError:
    from visual_planner import apply_visual_plans
YEAR=re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")
NAME=re.compile(r"\b(?:[A-ZÀ-ỸĐ][\wÀ-ỹĐđ]+(?:\s+|$)){2,6}")
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
def classify_main_entity(subject,supplied_type="",categories=None):
 if supplied_type in {"person","event","organization","place","concept","object","company"}:return "organization" if supplied_type=="company" else supplied_type
 cats=" ".join(categories or []).casefold()
 if any(k in cats for k in ("tàu","ship","aircraft","máy bay","phương tiện","sản phẩm")):return "object"
 if any(k in cats for k in ("công ty","company","tập đoàn","organization","tổ chức")):return "organization"
 if any(k in cats for k in ("trận","chiến dịch","sự kiện","disaster","thảm họa","cách mạng")):return "event"
 if any(k in cats for k in ("sinh năm","mất năm","doanh nhân","nhà sáng lập","nhân vật")):return "person"
 return "concept"
def build_search_queries(subject,event="",location="",objects=None,entity_type="concept"):
 objects=objects or []
 if entity_type=="person":q=[subject,f"{subject} portrait",f"{subject} archival photo",f"{subject} historical photograph"]
 elif entity_type=="object":q=[subject,f"{subject} historical photo",f"{subject} archive",f"{subject} exterior"]
 elif entity_type in {"organization","company"}:q=[subject,f"{subject} headquarters",f"{subject} historical photo",f"{subject} product"]
 else:q=[subject,f"{subject} historical photo",f"{subject} documentary photograph"]
 if event:q += [event,f"{event} historical photo"]
 if location:q += [location,f"{location} historical photo"]
 q += list(objects[:2]);return _unique(q)[:12]
def plan_entities(story,topic=None):
 topic=_clean(topic or story.get("topic") or story.get("title"));scenes=story.get("scenes") or [];research=story.get("research") or {};supplied=story.get("entities") or {}
 subject=_clean(research.get("canonicalTitle") or research.get("canonicalSubject") or research.get("resolvedSubject") or story.get("resolvedSubject") or supplied.get("mainEntity"))
 if not subject:raise RuntimeError("Thiếu canonical subject từ research stage; dừng trước visual planning")
 supplied_type=_clean(research.get("entityType") or story.get("resolvedEntityType") or supplied.get("mainEntityType"))
 entity_type=classify_main_entity(subject,supplied_type,research.get("categories") or [])
 text=" ".join([topic]+[_clean(s.get("narration") or s.get("loi_dan")) for s in scenes]);years=_unique(YEAR.findall(text));locations=_unique(supplied.get("locations",[]))
 for marker in PLACE_WORDS:locations += _unique(re.findall(rf"\b{re.escape(marker)}\s+([A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+){{0,3}})",text))
 locations=_unique(locations);events=[]
 for scene in scenes:events.append(_clean(scene.get("event") or scene.get("headline")))
 events=_unique(events);objects=_unique(supplied.get("visualObjects",[]))
 plan={"mainEntity":subject,"mainEntityType":entity_type,"secondaryEntities":_unique(supplied.get("secondaryEntities",[])),"locations":locations,"timePeriods":years,"organizations":_unique(supplied.get("organizations",[])),"events":events,"visualObjects":objects,"mapsNeeded":[f"Bản đồ {p}" for p in locations[:3]],"chartsNeeded":["Dòng thời gian"] if years else [],"archivalSearchTerms":build_search_queries(subject,events[0] if events else "",locations[0] if locations else "",objects,entity_type)}
 for scene in scenes:
  narration=_clean(scene.get("narration") or scene.get("loi_dan"));scene_years=YEAR.findall(narration);location=next((p for p in locations if _norm(p) in _norm(narration)),"");event=_clean(scene.get("event") or scene.get("headline"));roles=["paper-background","texture","main-subject","context-evidence","data-map-icon","annotation","typography"]
  ai_queries=_unique(scene.get("visualQueries") or scene.get("visual_queries") or [])
  # Ưu tiên visualQueries do story/research tạo cho từng scene. Chỉ dùng fallback khi AI không cung cấp.
  fallback_queries=build_search_queries(subject,event,location,objects,entity_type) if not ai_queries else []
  search_queries=_unique(ai_queries+fallback_queries)[:12]
  # Không dùng cả câu narration làm event/query vì dễ kéo ảnh lệch chủ đề.
  visual_evidence=_unique([event,location]+objects)[:4]
  scene["entityVisualPlan"]={"mainSubject":subject,"mainSubjectType":entity_type,"identityRequired":entity_type=="person","supportingSubjects":_unique(_names(narration))[:4],"location":location,"timePeriod":scene_years[0] if scene_years else "","event":event,"visualEvidence":visual_evidence,"searchQueries":search_queries,"assetRoles":roles};scene["assetRoles"]=roles
 story["entityVisualPlan"]=plan;story["resolvedEntityType"]=entity_type;story["topic"]=topic;apply_visual_plans(story);return story
def main():
 p=argparse.ArgumentParser();p.add_argument("--story",default="assets/story.json");p.add_argument("--topic");a=p.parse_args();path=Path(a.story);story=plan_entities(json.loads(path.read_text(encoding="utf-8")),a.topic);path.write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding="utf-8");print(f"VISUAL ENTITY: {story['entityVisualPlan']['mainEntity']} ({story['resolvedEntityType']})")
if __name__=="__main__":main()
