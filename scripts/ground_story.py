#!/usr/bin/env python3
"""Ground a generated story in Wikipedia facts before asset planning.

This module intentionally fails instead of rendering unrelated filler when the
requested topic cannot be resolved. It uses Wikipedia only as a factual seed;
asset licensing is still handled separately by Wikimedia Commons providers.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://vi.wikipedia.org/w/api.php"
USER_AGENT = "premium-sticktalk/3.0 (topic-grounding)"
BANNED_FILLER = (
    "mỗi bước nhỏ", "đừng bỏ cuộc", "thành công", "động lực", "lựa chọn",
    "nút thắt", "khẩu hiệu", "câu hỏi đúng", "hành động rõ ràng",
    "phản ứng quen thuộc", "tình huống rất cụ thể",
)


def _get(params: dict) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json", "origin": "*"})
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def resolve_topic(topic: str) -> tuple[str, str, str]:
    search = _get({"action": "query", "list": "search", "srsearch": topic, "srlimit": 5, "utf8": 1})
    results = search.get("query", {}).get("search", [])
    if not results:
        raise RuntimeError(f"Không tìm thấy nguồn nghiên cứu cho chủ đề: {topic}")
    title = results[0]["title"]
    page = _get({
        "action": "query", "prop": "extracts|pageimages|info", "titles": title,
        "explaintext": 1, "exsectionformat": "plain", "piprop": "original|thumbnail",
        "pithumbsize": 1600, "inprop": "url", "redirects": 1,
    })
    data = next(iter(page.get("query", {}).get("pages", {}).values()), {})
    extract = str(data.get("extract") or "").strip()
    source_url = str(data.get("fullurl") or "")
    if len(extract) < 180:
        raise RuntimeError(f"Nguồn nghiên cứu quá ít dữ liệu cho chủ đề: {topic}")
    return str(data.get("title") or title), extract, source_url


def sentences(text: str) -> list[str]:
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    output: list[str] = []
    for part in parts:
        part = part.strip()
        low = part.casefold()
        if not 45 <= len(part) <= 330:
            continue
        if any(marker in low for marker in ("tham khảo", "chú thích", "liên kết ngoài")):
            continue
        if part not in output:
            output.append(part)
    return output


def score_sentence(sentence: str, canonical: str, index: int) -> tuple[int, int]:
    low = sentence.casefold()
    score = 0
    if canonical.casefold() in low:
        score += 8
    if re.search(r"\b(18|19|20)\d{2}\b", sentence):
        score += 6
    if any(word in low for word in ("sinh", "thành lập", "chiến dịch", "đại tướng", "tổng tư lệnh", "chiến thắng", "qua đời", "di sản")):
        score += 4
    return (-score, index)


def build_facts(extract: str, canonical: str, count: int) -> list[str]:
    candidates = sentences(extract)
    ranked = sorted(enumerate(candidates), key=lambda item: score_sentence(item[1], canonical, item[0]))
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
    selected.sort(key=lambda item: item[0])
    facts = [sentence for _, sentence in selected]
    if len(facts) < count:
        raise RuntimeError(f"Chỉ tìm được {len(facts)} dữ kiện phù hợp, cần {count}")
    return facts


def short_headline(sentence: str, canonical: str, index: int) -> str:
    year = re.search(r"\b(18|19|20)\d{2}\b", sentence)
    if year:
        return f"{year.group(0)} · {canonical}"
    return canonical if index == 0 else f"Dấu mốc {index + 1}"


def ground_story(story: dict, topic: str) -> dict:
    canonical, extract, source_url = resolve_topic(topic)
    scenes = story.get("scenes") or story.get("canh") or []
    if not scenes:
        raise RuntimeError("story.json không có cảnh")
    facts = build_facts(extract, canonical, len(scenes))
    for index, (scene, fact) in enumerate(zip(scenes, facts)):
        scene["narration"] = fact
        scene["loi_dan"] = fact
        scene["headline"] = short_headline(fact, canonical, index)
        scene["text"] = scene["headline"]
        scene["keywords"] = [canonical, *re.findall(r"\b(?:18|19|20)\d{2}\b", fact)[:1]]
        scene["tu_khoa"] = scene["keywords"]
        scene["mainSubject"] = canonical
        scene["entityVisualPlan"] = {
            "mainSubject": canonical,
            "mainSubjectType": "person" if re.search(r"\b(sinh|ông|bà|đại tướng|tướng)\b", extract.casefold()) else "topic",
            "event": fact,
            "timePeriod": (re.search(r"\b(?:18|19|20)\d{2}\b", fact) or [""])[0] if re.search(r"\b(?:18|19|20)\d{2}\b", fact) else "",
            "location": "Việt Nam" if "Việt Nam" in extract else "",
            "visualEvidence": [fact],
            "searchQueries": [
                f'"{canonical}" portrait',
                f'"{canonical}" {fact[:90]}',
                f'"{canonical}" Wikimedia Commons',
            ],
            "assetRoles": ["main-subject", "context-evidence", "map-or-timeline", "topic-icon"],
        }
    story["title"] = story["tieu_de"] = canonical
    story["topicInput"] = topic
    story["research"] = {"canonicalTitle": canonical, "sourceUrl": source_url, "provider": "vi.wikipedia.org"}
    story["entityVisualPlan"] = {
        "mainEntity": canonical,
        "mainEntityType": scenes[0]["entityVisualPlan"]["mainSubjectType"],
        "archivalSearchTerms": [f'"{canonical}" portrait', f'"{canonical}" historical photo'],
    }
    all_text = " ".join(scene["narration"].casefold() for scene in scenes)
    if canonical.casefold() not in all_text and not any(token in all_text for token in canonical.casefold().split() if len(token) > 3):
        raise RuntimeError("Kịch bản không bám tên chủ đề sau bước grounding")
    if any(phrase in all_text for phrase in BANNED_FILLER):
        raise RuntimeError("Kịch bản còn chứa câu đệm chung chung bị cấm")
    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", default="assets/story.json")
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()
    path = Path(args.story)
    story = json.loads(path.read_text(encoding="utf-8"))
    story = ground_story(story, args.topic)
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output").mkdir(exist_ok=True)
    Path("output/script.txt").write_text("\n".join(s["narration"] for s in story["scenes"]), encoding="utf-8")
    print(f"Đã khóa kịch bản theo nguồn: {story['research']['canonicalTitle']}")


if __name__ == "__main__":
    main()
