# Pala Project Studio 0.3–0.4 Uygulama Planı

## M61 — Yerel RC sök-tak ve vaat doğrulama

### M61-T1 — Eski/yeni kurulum karşılaştırmalı kabulü

- **Sahip ajan:** Codex `/root`
- **Amaç:** Mevcut Pala kurulumunu ölçülebilir bir taban çizgisiyle kaydetmek,
  yalnız doğrulanan Pala kurulumunu kaldırmak, owner tarafından verilen final
  ZIP'i kurmak ve aynı öz-sorgu/mini testlerle vaat–gerçeklik farkını raporlamak.
- **Dosyalar:** `PLAN.md`, canonical WorkflowStore kaydı,
  `artifacts/install-acceptance/m61-t1/`; makine-yerel Pala marketplace/runtime
  kurulum kökleri yalnız installer'ın doğruladığı kapsamda.
- **Bitti sayılır:** Eski kurulum kimliği ve Doctor/öz-sorgu/mini test tabanı
  kaydedilmiş; hedef ZIP SHA-256 ve içerik manifesti doğrulanmış; kaldırma ile
  kurulum exit `0`; yeni kurulum Doctor/installed verify ve aynı mini testlerden
  geçmiş; her vaat `passed|not-run|blocked|configured-not-verified` ve ölçülen
  başarı yüzdesiyle karşılaştırılmıştır.
- **Bağımlılık:** `M60-T1` canonical `DONE`.
- **Kanıt:** Installer `Status`, `Uninstall`, `Install/Update` ve `Doctor`
  komutları; `py -3 scripts/verify.py --mode installed`; dar installer/plugin
  deneyimi testleri; önce/sonra JSON çıktıları ve SHA-256 manifesti.

## M60 — PALA 1.0 final evidence integrity closure

- [x] Caller-supplied `--quality-command/--quality-exit-code` completion
  authority bypass’ını adversarial testle yeniden üret ve kapat.
- [x] Existing Quality Engine approved argv’sini bounded, shell-free
  `pala-quality-runner` ile gerçek exit/output digest/basis’e bağla.
- [x] Beş process-boundary ve beş direct-runner forgery regresyonunu geçir;
  Windows command shim çözümünü shell açmadan doğrula.
- [x] Fresh 10/10 release ledger, 536 canonical test, 75% coverage, security,
  browser, source/portable/installed/Doctor ve validator kapılarını geçir.
- [x] 205-entry reproducible exact ZIP, schema-v2 manifest ve canonical
  TaskContract `DONE` / WorkflowStore `completed` kapanışını üret.
- [x] Push/PR/merge/tag/release/remote deploy yapma (`not-run`).

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
- [x] PR #6 üzerinde tam `Quality` kapısını Ubuntu + Windows'ta geçir:
  run `31131516966` (#36) iki matrix job'unda `success`, her ortamda `169` test;
  ikinci bağımsız run `31155100116` (#37) de `success`.

## M20 — Gerçeklik + vibe ilk 10 dk

Yeni özellik yok. Amaç: STATUS/PLAN = `main` gerçekliği; vibe yolu tek sayfa;
owner canary ve release iddiası kanıt etiketli.

- [x] PR #9'u `main`e merge et; merge sonrası Quality `31197621102`
  Windows + Ubuntu `success` (`passed`). Merge:
  `51b8ddca60777bfaae1a6e12867089d7eeba3730`.
- [x] STATUS / PLAN / PROGRESS'i 0.5–0.7.1 kod gerçekliğiyle uzlaştır;
  soft “done” yerine `passed|not-run|blocked` kullan.
- [x] Tek sayfa vibe sözleşmesi: `docs/VIBE_FIRST_SESSION.md` (Codex içi çağrı;
  ChatGPT Plus sohbet değil).
- [x] Owner Windows canary (otomatik kısım): Install / Doctor
  (`plugin_ready`/`healthy`) / Status HTML / SQLite path — `passed`
  (`STATUS.md`).
- [x] Hook trust: `blocked` (Doctor `hook=blocked`); yeni sohbet skill tetik
  `not-run` — insan: Codex `/hooks` + yeni sohbet.
- [x] Release truth: `v0.7.1` GitHub ZIP+SHA oluşturuldu
  (`4CD388A40392B7C8AAE0A1A742307993F829F116FB3D4F08989FB1A009230A9D`;
  target `c028bea`; Quality `31197621102`).

### M20 içinde özetlenen landed iş (önceden plansız drift)

- 0.5 hafıza sözleşmesi + plain memory CLI (ADR-012).
- 0.6 durum sayfası / `pala_report` ilk yüzey (ADR-013/014).
- 0.7 yerel SQLite store + catalog/provision/timeline (ADR-015).
- 0.7.1 Windows Codex keşfi + Doctor core/experts (ADR-016).

### M10 artıkları (kapatıldı — 2026-08-08)

- [x] RTK sabit release + SHA + Codex-native rewrite adaptörü (`pala_m10` + lock).
- [x] RTK girdilerini koru; tehlikeli komut rewrite yok (rewrite guard).
- [x] code-review-graph `uv` izole sabit kurulum (Pala adaptörü / expert suite).
- [x] Context7 / Playwright MCP keşif pin’leri (`pala_mcp` + `pala_m10`;
  `ensure` yalnız missing, conflict ezilmez).
- [x] OpenSpec bulunan projeyi ticket'a bağla; yoksa ikinci plan sistemi kurma
  (`OpenSpecAdapter.bind_active_ticket`).

## M21 — Yanında Pala + fork-ready + kalite kanıtı

- [x] SessionStart + skill Human Contract presence (`Pala burada — bu oturumda yanındayım.`)
- [x] `hooks.json` SessionStart `statusMessage`: `Pala yanınızda`
- [x] `examples/demo-software-project/` dolu bellek sözleşmesi
- [x] `scripts/pala_demo.py seed` + `test_pala_demo.py`
- [x] `scripts/pala_self_audit.py` + `verify.py` bağ + Doctor ince işaret
- [x] `docs/FORK_PACK.md`, README/CONTRIBUTING/VIBE güncellemesi
- [x] Packager allowlist (demo + FORK_PACK); manifest `0.8.0+codex.*`
- [ ] GitHub `v0.8.0` release ZIP (ayrı yetki)

## M21.1 — STAB-001 Local confidence gate + durable error brain

Amaç: M21/0.8.0 working tree üzerinde yeniden güven; yeni büyük ürün özelliği yok.
`DEBUGGING.md` hafıza sözleşmesinin parçası olarak kalıcı hata beyni güçlendirilir
(paralel sistem yok). Release/tag/push bu ticket'ta yok.

Paralel iş akışları:

1. Kapı: dar unittest → düzelt → `verify.py` tam yerel kapı.
2. Error-brain: kök `DEBUGGING.md` parse edilebilir incident formatı + sözleşme
   testi + self-audit fail-closed; ajanlar bilinen hatayı tekrarlamadan önce okur.
3. Kanıt: STATUS / PLAN / PROGRESS gerçek etiketlerle güncellenir.

- [x] STAB-001-A: `DEBUGGING.md` Format + zorunlu alanlar; `pala_memory` parser;
  stub gövdesi; AGENTS/skill referans işareti.
- [x] STAB-001-B: Dar sözleşme testleri (kırmızı→yeşil) + self-audit `debugging_brain`.
- [x] STAB-001-C: Dar kapı `test_pala_tools` + `test_plugin_experience` (+ yeni testler).
- [x] STAB-001-D: Tam `verify.py`; her kırmızı kapıda önce/yanında brain kaydı.
- [x] STAB-001-E: STATUS/PROGRESS kanıt etiketleri; aktif ticket kapanışı.

## M22 — Fork demosu elle tutulur olsun (insan planı)

**Neden:** Release/commit beklemeden ürünü daha kullanılabilir yapmak. Fork
eden veya vibe kullanıcı Status’u açınca “çalışıyor” hissi almalı; bilinen
hatalar oturumda unutulmamalı.

**Şu an tek sonraki iş:** Yok (M22 kapandı). Sonraki seçim: commit/release
veya M10 / DEMO-005 — owner karar verir.

### A — Demo Status paneli (DEMO-003 / DEMO-004)

- **Amaç:** Seed sonrası durum sayfasında aktif ticket ve üç zaman çizgisi olayı
  görünsün; bunu test kanıtlasın (gözle “galiba” yetmez).
- **Yapılacaklar:**
  - Seed → Status HTML zincirini tek fonksiyonla doğrula
  - “Şimdi” satırında ticket + sonraki iş net olsun
  - Demo PLAN/STATUS’u bu kanıtla kapat
- **Bitti sayılır:** Sözleşme testi yeşil; self-audit demo kapısı HTML’i de
  kontrol eder; demo STATUS’ta Status HTML = `passed`

### B — Hata beyni oturumda görünsün

- **Amaç:** `DEBUGGING.md` yalnız dosyada durmasın; oturum ve durum sayfası
  açık incident sayısını kısa göstersin.
- **Yapılacaklar:**
  - Parser özeti (açık / kapalı sayı)
  - SessionStart mesajına kısa `debug_open=…` (800 karakter sınırı korunur)
  - Status HTML’de “Hata beyni” satırı
- **Bitti sayılır:** Dar unittest + self-audit yeşil; hook hâlâ ağ/test
  başlatmaz

### C — Bilerek yapılmayanlar (bu tur)

- Commit / push / GitHub `v0.8.0` release
- M10 RTK/MCP canary
- İkinci orkestratör veya büyük yeni ürün yüzeyi

- [x] M22-A: Demo Status HTML kanıtı + DEMO-003/004 kapanışı
- [x] M22-B: Hata beyni özeti SessionStart + Status
- [x] M22-C: `verify.py` tam yerel kapı; STATUS/PROGRESS güncellemesi

## M23 — Release’e sağlam çık

**Neden:** Yeni özellik yok. Amaç içeriye doğru hatasız çıkmak: GitHub ile
uzlaş, sürüm yalanı olmasın, kapı yeşil olsun, ZIP üret, yayın için tek onay
beklesin.

**Şu an tek sonraki iş:** Owner’a sor — Commit + tag + GitHub `v0.8.0`
release yapılsın mı? (Bu turda yayın yok; yerel kapı yeşil.)

**Bitti sayılır:** `verify.py` `passed` + soft-claim/self-audit `passed` +
taşınabilir ZIP tekrar üretildi (SHA STATUS’ta) + STATUS’ta yayımlanmamış
şey `passed` yazılmıyor + `v0.8.0` GitHub release hâlâ `not-run` (onay yoksa).

### A — Remote uzlaştır

- `git fetch` + `origin/main` vs yerel; eksik commit varsa stash ile birleştir
- Son yayın `v0.7.1` notları / açık PR gözden geçir
- README yeşil rozet / indirme linki yayımlanmamış sürümü iddia etmesin

### B — Release kapısı / hatasız iç

- Manifest / CHANGELOG / STATUS sürüm metinleri `0.8.0` kaynak; GitHub yayın
  iddiası yok
- Dar unittest → kırmızıysa `DEBUGGING.md` INC → düzelt
- Tam `verify.py` + Doctor/self-audit soft claim
- M10 RTK/MCP yok (release blokörü değil)

### C — Paket + insan checklist

- CHANGELOG `[0.8.0]` net
- Portable ZIP (verify yolu) + SHA kanıtı
- İnsan adımları: Install → Doctor → `/hooks` → demo seed → self-audit
  (`docs/RELEASE_0_8_0_CHECKLIST.md`)
- Commit / tag / `gh release create` **yok** (ayrı onay)

- [x] M23-A: Remote reconcile + README dürüstlüğü
- [x] M23-B: Sözleşme + `verify.py` yeşil; INC yalnız gerçek arızada
- [x] M23-C: ZIP SHA + checklist; yayın onayı bekler
  (`v0.8.0` GitHub release: `not-run`)

## M24 — Ajan görevleri ile release-içi tamamlama

**Neden:** Yerel 0.8.0 zaten hazır (M21–M23). Bu tur yayın değil; ajanların
görev kartlarıyla çalışabilir hale gelmesi ve release-içi yüzeyin zayıf
kalan yerlerinin kapanması. Commit / tag / GitHub release yok.

**Şu an tek sonraki iş:** Yok (M24 kapandı). Sonraki seçim: owner’a
commit + tag + GitHub `v0.8.0` release sorulsun mu?

**Bitti sayılır:** Tüm M24-T* kartları `passed` veya dürüst `not-run`;
`verify.py` `passed`; GitHub `v0.8.0` hâlâ `not-run`.

### Aktif ajanlar

| Ajan | Rol |
| --- | --- |
| **Ajan-Plan** | Bellek / STATUS / PLAN tutarlılığı; kart panosu gerçeğe uyum |
| **Ajan-Kapı** | verify, self-audit, hata beyni, soft-claim, sürüm dürüstlüğü |
| **Ajan-Yüzey** | fork pack, vibe first session, demo Status, presence UX |
| **Ajan-Sözleşme** | AGENTS.md, skill referansları, geleceğe task-card formatı |

### Gelecekte multitask nasıl çalışır (kısa)

1. Owner veya orkestratör `PLAN.md` içine `M*-T*` görev kartı yazar
   (Sahip ajan, Amaç, Dosyalar, Bitti sayılır, Bağımlılık, Kanıt).
2. Her ajan işe başlamadan: `STATUS.md` → aktif milestone’daki kendi
   `M*-T*` kartları → `DEBUGGING.md` okur; **tek task ID** seçer.
3. Dosya sahipliği çakışmayan kartlar paralel yürür; STATUS/PLAN’ı
   orkestratör (veya Ajan-Plan) sonda uzlaştırır.
4. Soft “bitti” yok — kanıt etiketi zorunlu. Hook hâlâ test/ağ başlatmaz.

### Görev kartları

#### M24-T1 — Görev panosu gerçeğe otursun
- **Sahip ajan:** Ajan-Plan
- **Amaç:** PLAN/STATUS/PROGRESS’te M24 kartları gerçek durumla uyumlu olsun.
- **Dosyalar:** `PLAN.md`, `STATUS.md`, `PROGRESS.md`
- **Bitti sayılır:** Üstte tek sonraki iş net; M23 kapalı, M24 aktif; kart
  kanıtları dürüst (`passed` / `not-run`).
- **Bağımlılık:** Yok (önce yazılır)
- **Kanıt:** `passed`

#### M24-T2 — Release-içi kapı + ajan-görev denetimi
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** 0.8.0 prep metinleri dürüst kalsın; PLAN’daki task kartları
  parse/self-audit ile fail-closed doğrulansın.
- **Dosyalar:** `CHANGELOG.md`, `scripts/pala_memory.py`,
  `scripts/pala_self_audit.py`, `scripts/test_pala_memory.py`,
  `scripts/test_pala_self_audit.py`, `DEBUGGING.md`
- **Bitti sayılır:** Sözleşme testi kırmızı→yeşil; self-audit’te
  `agent_tasks` kapısı; CHANGELOG `[0.8.0]` M24 notu; GitHub yayın iddiası yok.
- **Bağımlılık:** M24-T1 plan metni kaydedilmiş olmalı
- **Kanıt:** `passed` (`parse_agent_task_cards`; self-audit `agent_tasks=cards=5`)

#### M24-T3 — Fork / vibe / demo çoklu-görev netliği
- **Sahip ajan:** Ajan-Yüzey
- **Amaç:** İnsan yüzeyi “hangi görev, kim”i göstersin; ikinci ürün olmasın.
- **Dosyalar:** `docs/FORK_PACK.md`, `docs/VIBE_FIRST_SESSION.md`,
  `CONTRIBUTING.md`, `examples/demo-software-project/STATUS.md`,
  `examples/demo-software-project/PLAN.md`,
  `examples/demo-software-project/AGENTS.md`
- **Bitti sayılır:** VIBE/FORK aktif task ID okumayı söyler; demo STATUS’ta
  örnek ajan→görev tablosu; presence iddiası yok.
- **Bağımlılık:** Yok (T1 ile paralel dosya seti)
- **Kanıt:** `passed` (metin + demo tablo; seed Status HTML bozulmadı)

#### M24-T4 — Sözleşme: ajan task ID seçsin
- **Sahip ajan:** Ajan-Sözleşme
- **Amaç:** AGENTS + skill bellek sözleşmesi “önce STATUS → aktif kartlar →
  DEBUGGING; bir task ID seç” desin.
- **Dosyalar:** `AGENTS.md`,
  `skills/pala-project-finisher/SKILL.md`,
  `skills/pala-project-finisher/references/project-memory.md`,
  `skills/pala-project-finisher/references/project-memory-contract.md`,
  `docs/PALA_0_5_MEMORY_CONTRACT.md`
- **Bitti sayılır:** Metinler task-card formatını ve kanıt etiketlerini
  işaretler; ikinci orkestratör ürünü yok.
- **Bağımlılık:** Yok (T2 ile dosya çakışması yok)
- **Kanıt:** `passed` (AGENTS bölümü + skill ≤450 kelime; phrase korundu)

#### M24-T5 — Tam yerel kapı
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Her şey yeşil olmadan M24’ü kapatma; arızada INC yaz.
- **Dosyalar:** `STATUS.md` (kanıt), `DEBUGGING.md` (yalnız gerçek arıza)
- **Bitti sayılır:** `py -3 scripts/verify.py` → `passed`; soft-claim yok.
- **Bağımlılık:** M24-T2, M24-T3, M24-T4
- **Kanıt:** `passed` (234 test + self-audit; ZIP
  `F626B3EBDE7CF71D9A752B3CECC6B2B8019418596C83FBD976AEC7F7CF6CDC6E`)

- [x] M24-T1: Görev panosu + ajan tablosu
- [x] M24-T2: `agent_tasks` parse/self-audit
- [x] M24-T3: Fork/vibe/demo netliği
- [x] M24-T4: AGENTS/skill task ID sözleşmesi
- [x] M24-T5: Tam `verify.py` (INC-20260808-skill-budget-m24 fixed)

### Bilerek yapılmayanlar (M24)

- M10 RTK / Context7-Playwright MCP genişletmesi
- ChatGPT Plus install, ikinci skill ürünü, büyük yeni özellik
- (Yayın M26’ya taşındı — owner “release olana kadar uygula” yetkisi)

## M26 — v0.8.0 GitHub release (2026-08-08)

**Durum:** Aktif. M21–M24 yerel hazır; tek sonraki iş = commit → push → tag →
`gh release create` + portable ZIP. M25 uygulama yok.

### Görev kartları

#### M26-T1 — Plan/STATUS: tek sonraki iş = release
- **Sahip ajan:** Ajan-Plan
- **Amaç:** PLAN/STATUS/PROGRESS’te M26 kartları ve tek sonraki iş release olsun.
- **Dosyalar:** `PLAN.md`, `STATUS.md`, `PROGRESS.md`
- **Bitti sayılır:** M24 kapalı işaretli; M26 aktif; M25 hâlâ DRAFT.
- **Bağımlılık:** M24-T5
- **Kanıt:** `passed`

#### M26-T2 — Final verify + dürüst kanıt
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Release öncesi `verify.py` yeşil; soft-claim yok.
- **Dosyalar:** `STATUS.md` (kanıt), `DEBUGGING.md` (yalnız gerçek arıza)
- **Bitti sayılır:** `py -3 scripts/verify.py` → `passed`; ZIP SHA kaydı.
- **Bağımlılık:** M26-T1
- **Kanıt:** `passed` (234 test + self-audit; ZIP
  `3EA17A1CEFF7DEEBF906D03184D9B9F09F800B4B64B4AD0D880AD30C22A6916E`)

#### M26-T3 — Commit (secretsız)
- **Sahip ajan:** Ajan-Yayın
- **Amaç:** 0.8.0 kaynak ağacını tek release commit’inde topla.
- **Dosyalar:** (release ağacı; `.env`/pem/secret yok)
- **Bitti sayılır:** `git status` temiz (veya yalnız post-release docs); commit
  mesajı neden odaklı.
- **Bağımlılık:** M26-T2
- **Kanıt:** `passed` (`c192ff3`)

#### M26-T4 — Push main
- **Sahip ajan:** Ajan-Yayın
- **Amaç:** `origin/main` ile release commit’i hizala; force push yok.
- **Dosyalar:** (git remote)
- **Bitti sayılır:** `git push` başarılı; branch tracking güncel.
- **Bağımlılık:** M26-T3
- **Kanıt:** `passed`

#### M26-T5 — Tag + GitHub release + ZIP
- **Sahip ajan:** Ajan-Yayın
- **Amaç:** Annotated `v0.8.0` + `gh release create` + portable ZIP asset.
- **Dosyalar:** (tag/release; asset `pala-project-studio-0.8.0.zip`)
- **Bitti sayılır:** `gh release view v0.8.0` başarılı; ZIP indirilebilir.
- **Bağımlılık:** M26-T4
- **Kanıt:** `passed` (https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.0)

#### M26-T6 — STATUS: release kanıtı
- **Sahip ajan:** Ajan-Plan
- **Amaç:** STATUS/CHANGELOG/README’de GitHub release `passed` + URL; gerekirse
  ikinci docs commit.
- **Dosyalar:** `STATUS.md`, `CHANGELOG.md`, `README.md`, `PROGRESS.md`
- **Bitti sayılır:** Yeşil rozet + release URL; soft `not-run` kalktı.
- **Bağımlılık:** M26-T5
- **Kanıt:** `passed`

- [x] M26-T1: Plan panosu
- [x] M26-T2: Final verify
- [x] M26-T3: Commit
- [x] M26-T4: Push main
- [x] M26-T5: Tag + gh release
- [x] M26-T6: Evidence docs

### Bilerek yapılmayanlar (M26)

- M25 Cursor/CLI ortak hafıza ürünü
- M10 RTK / MCP genişletmesi
- Force push / git config / secret paketleme

## M25 — Ortak hafıza (Codex + Cursor + CLI) — tamamlandı (2026-08-08)

**Durum:** Uygulandı (MVP). Kanıt: T2–T5 `passed`. Bulut sync yok (ADR-017).

**Neden (tek cümle):** Bugün Pala Codex plugin’i olarak yaşar; Cursor’da
“kurulu Pala plugin” yok. Aynı makinede Codex + Cursor + CLI aynı çalışma
hafızasını görsün.

**Bugünkü gerçek (araştırma, 2026-08-08):**

| Parça | Gerçek |
| --- | --- |
| Ürün hedefi | Codex Work / CLI plugin (`PROJECT.md`, ADR-001) |
| Cursor’da Pala | Yok — repoda `.cursor/` kurulumu, Cursor skill/hook paketi yok |
| Kaynak geliştirme | Owner çoğu zaman Cursor’da bu repoyu düzenler; runtime yüzey hâlâ Codex |
| Ortak DB | `%USERPROFILE%\Desktop\Codex\pala.sqlite` (`PALA_DB_PATH` / `PALA_CATALOG_ROOT`) |
| DB içeriği | `projects`, `provisions`, `events`, `meta` — secretsız katalog + zaman çizelgesi |
| Proje hafızası | Klasör dosyaları: `STATUS` / `PLAN` / `PROGRESS` / `AGENTS` (ADR-012) |
| Oturum sahipliği | Proje-içi `.codex/plugin-data/pala/v3/` JSON (`pala_store`) — SQLite değil |
| Hook | Codex `hooks.json` → `pala_hook.py`; ağ/test/build yok; DB’ye yazmaz |
| Taşınabilir skill notu | `docs/PALA_EVERYWHERE.md`: Claude/Cursor için SKILL çekirdeği **ileride**; aynı UX iddiası yok |

**İnce mimari (MVP):**

```text
[ Proje klasörü: STATUS/PLAN/… ]     ← kaynak gerçek (çalışma belleği metin)
              ↑ okur / yazar (agent + CLI)
[ pala.sqlite  tek yol, aynı makine ] ← projeler-arası katalog + olaylar
              ↑ aynı Python API (pala_db / catalog / report / state)
   ┌──────────┼──────────┐
Codex plugin   Cursor yüzeyi   CLI (pala_* / Install)
(hooks+skill)  (rules/skill;   (Status, memory, seed)
               hook ayrı veya yok)
```

**Paylaşılır:** DB yolu sözleşmesi, katalog/olay şeması, memory contract okuma
sırası, kanıt etiketleri, Status HTML üretimi, secretsız export
(`pala-catalog.json` / `INDEX.md`).

**Yüzeye özel kalır:** Codex marketplace + `/hooks` trust; Cursor rule/skill
keşfi; host-specific SessionStart biçimi; RTK PreToolUse rewrite.

**Sync modeli:** Tek makine, tek dosya. Cloud multi-user **yok** (ADR-015).
Taşıma = aynı `PALA_DB_PATH` veya Desktop/Codex klasörünü kopyala; migration
zaten `migrate_from_json` + mevcut yol override’ları.

**MVP vs sonra**

| MVP (M25) | Sonra (ayrı ADR) |
| --- | --- |
| Tek DB yolu + CLI’nin her yüzeyden aynı store’u okuması | Cursor native hook parity |
| İnce taşınabilir skill çekirdeği (agentskills) | Claude Code tam paket |
| Cursor’da rules/AGENTS ile “önce STATUS oku” | İkinci orkestratör / sync SaaS |
| Doktor: “hangi yüzey hazır?” dürüst rapor | Bulut veya çok kiracı DB |

### Görev kartları (uygulandı — 2026-08-08)

#### M25-T1 — Ajan-Araştır: bugünkü gerçek haritası
- **Sahip ajan:** Ajan-Araştır
- **Amaç:** Codex vs Cursor vs CLI / DB yolu / ADR sınırlarını tek doğru özetle.
- **Dosyalar:** (salt okuma) `PROJECT.md`, `DECISIONS.md`, `docs/PALA_EVERYWHERE.md`,
  `scripts/pala_db.py`, hook/skill yüzeyleri
- **Bitti sayılır:** Bu PLAN bölümündeki “Bugünkü gerçek” tablosu kanıtlı; yalan
  “Cursor’da çalışıyor” yok.
- **Bağımlılık:** Yok
- **Kanıt:** `passed` (bu turda araştırma yazıldı; ürün uygulaması yok)

#### M25-T2 — Store sözleşmesini yüzeyler için dondur
- **Sahip ajan:** Ajan-Sözleşme
- **Amaç:** “Tek store API = `pala_db` + env yolu; hook yazmaz; secret yok”u
  ADR notu / kısa sözleşme maddesi olarak kilitle (kod şişirmeden).
- **Dosyalar:** `DECISIONS.md` (yeni ADR taslağı veya ADR-015 ek not),
  gerekirse 1 sayfa `docs/PALA_SHARED_MEMORY.md`
- **Bitti sayılır:** Paylaşılır / paylaşılmaz listesi ve migration yolu yazılı;
  bulut sync önerilmez.
- **Bağımlılık:** M25-T1
- **Kanıt:** `passed`

#### M25-T3 — CLI tek kapı: memory / status / doctor yüzey etiketi
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Mevcut `pala_state` / `pala_report` / Doctor çıktısında “store
  yolu + hangi host bekleniyor” net olsun; yeni daemon yok.
- **Dosyalar:** `scripts/pala_state.py`, `scripts/pala_report.py`,
  `scripts/pala_installer.py` (Doctor metni), ilgili dar testler
- **Bitti sayılır:** Aynı `pala.sqlite` yolunu CLI her yerden gösterir; soft
  “Cursor kurulu” iddiası yok.
- **Bağımlılık:** M25-T2
- **Kanıt:** `passed`

#### M25-T4 — Cursor ince yüzey (skill/rules only)
- **Sahip ajan:** Ajan-Yüzey
- **Amaç:** agentskills uyumlu ince `SKILL.md` + isteğe bağlı Cursor rule:
  memory contract + “CLI ile Status/DB”; Codex hook’larını Cursor’da varmış gibi
  satma.
- **Dosyalar:** yeni ince skill/rules taslağı (konum T2’de karar),
  `docs/PALA_EVERYWHERE.md` güncellemesi
- **Bitti sayılır:** Cursor’da agent STATUS okuyup CLI Status açabilsin; Install
  “Codex plugin” iddiasını Cursor’a taşımaz; sözleşme testi veya self-audit
  dürüst `configured-not-verified` / `not-run` kullanır.
- **Bağımlılık:** M25-T2
- **Kanıt:** `passed`

#### M25-T5 — Codex regress + tek makine kanıtı
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Codex plugin davranışı bozulmadan aynı DB’yi üç yüzeyin okuduğunu
  tek makinede kanıtla (Cursor = skill/rules; Codex = plugin; CLI = script).
- **Dosyalar:** `scripts/test_pala_db.py` (+ gerekirse ince entegrasyon),
  `STATUS.md` / `PROGRESS.md` kanıt satırları
- **Bitti sayılır:** Dar test yeşil; owner canary: aynı `pala.sqlite` yolu üç
  yüzeyden görünür; hook hâlâ ağ/test/build başlatmaz.
- **Bağımlılık:** M25-T3, M25-T4
- **Kanıt:** `passed`

### Bilerek yapılmayanlar (M25)

- Bulut / çok kullanıcı sync DB
- Cursor’da Codex hook parity veya “Pala Cursor’da kurulu plugin” yalanı
- Ruflo / ikinci orkestör / MCP-zorunlu hafıza sunucusu
- Secret / transcript’i SQLite’a yazma
- Bu turda yeni GitHub release (ayrı yetki)

## M27 — Install artifact contract + 0.8.1 prep (Wave A)

Amaç: Kurulu marketplace “sağlıklı” demeden yalan söylemesin (issue #13);
runtime verify + uncommitted M25/M10 → `0.8.1` kaynak hazırlığı. Push/tag/release
ayrı owner yetkisi.

### Görev kartları

#### M27-T1 — Fingerprint allowlist (#13)
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** `tree_fingerprint` yalnız allowlisted bundle; `__pycache__` drift yok.
- **Dosyalar:** `scripts/pala_installer.py`, `scripts/test_pala_installer.py`
- **Bitti sayılır:** `test_installed_fingerprint_stable_after_pycache` yeşil.
- **Bağımlılık:** Yok
- **Kanıt:** `passed`

#### M27-T2 — Runtime self-audit + verify installed
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** `--profile runtime` ve `verify.py --mode installed` lean install’ta exit 0.
- **Dosyalar:** `scripts/pala_self_audit.py`, `scripts/verify.py`,
  `docs/INSTALL_ARTIFACT_CONTRACT.md`, ilgili testler
- **Bitti sayılır:** Kopya bundle + marketplace runtime audit `passed`.
- **Bağımlılık:** M27-T1
- **Kanıt:** `passed`

#### M27-T0 — Live Codex canary + cold-start
- **Sahip ajan:** Ajan-Canary
- **Amaç:** SessionStart smoke + Doctor ready; cold-start ms JSON (yüzde yok).
- **Dosyalar:** `STATUS.md`, `scripts/pala_cold_start.py`
- **Bitti sayılır:** Hook CLI smoke `passed`; `/hooks` UI `configured-not-verified`.
- **Bağımlılık:** M27-T2
- **Kanıt:** `passed` (CLI); UI `configured-not-verified`

#### M27-T3 — 0.8.1 prep + CI artifact smoke + checklist
- **Sahip ajan:** Ajan-Paket
- **Amaç:** Manifest `0.8.1`, CHANGELOG, README honesty, CI smoke job, checklist.
- **Dosyalar:** `.codex-plugin/plugin.json`, `CHANGELOG.md`, `README.md`,
  `.github/workflows/quality.yml`, `docs/CODEX_PLUGIN_CHECKLIST.md`
- **Bitti sayılır:** Kaynak bump + docs; `v0.8.1` release `not-run`.
- **Bağımlılık:** M27-T1, M27-T2
- **Kanıt:** `passed` (prep); release/Actions `not-run` / `configured-not-verified`

### Bilerek yapılmayanlar (M27 Wave A)

- `gh release` / tag `v0.8.1` / issue #13 close (owner-only)
- Wave B `pala_debug_gate`
- Soft hız yüzdesi iddiası

## M28 — Memory-as-Governance (Wave B)

Amaç: Açık `INC-*` varken SessionStart/begin/checkpoint uyarı zorunlu;
isteğe bağlı complete fail-closed; `memory_hit_rate` proxy; stop-condition
matrix satırlarını sözleşme testiyle doldur. Hooks UI trust `passed` sayılmaz.

### Görev kartları

#### M28-T1 — pala_debug_gate CLI + hook yüzeyi
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Açık INC varken begin/checkpoint/SessionStart metninde DEBUG GATE.
- **Dosyalar:** `scripts/pala_debug_gate.py`, `scripts/pala_hook.py`,
  `scripts/pala_state.py`, `scripts/test_pala_debug_gate.py`
- **Bitti sayılır:** `test_pala_debug_gate` uyarı + SessionStart gate yeşil.
- **Bağımlılık:** M27 Wave A
- **Kanıt:** `passed`

#### M28-T2 — Attempt kaydı + complete fail-closed
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Optional `Attempts` alanı; SQLite `kind=debug_attempt`; complete
  fail-closed (açık INC + related files + passed).
- **Dosyalar:** `scripts/pala_db.py`, `scripts/pala_memory.py`,
  `DEBUGGING.md`, `scripts/pala_debug_gate.py`
- **Bitti sayılır:** `debug_attempt` event + fail-closed contract yeşil.
- **Bağımlılık:** M28-T1
- **Kanıt:** `passed`

#### M28-T3 — memory_hit_rate proxy
- **Sahip ajan:** Ajan-Ölçüm
- **Amaç:** Cold/canary: `debug_open>0` ve DEBUGGING okundu → ratio (yüzde yok).
- **Dosyalar:** `scripts/pala_cold_start.py`, `scripts/pala_debug_gate.py`
- **Bitti sayılır:** `memory_hit_rate` JSON alanı; `%` yok.
- **Bağımlılık:** M28-T1
- **Kanıt:** `passed`

#### M28-T4 — Stop-condition matrix + demo
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Unregistered / bad evidence / hooks UI trust satırları
  `passed|partial|configured-not-verified` (N/A erit).
- **Dosyalar:** `scripts/test_pala_debug_gate.py`,
  `outputs/PALA_FEATURE_MATRIX.csv`,
  `examples/demo-software-project/reports/STOP_SCENARIOS.md`
- **Bitti sayılır:** Stop contract testleri yeşil; matrix güncellendi.
- **Bağımlılık:** M28-T1
- **Kanıt:** `passed` (contract); hooks UI `configured-not-verified`

### Bilerek yapılmayanlar (M28 Wave B)

- Wave C canlı Codex A/B 2.0
- Hooks `/hooks` UI trust = `passed`
- Tam `verify.py` / push / PR / release

## Wave E — Multi-host proof (M25 olgunlaştırma) — 2026-08-08

**Durum:** Tamamlandı (olgunlaştırma; M25 greenfield değil).

| Kapı | Kanıt |
| --- | --- |
| Aynı sqlite hit + unknown miss | `scripts/test_pala_shared_memory.py` |
| AGENTS tek kaynak; Cursor rule ince | `AGENTS.md` + `.cursor/rules/pala-memory.mdc` |
| Portable skill drift | self-audit `shared_memory` + skill markers |
| Doctor `shared_store` dokümanı | `docs/PALA_SHARED_MEMORY.md` |

**Bilerek yapılmayanlar:** Wave B gate; Cursor hook parity; bulut sync; push/release.

## M29 — Codex→Cursor Gate 0 + friction memory (Wave D)

Amaç: P0 skill-path / lifecycle / fail-closed düzeltmelerini otomatik
Windows-dostu E2E ile kanıtla (`artifacts/codex-compat/p0-smoke.json`);
aynı path/failure tekrarını SQLite komut hafızasıyla engelle; cold-session
packet + doc budget + capability preflight. Push/PR/release ve uzak Codex
makinesi kurulumu bu milestonda yok.

### Görev kartları

#### M29-Gate0 — P0 smoke E2E artifact
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** Temp git worktree üzerinde launcher, no `../../scripts`,
  register→begin→checkpoint→context→complete, fail-closed complete,
  path-failure ikinci oturumda tekrar etmeme, `pala kontrol et` structured
  statuses; çıktı `artifacts/codex-compat/p0-smoke.json`.
- **Dosyalar:** `scripts/pala_p0_smoke.py`, `scripts/test_pala_p0_friction.py`,
  `artifacts/codex-compat/p0-smoke.json`, `STATUS.md` / `PROGRESS.md`
- **Bitti sayılır:** Runner exit 0; critical rows `passed`; focused unittest yeşil.
- **Bağımlılık:** M29-T2 (path memory satırı için yeterli entegrasyon)
- **Kanıt:** `passed`

#### M29-T1 — Evidence-first cold-session packet (≤2 KB)
- **Sahip ajan:** Ajan-Hafıza
- **Amaç:** Yeni oturumda ≤2 KB paket: ticket/goal, branch/worktree/base
  commit, last verified, changed files, blocker, next action, do-not-retry,
  freshness + evidence source. Öncelik:
  `source+Git+test > Pala SQLite > Markdown > prior chat`. Çelişkide
  `stale-context`; eski state uygulanmaz.
- **Dosyalar:** `scripts/pala_cold_packet.py`, `scripts/pala_hook.py`,
  `scripts/pala_state.py`, `hooks/hooks.json`, `scripts/test_pala_cold_packet.py`
- **Bitti sayılır:** Packet SessionStart/context’te; minimal ≤2 KB; stale test yeşil.
- **Bağımlılık:** M29-Gate0 + M29-T2
- **Kanıt:** `passed`

#### M29-T2 — Failed command/path memory guard
- **Sahip ajan:** Ajan-Kapı
- **Amaç:** SQLite tool_attempts: command_family + env + failure_class;
  tekrarında prior resolution, default block / `--approve-retry`,
  DEBUGGING özeti, context/debug_gate “do not retry”.
- **Dosyalar:** `scripts/pala_db.py`, `scripts/pala_cmd_memory.py`,
  `scripts/pala_debug_gate.py`, `scripts/pala_state.py`, `scripts/pala_hook.py`,
  `scripts/test_pala_cmd_memory.py`
- **Bitti sayılır:** Aynı path failure ikinci cold session’da bloklanır; test yeşil.
- **Bağımlılık:** M28
- **Kanıt:** `passed`

#### M29-T3 — Context/doc budget profiles
- **Sahip ajan:** Ajan-Hafıza
- **Amaç:** `minimal` | `standard` | `milestone` profilleri; basit ticket
  AGENTS+PLAN+PROGRESS+TOOLING+DEBUGGING’i otomatik okumaz. Her kayıt:
  freshness, scope, confidence, superseded_by, estimated_token_cost.
  Bütçe aşımında eski log/unproven düşer; risk/test/blocker korunur.
- **Dosyalar:** `scripts/pala_cold_packet.py`, `scripts/test_pala_cold_packet.py`
- **Bitti sayılır:** Profile seçimi + budget trim testleri yeşil.
- **Bağımlılık:** M29-T1
- **Kanıt:** `passed`

#### M29-T4 — Capability preflight + parallel safety
- **Sahip ajan:** Ajan-Hafıza
- **Amaç:** Salt-okunur capability manifest (OS/shell, Git/Node/Python/test,
  browser, network, trusted dir, write/delete/commit/push authority,
  plugin/launcher, worktree/branch/base_commit). Eksik araç →
  `not-run|blocked|configured-not-verified` (asla sahte passed). Checkpoint:
  session_id, worktree, branch, base_commit, file_scope; başka worktree →
  reconcile.
- **Dosyalar:** `scripts/pala_cold_packet.py`, `scripts/pala_state.py`,
  `scripts/pala_hook.py`, `scripts/test_pala_cold_packet.py`
- **Bitti sayılır:** Manifest + parallel conflict testleri yeşil; verify
  installed bu turda `not-run` kabul.
- **Bağımlılık:** M29-T1
- **Kanıt:** `passed` (kaynak); `verify.py --mode installed` = `not-run`

### Owner-only kalanlar (M29 dışı yetki)

- Marketplace Update sonrası canlı Codex P0 / A/B re-measure: `not-run`
- Hooks `/hooks` UI trust: `configured-not-verified`
- `verify.py --mode installed` / tam `verify.py`: `not-run`
- Soft “A/B fixed” yok (canlı hâlâ 0.8.0 ölçümü)

### Bilerek yapılmayanlar (M29)

- Uzak Codex makinesine Install/Update/push/PR/release
- Soft “A/B issues fixed” iddiası
- Hooks UI trust = `passed` (CLI’dan iddia yok)

## M30 — Vibe Codex host-fit (2026-08-09)

Amaç: Codex host `additionalContext` ~1000-token sert tavanı + progressive
disclosure altında vibe first-session’ı truncation-safe ve ince skill ile
kilitlemek. Plan:
`docs/superpowers/plans/2026-08-09-vibe-codex-host-fit.md`.

Kaynak uygulama (branch `feat/m30-vibe-codex-host-fit`): limits doc, shared
`pala_tokens`, SessionStart çift bütçe, thin skill + `references/kontrol-et.md`,
host-fit contract tests, evidence bind. Checkpoint ayrıca
`.codex/plugin-data/` yollarını workflow gibi hariç tutar (v3 ticket gürültüsü).

| Paket | Kanıt |
| --- | --- |
| Limits + tokens + dual budget + thin skill | `passed` |
| Focused unittest / installed verify / Gate0 9/9 | `passed` |
| Tam source verify | `not-run` |
| Hooks UI trust | `configured-not-verified` |

### Bilerek yapılmayanlar (M30)

- `/hooks` UI trust = `passed`
- `v0.8.1` tag/release
- Soft “A/B fixed”
- Marketplace sync of M30 without Install after merge

## M31 — Superpowers continuity for Codex (2026-08-09)

Amaç: Superpowers process skill’lerinden Pala ürününe uyan süreklilik boşluklarını
(using ritual, ticket plan/execute, INC- debug, verify-before-done) ince
`references/` + contract test ile kapatmak. Design:
`docs/superpowers/specs/2026-08-09-pala-vs-superpowers-continuity-design.md`.

#### M31-T1 — Continuity refs + skill pointer

- **Sahip ajan:** Cursor agent
- **Amaç:** Pala continuity refs + tests + local ZIP; Superpowers wholesale yok.
- **Dosyalar:** `docs/superpowers/specs/2026-08-09-pala-vs-superpowers-continuity-design.md`, `skills/pala-project-finisher/references/using-pala.md`, `skills/pala-project-finisher/references/plan-tickets.md`, `skills/pala-project-finisher/references/execute-tickets.md`, `skills/pala-project-finisher/references/debugging-inc.md`, `skills/pala-project-finisher/references/quality-gates.md`, `skills/pala-project-finisher/references/specialist-routing.md`, `skills/pala-project-finisher/SKILL.md`, `scripts/test_plugin_experience.py`, `scripts/test_pala_tools.py`, `STATUS.md`, `CHANGELOG.md`, `PLAN.md`, `docs/README.md`
- **Bitti sayılır:** Focused unittest + `verify.py` passed; Desktop final ZIP+SHA; local commit; no push; `/hooks` trust claimed değil.
- **Bağımlılık:** M30
- **Kanıt:** `passed` (continuity contract + host_fit; verify/ZIP this turn)

- [x] M31-T1: Continuity refs + skill pointer

### Bilerek yapılmayanlar (M31)

- Superpowers skill tree wholesale copy
- Claude-only subagent/companion as Codex features
- Push / PR / tag / `/hooks` trust = passed

## M32 — Delivery Quality Engine 0.9 (2026-08-09)

Amaç: Proje-yerel kalite kapılarını keşfet, ticket başına kanıt defteri tut,
checkpoint/complete’te fail-closed kal; hook’tan gate çalıştırma.

#### M32-T1 — pala_quality engine + packaging secret allowlist

- **Sahip ajan:** Cursor agent
- **Amaç:** `pala_quality` plan/init/record/status; Status HTML beş sinyal;
  portable/install secret-shaped forbid; verify + Desktop final ZIP.
- **Dosyalar:** `scripts/pala_quality.py`, `scripts/test_pala_quality.py`,
  `scripts/pala_state.py`, `scripts/pala_report.py`, `scripts/pala_view.py`,
  `scripts/verify.py`, `scripts/build_portable.py`, `scripts/pala_installer.py`,
  `docs/PALA_0_9_QUALITY_ENGINE.md`, `docs/PALA_0_9_BENCHMARK.md`,
  `STATUS.md`, `CHANGELOG.md`, `PLAN.md`
- **Bitti sayılır:** Quality unittest + packaging contract + `verify.py` passed;
  Desktop `pala-project-studio-0.8.1-final.zip` + SHA; push/PR/tag yok.
- **Bağımlılık:** M31
- **Kanıt:** `passed` (quality 21 + packaging; verify/ZIP this turn)

- [x] M32-T1: Delivery Quality Engine + packaging P1

### Bilerek yapılmayanlar (M32)

- Push / PR / tag / `gh release`
- `/hooks` trust = `passed`

## M33 — Control Panel Modularity + Quality Ratchet (2026-08-09)

Amaç: Delivery Quality Engine'in görünür kontrol yüzeyini küçük, sahipliği net
modüllere ayır; Pala'nın kendi yeni kodunda sert güvenlik ve HTML sözleşmesi
regresyonunu fail-closed tut. Eski M31 workflow kaydı otomatik kapatılmaz;
ayrı bir reconciliation ticket'ında ele alınır.

#### M33-T1 — Status renderer ownership + audit ratchet

- **Sahip ajan:** Codex agent
- **Amaç:** Status renderer'ın section ve karar kartı sorumluluklarını ayırırken
  delivery kararını, mahremiyet varsayılanını ve erişilebilirlik sözleşmesini
  aynen koru; Python test discovery'nin sıfır-test komutunu `passed`a
  dönüştürmeyeceği gerçek bir proje köküne bağla.
- **Dosyalar:** `scripts/pala_view.py`, `scripts/pala_view_sections.py`,
  `scripts/pala_quality.py`, `scripts/test_pala_quality.py`,
  `scripts/test_pala_code_audit.py`, `scripts/test_pala_tools.py`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`,
  `DEBUGGING.md`, `PLAN.md`.
- **Bitti sayılır:** Root renderer 800 satır review eşiğinin altında;
  delivery decision / required gate / privacy / keyboard HTML sözleşmeleri
  korunur; static audit hard-security `passed`; source, portable ve installed
  verify `passed`; `scripts/test_*.py` için discovery komutu gerçekten test
  yüzeyini hedefler, sıfır-test sonucu gate kanıtı olamaz.
- **Bağımlılık:** M32
- **Kanıt:** `py -3 -m unittest scripts.test_pala_tools.PalaViewA11yTests scripts.test_pala_code_audit -v`; `py -3 scripts/verify.py --mode source`; portable ve installed verify.

- [x] M33-T1: Status renderer ownership + audit ratchet

### Bilerek yapılmayanlar (M33-T1)

- `pala_quality`, `pala_state` ve installer'ın geniş refactor'ı
- Stale M31 ticket'ını otomatik abandon/complete etmek
- Commit / push / PR / tag / release / deploy

## M34 — Core install truthfulness (2026-08-09)

Amaç: Pala'nın çekirdek kurulumunu isteğe bağlı uzman araçların ağ, indirme veya
paketleme sonucundan ayır. Kullanıcı açıkça istemedikçe installer uzman araç
kurulumu başlatmaz; eksik ya da başarısız uzman araç çekirdek Pala'nın sağlıklı
kurulduğu gerçeğini gizlemez.

#### M34-T1 — Explicit expert-install boundary

- **Sahip ajan:** Codex agent
- **Amaç:** `Install`, `Update` ve `Repair` için varsayılan yerel-first akışı
  koru; uzman araçları yalnız `-InstallExperts` ile çağır. Uzman worker sonucu
  çekirdeğin exit code'unu devralmaz, ham hata/URL göstermez ve başarısız
  uzmandan sonra yerel model başlatmayı denemez.
- **Dosyalar:** `Install-Pala.ps1`, `scripts/Install-Pala.ps1`,
  `scripts/test_pala_expert_installer.py`, `STATUS.md`, `PROGRESS.md`,
  `DEBUGGING.md`, `PLAN.md`.
- **Bitti sayılır:** PowerShell sözleşme testi varsayılanın expert indirmediğini
  ve expert exit'ini çekirdek exit'i yapmadığını doğrular; gerçek `Repair`
  çekirdek healthy ile exit 0 döner; source, portable ve installed verify
  `passed`.
- **Bağımlılık:** M33-T1
- **Kanıt:** explicit contract test; `Install-Pala.ps1 -Mode Repair`; source,
  portable ve installed verify.

- [x] M34-T1: Explicit expert-install boundary

## M35 — Quality discovery boundary (2026-08-09)

Amaç: Delivery Quality Engine'in salt-okunur proje keşfini ledger, gate ve CLI
politikasından ayır; sabit Git sorgularının kabuksuz ve süre sınırlı olmasını
sağla. Eski M31 workflow kaydı bu ticket'ın dışında kalır.

#### M35-T1 — Bounded discovery owner

- **Sahip ajan:** Codex agent
- **Amaç:** Paket/CI, değişen-yüzey, Git özeti ve Python/UI keşfini
  `pala_quality_discovery.py` sahibine ayır; `pala_quality.py` kamuya açık
  plan/ledger/gate/CLI yüzeyini korur. Git yoksa veya beş saniye içinde cevap
  vermezse plan çökmemeli; asla shell açmamalı.
- **Dosyalar:** `scripts/pala_quality.py`, `scripts/pala_quality_discovery.py`,
  `scripts/test_pala_quality.py`, `scripts/test_pala_code_audit.py`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`, `PLAN.md`.
- **Bitti sayılır:** Ana quality modülü 800 satır review eşiğinin altında;
  hard-security `passed`; `pala_quality` için timeout uyarısı yok; discovery
  timeout ve davranış sözleşmeleri, source/portable/installed verify geçer.
- **Bağımlılık:** M34-T1
- **Kanıt:** focused quality + code-audit tests; `verify.py --mode source`;
  portable ve installed verify.

- [x] M35-T1: Bounded discovery owner

### Bilerek yapılmayanlar (M35-T1)

- `build_quality_plan` içindeki policy dallarını davranış değiştirecek şekilde
  ikinci kez parçalamak
- `pala_state` veya installer'a geniş refactor karıştırmak
- Stale M31 ticket'ını otomatik reconcile/complete etmek
- Commit / push / PR / tag / release / deploy

## M36 — Modified install tree safety (2026-08-09)

Amaç: Pala'nın paket/kurulum iddiasını tam sahipli dosya ağacına bağla.
Kullanıcının eklediği veya değiştirdiği bir dosya varsa Doctor, Repair ve Update
üzerine yazmamalı; uninstall gibi `modified` ile durmalı.

#### M36-T1 — Fail-closed user-file preservation

- **Sahip ajan:** Codex agent
- **Amaç:** Exact manifest dışındaki dosya veya hash değişikliği `modified`
  döndürür; `install_all` Codex mutasyonundan önce durur. Yalnız gerçek
  `__pycache__` altındaki bytecode runtime artığıdır; rastgele `.pyc/.pyo`
  kullanıcı dosyasıdır.
- **Dosyalar:** `scripts/pala_installer.py`, `scripts/test_pala_installer.py`,
  `scripts/build_portable.py`, `docs/PALA_0_9_5_INSTALL_INTEGRITY.md`,
  `STATUS.md`, `PROGRESS.md`, `PLAN.md`.
- **Bitti sayılır:** User-added, changed owned file, dışarıdaki bytecode ve
  update/repair-before-Codex testleri geçer; Doctor `modified` ve tek güvenli
  sonraki adımı gösterir; source/portable/installed verify geçer.
- **Bağımlılık:** M35-T1
- **Kanıt:** focused installer suite; `verify.py --mode source`; portable ve
  installed verify.

- [x] M36-T1: Fail-closed user-file preservation

### Bilerek yapılmayanlar (M36-T1)

- Kullanıcı dosyasını otomatik silmek, taşımak veya bir Pala sürümüyle
  değiştirmek
- Installer'ın geniş bundle/transaction refactor'ı
- Commit / push / PR / tag / release / deploy

## M37 — State Git timeout boundary (2026-08-09)

Amaç: Project-state keşfi ve checkpoint hesaplarında kullanılan Pala-sabit Git
sorgularını tek bir kabuksuz, süre sınırlı yardımcıdan geçir. Git yoksa veya
zaman aşımına uğrarsa workflow semantiğini değiştirmeden muhafazakâr sonuç dön.

#### M37-T1 — Bounded state Git observation

- **Sahip ajan:** Codex agent
- **Amaç:** `git_root`, metin/binary Git sorguları ve ancestry kontrolü tek
  fixed-argv helper kullanır; `shell=False`, beş saniye timeout, missing/timeout
  için mevcut `None` / cwd / `False` fallback'leri korunur.
- **Dosyalar:** `scripts/pala_state.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_code_audit.py`, `docs/PALA_0_9_3_MODULARITY.md`,
  `STATUS.md`, `PROGRESS.md`, `PLAN.md`.
- **Bitti sayılır:** state Git timeout/missing/shell-free contractleri geçer;
  static audit'te `pala_state.py` unbounded process kalmaz; source, portable ve
  installed verify geçer.
- **Bağımlılık:** M36-T1
- **Kanıt:** focused state + code audit; `verify.py --mode source`; portable ve
  installed verify.

- [x] M37-T1: Bounded state Git observation

### Bilerek yapılmayanlar (M37-T1)

- `pala_state` workflow lifecycle/SQLite/main refactor'ı
- Başka modüllerdeki timeout adaylarını bu ticket'a toplamak
- Commit / push / PR / tag / release / deploy

## M38 — Read-only observation boundary (2026-08-09)

Goal: make the local discovery used by cold packets, optional code intelligence,
and GitHub routing bounded and honest, without mixing long-running verification,
smoke, or benchmark behavior into this narrow ticket.

#### M38-T1 — Bounded local observation

- **Sahip ajan:** Codex agent
- **Amaç:** Local Git/UV discovery uses resolved executable, fixed argv,
  `shell=False`, and a five-second timeout. Missing or timed-out commands never
  claim a clean/passed result. The cold packet shares one Git snapshot with its
  capability surface.
- **Dosyalar:** `scripts/pala_cold_packet_git.py`, `scripts/pala_cold_packet.py`,
  `scripts/pala_code_intel.py`, `scripts/pala_github.py`, contract tests, and
  quality/modularity records.
- **Bitti sayılır:** timeout and missing-binary fallback, `dirty=null` partial
  snapshot, shared cold-packet snapshot, and redacted GitHub fallback pass;
  the cold-packet core stays below the 800-line review threshold; source,
  portable, and installed verification pass.
- **Bağımlılık:** M37-T1
- **Kanıt:** focused observation + code-audit tests; source, portable, and
  installed verification.

- [x] M38-T1: Bounded local observation

### Intentionally deferred (M38-T1)

- Optional `code-review-graph` build/update timeout semantics
- Cold-start benchmark exit/timeout evidence schema
- P0 smoke child and `git init` timeout fail-closed behavior
- Release verifier test timeout policy
- Commit / push / PR / tag / release / deploy

## M39 — State Git/checkpoint ownership (2026-08-09)

Amaç: `pala_state` içindeki yalnız Git/checkpoint gözlemini küçük, sahipliği
net bir kardeş modüle çıkar; workflow, belge ve lifecycle kararlarını aynı
public/CLI sözleşmesiyle state çekirdeğinde bırak.

#### M39-T1 — State Git/checkpoint observation owner

- **Sahip ajan:** Codex agent
- **Amaç:** Git root/read/path/digest/checkpoint/ancestry/commit materialization
  `pala_state_git.py` sahibine taşınır ve `pala_state.py` tarafından yeniden
  dışa aktarılır. Fixed argv, `shell=False`, beş saniye timeout, NUL-safe path
  ve missing/timeout muhafazakâr sonuçları korunur.
- **Dosyalar:** `scripts/pala_state.py`, `scripts/pala_state_git.py`,
  `scripts/pala_installer.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_installer.py`, `scripts/test_pala_code_audit.py`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`, `PLAN.md`.
- **Bitti sayılır:** State public/CLI davranışı ve Git timeout sözleşmeleri
  geçer; eski Git/checkpoint tanımları state çekirdeğinde kalmaz; eksik yardımcı
  içeren bundle install öncesi fail-closed olur; source, portable ve installed
  verify geçer.
- **Bağımlılık:** M38-T1
- **Kanıt:** focused state/installer/audit tests; `verify.py --mode source`;
  portable ve installed verify.

- [x] M39-T1: State Git/checkpoint observation owner

### Bilerek yapılmayanlar (M39-T1)

- `pala_state` workflow lifecycle/SQLite/main refactor'ı
- Installer'ın integrity/transaction çekirdeği refactor'ı
- Release verifier, P0 smoke, cold-start veya optional graph timeout semantiği
- Commit / push / PR / tag / release / deploy

## M40 — Installer external Codex bridge (2026-08-09)

Amaç: Installer içindeki dış Codex CLI/marketplace/cache işlemlerini tek bir
owned bridge'e çıkar; bundle bütünlüğü, kullanıcı-dosyası koruması, atomik
replacement ve rollback çekirdekte kalsın.

#### M40-T1 — Codex bridge ownership

- **Sahip ajan:** Codex agent
- **Amaç:** Codex executable discovery, JSON argv, marketplace inventory/cache,
  legacy migration ve add/remove rollback `pala_installer_codex.py` sahibine
  taşınır. Core public API'yi ince wrapperlarla korur ve sibling-path loader ile
  source/portable/installed module cache karışmasını önler.
- **Dosyalar:** `scripts/pala_installer.py`,
  `scripts/pala_installer_codex.py`, `scripts/test_pala_installer.py`,
  `scripts/test_pala_code_audit.py`, `docs/PALA_0_9_3_MODULARITY.md`,
  `STATUS.md`, `PROGRESS.md`, `PLAN.md`.
- **Bitti sayılır:** Codex bridge shell-free/30-second çağrı, existing
  marketplace/rollback contractleri, sibling loader, missing-helper
  fail-closed ve portable member contractleri geçer; source, portable ve
  installed verify geçer.
- **Bağımlılık:** M39-T1
- **Kanıt:** focused installer/audit/runtime tests; `verify.py --mode source`;
  portable ve installed verify.

- [x] M40-T1: Codex bridge ownership

### Bilerek yapılmayanlar (M40-T1)

- Bundle integrity, kullanıcı-dosyası koruması ve transaction/rollback çekirdeği
  refactor'ı
- `pala_state` workflow lifecycle/SQLite/main refactor'ı
- Release verifier, P0 smoke, cold-start veya optional graph timeout semantiği
- Commit / push / PR / tag / release / deploy

## M42 — Quality policy ownership (2026-08-09)

Amaç: Delivery Quality Engine'in plan politikasını ledger, gate ve CLI
cephesinden ayır. Bu bir davranış değişikliği değil; mevcut proje-owned
komut, Playwright, scanner ve risk-yüzeyi kararlarını daha küçük ve
test-edilebilir sahiplerde tutma ticket'ıdır.

#### M42-T1 — Quality plan policy owner

- **Sahip ajan:** Codex agent
- **Amaç:** `pala_quality_policy.py`, salt-okunur discovery'den quality planını
  kurar; contract/native/browser/scanner/risk yardımcıları tek fonksiyonluk
  politika yüzeylerine ayrılır. `pala_quality.py` kamu API'sini, ledger'ı,
  gate kararını ve CLI'yi aynen korur/re-export eder.
- **Dosyalar:** `scripts/pala_quality.py`, `scripts/pala_quality_policy.py`,
  `scripts/pala_installer.py`, `scripts/test_pala_quality.py`,
  `scripts/test_pala_installer.py`, `scripts/test_pala_code_audit.py`,
  `scripts/pala_view_sections.py`, `scripts/test_pala_memory.py`,
  `scripts/test_pala_tools.py`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`, `PLAN.md`.
- **Bitti sayılır:** Planın gate sırası / required / status / command
  sözleşmesi korunur; `build_quality_plan` artık audit function budget'ını
  aşmaz; helper eksik bundle install öncesi fail-closed olur; source,
  portable ve installed verify geçer. Status'taki `n/n` yalnız çalışma
  bağlamı hazırlığıdır; proje ilerlemesi veya teslim yüzdesi değildir.
- **Bağımlılık:** M40-T1
- **Kanıt:** focused quality/installer/audit tests; `verify.py --mode source`;
  portable ve installed verify.

- [x] M42-T1: Quality plan policy owner

### Bilerek yapılmayanlar (M42-T1)

- Quality gate anlamını, scanner'ın ağ sınırını veya ledger kanıt
  modelini değiştirmek
- `pala_state` discovery/lifecycle refactor'ını bu ticket'a karıştırmak
- Commit / push / PR / tag / release / deploy

## M43 — Sıfırdan tek ana plan ve kontrollü teslim (2026-08-09)

**Amaç:** Tarihsel M31 workflow kaydını mevcut kaynak ağaçtan ayır, M33–M42
değişikliklerinin gerçek baseline'ını kanıtla ve kalan kod kalitesi işini
tek-sorumluluk, fail-closed ve release'e hazır bir sırada tamamla.

**Plan kilidi:** Bu kartlar yalnız aşağıdaki bağımlılık sırasıyla yürütülür.
Bir eklenti, hook veya araç yeni bir iş önerebilir; ancak kart sırasını
değiştiremez, test/build/ağ çağrısı başlatamaz ve kanıt üretmiş sayılmaz. Yeni
bir kök neden varsa ilgili kart `blocked` yazılır ve `DEBUGGING.md`ye incident
eklenir; owner açıkça onaylamadıkça yeni kart ya da sıra değişikliği yapılmaz.
Her uygulama turunda yalnız bir açık ticket seçilir.

#### M43-T1 — Sıfırdan uzlaştırma ve kilitli baseline

- **Sahip ajan:** Codex agent
- **Amaç:** Eski `M31-T1` checkpoint/parallel bilgisini canlı `main` HEAD'i ve
  çalışma ağacından güvenli biçimde ayır; M43'ü tek aktif sıra olarak kaydet.
- **Dosyalar:** `.codex/pala-workflow.json`,
  `.codex/plugin-data/pala/v3/tickets/d252f696a71cb4ce35727866fcb1031b22b4de50c3c6a5caa359e3356f5b977a.json`,
  `PLAN.md`, `STATUS.md`, `PROGRESS.md`, `DEBUGGING.md`.
- **Bitti sayılır:** `pala_state context` aktif ticket, goal, next action ve
  Git fingerprint için birbirini tutarlı gösterir; eski M31 kanıtı M43'e
  taşınmaz; açık incident yoksa uydurulmaz; M43-T2 tek sonraki iş olur.
- **Bağımlılık:** none.
- **Kanıt:** `py -3 scripts/pala_state.py context --cwd .`;
  `py -3 scripts/pala_state.py validate --cwd .`; kanıt etiketi bu ticket
  çalıştırılana kadar `not-run`.

#### M43-T2 — Güncel kaynak baseline kapısı

- **Sahip ajan:** Codex agent
- **Amaç:** M33–M42 kaynak ağacını yeni bir bütün olarak, tarihsel sonuçlara
  dayanmadan doğrula ve gerçek başlangıç kanıtını kaydet; legal bir
  current→next ticket checkpoint'inin STATUS'u kendiliğinden değiştirip bu
  kanıtı drift ettirmemesini sağla.
- **Dosyalar:** `scripts/verify.py`, `scripts/pala_code_audit.py`,
  `scripts/test_pala_code_audit.py`, `scripts/test_pala_quality.py`,
  `scripts/test_pala_installer.py`, `scripts/test_pala_tools.py`, `STATUS.md`,
  `PROGRESS.md`, `PLAN.md`, `DEBUGGING.md`, `scripts/pala_memory.py`,
  `scripts/pala_state.py`, `scripts/pala_quality_discovery.py`.
- **Bitti sayılır:** Açık test discovery en az bir test çalıştırır; source
  verify ve hard-security audit gerçek exit sonucu ile kaydedilir;
  maintainability bulguları `attention_required` olarak görünür kalır; ilk
  hata varsa yalnız kök neden için incident açılır; STATUS ve checkpoint
  `next_action` aynı sonraki ticket'ı gösterdiğinde false memory-mismatch
  yazılmaz ve quality ledger kendiliğinden drift etmez.
- **Bağımlılık:** M43-T1.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_tools.PalaStateTests -v`;
  `py -3 -m unittest discover -s scripts -p test_*.py`;
  `py -3 scripts/verify.py --mode source`;
  `py -3 scripts/pala_code_audit.py --root .`.

#### M43-T3 — Süre sınırlı süreç ve smoke sınırı

- **Sahip ajan:** Codex agent
- **Amaç:** Audit'in timeout'suz gösterdiği dış süreçleri davranış sınıfına
  göre sınırla; P0 smoke ve doğrulama çocuk süreçlerinde timeout'un gerçek
  `blocked`/başarısız sonucu gizlemesine izin verme.
- **Dosyalar:** `scripts/pala_code_intel.py`, `scripts/pala_cold_start.py`,
  `scripts/pala_p0_smoke.py`, `scripts/verify.py`,
  `scripts/test_code_intelligence.py`, `scripts/test_pala_p0_friction.py`,
  `scripts/test_pala_cold_start.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_code_audit.py`,
  `docs/PALA_0_9_2_CODE_QUALITY_CONTROL.md`, `STATUS.md`, `PROGRESS.md`,
  `PLAN.md`, `DEBUGGING.md`.
- **Bitti sayılır:** Her dış süreç fixed argv / `shell=False` / uygun timeout
  kullanır veya test-fixture istisnası belgelenir; timeout temiz ya da passed
  görünmez; smoke orchestration fonksiyonu review eşiğinin altına iner ya da
  ayrık sorumluluklara bölünür.
- **Bağımlılık:** M43-T2.
- **Kanıt:** İlgili dar unittest'ler; `py -3 scripts/pala_p0_smoke.py`;
  `py -3 scripts/pala_code_audit.py --root .`; source verify.

#### M43-T4 — State yaşam döngüsü ve CLI sahipliği

- **Sahip ajan:** Codex agent
- **Amaç:** `pala_state.py` içindeki workflow reconcile, checkpoint ve CLI
  orkestrasyonunu küçük sahipli modüllere ayır; M43-T1'in uzlaştırma
  sözleşmesini değiştirmeden state çekirdeğini 800-satır review eşiğinin altına
  indir.
- **Dosyalar:** `scripts/pala_state.py`, `scripts/pala_state_core.py`,
  `scripts/pala_state_documents.py`, `scripts/pala_state_git.py`,
  `scripts/pala_state_lifecycle.py`, `scripts/pala_state_cli.py`,
  `scripts/pala_installer.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_installer.py`, `scripts/test_pala_code_audit.py`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`, `PLAN.md`,
  `DEBUGGING.md`.
- **Bitti sayılır:** Mevcut public/CLI sonuçları korunur; missing sibling
  bundle install öncesi fail-closed olur; `main` ve `checkpoint_work` ayrı
  test edilebilir sahiplerde kalır; eski state core 800-satır eşiğinin altında
  olur.
- **Bağımlılık:** M43-T3.
- **Kanıt:** State/installer dar unittest'leri; static audit; source,
  portable ve installed verify.

#### M43-T5 — Installer integrity ve transaction sahipliği

- **Sahip ajan:** Codex agent
- **Amaç:** `pala_installer.py` içindeki bundle manifesti, kullanıcı-dosyası
  koruması, atomik replacement ve rollback'i dış Codex bridge'den ayrı küçük
  sahiplere ayır; preservation sözleşmesini zayıflatma.
- **Dosyalar:** `scripts/pala_installer.py`, `scripts/pala_installer_codex.py`,
  `scripts/pala_installer_shared.py`, `scripts/pala_installer_core.py`,
  `scripts/pala_installer_integrity.py`, `scripts/pala_installer_transaction.py`,
  `scripts/build_portable.py`, `scripts/test_pala_installer.py`,
  `scripts/test_pala_code_audit.py`, `docs/PALA_0_9_5_INSTALL_INTEGRITY.md`,
  `STATUS.md`, `PROGRESS.md`, `PLAN.md`, `DEBUGGING.md`.
- **Bitti sayılır:** Installer core 800-satır review eşiğinin altında kalır;
  added/changed/symlink/bytecode `modified` koruması ve rollback sözleşmesi
  aynen geçer; eksik yardımcı içeren bundle mutasyondan önce reddedilir.
- **Bağımlılık:** M43-T4.
- **Kanıt:** Installer dar unittest'leri; static audit; source, portable,
  Repair ve installed verify.

#### M43-T6 — Session, cold packet ve hook sorumlulukları

- **Sahip ajan:** Codex agent
- **Amaç:** Cold packet oluşturma ile hook session orchestration'ını ayrı,
  sınırlı sahipliklere böl; kısa, secretsız ve stale-context fail-closed
  sözleşmesini koru.
- **Dosyalar:** `scripts/pala_cold_packet.py`, `scripts/pala_cold_packet_git.py`,
  `scripts/pala_cold_packet_packet.py`, `scripts/pala_hook.py`,
  `scripts/pala_hook_session.py`,
  `.pala/quality.json`, `scripts/test_pala_cold_packet.py`,
  `scripts/test_pala_quality.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_code_audit.py`, `hooks/hooks.json`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`, `PLAN.md`,
  `DEBUGGING.md`.
- **Bitti sayılır:** `build_cold_packet`, `session_context` ve hook `main`
  review eşiğini aşmaz; tek Git snapshot, context bütçesi ve timeout/missing
  fallback testleri geçer; hook test/build/ağ başlatmaz.
- **Bağımlılık:** M43-T5.
- **Kanıt:** Cold packet/hook dar unittest'leri; static audit; source,
  portable ve installed verify; `/hooks` UI trust `configured-not-verified`
  kalır, ancak owner doğrularsa ayrı kanıt yazılır.

#### M43-T7 — Status görünümü ve CSS sahipliği

- **Sahip ajan:** Codex agent
- **Amaç:** Status HTML'in public render sözleşmesini korurken büyük CSS ve
  render fonksiyonlarını ayrı test edilebilir sahipliklere böl; context
  readiness'i teslim yüzdesi gibi göstermeme kuralını koru.
- **Dosyalar:** `scripts/pala_view.py`, `scripts/pala_view_sections.py`,
  `scripts/pala_view_styles.py`, `scripts/pala_view_layout.py`,
  `scripts/pala_installer_shared.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_memory.py`, `scripts/test_pala_code_audit.py`,
  `scripts/test_pala_installer.py`, `scripts/pala_report.py`,
  `docs/PALA_0_9_3_MODULARITY.md`, `STATUS.md`, `PROGRESS.md`, `PLAN.md`,
  `DEBUGGING.md`.
- **Bitti sayılır:** `_css` ve `render` review eşiklerini aşmaz; mevcut
  privacy, keyboard, delivery-decision ve no-progress-claim HTML
  sözleşmeleri geçer; yeni sibling paket/kurulum doğrulamasına dahildir.
- **Bağımlılık:** M43-T6.
- **Kanıt:** View/memory/code-audit dar unittest'leri; generated Status HTML
  contract kontrolü; source, portable ve installed verify.

#### M43-T8 — Milestone paketi ve owner teslimi

- **Sahip ajan:** Codex agent
- **Amaç:** M43-T1…T7 kanıtlarını tek milestone ledger'ında birleştir, source
  ve portable/installed yüzeyleri doğrula, owner'a değişmeyen güven sınırları
  ile tek teslim özeti bırak.
- **Dosyalar:** `scripts/verify.py`, `scripts/build_portable.py`,
  `scripts/pala_quality.py`, `scripts/pala_report.py`, `STATUS.md`,
  `PROGRESS.md`, `PLAN.md`, `DEBUGGING.md`.
- **Bitti sayılır:** Güncel source, portable clean extract ve installed runtime
  kontrollerinin gerçek kanıtı vardır; secret/package audit geçer; release,
  remote publish ve `/hooks` owner UI güveni ayrı yetki/etiket olarak kalır.
- **Bağımlılık:** M43-T7.
- **Kanıt:** `py -3 scripts/verify.py --mode source`; portable clean-extract;
  `py -3 scripts/verify.py --mode installed`; `pala_state doctor`; kalite
  ledger milestone status.
- **Sonuç:** `passed` — source, portable clean extract ve geçici installed
  runtime doğrulandı; 3/3 milestone quality kapısı geçti. Yayın/publish ve
  `/hooks` UI trust ayrı owner yetki/etiketinde kaldı.

- [x] M43-T1: Sıfırdan uzlaştırma ve kilitli baseline
- [x] M43-T2: Güncel kaynak baseline kapısı
- [x] M43-T3: Süre sınırlı süreç ve smoke sınırı
- [x] M43-T4: State yaşam döngüsü ve CLI sahipliği
- [x] M43-T5: Installer integrity ve transaction sahipliği
- [x] M43-T6: Session, cold packet ve hook sorumlulukları
- [x] M43-T7: Status görünümü ve CSS sahipliği
- [x] M43-T8: Milestone paketi ve owner teslimi

### Bilerek yapılmayanlar (M43)

- M43-T1'den önce stale `M31-T1` kaydını complete/abandon diye işaretlemek
- Tarihsel `passed` kanıtını güncel çalışma ağacı için yeniden kullanmak
- T2 başarısızken geniş refactor ya da paket/kurulum mutasyonu başlatmak
- Owner açık yetkisi olmadan commit, push, PR, tag, release veya deploy yapmak

## M44 — Runtime girişleri ve yeni oturum sürekliliği (2026-08-10)

#### M44-T1 — Installed CLI ve stale-context hotfix'i

- **Sahip ajan:** Codex agent
- **Amaç:** Gerçek ZIP Update/çağırma yolunda bulunan eksik CLI importlarını
  kapat ve yeni Codex oturumunda eski temiz M43-T5 v2 kaydının güncel iş gibi
  görünmesini yeni workflow başlangıcıyla uzlaştır.
- **Dosyalar:** `scripts/pala_installer.py`, `scripts/pala_state_documents.py`,
  `scripts/test_pala_installer.py`, `scripts/test_pala_tools.py`, `PLAN.md`,
  `STATUS.md`, `PROGRESS.md`, `DEBUGGING.md`.
- **Bitti sayılır:** Installed `pala_installer.py --help` ve
  `pala_state.py instructions` exit 0; `pala_state context` M44-T1'i gösterir;
  source verify, yeni portable clean extract, gerçek local Update Doctor ve
  installed verify `passed`; eski M43 kanıtı yeni kanıt diye kullanılmaz.
- **Bağımlılık:** M43-T8.
- **Kanıt:** İki dar unittest; `pala_state context`; source verify; portable
  clean extract; gerçek local Update + Doctor; installed verify.

- [x] M44-T1: Installed CLI ve stale-context hotfix'i

**Sonuç:** `passed` — iki dar sözleşme testi, `419` tam unittest (`1` skip),
hard-security audit, source verify, portable clean extract, gerçek local Update
+ Doctor ve installed verify geçti. Session'sız context M44-T1'e uzlaştırıldı.

## M45 — Yayın öncesi gerçek yükseltme uyumluluğu (2026-08-10)

#### M45-T1 — Güncelleme sözleşmesi ve destek matrisi

- **Sahip ajan:** Codex agent
- **Amaç:** Otomatik güncellik kontrolü, yeni paketle yükseltme, doğrulanmış eski
  Pala klasörü, değiştirilmiş kurulum ve isteğe bağlı uzman sınırlarını tek ve
  test edilebilir kullanıcı sözleşmesinde tanımla.
- **Dosyalar:** `docs/PALA_UPDATE_COMPATIBILITY.md`, `PROJECT.md`,
  `scripts/test_plugin_experience.py`, `PLAN.md`, `STATUS.md`, `PROGRESS.md`.
- **Bitti sayılır:** Belge `0.8.0`, `0.8.1`, yönetimsiz doğrulanmış legacy,
  modified/foreign ve experts davranışını açıkça ayırır; sözleşme testi geçer.
- **Bağımlılık:** M44-T1.
- **Kanıt:** İlgili `test_plugin_experience` sözleşme testi.

- [x] M45-T1: Güncelleme sözleşmesi ve destek matrisi

**Sonuç:** `passed` — güncellik kontrolü/kurulum ayrımı, gerçek paket matrisi,
legacy/modified/foreign koruması, experts opt-in ve yeni sohbet sınırı sözleşme
testiyle sabitlendi.

#### M45-T2 — 0.8.2 bakım sürümü kimliği

- **Sahip ajan:** Codex agent
- **Amaç:** İçerik hotfix'ini eski `0.8.1` kullanıcılarının güncelleme denetiminde
  görebileceği yeni `0.8.2` kimliğine taşı.
- **Dosyalar:** `.codex-plugin/plugin.json`, `README.md`, `STATUS.md`,
  `scripts/test_plugin_experience.py`, `scripts/test_pala_update.py`.
- **Bitti sayılır:** Manifest/README/paket politikası `0.8.2` ile tutarlı;
  `0.8.1 -> 0.8.2` update-available testi geçer.
- **Bağımlılık:** M45-T1.
- **Kanıt:** Update ve plugin-experience dar testleri.

- [x] M45-T2: 0.8.2 bakım sürümü kimliği

**Sonuç:** `passed` — manifest `0.8.2+codex.20260810070000`; README son
yayımlanmış `0.8.1` ile yerel `0.8.2 not-run` adayını ayırıyor ve
`0.8.1 -> 0.8.2` update-available testi geçiyor.

#### M45-T3 — Gerçek eski paket yükseltme matrisi

- **Sahip ajan:** Codex agent
- **Amaç:** Gerçek yayımlanmış `0.8.0` ve `0.8.1` paketlerinden yeni adaya
  yükseltmeyi temiz geçici profillerde kanıtla.
- **Dosyalar:** `scripts/pala_upgrade_matrix.py`,
  `scripts/test_pala_upgrade_matrix.py`, `scripts/pala_installer_core.py`,
  `scripts/test_pala_installer.py`, `artifacts/upgrade-compat/`, `DEBUGGING.md`,
  `STATUS.md`, `PROGRESS.md`.
- **Bitti sayılır:** `0.8.0 -> 0.8.2`, `0.8.1 -> 0.8.2` ve doğrulanmış legacy
  matris satırları kullanıcı verisini koruyarak `passed`; kaynak asset kimliği
  ve SHA-256 secretsız kanıtta yer alır.
- **Bağımlılık:** M45-T2.
- **Kanıt:** Matris unittest'i ve gerçek paket matrix komutu.

- [x] M45-T3: Gerçek eski paket yükseltme matrisi

**Sonuç:** `passed` — GitHub `v0.8.0` SHA-256
`3EA17A1CEFF7DEEBF906D03184D9B9F09F800B4B64B4AD0D880AD30C22A6916E`
ve `v0.8.1` SHA-256
`69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53`
ile managed `0.8.0`, verified legacy `0.8.0` ve managed `0.8.1` satırları
`0.8.2`ye yükseldi; state marker korundu ve required missing boş kaldı.

#### M45-T4 — Yeni bileşen ve Codex cache aktarımı

- **Sahip ajan:** Codex agent
- **Amaç:** Eski kurulumdan sonra yeni zorunlu runtime/skill/hook dosyalarının
  ve Codex cache içeriğinin güncel adayla aynı olduğunu doğrula; experts sınırını koru.
- **Dosyalar:** `scripts/test_pala_installer.py`,
  `scripts/test_pala_expert_installer.py`, `STATUS.md`, `PROGRESS.md`.
- **Bitti sayılır:** Yeni required siblings ve skill/hook aktarımı, aynı sürüm
  cache drift yenilemesi ve experts opt-in davranışı testte `passed`.
- **Bağımlılık:** M45-T3.
- **Kanıt:** Installer ve expert-installer dar testleri.

- [x] M45-T4: Yeni bileşen ve Codex cache aktarımı

**Sonuç:** `passed` — yeni runtime, skill ve hook içerikleri eski kurulumdan
sonra adayla byte-for-byte eşleşti; bundle/cache fingerprint yenilemesi,
required-sibling fail-fast ve experts açık opt-in sınırı yedi dar testle geçti.

#### M45-T5 — Arıza ve rollback matrisi

- **Sahip ajan:** Codex agent
- **Amaç:** Değiştirilmiş/yabancı kurulum, eksik paket, Codex CLI hatası ve
  aktivasyon arızasında kullanıcı verisi ile eski çalışan sürümü koru.
- **Dosyalar:** `scripts/test_pala_installer.py`, `DEBUGGING.md`, `STATUS.md`,
  `PROGRESS.md`.
- **Bitti sayılır:** Dört arıza sınıfı doğru nedenle fail-closed olur ve rollback
  fingerprint'i eski çalışan paketle aynıdır.
- **Bağımlılık:** M45-T4.
- **Kanıt:** Installer rollback/preservation testleri.

- [x] M45-T5: Arıza ve rollback matrisi

**Sonuç:** `passed` — modified, user-added, foreign, missing-runtime,
activation-state ve Codex CLI arıza yolları ile portable rollback döngüsü yedi
testte eski çalışan fingerprint'i ve kullanıcı malzemesini korudu.

#### M45-T6 — 0.8.2 yerel release kapısı

- **Sahip ajan:** Codex agent
- **Amaç:** Tam kaynak, güvenlik, portable, installed ve upgrade-matrix
  kanıtlarıyla yayıma hazır fakat henüz yayımlanmamış final paketi üret.
- **Dosyalar:** `dist/pala-project-studio-0.8.2-final.zip`, `STATUS.md`,
  `PROGRESS.md`, `PLAN.md`, `DEBUGGING.md`, `.codex/pala-workflow.json`.
- **Bitti sayılır:** Release-tier kapılar `passed`; final ZIP yeniden üretilebilir,
  SHA-256 kaydedilmiş ve gerçek local Update + Doctor `passed`; GitHub mutasyonu yok.
- **Bağımlılık:** M45-T5.
- **Kanıt:** Full unittest, code audit, source/portable/installed verify, gerçek
  upgrade matrix, local Update + Doctor, artifact SHA-256.

- [x] M45-T6: 0.8.2 yerel release kapısı

**Sonuç:** `passed` — `427` test (`1` kontrollü skip), release-tier kalite
kapısı, code audit, source/portable/installed verify, plugin/skill validatorları,
gerçek upgrade matrix ve local Update + Doctor geçti. Final paket `168` entry,
`386154` byte; SHA-256
`5C95EC50611D1FE06B43D7DA421A7934465D88BC2F19B9BD49AECC1EF9C10350`.
Commit, push, tag ve GitHub release `not-run`.

## M46 — Bellek doğruluğu ve Scorecard görünürlüğü

#### M46-T1 — Tamamlanan ticket uzlaştırması ve host sözleşmesi

- **Sahip ajan:** Codex agent
- **Amaç:** Tamamlanan ticket'ı legacy aktif bellekten temizle; cold packet ve
  status yüzeyinde dış owner eylemini aktif geliştirme işi olarak gösterme.
  Codex Hooks `additionalContextLimit` semantiğini güncel resmî davranışa
  hizala ve Scorecard'ı yayın kapısı olmayan gözlem workflow'u olarak ekle.
- **Dosyalar:** `scripts/pala_state_cli.py`, `scripts/pala_state_core.py`,
  `scripts/pala_hook.py`, `scripts/pala_p0_smoke.py`, ilgili contract testleri,
  `docs/CODEX_SCOPE_AND_LIMITS.md`, `docs/CODEX_PLUGIN_CHECKLIST.md`,
  `.github/workflows/scorecards.yml`, `STATUS.md`, `PROGRESS.md`, `DEBUGGING.md`.
- **Bitti sayılır:** Complete aynı v2/v3 ticket'ı fail-closed temizler; farklı,
  dirty veya sahipliği uyuşmayan state korunur; host eşiği ile Pala'nın char/token
  bütçeleri ayrı sözleşmelerdir; Scorecard haftalık/manual, SHA-pinned ve
  non-gatingdir; bellek matrisinin tüm senaryoları testte geçer.
- **Bağımlılık:** M45-T6.
- **Kanıt:** Dar state/host-fit/P0/UX testleri, tam unittest discovery,
  `verify.py --mode source`, self-audit ve P0 smoke. GitHub workflow çalışması
  push sonrasında `not-run` kalır.

- [x] M46-T1: Tamamlanan ticket uzlaştırması ve host sözleşmesi

**Sonuç:** `passed` — aynı v2/v3 ticket clean olduğunda active state temizlenir;
farklı/dirty/ownership uyuşmazlığı korunur. Host spill eşiği ile Pala'nın char ve
yaklaşık-token bütçeleri ayrıdır. Scorecard weekly/manual, SHA-pinned ve non-gating;
state matrix, P0, full unittest, source verify ve self-audit geçti. Uzak Scorecard
çalışması, commit/push olmadığı için `not-run`.

## R6 — Safe Runtime Authority Integration (2026-08-11)

Canonical yaşayan plan:
`docs/plans/active/PALA-0.9.0-R6-runtime-integration.md`.

#### R6-M0 — Safe mutable runtime root

- **Sahip ajan:** Codex agent
- **Amaç:** Canonical task/lease/Quality/generated runtime state'ini protected
  `.git/.codex` dışındaki, tüm worktree'lerin paylaştığı single-host köke taşı.
- **Dosyalar:** `scripts/pala_authority.py`, `scripts/pala_store.py`,
  `scripts/pala_quality.py`, `scripts/pala_state_core.py`, `scripts/pala_report.py`,
  `scripts/pala_cold_packet.py`, `scripts/test_pala_runtime_authority.py`.
- **Bitti sayılır:** İki gerçek worktree aynı external authority root'u kullanır;
  ikinci owner claim edemez; detached HEAD kimliği bozmaz; legacy migration
  atomic/idempotent/ownership-aware olur; restricted Codex smoke `passed`.
- **Bağımlılık:** R5/M49 kanıtlı baseline.
- **Kanıt:** Kırmızı/yeşil focused test, diff review, affected integration tests,
  safe workspace-write smoke.

- [x] R6-M0: Safe mutable runtime root

- [x] R6-M1: WorkflowStore ↔ TaskContract authority bridge

**Durum (2026-08-11):** `passed` — explicit `begin --acceptance` girdileri
TaskContract içinde structured `not-run` kriterler olarak kalıcılaşır. WorkflowStore
completion yalnız bu contract'ı kullanır; acceptance'sız veya salt legacy pass
`verification_required` kalır. Nested TaskContract lease checkpoint ile outer
lease birlikte serbest bırakılır. 196 affected test + `git diff --check` `passed`.

- [x] R6-M2: TaskContract ↔ Quality Engine bridge

**Durum (2026-08-11):** `passed` — Quality Engine ledger'ı tek evidence authority
olarak kullanılır. Acceptance `quality_check_ids` required/current `passed` ve
exit-code `0` check'lere eşlenmeden DONE olmaz; `complete --quality-ticket` bu
mapping'i zorunlu çalıştırır. 196 affected test + `git diff --check` `passed`.

**Durum (2026-08-11):** `passed` — external runtime layout, worktree identity,
lease, Quality, event, generated read-model ve kayıpsız/idempotent migration
regressionları 18 focused + 188 affected integration testinde `passed`. Codex CLI
0.147.0 invocation-local direct filesystem-map profili runtime köküne yazdı;
`.git/.codex` sınır yazıları `UnauthorizedAccess` ile reddedildi. Global config
değişikliği veya sandbox zayıflatması yapılmadı. M1-M6 `passed`.

- [x] R6-M3: Fail-closed legacy migration

**Durum (2026-08-11):** `passed` — structured acceptance olmayan legacy
completed/done kaynakları değişmeden kalır; canonical copy typed conflict ile
`needs_decision` olur. 19 focused + 197 affected integration test `passed`.

- [x] R6-M4: Dependency / scope / retry / recovery

**Durum (2026-08-11):** `passed` — canonical dependency ve scope kontrolleri,
retry budget ve dirty/orphan recovery completion yolunda fail-closed. 88 focused
+ 199 affected integration test `passed`.

- [x] R6-M5: Handoff / knowledge / generated projections

**Durum (2026-08-11):** `passed` — handoff ve read-only consumers tek active
TaskContract fallback kullanır; belirsizlik fail-closed kalır. 27 focused + 202
affected integration test `passed`.

- [x] R6-M6: AGENTS / skill alignment

**Durum (2026-08-11):** `passed` — canonical report/context → claim → Quality →
acceptance → DONE zinciri ve generated read-model sınırı AGENTS/skill tarafından
belirtilir. 36 focused + 203 affected integration test; `git diff --check`
`passed`.

- [x] R6-M7: GitHub read-only regression hardening

**Durum (2026-08-11):** `passed` — read-only policy complete argv şekline göre
değerlendirilir; `gh api` method/body ve Git branch/remote mutation şekilleri
reddedilir. 4 focused + 141 affected integration test; `git diff --check`
`passed`.

- [x] R6-M8: Release / knowledge hygiene

**Durum (2026-08-11):** `passed` — `0.9.0` local candidate kimliği current
manifest/README/STATUS'ta tutarlı; `v0.8.1` tarihsel kalır. Source full gate:
485 test (1 controlled skip), reproducible ZIP SHA-256
`D048B6ED3E4453CF212037E9F514D1DA3D6FE146FED98B5EBC9CDFBD93FB8573`;
portable ve installed-profile gates `passed`. Remote release mutation
`not-run`. Machine-local Pala validation environment ile PyYAML 6.0.3 kuruldu;
system plugin/skill validators `passed`, global Python değiştirilmedi.

- [x] R6-M8-PACKAGE: PyYAML-enabled local package validation

**Durum (2026-08-11):** `passed` — source full gate, portable clean extract,
installed profile, system plugin validator ve system skill validator
machine-local PyYAML 6.0.3 environment ile doğrulandı. Remote publish
`not-run`.

## M47 — Quality Hardening

Canonical card details: `docs/plans/active/PALA-0.9.0-R6-runtime-integration.md`.

**Durum:** passed (2026-08-11). Amaç, mevcut stdlib + `unittest` + installer/portable
sözleşmesini koruyarak geliştirici kalite ve kritik çekirdek doğrulanabilirliğini
artırmaktır. Pydantic/Loguru production dependency değildir; global config,
hook otomasyonu ve remote Git işlemleri kapsam dışıdır.

- [x] M47-T1: Ruff baseline ve güvenli kapsam
- [x] M47-T2: Coverage.py baseline
- [x] M47-T3: Kritik çekirdek Mypy kademesi
- [x] M47-T4: uv dev environment uyumluluğu
- [x] M47-T5: Pytest unittest uyumluluk kararı
- [x] M47-T6: Bandit + pip-audit release security gate

Sonuç: 488 canonical unittest (1 controlled skip), Coverage 75%, strict Mypy
critical subset, M47 changed-surface Ruff ratchet, Bandit High=0 ve pip-audit
clean. Ayrıntılı kanıt ve bilinçli legacy backlog kararı canonical ExecPlan'da.

İlk iş `M47-T1`'dir: önce failing/baseline evidence, sonra minimal config,
dar doğrulama ve milestone sonunda full local verification. Araçlar mevcut
packaging/portable etkisi kanıtlanmadan kurulmaz.
## M61–M68 — Sealed local product completion (owner-approved)

### M61-T2 — Donor governance and language contract

- **Sahip ajan:** Codex `/root`
- **Amaç:** Pin donor provenance, preserve the fresh local RC baseline, and
  establish English-canonical plus ASCII Turkish localization without changing
  TaskContract, WorkflowStore, or Quality Engine authority.
- **Dosyalar:** `docs/plans/active/PALA-1.0-sealed-local-final.md`,
  `THIRD_PARTY_NOTICES.md`, `artifacts/governance/third-party-inventory.json`,
  `locales/en.json`, `locales/tr-ascii.json`, `scripts/pala_governance.py`,
  `scripts/test_pala_governance.py`, `scripts/build_portable.py`.
- **Bitti sayılır:** Fresh baseline, donor pin/license inventory, no global
  installation, English canonical surfaces, and ASCII localization validator
  have fresh evidence labels.
- **Bağımlılık:** `M60-T1` canonical `DONE`.
- **Kanıt:** `py -3 scripts/verify.py`; `py -3 -m unittest
  scripts.test_pala_governance -v`; `git diff --check`.

`M61-T1` historical install-acceptance card and evidence remain unchanged.

### M62-T1 — DesignAdvisor and canonical design tokens

- **Sahip ajan:** Codex `/root`
- **Amaç:** Advisory-only DesignAdvisor contract, DTCG-compatible primitive /
  semantic / component tokens, and a deterministic token drift validator.
- **Dosyalar:** `scripts/pala_design.py`, `scripts/test_pala_design.py`,
  `design/tokens.json`, `scripts/pala_tokens.py`, `scripts/test_pala_tokens.py`.
- **Bitti sayılır:** Recommendations are always `advisory`; no API can write
  TaskContract, Quality, lifecycle, or acceptance state; token layers validate;
  accessibility constraints override advisory style; provenance remains donor
  inventory-backed.
- **Bağımlılık:** `M61-T2` checkpointed with passed quality ledger.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_design scripts.test_pala_tokens -v`;
  `py -3 scripts/pala_design.py --validate`.

### M63-T1 — Read-only Control Center projection

- **Sahip ajan:** Codex `/root`
- **Amaç:** Extend the existing owner cockpit with an owner-first static
  Control Center while preserving read-only canonical authority.
- **Dosyalar:** `scripts/pala_owner_cockpit.py`,
  `scripts/test_pala_control_center.py`, `.pala/quality.json`.
- **Bitti sayılır:** Home, Projects, Current Work, Known Problems, Quality,
  Policies, Release, History, and Advanced sections render; user text is
  escaped; keyboard focus, reduced motion, and narrow layouts remain usable.
- **Bağımlılık:** `M62-T1` checkpointed with passed quality ledger.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_control_center -v`;
  `npm run test:e2e`.
-
### M64-T1 — Shared Failure Intelligence

- **Sahip ajan:** Codex `/root`
- **Amaç:** Extend the existing local SQLite tool-attempt persistence with
  normalized, redacted failure fingerprints and evidence-gated resolution
  states without creating a second authority or retry loop.
- **Dosyalar:** `scripts/pala_failure_intelligence.py`,
  `scripts/test_pala_failure_intelligence.py`, `.pala/quality.json`.
- **Bitti sayılır:** Secrets and user paths are redacted before persistence;
  unrelated failures normalize to stable fingerprints; verified resolutions
  require passed exit-0 evidence; stale knowledge and retry budgets fail
  closed; concurrent local writes remain safe.
- **Bağımlılık:** `M63-T1` checkpointed with passed quality ledger.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_failure_intelligence -v`;
  full source verification at the M64 checkpoint.
-
### M65-T1 — Versioned offline policy library

- **Sahip ajan:** Codex `/root`
- **Amaç:** Add an offline-first, versioned policy pack with explicit source
  freshness, profiles, enforcement, evidence requirements, and honest unknown
  handling.
- **Dosyalar:** `policies/*.json`, `scripts/pala_policy.py`,
  `scripts/test_pala_policy.py`, `.pala/quality.json`.
- **Bitti sayılır:** Rules carry source/version/freshness metadata; Python,
  Web, and Release profiles map deterministically; stale or missing sources
  remain `configured-not-verified`; policy output never becomes TaskContract
  or Quality Engine authority.
- **Bağımlılık:** `M64-T1` checkpointed with passed quality ledger.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_policy -v` and the M65
  source verification gate.
-
### M66-T1 — UX, accessibility, responsive and visual gates

- **Sahip ajan:** Codex `/root`
- **Amaç:** Cover the static Control Center with deterministic accessibility,
  responsive viewport, bounded-content, and visual-digest checks.
- **Dosyalar:** `scripts/pala_ux_gates.py`, `scripts/test_pala_ux_gates.py`,
  `.pala/quality.json`.
- **Bitti sayılır:** Focus, reduced motion, narrow layout, bounded text, and
  three viewport contracts pass without a new frontend runtime or remote write.
- **Bağımlılık:** `M65-T1` checkpointed with passed quality ledger.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_ux_gates -v`;
  `npm run test:e2e`.
-
### M67-T1 — ReleaseTruth and remote preflight

- **Sahip ajan:** Codex `/root`
- **Amaç:** Provide read-only release identity, publication matrix, drift
  lint, and fail-closed remote preflight without publishing or deploying.
- **Dosyalar:** `scripts/pala_release_truth.py`,
  `scripts/test_pala_release_truth.py`, `artifacts/release/*.json`,
  `.pala/quality.json`.
- **Bitti sayılır:** Local identity comes from `product-identity.json`; public
  claims are marked pending/not-run; drift and unknown permissions fail closed;
  remote writes remain outside the implementation.
- **Bağımlılık:** `M66-T1` checkpointed with passed quality ledger.
- **Kanıt:** `py -3 -m unittest scripts.test_pala_release_truth -v`;
  source verification.
