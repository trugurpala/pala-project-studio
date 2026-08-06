# Pala Project Studio 0.3–0.4 Uygulama Planı

## M1 — Codex-native kapsam ve hafıza

- [x] Codex plugin, skill, hook, AGENTS, proje, context ve GitHub sınırlarını güncel resmî manual üzerinden doğrula.
- [x] ZIP kaynağını ayrı Git çalışma alanına al ve mevcut kurulu sürümle eşliğini doğrula.
- [x] Ürün, plan, durum ve karar belgelerini Pala'ya kaydet.
- [x] Mevcut projelerde kullanılan alternatif kapsam, plan ve durum belge
  adlarını otomatik keşif adaylarına ekle.
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
- [x] Yerel geliştirme kataloğunu güncelle, cachebuster uygula ve eklentiyi
  geliştirme ortamında yeniden kur.
- [x] Kaynağı secretsız GitHub deposunda sakla ve CI sonucunu doğrula.

## M5 — Büyük repo kod zekâsı

- [x] PALA-031: `code-review-graph` entegrasyonunu isteğe bağlı ve yerel-first olarak ekle.
- [x] Graph bulunmadığında dürüst `git diff`/`rg` fallback'i sağla.
- [x] Windows kurulumu, lisans kaydı, bağımsız testler ve portable paketi doğrula.

## M6 — Owner demo ve 0.3.1 dağıtımı

- [x] Kullanıcıya gösterilebilir ticket sonunda güncellenen secretsız `OWNER_DEMO.md` profilini ve şablonunu ekle.
- [x] Demo belgesini keşif/kayıt/fingerprint akışına bağla; gerçek tarayıcı olmadan ekran kanıtı üretmeyi yasakla.
- [x] 0.3.1 cachebuster, portable ZIP, yerel geliştirme kurulumu, GitHub push
  ve CI kanıtını tamamla.

## M7 — Checkpoint commit öz-referansı ve 0.3.2

- [x] Temiz örnek proje ağacında checkpoint commit'inden sonra oluşan yanlış
  stale uyarısını gerçek kullanımda yeniden üret.
- [x] Değişen yol sayısı + birleşik içerik özetiyle yalnız aynı snapshot'ı taşıyan descendant commit'i kabul et.
- [x] Aynı checkpoint'ten sonraki ek/farklı commit'in uzlaştırma gerektirmeye devam ettiğini sözleşme testiyle koru.
- [x] 0.3.2 tam doğrulama, portable ZIP, yerel geliştirme kurulumu, GitHub push
  ve CI kanıtını tamamla.

## M8 — 0.4 ürün sözleşmesi ve araç seçimi

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

## M9 — İdempotent tek komut Windows kurulumu

- [x] PALA-041: Repo ve portable ZIP kökünden aynı tek komutla çalışan
  `Install`, `Doctor`, `Repair`, `Update`, `Uninstall` ve `-WhatIf` akışını
  oluştur.
- [x] Kurulu bileşeni sürüm, kaynak ve sahiplik bilgisiyle keşfet; doğruysa
  `zaten hazır`, eskiyse `güncellenecek`, yabancı/çakışan ise `dokunulmadı`
  sonucu ver.
- [x] Pala dosyalarını staging klasöründe doğrula, atomik etkinleştir ve hata
  halinde önceki çalışan kuruluma geri dön.
- [x] Codex marketplace/plugin kurulumunu desteklenen CLI üzerinden idempotent
  yap; config ve marketplace JSON'unu elle düzenleme.
- [x] Repo kapsamlı `.agents/plugins/marketplace.json` kataloğunu doğrula;
  GitHub checkout veya portable ZIP kökünü desteklenen `codex plugin
  marketplace add` ve `codex plugin add` akışına bağla.
- [x] Temiz Windows kullanıcı profilinde kurulu Pala yok, güncel Pala var,
  eski Pala var ve aynı adlı yabancı kayıt var senaryolarını ayır; kullanıcıya
  ait katalog veya ayarı sessizce değiştirme.
- [x] Pala'ya ait kurulum envanteri, güncelleme önbelleği ve logları atomik,
  sınırlı ve secretsız yaz.

## M10 — Tek-kapı yönlendirme ve yönetilen araçlar

- [x] PALA-042: Pala skill'ini normal yazılım geliştirme, denetleme, kurtarma,
  çalıştırma ve tamamlama isteklerinde örtük seçilebilir yap; salt sohbet ve
  ilgisiz görevlerde tetiklenmesini önle.
- [x] Her SessionStart'ta ağsız yerel sağlık/güncellik özeti yükle; Pala'nın ilk
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

## M11 — Büyük iş dayanıklılığı

- [x] PALA-043: Bir aktif ticket, tek sonraki iş, atomik checkpoint ve
  compaction geri yükleme sözleşmesini çok oturumlu senaryolarla genişlet.
- [x] Aynı repo için paralel sohbetleri oturum kimliğiyle ayır; bir sohbetin
  dirty işi diğerinin `begin` veya checkpoint'iyle ezilmesin.
- [x] Başarısız/timeout/yarım doğrulamayı başarı sayma; tekrar deneme bütçesi,
  ilk nedensel hata ve açık blocker kaydı tut.
- [x] Büyük repo eşiklerini kaynak dosya sayısı, değişiklik yayılımı ve modül
  sınırından belirle; küçük işte graph/MCP/çoklu ajan maliyetini başlatma.
- [x] Kapanışta gerçek runtime, test, lint, typecheck, build, dependency ve
  secrets kontrollerinden yalnız projede var olan uygun kapıları çalıştır.

## M12 — Arıza, çakışma ve tekrar testleri

- [x] PALA-044: İzole geçici kullanıcı profiliyle 50 ardışık
  install/doctor/update çalıştırıp ikinci ve sonraki kurulumların değişiklik
  üretmediğini kanıtla.
- [x] Eski Pala, güncel Pala, bozuk kopya, yarım staging, kilitli dosya,
  çevrimdışı ağ, eksik PATH, eksik Python/Node/uv, yabancı MCP ve güvenilmemiş
  hook senaryolarını test et.
- [x] RTK rewrite için çıkış kodu, yan etki, argüman ve fallback eşdeğerlik
  testlerini Windows PowerShell 5.1/7 ve uygun CI ortamında çalıştır.
- [x] Kaynak testleri, portable ZIP içinden testler, temiz klasör kurulumu,
  repair, uninstall ve önceki sürüme rollback kapılarını geçir.

## M13 — 0.4 global paket ve teslim

- [x] Tüm source ve portable kapılar geçmeden manifest sürümünü artırma.
- [x] Windows ve Ubuntu CI başarılarını, temiz Windows doctor çıktısını,
  üretilen ZIP'i ve SHA-256 değerini kaydet.
- [x] Herkese açık GitHub checkout/release ZIP'i ile temiz Windows profilinde
  tek komut kurulumunu doğrula; yeni sohbette örtük ve açık çağrı testlerini
  yap.
- [x] Yerel geliştirici kurulumu ile global dağıtımı ayrı tut; ürün kurulumu
  kişisel katalog, belirli kullanıcı yolu veya geliştirici makinesi varsaymasın.
- [x] Commit, push, tag ve release'i ayrı yetki ve kanıt sınırlarında yürüt;
  CI başarılı olmadan release oluşturma. Depoyu public yapma veya evrensel
  kataloğa yayımlama yalnız bu hesap düzeyi işlem için açık kullanıcı yetkisiyle
  yapılır.

## M14 — Pala güvenli uzman işçileri

- [x] PALA-045: `code-review-graph` varsayılanını koruyan deterministik uzman
  yönlendiricisini; Graphify, Serena ve codebase-memory için ortak kanıt
  sözleşmesini ekle.
- [x] Graphify'nin tüm çıktısını Pala veri köküne yönlendir; kodda `--code-only`,
  belge/PDF işinde yalnız görev ömürlü yerel Ollama backend'i kullan.
- [x] Serena'yı Pala sahipliğinde, salt-okunur, dashboard/bellek/shell/edit
  araçları kapalı stdio MCP sarmalayıcısı olarak kur; Python, JS/TS, PHP ve
  PowerShell dil sunucularını sabitle.
- [x] codebase-memory'yi yalnız tek-atımlık CLI ve `CBM_ALLOWED_ROOT` sınırıyla
  çalıştır; UI, daemon, watcher ve hook kurma.
- [x] Standart kurulumda Pala sahipliğinde Ollama + Qwen3 4B hazırla; kullanıcı
  Ollama/model alanını değiştirme ve bütün dosyaları hash ile doğrula.

## M15 — GitHub ana sayfa ve yayın standardı

- [x] Her release öncesi README'nin güncel sürüm indirme bağlantısını, kısa
  değer önerisini, güvenlik sınırlarını ve Divan'ın ortak altyapı rolünü doğrula.
- [x] GitHub depo açıklamasını, release başlığını ve taşınabilir ZIP adını aynı
  sürümle uyumlu tut; eski etiketi yeni kodu gösterecek biçimde değiştirme.
- [x] Yayın sonrası release asset SHA-256 değerini GitHub API'den karşılaştır;
  ana dal, etiketi, CI ve indirme bağlantısı doğrulanmadan release'i tamamlandı
  sayma.

## M16 — Doktor uzlaştırma doğruluğu

- [x] PALA-046: `doctor` raporunun checkpoint belge/Git farklarını
  `context` ile aynı uzlaştırma hesabından göstermesini sağla; belge sürüklenmesi
  için regresyon testi ekle. Yeni v3 oturum ticket'larının checkpoint öncesi
  yanlışlıkla eski workflow sayılmamasını kapsa ve tam yerel kapıyı çalıştır.
- [x] PALA-047: Kurulum/doctor/update çevrim testini CI ana makinesindeki
  `codex`, `node` ve `uv` kurulumundan bağımsızlaştır; testin sözleşmesi olan
  yönetilen kurulum döngüsünü deterministik araç keşfiyle doğrula.

## M17 — 0.4.2–0.4.4 yama sürümleri

- [x] PALA-048: PALA-046 ve PALA-047 düzeltmelerini 0.4.2 manifesti,
  yeniden üretilebilir portable ZIP, GitHub tag/release ve asset bütünlük
  kanıtıyla son kullanıcıya teslim et. Desteklenen Update akışında bulunan
  çalışma zamanı kusuru PALA-049'a devredildi; yayımlanmış etiket değiştirilmedi.
- [x] PALA-049: `uv` ilerleme çıktısını uzman kurucu JSON protokolünden ayır,
  regresyon kapsamını ekle ve düzeltmeyi 0.4.3 yama sürümü olarak yayınla.
  Gerçek Update kapısında bulunan Ollama soğuk başlangıç kusuru PALA-050'ye
  devredildi; yayımlanmış etiket değiştirilmedi.
- [x] PALA-050: Beklenen Ollama bağlantı reddi stderr çıktısını güvenle yakala,
  yönetilen loopback sunucusunun başlayabilmesini doğrula ve 0.4.4'ü yayınla.

## M18 — GitHub sunum güncelliği

- [x] PALA-051: Private depoda anonim Shields.io release sorgusunun ürettiği
  yanlış kırmızı rozeti düzelt; README, sürüm metinleri, release, durum belgeleri
  ve Pala checkpoint'ini güncel gerçek durumla uzlaştır.

## M19 — Güvenli açık kaynak katkı akışı

- [x] PALA-052: Güncel GitHub/OSS araçlarını araştır; GitHub MCP/connector,
  `gh`, OSV-Scanner, zizmor, OpenSSF Scorecard ve alternatif ajan/tarayıcılar
  için ADOPT / ADAPT / REFERENCE / REJECT kararlarını kilitle.
- [x] Katkı metinlerini untrusted data olarak işleyen ağsız policy reader,
  açıklanabilir issue puanı ve güvenlik/mevcut PR/atama/AI politikası sert
  blocker'larını uygula.
- [x] Diff/commit/gate fingerprint'i, yalnız draft PR'a izin veren fail-closed
  publish kapısı ve fork/push/PR için üç ayrı uzak-yazma yetkisi ekle.
- [x] Vibe-coder doğal dil akışını Pala skill'i, OSS referansı, README, ADR-011
  ve kilitli M19 uygulama planına bağla.
- [x] Dar M19 sözleşme paketini çalıştır: `15/15 PASS`; `verify.py` ve portable
  paketleyicinin yeni script/test/reference yüzeyini otomatik kapsadığını
  doğrula; orkestratör skill'ini mevcut 450-kelime bütçesinin altında tut.
- [ ] Draft PR #6 üzerinde tam `Quality` kapısını Ubuntu + Windows'ta geçir.
  Connected GitHub oturumunda PR açma/synchronize/reopen olayları Actions koşusu
  oluşturmadı ve yeni `workflow_dispatch` başlatma aracı yok; bu kapı
  `BLOCKED_EXTERNAL_TRIGGER`, PASS değildir.
