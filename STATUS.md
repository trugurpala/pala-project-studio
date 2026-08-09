# Pala Project Studio — durum (2026-08-09)

Kanıt etiketleri yalnız: `passed` | `not-run` | `blocked` | `configured-not-verified`.

## Özet

Pala, Codex için yerel proje hafızası / plan / doğrulama eklentisidir. Bağlam
penceresi veya kota büyütmez; kısa SessionStart, dosya hafızası ve dürüst
kanıt etiketleriyle vibe coder akışını sürdürür.

| Alan | Değer |
| --- | --- |
| Güncelleme | 2026-08-09 — control center + GOAL; verify `5C16A96F…`; `v0.8.1` yayınlandı |
| Branch | `main` @ `9cf3b0f` (PR #20 merged) |
| Manifest | `0.8.1+codex.20260808124500` |
| Son GitHub release | `v0.8.1` (`passed`) — https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.1 |
| Tag/release `v0.8.1` | `passed` — asset `pala-project-studio-0.8.1-final.zip` SHA-256 `69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53` |
| Repo | public (`passed`) |

## Şu an tek sonraki iş (owner)

1. Codex Work'te `/hooks` trust (insan) — hâlâ `configured-not-verified`.  

Soft full-product "A/B fixed": **yok**.

## Publish phase D — 2026-08-09

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Push `feat/m30-vibe-codex-host-fit` | `passed` | `origin/feat/m30-vibe-codex-host-fit` @ `8484b3a` |
| PR → `main` | `passed` | https://github.com/trugurpala/pala-project-studio/pull/20 merged (`9cf3b0f`) |
| Tag `v0.8.1` | `passed` | on `main` merge commit |
| GitHub release | `passed` | https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.1 |
| Release ZIP asset | `passed` | `pala-project-studio-0.8.1-final.zip`; SHA-256 `69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53` |
| `/hooks` trust | `configured-not-verified` | owner UI; unchanged |

## Control center + GOAL — 2026-08-09

Status HTML kontrol merkezi (Filament yalnız UX esinlenmesi; PHP yok).
Hedef: `GOAL.md` → `docs/GOAL_0_8_1_FINISH.md`.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| GOAL + completeness audit | `passed` | plugins: Pala, Context7, Chrome, product-design |
| Admin Status HTML | `passed` | theme localStorage + sections + feature toggles |
| Landmarks contract test | `passed` | `test_status_html_has_admin_control_landmarks` |
| Tam `verify.py` | `passed` | Ran 362 / OK (skipped=1); reproducible_zip SHA-256 `5C16A96FA7D790969D84E36043D67E789E8ADEF835C29CF451EC0650F40FE65F` |
| Desktop final ZIP (yeniden) | `passed` | `C:\Users\Pala-Pc\Desktop\pala-project-studio-0.8.1-final.zip`; SHA-256 `5C16A96F…E65F`; 143 entries (post-tag control-center build; GitHub `v0.8.1` asset hâlâ tag anındaki `69325B6E…`) |
| `/hooks` trust | `configured-not-verified` | owner |

## M32 Delivery Quality Engine 0.9 + packaging P1 — 2026-08-09

Evidence-first `pala_quality` (plan/init/record/status), Status HTML beş sinyal,
checkpoint `--quality-ticket` fail-closed; portable/install allowlist
`credentials.json` / `id_rsa` / secret-shaped / `*.sqlite` yasak. Push yok;
`/hooks` trust owner.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| `pala_quality` contract tests | `passed` | Ran 21 / OK |
| Packaging secret forbid tests | `passed` | packager + installer |
| Tam `verify.py` | `passed` | Ran 352 / OK (skipped=1); reproducible_zip SHA-256 `69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53` |
| Final Desktop ZIP | `passed` | `C:\Users\Pala-Pc\Desktop\pala-project-studio-0.8.1-final.zip`; SHA-256 `69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53`; 140 entries |
| `/hooks` trust | `configured-not-verified` | owner |
| Push / PR / tag | `passed` | PR https://github.com/trugurpala/pala-project-studio/pull/20 merged; tag+release `v0.8.1` |

## Superpowers continuity (M31-T1) — 2026-08-09

Superpowers skill-only akışından Pala’ya uyarlanan süreklilik ritüeli:
`using-pala` + plan/execute ticket refs + debugging→INC- + verification-before-done.
Skill ≤480 kelime; ayrıntı `references/`. Push yok; `/hooks` trust owner.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Design note vs Superpowers | `passed` | `docs/superpowers/specs/2026-08-09-pala-vs-superpowers-continuity-design.md` |
| Refs using/plan/execute/debugging | `passed` | Pala M*-T* + INC-; Claude-only yok |
| quality-gates verification-before-done | `passed` | labels `passed|not-run|blocked|configured-not-verified` |
| SKILL pointer ≤480 | `passed` | `references/using-pala.md` |
| Focused unittest (continuity + host_fit) | `passed` | continuity contract OK |
| Tam `verify.py` | `passed` | Ran 350 / OK (skipped=1); reproducible_zip SHA-256 `57AC888A7CAB67189E25D83B311466B8FD09C40F48C1A52BA18CD4F5886BEAD1` |
| Final Desktop ZIP | `passed` | `pala-project-studio-0.8.1-final.zip`; SHA-256 `57AC888A7CAB67189E25D83B311466B8FD09C40F48C1A52BA18CD4F5886BEAD1`; 140 entries |
| `/hooks` trust | `configured-not-verified` | owner |
| Push / PR | `not-run` | istenmedi |

## Context restore honesty — 2026-08-09

Dürüst ürün cevabı: Pala host `SessionStart` (`startup|resume|clear|compact`) +
`PreCompact` ile yeniden yönlendirir; mid-turn unutmayı host event olmadan
onarmaz; pencere büyütmez. Ayrıntı: `docs/VIBE_FIRST_SESSION.md` § Codex unuttu.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Codex SessionStart sources (docs) | `passed` | startup/resume/clear/compact; compact sonrası additionalContext |
| Mid-turn re-inject (host event yok) | `passed` (sınır) | Yapamaz; kullanıcı `durumu oku` / yeni sohbet |
| Soft restart SessionStart skip | `configured-not-verified` | Host boşluğu (openai/codex#24228); Pala uydurmaz |
| Matcher `startup\|resume\|clear\|compact` | `passed` | `hooks/hooks.json` |
| PreCompact → needs_reconcile → SessionStart | `passed` | owned-ticket merge `needs_reconcile` düşürmez |
| Cold packet + active + next (resume/compact) | `passed` | SessionStart header’da `next=` her zaman |
| TR docs + skill mid-turn honesty | `passed` | VIBE_FIRST_SESSION / CODEX_SCOPE / SKILL ≤480 |
| Focused unittest (host_fit + PalaHookTests + plugin_experience) | `passed` | Ran 59 / OK |
| Tam `verify.py` | `passed` | Ran 349 / OK (skipped=1); reproducible_zip SHA-256 `6E51FFFB8A5765EA92B05504885D69AD601E2D7E25987FD04F5F88090B548CFC` |
| Final Desktop ZIP | `passed` | `pala-project-studio-0.8.1-final.zip`; SHA-256 `5C2DF2733EE54B82D12B34D93523A2EA4833B7E4C628CBE9D93C0188D5AE0E01`; 136 entries |
| `/hooks` trust | `configured-not-verified` | owner |

## Hook clamp audit (post-SessionEnd=3) — 2026-08-09

Kaynak: [Codex Hooks docs](https://developers.openai.com/codex/hooks) + `openai/codex` `discovery.rs` (`SESSION_END_MAX_TIMEOUT_SEC=3` yalnız SessionEnd).

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Codex timeout clamp (tüm eventler) | `passed` | Yalnız **SessionEnd** max 3s; diğerleri default 600, alt sınır 1 — üst clamp yok |
| SessionStart `timeout: 10` | `passed` | Clamp riski yok |
| PreToolUse `timeout: 5` | `passed` | Clamp riski yok |
| PreCompact `timeout: 10` | `passed` | Clamp riski yok |
| Stop `timeout: 10` | `passed` | Clamp riski yok |
| SessionEnd `timeout: 3` | `passed` | Max ile eşit; clamp uyarısı üretmez |
| `additionalContextLimit` yalnız SessionStart=1800 | `passed` | Desteklenen event; Stop/PreCompact/SessionEnd’de yok (yanlış yerde uyarı üretir) |
| Açık GitHub clamp/timeout bug (openai/codex) | `passed` | SessionEnd clamp feature (merged); açık “başka event clamp” bug’ı bulunamadı |
| Peer plugin timeouts | `passed` | Figma vb. çoğunlukla timeout alanı yok (Codex default 600) |
| Source = cache = marketplace `hooks.json` | `passed` | SHA-256 `E3D20248…CB8E` üçü de; SessionEnd=3 |
| Focused unittest (host_fit + self_audit + plugin_experience + PalaHookTests) | `passed` | 44 + 18 OK |
| Doctor (çekirdek) | `passed` | Repair sonrası `healthy=True` / `plugin=ready` / `hook_safety=passed`; uzmanlar `attention_required` (blocker değil) |
| Codex CLI hooks.json validate komutu | `not-run` | CLI’de ayrı validate yok; discovery runtime’da |
| `/hooks` UI zero-warning + trust | `configured-not-verified` | Owner tıklaması gerekir |
| Final Desktop ZIP | `passed` | `pala-project-studio-0.8.1-final.zip`; SHA-256 `F21E355E4B87DC7B8AAF039EA4AF61BECFA7DECB77C2E6C48A1A74729AECD2D4`; 132 entries |

**Sonuç:** SessionEnd=3 sonrası ek timeout/clamp düzeltmesi gerekmedi; kaynak değişmedi.

## SessionEnd timeout fix — 2026-08-09

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Root cause | Codex SessionEnd max **3s**; kaynak `timeout: 10` clamp uyarısı üretiyordu | [Hooks docs](https://developers.openai.com/codex/hooks) |
| `hooks.json` SessionEnd `timeout: 3` | `passed` | Handler yalnız yerel heartbeat |
| Focused unittest (host_fit + self_audit + plugin_experience + SessionEnd) | `passed` | — |
| Tam `verify.py` | `passed` | Ran 321 / OK; reproducible_zip SHA-256 `77A02501DC47B2F206FB3F5E651625182B2B0D1DDB7F739BBA13CE4C7CBEE7D4` |
| Portable ZIP hooks-timeout-fix | `passed` | `artifacts/portable/pala-project-studio-0.8.1-hooks-timeout-fix.zip`; Desktop kopyası; SHA-256 `77A02501DC47B2F206FB3F5E651625182B2B0D1DDB7F739BBA13CE4C7CBEE7D4`; 132 entries |
| Cache / `/hooks` UI after Repair | `passed` (cache) / `configured-not-verified` (UI trust) | `codex plugin remove`+`add` → cache SessionEnd `timeout: 3`; `/hooks` trust hâlâ insan |
| `ensure_codex_install` cache fingerprint refresh | `passed` | aynı version’da marketplace≠cache → remove+add; unittest OK |

## Owner sınırları (bilerek)

| Konu | Etiket |
| --- | --- |
| Hooks UI `/hooks` trust | `configured-not-verified` |
| Soft “A/B fixed” | yok |
| Tam source `verify.py` | `passed` (2026-08-09 SessionEnd timeout fix; 321 tests + reproducible ZIP) |
| Push / PR / tag / `gh release` (bu ajan turu) | yapılmadı (owner) |
| Marketplace Install sync (diğer makineler) | `not-run` |
| Doctor after Repair (bu makine) | `passed` (çekirdek `plugin=ready` / `healthy=True`) |

**Hatırlatma:** Doctor `hook_safety=passed` yalnızca dosya sözleşmesidir. Codex
`/hooks` UI trust ayrı insan adımıdır.

## Vibe-install UX (Codex-native first) — 2026-08-09

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Docs native-first (`VIBE_INSTALL` / first-session / README / `KUR.md`) | `passed` | Birincil = 2 CLI; ZIP ikincil; Plus-paste / ZIP-upload mitleri yasak |
| Marketplace `path: "."` | `passed` | `./` ve boş path reddi contract’ta |
| `Kur.cmd` + installer 3-adım Türkçe next | `passed` | Bypass → Install-Pala; Plugins / `/hooks` / yeni sohbet |
| Focused unittest (plugin_experience + host_fit + self_audit) | `passed` | Ran 43 / OK |
| Portable ZIP vibe-install (yerel, publish yok) | `passed` | `artifacts/portable/pala-project-studio-0.8.1-vibe-install.zip`; Desktop kopyası; SHA-256 `18DA984F548B54C450016D46135B6920CF382E62C1446F3E88BE0912C06ABA36`; 132 entries |
| Hooks UI `/hooks` trust | `configured-not-verified` | insan |
| Tag/release `v0.8.1` | `passed` — asset `pala-project-studio-0.8.1-final.zip` SHA-256 `69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53` |
| Soft A/B fixed | yok | — |

## M30 — Vibe Codex host-fit + checkpoint fix

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Codex limits doc (2026-08-09) | `passed` | ~1000-token additionalContext hard cap |
| Dual SessionStart budget | `passed` | char 1800 + approx-token ≤900; cold packet öncelikli |
| Thin skill + `kontrol-et.md` | `passed` | SKILL ≤480 words |
| Checkpoint ignores `.codex/plugin-data/` | `passed` | v3 ticket gürültüsü sayılmaz; focused checkpoint test OK |
| Focused unittest (host-fit + self_audit + tokens + checkpoint) | `passed` | Ran 16 / OK (önceki M30 tur) |
| `verify.py --mode installed` | `passed` | önceki M30 turunda exit 0 |
| Gate0 p0-smoke | `passed` | 9/9; SHA-256 `6FE7A3EC63D850BE8DE145EB260A0E401170D08FAB4C85A1BC5C50DD69680AEB` |
| Portable ZIP m30-local (önceki) | `passed` | `artifacts/portable/pala-project-studio-0.8.1-m30-local.zip`; SHA-256 `6270BC34F20678AD3C3A25381DA727AEBB4C4D173292D021CE4E219242ABAE1E`; 130 entries |
| Honesty contract (thin skill ticket wording) | `passed` | Test accepts SKILL `only the active ticket`; `…section` stays in memory-contract ref; `scripts.test_pala_tools` 68/OK |
| Tam source verify | `passed` | Ran 320 / OK; reproducible_zip SHA-256 `C5647286C63A889CC5B41C192F53E3A57FBEDD7810FFFDF464015C49B99E2A48` |
| Soft A/B fixed | yok | — |
| Doctor install fingerprint after Repair | `passed` | `Install-Pala -Mode Repair` → Doctor `plugin=ready` / `healthy=True` (çekirdek); `/hooks` hâlâ insan |
| Honesty P1 (kayıtsız SessionStart + drifted next-step + limit semantiği) | `passed` | VIBE docs; `plugin_next_step`; CODEX_SCOPE char≠host-token; uninstall user-added refuse |

Plan/spec: `docs/superpowers/plans/2026-08-09-vibe-codex-host-fit.md`,
`docs/superpowers/specs/2026-08-09-m30-close-081-local-release-design.md`.

## Kurulum / güncelleme (kısa)

**Birincil — Codex-native CLI** (ZIP Plugins’e yüklenmez):

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

**İkincil — ZIP / tam toolkit:** kök `Kur.cmd` veya:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

- Doctor çekirdek: `plugin_ready` / `healthy` beklenir; yerel edit sonrası `plugin=drifted` (source≠install) → `Install-Pala -Mode Repair` / Update / marketplace sync (`plugin_next_step`); sağlıklı iddia etme.  
- `hook_safety=passed` ≠ `/hooks` trust.  
- Kaynak ağaçta: `py -3 scripts/verify.py --mode installed` (marketplace varken).  
- Vibe kurulum: `docs/VIBE_INSTALL.md`; ilk oturum: `docs/VIBE_FIRST_SESSION.md`.  
- Release adımları: `docs/RELEASE_0.8.1_CHECKLIST.md`.

## Önceki dalgalar (özet)

Ayrıntılı tablolar `PROGRESS.md` ve `CHANGELOG.md` içinde.

- **M29** Gate0 + cold packet + cmd memory: kaynak `passed`; mini live A/B path/complete odaklı `passed`; soft full A/B yok.  
- **M28** debug gate: `passed` (hooks UI değil).  
- **M27** install artifact / fingerprint #13: `passed`.  
- **M25** shared memory ADR-017: `passed`.  
- **Wave C** live A/B early-stop: conditional-keep (handoff); hız zaferi yok.  
- **v0.8.0** GitHub release: `passed`.

## Ürün vaadi (kısa)

Pala yapar: presence, tek sonraki iş, cwd-safe scriptler, DEBUGGING, Status HTML,
fail-closed complete, cold packet, cmd memory, shared local sqlite.

Pala yapmaz: context/kota büyütme; hook içinden test/build/ağ; Cursor’da “Codex
plugin kurulu” iddiası; ölçülmemiş hız/token yüzdesi.
