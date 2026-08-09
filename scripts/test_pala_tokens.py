from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pala_tokens


class PalaTokensTests(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(pala_tokens.approx_tokens(""), 0)

    def test_four_chars_one_token(self) -> None:
        self.assertEqual(pala_tokens.approx_tokens("abcd"), 1)

    def test_unicode_counts_characters(self) -> None:
        # 8 unicode chars -> 2 approx tokens
        self.assertEqual(pala_tokens.approx_tokens("Palaİşte"), 2)


if __name__ == "__main__":
    unittest.main()
