#!/usr/bin/env python3
"""Gemini-only stability wrapper for the commercial text pipeline.

Adds stable Gemini retries/JSON parsing, duration-aware prompts, and a generic
research normalizer so history, science, lifestyle, how-to, people and concept
videos all feed the same downstream script/visual pipeline.
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
    context = wiki.get("extract") or "(Không có Wikipedia context. Dùng kiến thức chắc chắn, không bịa chi tiết.)"
    return f"""
Bạn là research editor tiếng Việt cho hệ thống tạo video Vox đa chủ đề. Gemini CHỈ nghiên cứu và viết text.

CHỦ ĐỀ: {topic}
CHỦ THỂ: {resolved['canonicalSubject']}
LOẠI SƠ BỘ: {resolved['entityType']}
Ý ĐỊNH NGƯỜI XEM: {resolved['intent']}
PHẠM VI: {resolved['scope']}
NGỮ CẢNH THAM CHIẾU NẾU CÓ:
{context}

NHIỆM VỤ:
1. Tự phân loại nội dung thành một trong: factual, history, science, biography, lifestyle, howto, explainer, story.
2. Tạo các ĐƠN VỊ KIẾN THỨC đúng với loại nội dung, không ép mọi chủ đề phải là sự kiện lịch sử.
   - history/science/factual: dữ kiện, nguyên nhân, diễn biến, kết quả.
   - biography/story: mốc, hành động, bước ngoặt, bối cảnh.
   - lifestyle/howto: bước thực hiện, trình tự, trải nghiệm thường gặp, lưu ý thực tế.
   - explainer: ý chính, cơ chế, ví dụ, hệ quả.
3. Mỗi đơn vị phải đủ cụ thể để dùng làm lời thoại và tìm ảnh minh họa. Không bịa số liệu/tên riêng/mốc thời gian.
4. Với chủ đề đời sống như gym, nấu ăn, du lịch, học tập... được phép dùng kiến thức thực hành phổ biến, không cần biến chúng thành "fact lịch sử".
5. Tạo visual_queries bằng tiếng Anh hoặc tên riêng, mô tả hành động/vật/bối cảnh có thể tìm trên Pexels, Pixabay, Unsplash, Openverse.

Trả DUY NHẤT JSON theo schema này:
{{
  "contentType":"factual|history|science|biography|lifestyle|howto|explainer|story",
  "summary":"2-4 câu tóm tắt đúng chủ đề",
  "knowledge_items":[
    {{
      "id":"K1",
      "text":"một đơn vị kiến thức/bước/trải nghiệm cụ thể",
      "kind":"fact|step|event|tip|mechanism|context|example",
      "date":"nếu thật sự có",
      "places":["nếu có"],
      "entities":["nếu có"],
      "visual_queries":["3-5 truy vấn ảnh cụ thể"]
    }}
  ]
}}

Mục tiêu 8-14 knowledge_items; video 90 giây nên cố gắng 10-14 mục nếu chủ đề cho phép. Nếu chủ đề đơn giản, ưu tiên đúng và hữu ích hơn là bịa cho đủ số lượng.
Gemini KHÔNG tạo ảnh.
""".strip()


def _as_list(value):
    if isinstance(value, list):
        return value
    return []


def _candidate_units(data: dict) -> list:
    """Accept multiple plausible Gemini schemas and normalize them downstream."""
    keys = (
        "knowledge_items", "knowledgeItems", "facts", "steps", "events",
        "key_points", "keyPoints", "recommendations", "tips", "points", "items",
    )
    out = []
    for key in keys:
        out.extend(_as_list(data.get(key)))
    return out


def _unit_text(unit) -> str:
    if isinstance(unit, str):
        return re.sub(r"\s+", " ", unit).strip()
    if not isinstance(unit, dict):
        return ""
    for key in ("text", "claim", "step", "event", "point", "tip", "description", "content", "title"):
        value = unit.get(key)
        if value:
            return re.sub(r"\s+", " ", str(value)).strip()
    return ""


def _summary_units(data: dict) -> list[dict]:
    """Last-resort recovery: turn concrete summary sentences into knowledge units."""
    summary = re.sub(r"\s+", " ", str(data.get("summary") or "")).strip()
    if not summary:
        return []
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+|;\s+", summary) if len(x.strip()) >= 18]
    return [{"text": p, "kind": "context", "visual_queries": []} for p in parts]


def _validate_research_resilient(data: dict) -> None:
    raw = _candidate_units(data)
    if not raw:
        raw = _summary_units(data)

    cleaned = []
    seen = set()
    for unit in raw:
        text = _unit_text(unit)
        if len(text) < 10:
            continue
        key = re.sub(r"[^\wÀ-ỹĐđ]+", " ", text.casefold()).strip()
        if key in seen:
            continue
        seen.add(key)
        source = dict(unit) if isinstance(unit, dict) else {}
        queries = source.get("visual_queries") or source.get("visualQueries") or source.get("image_queries") or []
        queries = [re.sub(r"\s+", " ", str(q)).strip() for q in _as_list(queries) if str(q).strip()][:5]
        cleaned.append({
            "id": f"F{len(cleaned)+1}",
            "claim": text,
            "kind": str(source.get("kind") or source.get("type") or "knowledge"),
            "date": str(source.get("date") or ""),
            "places": [str(x) for x in _as_list(source.get("places")) if str(x).strip()],
            "entities": [str(x) for x in _as_list(source.get("entities")) if str(x).strip()],
            "visual_queries": queries,
        })

    if not cleaned:
        raise RuntimeError("Gemini không trả được nội dung nghiên cứu dùng được cho chủ đề này.")

    # Do not kill lifestyle/how-to/explainer topics merely because the model used
    # fewer knowledge units. The script stage can create multiple scenes from one
    # grounded unit without inventing new claims.
    if len(cleaned) < 3:
        print(f"CẢNH BÁO: chỉ có {len(cleaned)} knowledge unit; vẫn tiếp tục thay vì dừng workflow.")
    elif len(cleaned) < 6:
        print(f"CẢNH BÁO: Gemini trả {len(cleaned)} knowledge units; script sẽ khai thác nhiều góc kể từ chính các mục này.")

    data["facts"] = cleaned
    data["knowledge_items"] = cleaned
    data["contentType"] = str(data.get("contentType") or data.get("content_type") or "general")


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
    fact_json = json.dumps({
        "canonicalSubject": research["canonicalSubject"],
        "intent": research["intent"],
        "contentType": research.get("contentType", "general"),
        "facts": research["facts"],
    }, ensure_ascii=False)
    return f"""
Bạn là biên tập viên Vox documentary/lifestyle đa chủ đề. Viết kịch bản tiếng Việt CHỈ từ KNOWLEDGE bên dưới, không thêm dữ kiện mới.
CHỦ ĐỀ: {topic}
THỜI LƯỢNG CHÍNH XÁC CẦN NHẮM TỚI: {duration} giây
MỤC TIÊU: khoảng {target} từ, sai số tối đa 10%.
KNOWLEDGE: {fact_json}

Trả DUY NHẤT JSON:
{{"title":"...","scenes":[{{"id":"scene-01","headline":"ngắn","narration":"1-2 câu tự nhiên, đúng chủ đề","fact_ids":["F1"],"visual_queries":["3-5 truy vấn ảnh thật cụ thể bám chính xác cảnh"],"icons":["0-2 từ khóa icon đúng ngữ nghĩa; để [] nếu không cần"]}}]}}

Quy tắc số cảnh: {scene_rule}.
- Nếu contentType là lifestyle/howto: kể theo trình tự trải nghiệm/bước thực hiện tự nhiên.
- Nếu history/science/factual: kể theo logic nguyên nhân-diễn biến-kết quả hoặc giải thích.
- Nếu biography/story: kể theo mốc và bước ngoặt.
- Có thể dùng cùng một F-id cho nhiều scene nếu mỗi scene khai thác một khía cạnh khác nhau, nhưng KHÔNG được thêm fact mới hay lặp nguyên câu.
- Mỗi scene phải có visual_queries riêng, ưu tiên hành động/vật/bối cảnh đang được nói tới.
- narration là CHÍNH XÁC văn bản gửi sang VieNeu và dùng làm phụ đề.
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
