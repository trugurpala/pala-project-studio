# Third-Party Notices

Pala Project Studio'nun kurulan çalışma zamanında Python standart kütüphanesi
dışında bir bağımlılık yoktur.

GitHub Actions kalite akışı aşağıdaki resmî GitHub eylemlerini kaynak pakete
kopyalamadan kullanır:

- `actions/checkout` v7.0.1,
  `3d3c42e5aac5ba805825da76410c181273ba90b1`, MIT License.
- `actions/setup-python` v7.0.0,
  `5fda3b95a4ea91299a34e894583c3862153e4b97`, MIT License.

Sürüm etiketleri ve commit türleri 2026-08-05 tarihinde GitHub API üzerinden
doğrulanmıştır. Bu bileşenlerin kendi lisans ve bildirimleri ilgili GitHub
depolarında geçerlidir.

İsteğe bağlı `code-review-graph` entegrasyonu:

- Proje: https://github.com/tirth8205/code-review-graph
- İncelenen sürüm: 2.3.7
- İncelenen commit: `6a1ee1c7063cc35cfa5ff12b8198c29360f3e4ad`
- Lisans: MIT, Copyright (c) 2026 Tirth Kanani
- Kapsam: ayrı kurulan yerel kod grafiği ve Codex MCP entegrasyonu

Pala bu projenin kaynak kodunu içermez. Kurulum ve güncelleme yaşam döngüsü
`code-review-graph` projesine aittir.

PALA-045 yönetilen uzman adayları (kaynak kodları Pala paketine dahil edilmez):

- Graphify `0.9.33` — Apache-2.0, https://github.com/Graphify-Labs/graphify
- Serena `1.6.1` — MIT, https://github.com/oraios/serena
- codebase-memory-mcp `0.9.0` — MIT,
  https://github.com/DeusData/codebase-memory-mcp
- Ollama `0.32.6` — MIT, https://github.com/ollama/ollama
- Qwen3 4B Instruct — Apache-2.0, https://ollama.com/library/qwen3:4b-instruct

Pala bunları yalnız kendi sabit sürüm/bütünlük kaydı üzerinden ve proje dışı
izole veri alanında çalıştıracaktır; kendi Codex kurucuları, hook'ları, daemon
veya kullanıcıya ait model alanları Pala tarafından çağrılmaz.
