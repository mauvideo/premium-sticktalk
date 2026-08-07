#!/usr/bin/env python3
"""Gemini-only stability wrapper for the commercial text pipeline.

Adds stable Gemini retries/JSON parsing and duration-aware prompts, including
90-second scripts. Gemini remains text-only; visual assets are fetched by the
separate web asset engine.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import commercial_ai_pipeline as base


def _extract_json_stable(text: str) -> dict:
    text = str(text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    decoder = json.JSONDecoder()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    for match in re.finditer(r"\{", text):
        try:
            value, _end = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise json.JSONDecodeError("Không tìm thấy JSON object hợp lệ trong phản hồi Gemini", text, 0)


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in {408, 429, 500, 502, 503, 504}
    msg = str(exc).casefold()
    return any(x in msg for x in (
        "429", "too many requests", "503", "service unavailable", "timeout",
        "timed out", "temporarily unavailable", "rate limit", "connection reset",
    ))


def _gemini_only_ai_text(prompt: str, use_search: bool = False) -> tuple[str, str]:
    if not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("Cần GEMINI_API_KEY trong GitHub Secrets để Gemini nghiên cứu và viết kịch bản.")
    primary = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"
    fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash").strip()
    models = [primary]
    if fallback and fallback != primary:
        models.append(fallback)
    errors: list[str] = []
    for model_index, model in enumerate(models):
        os.environ["GEMINI_MODEL"] = model
        for retry in range(5):
            try:
                return base._gemini_text(prompt, use_search), "gemini"
            except Exception as exc:
                errors.append(f"{model}: {exc}")
                if not _is_transient(exc):
                    break
                if retry < 4:
                    delay = min(4 * (2 ** retry), 32)
                    print(f"Gemini tạm lỗi ({model}); chờ {delay}s rồi thử lại {retry + 2}/5...")
                    time.sleep(delay)
        if model_index + 1 < len(models):
            print(f"Gemini chuyển model dự phòng: {models[model_index + 1]}")
    raise RuntimeError("Gemini thất bại sau retry: " + " | ".join(errors[-6:]))


def _research_prompt(topic: str, resolved: dict, wiki: dict) -> str:
    context = wiki.get("extract") or "(Không có Wikipedia context; chỉ nêu fact bạn chắc chắn.)"
    return f"""
Bạn là research editor tiếng Việt cho video Vox. Gemini CHỈ nghiên cứu và viết text.
CHỦ ĐỀ: {topic}
CHỦ THỂ: {resolved['canonicalSubject']}
LOẠI: {resolved['entityType']}
Ý ĐỊNH: {resolved['intent']}
PHẠM VI: {resolved['scope']}
NGỮ CẢNH THAM CHIẾU:
{context}

Tạo facts chính xác, không bịa, không lặp, phủ đúng câu hỏi. Mỗi fact phải đủ cụ thể để vừa viết lời thoại vừa tìm hình minh họa.
Trả DUY NHẤT JSON:
{{"summary":"2-4 câu","facts":[{{"id":"F1","claim":"một dữ kiện cụ thể","date":"nếu có","places":["..."],"entities":["..."],"visual_queries":["3-5 truy vấn ảnh web cụ thể bằng tiếng Anh hoặc tên riêng, mô tả đúng người/vật/hành động/bối cảnh của fact"]}}]}}
Mục tiêu 10-14 facts để đủ dữ liệu cho video dài 90 giây; nếu chủ đề đơn giản thì ưu tiên facts thật và hữu ích hơn là bịa cho đủ số lượng.
visual_queries dùng cho Pexels, Pixabay, Unsplash và Openverse; KHÔNG dùng Wikimedia và Gemini KHÔNG tạo ảnh.
""".strip()


def _validate_research_resilient(data: dict) -> None:
    """Clean usable Gemini facts instead of killing the whole workflow for a short list."""
    raw = data.get("facts") or []
    cleaned = []
    seen = set()
    for fact in raw:
        claim = re.sub(r"\s+", " ", str((fact or {}).get("claim") or "")).strip()
        if len(claim) < 12:
            continue
        key = claim.casefold()
        if key in seen:
            continue
        seen.add(key)
        item = dict(fact)
        item["claim"] = claim
        item["id"] = f"F{len(cleaned)+1}"
        item["visual_queries"] = [
            re.sub(r"\s+", " ", str(q)).strip()
            for q in (item.get("visual_queries") or [])
            if str(q).strip()
        ][:5]
        cleaned.append(item)
    if len(cleaned) < 3:
        raise RuntimeError(f"Gemini research chỉ có {len(cleaned)} fact dùng được; cần ít nhất 3 fact thật để viết kịch bản.")
    if len(cleaned) < 5:
        print(f"CẢNH BÁO: Gemini chỉ trả {len(cleaned)} facts dùng được; vẫn tiếp tục và để script mở rộng cách kể từ chính các facts này.")
    data["facts"] = cleaned


def _script_prompt(topic: str, duration: int, research: dict) -> str:
    target = round(duration * 2.35)
    if duration >= 90:
        scene_rule = "90s: 13-17 cảnh, mỗi cảnh khoảng 4.5-7 giây"
    elif duration >= 60:
        scene_rule = "60s: 9-12 cảnh"
    elif duration >= 45:
        scene_rule = "45s: 7-9 cảnh"
    else:
        scene_rule = "30s: 5-7 cảnh"
    fact_json = json.dumps({"canonicalSubject": research["canonicalSubject"], "intent": research["intent"], "facts": research["facts"]}, ensure_ascii=False)
    return f"""
Bạn là biên tập viên Vox documentary. Viết kịch bản tiếng Việt CHỈ từ FACTS bên dưới, không thêm dữ kiện mới.
CHỦ ĐỀ: {topic}
THỜI LƯỢNG CHÍNH XÁC CẦN NHẮM TỚI: {duration} giây
MỤC TIÊU: khoảng {target} từ, sai số tối đa 10%.
FACTS: {fact_json}

Trả DUY NHẤT JSON:
{{"title":"...","scenes":[{{"id":"scene-01","headline":"ngắn","narration":"1-2 câu tự nhiên, giàu thông tin","fact_ids":["F1"],"visual_queries":["3-5 truy vấn ảnh thật cụ thể bám chính xác câu thoại này"],"icons":["1-2 từ khóa icon đúng ngữ nghĩa cảnh, ví dụ dumbbell, heart, map, clock, phone, car, plane; để [] nếu không cần"]}}]}}
Quy tắc số cảnh: {scene_rule}.
Có thể khai thác nhiều góc kể khác nhau từ cùng một fact nhưng KHÔNG được tạo fact mới hoặc lặp nguyên câu. Mỗi scene phải có visual_queries riêng; ưu tiên ảnh thật về hành động/đối tượng đang được nói tới, không dùng ảnh người nổi tiếng không liên quan.
narration là CHÍNH XÁC văn bản gửi sang VieNeu và dùng làm phụ đề.
""".strip()


def main() -> None:
    base._extract_json = _extract_json_stable
    base.ai_text = _gemini_only_ai_text
    base.research_prompt = _research_prompt
    base.validate_research = _validate_research_resilient
    base.script_prompt = _script_prompt
    base.main()


if __name__ == "__main__":
    main()
