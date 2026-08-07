# Pala Project Studio Durumu

- Güncelleme: 2026-08-07
- Aktif milestone: M20 — Gerçeklik + vibe ilk 10 dk (`completed` bellek/release;
  skill canary insan adımı açık).
- Aktif ticket: Yok (yeni özellik yok).
- Plugin/manifest sürümü: `0.7.1+codex.20260807190000` (kaynak `main`).
- Son GitHub release: `v0.7.1` (`passed`).
  - URL: https://github.com/trugurpala/pala-project-studio/releases/tag/v0.7.1
  - Asset: `pala-project-studio-0.7.1.zip`
  - SHA-256: `4CD388A40392B7C8AAE0A1A742307993F829F116FB3D4F08989FB1A009230A9D`
  - Target: `c028bea32d159d16ab0b6734d36c12e73c9a53ac`
- Kod hattı: PR #9 + M20 docs PR #10 `main`de.
  - PR #9: https://github.com/trugurpala/pala-project-studio/pull/9
  - PR #10: https://github.com/trugurpala/pala-project-studio/pull/10
- `main` Quality (PR #9 merge): run `31197621102` — Windows + Ubuntu
  `success` (`passed`).
  - https://github.com/trugurpala/pala-project-studio/actions/runs/31197621102
- Yerel `py -3 scripts/verify.py` (release ZIP): `passed`; aynı SHA yukarıda.
## 0.5–0.7.1 kaynak özeti (kodda landed; STATUS drift giderildi)

| Sürüm | Kapsam | Kanıt |
| --- | --- | --- |
| 0.5 | Proje hafıza sözleşmesi (ADR-012), plain `pala_state memory` | `passed` (PR #8/#9 kod + Quality) |
| 0.6 | Durum sayfası ilk yüzey (ADR-013/014), `pala_report` / Status HTML | `passed` (kod + Quality) |
| 0.7 | Yerel SQLite store + timeline (ADR-015), catalog/provision | `passed` (kod + Quality) |
| 0.7.1 | Windows Codex PATH keşfi + core/experts Doctor ayrımı (ADR-016) | `passed` (kod + Quality); GitHub release ZIP ayrı |

## M19 (önceki teslim — korundu)

- M19 / PALA-052 `main`de: OSS katkı akışı, `pala_oss.py`, ADR-011.
- Merge sonrası Quality #41 (`31155491104`): `passed` (tarihsel kanıt).
- Gerçek üçüncü taraf OSS canary: `not-run`.

## Owner canary (bu makine — 2026-08-07)

- Install: `passed` (exit 0; güncelleme tamam; uzman ready).
- Doctor: `passed` — `healthy=True`, `plugin_ready=True`,
  `experts_ready=True`; kurulu plugin
  `0.7.1+codex.20260807190000`.
- Status: `passed` — HTML
  `.codex/pala-status.html`; katalog DB
  `C:\Users\Pala-Pc\Desktop\Codex\pala.sqlite` (`exists`, boyutu >0).
- Hook güveni: `blocked` — Doctor `hook=blocked`; otomatik bypass yok.
- Yeni Codex sohbetinde örtük/açık `pala-project-finisher` tetik:
  `not-run` (UI: `/hooks` + yeni sohbet gerekir; bu ortamdan otomatik
  doğrulanamadı).
- ChatGPT Plus düz sohbet kurulumu: desteklenmez (iddia yok).

## Açık artımlar (blokör değil)

- M10 RTK rewrite / Context7-Playwright MCP kurulum maddeleri: `not-run`
  (bilerek ertelendi; vibe ilk oturum için blokör değil).
- Taşınabilir Claude/Cursor skill kopyası: ayrı ticket.

## Tek sonraki iş

1. İnsan: Codex'te `/hooks` ile Pala hook güvenini ver → **yeni sohbet** aç →
   yazılım işi söyle veya `pala-project-finisher` çağır; Status/rapor
   göründüğünde skill canary `passed` yazılır.
2. Vibe yolu: [docs/VIBE_FIRST_SESSION.md](docs/VIBE_FIRST_SESSION.md).
