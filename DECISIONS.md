# Pala Project Studio Kararları

## ADR-001 — Skills + hooks + deterministic scripts

Pala 0.3, ayrı MCP sunucusu eklemeyecek. Mevcut yerel proje yürütme işi için skill, güvenilir hook ve deterministik Python scriptleri yeterlidir. Bu seçim kurulum, ağ, kimlik doğrulama ve context maliyetini düşük tutar. Haricî canlı veri gerektiğinde mevcut GitHub veya sağlayıcı connector'ları koşullu kullanılır.

## ADR-002 — Progressive disclosure

SessionStart bütün ürün ve plan belgelerini ana bağlama kopyalamaz. Kısa durum, aktif ticket, tek sonraki iş ve gerekli belge yollarını verir. Agent önce durum belgesini ve planın yalnız aktif ticket bölümünü okur; daha geniş belgeyi yalnız karar gerektiğinde açar.

## ADR-003 — Katmanlı doğrulama

Dar test geliştirme iç döngüsüdür. Ticket kapısı değişen yüzeyi, milestone kapısı bütün proje kalitesini, release kapısı paket/güvenlik/dağıtım kanıtını doğrular. Tam kapı her mikro adımda çalıştırılmaz ve milestone sonunda atlanmaz.

## ADR-004 — GitHub isteğe bağlı kalıcılıktır

Plugin GitHub MCP veya tokenını paketlemez. Kaynak ve secretsız proje hafızası Git ile taşınabilir. Commit, push, PR, release ve görünürlük değişimi ayrı kullanıcı yetkileri olarak kalır.
