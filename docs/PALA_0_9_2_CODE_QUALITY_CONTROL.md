# Pala 0.9.2 — Code Quality Control Plane

## Karar

Pala bir “her aracı otomatik kur ve her şeyi yeşil göster” ürünü olmayacak.
Teslim iddiası; proje-yerel kapılar, kanıt ledger'ı ve ayrı yetki sınırlarıyla
kalacak. Buna ek olarak Pala'nın kendi dağıtılan Python yüzeyi artık
`scripts/pala_code_audit.py` tarafından salt-okunur denetlenir.

Bu denetim yalnızca şu durumda `failed` döndürür:

- çalıştırılabilir kodda `eval`/`exec`, `os.system`, `os.popen`, pickle/marshal
  yükleme gibi yasaklı çağrı;
- `subprocess` için `shell=True` veya dinamik `shell`;
- hook içinde ağ modülü importu;
- dağıtılan kaynakta secret biçimli literal;
- okunamayan ya da sözdizimi geçersiz kaynak.

Uzun modül/fonksiyon ve timeout'suz process çağrıları ayrı `attention_required`
olarak raporlanır. Bu, “güvenlik geçti” sonucunu “kod mükemmel” diye yanlış
göstermemek içindir. Source `verify.py`, portable extract ve installed paket
hard güvenlik katmanını çalıştırır; hooks hiçbir kapıyı çalıştırmaz.

## Kontrol merkezi kararı

Status HTML artık şunları birbirinden ayırır:

| Karar | Anlamı |
| --- | --- |
| `Henüz değerlendirilmedi` | ticket veya uygun tier/ledger yok |
| `Bloke` | ticket uyumsuz ya da zorunlu kapı eksik/başarısız |
| `Ticket hazır` | yalnız ticket tier zorunlu kapıları kanıtlı geçti |
| `Milestone hazır` | milestone tier kapıları kanıtlı geçti |
| `Sürüme hazır` | yalnız release tier zorunlu kapıları kanıtlı geçti |

Bu kart zorunlu kapı adlarını ve tek sonraki eylemi gösterir. Yerel proje,
SQLite, provision hedefi ve remote bağlantısı ekran paylaşımında varsayılan
olarak kapalıdır; kullanıcı isterse `<details>` ile açar. Test fixture'larından
gelen `tmp…` katalog/timeline gürültüsü gösterilmez.

## Dış araç politikası

Yerel geliştirici denetiminde şu iki küçük araç izole Pala audit dizinine
kuruldu; Pala runtime bunları otomatik başlatmaz ve paket bunlara bağımlı
değildir:

- Ruff `0.15.22`: hızlı lint/format ve import düzeni.
- Bandit `1.9.4`: Python AST güvenlik sinyalleri.

İlk baseline'da Ruff mantıksal kural seti 60 iyileştirme buldu. Bunların çoğu
import düzeni ve sadeleştirme; geniş, mekanik bir otomatik düzeltme bu dilimde
yapılmadı. Bandit'in orta seviye sonuçları manual triage edildi: `_fetch`
fonksiyonu artık yalnız HTTPS kabul eder; kalan SQL sonuçları sabit iç
allowlist identifier'lardan, `shell` sonuçları ise `detect_environment`
parametre adından kaynaklanan tool false-positive'lerdir. Yine de bu sonuçlar
“temiz” diye saklanmaz: gelecekteki ratchet için baseline'dır.

### Katmanlı hedef stack

1. Pala static code audit — her source/portable/installed doğrulamada, offline.
2. Proje-native test, build, typecheck ve browser kanıtı — Delivery Quality
   Engine'in ticket/milestone/release kapıları.
3. Ruff — önce yeni/değişen dosyalarda ratchet, sonra sıfır baseline.
4. Bandit — Pala Python üretim yüzeyinde triage edilmiş policy ile.
5. Gitleaks — explicit pre-release secret taraması; log/artefact redaction ile.
6. zizmor — GitHub Actions güvenlik taraması; yalnız CI veya açık local çağrı.
7. CodeQL — GitHub CI code scanning; local varsayılan değil.
8. Dependency audit — yalnız mevcut lockfile ve açık network yetkisiyle;
   offline durumda `configured-not-verified`.
9. Reproducible portable/install/uninstall sınırı.
10. Evidence ledger + release/handoff kabul kriteri eşlemesi.

Bu sıralama “top-10” pazarlama iddiası değildir. Her katman ayrı kör noktayı
kapatır; bulunmayan/çalıştırılmayan katman `passed` sayılmaz.

## Yerel hafıza / RAG kararı

Bu Pala kaynağı için vektör RAG kurmak şu an faydalı değil: üretim script
yüzeyi küçük ve mevcut router focused işte `direct + rg` seçiyor. Ek embedding
modeli, indexleme süresi ve bakım maliyeti token/hız kazancını kanıtlamadan
eklenmeyecek.

Eşik aşıldığında Pala'nın mevcut local-first route'u kullanılacak:

- 1.000+ dosya, 50+ değişen dosya veya 4+ modül kökü: `code-review-graph`;
- 5.000+ dosya, 10+ modül kökü veya 3+ dil: `codebase-memory`;
- semantik belge araması: Graphify + yalnız loopback Ollama.

SQLite FTS5 ancak iki gerçek projede aynı sorgular için `rg` ile karşılaştırılan
median arama süresi, doğru dosya geri çağırma oranı ve cold-index maliyeti
ölçüldükten sonra pilot yapılır. Vektör DB veya cloud RAG kendiliğinden
kurulmaz, ağ açmaz ve proje kaynağını dışarı göndermez.

## Sonraki küçük dilimler

1. Ruff baseline'ı per-file ratchet ile azalt; otomatik fix yalnız ayrı onaylı
   değişiklikte.
2. `_scrub_remote_values` SQL identifier allowlist'ini kodla görünür kıl;
   Bandit B608 false-positive'lerini açıklayan dar test ekle.
3. Process timeout envanterini sınıflandır: user-facing/external çağrılara
   bounded timeout, test fixture'larına gerekçe.
4. Kabul kriteri → zorunlu gate → owner demo/rollback bağlantısını release
   manifestine ekle.
5. `pala_state`, installer, view ve quality monolitlerini davranış değişmeden
   küçük ownership modüllerine böl.
