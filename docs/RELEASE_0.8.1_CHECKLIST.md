# Release checklist — v0.8.1 (owner)

Bu ajan turunda **push / PR / tag /** `gh release` **yapılmadı**. Aşağıdaki adımlar
senin yetkinle.

Kanıt etiketleri: `passed` | `not-run` | `blocked` | `configured-not-verified`.

## Önkoşullar

- [ ] Branch `feat/m30-vibe-codex-host-fit` (veya merge sonrası `main`) istediğin
  ```
  commit’te.
  ```
- [ ] Doctor: `Install-Pala.ps1 -Mode Doctor` → çekirdek healthy/plugin_ready.
- [ ] Codex Work `/hooks`: Pala hook’larını **güven** (UI; CLI’dan `passed` yok).
- [ ] Soft “A/B fixed” iddiası yok; README birincil indirme hâlâ `v0.8.0` ise
  ```
  release öncesi metni kontrol et.
  ```



## Yerel doğrulama (önerilir)

```powershell
py -3 -m unittest scripts.test_plugin_experience scripts.test_pala_host_fit scripts.test_pala_self_audit -v
py -3 scripts/verify.py --mode installed
# İsteğe bağlı tam kapı:
# py -3 scripts/verify.py
```

Vibe-install focused unittest (2026-08-09): Ran 43 / OK (`passed`).

Yerel portable deneme (publish değil):

- Vibe-install UX ZIP (güncel):
  `artifacts/portable/pala-project-studio-0.8.1-vibe-install.zip`
  + Desktop kopyası `pala-project-studio-0.8.1-vibe-install.zip`
  - SHA-256: `18DA984F548B54C450016D46135B6920CF382E62C1446F3E88BE0912C06ABA36`
  - Entries: 132
- Önceki M30 local ZIP:
  `artifacts/portable/pala-project-studio-0.8.1-m30-local.zip`
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

**Birincil — Codex-native CLI** (native ZIP-upload UI yok):

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

Yerel kök: `codex plugin marketplace add <path-to-repo-root>` sonra aynı
`codex plugin add pala-project-studio@pala-project-studio`.

Sonra: `/hooks` trust → **yeni sohbet**.

**İkincil — ZIP / tam toolkit** (çıkar → `Kur.cmd` veya Install-Pala; Plugins’e
ZIP yükleme değil):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Doctor `hook_safety` ≠ `/hooks` UI trust. Vibe: `docs/VIBE_INSTALL.md` +
`docs/VIBE_FIRST_SESSION.md`. ZIP kökü: `KUR.md`.