# Pala 0.6 — Durum Sayfası Ana Yüzey

Pala herhangi bir projede çağrıldığında ilk yüzey yerel durum sayfasıdır.

## Amaç

- Sohbet geçmişine güvenmeden “nerede kaldım?” sorusunu tek bakışta cevaplamak
- Birden fazla kayıtlı projeyi sol menüden gezmek
- Pala sürüm güncelliğini ve proje tazeliğini görünür kılmak

## Üretim

```powershell
py -3 scripts\pala_report.py --cwd . --open
```

veya:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
```

Çıktı: `.codex/pala-status.html` (git'e girmez).

## Özellikler

- Sol menü: kontrol bölümleri + katalog projeleri (CSS-only radio + `:checked`)
- İlk yüzey: marka Pala + karar şeridi + Şimdi (tam sayfa kontrol merkezi hissi)
- Tema: koyu/açık — `localStorage` (`pala.ui.theme`); tek inline script, harici asset yok
- Yetki/özellik satırları: experts göster, kapalı INC soft-fail hatırlatma, quality tier
- Tazelik rozetleri: `<2 gün` taze, `2–7 gün` eskıyor, `>7 gün` bayat
- Güncellik bannerı: 24 saat önbellekli `pala_update.check_update`
- XSS'e karşı `html.escape`; harici `src` / `<link>` yok
- HTTPS linkler yalnız repo/release için serbest
- `/hooks` trust satırı: her zaman `configured-not-verified` (insan)

## Sınırlar

- Sunucu/port yok
- Hook içinde ağ veya tarayıcı açma yok (ADR-007)
- Deterministik script'ler tek kaynak gerçek olmaya devam eder
- Inline script yalnız UI tercihi yazar; ağ çağrısı yok

See also: `DECISIONS.md` ADR-013 / ADR-014 · `docs/GOAL_0_8_1_FINISH.md`

## İç kurulum (provision)

Ajans / self-host senaryosu için URL ile yerel clone+kayıt:

`docs/PALA_INTERNAL_PROVISION.md` · `py -3 scripts\pala_provision.py provision --url <https-git> --parent <dir>`
