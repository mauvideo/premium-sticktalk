#!/usr/bin/env python3
"""Fit grounded narration to the selected duration using factual source text only.

This runs after ground_story.py. It never adds generic filler. When narration is
short, it appends unused factual sentences from the resolved Wikipedia article.
When narration is long, it trims scene text while preserving complete clauses.
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://vi.wikipedia.org/w/api.php"
USER_AGENT = "premium-sticktalk/4.3 (factual-duration-fit)"
WORDS_PER_SECOND = 2.65
TOLERANCE_SECONDS = 2.0


def word_count(text: str) -> int:
    return len(re.findall(r"[\wÀ-ỹĐđ]+", text))


def fetch_extract(title: str) -> str:
    params = urllib.parse.urlencode({
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "explaintext": 1,
        "exsectionformat": "plain",
        "redirects": 1,
        "format": "json",
        "origin": "*",
    })
    request = urllib.request.Request(
        f"{API}?{params}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.load(response)
    page = next(iter(payload.get("query", {}).get("pages", {}).values()), {})
    return re.sub(r"\s+", " ", str(page.get("extract") or "")).strip()


def source_sentences(text: str) -> list[str]:
    output: list[str] = []
    for part in re.split(r"(?<=[.!?])\s+", text):
        sentence = re.sub(r"\s+", " ", part).strip()
        low = sentence.casefold()
        if not 38 <= len(sentence) <= 260:
            continue
        if any(mark in low for mark in ("tham khảo", "chú thích", "liên kết ngoài")):
            continue
        if sentence not in output:
            output.append(sentence)
    return output


def normalized(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[\wÀ-ỹĐđ]+", text.casefold())
        if len(token) > 3
    }


def trim_words(text: str, limit: int) -> str:
    if word_count(text) <= limit:
        return text.strip()
    clauses = re.split(r"(?<=[,;:.!?])\s+", text.strip())
    kept: list[str] = []
    for clause in clauses:
        trial = " ".join([*kept, clause]).strip()
        if kept and word_count(trial) > limit:
            break
        kept.append(clause)
    result = " ".join(kept).strip()
    if not result or word_count(result) > limit:
        words = text.split()[:max(8, limit)]
        result = " ".join(words).rstrip(",;:")
    if result[-1:] not in ".!?":
        result += "."
    return result


def fit(story: dict, duration: int) -> dict:
    scenes = story.get("scenes") or []
    if not scenes:
        raise RuntimeError("story.json không có cảnh để cân thời lượng")

    target = round(duration * WORDS_PER_SECOND)
    tolerance = round(TOLERANCE_SECONDS * WORDS_PER_SECOND)
    low, high = target - tolerance, target + tolerance
    canonical = str(story.get("research", {}).get("canonicalTitle") or story.get("title") or "").strip()
    extract = fetch_extract(canonical)
    candidates = source_sentences(extract)

    used_text = " ".join(str(scene.get("newFact") or scene.get("narration") or "") for scene in scenes)
    used_tokens = normalized(used_text)
    extras = sorted(
        candidates,
        key=lambda sentence: (
            -len(normalized(sentence) - used_tokens),
            -int(bool(re.search(r"\b(?:18|19|20)\d{2}\b", sentence))),
        ),
    )

    def total_words() -> int:
        return sum(word_count(str(scene.get("narration") or "")) for scene in scenes)

    extra_index = 0
    while total_words() < low and extra_index < len(extras):
        sentence = extras[extra_index]
        extra_index += 1
        sentence_tokens = normalized(sentence)
        if not sentence_tokens or len(sentence_tokens & used_tokens) / max(1, len(sentence_tokens)) > 0.72:
            continue
        scene = min(scenes, key=lambda item: word_count(str(item.get("narration") or "")))
        current = str(scene.get("narration") or "").strip()
        scene["narration"] = f"{current} {sentence}".strip()
        scene["loi_dan"] = scene["narration"]
        scene.setdefault("supportingFacts", []).append(sentence)
        used_tokens |= sentence_tokens

    total = total_words()
    if total > high:
        desired_per_scene = max(10, target // len(scenes))
        for scene in sorted(scenes, key=lambda item: word_count(str(item.get("narration") or "")), reverse=True):
            if total_words() <= high:
                break
            current = str(scene.get("narration") or "")
            excess = total_words() - target
            keep = max(10, word_count(current) - excess)
            keep = min(keep, desired_per_scene + 8)
            scene["narration"] = trim_words(current, keep)
            scene["loi_dan"] = scene["narration"]

    final_words = total_words()
    estimated = round(final_words / WORDS_PER_SECOND, 2)
    story["narrationTiming"] = {
        "selectedDuration": duration,
        "wordsPerSecond": WORDS_PER_SECOND,
        "targetWords": target,
        "actualWords": final_words,
        "estimatedSeconds": estimated,
        "toleranceSeconds": TOLERANCE_SECONDS,
        "withinTolerance": low <= final_words <= high,
        "method": "factual-source-only",
    }
    if final_words < low:
        raise RuntimeError(
            f"Nguồn dữ kiện không đủ để tạo lời thoại gần {duration}s: "
            f"ước tính {estimated}s. Không thêm câu đệm chung chung."
        )
    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", default="assets/story.json")
    parser.add_argument("--duration", required=True, type=int)
    args = parser.parse_args()

    path = Path(args.story)
    story = json.loads(path.read_text(encoding="utf-8"))
    story = fit(story, args.duration)
    path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output").mkdir(exist_ok=True)
    Path("output/script.txt").write_text(
        "\n".join(str(scene.get("narration") or "") for scene in story["scenes"]),
        encoding="utf-8",
    )
    timing = story["narrationTiming"]
    print(
        f"Thoại: {timing['actualWords']} từ, ước tính {timing['estimatedSeconds']}s/"
        f"{timing['selectedDuration']}s, đúng khoảng={timing['withinTolerance']}"
    )


if __name__ == "__main__":
    main()
