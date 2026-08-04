import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_tts import synthesize
from scripts.tts.google_tts import GoogleTtsProvider
from scripts.tts.presets import GOOGLE_PRESETS, PRESETS, resolve_preset


class GoogleTtsTest(unittest.TestCase):
    def test_voice_ids_chinh_xac_va_khong_fallback(self):
        expected={"google_nam_neural2":"vi-VN-Neural2-D","google_nam_wavenet":"vi-VN-Wavenet-D","google_nam_standard":"vi-VN-Standard-D","google_nam_chirp_tram":"vi-VN-Chirp3-HD-Charon","google_nam_chirp_noi_luc":"vi-VN-Chirp3-HD-Fenrir"}
        self.assertEqual({k:GOOGLE_PRESETS[k].voice for k in expected},expected)

    def test_khong_cho_tron_nha_cung_cap(self):
        with self.assertRaisesRegex(RuntimeError,"Không chuyển giọng tự động"):
            asyncio.run(synthesize("Xin chào",Path("khong-tao.mp3"),"Google Nam Neural 2","edge"))

    def test_google_thieu_credentials_bao_loi_tieng_viet(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaisesRegex(RuntimeError,"Chưa cấu hình Google Cloud"):
                GoogleTtsProvider()._client()

    @patch("scripts.generate_tts.MP3")
    @patch.object(GoogleTtsProvider,"synthesize")
    def test_mock_google_ghi_metadata_dung(self,mock_synthesize,mock_mp3):
        preset=resolve_preset("google_nam_standard")
        async def fake(text,destination,selected):
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(b"ID3-du-lieu-mock");return selected.voice
        mock_synthesize.side_effect=fake;mock_mp3.return_value.info.length=1.25
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"thu.mp3"
            asyncio.run(synthesize("Xin chào.",target,preset.code,"google"))
            info=json.loads(Path("output/tts-info.json").read_text(encoding="utf-8"))
            self.assertEqual((info["nha_cung_cap"],info["voice_id"]),("google","vi-VN-Standard-D"))

    def test_edge_presets_van_con(self):
        self.assertIn("Nam miền Bắc Nội lực Plus",PRESETS)
        self.assertEqual(PRESETS["Nam miền Bắc Nội lực Plus"].provider,"edge")

if __name__=="__main__":unittest.main()
