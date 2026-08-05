# Pala Project Studio Durumu

- Aktif milestone: M9 — İdempotent tek komut Windows kurulumu (`in_progress`)
- Aktif ticket: PALA-041 — Global dağıtıma uygun, atomik ve idempotent Windows
  kurucu çekirdeği uygulanıyor.
- Son tamamlanan sonuç: 0.3.3 kaynak ve GitHub release artifact'ı `742fb86`
  üzerinde doğrulandı. Yerel `python scripts/verify.py` 54 testi ve tekrarlanabilir
  portable SHA-256 kapısını geçti.
- Bulunan ürün açığı: Geliştirme ortamındaki etkin Pala sürümü kaynak sürümünün
  gerisinde kalabildi. Bu, global kurucuda desteklenen Codex CLI üzerinden
  kurulum keşfi, update ve doctor kapılarının zorunlu olduğunu kanıtlıyor.
- Ortam önkoşulu: Kurucu temiz Windows kullanıcı profillerinde çalışacak;
  geliştirici bilgisayarının donanımına, mutlak yollarına veya önceden kurulmuş
  yardımcı araçlarına güvenmeyecek.
- Doğrulama: `python scripts/verify.py` — 66 test passed;
  `reproducible_zip_sha256=09228C7D059D671EEB4A0124D6A6AAEE6773F5492448004EEEA8BDB0F1C092E6`.
  Bu SHA yalnız PALA-041 ara paketi içindir; 0.4 release kanıtı değildir.
  Son yayımlanmış 0.3.3 için GitHub Actions `31021033644` Windows ve Ubuntu'da
  başarılıydı.
- PALA-041 ara kanıtı: kurulum çekirdeği için 50 çalıştırmalı idempotency,
  dry-run, legacy migration, drift repair, rollback ve güvenli uninstall
  testleri geçti. Global marketplace/CLI bağlama ve temiz profil doğrulaması
  henüz tamamlanmadı.
- Engel: Yok.
- Tek sonraki iş: Repo marketplace kataloğunu ekle ve desteklenen Codex CLI
  kurulumunu izole temiz profilde sözleşme testiyle bağla.
- Güncelleme: 2026-08-05
