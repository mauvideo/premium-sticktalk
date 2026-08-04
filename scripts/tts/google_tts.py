"""Google Cloud Text-to-Speech thật qua Application Default Credentials."""

import asyncio
import os
import tempfile
from pathlib import Path

from .audio_postprocess import postprocess
from .base import TtsProvider


class GoogleTtsProvider(TtsProvider):
    ten_nha_cung_cap = "GOOGLE CLOUD TTS"

    def _client(self):
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            raise RuntimeError("Chưa cấu hình Google Cloud Text-to-Speech. Hãy thêm GitHub Secret GOOGLE_CLOUD_CREDENTIALS_JSON.")
        try:
            from google.cloud import texttospeech
            return texttospeech, texttospeech.TextToSpeechClient()
        except Exception as error:
            raise RuntimeError(f"Không thể xác thực Google Cloud Text-to-Speech: {error}") from error

    def _synthesize_sync(self, text: str, destination: Path, preset) -> str:
        api, client = self._client()
        available = {v.name for v in client.list_voices(language_code="vi-VN").voices}
        if preset.voice not in available:
            raise RuntimeError(f"Google Cloud không có Voice ID '{preset.voice}' tại thời điểm chạy. Đã dừng, không dùng giọng thay thế.")
        response = client.synthesize_speech(
            request={"input": api.SynthesisInput(text=text),
                     "voice": api.VoiceSelectionParams(language_code="vi-VN", name=preset.voice),
                     "audio_config": api.AudioConfig(audio_encoding=api.AudioEncoding.MP3,
                                                     speaking_rate=float(preset.speed), pitch=float(preset.pitch))})
        with tempfile.TemporaryDirectory(prefix="sticktalk-google-") as directory:
            raw = Path(directory) / "google-goc.mp3"
            raw.write_bytes(response.audio_content)
            destination.parent.mkdir(parents=True, exist_ok=True)
            postprocess(raw, destination, preset)
        return preset.voice

    async def synthesize(self, text: str, destination: Path, preset) -> str:
        return await asyncio.to_thread(self._synthesize_sync, text, destination, preset)
