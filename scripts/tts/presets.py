"""Cấu hình giọng đọc Edge TTS dùng trong Premium StickTalk."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePreset:
    code: str
    name: str
    provider: str
    voice: str
    gender: str
    speed: str
    pitch: str
    volume: str = "+0%"
    mastering: str = "tu_nhien"
    max_words: int = 24


def _edge(code, name, voice, rate, pitch, volume, mastering, max_words=24):
    return VoicePreset(
        code=code,
        name=name,
        provider="edge",
        voice=voice,
        gender="Nữ" if "Nữ" in name else "Nam",
        speed=rate,
        pitch=pitch,
        volume=volume,
        mastering=mastering,
        max_words=max_words,
    )


NAM_MINH = "vi-VN-NamMinhNeural"
HOAI_MY = "vi-VN-HoaiMyNeural"

EDGE_PRESETS = {
    "Nam tiếng Việt — Tự nhiên": _edge(
        "nam_tieng_viet_tu_nhien", "Nam tiếng Việt — Tự nhiên",
        NAM_MINH, "-3%", "-2Hz", "+6%", "mc",
    ),
    "Nam tiếng Việt — Nội lực": _edge(
        "nam_tieng_viet_noi_luc", "Nam tiếng Việt — Nội lực",
        NAM_MINH, "-8%", "-5Hz", "+9%", "power",
    ),
    "Nam tiếng Việt — Phát thanh": _edge(
        "nam_tieng_viet_phat_thanh", "Nam tiếng Việt — Phát thanh",
        NAM_MINH, "-6%", "-4Hz", "+8%", "business",
    ),
    "Nam tiếng Việt — Kể chuyện": _edge(
        "nam_tieng_viet_ke_chuyen", "Nam tiếng Việt — Kể chuyện",
        NAM_MINH, "-12%", "-4Hz", "+7%", "emotional", 20,
    ),
    "Nữ tiếng Việt — Tự nhiên": _edge(
        "nu_tieng_viet_tu_nhien", "Nữ tiếng Việt — Tự nhiên",
        HOAI_MY, "-8%", "+1Hz", "+4%", "gentle", 22,
    ),
}

PRESETS = dict(EDGE_PRESETS)
ALIASES = {preset.code: preset.name for preset in PRESETS.values()}
DEFAULT_PRESET = "Nam tiếng Việt — Tự nhiên"


def resolve_preset(name: str) -> VoicePreset:
    canonical = ALIASES.get(name, name)
    if canonical not in PRESETS:
        available = ", ".join(PRESETS)
        raise ValueError(f"Giọng đọc không hợp lệ: {name}. Các giọng hiện có: {available}")
    return PRESETS[canonical]
