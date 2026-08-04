import unittest

from scripts.generate_tts import clean_text, number_to_vietnamese, speech_parts, split_long_sentences


class GenerateTtsTest(unittest.TestCase):
    def test_clean_text_normalizes_units_numbers_and_spaces(self):
        self.assertEqual(
            clean_text("  12,5%   tăng trên  21 km, đạt 2 tỉ và 3 tr. "),
            "mười hai phẩy năm phần trăm tăng trên hai mươi mốt ki lô mét, đạt hai tỷ và ba triệu.",
        )

    def test_number_to_vietnamese(self):
        self.assertEqual(number_to_vietnamese(1_025_000_000), "một tỷ không trăm hai mươi lăm triệu")

    def test_pause_lengths(self):
        self.assertEqual(
            speech_parts("Một. Hai, Ba: Bốn; Năm"),
            [("Một", 500), ("Hai", 180), ("Ba", 250), ("Bốn", 220), ("Năm", 0)],
        )

    def test_long_sentence_is_split_at_25_words(self):
        text = " ".join(f"từ{i}" for i in range(1, 53))
        result = split_long_sentences(text)
        self.assertEqual([len(part.split()) for part in result.split(". ")], [25, 25, 2])


if __name__ == "__main__":
    unittest.main()
