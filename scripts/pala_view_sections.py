#!/usr/bin/env python3
"""Escaped, privacy-preserving sections for Pala's static status page.

`pala_view` owns the model-to-page orchestration.  This module owns the
independently testable decision, timeline, and section markup so a change to
one visible responsibility does not require editing the entire renderer.
"""

from __future__ import annotations

import html

SECTION_NAV = (
    ("overview", "Genel Bak\u0131\u015f"),
    ("install", "Kurulum ve Denetim"),
    ("hooks", "Hook g\u00fcveni"),
    ("quality", "Kalite"),
    ("memory", "Haf\u0131za"),
    ("tickets", "\u0130\u015fler ve sonraki ad\u0131m"),
    ("features", "Ayarlar"),
)

_PURPOSE_LABELS = {
    "instructions": "AGENTS / talimat",
    "status": "guncel durum",
    "progress": "ilerleme",
    "plan": "plan",
    "tooling": "arac kararlari",
    "debugging": "debug gunlugu",
    "git": "git durumu",
}

_KIND_LABELS = {
    "register": "kayit",
    "begin": "basla",
    "checkpoint": "checkpoint",
    "debug_attempt": "debug denemesi",
    "provision": "provision",
    "mismatch": "uyumsuzluk",
}


def escape(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def now_text(next_action: object, active_ticket: object = None) -> str:
    ticket = str(active_ticket).strip() if active_ticket else ""
    text = str(next_action).strip() if next_action else ""
    if ticket and text:
        if ticket not in text:
            text = f"{ticket} — {text}"
    elif ticket:
        text = ticket
    elif not text:
        text = "Henüz sonraki iş yok — register veya begin çalıştır."
    return text


def now_line(next_action: object, active_ticket: object = None) -> str:
    text = now_text(next_action, active_ticket)
    return (
        '<div class="nowline" role="status"><span class="now-k">Şimdi:</span> '
        f"<span>{escape(text)}</span></div>"
    )


def private_detail(label: str, value: object) -> str:
    """Keep local paths and URLs out of the default screen-share view."""
    text = str(value or "").strip()
    if not text:
        return ""
    return (
        '<details class="private-detail">'
        f"<summary>{escape(label)}</summary>"
        f'<span class="mono">{escape(text)}</span>'
        "</details>"
    )


def delivery_card(
    delivery: object, quality: object, *, element_id: str = "pala-delivery-decision"
) -> str:
    delivery = delivery if isinstance(delivery, dict) else {}
    quality = quality if isinstance(quality, dict) else {}
    status = str(delivery.get("status") or "not-assessed")
    tone = "ok" if status == "passed" else "alert" if status == "blocked" else "warn"
    label = str(delivery.get("label") or "Henüz değerlendirilmedi")
    detail = str(delivery.get("detail") or "Karar için kalite kanıtı bekleniyor.")
    checks = quality.get("required_checks")
    rows: list[str] = []
    if isinstance(checks, list):
        for item in checks[:12]:
            if not isinstance(item, dict):
                continue
            tone_name = "ok" if item.get("status") == "passed" else "gap"
            rows.append(
                "<li>"
                f'<span class="mono">{escape(item.get("id") or "quality-check")}</span>'
                f' <span class="badge {tone_name}">'
                f'{escape(item.get("status") or "not-run")}</span></li>'
            )
    gate_list = "".join(rows) or "<li>Henüz zorunlu kapı planı yok.</li>"
    action = str(quality.get("next_action") or "").strip()
    action_html = (
        f'<p class="delivery-action"><strong>Tek sonraki eylem:</strong> {escape(action)}</p>'
        if action
        else ""
    )
    return (
        f'<section class="delivery-card tone-{tone}" id="{escape(element_id)}" '
        'role="status" aria-label="Teslim kararı">'
        '<div class="delivery-k">Teslim kararı</div>'
        f'<div class="delivery-v">{escape(label)}</div>'
        f'<p class="delivery-detail">{escape(detail)}</p>'
        f"{action_html}"
        '<details><summary>Zorunlu kalite kapıları</summary>'
        f'<ul class="delivery-gates">{gate_list}</ul></details>'
        "</section>"
    )


def decision_strip(
    *,
    next_action: object,
    coherence: dict[str, object],
    brain: object,
    last_gate: object,
    freshness_level: object,
    quality: object,
) -> str:
    """Top decision strip: five shipping signals from the quality engine."""
    coherence = coherence if isinstance(coherence, dict) else {}
    quality = quality if isinstance(quality, dict) else {}
    risk = quality.get("risk") if isinstance(quality.get("risk"), dict) else {}
    coverage = quality.get("coverage") if isinstance(quality.get("coverage"), dict) else {}
    ticket = str(quality.get("ticket") or coherence.get("active") or "yok")
    risk_level = str(risk.get("level") or "unknown")
    reasons = ", ".join(str(item) for item in list(risk.get("reasons") or [])[:3])
    risk_label = f"{risk_level} — {reasons}" if reasons else risk_level
    quality_status = str(quality.get("status") or "not-run")
    quality_tone = (
        "ok"
        if quality_status == "passed"
        else "alert"
        if quality_status in {"blocked", "failed"}
        else "warn"
    )
    risk_tone = (
        "alert"
        if risk_level == "high"
        else "warn"
        if risk_level in {"medium", "unknown"}
        else "ok"
    )
    coverage_label = (
        f"{int(coverage.get('passed') or 0)}/{int(coverage.get('required') or 0)} passed"
    )
    cells = [
        ("Aktif ticket", ticket[:72], "now"),
        ("Risk seviyesi", risk_label[:72], risk_tone),
        ("Quality coverage", coverage_label, quality_tone),
        (
            "Son eksik gate",
            str(quality.get("last_problem") or "quality ledger not initialized")[:72],
            quality_tone,
        ),
        (
            "Tek sonraki eylem",
            str(quality.get("next_action") or next_action or "yok")[:120],
            "now",
        ),
    ]
    _ = (brain, last_gate, freshness_level)
    parts: list[str] = []
    for key, value, tone in cells:
        parts.append(
            f'<div class="signal tone-{tone}">'
            f'<div class="signal-k">{escape(key)}</div>'
            f'<div class="signal-v">{escape(value)}</div>'
            "</div>"
        )
    return (
        '<div class="decision-strip" role="region" aria-label="Karar sinyalleri">'
        f'{"".join(parts)}</div>'
    )


def brain_line(brain: object) -> str:
    if not isinstance(brain, dict) or not brain.get("ok"):
        detail = ""
        if isinstance(brain, dict) and brain.get("detail"):
            detail = f" ({escape(brain.get('detail'))})"
        return (
            f'<div class="warnline">Hata beyni: okunamadı{detail} — '
            "DEBUGGING.md Format / INC alanlarını kontrol et.</div>"
        )
    open_count = int(brain.get("open") or 0)
    fixed_count = int(brain.get("fixed") or 0)
    total = int(brain.get("total") or 0)
    path = escape(brain.get("path") or "DEBUGGING.md")
    soft_note = (
        '<span class="soft-closed-note muted-inline"> '
        f"(kapalı {fixed_count} — soft-fail kapalı hatırlatma açık)</span>"
    )
    if open_count:
        css_class = "alert"
        note = f"{open_count} açık / {fixed_count} kapalı (toplam {total})"
    else:
        css_class = "okline"
        note = f"açık yok; {fixed_count} kapalı (toplam {total})"
    return (
        f'<div class="{css_class}">Hata beyni: {note} — önce <span class="mono">{path}</span> '
        f"oku.{soft_note}</div>"
    )


def progress_block(progress: dict[str, object]) -> str:
    ready = int(progress.get("ready") or 0)
    total = int(progress.get("total") or 0)
    missing = progress.get("missing")
    missing_list = missing if isinstance(missing, list) else []
    if missing_list:
        items = "".join(f"<li>{escape(item)}</li>" for item in missing_list[:7])
        missing_html = f'<p class="gap-note">Eksik:</p><ul class="gap-list">{items}</ul>'
    else:
        missing_html = '<p class="ok-note">Okuma sirasi tamam.</p>'
    return (
        f'<div class="progress-block">'
        f'<div class="progress-head">Çalışma bağlamı: {ready}/{total} hazır</div>'
        '<p class="section-note">Bu, proje ilerlemesi veya teslim kararı değildir.</p>'
        f"{missing_html}"
        "</div>"
    )


def read_order_rows(read_order: list[object]) -> str:
    rows: list[str] = []
    for index, item in enumerate(read_order, start=1):
        if not isinstance(item, dict):
            continue
        purpose = str(item.get("purpose") or "")
        label = _PURPOSE_LABELS.get(purpose, purpose)
        path = item.get("path") or "(yok)"
        exists = bool(item.get("exists"))
        badge = "var" if exists else "eksik"
        css_class = "ok" if exists else "gap"
        rows.append(
            f'<tr><td class="num">{index}</td><td>{escape(label)}</td>'
            f'<td class="mono">{escape(path)}</td>'
            f'<td><span class="badge {css_class}">{badge}</span></td></tr>'
        )
    return "\n".join(rows)


def is_temporary_project_name(value: object) -> bool:
    text = str(value or "")
    suffix = text[3:]
    return text.startswith("tmp") and len(suffix) >= 6 and all(
        char.isalnum() or char == "_" for char in suffix
    )


def timeline_html(events: list[object]) -> str:
    if not events:
        return (
            '<p class="muted">Henüz olay yok. Bir proje kaydedildiğinde veya '
            "bir iş başlatıldığında burada görünür.</p>"
        )
    items: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = str(event.get("kind") or "")
        label = _KIND_LABELS.get(kind, kind or "olay")
        stamp = str(event.get("created_at") or "")[:19].replace("T", " ")
        name = event.get("project_name") or ""
        if is_temporary_project_name(name):
            continue
        detail = event.get("detail") or ""
        kind_class = f"kind-{kind}" if kind else "kind-unknown"
        items.append(
            f'<li class="timeline-item {kind_class}" data-kind="{escape(kind)}">'
            f'<span class="badge kind {kind_class}">{escape(label)}</span>'
            f'<span><span class="mono">{escape(stamp)}</span> '
            f"{escape(name)} — {escape(detail)}</span>"
            "</li>"
        )
    if not items:
        return '<p class="muted">Gösterilecek kalıcı proje olayı yok.</p>'
    return f'<ol class="timeline">{"".join(items)}</ol>'


def provisions_html(provisions: list[object]) -> str:
    if not provisions:
        return (
            '<p class="muted">Henüz URL ile kurulan proje yok.</p>'
        )
    rows: list[str] = []
    for item in provisions:
        if not isinstance(item, dict):
            continue
        source_detail = private_detail("URL'yi göster", item.get("source_url"))
        install_detail = private_detail("Hedefi göster", item.get("install_path"))
        rows.append(
            "<tr>"
            f"<td>{source_detail or '—'}</td>"
            f"<td>{install_detail or '—'}</td>"
            f'<td>{escape(item.get("status") or "?")}</td>'
            f'<td>{escape(item.get("created_at") or "")[:19]}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th>URL</th><th>Hedef</th><th>Durum</th><th>Zaman</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def project_history_html(model: object) -> str:
    """Render only the bounded, non-authoritative Project History read model."""
    if not isinstance(model, dict):
        return '<p class="muted">Proje geçmişi okunamadı.</p>'
    items = model.get("items")
    rows: list[str] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        lifecycle = str(item.get("lifecycle") or "")
        label = "Kapandı" if lifecycle == "project-closed" else "Yeniden açıldı"
        commit = str(item.get("final_commit") or "")[:12] or "—"
        release = str(item.get("release_ref") or "—")
        rows.append(
            "<tr>"
            f"<td>{escape(label)}</td>"
            f'<td class="mono">{escape(commit)}</td>'
            f"<td>{escape(release)}</td>"
            f"<td>{escape(item.get('summary') or '')}</td>"
            "</tr>"
        )
    status = str(model.get("validation_status") or "not-run")
    if not rows:
        return f'<p class="muted" data-history-status="{escape(status)}">Henüz kalıcı proje geçmişi yok.</p>'
    return (
        f'<p class="section-note" data-history-status="{escape(status)}">'
        "Proje geçmişi salt okunur bir görünümdür; iş tamamlayamaz.</p>"
        "<table><thead><tr><th>Yaşam döngüsü</th><th>Commit</th>"
        "<th>Sürüm</th><th>Özet</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def section_overview(
    *,
    root_name: str,
    decision: str,
    delivery: str,
    now: str,
    brain: str,
    mismatch_banner: str,
    progress: str,
    coherence: dict[str, object],
    git: dict[str, object],
    next_action: object,
    owner_cockpit: str = "",
) -> str:
    return (
        '<section id="panel-overview" class="panel" data-admin-section="overview">'
        '<div class="hero" id="pala-admin-hero">'
        '<p class="hero-brand">Pala</p>'
        '<p class="hero-lead">Yerel kontrol merkezi — hafıza, ticket, kalite ve '
        "kurulum. Bağlam penceresini büyütmez; yalnız gerekli bilgiyi gösterir.</p>"
        "</div>"
        f"{owner_cockpit}"
        f"{decision}"
        f"{delivery}"
        f"{now}"
        f"{brain}"
        f"{mismatch_banner}"
        f"{progress}"
        '<div class="grid">'
        '<div class="card"><div class="k">Aktif ticket</div>'
        f'<div class="v">{escape(coherence.get("active") or "yok")}</div></div>'
        '<div class="card"><div class="k">Sonraki iş</div>'
        f'<div class="v">{escape(coherence.get("inferred_next") or next_action or "yok")}</div></div>'
        '<div class="card"><div class="k">Git</div>'
        f'<div class="v mono">{escape(git.get("branch") or "?")}</div></div>'
        '<div class="card"><div class="k">Değişen dosya</div>'
        f'<div class="v">{escape(git.get("dirty_count", 0))}</div></div>'
        "</div>"
        f'<p class="muted-inline">Proje: {escape(root_name)}</p>'
        "</section>"
    )


def section_install() -> str:
    return (
        '<section id="panel-install" class="panel" data-admin-section="install">'
        "<h2>Kurulum ve Denetim</h2>"
        '<p class="section-note">Pala bu işlemleri siz istemeden başlatmaz. '
        "Kurulum, denetim ve onarım komutları gerektiğinde elle çalıştırılır.</p>"
        '<div class="cmd mono">codex plugin marketplace add trugurpala/pala-project-studio</div>'
        '<div class="cmd mono">codex plugin add pala-project-studio@pala-project-studio</div>'
        '<div class="cmd mono">powershell -NoProfile -ExecutionPolicy Bypass '
        "-File .\\Install-Pala.ps1 -Mode Doctor</div>"
        '<div class="cmd mono">powershell -NoProfile -ExecutionPolicy Bypass '
        "-File .\\Install-Pala.ps1 -Mode Repair</div>"
        '<div class="warnline">Doctor <span class="mono">healthy</span> / '
        '<span class="mono">plugin_ready</span> dosyaların hazır olduğunu gösterir; '
        "/hooks ekranındaki güven izninin verildiğini göstermez.</div>"
        "</section>"
    )


def section_hooks() -> str:
    return (
        '<section id="panel-hooks" class="panel" data-admin-section="hooks">'
        "<h2>Hook güveni</h2>"
        '<div class="warnline" id="pala-hooks-trust" data-evidence="configured-not-verified">'
        "Dosyalar hazır. Son adım: Codex'te <span class=\"mono\">/hooks</span> "
        "ekranını açın, Pala'ya güven verin ve yeni bir görev başlatın. "
        "<strong>configured-not-verified</strong></div>"
        '<p class="section-note"><span class="mono">hook_safety=passed</span> '
        "yalnız dosya ve sözleşme kontrolüdür; ekrandaki güven izninin kanıtı değildir.</p>"
        "</section>"
    )


def section_quality(quality: object, verification_tier: object, delivery: str) -> str:
    quality = quality if isinstance(quality, dict) else {}
    risk = quality.get("risk") if isinstance(quality.get("risk"), dict) else {}
    coverage = quality.get("coverage") if isinstance(quality.get("coverage"), dict) else {}
    tier = str(verification_tier or "not-run")
    return (
        '<section id="panel-quality" class="panel" data-admin-section="quality">'
        "<h2>Kalite kontrolleri</h2>"
        '<p class="section-note">Zorunlu kontroller ve kanıtlar burada özetlenir. '
        "Bir kontrol çalışmadıysa tamamlanmış sayılmaz.</p>"
        f"{delivery}"
        '<div class="grid">'
        '<div class="card"><div class="k">Durum</div>'
        f'<div class="v">{escape(quality.get("status") or "not-run")}</div></div>'
        '<div class="card"><div class="k">İş kartı</div>'
        f'<div class="v">{escape(quality.get("ticket") or "yok")}</div></div>'
        '<div class="card"><div class="k">Risk</div>'
        f'<div class="v">{escape(risk.get("level") or "unknown")}</div></div>'
        '<div class="card"><div class="k">Geçen kontroller</div>'
        f'<div class="v">{escape(int(coverage.get("passed") or 0))}/'
        f'{escape(int(coverage.get("required") or 0))}</div></div>'
        "</div>"
        f'<div class="warnline">Son eksik: {escape(quality.get("last_problem") or "yok")}</div>'
        f'<div class="okline">Sonraki: {escape(quality.get("next_action") or "yok")}</div>'
        '<div class="quality-tier-panel card" id="pala-quality-tier">'
        '<div class="k">Doğrulama düzeyi</div>'
        f'<div class="v mono">{escape(tier)}</div>'
        '<p class="pref-desc">Bu satır görünüm ayarlarından gizlenebilir; '
        "iş akışının gerçek durumunu değiştirmez.</p>"
        "</div>"
        "</section>"
    )


def section_memory(
    store_path: object,
    events: list[object],
    provisions: list[object],
    history: object,
) -> str:
    return (
        '<section id="panel-memory" class="panel" data-admin-section="memory">'
        "<h2>Hafıza</h2>"
        '<p class="section-note">SQLite yerel store yolu varsayılan olarak gizli.</p>'
        f'{private_detail("SQLite yolunu göster", store_path)}'
        '<div class="experts-panel card" id="pala-experts-panel">'
        '<div class="k">Uzman araçlar (isteğe bağlı)</div>'
        '<div class="v">Node veya uv ile hazır olabilir; Pala bunları kendiliğinden kurmaz ya da çalıştırmaz.</div>'
        '<p class="pref-desc">«Uzman araçları göster» kapalıysa bu panel gizlenir.</p>'
        "</div>"
        "<h2>Son olaylar</h2>"
        f"{timeline_html(events)}"
        "<h2>Geçmiş projeler</h2>"
        f"{project_history_html(history)}"
        "<h2>Son URL kurulumlari</h2>"
        f"{provisions_html(provisions)}"
        "</section>"
    )


def section_tickets(
    *, coherence: dict[str, object], next_action: object, read_order: list[object]
) -> str:
    return (
        '<section id="panel-tickets" class="panel" data-admin-section="tickets">'
        "<h2>\u0130\u015fler ve sonraki ad\u0131m</h2>"
        f"{now_line(next_action, coherence.get('active'))}"
        '<div class="grid">'
        '<div class="card"><div class="k">Aktif</div>'
        f'<div class="v">{escape(coherence.get("active") or "yok")}</div></div>'
        '<div class="card"><div class="k">Bulunan sonraki adım</div>'
        f'<div class="v">{escape(coherence.get("inferred_next") or next_action or "yok")}</div></div>'
        "</div>"
        "<h2>Zorunlu okuma sırası</h2>"
        "<table><thead><tr><th>#</th><th>Amac</th><th>Dosya</th><th>Durum</th>"
        f"</tr></thead><tbody>{read_order_rows(read_order)}</tbody></table>"
        "</section>"
    )


def section_features() -> str:
    return (
        '<section id="panel-features" class="panel" data-admin-section="features">'
        "<h2>Ayarlar</h2>"
        '<p class="section-note">Yalnız Pala görünümünü değiştirir. '
        "Ücretli kilit yoktur. Tercihler bu tarayıcıda saklanır ve iş akışını etkilemez.</p>"
        '<ul class="pref-list" id="pala-feature-toggles">'
        '<li class="pref-row">'
        '<input type="checkbox" id="pref-show-experts" checked>'
        '<label for="pref-show-experts">'
        '<span class="pref-title">Uzman araçları göster</span>'
        '<span class="pref-desc">Hafıza bölümündeki isteğe bağlı araçları gösterir. '
        "Herhangi bir kurulum başlatmaz.</span></label></li>"
        '<li class="pref-row">'
        '<input type="checkbox" id="pref-soft-fail-closed">'
        '<label for="pref-soft-fail-closed">'
        '<span class="pref-title">Kapanmış sorunları hatırlat</span>'
        '<span class="pref-desc">Kapanmış sorun sayısını ek bilgi olarak gösterir.</span></label></li>'
        '<li class="pref-row">'
        '<input type="checkbox" id="pref-show-quality-tier" checked>'
        '<label for="pref-show-quality-tier">'
        '<span class="pref-title">Doğrulama düzeyini göster</span>'
        '<span class="pref-desc">Kalite bölümünde doğrulama düzeyini gösterir.</span>'
        "</label></li>"
        "</ul>"
        "</section>"
    )
