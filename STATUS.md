# Pala Project Studio — durum (2026-08-09)

Kanıt etiketleri yalnız: `passed` | `not-run` | `blocked` | `configured-not-verified`.

## Özet

Pala, Codex için yerel proje hafızası / plan / doğrulama eklentisidir. Bağlam
penceresi veya kota büyütmez; kısa SessionStart, dosya hafızası ve dürüst
kanıt etiketleriyle vibe coder akışını sürdürür.

| Alan | Değer |
| --- | --- |
| Güncelleme | 2026-08-09 — vibe-install UX + M30 close (yerel; publish yok) |
| Branch | `feat/m30-vibe-codex-host-fit` (yerel; push/PR bu turda yok) |
| Manifest | `0.8.1+codex.20260808124500` |
| Son GitHub release | `v0.8.0` (`passed`) — https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.0 |
| Tag/release `v0.8.1` | `not-run` (owner) |
| Repo | public (`passed`) |

## Şu an tek sonraki iş (owner)

1. Desktop’teki vibe-install ZIP smoke + Codex Work’te native CLI / `Kur.cmd`.  
2. Bu branch’i istediğin gibi push / PR / merge et.  
3. Codex Work’te `/hooks` ile Pala hook’larını güven (`configured-not-verified` → insan).  
4. Hazırsan `docs/RELEASE_0.8.1_CHECKLIST.md` ile `v0.8.1` tag + release bas.  

Soft full-product “A/B fixed”: **yok**.

## Owner sınırları (bilerek)

| Konu | Etiket |
| --- | --- |
| Hooks UI `/hooks` trust | `configured-not-verified` |
| Soft “A/B fixed” | yok |
| Tam source `verify.py` | `not-run` (bu kapanışta) |
| Push / PR / tag / `gh release` (bu ajan turu) | yapılmadı (owner) |
| Marketplace Install sync (diğer makineler) | `not-run` |

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
| Tag/release `v0.8.1` | `not-run` | owner |
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
| Tam source verify | `not-run` | — |
| Soft A/B fixed | yok | — |

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

- Doctor çekirdek: `plugin_ready` / `healthy` beklenir.  
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
