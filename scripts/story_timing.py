#!/usr/bin/env python3
"""Story Timing Engine for local narration-length planning.

This module estimates VieNeu narration duration without touching VieNeu, ONNX,
voice mapping or any audio pipeline code.
"""
from __future__ import annotations

import re

WORDS_PER_SECOND = 2.9
ALLOWED_TIMING_ERROR_SECONDS = 2.0
MAX_TIMING_REVISIONS = 3

ROLE_EXPANSIONS = {
    "Hook": "Chi tiết này khiến người xem muốn biết chuyện gì vừa xảy ra.",
    "Context": "Bối cảnh được đặt rõ để người xem hiểu nhân vật đang ở đâu.",
    "Conflict": "Khó khăn trở nên cụ thể hơn, buộc nhân vật phải đối diện thay vì né tránh.",
    "Development": "Hành động tiếp theo làm câu chuyện tiến lên bằng một lựa chọn có thể quan sát.",
    "Turning Point": "Một dấu hiệu mới làm hướng đi thay đổi và mở ra cách giải quyết khác.",
    "Ending": "Kết quả được khép lại bằng hành động nhìn thấy được, không chỉ bằng lời khuyên.",
    "Lesson": "Bài học giữ ngắn: hiểu nút thắt, rồi chọn một bước đúng.",
}

def word_count(text: str) -> int:
    return len(re.findall(r"[\wÀ-ỹ]+", text))

def target_word_count(duration_seconds: int, words_per_second: float = WORDS_PER_SECOND) -> int:
    return round(duration_seconds * words_per_second)

def estimate_duration_seconds(text_or_words: str | int, words_per_second: float = WORDS_PER_SECOND) -> float:
    words = text_or_words if isinstance(text_or_words, int) else word_count(text_or_words)
    return round(words / words_per_second, 2)

def timing_bounds(duration_seconds: int, words_per_second: float = WORDS_PER_SECOND) -> tuple[int, int]:
    tolerance = round(ALLOWED_TIMING_ERROR_SECONDS * words_per_second)
    target = target_word_count(duration_seconds, words_per_second)
    return max(1, target - tolerance), target + tolerance

def _base_role(role: str) -> str:
    return re.sub(r"\s+\d+$", "", role or "Development")

def _trim_to_words(text: str, keep_words: int) -> str:
    words = re.findall(r"\S+", text)
    if len(words) <= keep_words:
        return text.strip()
    return " ".join(words[:max(4, keep_words)]).rstrip(",;:") + "."

def fit_scene_narrations_to_duration(scenes: list[dict], duration_seconds: int, words_per_second: float = WORDS_PER_SECOND) -> dict:
    """Mutate scene narrations until estimated duration is within ±2 seconds."""
    low, high = timing_bounds(duration_seconds, words_per_second)
    target = target_word_count(duration_seconds, words_per_second)
    revisions = 0
    for revision in range(MAX_TIMING_REVISIONS + 1):
        total = sum(word_count(scene.get("narration") or scene.get("loi_dan", "")) for scene in scenes)
        if low <= total <= high:
            revisions = revision
            break
        revisions = revision
        if total < low:
            missing = target - total
            for idx, scene in enumerate(scenes):
                if missing <= 0:
                    break
                role = _base_role(scene.get("sceneRole", "Development"))
                extra = ROLE_EXPANSIONS.get(role, ROLE_EXPANSIONS["Development"])
                scene["narration"] = f"{scene.get('narration') or scene.get('loi_dan', '')} {extra}".strip()
                scene["loi_dan"] = scene["narration"]
                missing -= word_count(extra)
        else:
            excess = total - target
            per_scene = max(1, round(excess / max(1, len(scenes))))
            for scene in scenes:
                current = scene.get("narration") or scene.get("loi_dan", "")
                scene["narration"] = _trim_to_words(current, max(6, word_count(current) - per_scene))
                scene["loi_dan"] = scene["narration"]
    final_words = sum(word_count(scene.get("narration") or scene.get("loi_dan", "")) for scene in scenes)
    return {
        "targetDuration": duration_seconds,
        "wordsPerSecond": words_per_second,
        "targetWordCount": target,
        "actualWordCount": final_words,
        "estimatedDuration": estimate_duration_seconds(final_words, words_per_second),
        "allowedErrorSeconds": ALLOWED_TIMING_ERROR_SECONDS,
        "revisionCount": revisions,
        "withinTolerance": low <= final_words <= high,
    }
