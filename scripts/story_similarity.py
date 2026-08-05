#!/usr/bin/env python3
"""Rule-based story similarity checks for scene-level anti-repetition.

The module is local-only: no network, no AI image/audio dependencies.
"""
from __future__ import annotations

import math
import re
from collections import Counter

STOPWORDS = {
    "và", "là", "của", "một", "những", "các", "cho", "trong", "khi", "để", "với", "này", "đó",
    "thì", "mà", "ta", "bạn", "họ", "nó", "the", "and", "or", "of", "to", "in", "a", "an",
}
SEMANTIC_GROUPS = {
    "persist": {"cố", "gắng", "kiên", "trì", "bền", "bỉ", "bỏ", "cuộc", "từ", "bỏ"},
    "problem": {"vấn", "đề", "khó", "khăn", "rắc", "rối", "xung", "đột", "trở", "ngại"},
    "change": {"bước", "ngoặt", "đổi", "thay", "chuyển", "biến", "nhận", "ra"},
    "action": {"hành", "động", "làm", "chọn", "quyết", "định", "thử", "kiểm", "chứng"},
    "result": {"kết", "quả", "kết", "thúc", "bài", "học", "giá", "trị"},
}

def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[\wÀ-ỹ]+", text.casefold()) if len(w) > 2 and w not in STOPWORDS]

def keyword_overlap(a: str, b: str) -> float:
    sa, sb = set(tokens(a)), set(tokens(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, min(len(sa), len(sb)))

def cosine_similarity(a: str, b: str) -> float:
    ca, cb = Counter(tokens(a)), Counter(tokens(b))
    if not ca or not cb:
        return 0.0
    dot = sum(ca[k] * cb[k] for k in ca.keys() & cb.keys())
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0

def semantic_similarity(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    hits = 0
    total = 0
    for group in SEMANTIC_GROUPS.values():
        aa = bool(ta & group)
        bb = bool(tb & group)
        if aa or bb:
            total += 1
            hits += int(aa and bb)
    return hits / total if total else 0.0

def combined_similarity(a: str, b: str) -> dict[str, float]:
    keyword = keyword_overlap(a, b)
    cosine = cosine_similarity(a, b)
    semantic = semantic_similarity(a, b)
    combined = max(keyword, cosine * 0.9, semantic * 0.85)
    return {"keywordOverlap": keyword, "cosineSimilarity": cosine, "semanticSimilarity": semantic, "combinedSimilarity": combined}

def too_similar(a: str, b: str, threshold: float = 0.75) -> bool:
    return combined_similarity(a, b)["combinedSimilarity"] > threshold
