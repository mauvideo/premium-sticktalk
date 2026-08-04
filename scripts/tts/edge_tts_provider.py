"""Nhà cung cấp Microsoft Edge TTS hiện hữu."""

import tempfile
from pathlib import Path

from .audio_postprocess import postprocess
from .base import TtsProvider


class EdgeTtsProvider(TtsProvider):
    ten_nha_cung_cap = "MICROSOFT EDGE TTS"

    async def synthesize(self, text: str, destination: Path, preset) -> str:
        import edge_tts
        with tempfile.TemporaryDirectory(prefix="sticktalk-edge-") as directory:
            raw = Path(directory) / "edge-goc.mp3"
            await edge_tts.Communicate(text=text, voice=preset.voice, rate=preset.speed,
                                       pitch=preset.pitch, volume=preset.volume).save(str(raw))
            destination.parent.mkdir(parents=True, exist_ok=True)
            postprocess(raw, destination, preset)
        return preset.voice
