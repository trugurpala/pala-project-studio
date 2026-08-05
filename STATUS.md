# Pala Project Studio Durumu

- Aktif milestone: M10 — Tek-kapı yönlendirme ve yönetilen araçlar (`in progress`)
- Aktif ticket: PALA-043 — Çok oturumlu ticket sahipliği ve doğrulama
  lifecycle'ı uygulanıyor.
- Son tamamlanan sonuç: Pala normal yazılım projesi isteklerinde örtük
  seçilebilir, salt sohbet kapsam dışı. SessionStart yalnız yerel plugin/Python/Git/
  hook durumunu özetler. İlk uygulama adımındaki sürüm kontrolü 24 saatlik atomik
  önbellek kullanır; ağ hatası engel üretmez ve sır saklamaz.
- Bulunan ürün açığı: Geliştirme ortamındaki etkin Pala sürümü kaynak sürümünün
  gerisinde kalabildi. Bu, global kurucuda desteklenen Codex CLI üzerinden
  kurulum keşfi, update ve doctor kapılarının zorunlu olduğunu kanıtlıyor.
- Ortam önkoşulu: Kurucu temiz Windows kullanıcı profillerinde çalışacak;
  geliştirici bilgisayarının donanımına, mutlak yollarına veya önceden kurulmuş
  yardımcı araçlarına güvenmeyecek.
- Doğrulama: PALA-043 state/hook yüzeyinde `py -3 -m unittest
  scripts.test_pala_tools -v` — 52 test passed. Tam kaynak kapısı, bu ticket'ın
  sonraki checkpoint'inde yeniden çalıştırılacak.
  Taşınabilir ZIP SHA-256 değeri yalnız üretim artifact'ı için ayrıca raporlanır;
  bu durum belgesi kendi paketini değiştirdiği için buraya sabitlenmez.
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
  geri yüklendi. Kurulum envanteri kaynak/sürüm/SHA/lisans/sahiplik bilgisiyle,
  güncelleme önbelleği atomik JSON olarak ve olay logu yalnız izinli alanlarla
  en fazla 256 KB olacak biçimde doğrulandı. İdempotent Update + Doctor
  Pala-managed fingerprint'i değiştirmedi.
- Engel: Yok.
- Tek sonraki iş: PALA-043 CLI lifecycle sözleşmesini gerçek çağrı testleriyle
  tamamla, ardından adapter sözleşmesi ve RTK ayrı ticket'ına geç.
- Güncelleme: 2026-08-05
- 0.4 teslim hazırlığı: session-safe state, adapter sözleşmeleri, fail-closed
  RTK hook'u, graph eşiği ve GitHub routing private release dalında birleşti.
  Repo görünürlüğü değiştirilmeden private PR/CI/release kanıtı bekleniyor.
