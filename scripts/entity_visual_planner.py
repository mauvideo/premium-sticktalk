#!/usr/bin/env python3
"""Topic-agnostic entity, event and evidence planner.

The planner deliberately has no catalogue of famous people or events.  It derives
its vocabulary from the supplied topic and story, so a new subject does not need
a code change.  An upstream LLM may provide ``entities`` metadata; the local
heuristics keep the pipeline useful and deterministic when it does not.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

YEAR = re.compile(r"\b(?:1[0-9]{3}|20[0-9]{2})\b")
NAME = re.compile(r"\b(?:[A-ZÀ-ỸĐ][\wÀ-ỹĐđ]+(?:\s+|$)){2,6}")
ORG_WORDS = {"công ty", "tập đoàn", "đại học", "quân đội", "company", "group", "university", "institute"}
PLACE_WORDS = {"tại", "ở", "từ", "đến", "thành phố", "tỉnh", "nước", "in", "at", "from", "to"}


def _clean(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _unique(values):
    seen = set()
    result = []
    for value in values:
        value = _clean(value).strip(" ,.;:–—-")
        key = unicodedata.normalize("NFKC", value).casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _names(text: str) -> list[str]:
    return _unique(match.group(0) for match in NAME.finditer(text))


def _topic_subject(topic: str) -> str:
    # Remove generic request words, never subject-specific words.
    subject = re.sub(r"^(?:cuộc đời|tiểu sử|lịch sử|hành trình|câu chuyện)\s+", "", topic, flags=re.I)
    return _clean(subject) or _clean(topic)


def classify_main_entity(subject: str, supplied_type: str = "") -> str:
    """Classify the subject without maintaining a catalogue of known names.

    Explicit upstream metadata wins.  The fallback only inspects linguistic
    shape, which means it works for previously unseen people and subjects.
    """
    if supplied_type in {"person", "event", "organization", "place", "concept", "object"}:
        return supplied_type
    lower = subject.casefold()
    if re.match(r"^(?:vì sao|tại sao|cách|how|why)\b", lower):
        return "concept"
    if re.match(r"^(?:lịch sử|trận|chiến dịch|sự kiện|history)\b", lower):
        return "event"
    words = subject.split()
    title_words = sum(bool(re.match(r"^[A-ZÀ-ỸĐ]", word)) for word in words)
    if 2 <= len(words) <= 7 and title_words >= max(2, len(words) - 1):
        return "person"
    return "concept"


def build_search_queries(subject: str, event: str = "", location: str = "", objects=None, entity_type: str = "person") -> list[str]:
    """Create Vietnamese and English discovery queries for a visual role."""
    objects = objects or []
    if entity_type == "person":
        queries = [f'"{subject}" chân dung Wikimedia Commons', f'"{subject}" portrait Wikimedia Commons']
    else:
        queries = [f'"{subject}" sơ đồ minh họa Wikimedia Commons', f'"{subject}" explanatory diagram Wikimedia Commons']
    queries += [f'"{subject}" public domain', f'"{subject}" Openverse']
    if event:
        queries += [f'"{subject}" "{event}" ảnh tư liệu', f'"{subject}" "{event}" historical photo', f'"{event}" bản đồ', f'"{event}" map']
    if location:
        queries += [f'"{location}" ảnh lịch sử', f'"{location}" historical photo Wikimedia Commons']
    for obj in objects[:2]:
        queries += [f'"{obj}" minh họa cổ điển', f'"{obj}" vintage illustration public domain']
    return _unique(queries)


def plan_entities(story: dict, topic: str | None = None) -> dict:
    topic = _clean(topic or story.get("topic") or story.get("title") or story.get("tieu_de"))
    scenes = story.get("scenes") or []
    text = " ".join([topic] + [_clean(s.get("narration") or s.get("loi_dan") or s.get("text")) for s in scenes])
    supplied = story.get("entities") or {}
    subject = _clean(supplied.get("mainEntity") or _topic_subject(topic))
    entity_type = classify_main_entity(subject, _clean(supplied.get("mainEntityType")))
    candidates = [n for n in _names(text) if n.casefold() not in {topic.casefold(), subject.casefold()}]
    years = _unique(YEAR.findall(text))
    organisations = _unique(supplied.get("organizations", []))
    lowered = text.casefold()
    for marker in ORG_WORDS:
        organisations += _unique(re.findall(rf"(?:{re.escape(marker)})\s+[\wÀ-ỹĐđ .&-]+", text, re.I))[:2]

    locations = _unique(supplied.get("locations", []))
    # Capitalised phrases after a place preposition are conservative candidates.
    for marker in PLACE_WORDS:
        locations += _unique(re.findall(rf"\b{re.escape(marker)}\s+([A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ-]+){{0,3}})", text))
    locations = _unique(locations)

    events = _unique(supplied.get("events", []))
    for scene in scenes:
        events.append(_clean(scene.get("event") or scene.get("headline") or scene.get("sceneRole")))
    events = _unique(events)
    objects = _unique(supplied.get("visualObjects", []))
    if not objects:
        # Neutral evidence roles adapt to any subject rather than pretending to
        # know subject-specific facts.
        objects = ["tài liệu gốc", "mốc thời gian", "ảnh bối cảnh"]

    entity_plan = {
        "mainEntity": subject,
        "mainEntityType": entity_type,
        "secondaryEntities": _unique(supplied.get("secondaryEntities", []) + candidates)[:12],
        "locations": locations,
        "timePeriods": _unique(supplied.get("timePeriods", []) + years),
        "organizations": organisations,
        "events": events,
        "visualObjects": objects,
        "mapsNeeded": _unique(supplied.get("mapsNeeded", []) + ([f"Bản đồ {place}" for place in locations[:3]] if locations else [])),
        "chartsNeeded": _unique(supplied.get("chartsNeeded", []) + (["Dòng thời gian"] if years else [])),
        "archivalSearchTerms": build_search_queries(subject, events[0] if events else "", locations[0] if locations else "", objects, entity_type),
    }
    for index, scene in enumerate(scenes):
        narration = _clean(scene.get("narration") or scene.get("loi_dan") or scene.get("text"))
        scene_names = _names(narration)
        scene_years = YEAR.findall(narration)
        location = next((p for p in locations if p.casefold() in narration.casefold()), locations[index % len(locations)] if locations else "")
        event = _clean(scene.get("event") or scene.get("headline") or (events[index % len(events)] if events else ""))
        asset_roles = ["paper-background", "texture", "main-subject", "context-evidence", "data-map-icon", "annotation", "typography"]
        scene["entityVisualPlan"] = {
            "mainSubject": subject,
            "mainSubjectType": entity_type,
            "supportingSubjects": _unique(scene_names + entity_plan["secondaryEntities"])[:4],
            "location": location,
            "timePeriod": scene_years[0] if scene_years else (years[index % len(years)] if years else ""),
            "event": event,
            "visualEvidence": _unique([event, location] + objects)[:4],
            "searchQueries": build_search_queries(subject, event, location, objects, entity_type),
            "assetRoles": asset_roles,
        }
        scene.setdefault("assetRoles", asset_roles)
    story["entityVisualPlan"] = entity_plan
    story["topic"] = topic
    # Rebuild the composition brief only after entities and evidence are known.
    # This makes the existing Vox template consume the same topic-derived plan
    # instead of retaining a generic character/icon brief from Story Engine.
    from scripts.visual_planner import apply_visual_plans
    apply_visual_plans(story)
    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", default="assets/story.json")
    parser.add_argument("--topic")
    args = parser.parse_args()
    path = Path(args.story)
    story = plan_entities(json.loads(path.read_text(encoding="utf-8")), args.topic)
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
