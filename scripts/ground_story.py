#!/usr/bin/env python3
"""Research-first story planning for arbitrary Vox documentary topics.

The module never hardcodes a person or topic. It resolves the current user
request, extracts factual material, rewrites every scene from those facts, and
creates scene-specific photo/icon queries before asset planning.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://vi.wikipedia.org/w/api.php"
USER_AGENT = "premium-sticktalk/4.1 (research-first-story-engine)"
BANNED_FILLER = (
    "mỗi bước nhỏ", "đừng bỏ cuộc", "động lực", "khẩu hiệu", "nút thắt",
    "câu hỏi đúng", "hành động rõ ràng", "phản ứng quen thuộc",
    "tình huống rất cụ thể", "một lựa chọn đang", "đổi hướng đúng chỗ",
)


def _get(params: dict) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json", "origin": "*"})
    request = urllib.request.Request(
        f"{API}?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def research_topic(topic: str) -> dict:
    search = _get({
        "action": "query", "list": "search", "srsearch": topic,
        "srlimit": 5, "utf8": 1,
    })
    results = search.get("query", {}).get("search", [])
    if not results:
        raise RuntimeError(f"Không tìm thấy nguồn nghiên cứu cho chủ đề: {topic}")

    title = results[0]["title"]
    page = _get({
        "action": "query", "prop": "extracts|pageimages|info|categories",
        "titles": title, "explaintext": 1, "exsectionformat": "plain",
        "piprop": "original|thumbnail", "pithumbsize": 1600,
        "inprop": "url", "cllimit": 30, "redirects": 1,
    })
    data = next(iter(page.get("query", {}).get("pages", {}).values()), {})
    extract = re.sub(r"\s+", " ", str(data.get("extract") or "")).strip()
    if len(extract) < 180:
        raise RuntimeError(f"Nguồn nghiên cứu quá ít dữ liệu cho chủ đề: {topic}")

    categories = [
        str(item.get("title", "")).replace("Thể loại:", "")
        for item in data.get("categories", [])
    ]
    image = data.get("original") or data.get("thumbnail") or {}
    return {
        "topicInput": topic,
        "canonicalTitle": str(data.get("title") or title),
        "sourceUrl": str(data.get("fullurl") or ""),
        "provider": "vi.wikipedia.org",
        "extract": extract,
        "categories": categories,
        "leadImageUrl": str(image.get("source") or ""),
    }


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    output: list[str] = []
    for part in parts:
        sentence = part.strip()
        low = sentence.casefold()
        if not 45 <= len(sentence) <= 300:
            continue
        if any(marker in low for marker in ("tham khảo", "chú thích", "liên kết ngoài")):
            continue
        if sentence not in output:
            output.append(sentence)
    return output


def entity_type(research: dict) -> str:
    text = (research["extract"] + " " + " ".join(research["categories"])).casefold()
    if any(token in text for token in (
        "sinh ngày", "sinh năm", "nhân vật", "chính khách", "tướng lĩnh",
        "nhà khoa học", "doanh nhân", "nhà văn", "nghệ sĩ",
    )):
        return "person"
    if any(token in text for token in ("trận đánh", "chiến dịch", "sự kiện", "thảm họa")):
        return "event"
    if any(token in text for token in ("thành phố", "quốc gia", "tỉnh", "đảo", "địa danh")):
        return "place"
    return "topic"


def sentence_score(sentence: str, canonical: str, index: int) -> tuple[int, int]:
    low = sentence.casefold()
    score = 0
    if canonical.casefold() in low:
        score += 9
    if re.search(r"\b(18|19|20)\d{2}\b", sentence):
        score += 7
    if any(word in low for word in (
        "sinh", "thành lập", "chiến dịch", "phát minh", "công bố", "chiến thắng",
        "qua đời", "di sản", "khởi công", "ra mắt", "phát triển", "được biết đến",
        "tham gia", "chỉ huy", "giữ chức", "bổ nhiệm",
    )):
        score += 5
    return (-score, index)


def choose_facts(research: dict, count: int) -> list[str]:
    candidates = split_sentences(research["extract"])
    ranked = sorted(
        enumerate(candidates),
        key=lambda item: sentence_score(item[1], research["canonicalTitle"], item[0]),
    )
    selected: list[tuple[int, str]] = []
    seen: set[str] = set()
    for original_index, sentence in ranked:
        normalized = re.sub(r"\W+", " ", sentence.casefold()).strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append((original_index, sentence))
        if len(selected) >= count:
            break
    if len(selected) < count:
        raise RuntimeError(f"Chỉ tìm được {len(selected)} dữ kiện phù hợp, cần {count}")
    selected.sort(key=lambda item: item[0])
    return [sentence for _, sentence in selected]


def narration_from_fact(fact: str, canonical: str, index: int) -> str:
    """Create concise voice-over while preserving the factual sentence."""
    clean = re.sub(r"\s+", " ", fact).strip()
    if len(clean) > 190:
        clauses = re.split(r"(?<=[,;:])\s+", clean)
        clean = " ".join(clauses[:2]).strip()
        if len(clean) > 190:
            clean = clean[:187].rsplit(" ", 1)[0] + "..."
    if index == 0 and canonical.casefold() not in clean.casefold():
        clean = f"{canonical} là nhân vật trung tâm của câu chuyện này. {clean}"
    return clean


def headline(fact: str, canonical: str, index: int) -> str:
    year = re.search(r"\b(?:18|19|20)\d{2}\b", fact)
    if year:
        return f"{year.group(0)} · {canonical}"
    if index == 0:
        return canonical
    words = re.findall(r"[\wÀ-ỹĐđ]+", fact)
    return " ".join(words[:6]).rstrip(".,:;")


def extract_location(fact: str, research: dict) -> str:
    common = (
        "Việt Nam", "Hà Nội", "Điện Biên", "Điện Biên Phủ", "Sài Gòn",
        "Thành phố Hồ Chí Minh", "Pháp", "Mỹ", "Trung Quốc", "Nhật Bản",
    )
    for place in common:
        if place.casefold() in fact.casefold():
            return place
    return ""


def build_story(story: dict, topic: str) -> dict:
    research = research_topic(topic)
    canonical = research["canonicalTitle"]
    scenes = story.get("scenes") or story.get("canh") or []
    if not scenes:
        raise RuntimeError("story.json không có cảnh")

    facts = choose_facts(research, len(scenes))
    kind = entity_type(research)
    timeline: list[dict] = []

    for index, (scene, fact) in enumerate(zip(scenes, facts)):
        narration = narration_from_fact(fact, canonical, index)
        year_match = re.search(r"\b(?:18|19|20)\d{2}\b", fact)
        year = year_match.group(0) if year_match else ""
        location = extract_location(fact, research)
        scene_title = headline(fact, canonical, index)
        fact_tokens = re.findall(r"[\wÀ-ỹĐđ]+", fact)[:8]
        fact_keywords = " ".join(fact_tokens)

        scene["narration"] = narration
        scene["loi_dan"] = narration
        scene["headline"] = scene_title
        scene["text"] = scene_title
        scene["newFact"] = fact
        scene["timeMarker"] = year
        scene["location"] = location
        scene["event"] = fact
        scene["visualEvidence"] = [fact]
        scene["mainSubject"] = canonical
        scene["keywords"] = [canonical, *([year] if year else [])]
        scene["tu_khoa"] = scene["keywords"]
        scene["entityVisualPlan"] = {
            "mainSubject": canonical,
            "mainSubjectType": kind if index == 0 else "event",
            "identityRequired": bool(kind == "person" and index == 0),
            "event": fact,
            "timePeriod": year,
            "location": location,
            "visualEvidence": [fact],
            "searchQueries": [
                f'"{canonical}" portrait Wikimedia Commons' if index == 0 and kind == "person" else f'"{canonical}" Wikimedia Commons',
                f'"{canonical}" {year} {location}'.strip(),
                f'"{canonical}" {fact_keywords}'.strip(),
            ],
            "iconQueries": [
                f'{location or canonical} map icon',
                f'{year or "timeline"} timeline icon',
                f'{fact_keywords} historical icon',
            ],
            "assetRoles": [
                "main-subject", "context-evidence", "map-or-timeline",
                "topic-icon", "newspaper-clipping", "annotation",
            ],
        }
        timeline.append({"scene": index + 1, "year": year, "fact": fact, "location": location})

    story["title"] = story["tieu_de"] = canonical
    story["topicInput"] = topic
    story["research"] = {key: value for key, value in research.items() if key != "extract"}
    story["research"]["entityType"] = kind
    story["research"]["timeline"] = timeline
    story["entityVisualPlan"] = {
        "mainEntity": canonical,
        "mainEntityType": kind,
        "archivalSearchTerms": [
            f'"{canonical}" portrait Wikimedia Commons',
            f'"{canonical}" historical photo',
            f'"{canonical}" Wikimedia Commons',
        ],
        "mapsNeeded": [item["location"] for item in timeline if item["location"]],
        "chartsNeeded": ["timeline"],
    }

    all_text = " ".join(scene["narration"].casefold() for scene in scenes)
    relevant_tokens = [token for token in canonical.casefold().split() if len(token) > 3]
    if relevant_tokens and not any(token in all_text for token in relevant_tokens):
        raise RuntimeError("Kịch bản không chứa dữ kiện nhận diện đúng chủ đề")
    if any(phrase in all_text for phrase in BANNED_FILLER):
        raise RuntimeError("Kịch bản còn chứa câu đệm chung chung bị cấm")

    Path("assets/research.json").write_text(
        json.dumps(story["research"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", default="assets/story.json")
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()

    path = Path(args.story)
    story = json.loads(path.read_text(encoding="utf-8"))
    story = build_story(story, args.topic)
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    Path("output").mkdir(exist_ok=True)
    Path("output/script.txt").write_text(
        "\n".join(scene["narration"] for scene in story["scenes"]), encoding="utf-8"
    )
    print(f"Đã nghiên cứu và lập kịch bản theo chủ đề: {story['research']['canonicalTitle']}")
    print(f"Loại chủ đề: {story['research']['entityType']}")
    print(f"Số dữ kiện mới: {len(story['research']['timeline'])}")


if __name__ == "__main__":
    main()
