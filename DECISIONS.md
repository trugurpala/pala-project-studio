# Pala Project Studio Kararları

## ADR-001 — Skills + hooks + deterministic scripts

Pala 0.3, ayrı MCP sunucusu eklemeyecek. Mevcut yerel proje yürütme işi için skill, güvenilir hook ve deterministik Python scriptleri yeterlidir. Bu seçim kurulum, ağ, kimlik doğrulama ve context maliyetini düşük tutar. Haricî canlı veri gerektiğinde mevcut GitHub veya sağlayıcı connector'ları koşullu kullanılır.

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
