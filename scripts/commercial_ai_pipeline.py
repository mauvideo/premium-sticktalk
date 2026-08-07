#!/usr/bin/env python3
"""Commercial research-first pipeline for arbitrary documentary topics.

One topic goes through one authoritative AI resolver. The same canonical subject,
facts and scene plans are then consumed by image, TTS and Remotion stages.

Provider order (AI_PROVIDER=auto): OpenAI Responses API -> Gemini API.
Secrets are read only from environment variables and are never stored in repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

OPENAI_URL = "https://api.openai.com/v1/responses"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
WIKI_API = "https://vi.wikipedia.org/w/api.php"
USER_AGENT = "premium-sticktalk-commercial/1.0"


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _openai_text(prompt: str, use_search: bool) -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình")
    payload: dict[str, Any] = {
        "model": os.getenv("OPENAI_MODEL", "gpt-5"),
        "input": prompt,
        "store": False,
    }
    if use_search:
        payload["tools"] = [{"type": "web_search"}]
    data = _post_json(OPENAI_URL, payload, {"Authorization": f"Bearer {key}"})
    chunks: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    if not chunks and data.get("output_text"):
        chunks.append(str(data["output_text"]))
    if not chunks:
        raise RuntimeError("OpenAI không trả về nội dung văn bản")
    return "\n".join(chunks)


def _gemini_text(prompt: str, use_search: bool) -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY chưa được cấu hình")
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    if use_search:
        payload["tools"] = [{"google_search": {}}]
    data = _post_json(
        f"{GEMINI_BASE}/{urllib.parse.quote(model, safe='.-_')}:generateContent",
        payload,
        {"x-goog-api-key": key},
    )
    chunks: list[str] = []
    for candidate in data.get("candidates", []) or []:
        for part in (candidate.get("content") or {}).get("parts", []) or []:
            if part.get("text"):
                chunks.append(str(part["text"]))
    if not chunks:
        raise RuntimeError("Gemini không trả về nội dung văn bản")
    return "\n".join(chunks)


def ai_text(prompt: str, use_search: bool = False) -> tuple[str, str]:
    provider = os.getenv("AI_PROVIDER", "auto").strip().lower()
    attempts: list[tuple[str, Any]] = []
    if provider in {"auto", "openai", "chatgpt"} and os.getenv("OPENAI_API_KEY"):
        attempts.append(("openai", _openai_text))
    if provider in {"auto", "gemini"} and os.getenv("GEMINI_API_KEY"):
        attempts.append(("gemini", _gemini_text))
    if not attempts:
        raise RuntimeError(
            "Commercial pipeline cần OPENAI_API_KEY hoặc GEMINI_API_KEY trong GitHub Secrets. "
            "Không dùng kịch bản cục bộ giả lập khi thiếu AI."
        )
    errors = []
    for name, fn in attempts:
        for retry in range(2):
            try:
                return fn(prompt, use_search), name
            except Exception as e:
                errors.append(f"{name}: {e}")
                if retry == 0:
                    time.sleep(2)
    raise RuntimeError("AI provider thất bại: " + " | ".join(errors[-4:]))


def _word_count(text: str) -> int:
    return len(re.findall(r"[\wÀ-ỹĐđ]+", str(text)))


def _wiki_lead(subject: str) -> dict:
    """Resolve a free Wikipedia/Wikimedia lead image for the canonical subject."""
    def get(params: dict) -> dict:
        q = urllib.parse.urlencode({**params, "format": "json", "origin": "*"})
        req = urllib.request.Request(f"{WIKI_API}?{q}", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    try:
        search = get({"action": "query", "list": "search", "srsearch": subject, "srlimit": 5, "utf8": 1})
        rows = search.get("query", {}).get("search", [])
        title = str(rows[0].get("title") if rows else subject)
        page = get({
            "action": "query", "prop": "pageimages|info|categories", "titles": title,
            "piprop": "original|thumbnail", "pithumbsize": 1800,
            "inprop": "url", "cllimit": 20, "redirects": 1,
        })
        data = next(iter(page.get("query", {}).get("pages", {}).values()), {})
        image = data.get("original") or data.get("thumbnail") or {}
        return {
            "wikiTitle": str(data.get("title") or title),
            "sourceUrl": str(data.get("fullurl") or ""),
            "leadImageUrl": str(image.get("source") or ""),
            "categories": [str(x.get("title", "")).replace("Thể loại:", "") for x in data.get("categories", [])],
        }
    except Exception as e:
        print(f"WIKIPEDIA LEAD SKIP: {e}")
        return {"wikiTitle": subject, "sourceUrl": "", "leadImageUrl": "", "categories": []}


def research_prompt(topic: str) -> str:
    return f"""
Bạn là research editor cho một video Vox-style bằng tiếng Việt.
CHỦ ĐỀ NGƯỜI DÙNG: {topic}

Hãy tự hiểu ý định người dùng, tìm kiếm web và nghiên cứu từ NHIỀU nguồn đáng tin cậy.
Không được biến cả câu hỏi thành tên chủ thể. Không được tự khóa theo danh sách tên có sẵn.
Ưu tiên nguồn: cơ quan chính thức, bảo tàng/thư viện, trường đại học, tổ chức uy tín,
Wikipedia/Wikimedia để định danh, báo chí lớn cho sự kiện đương đại. Tránh blog SEO, trang sao chép.

Trả về DUY NHẤT JSON hợp lệ, không markdown, schema:
{{
  "canonicalSubject": "tên/chủ thể cốt lõi",
  "entityType": "person|event|organization|place|object|concept",
  "intent": "người dùng muốn biết điều gì",
  "scope": "phạm vi câu chuyện",
  "summary": "2-4 câu tóm tắt đã kiểm chứng",
  "sources": [{{"title":"...","url":"https://...","authority":"official|academic|museum|reference|major_media"}}],
  "facts": [
    {{"id":"F1","claim":"một dữ kiện cụ thể","date":"nếu có","places":["..."],"entities":["..."],"source_urls":["https://..."],"visual_queries":["truy vấn ảnh cụ thể 1","truy vấn ảnh cụ thể 2"]}}
  ]
}}

Yêu cầu chất lượng:
- ít nhất 3 nguồn độc lập nếu web có đủ, ít nhất 8 facts cho video 60 giây;
- facts phải phủ đúng toàn bộ câu hỏi, không lặp ý;
- mỗi fact phải gắn source_urls từ danh sách sources;
- visual_queries phải cụ thể theo đúng fact, nhân vật, sự kiện, địa điểm hoặc vật thể;
- không viết câu động lực chung chung, không bịa dữ kiện.
""".strip()


def script_prompt(topic: str, duration: int, research: dict) -> str:
    target = round(duration * 2.35)
    fact_json = json.dumps({"canonicalSubject": research["canonicalSubject"], "intent": research["intent"], "facts": research["facts"]}, ensure_ascii=False)
    return f"""
Bạn là biên tập viên Vox documentary. Viết kịch bản tiếng Việt từ FACTS đã kiểm chứng bên dưới.
Không bổ sung dữ kiện mới ngoài FACTS.
CHỦ ĐỀ: {topic}
THỜI LƯỢNG: {duration} giây
MỤC TIÊU TỔNG SỐ TỪ: khoảng {target} từ (sai số tối đa 12%).
FACTS: {fact_json}

Trả về DUY NHẤT JSON hợp lệ:
{{
  "title":"...",
  "scenes":[
    {{"id":"scene-01","headline":"ngắn","narration":"1-2 câu tự nhiên, giàu thông tin","fact_ids":["F1"],"visual_queries":["..."],"icons":["map|timeline|document|person|building|ship|airplane|chart"]}}
  ]
}}

Quy tắc:
- 30s: 5-7 cảnh; 45s: 7-9 cảnh; 60s: 8-11 cảnh.
- hook đi thẳng vào chi tiết đáng chú ý của chủ đề;
- mỗi cảnh phải đưa câu chuyện tiến lên và dùng fact khác hoặc góc khác;
- không lặp câu, không triết lý, không câu đệm;
- narration là CHÍNH XÁC văn bản sẽ gửi sang VieNeu và cũng là phụ đề;
- visual_queries phải bám fact_ids của chính cảnh, không dùng stock keyword chung chung.
""".strip()


def validate_research(data: dict) -> None:
    subject = str(data.get("canonicalSubject") or "").strip()
    et = str(data.get("entityType") or "").strip()
    facts = data.get("facts") or []
    sources = data.get("sources") or []
    if len(subject) < 2 or et not in {"person", "event", "organization", "place", "object", "concept"}:
        raise RuntimeError("AI research không xác định được canonicalSubject/entityType hợp lệ")
    if len(facts) < 5:
        raise RuntimeError("AI research trả quá ít facts")
    urls = {str(s.get("url") or "").strip() for s in sources if str(s.get("url") or "").startswith("http")}
    if len(urls) < 2:
        raise RuntimeError("AI research chưa có đủ nguồn web độc lập")
    seen = set()
    for i, fact in enumerate(facts, 1):
        fact["id"] = str(fact.get("id") or f"F{i}")
        claim = re.sub(r"\s+", " ", str(fact.get("claim") or "")).strip()
        if len(claim) < 18:
            raise RuntimeError(f"Fact {fact['id']} quá mơ hồ")
        key = claim.casefold()
        if key in seen:
            raise RuntimeError("AI research có fact trùng lặp")
        seen.add(key)
        fact["claim"] = claim


def validate_script(data: dict, research: dict, duration: int) -> None:
    scenes = data.get("scenes") or []
    if not scenes:
        raise RuntimeError("AI script không có scene")
    allowed = {str(f["id"]) for f in research["facts"]}
    narrations = []
    for i, scene in enumerate(scenes, 1):
        narration = re.sub(r"\s+", " ", str(scene.get("narration") or "")).strip()
        refs = [str(x) for x in scene.get("fact_ids") or []]
        if not narration or not refs or not set(refs).issubset(allowed):
            raise RuntimeError(f"Scene {i} không được ground đúng facts")
        if narration.casefold() in {x.casefold() for x in narrations}:
            raise RuntimeError("Kịch bản có narration trùng lặp")
        narrations.append(narration)
        scene["narration"] = narration
    words = sum(_word_count(x) for x in narrations)
    target = duration * 2.35
    if not (target * 0.72 <= words <= target * 1.25):
        raise RuntimeError(f"Kịch bản sai thời lượng: {words} từ cho {duration}s")


def build_story(topic: str, duration: int, voice: str) -> dict:
    research_text, provider = ai_text(research_prompt(topic), use_search=True)
    research = _extract_json(research_text)
    validate_research(research)
    wiki = _wiki_lead(str(research["canonicalSubject"]))
    research.update({
        "provider": provider,
        "canonicalTitle": str(research["canonicalSubject"]),
        "resolvedSubject": str(research["canonicalSubject"]),
        "leadImageUrl": wiki["leadImageUrl"],
        "wikipediaTitle": wiki["wikiTitle"],
        "wikipediaUrl": wiki["sourceUrl"],
        "categories": wiki["categories"],
    })

    script_text, script_provider = ai_text(script_prompt(topic, duration, research), use_search=False)
    script = _extract_json(script_text)
    try:
        validate_script(script, research, duration)
    except Exception as first_error:
        repair = script_prompt(topic, duration, research) + f"\nBản trước lỗi: {first_error}. Hãy sửa và trả JSON mới."
        script_text, script_provider = ai_text(repair, use_search=False)
        script = _extract_json(script_text)
        validate_script(script, research, duration)

    scenes = script["scenes"]
    base_duration = duration / len(scenes)
    facts_by_id = {str(f["id"]): f for f in research["facts"]}
    for i, scene in enumerate(scenes, 1):
        refs = [str(x) for x in scene.get("fact_ids") or []]
        relevant = [facts_by_id[x] for x in refs if x in facts_by_id]
        queries = []
        for q in scene.get("visual_queries") or []:
            if q and q not in queries: queries.append(str(q))
        for f in relevant:
            for q in f.get("visual_queries") or []:
                if q and q not in queries: queries.append(str(q))
        scene.update({
            "id": str(scene.get("id") or f"scene-{i:02d}"),
            "duration": round(base_duration, 3),
            "loi_dan": scene["narration"],
            "keywords": [str(research["canonicalSubject"])],
            "event": str(relevant[0]["claim"] if relevant else scene.get("headline") or ""),
            "visualQueries": queries[:8],
            "sourceFactIds": refs,
        })

    story = {
        "title": str(script.get("title") or topic),
        "topic": topic,
        "duration": duration,
        "voice": voice,
        "style": "vox_giay_cat",
        "template": "vox-paper-collage",
        "research": research,
        "entities": {
            "mainEntity": str(research["canonicalSubject"]),
            "mainEntityType": str(research["entityType"]),
        },
        "resolvedSubject": str(research["canonicalSubject"]),
        "resolvedEntityType": str(research["entityType"]),
        "scenes": scenes,
        "pipeline": "commercial-ai-grounded-v1",
        "aiProviders": {"research": provider, "script": script_provider},
    }
    Path("assets").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path("assets/research.json").write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output/research.json").write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("assets/story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("output/script.txt").write_text("\n".join(scene["narration"] for scene in scenes), encoding="utf-8")
    print(f"COMMERCIAL AI: provider={provider}; subject={research['canonicalSubject']!r}; type={research['entityType']}; facts={len(research['facts'])}; scenes={len(scenes)}")
    return story


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--duration", type=int, required=True)
    p.add_argument("--voice", default="default")
    a = p.parse_args()
    build_story(a.topic, a.duration, a.voice)


if __name__ == "__main__":
    main()
