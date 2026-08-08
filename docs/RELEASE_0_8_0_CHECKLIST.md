# 0.8.0 release checklist (insan adımları)

Kısa yol. Kanıt etiketleri: `passed` | `not-run` | `blocked` | `configured-not-verified`.

Kaynak sürüm: **0.8.0** (manifest). Son GitHub yayını: **v0.7.1**. Bu sayfa
`v0.8.0` **yayımlanmadan önce** yerel hazırlığı kapatır; tag/`gh release`
ayrı onay ister.

## 1) Yerel kapı

```powershell
py -3 scripts\verify.py
```

Beklenen: tüm unittest yeşil + self-audit `passed` + portable ZIP üretildi.
SHA’yı `STATUS.md` kanıt satırına yaz.

## 2) Install → Doctor

Repo veya ZIP kökünde:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Beklenen: çekirdek `plugin_ready` / `healthy`.  
`hook_safety=passed` ≠ Codex `/hooks` trust (ayrı adım).

## 3) Codex `/hooks` trust

Codex Work → `/hooks` → Pala’ya **güven**. Bypass yok.  
Sonra **yeni sohbet** (eski thread’i zorlama).

## 4) Demo seed → Status

```powershell
py -3 scripts\pala_demo.py seed --demo-root examples\demo-software-project --catalog-root $env:USERPROFILE\Desktop\Codex
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
```

Beklenen: Status “Şimdi” satırında demo ticket + zaman çizgisi olayları.

## 5) Self-audit

```powershell
py -3 scripts\pala_self_audit.py
```

Beklenen: JSON `status=passed` (presence, fork pack, demo Status, soft-claim).

## 6) Yayın (ayrı onay — bu checklist’te otomatik yok)

Owner “evet” demeden:

- commit / push yok
- `v0.8.0` tag yok
- `gh release create` yok

Onay sonrası tipik sıra: temiz commit → tag `v0.8.0` → portable ZIP asset +
CHANGELOG gövdesi → GitHub Release → README rozetini yeşil `release-v0.8.0`
yapıp STATUS’ta release ZIP’i `passed` yaz.

## Bilerek yapılmayanlar

- M10 RTK / MCP genişletmesi
- ChatGPT Plus sohbet kurulumu iddiası
- Hook içinde test/build/ağ
