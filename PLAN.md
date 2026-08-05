# Pala Project Studio 0.3–0.4 Uygulama Planı

## M1 — Codex-native kapsam ve hafıza

- [x] Codex plugin, skill, hook, AGENTS, proje, context ve GitHub sınırlarını güncel resmî manual üzerinden doğrula.
- [x] ZIP kaynağını ayrı Git çalışma alanına al ve mevcut kurulu sürümle eşliğini doğrula.
- [x] Ürün, plan, durum ve karar belgelerini Pala'ya kaydet.
- [x] AZR gibi mevcut belge adlarını otomatik keşif adaylarına ekle.
- [x] Checkpoint kanıt özeti ve belge/Git fingerprint'iyle durum eskimesini algıla.

## M2 — Token-verimli aktif yürütme

- [x] SessionStart çıktısını aktif ticket, tek sonraki iş, engel ve gerekli belge yollarıyla sınırla.
- [x] Skill'i bütün planı okumak yerine durum + aktif ticket bölümüyle progressive disclosure kullanacak biçimde güncelle.
- [x] Ticket'ı mikro checkbox değil, bağımsız doğrulanabilir kullanıcı sonucu olarak tanımla.
- [x] Uzun işte yeniden planlamayı engelle; gerçek blocker yoksa güvenli yerel işi sürdür.

## M3 — Doğrulama ve performans dürüstlüğü

- [x] Dar, ticket, milestone ve release doğrulama katmanlarını tanımla.
- [x] Pala hook'larının hiçbir kalite komutunu otomatik çalıştırmadığını sözleşme testiyle koru.
- [x] Süre/başlangıç ölçümü olmadan yüzde hız veya token kazancı raporlamayı yasakla.
- [x] Tek komutlu tam plugin doğrulama scripti ekle.

## M4 — GitHub ve dağıtım

- [x] GitHub'a alınan/alınmayan verileri ve ayrı yetki sınırlarını skill referansına işle.
- [x] Manifest, README, lisans, güvenlik ve CI yüzeylerini tamamla.
- [x] Birim, sözleşme, skill, plugin ve portable paket doğrulamalarını çalıştır.
- [x] Yeni portable ZIP üret ve SHA-256 kaydet.
- [x] Kişisel marketplace kaynağını güncelle, cachebuster uygula ve eklentiyi yeniden kur.
- [x] Kaynağı secretsız özel GitHub deposunda sakla ve CI sonucunu doğrula.

## M5 — AZR'ye dönüş

- [x] AZR'nin gerçek F2 durumunun ayrı `feat/f2-collection-requests` worktree'inde ilerlediğini salt okunur doğrula.
- [x] Aktif Task 8 oturumuna dosya çakışması yaratmadan kesin dönüş noktasını ve bekleyen görsel kabul işini belirle.

## M6 — Büyük repo kod zekâsı

- [x] PALA-031: `code-review-graph` entegrasyonunu isteğe bağlı ve yerel-first olarak ekle.
- [x] Graph bulunmadığında dürüst `git diff`/`rg` fallback'i sağla.
- [x] Windows kurulumu, lisans kaydı, bağımsız testler ve portable paketi doğrula.

## M7 — Owner demo ve 0.3.1 dağıtımı

- [x] Kullanıcıya gösterilebilir ticket sonunda güncellenen secretsız `OWNER_DEMO.md` profilini ve şablonunu ekle.
- [x] Demo belgesini keşif/kayıt/fingerprint akışına bağla; gerçek tarayıcı olmadan ekran kanıtı üretmeyi yasakla.
- [x] 0.3.1 cachebuster, portable ZIP, kişisel kurulum, private GitHub push ve CI kanıtını tamamla.

## M8 — Checkpoint commit öz-referansı ve 0.3.2

- [x] Temiz AZR ağacında checkpoint commit'inden sonra oluşan yanlış stale uyarısını gerçek kullanımda yeniden üret.
- [x] Değişen yol sayısı + birleşik içerik özetiyle yalnız aynı snapshot'ı taşıyan descendant commit'i kabul et.
- [x] Aynı checkpoint'ten sonraki ek/farklı commit'in uzlaştırma gerektirmeye devam ettiğini sözleşme testiyle koru.
- [x] 0.3.2 tam doğrulama, portable ZIP, kişisel kurulum, private GitHub push ve CI kanıtını tamamla.

## M9 — 0.4 ürün sözleşmesi ve araç seçimi

- [x] PALA-040: Geçmiş kullanıcı önerilerini, güncel Codex manual'ini, mevcut
  0.3.3 kaynağını, kurulu 0.3.2 eklentisini ve Windows makine durumunu tek
  kanıtta uzlaştır.
- [x] Tek görünür Pala kapısını, örtük skill etkinleşmesini, oturum güncellik
  kontrolünü ve yeni-sohbet sınırını ürün sözleşmesine işle.
- [x] RTK, code-review-graph, Context7, Playwright, OpenSpec,
  planning-with-files, developer-roadmap ve Ruflo için al/kullan/uyumla/reddet
  kararını lisans, çakışma, bakım ve doğrulama kanıtıyla kaydet.
- [x] 0.4 kabul kapılarını ve geri alma modelini kesinleştir; kod sürümünü
  artırma.

## M10 — İdempotent tek komut Windows kurulumu

- [ ] PALA-041: Repo ve portable ZIP kökünden aynı tek komutla çalışan
  `Install`, `Doctor`, `Repair`, `Update`, `Uninstall` ve `-WhatIf` akışını
  oluştur.
- [ ] Kurulu bileşeni sürüm, kaynak ve sahiplik bilgisiyle keşfet; doğruysa
  `zaten hazır`, eskiyse `güncellenecek`, yabancı/çakışan ise `dokunulmadı`
  sonucu ver.
- [ ] Pala dosyalarını staging klasöründe doğrula, atomik etkinleştir ve hata
  halinde önceki çalışan kuruluma geri dön.
- [ ] Codex marketplace/plugin kurulumunu desteklenen CLI üzerinden idempotent
  yap; config ve marketplace JSON'unu elle düzenleme.
- [ ] Pala'ya ait kurulum envanteri, güncelleme önbelleği ve logları atomik,
  sınırlı ve secretsız yaz.

## M11 — Tek-kapı yönlendirme ve yönetilen araçlar

- [ ] PALA-042: Pala skill'ini normal yazılım geliştirme, denetleme, kurtarma,
  çalıştırma ve tamamlama isteklerinde örtük seçilebilir yap; salt sohbet ve
  ilgisiz görevlerde tetiklenmesini önle.
- [ ] Her SessionStart'ta ağsız yerel sağlık/güncellik özeti yükle; Pala'nın ilk
  ilgili adımında 24 saatlik önbellekle uzak sürüm kontrolü yap.
- [ ] RTK'yı Pala'nın sahip olduğu klasöre sabitlenmiş release + SHA-256 ile
  kur ve yalnız güvenli allowlist komutlarında çalışan Codex-native rewrite
  adaptörü ekle.
- [ ] RTK adaptöründe komut, çalışma klasörü, timeout ve diğer tool girdilerini
  koru; bileşik, interaktif, secret taşıyan veya Git/deploy mutasyonu yapan
  komutları değiştirme.
- [ ] code-review-graph'ı `uv` ile izole ve sürümü sabit kur; kendi Codex
  konfigürasyonunu çalıştırmadan Pala adaptöründen kullan.
- [ ] Context7 ve Playwright MCP kayıtlarını keşfet; aynı doğru kayıt varsa
  koru, eksikse desteklenen `codex mcp add` akışıyla kur, farklı kayıt varsa
  kullanıcı verisini ezmeden doctor'da çakışma raporla.
- [ ] OpenSpec bulunan projeyi algıla ve artifact'larını Pala ticket'ına bağla;
  bulunmayan projeye ikinci plan sistemi kurma.

## M12 — Büyük iş dayanıklılığı

- [ ] PALA-043: Bir aktif ticket, tek sonraki iş, atomik checkpoint ve
  compaction geri yükleme sözleşmesini çok oturumlu senaryolarla genişlet.
- [ ] Aynı repo için paralel sohbetleri oturum kimliğiyle ayır; bir sohbetin
  dirty işi diğerinin `begin` veya checkpoint'iyle ezilmesin.
- [ ] Başarısız/timeout/yarım doğrulamayı başarı sayma; tekrar deneme bütçesi,
  ilk nedensel hata ve açık blocker kaydı tut.
- [ ] Büyük repo eşiklerini kaynak dosya sayısı, değişiklik yayılımı ve modül
  sınırından belirle; küçük işte graph/MCP/çoklu ajan maliyetini başlatma.
- [ ] Kapanışta gerçek runtime, test, lint, typecheck, build, dependency ve
  secrets kontrollerinden yalnız projede var olan uygun kapıları çalıştır.

## M13 — Arıza, çakışma ve tekrar testleri

- [ ] PALA-044: İzole geçici kullanıcı profiliyle 50 ardışık
  install/doctor/update çalıştırıp ikinci ve sonraki kurulumların değişiklik
  üretmediğini kanıtla.
- [ ] Eski Pala, güncel Pala, bozuk kopya, yarım staging, kilitli dosya,
  çevrimdışı ağ, eksik PATH, eksik Python/Node/uv, yabancı MCP ve güvenilmemiş
  hook senaryolarını test et.
- [ ] RTK rewrite için çıkış kodu, yan etki, argüman ve fallback eşdeğerlik
  testlerini Windows PowerShell 5.1/7 ve uygun CI ortamında çalıştır.
- [ ] Kaynak testleri, portable ZIP içinden testler, temiz klasör kurulumu,
  repair, uninstall ve önceki sürüme rollback kapılarını geçir.

## M14 — 0.4 paket ve teslim

- [ ] Tüm source ve portable kapılar geçmeden manifest sürümünü artırma.
- [ ] Windows ve Ubuntu CI başarılarını, temiz Windows doctor çıktısını,
  üretilen ZIP'i ve SHA-256 değerini kaydet.
- [ ] Kurulu kişisel Pala'yı doğrulanmış paketle güncelle; yeni sohbette örtük
  ve açık çağrı testlerini yap.
- [ ] Commit, push, tag ve release'i ayrı yetki ve kanıt sınırlarında yürüt;
  CI başarılı olmadan release oluşturma.
