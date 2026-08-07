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

- Sol menü: aktif proje + katalog projeleri (CSS-only; JavaScript yok)
- Tazelik rozetleri: `<2 gün` taze, `2–7 gün` eskıyor, `>7 gün` bayat
- Güncellik bannerı: 24 saat önbellekli `pala_update.check_update`
- XSS'e karşı `html.escape`; harici `src` / `<link>` / `<script>` yok
- HTTPS linkler yalnız repo/release için serbest

## Sınırlar

- Sunucu/port yok
- Hook içinde ağ veya tarayıcı açma yok (ADR-007)
- Deterministik script'ler tek kaynak gerçek olmaya devam eder

See also: `DECISIONS.md` ADR-013 / ADR-014.
