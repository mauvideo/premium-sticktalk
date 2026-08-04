#!/usr/bin/env python3
"""Tạo giọng đọc tiếng Việt bằng VieNeu-TTS với các giọng đặt sẵn."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from mutagen.mp3 import MP3
from vieneu import Vieneu


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=\d)\s*%", " phần trăm", text)
    return re.sub(r"\s+([.!?,:;])", r"\1", text)


def split_long_sentences(text: str, max_words: int = 34) -> str:
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


def normalize_voice_id(selected: str, custom_voice_id: str) -> str | None:
    value = selected.strip()
    if value in {"", "default", "Mặc định — Trúc Ly"}:
        return None
    if value in {"Bác sĩ Tuyên", "bac_si_tuyen"}:
        return "bac_si_tuyen"
    if value == "Nhập mã giọng khác":
        custom = custom_voice_id.strip()
        if not custom:
            raise ValueError("Bạn đã chọn nhập mã giọng khác nhưng chưa điền mã giọng VieNeu.")
        return custom
    return value


def synthesize(voice_selection: str, custom_voice_id: str, emotion: str) -> None:
    text = load_story_text()
    wav_path = Path("assets/narration.wav")
    mp3_path = Path("assets/narration.mp3")
    output_dir = Path("output")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    emotion_code = {"Tự nhiên": "natural", "Kể chuyện": "storytelling", "natural": "natural", "storytelling": "storytelling"}.get(emotion)
    if emotion_code is None:
        raise ValueError(f"Cảm xúc giọng không hợp lệ: {emotion}")

    requested_voice_id = normalize_voice_id(voice_selection, custom_voice_id)

    with Vieneu(mode="standard", emotion=emotion_code) as tts:
        available = tts.list_preset_voices()
        voice_map = {voice_id: description for description, voice_id in available}

        if requested_voice_id is None:
            voice_data = tts.get_preset_voice()
            actual_voice_id = "default"
            description = "Giọng mặc định VieNeu (Trúc Ly theo tài liệu chính thức)"
        else:
            if requested_voice_id not in voice_map:
                ids = ", ".join(sorted(voice_map)) or "không có"
                raise RuntimeError(
                    f"Mã giọng VieNeu '{requested_voice_id}' không tồn tại. "
                    f"Các mã hiện có: {ids}"
                )
            voice_data = tts.get_preset_voice(requested_voice_id)
            actual_voice_id = requested_voice_id
            description = voice_map[requested_voice_id]

        print("========================================")
        print("HỆ THỐNG GIỌNG ĐỌC: VieNeu-TTS")
        print("CHẾ ĐỘ: Standard")
        print(f"VOICE ID: {actual_voice_id}")
        print(f"MÔ TẢ: {description}")
        print(f"CẢM XÚC: {emotion_code}")
        print("ĐẦU RA: WAV 24 kHz và MP3")
        print("========================================")

        audio = tts.infer(text=text, voice=voice_data)
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
        "che_do": "standard",
        "voice_id": actual_voice_id,
        "mo_ta_giong": description,
        "cam_xuc": emotion_code,
        "dinh_dang_goc": "WAV 24 kHz",
        "dinh_dang_su_dung": "MP3 192 kbps",
        "thoi_luong_giay": round(duration, 3),
        "dung_luong_byte": mp3_path.stat().st_size,
    }
    Path("output/tts-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã tạo giọng VieNeu: {duration:.2f} giây")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo giọng đọc bằng VieNeu-TTS")
    parser.add_argument("--voice", default=os.getenv("VIENEU_VOICE", "default"))
    parser.add_argument("--custom-voice-id", default=os.getenv("VIENEU_CUSTOM_VOICE_ID", ""))
    parser.add_argument("--emotion", default=os.getenv("VIENEU_EMOTION", "Tự nhiên"))
    args = parser.parse_args()
    try:
        synthesize(args.voice, args.custom_voice_id, args.emotion)
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
