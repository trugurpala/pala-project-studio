#!/usr/bin/env python3
"""Provider-neutral, advisory-only design intelligence contracts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pala_tokens


@dataclass(frozen=True)
class DesignRequest:
    product_category: str
    layout_pattern: str = ""
    constraints: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class DesignConstraint:
    name: str
    requirement: str
    severity: str = "P1"


@dataclass(frozen=True)
class DesignEvidence:
    source_ref: str
    summary: str


@dataclass(frozen=True)
class DesignRecommendation:
    product_category: str
    layout_pattern: str = ""
    style_direction: str = ""
    color_direction: str = ""
    typography_direction: str = ""
    component_guidance: tuple[str, ...] = ()
    interaction_guidance: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()
    accessibility_notes: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence: tuple[DesignEvidence, ...] = ()
    status: str = field(default="advisory", init=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_category": self.product_category,
            "layout_pattern": self.layout_pattern,
            "style_direction": self.style_direction,
            "color_direction": self.color_direction,
            "typography_direction": self.typography_direction,
            "component_guidance": list(self.component_guidance),
            "interaction_guidance": list(self.interaction_guidance),
            "anti_patterns": list(self.anti_patterns),
            "accessibility_notes": list(self.accessibility_notes),
            "source_refs": list(self.source_refs),
            "evidence": [item.__dict__ for item in self.evidence],
            "status": self.status,
        }


class DesignAdvisor:
    """Return suggestions; intentionally has no canonical-state write API."""

    def recommend(
        self,
        request: DesignRequest,
        advisory: dict[str, Any] | None = None,
        *,
        constraints: tuple[DesignConstraint, ...] = (),
    ) -> DesignRecommendation:
        payload = dict(advisory or {})
        color = str(payload.get("color_direction") or "")
        notes: list[str] = [str(item) for item in payload.get("accessibility_notes", []) if str(item)]
        contrast = payload.get("contrast_ratio")
        needs_contrast = any("contrast" in item.name.casefold() for item in constraints)
        if needs_contrast and isinstance(contrast, (int, float)) and contrast < 4.5:
            color = "accessibility-first contrast required"
            notes.append("Accessibility constraint overrides the advisory color direction.")
        refs = tuple(str(item) for item in payload.get("source_refs", request.source_refs))
        evidence = tuple(
            DesignEvidence(str(item.get("source_ref")), str(item.get("summary")))
            for item in payload.get("evidence", [])
            if isinstance(item, dict) and item.get("source_ref")
        )
        return DesignRecommendation(
            product_category=request.product_category,
            layout_pattern=str(payload.get("layout_pattern") or request.layout_pattern),
            style_direction=str(payload.get("style_direction") or ""),
            color_direction=color,
            typography_direction=str(payload.get("typography_direction") or ""),
            component_guidance=tuple(str(item) for item in payload.get("component_guidance", [])),
            interaction_guidance=tuple(str(item) for item in payload.get("interaction_guidance", [])),
            anti_patterns=tuple(str(item) for item in payload.get("anti_patterns", [])),
            accessibility_notes=tuple(notes),
            source_refs=refs,
            evidence=evidence,
        )

    @staticmethod
    def apply_to_authority(_recommendation: DesignRecommendation, _authority: object) -> None:
        raise PermissionError("DesignAdvisor recommendations are advisory and cannot mutate Pala authority")


def validate_tokens(root: Path) -> dict[str, object]:
    return pala_tokens.validate_token_document(root / "design" / "tokens.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    result = validate_tokens(Path(__file__).resolve().parent.parent) if args.validate else {"status": "advisory"}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result["status"] in {"passed", "advisory"} else 1)
