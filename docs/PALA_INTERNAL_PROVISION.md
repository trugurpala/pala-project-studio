# Pala iç kurulum (provision) — dahili MVP

Ajans senaryosu: **URL ver → Pala kuruluşa alır → katalog + makine kaydı**.
Bu bulut veritabanı veya çok kiracılı SaaS değildir; yalnız yerel, secretsız kayıt.

## Ne yapar?

`scripts/pala_provision.py`:

1. HTTPS git URL doğrular (`file://` ve shell meta karakterleri reddedilir)
2. `--parent` altında clone eder; klasör varsa yalnız `git fetch` (reset yok)
3. İsteğe bağlı `--register` ile `pala_state.register` (memory stub'ları)
4. `Desktop/Codex/pala-catalog.json` içine `phase=provisioned` upsert
5. `%LOCALAPPDATA%/Pala/provision-registry.json` içine makine kaydı yazar

## Komutlar

```powershell
# Önizleme (ağ/yazma yok)
py -3 scripts\pala_provision.py provision --url https://github.com/org/repo.git --parent $env:USERPROFILE\Desktop\Cursor --dry-run

# Gerçek clone + katalog + registry
py -3 scripts\pala_provision.py provision --url https://github.com/org/repo.git --parent $env:USERPROFILE\Desktop\Cursor

# Clone sonrası register dene
py -3 scripts\pala_provision.py provision --url https://github.com/org/repo.git --parent $env:USERPROFILE\Desktop\Cursor --register
```

Katalog özeti:

```powershell
py -3 scripts\pala_catalog.py summary
```

Durum sayfası:

```powershell
py -3 scripts\pala_report.py --cwd . --open
```

## PowerShell kapısı

`Install-Pala.ps1` Mode ValidateSet değiştirilmedi (mevcut sözleşme testleri).
Provision yüzeyi Python CLI'dır; tek kurulum kapısı Install-Pala olarak kalır.

## Sınırlar

- Hook içinde ağ yok (ADR-007)
- Cloud DB / Claude / ChatGPT tek tık kurulum yok
- Ölçülmemiş % hız iddiası yok

See also: `docs/ARCHITECTURE.md`, ADR-012 katalog.
