#!/usr/bin/env python3
"""Tạo giọng đọc tiếng Việt bằng VieNeu-TTS v3 Turbo (ONNX/CPU)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from mutagen.mp3 import MP3
from vieneu import Vieneu


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=\d)\s*%", " phần trăm", text)
    return re.sub(r"\s+([.!?,:;])", r"\1", text)


def split_long_sentences(text: str, max_words: int = 32) -> str:
    output: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = sentence.split()
        while len(words) > max_words:
            output.append(" ".join(words[:max_words]).rstrip(".,:;") + ".")
            words = words[max_words:]
        if words:
            output.append(" ".join(words))
    return " ".join(output)


def load_story_text() -> str:
    story_path = Path("assets/story.json")
    if not story_path.is_file():
        raise RuntimeError("Không tìm thấy assets/story.json.")
    story = json.loads(story_path.read_text(encoding="utf-8"))
    scenes = story.get("scenes") or story.get("canh") or []
    texts = [scene.get("narration") or scene.get("loi_dan") or "" for scene in scenes]
    text = clean_text(" ".join(item for item in texts if item))
    if not text:
        raise RuntimeError("Kịch bản không có lời dẫn để tạo giọng đọc.")
    return split_long_sentences(text)


def normalize_requested_voice(selected: str, custom_voice_id: str) -> str:
    value = selected.strip()
    aliases = {
        "": "Trúc Ly",
        "default": "Trúc Ly",
        "Mặc định — Trúc Ly": "Trúc Ly",
        "Bác sĩ Tuyên": "Phạm Tuyền",
        "bac_si_tuyen": "Phạm Tuyền",
    }
    if value in aliases:
        return aliases[value]
    if value == "Nhập mã giọng khác":
        custom = custom_voice_id.strip()
        if not custom:
            raise ValueError("Bạn đã chọn nhập mã giọng khác nhưng chưa điền tên hoặc mã giọng VieNeu.")
        return custom
    return value


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    return re.sub(r"\s+", " ", text).strip().casefold()


def resolve_preset_voice(available: list[tuple[Any, Any]], requested: str) -> tuple[Any, str, str]:
    """Trả đúng voice_id nguyên bản do VieNeu cung cấp, không tự đổi sang giọng khác."""
    wanted = _key(requested)
    for label, voice_id in available:
        label_text = str(label).strip()
        voice_id_text = str(voice_id).strip()
        if wanted in {_key(label_text), _key(voice_id_text)}:
            return voice_id, voice_id_text, label_text

    choices = ", ".join(str(voice_id) for _, voice_id in available) or "không có"
    raise ValueError(f"Không tìm thấy giọng VieNeu '{requested}'. Các giọng hiện có: {choices}")


def synthesize(voice_selection: str, custom_voice_id: str, emotion: str) -> None:
    text = load_story_text()
    wav_path = Path("assets/narration.wav")
    mp3_path = Path("assets/narration.mp3")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    Path("output").mkdir(parents=True, exist_ok=True)

    style_code = {
        "Tự nhiên": "tu_nhien",
        "Kể chuyện": "ke_chuyen",
        "Tin tức": "tin_tuc",
        "tu_nhien": "tu_nhien",
        "ke_chuyen": "ke_chuyen",
        "tin_tuc": "tin_tuc",
    }.get(emotion)
    if style_code is None:
        raise ValueError(f"Phong cách đọc không hợp lệ: {emotion}")

    requested = normalize_requested_voice(voice_selection, custom_voice_id)
    tts = Vieneu(backend="onnx")
    available = list(tts.list_preset_voices())
    voice_value, voice_name, description = resolve_preset_voice(available, requested)

    print("========================================")
    print("HỆ THỐNG GIỌNG ĐỌC: VieNeu-TTS")
    print("ENGINE: v3 Turbo")
    print("BACKEND: ONNX/CPU")
    print(f"GIỌNG YÊU CẦU: {requested}")
    print(f"MÃ GIỌNG THỰC TẾ: {voice_name}")
    print(f"MÔ TẢ: {description}")
    print(f"PHONG CÁCH ĐỌC: {style_code}")
    print("ĐẦU RA: WAV 48 kHz và MP3")
    print("========================================")

    try:
        # Truyền nguyên voice_id do chính list_preset_voices() trả về.
        # Không đổi giọng, không fallback sang giọng khác.
        audio = tts.infer(text, voice=voice_value, style=style_code)
    except Exception as error:
        raise RuntimeError(
            f"VieNeu không tạo được giọng '{voice_name}': {error}"
        ) from error

    tts.save(audio, str(wav_path))
    if not wav_path.is_file() or wav_path.stat().st_size <= 0:
        raise RuntimeError("VieNeu không tạo được file WAV hợp lệ.")

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_path)],
        check=True,
    )
    if not mp3_path.is_file() or mp3_path.stat().st_size <= 0:
        raise RuntimeError("Không chuyển được âm thanh VieNeu sang MP3.")

    duration = MP3(mp3_path).info.length
    info = {
        "nha_cung_cap": "vieneu",
        "engine": "v3_turbo",
        "backend": "onnx_cpu",
        "ten_giong": voice_name,
        "voice_requested": requested,
        "mo_ta_giong": description,
        "phong_cach_doc": style_code,
        "dinh_dang_goc": "WAV 48 kHz",
        "dinh_dang_su_dung": "MP3 192 kbps",
        "thoi_luong_giay": round(duration, 3),
        "dung_luong_byte": mp3_path.stat().st_size,
    }
    Path("output/tts-info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Đã tạo giọng VieNeu: {duration:.2f} giây")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo giọng đọc bằng VieNeu-TTS v3 Turbo")
    parser.add_argument("--voice", default=os.getenv("VIENEU_VOICE", "Mặc định — Trúc Ly"))
    parser.add_argument("--custom-voice-id", default=os.getenv("VIENEU_CUSTOM_VOICE_ID", ""))
    parser.add_argument("--emotion", default=os.getenv("VIENEU_EMOTION", "Tự nhiên"))
    args = parser.parse_args()
    try:
        synthesize(args.voice, args.custom_voice_id, args.emotion)
    except (ValueError, RuntimeError, ImportError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
