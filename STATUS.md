# Pala Project Studio Durumu

- Güncelleme: 2026-08-08 (M26 — v0.8.0 GitHub release)
- Aktif milestone: **M26**
- Aktif ticket: **M26-T3** (commit → push → tag → release)
- Plugin/manifest sürümü: `0.8.0+codex.20260808021500` (kaynak; GitHub’da henüz yok)
- Son GitHub release: `v0.7.1` (`passed`); `v0.8.0` release ZIP: `not-run`
- Repo görünürlük: **public** (`passed`).
- `origin/main`: `ac57dd1`; yerel 0.8.0 working tree commit bekliyor.

## Şu an tek sonraki iş

**M26-T3…T5:** Commit → push `main` → tag `v0.8.0` → `gh release create` +
portable ZIP. (Owner: “release olana kadar uygula”.)

## M26 ajan → görev

| Task | Sahip | Kanıt |
| --- | --- | --- |
| M26-T1 Plan panosu | Ajan-Plan | `passed` |
| M26-T2 Final verify | Ajan-Kapı | `passed` |
| M26-T3 Commit | Ajan-Yayın | `not-run` |
| M26-T4 Push main | Ajan-Yayın | `not-run` |
| M26-T5 Tag + gh release | Ajan-Yayın | `not-run` |
| M26-T6 Evidence docs | Ajan-Plan | `not-run` |

## M26 / release kanıt

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Tam yerel kapı `verify.py` | `passed` | 234 test + self-audit |
| Portable ZIP SHA-256 | `passed` | `3EA17A1CEFF7DEEBF906D03184D9B9F09F800B4B64B4AD0D880AD30C22A6916E` |
| GitHub `v0.8.0` release | `not-run` | sıradaki adım |

## Önceki kapılar (özet)

| Kapı | Sonuç |
| --- | --- |
| M24 ajan görevleri + verify | `passed` |
| M23 yerel release hazırlığı | `passed` |
| M22 demo Status + hata beyni | `passed` |
| M21 presence + fork pack | `passed` |
| GitHub `v0.7.1` | `passed` |

## Açık ama blokör değil

- M10 RTK / Context7-Playwright MCP: `not-run`
- M25 ortak hafıza ürünü: DRAFT / uygulama yok
- Açık eski PR `#5` (0.5A): release blokörü değil
- DEMO-005 owner handoff (demo örneği): isteğe bağlı
- Owner Install/Doctor/UI canary bu turda yeniden koşulmadı: `not-run`
