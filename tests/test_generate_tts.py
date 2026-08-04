import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_tts import synthesize
from scripts.tts.edge_tts_provider import EdgeTtsProvider
from scripts.tts.presets import DEFAULT_PRESET, PRESETS, resolve_preset


class EdgeTtsTest(unittest.TestCase):
    def test_chi_con_5_preset_edge(self):
        self.assertEqual(DEFAULT_PRESET, "Nam tiếng Việt — Tự nhiên")
        self.assertEqual(len(PRESETS), 5)
        self.assertTrue(all(preset.provider == "edge" for preset in PRESETS.values()))

    def test_voice_theo_gioi_tinh(self):
        male = [preset for preset in PRESETS.values() if preset.gender == "Nam"]
        female = [preset for preset in PRESETS.values() if preset.gender == "Nữ"]
        self.assertTrue(all(preset.voice == "vi-VN-NamMinhNeural" for preset in male))
        self.assertTrue(all(preset.voice == "vi-VN-HoaiMyNeural" for preset in female))

    def test_giong_khong_ton_tai_bao_ro(self):
        with self.assertRaisesRegex(ValueError, "Giọng đọc không hợp lệ"):
            resolve_preset("Google Nam Neural 2")

    def test_khong_cho_nha_cung_cap_khac_edge(self):
        with self.assertRaisesRegex(ValueError, "chỉ hỗ trợ Microsoft Edge TTS"):
            asyncio.run(synthesize("Xin chào", Path("khong-tao.mp3"), DEFAULT_PRESET, "google"))

    @patch("scripts.generate_tts.MP3")
    @patch.object(EdgeTtsProvider, "synthesize")
    def test_edge_tao_file_va_tra_dung_voice(self, mock_synthesize, mock_mp3):
        preset = resolve_preset(DEFAULT_PRESET)

        async def fake(text, destination, selected):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"ID3-du-lieu-mock")
            return selected.voice

        mock_synthesize.side_effect = fake
        mock_mp3.return_value.info.length = 1.25
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "thu.mp3"
            actual = asyncio.run(synthesize("Xin chào.", target, DEFAULT_PRESET))
            self.assertEqual(actual, "vi-VN-NamMinhNeural")
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
