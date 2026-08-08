# Pala Project Studio Durumu

- Güncelleme: 2026-08-08 (Pala-Pc live: marketplace 0.8.1 sync + kontrol smoke + mini A/B n=1+1)
- Aktif milestone: M29 tamamlandı (kaynak); canlı mini re-measure bu makinede alındı
- Aktif ticket: yok (sonraki iş owner: hooks UI trust / v0.8.1 release)
- Plugin/manifest sürümü: `0.8.1+codex.20260808124500` (kaynak + Local marketplace + temp profile `live-08x`)
- Son GitHub release: `v0.8.0` (`passed`)
  https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.0
- GitHub tag/release `v0.8.1`: `not-run` (owner yetkisi ayrı)
- Repo görünürlük: **public** (`passed`).

## Şu an tek sonraki iş (owner)

Hooks UI `/hooks` trust (`configured-not-verified`). Soft full-product “A/B fixed”: **yok** (yalnız mini n=1+1). Push/PR/release ayrı yetki.

## Codex koşullu kabul — kaynak kanıt bağlamları (2026-08-08)

| Bağlam | Sonuç | Not |
| --- | --- | --- |
| Source commit SHA | `passed` | `10dd7de617d7198e06ea2f42ec3829fbd215a532` (working tree **dirty**) |
| `artifacts/codex-compat/p0-smoke.json` SHA-256 | `passed` | `a5ce3bbf9c6d1dce285858a367964b1d6c48bc135ab944cc8f0feb231c0cbcda` |
| Gate 0 | `passed` | `py -3 scripts/pala_p0_smoke.py` → exit **0**; overall `passed` **9/9** |
| Combined focused unittest | `passed` | `py -3 -m unittest scripts.test_pala_cold_packet scripts.test_pala_cmd_memory scripts.test_pala_p0_friction scripts.test_pala_debug_gate scripts.test_pala_memory -v` → Ran **69** / OK; exit **0** |
| `verify.py --mode installed` | `passed` | `py -3 scripts/verify.py --mode installed` → exit **0** (`PASSED: installed mode`) |
| Tam verify source full | `not-run` | bilerek; bu kapanışta çalıştırılmadı |
| Marketplace canlı (Pala-Pc Local + temp `live-08x`) | `passed` | `0.8.1+codex.20260808124500`; Install already-ready; plugin enabled on temp profile |
| Live `pala kontrol et` smoke | `passed` | `artifacts/codex-compat/live-kontrol-smoke.json`; hooks UI still `configured-not-verified` |
| Mini live A/B n=1+1 | `passed` | `outputs/PALA_AB_LIVE_MINI.md`; class `controlled-ab-mini`; path-not-repeated + complete fail-closed/close |
| Hooks UI trust | `configured-not-verified` | insan / canlı Codex UI |
| Soft “A/B fixed” | yok | mini re-measure only; not full-product claim |

## M29 — Gate 0 + cold packet + cmd memory (Wave D)

| Task | Sonuç | Not |
| --- | --- | --- |
| M29-Gate0 p0-smoke.json | `passed` | 9/9; fresh `pala_p0_smoke.py` exit 0; SHA-256 `a5ce3bbf9c6d1dce…` |
| M29-T1 cold-session packet ≤2KB | `passed` | `pala_cold_packet.py` + SessionStart/context |
| M29-T2 tool_attempts / do-not-retry | `passed` | focused + smoke path-memory row |
| M29-T3 context/doc budget profiles | `passed` | minimal\|standard\|milestone |
| M29-T4 capability + parallel safety | `passed` | honest labels; worktree reconcile |
| Focused unittest cold packet | `passed` | 13 ok (`test_pala_cold_packet`) |
| Focused regression (cmd+p0+debug+memory) | `passed` | Ran 69 / OK; exit 0 (fresh re-run) |
| Live A/B / marketplace re-measure | `passed` | Pala-Pc temp profile mini n=1+1; see Live mini table |
| Hooks UI trust | `configured-not-verified` | insan / canlı Codex |
| `verify.py --mode installed` | `passed` | fresh re-run exit 0; `PASSED: installed mode (runtime self-audit)` |
| Install-Pala Doctor (Pala-Pc) | `passed` | healthy=True, plugin=ready, codex=ready, hook_safety=passed; PS1 exit 2 experts `attention_required` |
| Tam `verify.py` (source full) | `not-run` | explicit; kapanışta çalıştırılmadı |
| Soft “A/B issues fixed” | yok | Gate0 kaynak `passed`; canlı A/B hâlâ 0.8.0 |

## Wave C — Codex live A/B (early-stop ingest)

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Controlled live A/B (temp profiles) | `passed` | early-stop; control n=3 pala n=2 |
| Blind eval | `not-run` | erken duruş; sahte skor yok |
| Decision | conditional-keep | handoff/checkpoint aid; not speed/reliability |
| Token / commands / duration | recorded | +49.97% / +60.61% / +26.79% (pala vs control completed) |
| Feature matrix (live) | `passed` | presence/register/context/checkpoint/handoff passed; begin partial; DEBUGGING partial; complete + same-error failed |
| outputs/PALA_AB_* ingest | `passed` | BACKTEST.md + RESULTS.json + FEATURE_MATRIX.csv |
| Focused unittest (ingest tur) | `passed` | 9 ok (`test_pala_p0_friction` + kontrol-et marker) |
| Hooks `/hooks` UI trust | `configured-not-verified` | insan adımı |
| Tam `verify.py` | `not-run` | scope dışı |

## Premium kontrol et bar

| Adım | Sonuç | Not |
| --- | --- | --- |
| Skill checklist (`kontrol et` / rapor / denetle) | `passed` | numbered read-only Codex list; no register/begin |
| Report → `.codex/pala-status.html` + `açmak için:` | `passed` | `pala_report` stdout contract |
| Status HTML decision strip | `passed` | Şimdi / INC / ticket / gate / tazelik |
| Skill script path (`../../scripts` kırığı) | `passed` | marketplace/repo + `pala_paths`; INC fixed focused |
| begin `--goal` DX / complete ticket recovery | `passed` | Turkish error; v3 ticket; recovery msg |
| Focused `test_pala_p0_friction` | `passed` | 8 ok (+1 checklist = 9 ok ingest tur) |
| Live Codex `pala kontrol et` smoke | `passed` | temp `live-08x`; presence/report/discover/HTML; see smoke JSON |
| Hooks `/hooks` UI trust | `configured-not-verified` | insan adımı |
| Tam `verify.py` | `not-run` | scope dışı |

## Live mini A/B re-measure (Pala-Pc, 0.8.1 temp profile)

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Temp profile plugin | `passed` | `CODEX_HOME=…/PalaAB/profiles/live-08x`; `0.8.1+codex.20260808124500` enabled |
| Control live ×2 cold | `passed` | `codex exec` gpt-5.6-terra; S1/S2 ~126s/34s |
| Pala live ×2 cold | `passed` | stdin prompts; S1/S2 ~377s/493s; marketplace scripts used |
| Path `../../scripts` not repeated | `passed` | wrong-path exec count 0; marketplace invokes present |
| Complete fail-closed + close | `passed` | live recovery + quasi record-verification→complete |
| Soft full-product A/B fixed | yok | n=1+1 mini only |
| Hooks UI trust | `configured-not-verified` | bilerek |
| Outputs | `passed` | `outputs/PALA_AB_LIVE_MINI.md` + `PalaAB/meta/live-mini-08x/result.json` |

## M28 Memory-as-Governance (Wave B)

| Task | Sonuç | Not |
| --- | --- | --- |
| M28-T1 pala_debug_gate CLI + hook | `passed` | SessionStart/begin DEBUG GATE |
| M28-T2 Attempts + debug_attempt + fail-closed | `passed` | optional Attempts; complete gate |
| M28-T3 memory_hit_rate proxy | `passed` | cold-start ratio; no % |
| M28-T4 Stop-condition matrix/demo | `passed` | contract; UI trust not passed |
| Focused unittest `test_pala_debug_gate` | `passed` | 17 ok |
| Hooks `/hooks` UI trust | `configured-not-verified` | bilerek |
| Tam `verify.py` | `not-run` | Wave B scope dışı |
| Wave C live A/B | `passed` | early-stop ingest; see Wave C table |

## M27 Install artifact + 0.8.1 prep

| Task | Sonuç | Not |
| --- | --- | --- |
| M27-T1 Fingerprint allowlist (#13) | `passed` | `__pycache__` drift yok |
| M27-T2 Runtime self-audit | `passed` | marketplace `--profile runtime` exit 0 |
| M27-T3 verify `--mode installed` | `passed` | lean marketplace |
| M27-T4 PYTHONUTF8 test | `passed` | parent env idempotent |
| M27-T5 README honesty | `passed` | download = `v0.8.0` while `v0.8.1` `not-run` |
| M27-T0 SessionStart CLI smoke | `passed` | `Pala burada` prefix |
| M27-T0 `/hooks` UI trust | `configured-not-verified` | insan adımı |
| M27 Cold-start ms | `passed` | median_ms=208 (n=3; no %) |
| Doctor after runtime audit | `passed` | healthy/plugin_ready/ready; no false drifted |
| Doctor after source sync (2026-08-08) | `passed` | before: plugin=drifted + UnicodeEncodeError; after Install: healthy/plugin=ready/fp match |
| Doctor JSON cp1254 print | `passed` | `emit_json` UTF-8 buffer; unittest `test_emit_json_survives_cp1254_*` |
| M27 Artifact CI smoke | `configured-not-verified` | YAML landed; Actions needs push |
| M27 Checklist doc | `passed` | `docs/CODEX_PLUGIN_CHECKLIST.md` |
| Issue #13 close | `not-run` | owner-only |
| `v0.8.1` release | `not-run` | owner-only |

## A/B Su Takip backtest (v0.8.0 harness quasi)

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Isolation uninstall/install | `passed` | 5 çift; kontrolde plugin yok |
| Blind score n=5+5 | `passed` | quality_% ≈ 7.3; karar: koşullu |
| Extra pairs (+2) | `passed` | \|diff\|&lt;10 sonrası protokol |
| outputs (historical quasi) | superseded | Wave C live early-stop now primary in `PALA_AB_*` |
| Status HTML a11y | `passed` | landmarks/skip/focus + browser smoke |
| Restore Doctor | `passed` | healthy, plugin=ready, hook_safety=passed |
| Hooks UI trust | `configured-not-verified` | insan adımı |

## Owner canary (0)

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Install-Pala Install | `passed` | 2026-08-08 resync — fingerprint match; experts invoke `attention_required` (core ok) |
| Install-Pala Doctor | `passed` | healthy=True, plugin_ready=True, plugin=ready (core); PS1 exit 2 = experts only |
| Status / memory + sqlite yolu | `passed` | Desktop\Codex\pala.sqlite göründü |
| Codex `/hooks` UI trust | `configured-not-verified` | Terminalden yapılamaz; insan adımı |
| SessionStart hook smoke (CLI) | `passed` | m27-smoke stdin → presence line |

## M25 ortak hafıza

| Task | Sonuç |
| --- | --- |
| M25-T1 Gerçek haritası | `passed` |
| M25-T2 Store sözleşmesi ADR-017 | `passed` |
| M25-T3 CLI/Doctor shared_store | `passed` |
| M25-T4 Cursor ince skill/rules | `passed` |
| M25-T5 Üç yüzey aynı DB testi | `passed` |

## M10 artıkları

| Parça | Sonuç |
| --- | --- |
| RTK pin + rewrite guard (`pala_m10`) | `passed` |
| Context7 / Playwright MCP pin keşif | `passed` (ensure yalnız missing; ağ Doctor’da yok) |
| code-review-graph uv izole suite | `passed` (lock + installer) |
| OpenSpec → aktif ticket bind | `passed` |

## Küçükler

| İş | Sonuç |
| --- | --- |
| DEMO-005 owner handoff | `passed` |
| PR `#5` (0.5A stale) | `passed` (closed) |

## Önceki kapılar (özet)

| Kapı | Sonuç |
| --- | --- |
| GitHub `v0.8.0` | `passed` |
| M26 release | `passed` |
| M24 ajan görevleri | `passed` |
| Tam yerel `verify.py` (önceki tur) | `passed` | 242 test + self-audit |
| Wave A focused unittest | `passed` | 15 ok (installer/self-audit/verify/cold/readme/utf8) |
| Wave B focused unittest | `passed` | 17 ok (`test_pala_debug_gate`) |
