#!/usr/bin/env python3
"""CSS ownership for Pala's local status page."""

from __future__ import annotations


def _shell_rules(checked_label_css: str, focus_label_css: str, show_css: str) -> str:
    return f"""
  :root, html[data-theme="dark"] {{
    color-scheme: dark;
    --bg: #12151c;
    --bg-accent: #181c26;
    --fg: #e8eaef;
    --muted: #9aa3b5;
    --panel: #1a1f2a;
    --line: #2c3446;
    --brand: #e8dcc8;
    --accent: #c4a574;
    --focus: #e6c35c;
    --ok-bg: #14261c;
    --ok-fg: #8fcea8;
    --warn-bg: #2a2e38;
    --warn-fg: #d0d5e0;
    --alert-bg: #3a2320;
    --alert-fg: #f0a898;
    --now-bg: #1a2434;
    --now-bd: #3d5678;
    --sidebar: #151922;
    --nav-hover: #1e2430;
    --nav-active: #243044;
  }}
  html[data-theme="light"] {{
    color-scheme: light;
    --bg: #f3f5f7;
    --bg-accent: #e8ecf1;
    --fg: #1c1f26;
    --muted: #5c6575;
    --panel: #ffffff;
    --line: #cfd5de;
    --brand: #1c1f26;
    --accent: #3d6a8a;
    --focus: #3d6a8a;
    --ok-bg: #e5f2ea;
    --ok-fg: #1f5c3a;
    --warn-bg: #eef0f3;
    --warn-fg: #5c5340;
    --alert-bg: #f7e6e2;
    --alert-fg: #8a3a2e;
    --now-bg: #e8eef5;
    --now-bd: #b8c4d6;
    --sidebar: #e7ebf0;
    --nav-hover: #dce2ea;
    --nav-active: #d0d8e2;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    margin: 0; background: var(--bg); color: var(--fg); line-height: 1.45;
  }}
  .skip-link {{
    position: absolute; left: -9999px; top: 0; z-index: 100;
    background: #fff; color: #111; padding: .6rem 1rem; border-radius: 6px;
    font-weight: 600; text-decoration: none;
  }}
  .skip-link:focus {{ left: 1rem; top: 1rem; outline: 3px solid var(--focus); outline-offset: 2px; }}
  input[type="radio"] {{ position: absolute; opacity: 0; width: 1px; height: 1px; }}
  .shell {{ display: grid; grid-template-columns: minmax(12rem, 15rem) 1fr; min-height: 100vh; }}
  .sidebar {{
    background: var(--sidebar); border-right: 1px solid var(--line);
    padding: 16px 12px; display: flex; flex-direction: column; gap: 4px;
  }}
  .brand-block {{
    padding: 8px 10px 14px; margin-bottom: 8px; border-bottom: 1px solid var(--line);
  }}
  .brand-name {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.55rem; letter-spacing: .02em; color: var(--brand); margin: 0;
  }}
  .brand-tag {{ color: var(--muted); font-size: 12px; margin: 4px 0 0; }}
  .sidebar .nav-title {{
    font-size: 11px; margin: 12px 0 6px; color: var(--muted);
    text-transform: uppercase; letter-spacing: .06em;
  }}
  .nav-item {{
    display: flex; justify-content: space-between; align-items: center;
    gap: 8px; padding: 9px 12px; border-radius: 8px; cursor: pointer;
    border: 1px solid transparent; color: var(--fg);
  }}
  .nav-item:hover {{ background: var(--nav-hover); }}
  .nav-item:focus-within, .nav-item:focus {{
    outline: 3px solid var(--focus); outline-offset: 2px;
  }}
  .nav-name {{ font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  {checked_label_css}
  {focus_label_css}
  .main {{ padding: 20px 24px 32px; max-width: 74rem; }}
  .topbar {{
    display: flex; flex-wrap: wrap; align-items: flex-start;
    justify-content: space-between; gap: 12px; margin-bottom: 8px;
  }}
  .panel {{ display: none; }}
  {show_css}
""".replace("{{", "{").replace("}}", "}")


def _component_rules() -> str:
    return """  h1.title {{ font-size: 1.45rem; margin: 0 0 4px; color: var(--brand); }}
  h2 {{
    font-size: 13px; margin: 22px 0 8px; color: var(--muted);
    text-transform: uppercase; letter-spacing: .05em;
  }}
  .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 12px; }}
  .private-detail {{ color: var(--muted); font-size: 12px; margin: 6px 0; }}
  .private-detail summary {{ cursor: pointer; color: var(--muted); }}
  .private-detail span, .private-detail a {{ display: inline-block; margin-top: 6px; overflow-wrap: anywhere; }}
  .delivery-card {{
    border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px;
    margin: 0 0 12px; background: var(--panel);
  }}
  .delivery-card.tone-ok {{ background: var(--ok-bg); border-color: var(--ok-fg); }}
  .delivery-card.tone-warn {{ background: var(--warn-bg); border-color: var(--line); }}
  .delivery-card.tone-alert {{ background: var(--alert-bg); border-color: var(--alert-fg); }}
  .delivery-k {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }}
  .delivery-v {{ font-size: 1.05rem; font-weight: 700; margin: 3px 0; }}
  .delivery-detail, .delivery-action {{ margin: 5px 0; font-size: 13px; }}
  .delivery-card details {{ margin-top: 8px; font-size: 13px; }}
  .delivery-card summary {{ cursor: pointer; font-weight: 600; }}
  .delivery-gates {{ margin: 7px 0 0; padding-left: 18px; }}
  .delivery-gates li {{ margin: 4px 0; }}
  .hero {{
    background: var(--bg-accent); border: 1px solid var(--line);
    border-radius: 12px; padding: 18px 20px; margin: 0 0 14px;
  }}
  .hero-brand {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.75rem; margin: 0 0 6px; color: var(--brand);
  }}
  .hero-lead {{ margin: 0; color: var(--muted); font-size: 14px; max-width: 42rem; }}
  .nowline {{
    background: var(--now-bg); border: 1px solid var(--now-bd); color: var(--fg);
    padding: 14px 16px; border-radius: 10px; margin: 8px 0 16px; font-size: 1.05rem;
    display: flex; flex-wrap: wrap; gap: .35rem .6rem; align-items: baseline;
  }}
  .now-k {{ color: var(--accent); font-weight: 600; }}
  .decision-strip {{
    display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;
    margin: 8px 0 16px;
  }}
  .signal {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 10px 12px; min-width: 0;
  }}
  .signal-k {{
    color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: .04em; margin-bottom: 4px;
  }}
  .signal-v {{ font-size: 13px; word-break: break-word; line-height: 1.35; }}
  .signal.tone-now {{ background: var(--now-bg); border-color: var(--now-bd); }}
  .signal.tone-ok {{ border-color: #1f4a34; }}
  .signal.tone-ok .signal-v {{ color: var(--ok-fg); }}
  .signal.tone-warn {{ border-color: #5a4e28; }}
  .signal.tone-warn .signal-v {{ color: #c9a84a; }}
  html[data-theme="light"] .signal.tone-warn .signal-v {{ color: #7a6220; }}
  .signal.tone-alert {{ border-color: #5a2f2a; }}
  .signal.tone-alert .signal-v {{ color: var(--alert-fg); }}
  .progress-block {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px; margin: 8px 0 16px;
  }}
  .progress-head {{ font-size: 18px; margin-bottom: 8px; }}
  .gap-note {{ color: var(--alert-fg); margin: 0; }}
  .ok-note {{ color: var(--ok-fg); margin: 0; }}
  .gap-list {{ margin: 6px 0 0; padding-left: 18px; color: var(--alert-fg); }}
  .timeline {{ list-style: none; margin: 0; padding: 0; }}
  .timeline li {{
    padding: 10px 0; border-bottom: 1px solid var(--line); font-size: 13px;
    display: grid; grid-template-columns: auto 1fr; gap: .35rem .75rem;
  }}
  .timeline li:last-child {{ border-bottom: none; }}
  .badge.kind {{ background: var(--nav-active); color: var(--fg); }}
  .badge.kind-checkpoint {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.kind-debug_attempt {{ background: #3a3218; color: #e8c56a; }}
  html[data-theme="light"] .badge.kind-debug_attempt {{ background: #f3e8c8; color: #6a5418; }}
  .timeline-item.kind-debug_attempt {{ border-left: 3px solid #c9a84a; padding-left: 8px; }}
  .timeline-item.kind-checkpoint {{ border-left: 3px solid var(--ok-fg); padding-left: 8px; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin: 12px 0;
  }}
""".replace("{{", "{").replace("}}", "}")


def _responsive_rules() -> str:
    return """  .card {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px;
  }}
  .card .k {{ color: var(--muted); font-size: 12px; }}
  .card .v {{ font-size: 16px; margin-top: 4px; word-break: break-word; }}
  table {{
    width: 100%; border-collapse: collapse; background: var(--panel);
    border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  }}
  th, td {{
    text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px;
  }}
  th {{ color: var(--muted); font-weight: 600; background: var(--sidebar); }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ color: var(--muted); width: 34px; }}
  .mono {{
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace; color: var(--muted);
  }}
  .muted {{ color: var(--muted); text-align: center; }}
  .muted-inline {{ color: var(--muted); font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; }}
  .badge.ok {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.gap {{ background: var(--alert-bg); color: var(--alert-fg); }}
  .badge.fresh {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.aging {{ background: #3a3218; color: #e8c56a; }}
  .badge.stale {{ background: var(--alert-bg); color: var(--alert-fg); }}
  .alert {{
    background: var(--alert-bg); color: var(--alert-fg); padding: 10px 14px;
    border-radius: 8px; margin: 8px 0;
  }}
  .okline {{
    background: var(--ok-bg); color: var(--ok-fg); padding: 10px 14px;
    border-radius: 8px; margin: 8px 0;
  }}
  .warnline {{
    background: var(--warn-bg); color: var(--warn-fg); padding: 10px 14px;
    border-radius: 8px; margin: 8px 0;
  }}
  a {{ color: var(--accent); }}
  a:focus-visible, button:focus-visible, .nav-item:focus-visible {{
    outline: 3px solid var(--focus); outline-offset: 2px;
  }}
  .theme-toggle, .pref-row input {{ cursor: pointer; }}
  .theme-toggle {{
    background: var(--panel); color: var(--fg); border: 1px solid var(--line);
    border-radius: 8px; padding: 8px 12px; font-size: 13px;
  }}
  .pref-list {{ list-style: none; margin: 0; padding: 0; }}
  .pref-row {{
    display: flex; align-items: flex-start; gap: 12px;
    padding: 14px 12px; border: 1px solid var(--line); border-radius: 10px;
    background: var(--panel); margin-bottom: 8px;
  }}
  .pref-row label {{ flex: 1; cursor: pointer; }}
  .pref-title {{ font-weight: 600; display: block; margin-bottom: 2px; }}
  .pref-desc {{ color: var(--muted); font-size: 13px; }}
  .cmd {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
    padding: 10px 12px; font-size: 12px; overflow-x: auto; margin: 8px 0;
  }}
  .section-note {{ color: var(--muted); font-size: 13px; margin: 0 0 10px; }}
  html[data-show-experts="0"] .experts-panel {{ display: none; }}
  html[data-soft-fail-closed="0"] .soft-closed-note {{ display: none; }}
  html[data-show-quality-tier="0"] .quality-tier-panel {{ display: none; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 24px; }}
  .catalog-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  @media (max-width: 720px) {{
    .shell {{ grid-template-columns: minmax(0, 1fr); width: 100%; min-width: 0; }}
    .sidebar {{
      border-right: none; border-bottom: 1px solid var(--line);
      flex-direction: row; flex-wrap: wrap; gap: 8px;
      max-height: 46vh; overflow-y: auto; min-width: 0; width: 100%;
    }}
    .brand-block, .sidebar .nav-title {{ width: 100%; }}
    .nav-item {{ flex: 1 1 42%; min-width: 8rem; }}
    .main {{ padding: 16px; min-width: 0; width: 100%; }}
    .nowline {{ font-size: 1rem; }}
    .decision-strip {{ grid-template-columns: 1fr 1fr; }}
    .decision-strip .signal:first-child {{ grid-column: 1 / -1; }}
    .timeline li {{ grid-template-columns: 1fr; }}
    table {{ font-size: 12px; }}
  }}""".replace("{{", "{").replace("}}", "}")


def render_css(checked_label_css: str, focus_label_css: str, show_css: str) -> str:
    return "".join((
        _shell_rules(checked_label_css, focus_label_css, show_css),
        _component_rules(),
        _responsive_rules(),
    ))
