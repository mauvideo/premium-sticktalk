#!/usr/bin/env python3
"""Gemini-only stability wrapper for the commercial text pipeline.

Keeps the existing research/script pipeline intact, but makes two failure modes
more tolerant:
- Gemini 429/503/transient errors: retry with exponential backoff and optional
  Gemini fallback model.
- Gemini JSON with trailing prose or multiple JSON objects: parse the first
  complete JSON object instead of failing with `Extra data`.

No OpenAI fallback is used here.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
from pathlib import Path

# This file is invoked directly by make_video.sh. In that mode Python puts
# scripts/ (not the repository root) on sys.path, so `from scripts import ...`
# would fail. Add the repo root explicitly without changing the pipeline.
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
                text = base._gemini_text(prompt, use_search)
                return text, "gemini"
            except Exception as exc:
                errors.append(f"{model}: {exc}")
                transient = _is_transient(exc)
                if not transient:
                    break
                if retry < 4:
                    delay = min(4 * (2 ** retry), 32)
                    print(f"Gemini tạm lỗi ({model}); chờ {delay}s rồi thử lại {retry + 2}/5...")
                    time.sleep(delay)
        if model_index + 1 < len(models):
            print(f"Gemini chuyển model dự phòng: {models[model_index + 1]}")

    raise RuntimeError("Gemini thất bại sau retry: " + " | ".join(errors[-6:]))


def main() -> None:
    base._extract_json = _extract_json_stable
    base.ai_text = _gemini_only_ai_text
    base.main()


if __name__ == "__main__":
    main()
