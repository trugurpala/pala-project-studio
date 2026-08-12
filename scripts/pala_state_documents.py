#!/usr/bin/env python3
"""Document discovery, registration, and doctor ownership for Pala state."""

from __future__ import annotations

import tomllib

from pala_state_core import *  # compatibility-owned primitives
from pala_state_core import _record_store_event

def instruction_report(
    root: Path,
    cwd: Path,
    max_bytes: int = DEFAULT_INSTRUCTION_LIMIT,
    fallback_names: tuple[str, ...] = (),
) -> dict[str, object]:
    """Report the canonical project instruction chain Codex loads for a run."""
    root = root.resolve()
    cwd = cwd.resolve()
    try:
        cwd.relative_to(root)
    except ValueError as exc:
        raise ValueError("cwd must remain inside project root") from exc

    directories = [root]
    current = root
    for part in cwd.relative_to(root).parts:
        current = current / part
        directories.append(current)

    selected: list[str] = []
    total_bytes = 0
    names = ("AGENTS.override.md", "AGENTS.md", *fallback_names)
    for directory in directories:
        match = next(
            (
                directory / name
                for name in names
                if (directory / name).is_file()
                and (directory / name).stat().st_size > 0
            ),
            None,
        )
        if match is None:
            continue
        selected.append(relative(root, match))
        total_bytes += match.stat().st_size
    return {
        "selected": selected,
        "total_bytes": total_bytes,
        "max_bytes": max_bytes,
        "within_budget": total_bytes <= max_bytes,
        "scope": "project-only",
        "note": (
            "Global ~/.codex instructions and configured fallback names are "
            "outside this project-only report unless passed explicitly."
        ),
    }


def configured_instruction_report(root: Path, cwd: Path) -> dict[str, object]:
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    config_path = codex_home / "config.toml"
    config: dict[str, object] = {}
    if config_path.is_file():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            config = {}
    raw_limit = config.get("project_doc_max_bytes", DEFAULT_INSTRUCTION_LIMIT)
    limit = (
        raw_limit
        if isinstance(raw_limit, int) and raw_limit > 0
        else DEFAULT_INSTRUCTION_LIMIT
    )
    raw_fallbacks = config.get("project_doc_fallback_filenames", [])
    fallbacks = (
        tuple(
            name
            for name in raw_fallbacks
            if isinstance(name, str)
            and name
            and "/" not in name
            and "\\" not in name
        )
        if isinstance(raw_fallbacks, list)
        else ()
    )
    report = instruction_report(root, cwd, limit, fallbacks)
    global_selected = next(
        (
            str(path)
            for path in (
                codex_home / "AGENTS.override.md",
                codex_home / "AGENTS.md",
            )
            if path.is_file() and path.stat().st_size > 0
        ),
        None,
    )
    report.update(
        {
            "global_selected": global_selected,
            "config": str(config_path),
            "fallback_names": list(fallbacks),
        }
    )
    return report


def project_files(root: Path, filename: str):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in IGNORED_DISCOVERY_DIRS
        ]
        if filename in filenames:
            yield Path(directory) / filename


def package_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in project_files(root, "package.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for field in ("dependencies", "devDependencies", "peerDependencies"):
            values = payload.get(field)
            if isinstance(values, dict):
                names.update(str(name).casefold() for name in values)
    return names


def composer_package_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in project_files(root, "composer.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for field in ("require", "require-dev"):
            values = payload.get(field)
            if isinstance(values, dict):
                names.update(str(name).casefold() for name in values)
    return names


def project_profiles(root: Path) -> tuple[str, list[str]]:
    meaningful = any((root / marker).exists() for marker in PROJECT_MARKERS) or any(
        (root / name).exists()
        for name in ("src", "app", "apps", "packages", "services", "backend", "server")
    )
    project_kind = "existing" if meaningful else "greenfield"
    packages = package_names(root)
    composer_packages = composer_package_names(root)
    pyproject_text = " ".join(
        path.read_text(encoding="utf-8", errors="replace").casefold()
        for path in project_files(root, "pyproject.toml")
    )
    frontend = bool(packages.intersection(FRONTEND_PACKAGES)) or any(
        (root / name).exists() for name in ("frontend", "web")
    )
    backend = bool(packages.intersection(BACKEND_PACKAGES)) or any(
        marker in pyproject_text for marker in BACKEND_PYTHON_MARKERS
    ) or bool(composer_packages.intersection(BACKEND_COMPOSER_PACKAGES)) or any(
        (root / name).exists() for name in ("backend", "server")
    )

    profiles = ["project-intake", "reuse-or-build", "architecture-selection"]
    if project_kind == "greenfield":
        profiles.append("greenfield-scaffolding")
    if frontend:
        profiles.append("frontend-engineering")
    if backend:
        profiles.append("backend-engineering")
    profiles.extend(("modularity-budgets", "runtime-delivery"))
    return project_kind, profiles


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".tmp",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2))
        stream.write("\n")
        temp_path = Path(stream.name)
    temp_path.replace(path)


def bounded_strings(values: list[str], *, limit: int) -> list[str]:
    return [item.strip()[:500] for item in values if item.strip()][:limit]


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def document_fingerprints(
    root: Path, manifest: dict[str, object]
) -> dict[str, dict[str, str | None]]:
    documents = manifest.get("documents")
    if not isinstance(documents, dict):
        return {}
    result: dict[str, dict[str, str | None]] = {}
    for purpose, value in documents.items():
        if not isinstance(purpose, str) or not isinstance(value, str) or not value:
            continue
        path = (root / value).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            continue
        result[purpose] = {"path": value, "sha256": file_sha256(path)}
    return result


def has_failed_verification(entries: list[str]) -> bool:
    for value in entries:
        lowered = value.casefold()
        if any(token in lowered for token in VERIFY_STATUS_FAILED_KEYWORDS):
            return True
    return False


def _normalize_evidence_entries(entries: list[str]) -> list[dict[str, str]]:
    """Parse `name=status` or `name: status` evidence lines."""
    import re

    parsed: list[dict[str, str]] = []
    for raw in entries:
        text = raw.strip()
        if not text:
            continue
        lowered = text.casefold()
        # Soft completion words alone are never evidence.
        if lowered in SOFT_DONE_RE:
            raise ValueError(
                "checkpoint refused: soft done word is not evidence; "
                "use name=passed|not-run|blocked|configured-not-verified"
            )
        match = re.match(
            r"^(?P<name>[^=:]+)[=:]\s*(?P<status>[A-Za-z0-9_-]+)\s*(?P<rest>.*)$",
            text,
        )
        if not match:
            raise ValueError(
                "checkpoint refused: evidence must look like "
                "'unittest=passed' or 'install=configured-not-verified'"
            )
        name = match.group("name").strip()[:120]
        if name.casefold() in SOFT_DONE_RE:
            raise ValueError(
                "checkpoint refused: soft done word is not an evidence name; "
                "use a real gate like 'unittest=passed'"
            )
        status = match.group("status").casefold().replace("_", "-")
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"unsupported evidence status: {status}")
        if status in {"failed"}:
            raise ValueError("checkpoint refused: verification contains failed status")
        parsed.append(
            {
                "name": name,
                "status": status,
                "detail": match.group("rest").strip()[:200],
            }
        )
    if not parsed:
        raise ValueError("verification evidence is required for checkpoint")
    if not any(item["status"] == "passed" for item in parsed):
        # Allow checkpoint when only blocked/not-run if explicitly present,
        # but require at least one non-soft structured line (already true).
        # Still refuse if every line is soft-adjacent without passed when tier expects work.
        pass
    return parsed


def hook_safety_report(root: Path) -> dict[str, object]:
    hooks_path = root / "hooks" / "hooks.json"
    hook_script = root / "scripts" / "pala_hook.py"
    state_file = root / ".codex" / "pala-workflow.json"
    reasons: list[str] = []
    if not hooks_path.is_file():
        reasons.append("hooks.json missing")
    else:
        try:
            hook_payload = json.loads(hooks_path.read_text(encoding="utf-8"))
            if not isinstance(hook_payload, dict):
                reasons.append("hooks.json is not a JSON object")
            elif "hooks" not in hook_payload:
                reasons.append("hooks.json is missing the hooks map")
        except (OSError, json.JSONDecodeError):
            reasons.append("hooks.json cannot be parsed")

    if not hook_script.is_file():
        reasons.append("pala_hook.py is missing")
    elif "github.com" in hook_script.read_text(encoding="utf-8").casefold():
        reasons.append("hook script uses restricted external references")

    if not state_file.is_file():
        reasons.append("hook state file is missing")

    if not reasons:
        return {
            "status": "passed",
            "reasons": [],
            "ui_trust": "configured-not-verified",
            "recommendation": "run /hooks to review hook policy when you change safety boundaries",
        }
    return {
        "status": "blocked",
        "reasons": reasons,
        "ui_trust": "configured-not-verified",
        "recommendation": "run /hooks to inspect and repair hook safety",
    }


def doctor_report(
    root: Path, manifest: dict[str, object] | None = None, session: str | None = None
) -> dict[str, object]:
    python_info = {
        "executable": os.environ.get("PYTHON", sys.executable),
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    git_root = run_git(root, "rev-parse", "--show-toplevel")
    plugin_root = root.resolve()
    status = {
        "plugin": {
            "root": str(plugin_root),
            "manifest": str(plugin_root / ".codex-plugin" / "plugin.json"),
            "hooks": str(plugin_root / "hooks" / "hooks.json"),
            "manifest_present": (plugin_root / ".codex-plugin" / "plugin.json").is_file(),
            "hooks_present": (plugin_root / "hooks" / "hooks.json").is_file(),
        },
        "python": python_info,
        "git": {
            "installed": git_root is not None,
            "root": git_root,
            "status_command": run_git(root, "status", "--short", "--branch"),
        },
        "project_registration": {
            "registered": False,
            "document_mapping": None,
            "error": None,
        },
        "hook_discovery": {
            "workflow_state_exists": (root / WORKFLOW).is_file(),
            "workflow_state_preview": relative(
                root, root / WORKFLOW
            )
            if (root / WORKFLOW).is_file()
            else None,
        },
        "hook_safety": hook_safety_report(root),
    }

    if manifest is None:
        try:
            manifest = load_manifest(root)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            status["project_registration"]["error"] = str(error)
        else:
            status["project_registration"]["registered"] = True
            status["project_registration"]["document_mapping"] = manifest.get("documents")

    workflow = None
    if status["project_registration"]["registered"]:
        try:
            workflow = load_workflow(root)
        except (OSError, ValueError, json.JSONDecodeError):
            workflow = None
        status["hook_discovery"]["active_ticket"] = (
            workflow.get("active_ticket") if isinstance(workflow, dict) else None
        )
        reconciliation = (
            reconciliation_report(root, manifest, workflow)
            if isinstance(workflow, dict)
            else None
        )
        status["hook_discovery"]["needs_reconcile"] = (
            reconciliation["needed"] if reconciliation is not None else None
        )
        status["hook_discovery"]["dirty"] = (
            bool(workflow and workflow.get("dirty")) if workflow else None
        )
    if session is not None:
        from pala_store import WorkflowStore

        owned = WorkflowStore(root).active_for_session(session)
        status["session_ticket"] = (
            {
                "ticket": owned.get("ticket"),
                "lifecycle": owned.get("lifecycle"),
                "dirty": bool(owned.get("dirty")),
            }
            if owned is not None
            else None
        )

    status["healthy"] = (
        status["plugin"]["manifest_present"]
        and status["plugin"]["hooks_present"]
        and status["git"]["installed"]
        and status["project_registration"]["registered"]
        and status["hook_safety"]["status"] == "passed"
    )

    try:
        from pala_shared_memory import doctor_store_block

        status["shared_store"] = doctor_store_block()
    except Exception as error:  # noqa: BLE001 â€” doctor JSON stays useful
        status["shared_store"] = {"error": str(error), "cloud_sync": False}

    return status


def discover(root: Path) -> dict[str, object]:
    project_kind, profiles = project_profiles(root)
    documents: dict[str, str | None] = {}
    for purpose, names in CANDIDATES.items():
        match = next((root / name for name in names if (root / name).exists()), None)
        documents[purpose] = relative(root, match) if match else None
    return {
        "root": str(root),
        "manifest": str(root / MANIFEST),
        "registered": (root / MANIFEST).is_file(),
        "project_kind": project_kind,
        "profiles": profiles,
        "documents": documents,
        "fallbacks": {
            "project": "docs/codex/PROJECT.md",
            "plan": "docs/codex/PLAN.md",
            "status": "reports/CURRENT_STATUS.md",
            "progress": "PROGRESS.md",
            "tooling": "TOOLING_DECISIONS.md",
            "debugging": "DEBUGGING.md",
            "decisions": "docs/codex/DECISIONS.md",
            "open_source": "docs/codex/OPEN_SOURCE.md",
            "demo": "reports/OWNER_DEMO.md",
        },
    }


def normalize_document(root: Path, value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        return relative(root, resolved)
    except ValueError as exc:
        raise ValueError(f"document must remain inside project root: {value}") from exc


def register(args: argparse.Namespace, root: Path) -> int:
    from pala_memory import ensure_memory_stubs

    discovery = discover(root)
    found = discovery["documents"]
    documents = {
        "instructions": normalize_document(root, args.instructions or found["instructions"]),
        "project": normalize_document(root, args.project or found["project"]),
        "plan": normalize_document(root, args.plan or found["plan"]),
        "status": normalize_document(root, args.status or found["status"]),
        "progress": normalize_document(
            root, getattr(args, "progress", None) or found.get("progress")
        ),
        "tooling": normalize_document(
            root, getattr(args, "tooling", None) or found.get("tooling")
        ),
        "debugging": normalize_document(
            root, getattr(args, "debugging", None) or found.get("debugging")
        ),
        "decisions": normalize_document(root, args.decisions or found["decisions"]),
        "open_source": normalize_document(root, args.open_source or found["open_source"]),
        "demo": normalize_document(
            root, getattr(args, "demo", None) or found["demo"]
        ),
    }
    # Create optional memory-contract stubs when missing (status still required).
    stubbed = ensure_memory_stubs(
        root,
        {k: (v if isinstance(v, str) else None) for k, v in documents.items()},
    )
    for key in ("status", "progress", "tooling", "debugging"):
        if not documents.get(key) and stubbed.get(key):
            documents[key] = stubbed[key]
    missing = [name for name in REQUIRED if not documents[name]]
    if missing:
        print(
            "missing required document mappings: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2
    manifest_path = root / MANIFEST
    payload = {
        "schema_version": SCHEMA_VERSION,
        "managed_by": "pala-project-finisher",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "project_kind": discovery["project_kind"],
        "profiles": discovery["profiles"],
        "documents": documents,
        "memory_contract_version": 1,
    }
    write_json(manifest_path, payload)
    try:
        from pala_catalog import upsert_project

        upsert_project(root, phase="registered", next_action="begin first ticket")
    except (OSError, ValueError, TypeError):
        pass
    _record_store_event(root, "register", detail="project registered")
    print(str(manifest_path))
    return 0
