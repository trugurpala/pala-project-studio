# Pala Project Studio

Pala Project Studio, Codex'in uzun soluklu yazılım projelerinde aktif işi
kaybetmeden ilerlemesine yardımcı olan Türkçe odaklı bir proje yürütme
eklentisidir. Ürün kararlarının yerine geçmez; mevcut proje belgelerini bulur,
aktif işi kısa bir kontrol noktasında tutar ve doğrulamayı değişikliğin riskine
göre katmanlandırır.

## Ne sağlar?

- Mevcut `AGENTS.md`, ürün, plan, durum ve karar belgelerini yeniden kullanır.
- Yalnızca aktif iş için küçük bir oturum bağlamı üretir.
- Belge, Git başı veya çalışma ağacı kontrol noktasından sonra değiştiğinde
  uzlaştırma gerektiğini bildirir.
- Dar test, görev testi, kilometre taşı ve sürüm doğrulamasını birbirinden
  ayırır.
- Kullanıcıya gösterilebilir işlerde ticket sonunda kısa bir owner-demo dosyası
  ve varsa gerçek tarayıcı ekran kanıtı bırakır.
- Hook içinde test, build, ağ veya GitHub işlemi çalıştırmaz.
- Commit, push, PR, release ve deploy için ayrı kullanıcı yetkisini korur.

Pala daha fazla token veya daha geniş bir Codex bağlamı oluşturamaz. Katkısı,
gereksiz belgeleri her turda tekrar yüklemeyi ve ağır doğrulamayı yanlış yerde
çalıştırmayı azaltmaktır. Ölçülmemiş hız ya da token tasarrufu yüzdesi vaat
etmez.

## Büyük repo kod zekâsı

Pala, büyük ve çapraz modüllü incelemelerde isteğe bağlı
[`code-review-graph`](https://github.com/tirth8205/code-review-graph)
entegrasyonunu kullanabilir. Araç Pala'ya gömülmez; yerel graph üretir ve
değişiklik etkisini daraltmaya yardımcı olur. Bulgular yine kaynak ve testlerle
doğrulanır.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install_code_intelligence.ps1 -ProjectPath C:\proje
```

Komut, global `pip` yerine `uv` veya `pipx` ile izole kurulum yapar. Codex
yapılandırması ve ilk graph varsayılan olarak değişmez; bunlar ancak sırasıyla
`-ConfigureCodex` ve `-BuildGraph` bayrakları verilirse çalışır. Önizleme için
`-DryRun` kullanın.

Doğrulanmış Codex sınırları ve bunların tasarıma etkisi için
[Codex kapsam ve limitleri](docs/CODEX_SCOPE_AND_LIMITS.md) belgesine bakın.

## Kullanım

Eklenti Codex'e kurulduktan sonra yeni bir oturum açın ve örneğin şunu yazın:

> Pala Project Studio ile mevcut durumu oku, aktif işi bul ve yetkilendirilmiş
> yerel uygulamaya kaldığı yerden devam et.

Proje kaydı ve kontrol noktaları için:

```powershell
py -3 scripts/pala_state.py discover --cwd C:\proje
py -3 scripts/pala_state.py register --cwd C:\proje
py -3 scripts/pala_state.py begin --cwd C:\proje --ticket F2-T1 --goal "Aktif hedef"
py -3 scripts/pala_state.py checkpoint --cwd C:\proje --tier ticket --next-action "Sıradaki iş"
py -3 scripts/pala_state.py context --cwd C:\proje
```

Komut seçeneklerinin güncel biçimi için `--help` kullanın. Projenin kendi
durum ve plan belgeleri kaynak gerçektir; `.codex` altındaki Pala dosyaları
küçük bir çalışma kontrol noktasıdır.

Checkpoint, değişen dosya içeriklerini belleğe kopyalamaz; yol sayısı ve
birleşik SHA-256 özeti saklar. Checkpoint'ten sonra aynı değişikliklerin atomik
commit edilmesi yeni iş sayılmaz. Ek veya farklı bir commit ise yeniden
uzlaştırma gerektirir.

Kullanıcıya gösterilebilir bir ürün üzerinde çalışılıyorsa mevcut demo belgesi
yeniden kullanılır; yoksa uygun ticket sonunda `reports/OWNER_DEMO.md` şablonu
oluşturulur. Hook kendi başına ekran görüntüsü almaz. Görsel kanıt ancak gerçek
runtime tarayıcıda açılıp incelendiyse eklenir.

## Yerel doğrulama

```powershell
py -3 scripts/verify.py
```

Bu komut sözleşme testlerini, Python sözdizimini, JSON dosyalarını ve taşınabilir
ZIP'in tekrarlanabilir üretimini ağ erişimi olmadan doğrular.

## GitHub güvenliği

Kaynak depoya token, parola, `.env`, oturum dökümü, müşteri verisi veya başka
projelerin özel içeriği eklenmemelidir. Pala bir projeyi yürütürken uzak depo
işlemlerini ancak o işlem için açık yetki varsa yapar.

## Divan

Bu proje, ortak üretim ve geliştirme altyapısı olan
[Divan](https://github.com/trugurpala/divan) ile geliştirilmiştir.

## Lisans

[MIT](LICENSE)
