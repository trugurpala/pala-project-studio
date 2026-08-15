"""Owner-readable product delivery projection; never a canonical authority."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from pala_models import VERIFICATION_STATUSES
from pala_privacy import private_data_reason


@dataclass(frozen=True)
class LiveVerification:
    deployment_status: str
    live_status: str
    evidence_refs: list[str]

    def __post_init__(self) -> None:
        if self.deployment_status not in {"not-run", "DEPLOYED"}:
            raise ValueError("invalid deployment status")
        if self.live_status not in VERIFICATION_STATUSES:
            raise ValueError("invalid live verification status")
        if self.live_status == "passed" and (
            self.deployment_status != "DEPLOYED" or not self.evidence_refs
        ):
            raise ValueError("live verification requires deployment and evidence")

    def with_result(self, status: str, evidence_refs: list[str]) -> LiveVerification:
        return LiveVerification(self.deployment_status, status, evidence_refs)

    def is_live_verified(self) -> bool:
        return (
            self.deployment_status == "DEPLOYED"
            and self.live_status == "passed"
            and bool(self.evidence_refs)
        )


def render_owner_cockpit(snapshot: dict[str, object], *, fragment: bool = False) -> str:
    required = (
        "project",
        "state",
        "acceptance_verified",
        "acceptance_total",
        "quality",
        "environment",
        "delivery",
        "live_verification",
        "blocker",
        "next_action",
        "owner_request",
    )
    if any(name not in snapshot for name in required):
        raise ValueError("owner cockpit snapshot is incomplete")
    verified = snapshot["acceptance_verified"]
    total = snapshot["acceptance_total"]
    if (
        not isinstance(verified, int)
        or not isinstance(total, int)
        or verified < 0
        or total < 1
        or verified > total
    ):
        raise ValueError("invalid acceptance counts")
    labels = (
        ("Project", snapshot["project"]),
        ("State", snapshot["state"]),
        ("Acceptance", f"{verified}/{total}"),
        ("Quality", snapshot["quality"]),
        ("Environment", snapshot["environment"]),
        ("Delivery", snapshot["delivery"]),
        ("Live verification", snapshot["live_verification"]),
        ("Blocker", snapshot["blocker"]),
        ("Next action", snapshot["next_action"]),
        ("Owner request", snapshot["owner_request"]),
    )
    cards = "".join(
        f'<section class="signal"><h2>{escape(label)}</h2><p>{escape(str(value))}</p></section>'
        for label, value in labels
    )
    version = _control_value(snapshot, "product_version", "unknown")
    section = (
        '<section class="pala-product-cockpit" aria-labelledby="pala-product-cockpit-title">'
        f'<h2 id="pala-product-cockpit-title">Pala {version} Owner Cockpit</h2>'
        f'<div class="grid">{cards}</div></section>'
    )
    control_center = render_control_center(snapshot)
    if fragment:
        return section + control_center
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Pala Control Center</title></head><body><main>"
        f"{section}{control_center}</main></body></html>"
    )


def _control_value(snapshot: dict[str, object], key: str, fallback: str = "Not assessed") -> str:
    value = snapshot.get(key)
    text = str(value if value is not None else fallback)
    if private_data_reason(text):
        text = "[private value hidden]"
    return escape(text)


def _read_model_body(snapshot: dict[str, object], key: str) -> str:
    model = snapshot.get(key)
    model = model if isinstance(model, dict) else {}
    if model.get("can_complete") is not False:
        return (
            '<p class="cc-empty" data-read-model-status="blocked">'
            "READ_MODEL_NOT_READ_ONLY</p>"
        )
    items = model.get("items")
    items = items if isinstance(items, list) else []
    findings = model.get("findings")
    if not isinstance(findings, list):
        findings = model.get("finding_codes")
    findings = findings if isinstance(findings, list) else []
    rows: list[str] = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        cells: list[str] = []
        for name, value in list(item.items())[:6]:
            text = str(value)
            if private_data_reason(text):
                text = "[private value hidden]"
            cells.append(f"<dt>{escape(str(name))}</dt><dd>{escape(text)}</dd>")
        rows.append(f'<article class="cc-read-item"><dl>{"".join(cells)}</dl></article>')
    if not rows:
        rows.append('<p class="cc-empty">No current records.</p>')
    safe_findings: list[str] = []
    for value in findings[:5]:
        text = str(value)
        if private_data_reason(text):
            text = "[private value hidden]"
        safe_findings.append(text)
    finding_html = "".join(f"<li>{escape(value)}</li>" for value in safe_findings)
    if finding_html:
        rows.append(f'<ul class="cc-findings">{finding_html}</ul>')
    return "".join(rows)


def render_control_center(snapshot: dict[str, object]) -> str:
    """Render the owner-first static Control Center projection.

    The projection is intentionally read-only. Canonical commands, evidence,
    and identifiers are available only under Advanced and are escaped.
    """
    project = _control_value(snapshot, "project", "Unnamed project")
    state = _control_value(snapshot, "state")
    quality = _control_value(snapshot, "quality")
    blocker = _control_value(snapshot, "blocker", "No known problem")
    next_action = _control_value(snapshot, "next_action", "Nothing")
    owner_request = _control_value(snapshot, "owner_request", "Nothing")
    owner_request_raw = str(snapshot.get("owner_request") or "Nothing").strip().casefold()
    no_request = owner_request_raw in {
        "nothing",
        "hicbir sey",
        "hiçbir şey",
        "no owner action is required before local verification.",
    }
    owner_request_text = (
        "Sizden gereken:\nHicbir sey." if no_request else f"Sizden gereken:\n{owner_request}"
    )
    version = _control_value(snapshot, "product_version", "unknown")
    milestones = snapshot.get("milestones")
    milestones = milestones if isinstance(milestones, dict) else {}
    milestone_id = sorted((str(key) for key in milestones), reverse=True)
    current_milestone = milestone_id[0] if milestone_id else ""
    milestone = milestones.get(current_milestone)
    milestone = milestone if isinstance(milestone, dict) else {}
    milestone_line = (
        f"<p>Milestone {escape(current_milestone)}: "
        f"<strong>{escape(str(milestone.get('task_status') or 'not-run'))}</strong> "
        f"({escape(str(milestone.get('workflow_lifecycle') or 'unknown'))}).</p>"
        if milestone
        else ""
    )
    release_state = str(snapshot.get("release_status") or "pending").casefold()
    if release_state in {"published", "public released", "passed"}:
        release_message = "GitHub publication is published and remote-verified."
    elif release_state in {"blocked", "public release blocked"}:
        release_message = "Publication stopped safely. Review the known problem above."
    elif release_state in {"needs_decision", "public release needs_decision"}:
        release_message = "GitHub publication needs your approval."
    else:
        release_message = "GitHub publication is ready for the owner's approval."
    sections = (
        (
            "home",
            "Home",
            f'<div class="cc-owner-grid"><article><h4>Neredeyiz?</h4><p><strong>{project}</strong>: {state}</p></article><article><h4>Pala ne yapiyor?</h4><p>{next_action}</p></article><article><h4>Problem var mi?</h4><p>{blocker}</p></article><article><h4>Sizden ne gerekiyor?</h4><pre>{owner_request_text}</pre></article></div>{milestone_line}<p>Quality: {quality}.</p>',
        ),
        ("projects", "Projects", f"<p>Project: {project}</p>"),
        ("current-work", "Current Work", f"<p>Now: {next_action}</p>"),
        ("known-problems", "Known Problems", f"<p>{blocker}</p>"),
        ("quality", "Quality", f"<p>Acceptance and quality: {quality}</p>"),
        (
            "policies",
            "Policies",
            "<p>Policy decisions are evidence-backed and owner-authorized.</p>",
        ),
        ("release", "Release", f"<p>{release_message}</p><p>Real deployment: not-run.</p>"),
        ("queue", "Queue", _read_model_body(snapshot, "queue")),
        ("receipts", "Receipts", _read_model_body(snapshot, "context_receipts")),
        ("history", "History", _read_model_body(snapshot, "project_history")),
        (
            "failure-intelligence",
            "Failure Intelligence",
            _read_model_body(snapshot, "failure_intelligence"),
        ),
        ("profiles", "Profiles", _read_model_body(snapshot, "profiles")),
        (
            "host-capabilities",
            "Host Capabilities",
            _read_model_body(snapshot, "host_capabilities"),
        ),
        ("host-processes", "Host & Processes", _read_model_body(snapshot, "host_processes")),
        ("security-release", "Security & Release", _read_model_body(snapshot, "security_release")),
    )
    links = "".join(f'<a href="#cc-{anchor}">{label}</a>' for anchor, label, _ in sections)
    panels = "".join(
        f'<section id="cc-{anchor}" class="cc-panel" aria-labelledby="cc-{anchor}-title">'
        f'<h3 id="cc-{anchor}-title">{label}</h3>{body}</section>'
        for anchor, label, body in sections
    )
    advanced = (
        '<details id="cc-advanced" class="cc-advanced"><summary>Advanced technical evidence</summary>'
        f"<p>Task state: {_control_value(snapshot, 'state')}</p>"
        f"<p>Evidence references: {_control_value(snapshot, 'evidence_refs', 'None')}</p>"
        f"<p>Providers: {_control_value(snapshot, 'providers', 'not-run')}</p>"
        f"<p>Exact versions: {_control_value(snapshot, 'provider_versions', 'not-run')}</p>"
        f"<p>Provenance/freshness: {_control_value(snapshot, 'provenance_freshness', 'not-run')}</p>"
        f"<p>Telemetry/daemon: {_control_value(snapshot, 'telemetry_daemon', 'disabled/not-run')}</p>"
        "</details>"
    )
    return (
        '<section class="pala-control-center" aria-labelledby="cc-title" data-can-complete="false">'
        '<h2 id="cc-title" aria-label="Pala Control Center">PALA CONTROL CENTER</h2>'
        f'<p class="pala-version">Pala {version}</p>'
        f'<nav aria-label="Control Center sections" class="cc-nav">{links}</nav>'
        f"{panels}{advanced}"
        "<style>"
        ".pala-control-center{font-family:system-ui,sans-serif;max-width:100%;overflow-x:hidden;}"
        ".cc-nav{display:flex;flex-wrap:wrap;gap:.5rem;margin:1rem 0;}"
        ".cc-nav a{padding:.55rem .7rem;border:1px solid #9aa8bb;border-radius:.4rem;}"
        ".cc-nav a:focus-visible,.cc-advanced summary:focus-visible{outline:3px solid #2f6fed;outline-offset:2px;}"
        ".cc-panel{padding:1rem;margin:.75rem 0;border:1px solid #d8e0eb;border-radius:.6rem;}"
        ".cc-panel p{line-height:1.5;overflow-wrap:anywhere;}"
        ".cc-owner-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:.75rem;}"
        ".cc-owner-grid article{border:1px solid #d8e0eb;border-radius:.5rem;padding:.75rem;}"
        ".cc-read-item{border-top:1px solid #d8e0eb;padding:.5rem 0;}.cc-read-item dl{display:grid;grid-template-columns:minmax(8rem,1fr) 2fr;gap:.25rem .75rem;margin:0;}.cc-read-item dt{font-weight:700}.cc-read-item dd{margin:0;overflow-wrap:anywhere}"
        ".cc-owner-grid pre{white-space:pre-wrap;font:inherit;}"
        ".cc-advanced{margin-top:1rem;padding:1rem;background:#f4f7fb;}"
        "@media (max-width:600px){.cc-nav a{min-height:2.75rem;box-sizing:border-box;}.cc-panel{margin-inline:0;}}"
        "@media (prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important;}}"
        "</style></section>"
    )
