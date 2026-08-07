# Pala Project Studio Durumu

- Güncelleme: 2026-08-07
- Aktif milestone: M19 — Güvenli açık kaynak katkı akışı (`completed`).
- Aktif ticket: Yok.
- Son kararlı sürüm: `v0.4.4`; M19 sürüm artırımı veya release değildir.
- Son tamamlanan sonuç: M19 / PALA-052, PR #6 üzerinden squash-merge ile
  `main`e alındı. Main commit: `2a8ad32f434fc88069e5d8e17bb2cc9bbf2a6e27`.
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
  - Orkestratör skill'i 434 kelime; mevcut <=450 sözleşmesi korunuyor.
  - PR Quality #36 (`31131516966`): Windows + Ubuntu `success`; her ortamda
    `169` test geçti.
  - İkinci PR Quality #37 (`31155100116`): `success`.
  - Final PR head Quality #40 (`31155437330`): `success`.
  - Merge sonrası `main` Quality #41 (`31155491104`): Windows + Ubuntu
    `success`.
  - Windows aynı-ortam reproducible ZIP SHA-256:
    `6FEF66592E544F6C4FF1314E68FFE8AA934CD83A9F731462D9A72B9772398F07`.
  - Ubuntu aynı-ortam reproducible ZIP SHA-256:
    `1AF2C40FAC26064BBAC03704073E27CA030A33FCAA19611FEEC9F282AD751CF3`.
  - Ayrıntılı kanıt: `reports/M19_OSS_CONTRIBUTOR_VERIFICATION.md`.
- Engel: Yok — M19 kaynak teslimi `main` üzerinde yeşil.
- Post-M19 dış kabul: Gerçek owner Windows/Codex masaüstü canary ve gerçek
  üçüncü taraf fork/push/draft-PR canary bu bağlı ortamdan çalıştırılamadığı için
  `NOT_RUN`; çalıştırılmadan PASS sayılmaz.
- Tek sonraki iş: Owner Windows/Codex canary ile kurulu ürün davranışını doğrula;
  ardından seçilmiş bir upstream depoda gerçek OSS katkı canary'sini çalıştır.
