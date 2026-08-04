#!/usr/bin/env python3
"""Tạo giọng đọc tiếng Việt bằng Microsoft Edge TTS miễn phí."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from mutagen.mp3 import MP3

# Khi chạy trực tiếp `python scripts/generate_tts.py`, Python chỉ thêm thư mục
# `scripts/` vào sys.path. Bổ sung thư mục gốc để import package `scripts` ổn định.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tts.edge_tts_provider import EdgeTtsProvider
from scripts.tts.presets import DEFAULT_PRESET, HOAI_MY, NAM_MINH, PRESETS, resolve_preset
from scripts.tts.audio_postprocess import EDGE_FILTERS as MASTERING_FILTERS, postprocess as _postprocess

ONES = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def number_to_vietnamese(n: int) -> str:
    if n == 0:
        return ONES[0]
    if n < 0:
        return "âm " + number_to_vietnamese(-n)
    scales, groups = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"], []
    while n:
        groups.append(n % 1000)
        n //= 1000

    def under(x: int, full: bool = False) -> str:
        h, r = divmod(x, 100)
        t, u = divmod(r, 10)
        words: list[str] = []
        if h:
            words += [ONES[h], "trăm"]
        elif full and r:
            words += ["không", "trăm"]
        if t > 1:
            words += [ONES[t], "mươi"]
        elif t == 1:
            words += ["mười"]
        elif u and (h or full):
            words += ["lẻ"]
        if u:
            words += ["mốt" if u == 1 and t > 1 else "lăm" if u == 5 and t else "tư" if u == 4 and t > 1 else ONES[u]]
        return " ".join(words)

    parts: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        group = groups[i]
        if group:
            parts.append(f"{under(group, bool(parts) and group < 100)} {scales[i]}".strip())
    return " ".join(parts)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=\d)\s*%", " phần trăm", text)
    return re.sub(r"\s+([.!?,:;])", r"\1", text)


def split_long_sentences(text: str, max_words: int = 24) -> str:
    output: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = sentence.split()
        while len(words) > max_words:
            output.append(" ".join(words[:max_words]).rstrip(".,:;") + ".")
            words = words[max_words:]
        if words:
            output.append(" ".join(words))
    return " ".join(output)


PAUSES_MS = {".": 560, ",": 210, ":": 300, ";": 330, "?": 620, "!": 600}


def speech_parts(text: str):
    parts = []
    start = 0
    for match in re.finditer(r"[.!?,:;]", text):
        if text[start:match.start()].strip():
            parts.append((text[start:match.start()].strip(), PAUSES_MS[match.group()]))
        start = match.end()
    if text[start:].strip():
        parts.append((text[start:].strip(), 0))
    return parts


async def synthesize(text: str, destination: Path, preset_name: str, provider_name: str | None = None) -> str:
    if provider_name not in (None, "edge"):
        raise ValueError("Hệ thống hiện chỉ hỗ trợ Microsoft Edge TTS miễn phí.")

    preset = resolve_preset(preset_name)
    if preset.provider != "edge":
        raise RuntimeError(f"Preset '{preset.name}' không thuộc Edge TTS.")
    if preset.gender == "Nam" and preset.voice != NAM_MINH:
        raise RuntimeError("Preset nam bắt buộc dùng vi-VN-NamMinhNeural.")
    if preset.gender == "Nữ" and preset.voice != HOAI_MY:
        raise RuntimeError("Preset nữ bắt buộc dùng vi-VN-HoaiMyNeural.")

    print("========================================")
    print("Nhà cung cấp thực tế: Microsoft Edge TTS")
    print(f"Preset đã chọn: {preset.name}")
    print(f"Voice ID thực tế: {preset.voice}")
    print("LANGUAGE CODE: vi-VN")
    print(f"TỐC ĐỘ: {preset.speed}")
    print(f"CAO ĐỘ: {preset.pitch}")
    print("ĐỊNH DẠNG: MP3")
    print("========================================")

    provider = EdgeTtsProvider()
    normalized = split_long_sentences(clean_text(text), preset.max_words)
    actual = await provider.synthesize(normalized, destination, preset)
    if actual != preset.voice:
        raise RuntimeError("Voice ID thực tế không khớp yêu cầu; đã dừng.")
    if not destination.is_file() or destination.stat().st_size <= 0:
        raise RuntimeError("File giọng đọc không tồn tại hoặc rỗng.")

    duration = MP3(destination).info.length
    info = {
        "nha_cung_cap": "edge",
        "ten_hien_thi": preset.name,
        "ma_preset": preset.code,
        "voice_id": actual,
        "language_code": "vi-VN",
        "toc_do": preset.speed,
        "cao_do": preset.pitch,
        "dinh_dang": "MP3",
        "thoi_luong_giay": round(duration, 3),
        "dung_luong_byte": destination.stat().st_size,
    }
    Path("output").mkdir(exist_ok=True)
    Path("output/tts-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã tạo giọng đọc: {duration:.2f} giây, {destination.stat().st_size} byte")
    return actual


async def run(preset_name: str) -> None:
    story = json.loads(Path("assets/story.json").read_text(encoding="utf-8"))
    text = " ".join(scene["narration"] for scene in story["scenes"])
    await synthesize(text, Path("assets/narration.mp3"), preset_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo giọng đọc tiếng Việt bằng Edge TTS")
    parser.add_argument("--preset", default=os.getenv("TTS_VOICE", DEFAULT_PRESET))
    args = parser.parse_args()
    try:
        asyncio.run(run(args.preset))
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()


def _master_audio(source, destination, preset):
    _postprocess(source, destination, preset)
