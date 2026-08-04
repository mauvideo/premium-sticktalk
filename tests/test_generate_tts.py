import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.generate_tts import (
    HOAI_MY, NAM_MINH, MASTERING_FILTERS, PRESETS, clean_text,
    number_to_vietnamese, resolve_preset, speech_parts, split_long_sentences,
    _master_audio,
)


class GenerateTtsTest(unittest.TestCase):
    def test_all_northern_male_presets_are_nam_minh(self):
        male = [preset for name, preset in PRESETS.items() if name.startswith("Nam miền Bắc")]
        self.assertEqual(len(male), 6)
        self.assertTrue(all(preset.voice == NAM_MINH for preset in male))
        self.assertEqual(PRESETS["Nữ miền Bắc Dịu nhẹ"].voice, HOAI_MY)

    def test_all_required_presets_exist(self):
        self.assertEqual(set(PRESETS), {
            "Nam miền Bắc MC", "Nam miền Bắc Nội lực", "Nam miền Bắc Nội lực Plus",
            "Nam miền Bắc Podcast", "Nam miền Bắc Truyền cảm", "Nam miền Bắc Doanh nhân",
            "Nữ miền Bắc Dịu nhẹ",
        })

    def test_old_alias_resolves_without_changing_actual_preset(self):
        self.assertEqual(resolve_preset("nam_bac_noi_luc_plus").name, "Nam miền Bắc Nội lực Plus")

    def test_clean_text_normalizes_currency_units_numbers_and_spaces(self):
        self.assertEqual(
            clean_text("  $12,5 tăng 21 km, đạt 2 tỉ, 3 tr và 15%. "),
            "mười hai phẩy năm đô la Mỹ tăng hai mươi mốt ki lô mét, đạt hai tỷ, ba triệu và mười lăm phần trăm.",
        )

    def test_number_to_vietnamese(self):
        self.assertEqual(number_to_vietnamese(1_025_000_000), "một tỷ không trăm hai mươi lăm triệu")

    def test_pause_lengths_include_expressive_punctuation(self):
        self.assertEqual(
            speech_parts("Một. Hai, Ba: Bốn; Năm? Sáu!"),
            [("Một", 560), ("Hai", 210), ("Ba", 300), ("Bốn", 330), ("Năm", 620), ("Sáu", 600)],
        )

    def test_long_sentence_is_split_at_requested_length(self):
        text = " ".join(f"từ{i}" for i in range(1, 53))
        result = split_long_sentences(text, 25)
        self.assertEqual([len(part.split()) for part in result.split(". ")], [25, 25, 2])

    def test_plus_is_slower_louder_and_has_full_mastering(self):
        plus = PRESETS["Nam miền Bắc Nội lực Plus"]
        self.assertEqual((plus.rate, plus.volume, plus.max_words), ("-14%", "+14%", 20))
        audio_filter = MASTERING_FILTERS[plus.mastering]
        for stage in ("equalizer=f=90", "equalizer=f=180", "acompressor=", "alimiter=", "loudnorm="):
            self.assertIn(stage, audio_filter)

    @patch("scripts.generate_tts.subprocess.run")
    def test_mastering_invokes_ffmpeg_with_plus_filter(self, run):
        preset = PRESETS["Nam miền Bắc Nội lực Plus"]
        _master_audio(Path("input.mp3"), Path("output.mp3"), preset)
        command = run.call_args.args[0]
        self.assertIn(MASTERING_FILTERS["power_plus"], command)
        run.assert_called_once_with(command, check=True)


if __name__ == "__main__":
    unittest.main()
