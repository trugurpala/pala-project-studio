# Açık Kaynak Kaydı

- Pala Project Studio kaynak kodu kullanıcıya aittir ve MIT lisansıyla dağıtılacaktır.
- Python standart kütüphanesi dışında runtime bağımlılığı yoktur.
- Codex plugin ve skill biçimleri OpenAI'nin güncel resmî belgelerine göre uygulanır; OpenAI kaynak kodu pakete kopyalanmaz.
- GitHub CI, pakete kopyalanmayan MIT lisanslı `actions/checkout` v7.0.1 ve
  `actions/setup-python` v7.0.0 adımlarını doğrulanmış commit SHA'larıyla kullanır.
- `code-review-graph` 2.3.7 isteğe bağlı, ayrı kurulan yerel kod zekâsı
  entegrasyonudur. Kaynak kodu Pala paketine kopyalanmaz; Pala yalnız güvenli
  adaptör, kurulum ve yönlendirme sağlar.

## 0.4 değerlendirmesi

| Kaynak | Doğrulanan sürüm | Lisans | Karar | Gerekçe |
| --- | --- | --- | --- | --- |
| `rtk-ai/rtk` | v0.44.2 | Apache-2.0 | Yönetilen CLI | Uzun komut çıktısını daraltır; Codex entegrasyonu yerine Pala'nın kanıtlı dar adaptörü kullanılır. |
| `tirth8205/code-review-graph` | v2.3.7 | MIT | Yönetilen CLI | Büyük repo etki analizinde kullanılır; kendi Codex hook/MCP kurucusu çalıştırılmaz. |
| `Fission-AI/OpenSpec` | v1.7.0 | MIT | Mevcut projeyle uyum | Pala'nın plan sahibi olduğu projeye ikinci artifact/komut sistemi zorla eklenmez. |
| `othmanadi/planning-with-files` | v3.9.0 | MIT | İlke uyarlaması | Plan, hook, compaction ve completion sahipliği Pala ile çakışır; dayanıklılık fikirleri testlere alınır. |
| `nilbuild/developer-roadmap` | 4.0 release; aktif master | Lisans metni ayrıca incelenecek | Referans | Çalıştırılabilir araç değil; mimari/kalite kapsam kontrolünde seçici kullanılır. |
| `ruvnet/ruflo` | v3.34.0 | MIT | 0.4 dışında | Ayrı MCP, daemon, hafıza, hook ve geniş ajan yüzeyi tek-kapı güvenilirliğini azaltır. |

Sürümler araştırma anındaki kabul adaylarıdır. Kurulumda kullanılan kesin
release, asset SHA-256, lisans metni ve indirme kaynağı ayrı makine-okunur kilit
dosyasında tutulacak; yeni sürüm kendiliğinden güvenilmiş sayılmayacaktır.
