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

