# Pala Project Studio Durumu

- Güncelleme: 2026-08-07
- Aktif milestone: M19 — Güvenli açık kaynak katkı akışı (`completed`).
- Aktif ticket: Yok.
- Son kararlı sürüm: `v0.4.4`; M19 kaynak teslimi sürüm artırımı veya release değildir.
- Son tamamlanan sonuç: Pala'nın tek-kapı, local-first yapısını bozmadan güvenli
  açık kaynak katkı akışı eklendi ve GitHub Quality kapısı Windows + Ubuntu'da
  geçirildi.
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
  - GitHub Quality run `31131516966` (#36): Windows + Ubuntu `success`;
    her ortamda `169` test geçti.
  - Windows reproducible ZIP SHA-256:
    `6FEF66592E544F6C4FF1314E68FFE8AA934CD83A9F731462D9A72B9772398F07`.
  - Ubuntu reproducible ZIP SHA-256:
    `1AF2C40FAC26064BBAC03704073E27CA030A33FCAA19611FEEC9F282AD751CF3`.
  - İkinci bağımsız Quality run `31155100116` (#37) de `success` tamamlandı.
  - Ayrıntılı kanıt: `reports/M19_OSS_CONTRIBUTOR_VERIFICATION.md`.
- Engel: Yok — M19 kaynak kabulü tamamlandı.
- Post-M19 dış kabul: Kurulu owner Windows/Codex canary ve gerçek üçüncü taraf
  fork/push/draft-PR canary bu ortamdan çalıştırılamadığı için `NOT_RUN`; bunlar
  M19 kaynak kabulünü geriye düşürmez ve çalıştırılmadan PASS sayılmaz.
- Tek sonraki iş: M19 teslimini `main`e al; sonrasında gerçek owner-canary ile
  ürünün kurulu ortam davranışını doğrula.
