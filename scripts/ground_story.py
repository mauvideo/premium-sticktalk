#!/usr/bin/env python3
"""Research-first story planning for arbitrary Vox documentary topics.

The module resolves the complete subject requested by the user, builds factual
research, rewrites every scene, and creates scene-specific photo/icon queries.
Generic prefixes such as "lịch sử" or "cuộc đời" are not treated as subjects.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://vi.wikipedia.org/w/api.php"
USER_AGENT = "premium-sticktalk/4.3 (research-first-story-engine)"
BANNED_FILLER = (
    "mỗi bước nhỏ", "đừng bỏ cuộc", "động lực", "khẩu hiệu", "nút thắt",
    "câu hỏi đúng", "hành động rõ ràng", "phản ứng quen thuộc",
    "tình huống rất cụ thể", "một lựa chọn đang", "đổi hướng đúng chỗ",
)
GENERIC_PREFIXES = (
    "lịch sử", "cuộc đời", "tiểu sử", "sự nghiệp", "câu chuyện về",
    "tìm hiểu về", "video về", "kể về", "giới thiệu về", "phim về",
)
GENERIC_CONNECTORS = (
    "và hành trình", "và câu chuyện", "và quá trình", "và sự nghiệp",
    "và những", "qua các", "từ khi", "đến khi",
)
STOP_WORDS = {
    "lịch", "sử", "cuộc", "đời", "tiểu", "sự", "nghiệp", "câu", "chuyện",
    "tìm", "hiểu", "video", "phim", "về", "của", "và", "theo", "hành", "trình",
    "tạo", "nên", "quá", "trình", "những", "qua", "các", "đến", "khi", "từ",
}


def _get(params: dict) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json", "origin": "*"})
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\wÀ-ỹĐđ]+", normalized))


def _tokens(value: str) -> list[str]:
    return [token for token in _normalize(value).split() if len(token) > 1]


def subject_from_prompt(topic: str) -> str:
    subject = re.sub(r"\s+", " ", topic).strip(" .,:;-_\"'“”")
    changed = True
    while changed:
        changed = False
        lowered = subject.casefold()
        for prefix in GENERIC_PREFIXES:
            marker = prefix + " "
            if lowered.startswith(marker):
                subject = subject[len(marker):].strip(" .,:;-_\"'“”")
                changed = True
                break
    # Documentary prompts often append a scope after the actual named subject,
    # e.g. "Steve Jobs và hành trình tạo nên Apple". Resolve Wikipedia against
    # the named subject, while keeping the complete original topic as story scope.
    lowered = subject.casefold()
    cuts = [lowered.find(marker) for marker in GENERIC_CONNECTORS if lowered.find(marker) > 0]
    if cuts:
        subject = subject[:min(cuts)].strip(" .,:;-_\"'“”")
    if not subject:
        raise RuntimeError(f"Không xác định được chủ thể chính từ yêu cầu: {topic}")
    return subject


def _candidate_score(title: str, subject: str, search_index: int) -> tuple[int, int]:
    title_norm = _normalize(title)
    subject_norm = _normalize(subject)
    subject_tokens = [token for token in _tokens(subject) if token not in STOP_WORDS]
    title_tokens = set(_tokens(title))
    overlap = sum(1 for token in subject_tokens if token in title_tokens)
    score = overlap * 20
    if title_norm == subject_norm:
        score += 100
    elif subject_norm in title_norm:
        score += 45
    if subject_tokens and overlap == len(subject_tokens):
        score += 35
    return (-score, search_index)


def _validate_resolution(topic: str, subject: str, canonical: str) -> None:
    subject_tokens = [token for token in _tokens(subject) if token not in STOP_WORDS]
    canonical_tokens = set(_tokens(canonical))
    overlap = [token for token in subject_tokens if token in canonical_tokens]
    # A valid encyclopedia title is allowed to be shorter than the user's
    # documentary scope. For multi-word proper names require a majority match;
    # never compare the canonical title against generic scope words.
    if not subject_tokens:
        return
    minimum = 1 if len(subject_tokens) <= 2 else max(2, (len(subject_tokens) + 1) // 2)
    if len(overlap) < minimum:
        raise RuntimeError(
            "Wikipedia đã trả về sai chủ đề. "
            f"Yêu cầu='{topic}', chủ thể='{subject}', kết quả='{canonical}'."
        )


def research_topic(topic: str) -> dict:
    subject = subject_from_prompt(topic)
    variants = [f'intitle:"{subject}"', f'"{subject}"', subject]
    combined: list[dict] = []
    seen_titles: set[str] = set()
    for query_text in variants:
        search = _get({
            "action": "query", "list": "search", "srsearch": query_text,
            "srlimit": 10, "utf8": 1,
        })
        for item in search.get("query", {}).get("search", []):
            title = str(item.get("title") or "").strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                combined.append(item)
        if any(_normalize(item.get("title", "")) == _normalize(subject) for item in combined):
            break

    if not combined:
        raise RuntimeError(f"Không tìm thấy nguồn nghiên cứu cho chủ đề: {topic}")

    ranked = sorted(
        enumerate(combined),
        key=lambda pair: _candidate_score(str(pair[1].get("title") or ""), subject, pair[0]),
    )
    title = str(ranked[0][1]["title"])
    page = _get({
        "action": "query", "prop": "extracts|pageimages|info|categories",
        "titles": title, "explaintext": 1, "exsectionformat": "plain",
        "piprop": "original|thumbnail", "pithumbsize": 1600,
        "inprop": "url", "cllimit": 30, "redirects": 1,
    })
    data = next(iter(page.get("query", {}).get("pages", {}).values()), {})
    canonical = str(data.get("title") or title)
    _validate_resolution(topic, subject, canonical)

    extract = re.sub(r"\s+", " ", str(data.get("extract") or "")).strip()
    if len(extract) < 180:
        raise RuntimeError(f"Nguồn nghiên cứu quá ít dữ liệu cho chủ đề: {topic}")

    categories = [str(item.get("title", "")).replace("Thể loại:", "") for item in data.get("categories", [])]
    image = data.get("original") or data.get("thumbnail") or {}
    return {
        "topicInput": topic,
        "resolvedSubject": subject,
        "canonicalTitle": canonical,
        "sourceUrl": str(data.get("fullurl") or ""),
        "provider": "vi.wikipedia.org",
        "extract": extract,
        "categories": categories,
        "leadImageUrl": str(image.get("source") or ""),
    }


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 35]


def sentence_score(sentence: str, subject: str) -> int:
    norm = _normalize(sentence)
    score = 0
    if _normalize(subject) in norm:
        score += 8
    if re.search(r"\b(18|19|20)\d{2}\b", sentence):
        score += 5
    if any(word in norm for word in ("sinh", "thành lập", "ra mắt", "chiến dịch", "phát triển", "được bổ nhiệm", "sáng lập", "thành công", "qua đời", "phát minh", "xây dựng")):
        score += 4
    if any(filler in norm for filler in BANNED_FILLER):
        score -= 20
    return score


def _year(sentence: str) -> int | None:
    match = re.search(r"\b(18|19|20)\d{2}\b", sentence)
    return int(match.group(0)) if match else None


def _historical_scope(topic: str) -> bool:
    norm = _normalize(topic)
    return any(prefix in norm for prefix in ("lich su", "cuoc doi", "tieu su", "su nghiep", "hanh trinh"))


def _balanced_facts(sentences: list[str], subject: str, topic: str, limit: int = 18) -> list[str]:
    candidates = [s for s in sentences if sentence_score(s, subject) >= 0]
    if not candidates:
        return sentences[:limit]
    if not _historical_scope(topic):
        return sorted(candidates, key=lambda s: sentence_score(s, subject), reverse=True)[:limit]
    dated = [(i, s, _year(s)) for i, s in enumerate(candidates) if _year(s) is not None]
    undated = [(i, s) for i, s in enumerate(candidates) if _year(s) is None]
    dated.sort(key=lambda item: (item[2] or 9999, item[0]))
    chosen: list[str] = []
    if dated:
        # Sample the whole chronology instead of allowing one late-life cluster
        # (death/funeral, retirement, etc.) to dominate a broad history prompt.
        slots = min(max(6, limit - 4), len(dated))
        for n in range(slots):
            idx = round(n * (len(dated) - 1) / max(1, slots - 1))
            s = dated[idx][1]
            if s not in chosen:
                chosen.append(s)
    for _, s in undated:
        if len(chosen) >= limit:
            break
        if s not in chosen and sentence_score(s, subject) >= 4:
            chosen.append(s)
    # Cap end-of-life material at one fact unless the user explicitly asks for it.
    end_terms = ("qua đời", "từ trần", "quốc tang", "tang lễ", "an táng", "lễ viếng")
    end_count = 0
    balanced: list[str] = []
    for s in chosen:
        if any(term in _normalize(s) for term in end_terms):
            if end_count >= 1:
                continue
            end_count += 1
        balanced.append(s)
    return balanced[:limit]


def _entities(sentence: str, canonical: str) -> list[str]:
    entities = [canonical]
    for name in re.findall(r"\b[A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+){0,4}", sentence):
        if name not in entities and len(name) > 3:
            entities.append(name)
    return entities[:6]


def _places(sentence: str) -> list[str]:
    markers = re.findall(r"(?:tại|ở|đến|từ)\s+([A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+(?:\s+[A-ZÀ-ỸĐ][\wÀ-ỹĐđ.-]+){0,3})", sentence)
    return list(dict.fromkeys(markers))[:4]


def _event_phrase(sentence: str) -> str:
    clean = re.sub(r"\s+", " ", sentence).strip()
    return clean[:150]


def _scene_visual_plan(sentence: str, canonical: str, index: int) -> dict:
    year = str(_year(sentence) or "")
    places = _places(sentence)
    entities = _entities(sentence, canonical)
    event = _event_phrase(sentence)
    queries = [
        canonical,
        f'"{canonical}" {year}'.strip(),
        f'"{canonical}" {event[:70]}'.strip(),
    ]
    if places:
        queries.append(f'"{canonical}" {places[0]}')
    queries.append(f'{event[:90]} historical photo')
    return {
        "mainCharacter": canonical,
        "event": event,
        "time": year,
        "location": places[0] if places else "",
        "entities": entities,
        "assetQueries": list(dict.fromkeys(q for q in queries if q.strip())),
        "icons": ["timeline", "document"] if year else ["document", "map"],
        "dataLayers": [year] if year else [],
        "secondaryObjects": entities[1:3],
        "paperElements": ["newspaper", "grid"],
        "background": "paper-grid",
        "camera": ["push-in", "pan-left", "pan-right", "parallax"][index % 4],
        "transition": "paper-swipe",
        "highlight": year or canonical,
    }


def build_story(story: dict, topic: str) -> dict:
    research = research_topic(topic)
    subject = research["canonicalTitle"]
    sentences = split_sentences(research["extract"])
    facts = _balanced_facts(sentences, subject, topic, limit=max(16, len(story.get("scenes", [])) * 2))
    if len(facts) < 4:
        raise RuntimeError(f"Nguồn nghiên cứu không đủ dữ kiện riêng cho chủ đề: {topic}")

    scenes = story.get("scenes") or []
    if not scenes:
        raise RuntimeError("Kịch bản không có scene để biên tập.")

    # Preserve requested scope in the title, but ground every scene in the
    # resolved canonical subject and a distinct researched fact.
    story["title"] = topic.strip(" \"'“”")
    story["research"] = research
    story["resolvedSubject"] = subject
    story["researchFacts"] = facts
    for index, scene in enumerate(scenes):
        fact = facts[min(index, len(facts) - 1)]
        scene["narration"] = fact
        scene["headline"] = subject if index == 0 else (str(_year(fact) or "") or subject)
        scene["keywords"] = list(dict.fromkeys([subject, *(_places(fact)), str(_year(fact) or "")]))[:5]
        scene["visualPlan"] = _scene_visual_plan(fact, subject, index)
    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("story")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    path = Path(args.story)
    story = json.loads(path.read_text(encoding="utf-8"))
    story = build_story(story, args.topic)
    output = Path(args.output) if args.output else path
    output.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã nghiên cứu và lập kịch bản theo chủ đề: {story['resolvedSubject']}")
    print(f"Số dữ kiện mới: {len(story['researchFacts'])}")
    if _historical_scope(args.topic):
        print("EDITORIAL GUARD: đã phân bố dữ kiện theo toàn tiến trình, không để một sự kiện cuối đời chiếm toàn video")


if __name__ == "__main__":
    main()
