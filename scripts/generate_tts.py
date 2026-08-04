#!/usr/bin/env python3
"""Generate Vietnamese narration, preferring Edge TTS with a gTTS fallback."""

import argparse
import asyncio
import json
import re
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class VoicePreset:
    voice: str
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"


PRESETS = {
    "nam_bac_noi_luc_plus": VoicePreset("vi-VN-NamMinhNeural", "-6%", "-4Hz", "+10%"),
    "nam_bac_phat_thanh": VoicePreset("vi-VN-NamMinhNeural", "-4%", "-2Hz", "+8%"),
    "nam_bac_news": VoicePreset("vi-VN-NamMinhNeural", "-6%", "-3Hz", "+8%"),
    "nam_bac_noi_luc": VoicePreset("vi-VN-NamMinhNeural", "-8%", "-5Hz", "+10%"),
    "nam_bac_truyen_cam": VoicePreset("vi-VN-NamMinhNeural", "-12%", "-3Hz", "+6%"),
    "nam_bac_nang_luong": VoicePreset("vi-VN-NamMinhNeural", "+6%", "+1Hz", "+8%"),
    "nam_bac_tu_nhien": VoicePreset("vi-VN-NamMinhNeural", "-2%", "+0Hz", "+2%"),
    "nu_viet_nam_ro_rang": VoicePreset("vi-VN-HoaiMyNeural", "-1%", "+0Hz", "+3%"),
}
DEFAULT_PRESET = "nam_bac_noi_luc"
PAUSES_MS = {".": 500, ",": 180, ":": 250, ";": 220}

ONES = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _under_thousand(number: int, full: bool = False) -> str:
    hundreds, remainder = divmod(number, 100)
    tens, unit = divmod(remainder, 10)
    words = []
    if hundreds:
        words.extend((ONES[hundreds], "trăm"))
    elif full and remainder:
        words.extend(("không", "trăm"))
    if tens > 1:
        words.extend((ONES[tens], "mươi"))
    elif tens == 1:
        words.append("mười")
    elif unit and (hundreds or full):
        words.append("lẻ")
    if unit:
        if unit == 1 and tens > 1:
            words.append("mốt")
        elif unit == 5 and tens:
            words.append("lăm")
        elif unit == 4 and tens > 1:
            words.append("tư")
        else:
            words.append(ONES[unit])
    return " ".join(words)


def number_to_vietnamese(number: int) -> str:
    if number == 0:
        return ONES[0]
    if number < 0:
        return "âm " + number_to_vietnamese(-number)
    scales = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
    groups = []
    while number:
        groups.append(number % 1000)
        number //= 1000
    parts = []
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        if not group:
            continue
        spoken = _under_thousand(group, full=bool(parts) and group < 100)
        parts.append(f"{spoken} {scales[index]}".strip())
    return " ".join(parts)


def _speak_number(match: re.Match[str]) -> str:
    raw = match.group(0)
    if re.fullmatch(r"\d+[,.]\d+", raw):
        whole, fraction = re.split(r"[,.]", raw)
        return f"{number_to_vietnamese(int(whole))} phẩy {' '.join(ONES[int(n)] for n in fraction)}"
    return number_to_vietnamese(int(raw))


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=\d)\s*%", " phần trăm", text)
    text = re.sub(r"(?<=\d)\s*km\b", " ki lô mét", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+(?:[,.]\d+)?\b", _speak_number, text)
    text = re.sub(r"\b(tỉ|ty)\b", "tỷ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(tr|trieu)\b", "triệu", text, flags=re.IGNORECASE)
    return re.sub(r"\s+([.,:;])", r"\1", text).strip()


def split_long_sentences(text: str, max_words: int = 25) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    for sentence in sentences:
        words = sentence.split()
        while len(words) > max_words:
            cut = max_words
            for index in range(max_words - 1, max_words // 2, -1):
                if words[index - 1].endswith((",", ":", ";")):
                    cut = index
                    break
            part = " ".join(words[:cut]).rstrip(".,:;") + "."
            result.append(part)
            words = words[cut:]
        if words:
            result.append(" ".join(words))
    return " ".join(result)


def speech_parts(text: str) -> list[tuple[str, int]]:
    parts = []
    start = 0
    for match in re.finditer(r"[.,:;]", text):
        chunk = text[start:match.start()].strip()
        if chunk:
            parts.append((chunk, PAUSES_MS[match.group()]))
        start = match.end()
    tail = text[start:].strip()
    if tail:
        parts.append((tail, 0))
    return parts


async def _edge_part(text: str, destination: Path, preset: VoicePreset) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(
        text=text,
        voice=preset.voice,
        rate=preset.rate,
        pitch=preset.pitch,
        volume=preset.volume,
    )
    await communicate.save(str(destination))


def _silence(destination: Path, milliseconds: int) -> None:
    frames = int(24_000 * milliseconds / 1000)
    with wave.open(str(destination), "wb") as output:
        output.setparams((1, 2, 24_000, frames, "NONE", "not compressed"))
        output.writeframes(b"\0\0" * frames)


def _join_audio(inputs: list[Path], destination: Path) -> None:
    command = ["ffmpeg", "-y", "-loglevel", "error"]
    for source in inputs:
        command.extend(("-i", str(source)))
    command.extend(("-filter_complex", f"concat=n={len(inputs)}:v=0:a=1[out]", "-map", "[out]", str(destination)))
    subprocess.run(command, check=True)


def _master_audio(source: Path, destination: Path) -> None:
    """Make narration clearer, steadier and more present without clipping."""
    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
        "-af",
        "highpass=f=70,lowpass=f=14500,acompressor=threshold=-18dB:ratio=2.5:attack=15:release=180:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=8",
        "-c:a", "libmp3lame", "-b:a", "192k", str(destination),
    ]
    subprocess.run(command, check=True)


async def synthesize(text: str, destination: Path, preset_name: str) -> str:
    preset = PRESETS[preset_name]
    parts = speech_parts(split_long_sentences(clean_text(text)))
    if not parts:
        raise ValueError("Nội dung TTS trống")
    with tempfile.TemporaryDirectory(prefix="sticktalk-tts-") as directory:
        temporary = Path(directory)
        speech_files = [temporary / f"speech-{index}.mp3" for index in range(len(parts))]
        provider = "Edge TTS"
        try:
            for (chunk, _), output in zip(parts, speech_files):
                await _edge_part(chunk, output, preset)
        except Exception as error:
            from gtts import gTTS
            provider = "gTTS"
            print(f"Edge TTS lỗi ({error}); chuyển sang gTTS.")
            for (chunk, _), output in zip(parts, speech_files):
                gTTS(text=chunk, lang="vi").save(str(output))

        timeline = []
        for index, ((_, pause), speech_file) in enumerate(zip(parts, speech_files)):
            timeline.append(speech_file)
            if pause:
                pause_file = temporary / f"pause-{index}.wav"
                _silence(pause_file, pause)
                timeline.append(pause_file)

        joined = temporary / "joined.mp3"
        _join_audio(timeline, joined)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _master_audio(joined, destination)
        return provider


async def run(preset_name: str) -> None:
    story = json.loads(Path("assets/story.json").read_text(encoding="utf-8"))
    text = " ".join(scene["narration"] for scene in story["scenes"])
    provider = await synthesize(text, Path("assets/narration.mp3"), preset_name)
    preset = PRESETS[preset_name]
    print(
        f"Đã tạo assets/narration.mp3 bằng {provider} | preset={preset_name} | "
        f"voice={preset.voice} | rate={preset.rate} | pitch={preset.pitch} | volume={preset.volume}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=PRESETS, default=DEFAULT_PRESET)
    args = parser.parse_args()
    asyncio.run(run(args.preset))


if __name__ == "__main__":
    main()
