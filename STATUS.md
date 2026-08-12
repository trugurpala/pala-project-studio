# Pala Project Studio — durum (2026-08-11)

## PALA 1.0 generated/read-model projection

Current canonical identity is `product_version=1.0.0-local-rc` and
`plugin_version=1.0.0-local-rc+codex.20260811000000`; source is
`product-identity.json`. `M60-T1` canonical olarak `DONE` ve WorkflowStore
`completed`: caller-supplied command/exit authority kaldırıldı; 10/10 release
check yalnız `pala-quality-runner` tarafından gerçek exit, output digest ve
verification basis ile üretildi. Fresh canonical suite 536 test (1 controlled
skip), Pytest 535 passed (1 skip, 44 subtests), coverage 75%, Playwright 1/1,
critical Mypy, touched Ruff, Bandit High=0, pip-audit=0, source/portable/
installed/Doctor ve official validators `passed`. Exact reproducible ZIP
`3424FB0AAE6EEFBEBE937A6EB0D065705844E846737C15A4C3301E518DDE5D54`
(205 entry); schema-v2 manifestte `quality_execution_authority` ve 10-case
forgery regression kanıtı var. Bu STATUS generated read modeldir; canonical
authority değildir. Remote publish ve real remote deploy `not-run`.

Tek sonraki iş: `not-run` — owner yerel RC’yi inceleyebilir; yeni ürün işi ayrı
ticket gerektirir.

## R6 historical status

`R6-M0` `passed`. External single-host runtime root ve migration uygulaması
yerel testlerde kanıtlandı (`18` focused + `188` affected integration, exit 0).
Codex CLI `0.147.0` ile invocation-local kısıtlı profil Pala runtime root'una
yazdı; `.git` ve `.codex` yazıları `UnauthorizedAccess` ile reddedildi.

`R6-M1` de `passed`: WorkflowStore kalıcı TaskContract acceptance semantics
kullanıyor; explicit acceptance olmadan veya salt legacy `passed` ile DONE
oluşmuyor. Taze focused/affected integration kanıtı: 196 test, exit 0.

`R6-M2` `passed`: yalnız mevcut Pala Quality Engine ledger'ındaki required,
current, exit-code `0` kanıtlar explicit acceptance `quality_check_ids` ile
eşleşir. Partial veya unmapped evidence completion yapamaz. Taze kanıt: 196 test,
exit 0.

`R6-M3` `passed`: acceptance'sız legacy `completed`/`done` task kaynakları
değişmeden kalır; external canonical kopya typed conflict ile `needs_decision`
olur. Taze kanıt: 19 focused + 197 affected integration test, exit 0.

`R6-M4` `passed`: canonical TaskContract dependency DAG, write/deny scope,
tekrarlanan verification bütçesi ve dirty/orphan recovery completion yolunda
fail-closed. Taze kanıt: 88 focused + 199 affected integration test, exit 0.

`R6-M5` `passed`: handoff, cold packet ve state-core workflow consumers workflow
projection yoksa tek canonical aktif TaskContract'tan read-only türetilir;
belirsizlik fail-closed kalır. Taze kanıt: 27 focused + 202 affected integration
test, exit 0.

`R6-M6` `passed`: AGENTS ve Pala skill canonical report/context → claim →
Quality → acceptance → DONE zincirini; TaskContract/WorkflowStore/Quality Engine
authority ayrımını ve generated STATUS/handoff/cold packet read-model sınırını
açıkça tanımlar. Taze kanıt: 36 focused + 203 affected integration test, exit 0;
diff review `passed`.

`R6-M7` `passed`: GitHub allowlist'i prefix yerine complete argv şeklini
doğrular; `gh api` method/body flags ile Git branch/remote mutasyonları
reddedilir. Taze kanıt: 4 focused + 141 affected integration test, exit 0; diff
review `passed`.

`0.9.0` local candidate: manifest/source identity is current; published
`v0.8.1` remains historical. Push, tag, release, and deploy are `not-run`.

`R6-M8` `passed`: `0.9.0` local candidate kimliği manifest/README/STATUS
yüzeylerinde tutarlı; `v0.8.1` tarihsel release olarak korunur. Source full
gate 485 test (1 controlled skip) ve reproducible ZIP SHA-256
`D048B6ED3E4453CF212037E9F514D1DA3D6FE146FED98B5EBC9CDFBD93FB8573`;
portable clean-extract ve installed-profile gates `passed`. Remote actions
`not-run`. System plugin/skill validators `passed` via the machine-local
Pala validation environment (PyYAML 6.0.3); global Python unchanged.

Tek sonraki iş: `M47-T1` — Quality Hardening Ruff baseline'ını mevcut
packaging/portable sözleşmesini bozmadan ölçmek. Remote release kararı hâlâ
owner'a aittir.

`R6-M8-PACKAGE` `passed`: PyYAML 6.0.3 machine-local validation environment
ile source full gate, portable clean-extract, installed-profile, system plugin
validator ve system skill validator çalıştı. Teslim ZIP'i yerel artefakttır;
remote publish `not-run`.

Branch: `codex/r6-safe-runtime-authority`. Commit, push, PR, merge, tag, release
ve deploy `not-run`.

Kanıt etiketleri yalnız: `passed` | `not-run` | `blocked` | `configured-not-verified`.

## Özet

Pala, Codex için yerel proje hafızası / plan / doğrulama eklentisidir. Bağlam
penceresi veya kota büyütmez; kısa SessionStart, dosya hafızası ve dürüst
kanıt etiketleriyle vibe coder akışını sürdürür.

| Alan | Değer |
| --- | --- |
| Güncelleme | 2026-08-10 — M45 tamamlandı; 0.8.2 yerel yayın adayı ve gerçek yükseltme kanıtları hazır |
| Branch | `main` @ `58fcf61`; çalışma ağacında kaynak ve plan değişiklikleri var |
| Manifest | `0.8.2+codex.20260810070000` |
| Son GitHub release | `v0.8.1` (`passed`) — https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.1 |
| Tag/release `v0.8.1` | `passed` — asset `pala-project-studio-0.8.1-final.zip` SHA-256 `69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53` |
| Tag/release `v0.8.2` | `not-run` — yalnız yerel yayın adayı; commit/push/tag/release yetkisi yok |
| Repo | public (`passed`) |

## Şu an tek sonraki iş

`M47-T1` Quality Hardening kartı için önce Ruff baseline/failing evidence
alınacak; araç kurulumu, production dependency ve packaging/portable değişikliği
bu kanıt olmadan yapılmayacak. Commit/push/tag/release hâlâ ayrı owner yetkisi
ister ve şu anda `not-run`.

## M45-T6 sonucu

## M46-T1 sonucu

- Tamamlanan v3 ticket artık yalnız eşleşen, clean legacy v2 workflow'dan
  `active_ticket` ve `goal` alanlarını temizler. Dış owner `next_action` ile
  doğrulama kanıtı korunur; farklı ticket, dirty veya sahipliği uyuşmayan kayıt
  fail-closed olarak değiştirilmez.
- Hooks semantiği `additionalContextLimit` için host spill eşiği (1800) ile
  Pala'nın mesaj char (1800) ve yaklaşık token (900) ürün bütçelerini ayırır.
  `/hooks` UI trust hâlâ `configured-not-verified`.
- Yerel kapılar `passed`: dar bellek/host-fit/cold-packet/P0/UX paketi (109),
  P0 smoke, tam unittest discovery, source verify ve self-audit.
- OpenSSF Scorecard workflow'u yalnız weekly/manual gözlemdir; SHA-pinned SARIF
  yüklemesi local kalite veya release kararı değildir. İlk uzak çalıştırma
  push yapılmadığı için `not-run`.

- Release-tier kalite kapısı `passed`: `427` test geçti (`1` kontrollü skip),
  code audit, source/portable/installed verify ve sistem plugin/skill validatorları geçti.
- Gerçek local `Update` ve `Doctor` `passed`; kurulu manifest
  `0.8.2+codex.20260810070000`, Doctor `healthy=True`, plugin ve Codex `ready`.
- Final yerel artifact: `dist/pala-project-studio-0.8.2-final.zip`, `168` entry,
  `386154` byte, SHA-256
  `5C95EC50611D1FE06B43D7DA421A7934465D88BC2F19B9BD49AECC1EF9C10350`.
- Açık sohbet eski plugin metadata/cache'iyle başladığı için yeni skill/hook yüzeyi
  yeni Codex sohbetinde yüklenir. `/hooks` kullanıcı trust adımı
  `configured-not-verified` olarak ayrı kalır.

## M45 gerçek yükseltme kanıtı

- `v0.8.0 managed -> 0.8.2`: `passed`.
- `v0.8.0 verified legacy -> 0.8.2`: `passed`.
- `v0.8.1 managed -> 0.8.2`: `passed`.
- Kanıt: `artifacts/upgrade-compat/m45-real-release-matrix.json`.

## M44-T1 sonucu

- Eksik `argparse` ve `tomllib` importları sözleşme testleriyle sabitlendi.
- Session'sız context eski M43-T5 yerine M44-T1 workflow kaydına uzlaştırıldı.
- `419` test `passed` (`1` kontrollü skip); code audit, source verify, portable
  clean extract, gerçek local Update + Doctor ve installed verify `passed`.
- Final yerel artifact: `dist/pala-project-studio-m44-t1-final.zip`, SHA-256
  `0C3BA6738A95044BFC99173205F4A118E16168CDC460FA34042A97F54FE32B3F`.

M43 kartları bağımlılık sırasıyla kilitlidir. Yeni bir bulgu kartların sırasını
kendiliğinden değiştirmez: ilgili ticket `blocked` olur ve gerekiyorsa
`DEBUGGING.md` içinde incident açılır. Commit, push, PR, tag, release ve deploy
bu planın dışındadır; her biri ayrı owner yetkisi ister.

`/hooks` trust insan adımı olarak ayrı kalır: `configured-not-verified`.

Soft full-product "A/B fixed": **yok**.

## M43-T8 — Milestone paketi ve owner teslimi (2026-08-10)

M43-T1…T7'nin güncel kaynak ağacındaki sonucu, aynı SHA-256'ya ulaşan kaynak ve
portable paket yüzeylerinde yeniden doğrulandı. Installed kontrolü gerçek
marketplace kurulumunu değiştirmeden, installer'ın ürettiği geçici bir kurulum
kopyasında çalıştırıldı. Bu yerel doğrulama yayın ya da `/hooks` UI güveni yerine
geçmez.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Açık Python test discovery | `passed` | 417 test, 1 skipped; exit 0 |
| Source verify | `passed` | reproducible source paketi; final arşivle aynı SHA-256 (teslim çıktısında kaydedildi) |
| Portable build + clean extract | `passed` | `dist/pala-project-studio-m43-t8-final.zip`; 166 entry; source ile aynı SHA-256 |
| Installed runtime | `passed` | installer ile oluşturulmuş geçici kurulum kopyasında runtime self-audit; gerçek marketplace değiştirilmedi |
| Static code audit | `passed` (hard security) | 0 hard finding; `checkpoint_work` ve `doctor_installation` için 2 advisory bakım adayı |
| M43-T8 milestone quality ledger | `passed` | unit + source verify + yerel code audit, 3/3 zorunlu kapı |
| Pala state Doctor | `passed` | Doctor çalışırken aktif v3 `M43-T8` oturumu sağlıklıydı; eski v2 `M43-T5` workflow kaydı korunarak `needs_reconcile=true` görünüyordu |
| Commit/push/PR/tag/release/deploy/remote publish | `not-run` | owner yetkisi verilmedi |
| `/hooks` UI trust | `configured-not-verified` | insan/owner UI adımı |

## M43-T1 — Sıfırdan uzlaştırma ve kilitli baseline (2026-08-09)

Eski M31 v2 workflow ve v3 ticket kaydı, canlı `main` / çalışma ağacından
farklı bir checkpoint'e bağlıydı. M31 kaydı silinmedi veya M43 kanıtına
taşınmadı: `checkpointed`, `superseded_by=M43-T1` olarak korunup sahibi
bırakıldı. Yeni M43 workflow'u sıfır kanıtla başlatıldı; stale-context uyarısı
artık yoktur.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| M43 workflow başlangıcı | `passed` | `pala_state begin`; `active_ticket=M43-T1`, reconciliation `false` |
| Doküman kaydı | `passed` | `pala_state validate --cwd .` |
| M31 tarihsel kanıt | `passed` (korundu) | M43'e taşınmadı; superseded checkpoint kaydı |
| Güncel source/portable/installed kapıları | `not-run` | M43-T2 ve ileriki ticket'ların kanıtı |
| `/hooks` UI trust | `configured-not-verified` | owner UI adımı; unchanged |

## M43-T3 — Süre sınırlı süreç ve smoke sınırı (2026-08-10)

Beş dış süreç sahibi fixed argv, `shell=False` ve sınırlı timeout kullanır.
Timeout artık graph için `124`, cold-start için `blocked`, P0 child süreçlerinde
başarısız sonuç ve verify için fail-closed gate olarak görünür. P0 smoke adımları
ayrıldı; `run_smoke` review eşiğinin altındadır.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Dar timeout/smoke sözleşmeleri | `passed` | 6 test; timeout görünürlüğü ve audit sınırı |
| P0 smoke | `passed` | `py -3 scripts/pala_p0_smoke.py`; 10 satır kanıt |
| Static code audit | `passed` (hard security) | süreç hijyeni `passed`; 10 advisory bakım adayı |
| Açık Python test discovery | `passed` | 409 test, 1 skipped; exit 0 |
| Source verify | `passed` | reproducible ZIP SHA-256 `48AA68FB1B08B3DB4ED8288D5FB3F0392B0D27A57FFAC5EA1969FA58E35B2508` |
| Portable / installed runtime | `not-run` | M43-T8 milestone sınırı |

## M43-T4 — State yaşam döngüsü ve CLI sahipliği (2026-08-10)

`pala_state.py` compatibility facade oldu; lifecycle çekirdeği, belge/doctor
katmanı ve CLI ayrı sahiplere bölündü. Session-key checkpoint artık eşleşen v2
workflow kaydını da kapatır; sonraki `begin` ikinci manuel checkpoint istemez.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Session checkpoint lifecycle sözleşmesi | `passed` | v2 + v3 kayıtları birlikte checkpointed |
| State/P0/installer dar regresyonu | `passed` | facade, lifecycle ve fail-closed davranış korunuyor |
| Static code audit | `passed` (hard security) | state modül adayı kalmadı; 8 advisory kaldı |
| Açık Python test discovery | `passed` | 410 test, 1 skipped; exit 0 |
| Source verify | `passed` | reproducible ZIP SHA-256 `9E5011542344A2E5F3D51AB14B842F432ACD6A31647FBC0A06ED72571AA30D64` |
| Portable / installed runtime | `not-run` | M43-T8 milestone sınırı |

## M43-T5 — Installer integrity ve transaction sahipliği (2026-08-10)

`pala_installer.py` uyumluluk cephesi oldu. Bundle admission ve exact-file
preservation `pala_installer_integrity.py`ye; stage/activate/rollback/uninstall
işlemleri `pala_installer_transaction.py`ye; shared state ve doctor/Codex
gözlemi ayrı sahiplere taşındı. Yeni runtime sibling'ları paket mutasyonundan
önce zorunlu olarak doğrulanır.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Missing-helper fail-closed sözleşmesi | `passed` | state ve installer runtime sibling'ları `validate_bundle()` tarafından staging öncesi reddedilir |
| Installer + static-audit dar regresyonu | `passed` | 67 test, 1 skipped; added/changed/symlink/bytecode ve rollback korunuyor |
| Static code audit | `passed` (hard security) | installer modül boyutu adayı yok; 7 advisory sonraki ticket'larda |
| Açık Python test discovery | `passed` | 412 test, 1 skipped; exit 0 |
| Source verify | `passed` | reproducible ZIP SHA-256 `199F2AC771FB5913822D9673A70A2A24FCCACC8996AB44328296C7C6F790B59A` |
| Portable / installed runtime | `not-run` | M43-T8 milestone sınırı |

## M43-T6 — Session, cold packet ve hook sahipliği (2026-08-10)

`pala_cold_packet.py` ile `pala_hook.py` uyumluluk cepheleri olarak kaldı;
packet assembly ve SessionStart context oluşturma ayrı sahiplerde. Bu ayrım tek
Git snapshot'ını, kısa context bütçesini ve testlerdeki injected/mocked helper
sözleşmesini korur. Eksik packet/hook sibling'i bundle staging'inden önce
reddedilir. Hook test, build, kurulum veya ağ çağrısı başlatmaz.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Packet/hook ownership sözleşmeleri | `passed` | facade API, tek Git snapshot ve SessionStart davranışı korunuyor |
| Missing-helper fail-closed | `passed` | packet ve hook session sibling'ları install mutasyonundan önce zorunlu |
| Açık Python test discovery | `passed` | 415 test, 1 skipped; exit 0 |
| Static code audit | `passed` (hard security) | 0 hard finding; 4 advisory bakım adayı ayrı sahipli kartlarda |
| Source verify | `passed` | reproducible ZIP SHA-256 `7E5395297730F3119DD4F10208E48E058533CE0C3F4ED219DF9F627DFAFA3F57` |
| M43-T6 milestone quality ledger | `passed` | unit + source verify + yerel code audit, 3/3 zorunlu kapı |
| Portable / installed runtime | `not-run` | M43-T8 milestone sınırı |
| `/hooks` UI trust | `configured-not-verified` | insan/owner UI adımı; kaynak davranışı bunu `passed` yapmaz |

## M43-T7 — Status görünümü ve CSS sahipliği (2026-08-10)

`pala_view.py` public `render()` uyumluluk cephesi oldu. CSS üç küçük style
bölümüne, model/document orkestrasyonu ise `pala_view_layout.py` içindeki
sınırlı sahiplerine ayrıldı; existing section markup `pala_view_sections.py`de
kaldı. Status HTML'in privacy, keyboard, delivery-decision, localStorage-only
ve no-progress-claim sözleşmeleri korundu. Yeni runtime sibling'lar eksikse
installer staging öncesi fail-closed kalır.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| View ownership + HTML sözleşmeleri | `passed` | facade, CSS, layout ve section sorumlulukları ayrı; public render davranışı korunuyor |
| Missing-view-helper fail-closed | `passed` | style/layout sibling'ları eksik bundle install öncesi reddediliyor |
| Açık Python test discovery | `passed` | 417 test, 1 skipped; exit 0 |
| Static code audit | `passed` (hard security) | view/CSS adayları kapandı; 2 advisory state/installer kart sahiplerinde kaldı |
| Source verify | `passed` | reproducible ZIP SHA-256 `C07EC20C5D163B67B6946AE0224F89A9DEA6FDED2B257A8D3FF459DEDA2087AB` |
| M43-T7 milestone quality ledger | `passed` | unit + source verify + yerel code audit, 3/3 zorunlu kapı |
| Portable / installed runtime | `not-run` | M43-T8 milestone sınırı |
| `/hooks` UI trust | `configured-not-verified` | insan/owner UI adımı; unchanged |

## M43-T2 — Güncel kaynak baseline kapısı (2026-08-10)

M33–M42 çalışma ağacı tarihsel ledger sonucu devralınmadan yeniden çalıştırıldı.
Zorunlu iki milestone kapısı `M43-T2` ledger'ında geçti. Static audit güvenlik
ihlali bulmadı; 11 bakım adayı `attention_required` olarak kaldı ve M43-T3…T7
ile sahipli çözüm sırasına bağlıdır.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| Açık Python test discovery | `passed` | `py -3 -m unittest discover -s scripts -p test_*.py`; exit 0 |
| Source verify | `passed` | `py -3 scripts/verify.py --mode source`; exit 0 |
| Static code audit | `passed` (hard security) | 0 hard finding; 11 advisory maintainability adayı |
| Portable / installed runtime | `not-run` | M43-T8 milestone sınırı |
| `/hooks` UI trust | `configured-not-verified` | owner UI adımı; unchanged |

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

## M33 — Control Panel Modularity + Quality Ratchet (2026-08-09)

Status renderer üç görünür sorumluluğa ayrıldı: ana renderer, güvenli section /
delivery-card markup'ı ve mevcut statik page shell. Harici UI paketi, server,
ağ veya yeni runtime bağımlılığı eklenmedi.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| View contract + code audit tests | `passed` | 15 test; delivery kararları, privacy, keyboard ve 800 satır budget |
| Static code audit | `passed` | hard-security bulgusu yok; `pala_view.py` artık module-limit adayı değil |
| Source verify | `passed` | JSON, syntax, static audit, contract tests, reproducible package, self-audit |
| Quality ledger ticket gate | `passed` | Açık `scripts` discovery + yeni source verify; 2/2 zorunlu kanıt |
| Ara portable ZIP | `passed` | 146 entry; clean extract + runtime self-audit |
| Ara ZIP ile Repair + installed verify | `passed` | marketplace runtime audit + self-audit |
| Ruff / Bandit hedefli kontrol | `passed` | yeni/ayrılan view dosyalarında; eski style backlog'u gizlenmedi |
| Push / PR / tag / release / deploy | `not-run` | ayrı owner yetkisi gerekir |
| `/hooks` UI trust | `configured-not-verified` | insan adımı; unchanged |

## M34 — Core install truthfulness (2026-08-09)

Core Pala artık varsayılan Repair/Install/Update sırasında ağdan uzman araç
indirmeyi başlatmaz. İsteğe bağlı araçlar yalnız `-InstallExperts` ile seçilir;
onların sonucu çekirdeğin sağlıklı kurulduğu bilgisini veya exit code'unu
maskeleyemez.

| Kapı | Sonuç | Not |
| --- | --- | --- |
| PowerShell parse + expert installer contract | `passed` | 16 test; explicit opt-in, nonfatal expert result, model guard, honest expert readiness |
| Gerçek varsayılan Repair | `passed` | exit 0; `healthy=True`, `plugin=ready`, Codex `ready`, experts `False` / prerequisites `True`; expert download yok |
| Kullanıcı dosyası / kurulu runtime audit | `passed` | Repair sonrası `verify.py --mode installed` |
| Uzman araçların explicit kurulumu | `not-run` | ayrı kullanıcı isteği + ağ/indirme yetkisi gerekir |
| `/hooks` UI trust | `configured-not-verified` | insan adımı; unchanged |

## M35 — Quality discovery boundary (2026-08-09)

`pala_quality.py` now owns only policy, ledger, gate decision and CLI work;
new `pala_quality_discovery.py` owns bounded project/Git observation. This
does not execute a project command, a scanner, a network call, or a hook.

| Gate | Result | Note |
| --- | --- | --- |
| Focused quality + audit contracts | `passed` | 31 tests; timeout and shell-free Git discovery covered |
| Static code audit | `passed` | hard-security 0; `pala_quality.py` 688 lines; its timeout list clear |
| Source verify | `passed` | JSON, syntax, contracts, reproducible package, self-audit |
| Portable verify | `passed` | clean extract + runtime self-audit; r9 SHA-256 `D9CB7103…D47FDA` |
| Repair + installed verify | `passed` | marketplace runtime audit; Doctor core `healthy=True`, plugin `ready` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

## M36 — Modified install tree safety (2026-08-09)

The installed bundle now fails closed when a user-added or changed file is
present. The safety boundary treats a changed Pala file as user material too:
Repair and Update cannot safely decide to overwrite it.

| Gate | Result | Note |
| --- | --- | --- |
| Installer preservation contracts | `passed` | 49 tests; added/changed/bytecode/update-before-Codex cases covered |
| Doctor / Repair / Update behavior | `passed` | `modified`, `changed=false`; explicit recovery message; no Codex mutation |
| Static code audit | `passed` | hard-security 0; installer size remains an explicit advisory |
| Source verify | `passed` | JSON, syntax, contracts, reproducible package, self-audit |
| Portable verify | `passed` | clean extract + runtime self-audit; r10 SHA-256 `D81C797B…0A325F` |
| Repair + installed verify | `passed` | marketplace runtime audit; Doctor core `healthy=True`, plugin `ready` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

## M37 — State Git timeout boundary (2026-08-09)

Pala state discovery and checkpoint observation now use one resolved Git helper:
fixed arguments, no shell, and a five-second bound. Missing or timed-out Git
keeps the prior conservative fallback rather than blocking the local workflow.

| Gate | Result | Note |
| --- | --- | --- |
| State Git timeout contracts | `passed` | fixed argv, `shell=false`, timeout, missing-Git fallback |
| Static code audit | `passed` | hard-security 0; `pala_state` no longer appears in timeout list |
| Source verify | `passed` | JSON, syntax, contracts, reproducible package, self-audit |
| Portable verify | `passed` | clean extract + runtime self-audit; r11 SHA-256 `E5D019FC…8D1095` |
| Repair + installed verify | `passed` | marketplace runtime audit; Doctor core `healthy=True`, plugin `ready` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

## M38 — Salt-okunur observation boundary (2026-08-09)

Cold-packet Git observation now has a small, separate owner. Git/UV/origin
reads use a resolved executable, fixed argv, `shell=false`, and a five-second
bound. A `git status` timeout now produces `dirty=null` and partial observation,
not a clean worktree; the packet asks for Git verification before continuing and
reuses that exact snapshot for its capability surface.

| Gate | Result | Note |
| --- | --- | --- |
| Focused observation + audit contracts | `passed` | timeout, missing binary, partial snapshot, GitHub fallback, one snapshot |
| Static code audit | `passed` | hard-security 0; cold packet is below the 800-line threshold; 5 timeout candidates remain explicit |
| Source verify | `passed` | JSON, syntax, contracts, reproducible package, self-audit |
| Portable verify | `passed` | clean extract + runtime self-audit; r12 SHA-256 `BD8FDEBA…115C30` |
| Repair + installed verify | `passed` | marketplace runtime audit; Doctor core `healthy=True`, plugin `ready` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

## M39 — State Git/checkpoint ownership (2026-08-09)

State Git/checkpoint observation is now owned by `pala_state_git.py`.
`pala_state.py` preserves the public helpers and keeps workflow/document policy,
SQLite lifecycle, and CLI decisions. A truncated bundle without that sibling is
rejected before installation rather than producing a later runtime import error.

| Gate | Result | Note |
| --- | --- | --- |
| Focused state + installer + audit contracts | `passed` | 157 tests; state behavior, bounded Git, package membership, missing-helper failure |
| Static code audit | `attention_required` | hard-security 0; `pala_state.py` is 1539 lines and remains explicit modularity work |
| Source verify | `passed` | JSON, syntax, contracts, reproducible package, self-audit |
| Portable verify | `passed` | clean extract + runtime self-audit; r13 SHA-256 recorded with artifact |
| Repair + installed verify | `passed` | marketplace runtime audit; Doctor core `healthy=True`, plugin `ready` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

## M40 — Installer external Codex bridge (2026-08-09)

Codex CLI, marketplace, cache, and migration behavior is now separately owned
by `pala_installer_codex.py`. The installer core retains exact bundle integrity,
user-file protection, and filesystem rollback. Its sibling loader prevents a
directly-loaded source, portable, or installed copy from sharing another copy's
bridge module.

| Gate | Result | Note |
| --- | --- | --- |
| Focused installer + state + runtime contracts | `passed` | 173 tests; rollback, missing bridge, sibling loader, explicit shell-free timeout |
| Static code audit | `attention_required` | hard-security 0; installer core is 1220 lines and remains visible modularity work |
| Source verify | `passed` | JSON, syntax, contracts, reproducible package, self-audit |
| Portable verify | `passed` | clean extract + runtime self-audit; r14 SHA-256 recorded with artifact |
| Repair + installed verify | `passed` | marketplace runtime audit; Doctor core `healthy=True`, plugin `ready` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

## M42 — Quality policy ownership (2026-08-09)

The deterministic quality-plan policy now has its own leaf owner,
`pala_quality_policy.py`. The public `pala_quality.py` surface still exposes
plan discovery, ledger, gate decision, and CLI behavior; no project command,
scanner, network request, or hook execution was added.

The Status page's `n/n` figure now explicitly means **working-context
readiness**, never product completion or a release decision. Delivery remains
the evidence-backed decision card and its required gates; Pala does not report
an unmeasured completion percentage.

| Gate | Result | Note |
| --- | --- | --- |
| Policy/API and installer contracts | `passed` | ordered native plan, public facade, missing policy helper fail-closed |
| Status language contract | `passed` | context readiness cannot read as project progress or delivery approval |
| Static code audit | `passed` | hard-security 0; 11 remaining maintainability candidates stay explicit |
| Source verify | `passed` | syntax, contracts, package reproducibility, self-audit |
| Portable / Repair / installed verify | `passed` | clean extract, safe Repair, marketplace runtime verify, Doctor `healthy=True` |
| Push / PR / tag / release / deploy | `not-run` | separate owner authority |
| `/hooks` UI trust | `configured-not-verified` | human action; unchanged |

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

## Memory mismatch

- Detected: 2026-08-09T20:58:25.649996+00:00
- Detail: active=M43-T1 but next/status references M43-T2
- Action: reconcile active ticket with next work before claiming progress.

## Memory mismatch

- Detected: 2026-08-09T21:04:49.268082+00:00
- Detail: active=M43-T2 but next/status references M43-T3
- Action: reconcile active ticket with next work before claiming progress.

## Memory mismatch

- Detected: 2026-08-09T21:22:48.433467+00:00
- Detail: active=M43-T3 but next/status references M43-T4
- Action: reconcile active ticket with next work before claiming progress.

## Memory mismatch

- Detected: 2026-08-09T21:34:22.238481+00:00
- Detail: active=M43-T4 but next/status references M43-T5
- Action: reconcile active ticket with next work before claiming progress.

## Memory mismatch

- Detected: 2026-08-09T21:46:22.666186+00:00
- Detail: active=M43-T5 but next/status references M43-T6
- Action: reconcile active ticket with next work before claiming progress.
