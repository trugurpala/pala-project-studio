#!/usr/bin/env python3
"""Privacy-safe durable continuity and immutable Project History v1."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import pala_db
from pala_context_receipt import (
    ContextExpectation,
    ContextReceipt,
    ContextReceiptError,
    receipt_summary,
)
from pala_privacy import has_private_data
from pala_project_profile import ProjectProfile, ProjectProfileError

PROJECT_HISTORY_SCHEMA = "pala.project_history.v1"
AUTHORITY = "ProjectHistory/read-only"
MAX_TEXT = 500
MAX_ITEMS = 16

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REPOSITORY_ID = re.compile(r"^[0-9a-f]{24}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_LIFECYCLES = ("project-closed", "project-reopened")


class ProjectHistoryError(ValueError):
    """Sanitized, stable history failure."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code} at {field}")

    def finding(self) -> dict[str, str]:
        return {"status": "blocked", "code": self.code, "field": self.field}


def _canonical(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(
    value: object,
    field: str,
    *,
    limit: int = MAX_TEXT,
    identifier: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", field)
    normalized = unicodedata.normalize("NFC", value.strip())
    if len(normalized.encode("utf-8")) > limit or has_private_data(normalized):
        code = (
            "HISTORY_PRIVATE_DATA_REJECTED"
            if has_private_data(normalized)
            else "HISTORY_LIMIT_EXCEEDED"
        )
        raise ProjectHistoryError(code, field)
    if identifier and not _IDENTIFIER.fullmatch(normalized):
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", field)
    return normalized


def _optional_text(
    value: object,
    field: str,
    *,
    limit: int = 160,
    identifier: bool = False,
) -> str | None:
    if value is None:
        return None
    return _text(value, field, limit=limit, identifier=identifier)


def _items(values: Sequence[object], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or len(values) > MAX_ITEMS:
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", field)
    parsed = {
        _text(item, f"{field}[{index}]", limit=240, identifier=True)
        for index, item in enumerate(values)
    }
    return tuple(sorted(parsed, key=str.casefold))


def _history_id(body: dict[str, object]) -> str:
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _safe_continuity_read_model(row: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": PROJECT_HISTORY_SCHEMA,
        "validation_status": "passed",
        "project_id": row["project_id"],
        "repository_id": row["repository_id"],
        "worktree_id": row["worktree_id"],
        "profile_digest": row["profile_digest"],
        "profile_kind": row["profile_kind"],
        "data_classification": row["data_classification"],
        "receipt_id": row["receipt_id"],
        "receipt_validation_status": row["receipt_validation_status"],
        "updated_at": row["updated_at"],
        "authority": AUTHORITY,
        "can_complete": False,
    }


def persist_context_summary(
    profile_payload: object,
    receipt_payload: object,
    *,
    expected: ContextExpectation,
    path: Path,
) -> dict[str, object]:
    """Validate owner contracts and persist only their safe scalar bindings."""
    try:
        profile = ProjectProfile.from_dict(profile_payload)
        receipt = (
            receipt_payload
            if isinstance(receipt_payload, ContextReceipt)
            else ContextReceipt.from_dict(receipt_payload, expected=expected)
        )
        if isinstance(receipt_payload, ContextReceipt):
            ContextReceipt.from_dict(receipt.to_dict(), expected=expected)
        validation = receipt_summary(receipt, expected=expected)
    except (ProjectProfileError, ContextReceiptError) as exc:
        raise ProjectHistoryError("HISTORY_CONTEXT_INVALID", "context") from exc
    if validation.get("validation_status") != "passed":
        raise ProjectHistoryError("HISTORY_CONTEXT_INVALID", "receipt")
    profile_digest = profile.digest()
    if receipt.profile_digest != profile_digest:
        raise ProjectHistoryError("HISTORY_CONTEXT_MISMATCH", "profile_digest")
    project_id = _text(profile.project_id, "project_id", limit=160, identifier=True)
    repository_id = expected.project.repository_id
    worktree_id = expected.project.worktree_id
    if not _REPOSITORY_ID.fullmatch(repository_id) or not _REPOSITORY_ID.fullmatch(worktree_id):
        raise ProjectHistoryError("HISTORY_CONTEXT_INVALID", "project")
    try:
        row = pala_db.upsert_project_continuity(
            {
                "project_id": project_id,
                "repository_id": repository_id,
                "worktree_id": worktree_id,
                "profile_digest": profile_digest,
                "profile_kind": profile.profile_kind.value,
                "data_classification": profile.data_classification.value,
                "receipt_id": receipt.receipt_id,
                "receipt_validation_status": "passed",
            },
            path=path,
        )
    except (ValueError, pala_db.StoreError) as exc:
        raise ProjectHistoryError("HISTORY_CONTINUITY_CONFLICT", "project_id") from exc
    return _safe_continuity_read_model(row)


def get_continuity(project_id: str, *, path: Path) -> dict[str, object]:
    project = _text(project_id, "project_id", limit=160, identifier=True)
    row = pala_db.get_project_continuity(project, path=path)
    if row is None:
        return {
            "schema_version": PROJECT_HISTORY_SCHEMA,
            "validation_status": "not-run",
            "project_id": project,
            "authority": AUTHORITY,
            "can_complete": False,
        }
    return _safe_continuity_read_model(row)


def _append(
    *,
    project_id: str,
    repository_id: str,
    lifecycle: str,
    body: dict[str, object],
    path: Path,
) -> dict[str, object]:
    history_id = _history_id(body)
    payload = {
        "schema_version": PROJECT_HISTORY_SCHEMA,
        "history_id": history_id,
        **body,
        "authority": AUTHORITY,
        "can_complete": False,
    }
    created_at = _now()
    try:
        row, _created = pala_db.append_project_history(
            {
                "history_id": history_id,
                "project_id": project_id,
                "repository_id": repository_id,
                "lifecycle": lifecycle,
                "payload_json": _canonical(payload),
                "created_at": created_at,
            },
            path=path,
        )
    except (ValueError, pala_db.StoreError) as exc:
        raise ProjectHistoryError("HISTORY_APPEND_CONFLICT", "history_id") from exc
    restored = _parse_row(row)
    if restored is None:
        raise ProjectHistoryError("HISTORY_ROW_CORRUPT", "history_id")
    return restored


def record_closure(
    project_id: str,
    *,
    current_receipt_id: str,
    summary: str,
    final_commit: str,
    release_ref: str | None,
    risk_codes: Sequence[object],
    lessons: Sequence[object],
    authority_ref: str,
    path: Path,
) -> dict[str, object]:
    project = _text(project_id, "project_id", limit=160, identifier=True)
    continuity = pala_db.get_project_continuity(project, path=path)
    if continuity is None:
        raise ProjectHistoryError("HISTORY_CONTEXT_REQUIRED", "project_id")
    if not isinstance(current_receipt_id, str) or not _DIGEST.fullmatch(current_receipt_id):
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", "current_receipt_id")
    if current_receipt_id != continuity["receipt_id"]:
        raise ProjectHistoryError("HISTORY_CONTEXT_MISMATCH", "current_receipt_id")
    if not isinstance(final_commit, str) or not _COMMIT.fullmatch(final_commit):
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", "final_commit")
    body: dict[str, object] = {
        "lifecycle": "project-closed",
        "project_id": project,
        "repository_id": continuity["repository_id"],
        "worktree_id": continuity["worktree_id"],
        "profile_digest": continuity["profile_digest"],
        "context_receipt_id": current_receipt_id,
        "summary": _text(summary, "summary"),
        "final_commit": final_commit,
        "release_ref": _optional_text(release_ref, "release_ref", identifier=True),
        "risk_codes": list(_items(risk_codes, "risk_codes")),
        "lessons": list(_items(lessons, "lessons")),
        "authority_ref": _text(authority_ref, "authority_ref", limit=160, identifier=True),
        "prior_history_id": None,
    }
    return _append(
        project_id=project,
        repository_id=str(continuity["repository_id"]),
        lifecycle="project-closed",
        body=body,
        path=path,
    )


def record_reopen(
    project_id: str,
    *,
    closure_id: str,
    profile_payload: object,
    receipt_payload: object,
    expected: ContextExpectation,
    authority_ref: str,
    path: Path,
) -> dict[str, object]:
    project = _text(project_id, "project_id", limit=160, identifier=True)
    if not isinstance(closure_id, str) or not _DIGEST.fullmatch(closure_id):
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", "closure_id")
    rows = pala_db.list_project_history_rows(project_id=project, limit=10_000, path=path)
    closure_row = next((row for row in rows if row["history_id"] == closure_id), None)
    closure = _parse_row(closure_row) if closure_row is not None else None
    if closure is None or closure.get("lifecycle") != "project-closed":
        raise ProjectHistoryError("HISTORY_CLOSURE_NOT_FOUND", "closure_id")
    continuity = persist_context_summary(
        profile_payload, receipt_payload, expected=expected, path=path
    )
    if continuity["project_id"] != project:
        raise ProjectHistoryError("HISTORY_CONTEXT_MISMATCH", "project_id")
    body: dict[str, object] = {
        "lifecycle": "project-reopened",
        "project_id": project,
        "repository_id": continuity["repository_id"],
        "worktree_id": continuity["worktree_id"],
        "profile_digest": continuity["profile_digest"],
        "context_receipt_id": continuity["receipt_id"],
        "summary": "project reopened with fresh live context",
        "final_commit": None,
        "release_ref": None,
        "risk_codes": [],
        "lessons": [],
        "authority_ref": _text(authority_ref, "authority_ref", limit=160, identifier=True),
        "prior_history_id": closure_id,
    }
    return _append(
        project_id=project,
        repository_id=str(continuity["repository_id"]),
        lifecycle="project-reopened",
        body=body,
        path=path,
    )


def _parse_row(row: dict[str, object] | None) -> dict[str, object] | None:
    if row is None or not isinstance(row.get("payload_json"), str):
        return None
    try:
        payload = json.loads(str(row["payload_json"]))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    required = {
        "schema_version",
        "history_id",
        "lifecycle",
        "project_id",
        "repository_id",
        "worktree_id",
        "profile_digest",
        "context_receipt_id",
        "summary",
        "final_commit",
        "release_ref",
        "risk_codes",
        "lessons",
        "authority_ref",
        "prior_history_id",
        "authority",
        "can_complete",
    }
    if set(payload) != required:
        return None
    body = {
        key: payload[key]
        for key in payload
        if key not in {"schema_version", "history_id", "authority", "can_complete"}
    }
    if (
        payload["schema_version"] != PROJECT_HISTORY_SCHEMA
        or payload["authority"] != AUTHORITY
        or payload["can_complete"] is not False
        or payload["history_id"] != row.get("history_id")
        or payload["history_id"] != _history_id(body)
        or payload["project_id"] != row.get("project_id")
        or payload["repository_id"] != row.get("repository_id")
        or payload["lifecycle"] not in _LIFECYCLES
        or payload["lifecycle"] != row.get("lifecycle")
    ):
        return None
    return {**payload, "created_at": row.get("created_at")}


def list_history(
    *,
    project_id: str | None = None,
    repository_id: str | None = None,
    lifecycle: str | None = None,
    limit: int = 50,
    path: Path,
) -> dict[str, object]:
    project = (
        _text(project_id, "project_id", limit=160, identifier=True)
        if project_id is not None
        else None
    )
    repository = None
    if repository_id is not None:
        if not isinstance(repository_id, str) or not _REPOSITORY_ID.fullmatch(repository_id):
            raise ProjectHistoryError("HISTORY_VALUE_INVALID", "repository_id")
        repository = repository_id
    if lifecycle is not None and lifecycle not in _LIFECYCLES:
        raise ProjectHistoryError("HISTORY_VALUE_INVALID", "lifecycle")
    rows = pala_db.list_project_history_rows(
        project_id=project,
        repository_id=repository,
        lifecycle=lifecycle,
        limit=max(min(int(limit), 200), 0),
        path=path,
    )
    items: list[dict[str, object]] = []
    corrupt = False
    for row in rows:
        parsed = _parse_row(row)
        if parsed is None:
            corrupt = True
        else:
            items.append(parsed)
    model: dict[str, object] = {
        "schema_version": PROJECT_HISTORY_SCHEMA,
        "validation_status": "blocked" if corrupt else "passed",
        "items": items,
        "authority": AUTHORITY,
        "can_complete": False,
    }
    if corrupt:
        model["finding"] = {
            "status": "blocked",
            "code": "HISTORY_ROW_CORRUPT",
            "field": "project_history",
        }
    return model
