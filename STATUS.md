# Pala Project Studio Durumu

- Aktif milestone: M14 — Pala güvenli uzman işçileri (`completed`)
- Aktif ticket: PALA-045 — Pala tek otoriteyken Graphify, Serena ve
  codebase-memory'yi izole, kanıt döndüren uzman işçilere bağlama.
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
- Doğrulama: M11 PALA-043 için `python -m unittest discover -s scripts -p
  "test_*.py"` — 150 test passed (12.187 sn). `verification required` durumundan
  `completed` lifecycle'a
  geçiş başarıyla çalıştı; paralel oturum izolasyonu, yeniden deneme-bütçesi,
  graph eşiği ve kapanış kapısı sözleşmesi test kapsamına alındı.
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
- Doğrudan M12 ara kanıtı: `test_install_doctor_update_cycles_are_dry` ve
  `test_doctor_installation_reports_missing_required_tools` testleri ile PALA-044'ün
  ilk madde seti ve PATH/özel araç bağımlılığı denetimi doğrulandı.
- Doğrudan ikinci aşama kanıtı: `test_install_all_current_version_is_noop_for_ready_codex`,
  `test_install_all_reports_unavailable_when_codex_is_offline`,
  `test_install_all_restores_previous_state_after_mid_install_exception`,
  `test_doctor_installation_blocks_if_project_hook_safety_fails` ile eski/güncel
  Pala, çevrimdışı durum, yarım-staging rollback ve güvenilmemiş hook senaryoları da
  tamamlandı.
- Doğrudan üçüncü aşama kanıtı: `test_rtk_hook_rewrites_supported_command_with_managed_binary`
  ve `test_rtk_hook_falls_back_to_no_update_for_disallowed_command` testleri ile RTK
  rewrite fallback/safe argüman davranışı doğrulandı.
- Dördüncü aşama kanıtı: `test_source_root_install_repair_uninstall_in_clean_profile`
  ve `test_portable_zip_source_install_repair_uninstall_and_rollback` ile kaynak modda ve
  portable ZIP’den temiz profil kurulum, `repair`, `uninstall` ve `rollback` kapıları
  geçti.
- Engel: Yok. PALA-043 yerel workflow kaydı ana çalışma alanında eski kalmıştı;
  izole PALA-045 worktree'sinde yeni state ile uzlaştırıldı.
- Tek sonraki iş: Değişiklikleri GitHub'a push et, draft PR aç ve CI kanıtını
  kaydet.
- PALA-045 yerel kanıtı: Pala-owned Graphify, Serena, codebase-memory ve
  Ollama artifact'ları SHA-256 ile doğrulandı. Graphify `--code-only` smoke
  çalışması Pala veri kökünde 451 düğüm/909 kenar üretti; codebase-memory
  tek-atımlık index 844 düğüm/3298 kenarla tamamlandı. Ayrı loopback Ollama
  deposunda `qwen3:4b-instruct` kimliği `0edcdef34593` olarak doğrulandı.
- Güncelleme: 2026-08-05
- GitHub sayfa standardı: Her release'te README hızlı başlangıç, güncel indirme
  bağlantısı, uzman işçi güvenlik sınırları, Divan açıklaması ve GitHub release
  asset bütünlüğü doğrulanmıştır; bu kontrol M15 altında tamamlandı.
- 0.4 teslim hazırlığı: session-safe state, adapter sözleşmeleri, fail-closed
  RTK hook'u, graph eşiği ve GitHub routing private release dalında birleşti.
  Repo görünürlüğü değiştirilmeden private PR/CI/release kanıtı bekleniyor.
- 0.4.1 için son durum: M13 tüm kapıları toplu doğrulandı ve yayın
  manifesti senkronize edildi.
- M13 kanıt özeti: `py -3 scripts/verify.py` (150 test geçti, OK),
  GH Actions `Quality` çalışma `31048474907` (windows-latest + ubuntu-latest,
  sonuçlar: `success`), `py -3 scripts/build_portable.py --output dist/pala-project-studio-0.4.1+codex.20260806090000.zip`
  (SHA-256: `7CB222E89B8694924A200220E324E55F12F1B39FADC1464C89C7A1BBAF1FF9A3`).
  Release `v0.4.1` güncellendi: `pala-project-studio-0.4.1.zip` asset'i bu SHA-256 ile
  tekrar yüklenmiştir.
