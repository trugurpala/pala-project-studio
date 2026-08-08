# Pala A/B — live mini re-measure (0.8.1)

- Generated: `2026-08-08T12:17:06.451747+00:00`
- Plugin (temp profile): `0.8.1+codex.20260808124500`
- CODEX_HOME pala: `C:\Users\Pala-Pc\Desktop\PalaAB\profiles\live-08x`
- CODEX_HOME control: `C:\Users\Pala-Pc\Desktop\PalaAB\profiles\live-08x-ctrl`
- Design: n=1 control + n=1 pala × 2 cold sessions (Su Takip day-boundary)
- Experiment class: `controlled-ab-mini`
- Soft full-product “A/B fixed”: **no** — mini re-measure only (n=1+1).
- Hooks UI trust: `configured-not-verified`

## Focus outcomes

| Check | Control | Pala |
| --- | --- | --- |
| Live sessions (codex exec) | `passed` | `passed` |
| Path error not repeated (`../../scripts`) | `not-applicable` | `passed` |
| Complete lifecycle fail-closed + close | `not-applicable` | `passed` |

## Session wall times

- Control S1/S2 ms: `125626` / `34355`
- Pala S1/S2 ms: `376848` / `492642`

## Notes

- Control path_wrong_mentions S1+S2: `0`
- Pala path_wrong_mentions S1+S2: `0`
- Pala marketplace path mentioned: `True` / `True`
- Pala quasi path_memory: `passed`
- Pala quasi complete_fail_closed: `passed`
- Pala quasi complete_ok: `passed`
- Pala S1 last tail: `Tamamlandı. Yerel commit oluşturuldu: `ed74df4 chore: checkpoint WATER-001 session` — push yapılmadı.  - `WATER-001` hedefle başlatıldı ve evidence’li checkpoint alındı. - `node test_smoke.mjs`: `passed`. - Geçersiz bilet/oturumla `complete`
- Pala S2 last tail: `Tamamlandı: WATER-001 kaydı `completed`, INC-001 `CLOSED`.  - Günlük kayıtlar artık `days[dateKey]` altında ayrılıyor; yeni gün 0 ml ile başlıyor ve geri alma yalnızca o günü etkiliyor. Tarihsiz eski kayıtlar güvenle güne atanamadığı için h`

Prior Wave C early-stop (0.8.0) saw complete fail + `../../scripts` repeat.
This mini run measures 0.8.1 temp-profile marketplace only; not a full product A/B claim.

Raw JSON: `C:\\Users\\Pala-Pc\\Desktop\\PalaAB\\meta\\live-mini-08x\\result.json`
