from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pala_design
import pala_tokens

ROOT = Path(__file__).resolve().parent.parent


class DesignAdvisorTests(unittest.TestCase):
    def test_recommendation_is_advisory_and_cannot_write_authority(self) -> None:
        advisor = pala_design.DesignAdvisor()
        recommendation = advisor.recommend(
            pala_design.DesignRequest(product_category="delivery dashboard"),
            {"layout_pattern": "sidebar", "source_refs": ["donor:ui-ux-pro-max"]},
        )
        self.assertEqual(recommendation.status, "advisory")
        with self.assertRaises(PermissionError):
            advisor.apply_to_authority(recommendation, object())

    def test_accessibility_overrides_low_contrast_advice(self) -> None:
        recommendation = pala_design.DesignAdvisor().recommend(
            pala_design.DesignRequest(product_category="dashboard"),
            {"color_direction": "low contrast", "contrast_ratio": 2.0},
            constraints=(pala_design.DesignConstraint("contrast", "minimum 4.5:1", "P1"),),
        )
        self.assertIn("accessibility", recommendation.color_direction.casefold())
        self.assertEqual(recommendation.status, "advisory")

    def test_token_layers_validate_and_drift_is_detected(self) -> None:
        result = pala_tokens.validate_token_document(ROOT / "design" / "tokens.json")
        self.assertEqual(result["status"], "passed")
        drift = pala_tokens.token_drift(
            ROOT / "design" / "tokens.json", ["semantic.text.primary", "component.card.background"]
        )
        self.assertEqual(drift["status"], "passed")
        self.assertIn("component.card.missing", pala_tokens.token_drift(ROOT / "design" / "tokens.json", ["component.card.missing"])["unknown"])


if __name__ == "__main__":
    unittest.main()
