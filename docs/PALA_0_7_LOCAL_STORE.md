# Pala 0.7 — Yerel Store + Zaman Çizelgeli Panel

Pala'nın projeler-arası hafızası artık JSON yerine yerel SQLite'tadır; durum
sayfası üç soruyu 5 saniyede cevaplamayı hedefler.

## Neden SQLite?

1. **Eşzamanlılık** — iki Codex oturumu aynı anda katalog yazınca JSON'da kayıt
   kaybolabiliyordu; WAL + busy timeout bunu önler.
2. **Geçmiş** — `events` tablosu register / begin / checkpoint / provision /
   mismatch kayıtlarını tutar.
3. **Sorgu** — bayat projeler, son provision'lar, son olaylar dosya taraması
   olmadan listelenir.

JSON over-engineering olurdu; bu üç gerekçe olmadan da yapılmazdı.

## Konum

- Varsayılan: `%USERPROFILE%\Desktop\Codex\pala.sqlite`
- Taşıma: `PALA_CATALOG_ROOT` (katalog kökü) veya `PALA_DB_PATH` (dosya)
- İnsan yedeği: aynı klasörde `pala-catalog.json` + `INDEX.md` (export)

```powershell
py -3 scripts\pala_catalog.py export
```

## Panel (3 soru)

```powershell
py -3 scripts\pala_report.py --cwd . --open
```

1. **Şimdi:** tek `next_action` satırı
2. **Unuttum:** okuma sırası `N/7` + eksikler
3. **Dün:** son olaylar zaman çizelgesi + son URL kurulumları

Sözleşmeler: `<script>` yok, harici asset yok, XSS escape, CSS-only menü.
Hook içinde ağ veya DB yazımı yok.

## Geri dönüş

1. `pala_catalog.py export` ile JSON+INDEX üret
2. DB bozulursa `pala-catalog.json.bak` ve eski `provision-registry.json`
   üzerinden `pala_db.migrate_from_json` yeniden çalışır

## Sınırlar

- Bulut DB / login / ödeme yok
- Hook DB'ye yazmaz
- `%LOCALAPPDATA%\Pala` yalnız Pala kurulum/araç sahipliği; katalog store ile
  birleştirilmez

See also: `DECISIONS.md` ADR-015, `docs/PALA_0_6_STATUS_SURFACE.md`.
