# GOAL — Pala 0.8.1 finish + kontrol merkezi

Güncelleme: 2026-08-09 · Kanıt etiketleri: `passed` | `not-run` | `blocked` |
`configured-not-verified`.

## Product goal / Ürün hedefi

**EN:** Pala (`@pala-project-studio`) is a Codex-native project memory / plan /
verification plugin. It does not enlarge context windows or quotas. Long work
stays durable via AGENTS → STATUS → PLAN, SessionStart presence, SQLite catalog,
and an honest local Status HTML surface that feels like a real app page
(sidebar, sections, theme, feature toggles) — not a dump of logs.

**TR:** Pala, Codex için yerel proje yürütme eklentisidir. Pencere/kota iddiası
yok. Kullanıcı “tam sayfa uygulama” hissi bekler: marka Pala, tek kompozisyon,
açık bölümler, koyu/açık tema, gerçek Pala ayarları için yetki/özellik
anahtarları. Soft “bitti/% hız” kanıt sayılmaz.

## Required plugins / tool surface (cite)

| Plugin / tool | Role | Pala relationship |
| --- | --- | --- |
| **Pala** (`@pala-project-studio`) | Product under build | Source of truth |
| **Context7** | Library docs MCP | Optional agent assist; not a Pala runtime dep |
| **Chrome / browser control** | Optional UI smoke | Status HTML may be opened; hooks never auto-open |
| **product-design** | Visual / IA guidance | Sidebar, sections, readable type — no purple-AI-slop |
| **Filament PHP** (+ [superduper-filament-starter-kit](https://github.com/riodwanto/superduper-filament-starter-kit)) | **UX inspiration only** | Patterns: sidebar, settings rows, dark/light. **No Laravel/PHP rewrite of Pala.** |

## Done criteria

1. **Publish 0.8.1** — branch push, PR merge, tag `v0.8.1`, GitHub release ZIP —
   `passed` (or record URLs if already done).
2. **GOAL documented** — this file + root `GOAL.md` pointer — `passed`.
3. **Admin / control Status HTML** — theme (localStorage), sections (Overview,
   Install/Doctor, Hooks trust, Quality 0.9, Memory/store, Tickets/next,
   Yetki/özellik), real Pala prefs only — `passed` with contract tests.
4. **Honesty** — `/hooks` UI trust remains `configured-not-verified` until a
   human clicks trust in Codex Work. No fake premium paywall. No network feature
   claims for hook path.
5. **verify.py** green (or focused + honest labels) + Desktop final ZIP digest
   recorded — `passed` | `not-run`.
6. **Turkish-friendly docs**; code identifiers stay English.

## Explicit non-goals

- Rewriting Pala as Filament / Laravel / PHP admin panel.
- Soft A/B % quality or speed claims.
- Claiming `/hooks` trust `passed` without owner UI action.
- Editing the `finish_all_remaining` plan file.

## Completeness audit (vs this GOAL)

| Item | Status | Evidence |
| --- | --- | --- |
| M30 vibe / host-fit on `main` | `passed` | PR [#20](https://github.com/trugurpala/pala-project-studio/pull/20) merged |
| Tag + release `v0.8.1` | `passed` | https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.1 |
| Release ZIP asset | `passed` | `pala-project-studio-0.8.1-final.zip` (SHA-256 `69325B6E…FF53` at tag time) |
| Quality engine 0.9 surface | `passed` | five-signal Status strip + `pala_quality` |
| GOAL.md docs | `passed` | this file + root pointer |
| Admin control center (theme + sections + toggles) | `passed` | landmarks + verify 362 OK |
| `/hooks` trust | `configured-not-verified` | human / Codex Work |
| Soft full-product “A/B fixed” | **yok** | intentionally not claimed |
| Post-tag Desktop ZIP (control center) | `passed` | SHA-256 `5C16A96FA7D790969D84E36043D67E789E8ADEF835C29CF451EC0650F40FE65F` (local; GitHub release asset remains tag-time `69325B6E…`) |

## How to open the control page

```powershell
py -3 scripts\pala_report.py --cwd . --open
```

or `Install-Pala.ps1 -Mode Status`. Output: `.codex/pala-status.html`
(gitignored). Open hint printed as `açmak için: file://…`.

## Publish URLs (0.8.1)

- PR: https://github.com/trugurpala/pala-project-studio/pull/20
- Release: https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.1
- ZIP: https://github.com/trugurpala/pala-project-studio/releases/download/v0.8.1/pala-project-studio-0.8.1-final.zip
