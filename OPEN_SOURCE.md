# Açık Kaynak Kaydı

- Pala Project Studio kaynak kodu kullanıcıya aittir ve MIT lisansıyla dağıtılacaktır.
- Python standart kütüphanesi dışında runtime bağımlılığı yoktur.
- Codex plugin ve skill biçimleri OpenAI'nin güncel resmî belgelerine göre uygulanır; OpenAI kaynak kodu pakete kopyalanmaz.
- GitHub CI, pakete kopyalanmayan MIT lisanslı `actions/checkout` v7.0.1 ve
  `actions/setup-python` v7.0.0 adımlarını doğrulanmış commit SHA'larıyla kullanır.
- `code-review-graph` 2.3.7 isteğe bağlı, ayrı kurulan yerel kod zekâsı
  entegrasyonudur. Kaynak kodu Pala paketine kopyalanmaz; Pala yalnız güvenli
  adaptör, kurulum ve yönlendirme sağlar.
