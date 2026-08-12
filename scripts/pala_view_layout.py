#!/usr/bin/env python3
"""Document-layout owner for Pala's static status page."""

from __future__ import annotations

from typing import Any

from pala_view_sections import (
    SECTION_NAV as _SECTION_NAV,
    brain_line as _brain_line,
    decision_strip as _decision_strip,
    delivery_card as _delivery_card,
    escape as _e,
    is_temporary_project_name as _is_temporary_project_name,
    now_line as _now_line,
    private_detail as _private_detail,
    progress_block as _progress_block,
    section_features as _section_features,
    section_hooks as _section_hooks,
    section_install as _section_install,
    section_memory as _section_memory,
    section_overview as _section_overview,
    section_quality as _section_quality,
    section_tickets as _section_tickets,
)
from pala_view_styles import render_css


def _freshness_badge(level: str) -> str:
    labels = {"fresh": "taze", "aging": "eskiyor", "stale": "bayat"}
    return f'<span class="badge {level}">{labels.get(level, level)}</span>'


def _update_banner(
    update: dict[str, object] | None, cache_checked_at: str | None = None
) -> str:
    if not update:
        return '<div class="warnline">Pala guncellik: bilinmiyor</div>'
    status = str(update.get("status") or "unavailable")
    installed = _e(update.get("installed_version") or "?")
    available = _e(update.get("available_version") or "")
    url = update.get("url")
    checked = ""
    if isinstance(cache_checked_at, str) and cache_checked_at:
        checked = f' <span class="muted-inline">(son bakis: {_e(cache_checked_at)})</span>'
    if status == "update-available":
        link = f' <a href="{_e(url)}">indir</a>' if isinstance(url, str) and url.startswith("https://") else ""
        return f'<div class="alert">Guncelleme var: {installed} &rarr; {available}{link}{checked}</div>'
    if status == "current":
        return f'<div class="okline">Pala guncel ({installed}){checked}</div>'
    return f'<div class="warnline">Pala guncellik: cevrimdisi / bilinmiyor{checked}</div>'


def _project_detail_html(item: dict[str, object], freshness_fn: Any) -> str:
    tech = item.get("tech")
    tech_text = ", ".join(tech) if isinstance(tech, list) else ""
    blockers = item.get("blockers")
    blocker_list = blockers if isinstance(blockers, list) else []
    level = freshness_fn(item.get("updated_at"))
    github = item.get("github")
    github_html = (
        '<details class="private-detail"><summary>GitHub ba?lant?s?n? g?ster</summary>'
        f'<a href="{_e(github)}">{_e(github)}</a></details>'
        if isinstance(github, str) and github.startswith("https://") else ""
    )
    blocker_html = ""
    if blocker_list:
        items = "".join(f"<li>{_e(b)}</li>" for b in blocker_list[:8])
        blocker_html = f"<p>Blokajlar:</p><ul>{items}</ul>"
    return (
        f'<div class="grid"><div class="card"><div class="k">Faz</div><div class="v">{_e(item.get("phase") or "belirsiz")}</div></div>'
        f'<div class="card"><div class="k">Sonraki is</div><div class="v">{_e(item.get("next_action") or "yok")}</div></div>'
        f'<div class="card"><div class="k">Kalite</div><div class="v">{_e(item.get("quality_result") or "yok")}</div></div>'
        f'<div class="card"><div class="k">Tazelik</div><div class="v">{_freshness_badge(level)}</div></div></div>'
        f'{_private_detail("Yerel yolu g?ster", item.get("path"))}'
        f'<p>Teknoloji: {_e(tech_text or "?")}</p>{github_html}{blocker_html}'
    )


def _theme_script() -> str:
    """Inline prefs only: theme + display toggles via localStorage (no network)."""
    return """
<script>
(function () {
  var KEYS = { theme: "pala.ui.theme", experts: "pala.ui.showExperts", softFail: "pala.ui.softFailClosed", qualityTier: "pala.ui.showQualityTier" };
  function read(key, fallback) { try { var v = localStorage.getItem(key); return v == null ? fallback : v; } catch (e) { return fallback; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }
  function apply() {
    var root = document.documentElement, theme = read(KEYS.theme, "dark");
    if (theme !== "light" && theme !== "dark") theme = "dark";
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-show-experts", read(KEYS.experts, "1") === "0" ? "0" : "1");
    root.setAttribute("data-soft-fail-closed", read(KEYS.softFail, "0") === "1" ? "1" : "0");
    root.setAttribute("data-show-quality-tier", read(KEYS.qualityTier, "1") === "0" ? "0" : "1");
    var themeBtn = document.getElementById("pala-theme-toggle");
    if (themeBtn) { themeBtn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false"); themeBtn.textContent = theme === "dark" ? "Acik tema" : "Koyu tema"; }
    var map = [["pref-show-experts", KEYS.experts, "1"], ["pref-soft-fail-closed", KEYS.softFail, "0"], ["pref-show-quality-tier", KEYS.qualityTier, "1"]];
    for (var i = 0; i < map.length; i++) { var el = document.getElementById(map[i][0]); if (el) el.checked = read(map[i][1], map[i][2]) === "1"; }
  }
  function bind() {
    var themeBtn = document.getElementById("pala-theme-toggle");
    if (themeBtn) themeBtn.addEventListener("click", function () { var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light"; write(KEYS.theme, next); apply(); });
    function wire(id, key) { var el = document.getElementById(id); if (el) el.addEventListener("change", function () { write(key, el.checked ? "1" : "0"); apply(); }); }
    wire("pref-show-experts", KEYS.experts); wire("pref-soft-fail-closed", KEYS.softFail); wire("pref-show-quality-tier", KEYS.qualityTier);
  }
  apply(); if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind); else bind();
})();
</script>
"""


def _mapping(value: object, default: dict[str, object] | None = None) -> dict[str, object]:
    return value if isinstance(value, dict) else (default or {})


def _context(model: dict[str, object]) -> dict[str, object]:
    freshness = model.get("freshness_level")
    return {
        "root_name": str(model.get("root_name") or "project"), "root_path": str(model.get("root_path") or ""),
        "stamp": str(model.get("stamp") or ""), "coherence": _mapping(model.get("coherence")),
        "git": _mapping(model.get("git")), "read_order": model.get("read_order") if isinstance(model.get("read_order"), list) else [],
        "progress": _mapping(model.get("progress"), {"ready": 0, "total": 7, "missing": []}),
        "projects": model.get("projects") if isinstance(model.get("projects"), list) else [],
        "events": model.get("events") if isinstance(model.get("events"), list) else [],
        "provisions": model.get("provisions") if isinstance(model.get("provisions"), list) else [],
        "update": model.get("update") if isinstance(model.get("update"), dict) else None,
        "update_checked_at": model.get("update_checked_at"), "next_action": model.get("next_action"),
        "brain": model.get("debugging_brain"), "last_gate": model.get("last_gate"),
        "freshness_level": freshness if isinstance(freshness, str) and freshness else "stale",
        "quality": model.get("quality"), "delivery": model.get("delivery"),
        "store_path": model.get("store_path") or "", "verification_tier": model.get("verification_tier") or "not-run",
        "owner_cockpit_html": model.get("owner_cockpit_html") or "",
    }


def _fixed_panels(context: dict[str, object]) -> list[str]:
    coherence = _mapping(context["coherence"])
    quality = context["quality"]
    delivery = context["delivery"]
    mismatch = bool(coherence.get("mismatch"))
    mismatch_banner = f'<div class="alert">Ticket uyumsuzlugu: {_e(coherence.get("note"))}</div>' if mismatch else '<div class="okline">Ticket uyumu: tamam</div>'
    decision = _decision_strip(next_action=context["next_action"], coherence=coherence, brain=context["brain"], last_gate=context["last_gate"], freshness_level=context["freshness_level"], quality=quality)
    delivery_html = _delivery_card(delivery, quality)
    quality_delivery = _delivery_card(delivery, quality, element_id="pala-delivery-quality")
    return [
        _section_overview(root_name=str(context["root_name"]), decision=decision, delivery=delivery_html, now=_now_line(context["next_action"], coherence.get("active")), brain=_brain_line(context["brain"]), mismatch_banner=mismatch_banner, progress=_progress_block(_mapping(context["progress"])), coherence=coherence, git=_mapping(context["git"]), next_action=context["next_action"], owner_cockpit=str(context["owner_cockpit_html"])),
        _section_install(), _section_hooks(), _section_quality(quality, context["verification_tier"], quality_delivery),
        _section_memory(context["store_path"], context["events"], context["provisions"]),
        _section_tickets(coherence=coherence, next_action=context["next_action"], read_order=context["read_order"]), _section_features(),
    ]


def _navigation(context: dict[str, object], panels: list[str], freshness_fn: Any) -> dict[str, object]:
    radios = ['<input type="radio" name="pala-nav" id="nav-overview" aria-controls="panel-overview" checked>']
    labels = [f'<label for="nav-{sid}" class="nav-item"><span class="nav-name">{_e(label)}</span></label>' for sid, label in _SECTION_NAV]
    ordered = sorted([item for item in context["projects"] if isinstance(item, dict) and not _is_temporary_project_name(item.get("name"))], key=lambda item: str(item.get("updated_at", "")), reverse=True)
    project_labels: list[str] = []
    for index, item in enumerate(ordered):
        pid = f"nav-project-{index}"
        radios.append(f'<input type="radio" name="pala-nav" id="{pid}" aria-controls="panel-project-{index}">')
        project_labels.append(f'<label for="{pid}" class="nav-item"><span class="nav-name">{_e(item.get("name"))}</span>{_freshness_badge(freshness_fn(item.get("updated_at")))}</label>')
        panels.append(f'<section id="panel-project-{index}" class="panel"><h2>{_e(item.get("name"))}</h2>{_project_detail_html(item, freshness_fn)}</section>')
    return {"radios": radios, "labels": labels, "panels": panels, "ordered": ordered, "project_nav": "".join(project_labels) if project_labels else '<p class="muted-inline">Kayit yok</p>'}


def _navigation_css(ordered: list[dict[str, object]]) -> tuple[str, str, str]:
    rules = [f"#nav-{sid}:checked ~ .shell #panel-{sid} {{ display: block; }}" for sid, _ in _SECTION_NAV]
    rules.extend(f"#nav-project-{index}:checked ~ .shell #panel-project-{index} {{ display: block; }}" for index in range(len(ordered)))
    checked = [f'#nav-{sid}:checked ~ .shell label[for="nav-{sid}"]' for sid, _ in _SECTION_NAV]
    checked.extend(f'#nav-project-{index}:checked ~ .shell label[for="nav-project-{index}"]' for index in range(len(ordered)))
    focused = [f'#nav-{sid}:focus-visible ~ .shell label[for="nav-{sid}"]' for sid, _ in _SECTION_NAV]
    focused.extend(f'#nav-project-{index}:focus-visible ~ .shell label[for="nav-project-{index}"]' for index in range(len(ordered)))
    return ",\n  ".join(checked) + " { background: var(--nav-active); border-color: var(--line); }", ",\n  ".join(focused) + " { outline: 3px solid var(--focus); outline-offset: 2px; }", "\n  ".join(rules)


def _catalog_rows(ordered: list[dict[str, object]], freshness_fn: Any) -> str:
    if not ordered:
        return '<tr><td colspan="6" class="muted">Henuz kayitli proje yok. Bir projede register calistir.</td></tr>'
    rows: list[str] = []
    for item in ordered:
        tech = item.get("tech")
        tech_text = ", ".join(tech) if isinstance(tech, list) else ""
        rows.append("<tr>" + f'<td>{_e(item.get("name"))}</td><td>{_e(item.get("phase") or "belirsiz")}</td><td>{_e(item.get("next_action") or "yok")}</td><td>{_e(item.get("quality_result") or "yok")}</td><td>{_freshness_badge(freshness_fn(item.get("updated_at")))}</td><td class="mono">{_e(tech_text or "?")}</td></tr>')
    return "".join(rows)


def _document(context: dict[str, object], navigation: dict[str, object], style: str, catalog: str) -> str:
    update_checked = context["update_checked_at"] if isinstance(context["update_checked_at"], str) else None
    return f"""<!doctype html>
<html lang="tr" data-theme="dark" data-show-experts="1" data-soft-fail-closed="0" data-show-quality-tier="1">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Pala kontrol - {_e(context["root_name"])}</title><style>{style}</style></head>
<body>
  <a class="skip-link" href="#pala-main">??eri?e ge?</a>{"".join(navigation["radios"])}
  <div class="shell"><nav class="sidebar" aria-label="Pala kontrol menusu" id="pala-admin-nav">
    <div class="brand-block"><p class="brand-name">Pala</p><p class="brand-tag">kontrol merkezi</p></div><p class="nav-title">Bolumler</p>{"".join(navigation["labels"])}<p class="nav-title">Projeler</p>{navigation["project_nav"]}
  </nav><main id="pala-main" class="main"><div class="topbar"><div><h1 class="title">Pala kontrol ? {_e(context["root_name"])}</h1><div class="sub">Yerel yol gizli &middot; {context["stamp"]}</div>{_private_detail("Yerel proje yolunu g?ster", context["root_path"])}</div><button type="button" class="theme-toggle" id="pala-theme-toggle" aria-pressed="true">Acik tema</button></div>
  {_update_banner(context["update"], update_checked)}{"".join(navigation["panels"])}
  <h2>Proje katalogu</h2><div class="catalog-wrap"><table><thead><tr><th>Proje</th><th>Faz</th><th>Sonraki is</th><th>Kalite</th><th>Tazelik</th><th>Teknoloji</th></tr></thead><tbody>{catalog}</tbody></table></div>
  <footer>Sohbet gecmisine guvenme; yukaridaki dosyalari sirayla oku. Bu sayfa yerel kayitlardan uretildi; guncellik 24 saat onbelleklidir (hook icinde ag yok). Tema/tercihler localStorage.</footer></main></div>{_theme_script()}
</body></html>
"""


def render(model: dict[str, object], *, freshness_fn: Any) -> str:
    """Render a status / control-center model into a single static HTML document."""
    context = _context(model)
    navigation = _navigation(context, _fixed_panels(context), freshness_fn)
    checked_css, focus_css, show_css = _navigation_css(navigation["ordered"])
    style = render_css(checked_css, focus_css, show_css)
    return _document(context, navigation, style, _catalog_rows(navigation["ordered"], freshness_fn))
