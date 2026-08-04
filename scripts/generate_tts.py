#!/usr/bin/env python3
"""Tạo và hậu kỳ giọng đọc tiếng Việt cho Premium StickTalk."""

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
    name: str
    voice: str
    rate: str
    pitch: str
    volume: str
    mastering: str
    max_words: int = 24


NAM_MINH = "vi-VN-NamMinhNeural"
HOAI_MY = "vi-VN-HoaiMyNeural"
VOICE_REGION_CONFIG = Path(__file__).with_name("tts") / "vung_giong.json"
VOICE_REGIONS = {
    "Miền Bắc": "mien_bac",
    "Miền Nam": "mien_nam",
    "Chưa xác định": "chua_xac_dinh",
    "mien_bac": "mien_bac",
    "mien_nam": "mien_nam",
    "chua_xac_dinh": "chua_xac_dinh",
}
REGION_LABELS = {
    "mien_bac": "Miền Bắc",
    "mien_nam": "Miền Nam",
    "chua_xac_dinh": "Chưa xác định",
}

# Tên hiển thị cũng là giá trị truyền xuyên suốt workflow, tránh việc UI đúng nhưng
# pipeline lại âm thầm chọn một preset/voice khác.
PRESETS = {
    "Nam miền Bắc MC": VoicePreset("Nam miền Bắc MC", NAM_MINH, "-3%", "-2Hz", "+6%", "mc"),
    "Nam miền Bắc Nội lực": VoicePreset("Nam miền Bắc Nội lực", NAM_MINH, "-8%", "-5Hz", "+9%", "power"),
    "Nam miền Bắc Nội lực Plus": VoicePreset(
        "Nam miền Bắc Nội lực Plus", NAM_MINH, "-14%", "-7Hz", "+14%", "power_plus", 20
    ),
    "Nam miền Bắc Podcast": VoicePreset("Nam miền Bắc Podcast", NAM_MINH, "-10%", "-3Hz", "+5%", "podcast", 22),
    "Nam miền Bắc Truyền cảm": VoicePreset("Nam miền Bắc Truyền cảm", NAM_MINH, "-12%", "-4Hz", "+7%", "emotional", 20),
    "Nam miền Bắc Doanh nhân": VoicePreset("Nam miền Bắc Doanh nhân", NAM_MINH, "-6%", "-4Hz", "+8%", "business"),
    "Nữ miền Bắc Dịu nhẹ": VoicePreset("Nữ miền Bắc Dịu nhẹ", HOAI_MY, "-8%", "+1Hz", "+4%", "gentle", 22),
}
DEFAULT_PRESET = "Nam miền Bắc Nội lực Plus"
PAUSES_MS = {".": 560, ",": 210, ":": 300, ";": 330, "?": 620, "!": 600}

# Giữ tương thích với các job cũ, nhưng mọi alias đều được chuẩn hóa trước khi render/log.
PRESET_ALIASES = {
    "nam_bac_mc": "Nam miền Bắc MC",
    "nam_bac_noi_luc": "Nam miền Bắc Nội lực",
    "nam_bac_noi_luc_plus": "Nam miền Bắc Nội lực Plus",
    "nam_bac_podcast": "Nam miền Bắc Podcast",
    "nam_bac_truyen_cam": "Nam miền Bắc Truyền cảm",
    "nam_bac_doanh_nhan": "Nam miền Bắc Doanh nhân",
    "nu_mien_bac_diu_nhe": "Nữ miền Bắc Dịu nhẹ",
}

ONES = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def resolve_preset(name: str) -> VoicePreset:
    canonical = PRESET_ALIASES.get(name, name)
    if canonical not in PRESETS:
        raise ValueError(f"Preset không hợp lệ: {name}")
    preset = PRESETS[canonical]
    if preset.name.startswith("Nam miền Bắc") and preset.voice != NAM_MINH:
        raise RuntimeError(f"Preset {preset.name} bắt buộc dùng {NAM_MINH}, không phải {preset.voice}")
    return preset


def load_voice_regions(config_path: Path = VOICE_REGION_CONFIG) -> dict[str, str]:
    """Đọc phân loại thủ công; tuyệt đối không suy luận vùng từ tên Voice ID."""
    try:
        regions = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Không đọc được cấu hình vùng giọng {config_path}: {error}") from error
    if not isinstance(regions, dict) or any(region not in REGION_LABELS for region in regions.values()):
        raise ValueError(
            "Cấu hình vùng giọng không hợp lệ; chỉ chấp nhận mien_bac, mien_nam hoặc chua_xac_dinh"
        )
    return regions


def validate_voice_region(selected_region: str, voice_id: str, config_path: Path = VOICE_REGION_CONFIG) -> str:
    region = VOICE_REGIONS.get(selected_region)
    if region is None:
        raise ValueError(f"Vùng giọng không hợp lệ: {selected_region}")
    actual_region = load_voice_regions(config_path).get(voice_id)
    actual_label = REGION_LABELS.get(actual_region, "Không có trong cấu hình")
    print(f"Vùng giọng đã chọn: {REGION_LABELS[region]}")
    print(f"Voice ID thực tế: {voice_id}")
    print(f"Vùng giọng của Voice ID: {actual_label}")
    if actual_region != region:
        raise RuntimeError(
            f"Không có giọng phù hợp: Voice ID {voice_id} thuộc vùng '{actual_label}', "
            f"không khớp vùng đã chọn '{REGION_LABELS[region]}'. Không fallback sang vùng khác."
        )
    return actual_region


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
    original = number
    groups = []
    while number:
        groups.append(number % 1000)
        number //= 1000
    if len(groups) > len(scales):
        return " ".join(ONES[int(digit)] for digit in str(original))
    parts = []
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        if group:
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
    """Chuẩn hóa ký hiệu trước khi gửi TTS để cách đọc luôn tự nhiên, nhất quán."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\$\s*(\d+(?:[,.]\d+)?)", r"\1 đô la Mỹ", text)
    text = re.sub(r"(\d+(?:[,.]\d+)?)\s*\$", r"\1 đô la Mỹ", text)
    text = re.sub(r"(?<=\d)\s*%", " phần trăm", text)
    text = re.sub(r"(?<=\d)\s*km\b", " ki lô mét", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(tr|trieu)\b", "triệu", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(tỉ|ty)\b", "tỷ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d+(?:[,.]\d+)?\b", _speak_number, text)
    return re.sub(r"\s+([.!?,:;])", r"\1", text).strip()


def split_long_sentences(text: str, max_words: int = 24) -> str:
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
            result.append(" ".join(words[:cut]).rstrip(".,:;") + ".")
            words = words[cut:]
        if words:
            result.append(" ".join(words))
    return " ".join(result)


def speech_parts(text: str) -> list[tuple[str, int]]:
    parts, start = [], 0
    for match in re.finditer(r"[.!?,:;]", text):
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
    await edge_tts.Communicate(
        text=text, voice=preset.voice, rate=preset.rate, pitch=preset.pitch, volume=preset.volume
    ).save(str(destination))


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


MASTERING_FILTERS = {
    "power_plus": "highpass=f=55,equalizer=f=90:t=q:w=1.0:g=5,equalizer=f=180:t=q:w=1.1:g=3,equalizer=f=3200:t=q:w=1.2:g=1.5,acompressor=threshold=-20dB:ratio=4:attack=8:release=160:makeup=4,alimiter=limit=0.89:attack=5:release=60,loudnorm=I=-14:TP=-1.0:LRA=5",
    "power": "highpass=f=65,equalizer=f=110:t=q:w=1:g=3,acompressor=threshold=-19dB:ratio=3:attack=10:release=170:makeup=3,alimiter=limit=0.91,loudnorm=I=-15:TP=-1.2:LRA=6",
    "mc": "highpass=f=75,equalizer=f=2500:t=q:w=1:g=2,acompressor=threshold=-18dB:ratio=2.8:attack=10:release=150,loudnorm=I=-16:TP=-1.5:LRA=7",
    "podcast": "highpass=f=65,equalizer=f=130:t=q:w=1:g=2,acompressor=threshold=-21dB:ratio=2.5:attack=18:release=220,loudnorm=I=-17:TP=-1.5:LRA=7",
    "emotional": "highpass=f=65,equalizer=f=150:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=2.2:attack=20:release=240,loudnorm=I=-16:TP=-1.5:LRA=8",
    "business": "highpass=f=70,equalizer=f=120:t=q:w=1:g=2.5,acompressor=threshold=-18dB:ratio=3:attack=10:release=160,loudnorm=I=-15:TP=-1.3:LRA=6",
    "gentle": "highpass=f=85,equalizer=f=3500:t=q:w=1:g=1.5,acompressor=threshold=-20dB:ratio=2:attack=20:release=240,loudnorm=I=-17:TP=-1.5:LRA=8",
}


def _master_audio(source: Path, destination: Path, preset: VoicePreset) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-af",
        MASTERING_FILTERS[preset.mastering], "-c:a", "libmp3lame", "-b:a", "192k", str(destination),
    ], check=True)


async def synthesize(text: str, destination: Path, preset_name: str) -> str:
    preset = resolve_preset(preset_name)
    parts = speech_parts(split_long_sentences(clean_text(text), preset.max_words))
    if not parts:
        raise ValueError("Nội dung TTS trống")
    with tempfile.TemporaryDirectory(prefix="sticktalk-tts-") as directory:
        temporary = Path(directory)
        speech_files = [temporary / f"speech-{index}.mp3" for index in range(len(parts))]
        # Không fallback sang gTTS/HoàiMy: sai provider phải dừng render thay vì xuất sai giọng.
        for (chunk, _), output in zip(parts, speech_files):
            await _edge_part(chunk, output, preset)
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
        _master_audio(joined, destination, preset)
    return preset.voice


async def run(preset_name: str, selected_region: str) -> None:
    preset = resolve_preset(preset_name)
    validate_voice_region(selected_region, preset.voice)
    story = json.loads(Path("assets/story.json").read_text(encoding="utf-8"))
    text = " ".join(scene["narration"] for scene in story["scenes"])
    actual_voice = await synthesize(text, Path("assets/narration.mp3"), preset.name)
    if actual_voice != preset.voice:
        raise RuntimeError(f"Sai voice: yêu cầu {preset.voice}, thực tế {actual_voice}")
    print(f"Voice thực tế sử dụng:\n{actual_voice}\n\nPreset:\n{preset.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default=DEFAULT_PRESET, help="Tên preset tiếng Việt (hoặc alias cũ)")
    parser.add_argument(
        "--vung-giong", "--voice-region", default="Chưa xác định",
        choices=("Miền Bắc", "Miền Nam", "Chưa xác định"), help="Phân loại vùng giọng đã xác nhận thủ công",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args.preset, args.vung_giong))
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
