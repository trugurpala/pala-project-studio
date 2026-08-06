# Pala Project Studio Durumu

- Güncelleme: 2026-08-07
- Aktif milestone: M19 — Güvenli açık kaynak katkı akışı (`in_progress`).
- Aktif ticket: PALA-052.
- Son kararlı sürüm: `v0.4.4`; bu çalışma sürüm artırımı veya release değildir.
- Çalışma branch'i: `feat/oss-contributor-m19`; draft PR: `#6`.
- Uygulanan kapsam:
  - GitHub connector/MCP salt-okunur scout sözleşmesi ve `gh` için ayrı yazma
    yetkisi modeli kilitlendi.
  - Ağsız `scripts/pala_oss.py` ile katkı politikası, açıklanabilir issue
    puanlama, sert blocker'lar, approval fingerprint, draft-PR publish kapısı ve
    opsiyonel OSV/zizmor keşfi eklendi.
  - Pala skill'i, OSS katkı referansı, README, ADR-011 ve M19 plan kilidi
    güncellendi.
- Doğrulama kanıtı:
  - M19 dar sözleşme paketi: `15/15 PASS`.
  - Orkestratör skill'i M19 eklemelerinden sonra 493 kelimeye çıkmıştı; mevcut
    450-kelime sözleşmesini korumak için 434 kelimeye indirildi.
  - `scripts/verify.py` bütün `scripts/*.py` dosyalarını derler ve
    `scripts/test_*.py` testlerini otomatik keşfeder; portable paketleyici tüm
    `scripts/*.py` ile `skills/` ağacını kapsar.
  - Ayrıntılı kanıt: `reports/M19_OSS_CONTRIBUTOR_VERIFICATION.md`.
  - Draft PR #6 açıldı, branch PR açıkken güncellendi ve bir kez kapatılıp
    yeniden açıldı; buna rağmen bu connector oturumunda hiçbir GitHub Actions
    koşusu oluşmadı. Bağlantıda yeni `workflow_dispatch` başlatma aracı yok.
- Engel: Tam `Quality` kapısı `BLOCKED_EXTERNAL_TRIGGER`; PASS sayılmadı.
- Tek sonraki iş: PR #6 için GitHub `Quality` workflow'unu gerçek GitHub
  tetikleyicisiyle çalıştır; Ubuntu + Windows başarılıysa M19'u tamamla. Ardından
  kurulu Windows owner-canary ve gerçek üçüncü taraf katkı canary'si ayrı dış
  kabul kapılarıdır.
