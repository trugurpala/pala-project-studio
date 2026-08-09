# Release checklist — v0.8.1 (owner)

Bu ajan turunda **push / PR / tag / `gh release` yapılmadı**. Aşağıdaki adımlar
senin yetkinle.

Kanıt etiketleri: `passed` | `not-run` | `blocked` | `configured-not-verified`.

## Önkoşullar

- [ ] Branch `feat/m30-vibe-codex-host-fit` (veya merge sonrası `main`) istediğin
      commit’te.
- [ ] Doctor: `Install-Pala.ps1 -Mode Doctor` → çekirdek healthy/plugin_ready.
- [ ] Codex Work `/hooks`: Pala hook’larını **güven** (UI; CLI’dan `passed` yok).
- [ ] Soft “A/B fixed” iddiası yok; README birincil indirme hâlâ `v0.8.0` ise
      release öncesi metni kontrol et.

## Yerel doğrulama (önerilir)

```powershell
py -3 -m unittest scripts.test_pala_host_fit scripts.test_pala_self_audit scripts.test_pala_tokens -v
py -3 scripts/verify.py --mode installed
# İsteğe bağlı tam kapı:
# py -3 scripts/verify.py
```

Yerel portable deneme (bu turda üretildi, publish değil):

- Path: `artifacts/portable/pala-project-studio-0.8.1-m30-local.zip`
- SHA-256: `6270BC34F20678AD3C3A25381DA727AEBB4C4D173292D021CE4E219242ABAE1E`
- Entries: 130

Release asset için taze ZIP istersen:

```powershell
py -3 scripts/build_portable.py --output artifacts/portable/pala-project-studio-0.8.1.zip
```

## GitHub (owner)

```powershell
git checkout main
git pull
# feature merge sonrası:
git tag -a v0.8.1 -m "Pala 0.8.1"
git push origin v0.8.1
gh release create v0.8.1 artifacts/portable/pala-project-studio-0.8.1.zip --title "Pala 0.8.1" --notes-file CHANGELOG.md
```

Notlar:

- Tag/release sonrası README download linkini `v0.8.1` yap.  
- Issue #13 close (kaynak fix zaten landed) owner kararı.  
- Hooks UI trust hâlâ insan adımı; release notunda `configured-not-verified`
  bırakılabilir.

## Kurulum (kullanıcıya)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Sonra yeni sohbet + `/hooks` trust. Vibe yolu: `docs/VIBE_FIRST_SESSION.md`.
