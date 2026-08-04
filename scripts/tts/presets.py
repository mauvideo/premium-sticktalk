"""Nguồn cấu hình duy nhất cho toàn bộ Voice ID và preset giọng đọc."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePreset:
    code: str
    name: str
    provider: str
    voice: str
    gender: str
    speed: float | str
    pitch: float | str
    volume: str = "+0%"
    mastering: str = "tu_nhien"
    max_words: int = 24
    require_runtime_voice: bool = False


def _g(code, name, voice, gender="Nam", speed=1.0, mastering="tu_nhien", require=False):
    return VoicePreset(code, name, "google", voice, gender, speed, 0.0, mastering=mastering,
                       require_runtime_voice=require)


def _e(code, name, voice, rate, pitch, volume, mastering, max_words=24):
    return VoicePreset(code, name, "edge", voice, "Nữ" if "Nữ" in name else "Nam", rate, pitch,
                       volume, mastering, max_words)


GOOGLE_PRESETS = {
    "google_nam_bac_tram": _g("google_nam_bac_tram", "Google Nam tiếng Việt — Trầm", "vi-VN-Neural2-D", speed=.94, mastering="noi_luc"),
    "google_nam_bac_phat_thanh": _g("google_nam_bac_phat_thanh", "Google Nam tiếng Việt — Phát thanh", "vi-VN-Wavenet-D", speed=.96, mastering="phat_thanh"),
    "google_nam_bac_noi_luc": _g("google_nam_bac_noi_luc", "Google Nam tiếng Việt — Nội lực", "vi-VN-Chirp3-HD-Fenrir", speed=.94, mastering="noi_luc", require=True),
    "google_nam_neural2": _g("google_nam_neural2", "Google Nam Neural 2", "vi-VN-Neural2-D"),
    "google_nam_wavenet": _g("google_nam_wavenet", "Google Nam WaveNet", "vi-VN-Wavenet-D", speed=.98, mastering="phat_thanh"),
    "google_nam_standard": _g("google_nam_standard", "Google Nam Standard", "vi-VN-Standard-D"),
    "google_nam_chirp_tram": _g("google_nam_chirp_tram", "Google Nam Chirp HD Trầm", "vi-VN-Chirp3-HD-Charon", speed=.94, mastering="noi_luc", require=True),
    "google_nam_chirp_noi_luc": _g("google_nam_chirp_noi_luc", "Google Nam Chirp HD Nội lực", "vi-VN-Chirp3-HD-Fenrir", speed=.94, mastering="noi_luc", require=True),
    "google_nam_chirp_phat_thanh": _g("google_nam_chirp_phat_thanh", "Google Nam Chirp HD Phát thanh", "vi-VN-Chirp3-HD-Orus", speed=.96, mastering="phat_thanh", require=True),
    "google_nu_neural2": _g("google_nu_neural2", "Google Nữ Neural 2", "vi-VN-Neural2-A", gender="Nữ"),
    "google_nu_wavenet": _g("google_nu_wavenet", "Google Nữ WaveNet", "vi-VN-Wavenet-C", gender="Nữ"),
}

NAM_MINH, HOAI_MY = "vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"
EDGE_PRESETS = {
    "Nam tiếng Việt — Tự nhiên": _e("nam_tieng_viet_tu_nhien", "Nam tiếng Việt — Tự nhiên", NAM_MINH, "-3%", "-2Hz", "+6%", "mc"),
    "Nam tiếng Việt — Nội lực": _e("nam_tieng_viet_noi_luc", "Nam tiếng Việt — Nội lực", NAM_MINH, "-8%", "-5Hz", "+9%", "power"),
    "Nam tiếng Việt — Phát thanh": _e("nam_tieng_viet_phat_thanh", "Nam tiếng Việt — Phát thanh", NAM_MINH, "-6%", "-4Hz", "+8%", "business"),
    "Nam tiếng Việt — Kể chuyện": _e("nam_tieng_viet_ke_chuyen", "Nam tiếng Việt — Kể chuyện", NAM_MINH, "-12%", "-4Hz", "+7%", "emotional", 20),
    "Nữ tiếng Việt — Tự nhiên": _e("nu_tieng_viet_tu_nhien", "Nữ tiếng Việt — Tự nhiên", HOAI_MY, "-8%", "+1Hz", "+4%", "gentle", 22),
}
PRESETS = {**{p.name: p for p in GOOGLE_PRESETS.values()}, **EDGE_PRESETS}
ALIASES = {p.code: p.name for p in PRESETS.values()}
DEFAULT_PRESET = "Nam tiếng Việt — Tự nhiên"


def resolve_preset(name: str) -> VoicePreset:
    canonical = ALIASES.get(name, name)
    if canonical not in PRESETS:
        raise ValueError(f"Giọng đọc không hợp lệ: {name}")
    return PRESETS[canonical]
