#!/usr/bin/env python3
"""Topic-agnostic entity, event and evidence planner.

Visual identity is grounded in the subject already resolved by the research
stage.  The planner never re-interprets a long documentary title as the visual
subject and never maintains a catalogue of famous names.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

try:
    from .visual_planner import apply_visual_plans
except ImportError:
    from visual_planner import apply_visual_plans

YEAR = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")
NAME = re.compile(r"\b(?:[A-ZÀ-ỸĐ][\wÀ-ỹĐđ]+(?:\s+|$)){2,6}")
ORG_WORDS = {"công ty", "tập đoàn", "đại học", "quân đội", "company", "group", "university", "institute"}
PLACE_WORDS = {"tại", "ở", "từ", "đến", "thành phố", "tỉnh", "nước", "in", "at", "from", "to"}


def _clean(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: str) -> str:
    return unicodedata.normalize("NFKC", _clean(value)).casefold()


def _unique(values):
    seen = set(); result = []
    for value in values:
        value = _clean(value).strip(" ,.;:–—-")
        key = _norm(value)
        if value and key not in seen:
            seen.add(key); result.append(value)
    return result


def _names(text: str) -> list[str]:
    return _unique(match.group(0) for match in NAME.finditer(text))


def _topic_subject(topic: str) -> str:
    subject = re.sub(r"^(?:cuộc đời|tiểu sử|lịch sử|hành trình|câu chuyện)\s+", "", topic, flags=re.I)
    if ":" in subject:
        subject = subject.split(":", 1)[0]
    for marker in (" và hành trình ", " và câu chuyện ", " và sự nghiệp "):
        pos = subject.casefold().find(marker)
        if pos > 0:
            subject = subject[:pos]
            break
    return _clean(subject) or _clean(topic)


def classify_main_entity(subject: str, supplied_type: str = "", categories=None) -> str:
    if supplied_type in {"person", "event", "organization", "place", "concept", "object", "company"}:
        return "organization" if supplied_type == "company" else supplied_type
    cats = " ".join(categories or []).casefold()
    # Wikipedia category evidence beats title-shape heuristics.  This prevents
    # things such as "RMS Titanic" from being mistaken for a person's name.
    if any(k in cats for k in ("tàu", "ship", "aircraft", "máy bay", "phương tiện", "sản phẩm")):
        return "object"
    if any(k in cats for k in ("công ty", "company", "tập đoàn", "organization", "tổ chức")):
        return "organization"
    if any(k in cats for k in ("trận", "chiến dịch", "sự kiện", "disaster", "thảm họa")):
        return "event"
    if any(k in cats for k in ("sinh năm", "mất năm", "người mỹ", "người việt", "doanh nhân", "nhà sáng lập", "nhân vật")):
        return "person"
    lower = subject.casefold()
    if re.match(r"^(?:vì sao|tại sao|cách|how|why)\b", lower): return "concept"
    if re.match(r"^(?:lịch sử|trận|chiến dịch|sự kiện|history)\b", lower): return "event"
    words = subject.split(); title_words = sum(bool(re.match(r"^[A-ZÀ-ỸĐ]", w)) for w in words)
    if 2 <= len(words) <= 5 and title_words >= max(2, len(words) - 1): return "person"
    return "concept"


def build_search_queries(subject: str, event: str = "", location: str = "", objects=None, entity_type: str = "person") -> list[str]:
    objects = objects or []
    if entity_type == "person":
        queries = [subject, f'{subject} portrait', f'{subject} archival photo', f'{subject} historical photograph']
    elif entity_type == "object":
        queries = [subject, f'{subject} historical photo', f'{subject} exterior', f'{subject} archive']
    elif entity_type in {"organization", "company"}:
        queries = [subject, f'{subject} headquarters', f'{subject} historical photo', f'{subject} product']
    else:
        queries = [subject, f'{subject} historical photo', f'{subject} documentary photograph']
    if event:
        queries += [event, f'{event} historical photo', f'{event} archive']
    if location:
        queries += [location, f'{location} historical photo']
    for obj in objects[:2]: queries += [obj]
    return _unique(queries)


def plan_entities(story: dict, topic: str | None = None) -> dict:
    topic = _clean(topic or story.get("topic") or story.get("title") or story.get("tieu_de"))
    scenes = story.get("scenes") or []
    research = story.get("research") or {}
    supplied = story.get("entities") or {}
    # Research stage is authoritative for the visual subject.
    subject = _clean(supplied.get("mainEntity") or research.get("canonicalTitle") or research.get("resolvedSubject") or _topic_subject(topic))
    entity_type = classify_main_entity(subject, _clean(supplied.get("mainEntityType")), research.get("categories") or [])
    text = " ".join([topic] + [_clean(s.get("narration") or s.get("loi_dan") or s.get("text")) for s in scenes])
    candidates = [n for n in _names(text) if n.casefold() not in {topic.casefold(), subject.casefold()}]
    years = _unique(YEAR.findall(text))
    organisations = _unique(supplied.get("organizations", []))
    locations = _unique(supplied.get("locations", []))
    for marker in PLACE_WORDS:
        locations += _unique(re.findall(rf"\b{re.escape(marker)}\s+([A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+){{0,3}})", text))
    locations = _unique(locations)
    events = _unique(supplied.get("events", []))
    for scene in scenes:
        events.append(_clean(scene.get("event") or scene.get("headline") or scene.get("sceneRole")))
    events = _unique(events)
    objects = _unique(supplied.get("visualObjects", [])) or ["tài liệu gốc", "mốc thời gian", "ảnh bối cảnh"]
    entity_plan = {
        "mainEntity": subject, "mainEntityType": entity_type,
        "secondaryEntities": _unique(supplied.get("secondaryEntities", []) + candidates)[:12],
        "locations": locations, "timePeriods": _unique(supplied.get("timePeriods", []) + years),
        "organizations": organisations, "events": events, "visualObjects": objects,
        "mapsNeeded": _unique(supplied.get("mapsNeeded", []) + ([f"Bản đồ {p}" for p in locations[:3]] if locations else [])),
        "chartsNeeded": _unique(supplied.get("chartsNeeded", []) + (["Dòng thời gian"] if years else [])),
        "archivalSearchTerms": build_search_queries(subject, events[0] if events else "", locations[0] if locations else "", objects, entity_type),
    }
    for index, scene in enumerate(scenes):
        narration = _clean(scene.get("narration") or scene.get("loi_dan") or scene.get("text"))
        scene_names = _names(narration); scene_years = YEAR.findall(narration)
        location = next((p for p in locations if p.casefold() in narration.casefold()), "")
        event = _clean(scene.get("event") or scene.get("headline") or narration[:120])
        roles = ["paper-background","texture","main-subject","context-evidence","data-map-icon","annotation","typography"]
        scene["entityVisualPlan"] = {
            "mainSubject": subject, "mainSubjectType": entity_type,
            "identityRequired": entity_type == "person",
            "supportingSubjects": _unique(scene_names + entity_plan["secondaryEntities"])[:4],
            "location": location, "timePeriod": scene_years[0] if scene_years else "",
            "event": event, "visualEvidence": _unique([event, location] + objects)[:4],
            "searchQueries": build_search_queries(subject, event, location, objects, entity_type),
            "assetRoles": roles,
        }
        scene.setdefault("assetRoles", roles)
    story["entityVisualPlan"] = entity_plan
    story["resolvedEntityType"] = entity_type
    story["topic"] = topic
    apply_visual_plans(story)
    return story


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--story", default="assets/story.json"); parser.add_argument("--topic")
    args = parser.parse_args(); path = Path(args.story)
    story = plan_entities(json.loads(path.read_text(encoding="utf-8")), args.topic)
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"VISUAL ENTITY: {story['entityVisualPlan']['mainEntity']} ({story['resolvedEntityType']})")

if __name__ == "__main__": main()
