# Pala Project Studio Durumu

- Güncelleme: 2026-08-06
- Aktif milestone: M18 — GitHub sunum güncelliği (`completed`)
- Aktif ticket: Yok.
- Son tamamlanan sonuç: Pala Project Studio `v0.4.4`, GitHub'da `Latest`
  release olarak yayınlandı ve yerel kurulum `0.4.4+codex.20260806055124`
  sürümüne güncellendi.
- Çalışma ağacı: README release rozeti private depo davranışına uygun statik
  sürüm rozetiyle değiştirildi; kullanıcıya dönük güncellik metni yenilendi ve
  bu sözleşme sürüm uyumluluk testine eklendi. Eski ve çelişkili ara durum
  notları bu kısa durum belgesinden kaldırıldı.
- Doğrulama kanıtı:
  - `v0.4.4` release ve `pala-project-studio-0.4.4.zip` asset'i mevcut.
  - Release ZIP SHA-256:
    `F092D2066CE15BC6900C40B09B8AEDDB2939AB779C7178C9DED61092CD254B4F`.
  - Gerçek ZIP üzerinden `Update` idempotent tamamlandı; `Doctor` çekirdek,
    Codex, hook ve uzman işçileri `healthy/ready` raporladı.
  - Son yayımlanmış kod kapısı: GitHub Actions `31075515086`, Windows ve
    Ubuntu `success`; yerel 154 test geçti.
  - Shields.io'nun private repo için anonim dinamik sorgusu yanlış kırmızı
    sonuç üretiyordu; yeni statik `v0.4.4` rozeti HTTP 200 ile doğru metni
    render ediyor.
- Engel: Yok.
- Tek sonraki iş: Yeni kullanıcı isteğini bekle.
