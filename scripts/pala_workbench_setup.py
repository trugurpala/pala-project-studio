#!/usr/bin/env python3
"""Owner-readable, fixed-mode Professional Workbench setup orchestration."""

from __future__ import annotations

import unicodedata


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


def interpret_intent(value: str) -> str:
    text = _normalized(value)
    if any(word in text for word in ("doctor", "saglik", "kontrol et")):
        return "doctor"
    if any(word in text for word in ("onar", "repair")):
        return "repair"
    if any(word in text for word in ("guncelle", "update", "yukselt")):
        return "update"
    if any(word in text for word in (" kur", "kur ", "yukle", "install")) or text.endswith(" kur"):
        return "install"
    return "unknown"


def setup(
    mode: str,
    *,
    install_codegraph,
    install_semgrep,
    doctor,
    offline: bool = False,
) -> dict[str, object]:
    base = {
        "mode": mode,
        "browser_opened": False,
        "helper_ui_opened": False,
        "global_path_mutated": False,
        "remote_publication": "not-run",
        "deploy": "not-run",
    }
    if mode == "unknown":
        return {
            **base,
            "status": "not-run",
            "changed": False,
            "owner_message": "Niyet anlasilmadi. Kur, guncelle, onar veya Doctor deyin.",
        }
    if mode == "doctor":
        health = doctor()
        return {
            **base,
            "status": "ready" if health.get("healthy") else "attention_required",
            "changed": False,
            "doctor": health,
            "owner_message": "Pala Workbench hazir. Sizden gereken: Hicbir sey." if health.get("healthy") else "Pala Workbench dikkat gerektiriyor.",
        }
    codegraph = install_codegraph()
    if offline and codegraph.get("state") in {"offline", "absent"}:
        return {
            **base,
            "status": "blocked",
            "changed": False,
            "reason": "offline-artifact-unavailable",
            "codegraph": codegraph,
        }
    semgrep = install_semgrep()
    if offline and semgrep.get("state") in {"offline", "absent"}:
        return {
            **base,
            "status": "blocked",
            "changed": bool(codegraph.get("changed")),
            "reason": "offline-artifact-unavailable",
            "codegraph": codegraph,
            "semgrep": semgrep,
        }
    health = doctor()
    changed = bool(codegraph.get("changed") or semgrep.get("changed"))
    return {
        **base,
        "status": "ready" if health.get("healthy") else "blocked",
        "changed": changed,
        "codegraph": codegraph,
        "semgrep": semgrep,
        "doctor": health,
        "owner_message": "Pala Workbench hazir. Sizden gereken: Hicbir sey." if health.get("healthy") else "Pala Workbench kurulumu tamamlanamadi; Doctor ayrintisini inceleyin.",
    }
