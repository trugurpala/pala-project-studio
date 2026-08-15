# Pala Project Studio Kararları

## ADR-001 — Varsayılan yüzey: skills + hooks + deterministic scripts

Pala'nın **varsayılan** yürütme yüzeyi skill, güvenilir hook ve deterministik
Python scriptleridir; bu, kurulum, ağ, kimlik doğrulama ve context maliyetini
düşük tutar. Bu bir "sonsuza dek yasak" değil, düşük bağımlılıklı başlangıç
tercihidir. Ayrı MCP sunucusu, kalıcı servis veya görsel yüzey (dashboard/UI)
çekirdeğe **kendiliğinden** eklenmez; ancak açık bir faz kararıyla (ADR-013)
tek-kapı, yerel-first, secretsız ve hook-içinde-ağ-yok sınırlarını koruyarak
açılabilir. Haricî canlı veri gerektiğinde mevcut GitHub veya sağlayıcı
connector'ları koşullu kullanılır.

## ADR-002 — Progressive disclosure

SessionStart bütün ürün ve plan belgelerini ana bağlama kopyalamaz. Kısa durum, aktif ticket, tek sonraki iş ve gerekli belge yollarını verir. Agent önce durum belgesini ve planın yalnız aktif ticket bölümünü okur; daha geniş belgeyi yalnız karar gerektiğinde açar.

## ADR-003 — Katmanlı doğrulama

Dar test geliştirme iç döngüsüdür. Ticket kapısı değişen yüzeyi, milestone kapısı bütün proje kalitesini, release kapısı paket/güvenlik/dağıtım kanıtını doğrular. Tam kapı her mikro adımda çalıştırılmaz ve milestone sonunda atlanmaz.

## ADR-004 — GitHub isteğe bağlı kalıcılıktır

Plugin GitHub MCP veya tokenını paketlemez. Kaynak ve secretsız proje hafızası Git ile taşınabilir. Commit, push, PR, release ve görünürlük değişimi ayrı kullanıcı yetkileri olarak kalır.

## ADR-005 — Kullanıcı için tek kapı, içeride izole bileşenler

Pala 0.4 kullanıcıya tek kurulum ve tek doğal dil kapısı sunar. Üçüncü taraf
araçların aynı klasöre kaynak olarak kopyalanması yerine Pala; sürüm, bütünlük,
lisans ve sahiplik kaydı olan izole kurulumları yönetir. Bu ayrım kullanıcı
deneyiminde görünmez, fakat update, repair, uninstall ve rollback işlemlerini
güvenilir kılar.

## ADR-006 — Örtük Pala seçimi sınırlı kapsamda açılır

Pala skill'i yazılım projesini denetleme, planlama, kurtarma, uygulama,
çalıştırma ve tamamlama isteklerinde örtük seçilebilir. Açıklama
genel sohbeti veya yazılım dışı işleri kapsamamalıdır. Açık `$pala...` çağrısı
her zaman desteklenir. Yeni plugin kurulumu veya güncellemesi mevcut sohbetin
yüklenmiş becerilerini geriye dönük değiştirdiği varsayılmaz; kurucu doctor
sonunda yeni sohbet gereksinimini doğru raporlar.

## ADR-007 — Hook içinde ağ yok, her oturumda yerel güncellik var

SessionStart hızlı yerel sağlık ve önbellek durumunu okur; ağ, package install,
test veya GitHub mutasyonu çalıştırmaz. Uzak release kontrolü Pala'nın ilk
ilgili iş adımında, 24 saatlik atomik önbellekle yapılır. Böylece her oturum
güncellik durumunu görür, ancak çevrimdışı başlangıç ve hook güveni bozulmaz.

## ADR-008 — Yardımcı araç sahipliği

RTK ve code-review-graph Pala'nın yönettiği CLI bağımlılıklarıdır; kendi Codex
entegrasyon kurucuları çalıştırılmaz. Context7 ve Playwright desteklenen Codex
MCP CLI'siyle keşfedilir ve yalnız eksikse eklenir. OpenSpec yalnız zaten
kullanan projelerde uyumluluk yüzeyidir. planning-with-files ve Ruflo ayrı
hook/hafıza/orkestrasyon sahibi oldukları için kurulmaz; yararlı ilkeleri Pala
testlerine uyarlanır. developer-roadmap yalnız kapsam kontrol kaynağıdır.

## ADR-009 — Otomatik RTK rewrite dar ve kanıtlıdır

Codex `PreToolUse updatedInput` komut girdisini değiştirebilir. Pala adaptörü
yalnız açık allowlist'teki güvenli, salt-okunur ve eşdeğerliği test edilmiş
komutları RTK'ya yönlendirir. Bileşik shell ifadeleri, redirection, interaktif
komutlar, secrets taşıyabilecek işlemler ve Git/deploy mutasyonları aynen
bırakılır. RTK yoksa veya parser emin değilse başarısız olmak yerine orijinal
komut çalışır.

## ADR-010 — V3 ticket durumu oturum sahipliğiyle ayrılır

Pala v3 dinamik ticket kayıtları yalnız ignore edilen
`.codex/plugin-data/pala/v3/` altında tutulur. Ham Codex `session_id` hiçbir
JSON kaydına yazılmaz; ticket sahibi SHA-256'nın sınırlı özetidir. Her ticket
ayrı atomik kilit kullanır. Eski v2 workflow dosyası yerinde ve okunabilir
kalır; v3 yalnız gözlemci migration marker'ı yazar.

## ADR-012 — Project Memory Contract (0.5)

Pala 0.5 zorunlu bir proje hafızası sözleşmesi ekler. Oturum kaynağı sohbet
geçmişi değil klasördeki güncel kayıttır. Zorunlu okuma sırası:
`AGENTS.md` → CURRENT_STATUS → PROGRESS → aktif plan → TOOLING_DECISIONS →
DEBUGGING → git durumu. SessionStart hâlâ ADR-002 progressive disclosure
kuralına uyar: yalnız yollar, ticket skalerleri, araç özeti ve uyumsuzluk
bayrağı verir (≤800 karakter); belge gövdesi enjekte edilmez. Araç durumları
(`installed` / `recommended` / `installed_unverified` / `not_installed` /
`unavailable`) ticket doğrulama enum’larından ayrıdır. “Bitti” yalnız yapılandırılmış
kanıt etiketleriyle (`passed`, `not-run`, `blocked`, `configured-not-verified`,
`failed`, `timeout`) iddia edilir. Aktif ticket ile sonraki iş uyumsuzsa
workflow ve CURRENT_STATUS uyarılır. İsteğe bağlı yerel katalog
`Desktop\Codex\pala-catalog.json` secretsızdır; portable kurulumun parçası
değildir. 0.5A Truth Core (PR #5 snapshot) bu ADR’nin kapsamı dışındadır.

## ADR-013 — Görsel yüzey faz kapısı (ileride açılabilir)

Pala'ya görsel bir yüzey (yerel dashboard / read-only durum ekranı) eklemek
yasak değildir; bir **faz kararına** bağlıdır. Böyle bir yüzey ancak şu
sınırların hepsini korursa çekirdeğe alınabilir: (1) tek kurulum kapısı bozulmaz;
(2) yerel-first kalır, uzak servis veya telemetri gerektirmez; (3) secret,
transcript veya gerçek proje verisi paketlenmez; (4) hook davranışı değişmez —
hook içinde ağ/test/build yok; (5) mevcut deterministik script'ler tek kaynak
gerçek olmaya devam eder, yüzey yalnız onları okur/tetikler. İlk uygun adım,
yeni bileşen yerine mevcut `pala_state.py memory` ve `pala_catalog.py summary`
gibi okunur çıktıları zenginleştirmektir. Ağır bir UI kararı ayrı bir ADR ve
sözleşme testi gerektirir.

## ADR-014 — Durum sayfası zorunlu ilk yüzey (0.6)

Pala 0.6, ADR-013 faz kapısının ilk gerçeklemesi olarak sunucusuz bir yerel
HTML durum sayfasını zorunlu ilk yüzey yapar. Skill Implementation modunda
oturumun ilk işi `pala_report.py --cwd .` ile sayfayı üretmektir.
Sayfa tek statik dosyadır (`.codex/pala-status.html`): inline CSS, CSS-only sol
menü (radio + `:checked`), harici asset yok. 0.8.1 sonrası kontrol merkezi:
bölümler (Genel / Doctor / Hooks / Quality / Hafıza / Ticket / Yetki) + katalog
projeleri; tek inline script yalnız `localStorage` tema/tercih yazar (ağ yok).
Sol menü tazelik rozeti (`fresh`/`aging`/`stale`) taşır. Pala sürüm güncelliği
`pala_update` 24 saat önbelleğiyle banner olarak gösterilir; ağ yalnız
agent/Status yolunda ve günde en fazla bir kez çalışır. Hook içinde ağ veya
tarayıcı açma yoktur (ADR-007). Yalnız açık `paneli aç` / `paneli ac` niyeti
raporu yenileyip tek Control Center açar. `/hooks` UI trust bu sayfada
`configured-not-verified` kalır.

## ADR-015 — Yerel SQLite store (0.7)

Pala 0.7, projeler-arası katalog, URL provision kayıtları ve olay geçmişini
makine-yerel tek bir SQLite dosyasında tutar: `Desktop\Codex\pala.sqlite`
(`PALA_CATALOG_ROOT` / `PALA_DB_PATH` ile taşınır). Gerekçe: eşzamanlı oturum
yazımlarında JSON son-yazan-kazanır kaybını önlemek, "dün ne yaptım?" için
zaman çizelgesi tutmak ve bayat/blokajlı sorguları ucuzlaştırmak. Bu bulut veya
çok kiracılı bir DB değildir; secret/transcript yazılmaz; hook DB'ye yazmaz
(yalnız okur/dürtüler). `pala-catalog.json` ve `INDEX.md` DB'den yeniden üretilen
export olarak kalır; bozulursa `.bak` JSON'dan `migrate_from_json` ile geri
dönülür. Durum sayfası (ADR-014) bu store'dan timeline, progress ve provision
özetini okur.

## ADR-016 — Windows Codex keşfi ve core/experts ayrımı (0.7.1)

Pala 0.7.1, “her Windows Codex makinesinde kurulum” sürtünmesini iki somut
adımla düşürür: (1) `resolve_codex_executable` PATH yanında bilinen OpenAI
desktop / npm konumlarını tarar; (2) Doctor `healthy`/`plugin_ready` çekirdeği
(Python, Git, Codex, plugin) ile `experts_ready` (Node/uv/uzmanlar) ayrılır —
uzman eksikliği çekirdek sağlığını düşürmez. Git URL marketplace kapısı
dokümante edilir; ChatGPT Plus düz sohbet kurulum yüzeyi değildir.

## ADR-011 — OSS katkısı tek kapı, salt-okunur scout ve ayrı yazma yetkisidir

Açık kaynak katkısı Pala içinde ayrı bir agent platformuna dönüşmez. GitHub
connector/MCP varsa yalnız keşif ve kanıt toplama için salt-okunur scout olarak
tercih edilir; yerel `gh` yalnız kullanıcının ayrıca yetkilendirdiği fork/push ve
draft PR işlemleri için taşıma katmanıdır. Hedef deponun katkı metinleri
untrusted data sayılır ve ajan yetkisini genişletemez. AI katkısını yasaklayan,
atama şartı karşılanmayan, güvenlik hassasiyetli, başkasına atanmış veya mevcut
uygulama PR'ı bulunan işler otomatik katkı akışından çıkarılır. OSV-Scanner ve
zizmor yalnız zaten mevcutsa isteğe bağlı kalite kanıtıdır; OpenSSF Scorecard
risk sinyali olarak referans alınabilir ancak tek başına kabul/ret kapısı
olamaz. OpenHands gibi ikinci orkestratörler ve zorunlu evrensel tarayıcılar
tek-kapı, yerel-first ve düşük bağımlılık kararlarıyla çakıştığı için çekirdeğe
alınmaz. Yayın onayı diff/commit/gate fingerprint'ine bağlıdır ve yalnız draft
PR için geçerlidir; merge, release, tag, force-push ve görünürlük değişimi ayrı
yetki olarak kalır.

## ADR-017 — Ortak hafıza: tek makine store, üç ince yüzey (M25)

Pala'nın çalışma belleği iki katmandır: (1) proje klasöründeki metin hafızası
(`AGENTS` / `STATUS` / `PLAN` / …, ADR-012); (2) makine-yerel
`Desktop\Codex\pala.sqlite` katalog + olaylar (ADR-015). M25 bu store'u
**Codex + Cursor + CLI** için aynı yol sözleşmesiyle okunur kılar.

**Paylaşılır:** `PALA_DB_PATH` / `PALA_CATALOG_ROOT` ile tek sqlite yolu;
katalog şeması; memory contract; kanıt etiketleri; Status HTML (CLI).

**Yüzeye özel:** Codex marketplace + `hooks.json`; Cursor yalnız ince
skill/rules (Codex hook parity yok); CLI script kapısı.

**Yasak:** bulut/çok kullanıcı sync; secret/transcript DB'ye; ChatGPT Plus
kurulum iddiası; Cursor'da "Pala kurulu plugin" yalanı; hook içinde ağ/test.

Uygulama yüzeyi: `scripts/pala_shared_memory.py` + Doctor `shared_store`
bloğu. Cursor paketi: `portable/cursor/` (skill + rule); Codex plugin
davranışını taşımaz. Wave E kanıt/doküman: `docs/PALA_SHARED_MEMORY.md`
(hit/miss + drift check); `AGENTS.md` tek kaynak, Cursor rule ince kalır.

## ADR-018 — ProjectSnapshot repo/worktree kimliğini ayırır (M76)

Pala canonical uzlaştırması için salt-okunur, sürümlü `ProjectSnapshot`
kullanır. Repository identity varsa sıralı Git root-commit setinin digest'idir;
unborn repository yalnız zorunlu fallback olarak normalize common-dir kullanır;
worktree identity gerçek worktree kökünün ayrı digest'idir. Mutlak makine yolu
serialize edilmez. Linked worktree adayları aynı repository identity'yi
paylaşabilir fakat açık bir worktree identity seçilmeden birden fazla adaydan
tahmin yapılmaz; typed `PROJECT_SNAPSHOT_WORKTREE_AMBIGUOUS` bulgusu üretilir.

Snapshot yalnız bounded `git` sorguları (`shell=False`, timeout) ve dosya
digestleri okur; catalog/runtime store oluşturmaz. Git timeout veya gözlem
hatası temiz durum sayılmaz, `unknown` ve blocking finding olur. Remote userinfo
kalıcı/read-model çıktısına girmeden redakte edilir. Snapshot kanıttır;
TaskContract, WorkflowStore veya Quality Engine'in yerine geçmez.

## ADR-019 — ProjectProfile açık ve değişmez güvenlik sözleşmesidir (M76)

`ProjectProfile v1` beyan edilmiş scope, stack, risk, Quality, release,
ownership, security ve data-classification gerçeklerinin sahibidir. Skill
routing `profiles` yalnız discovery hint olarak kalır; bu sözleşmeyi dolduramaz
veya geçersiz kılamaz.

Standard, confidential, regulated ve public-release modları explicit,
fail-closed policy invariant'larına sahiptir. Bilinmeyen alan/değer ile secret,
kişisel tanımlayıcı ve private machine path şekilleri best-effort coercion yerine
sanitized typed finding üretir. Değerler frozen tuple-backed nesneler, canonical
sorted JSON ve SHA-256 digest olarak temsil edilir.

State-document adapter yalnız bounded özet read modelidir; persistence yaratmaz
ve ikinci authority değildir. Durable profile özetleri ve migration M76-T4'ün
tek machine-local store kapsamındadır; source, credential, personal identifier,
private path veya chat saklanmaz.

## ADR-020 — Context Receipt canlı beklentiye bağlı bütünlük kaydıdır (M76)

`Context Receipt v1`, bir `ProjectSnapshot` ile aktif TaskContract, ProjectProfile
ve proje-göreli kaynak digestlerini tek deterministik, immutable kayıtta bağlar.
Tüketici yalnız receipt'in kendi beyanına güvenmez: güncel snapshot, task,
profile ve kaynaklardan kurulan `ContextExpectation` olmadan doğrulama sonucu
`blocked` kalır. Her mismatch tipli ve sanitize edilmiş bulgu üretir.

Canonical JSON UTF-8, sıralı anahtarlar, compact separator ve standart dışı
floatları reddeden sözleşmeyle SHA-256 digestlenir. `receipt_id` yalnız içerik
bütünlüğü fingerprint'idir; imza, üretici kimliği veya authenticity kanıtı
değildir. Absolute/private path, credential, PII ve transcript şekilleri
saklanmaz; kaynaklar yalnız göreli path + digesttir.

Cold-packet ve state adapter'ları yalnız 2 KiB altı güvenli özeti sunar,
`can_complete=false` taşır ve `validation_status` değerini Quality sonucu gibi
kullanmaz. Receipt TaskContract/WorkflowStore/Quality Engine yerine geçmez ve
persistence yapmaz; durable receipt/history migration M76-T4 kapsamındadır.

## ADR-021 — Continuity özeti ve Project History tek store'da ayrı authority'dir (M76)

Machine-local `pala.sqlite` schema v2, owner-validated ProjectProfile ve canlı
Context Receipt'ten yalnız repository/worktree kimliği, digest, profil modu ve
validation status scalar'larını saklar. Full profile/receipt, source ref, path,
credential, PII veya transcript durable store'a kopyalanmaz. Ortak privacy-shape
sahibi bu üç contract tarafından reuse edilir ve typed finding değeri echo etmez.

V1→v2 geçişi `quick_check`, SQLite backup, `BEGIN IMMEDIATE` ve rollback ile
transactional'dır; duplicate/future/incomplete schema fail-closed kalır.
Salt-okunur açılış dosya, WAL, migration, scrub veya marker yaratmaz. Project
History close/reopen kayıtları content-idempotent ve trigger ile append-only'dir;
transient event pruning bunlara dokunmaz. Diagnostic event'ler aynı machine-local
store'a yazılır ve aktif repository filtresi olmadan rapora verilmez.

History ve continuity yalnız bounded read modeldir (`can_complete=false`). Project
closure otomatik ticket-complete hook'u değildir; current receipt ve açık authority
ref gerektirir. TaskContract, WorkflowStore ve Quality Engine completion zinciri
değişmez.

## ADR-022 — Host capability ve delegation kanıta bağlı, candidate-only'dir (M77)

Host/provider adı bir yeteneği doğrulamaz. Codex adaptörü yalnız çağıranın
gözlediği bounded tool/probe envanterinden üretilen immutable Host Capability
Snapshot'taki `passed` yetenekleri ilan eder; bilinmeyen ve eksik gözlem
fail-closed kalır. Snapshot deterministiktir, private host verisi saklamaz ve
completion authority taşımaz.

Alt-ajan sözleşmesi parent TaskContract digest'i, current Context Receipt,
repository/worktree kimliği, dar read/write/deny scope, acceptance ve Quality
check ID'lerini bağlar. Çıktı yalnız `awaiting_primary_review` adayıdır. Tek
ExecutionCoordinator Windows case/separator aliaslarını, kapasiteyi, same-holder
scope genişletmesini ve writer çatışmalarını yönetir; canonical completion
zinciri değişmez.

## ADR-023 — Process lifecycle exact owned handle ve OS process group sınırındadır (M77)

Supervisor shell açmadan explicit argv başlatır; komut ve private host path'i
serialize etmez, yalnız digest ve typed lifecycle evidence üretir. PID tek
başına ownership kanıtı değildir: stop/restart yalnız supervisor registry'sindeki
exact child handle ile kabul edilir, arbitrary attach fail-closed kalır.

Windows'ta kill-on-close Job Object, POSIX'te yeni session/process group child
ağacının sınırıdır. Health/port, startup, timeout, unexpected exit, orphan,
cancel, restart ve context shutdown bounded'dır. Evidence `can_complete=false`
kalır; yabancı process/port sahibini öldürmek yasaktır.

## ADR-024 — Failure Intelligence requires a current Quality basis (M78)

The fingerprint binds failure class, command family, tool, platform, scope and
exit code; Bearer values are fully redacted. Project filtering is exact and
corrupt rows are isolated. A recipe becomes verified only through exit-zero
`pala-quality-runner` evidence for the current surface digest. The bounded read
model remains `can_complete=false`.

## ADR-025 — Control Center is one escaped owner read model (M78)

Queue, receipt, history, Failure Intelligence, profile, host/process and
security/release surfaces share one bounded owner-first renderer. Raw HTML is
accepted only with Pala's exact generated marker; private paths and hostile
private values are hidden. Responsive, keyboard, reduced-motion and offline
behavior are exercised on the real generated Playwright page. The panel is
read-only and does not alter TaskContract/WorkflowStore/Quality authority.

## ADR-026 — Final Agency artifact is deterministic and locally sealed (M79)

The local unpublished `1.2.0` candidate ZIP uses fixed member timestamps, normalized relative
names and sorted source bytes. A CycloneDX 1.5 SBOM is derived only from committed
lock files; a separate inventory hashes every ZIP member. Windows and Linux CI
builds must produce the same archive SHA. Manifest, SBOM and inventory contain no
absolute path, timestamp, credential or completion claim. Remote publish and
deploy remain `not-run` without separate authority.

## ADR-027 — Upgrade evidence uses published bytes and real SQLite continuity (M79)

The upgrade matrix downloads only SHA-pinned public 0.4.4, 0.8.0, 0.8.1, 1.0.0
and 1.1.2 assets. Each case installs in a unique temporary profile, verifies
Doctor and mutation-free second ensure-current, and preserves a real schema-v2
`pala.sqlite` plus Failure Intelligence row. A fault injected at the transaction
state-write boundary must restore the exact previous bundle and database hash.
