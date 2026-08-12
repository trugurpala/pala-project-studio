# M61-T1 — Eski/yeni Pala kurulum kabul raporu

Zaman: 2026-08-12T00:20:01+03:00

## Kimlik ve bütünlük

| Ölçüt | Eski | Yeni | Sonuç |
| --- | --- | --- | --- |
| Plugin sürümü | `1.0.0-local-rc+codex.20260811000000` | `1.0.0-local-rc+codex.20260811000000` | aynı |
| Marketplace fingerprint | `B955AAF7B64DD684545FE9509C9F96879841F8770681B7C15711A87EFF21B544` | aynı | `passed` |
| ZIP SHA-256 | n/a | `3424FB0AAE6EEFBEBE937A6EB0D065705844E846737C15A4C3301E518DDE5D54` | `passed` |
| ZIP girişleri | n/a | 205; unsafe path 0 | `passed` |
| Kurulan yönetilen dosya | 150 | 150 | aynı |
| installed_at (UTC) | 2026-08-11T20:31:11+00:00 | 2026-08-11T21:15:09+00:00 | yeniden kuruldu |

## Önce/sonra ölçümleri

| Kapı | Eski | Yeni | Yüzde |
| --- | --- | --- | --- |
| Doctor çekirdek: healthy/plugin_ready/codex ready | 3/3 | 3/3 | %100 → %100 |
| Installed verify | 1/1 | 1/1 | %100 → %100 |
| Runtime self-audit | 4/4 | 4/4 | %100 → %100 |
| Tools + plugin-experience mini testleri | 126/126 | 126/126 | %100 → %100 |
| Installer mini testleri (çalıştırılan) | 61/61 | 61/61 | %100 → %100 |
| Planlanan mini test kapsaması | 187/188 (1 skip) | 187/188 (1 skip) | %99,47 → %99,47 |
| İsteğe bağlı adapter hazır oluşu | 4/9 | 4/9 | %44,44 → %44,44 |
| Hooks UI kullanıcı güveni doğrulama kapsamı | 0/1 | 0/1 | %0 → %0 (`configured-not-verified`) |

## Yaşam döngüsü ve ek kapılar

- Uninstall dry-run: `passed` (`would_uninstall`).
- Uninstall: `passed`; marketplace/install-state/cache kaldırıldı.
- Shared SQLite memory preservation: `passed`; `pala.sqlite` kaldı.
- Portable clean-extract verify: `passed`.
- Install dry-run: `passed` (`would_install`).
- ZIP içinden Install-Pala: `passed`, exit 0.
- Codex `plugin list`: `passed`; Pala installed+enabled.
- Full local gate: `passed`; 536 test, 1 controlled skip, exit 0.
- Official plugin validator: `passed`.
- Official skill validator: `passed`.
- Remote publish/deploy: `not-run`.

## Sonuç

Ölçülen yerel çekirdek kabul noktaları `passed`. Paket eski kurulumla aynı
sürüm ve aynı fingerprint'i taşıdığı için fonksiyonel sürüm farkı %0; yapılan
işlem temiz kaldırma/yeniden kurulum ve cache yenilemesidir. İsteğe bağlı
uzmanlar varsayılan kurulum kapsamına alınmadı. Codex Work `/hooks` kullanıcı
trust adımı otomatikleştirilemediği için `configured-not-verified` kaldı.
