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
- Doğrulama: kaynak ve portable içinden `python scripts/verify.py` — 76 test
  passed; güncel ara `reproducible_zip_sha256=DC62D04ECE4BC2DA30B08CCFEDFF89E073E4CFFC32CBA1CACFCB1D2AD8933FD0`.
  Bu SHA yalnız PALA-041 ara paketi içindir; 0.4 release kanıtı değildir.
  Son yayımlanmış 0.3.3 için GitHub Actions `31021033644` Windows ve Ubuntu'da
  başarılıydı.
- PALA-041 ara kanıtı: kurulum çekirdeği için 50 çalıştırmalı idempotency,
  dry-run, legacy migration, drift repair, rollback ve güvenli uninstall
  testleri geçti. Repo marketplace'i desteklenen Codex CLI akışına bağlandı.
  İzole temiz Windows profilinde PowerShell 5.1/7 ile `-WhatIf`, install,
  doctor, idempotent update ve uninstall gerçek Codex CLI üzerinden geçti;
  ana kullanıcı profili değiştirilmedi. Aynı akış temiz klasöre açılan portable
  ZIP içinden de geçti. Yönetilen dosya bozularak doctor'ın `drifted` raporu ve
  `Repair` sonrası yeniden `ready` durumu gerçek akışta doğrulandı. Uzun Windows
  yollarında Codex marketplace temizliğiyle yarışan uninstall güvenli biçimde
  düzeltildi. Eski resmî Pala gerçek Codex CLI ile kaynak hash'i değişmeden
  global kimliğe taşındı. Yabancı aynı adlı eklenti sıfır yazmayla korundu.
  Codex CLI güncelleme hata enjeksiyonunda önceki bundle ve atomik durum kaydı
  geri yüklendi.
- Engel: Yok.
- Tek sonraki iş: Kurulum envanteri, güncelleme önbelleği ve log sınırlarını
  tamamla; PALA-041'in kalan kapısını kapatıp milestone checkpoint'i üret.
- Güncelleme: 2026-08-05
