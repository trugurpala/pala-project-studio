# Pala Project Studio

![CI](https://github.com/trugurpala/pala-project-studio/actions/workflows/quality.yml/badge.svg)
[![Release v0.5.0](https://img.shields.io/badge/release-v0.5.0-2ea44f)](https://github.com/trugurpala/pala-project-studio/releases/tag/v0.5.0)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Pala Project Studio, Codex'in uzun soluklu yazılım projelerinde aktif işi
kaybetmeden ilerlemesine yardımcı olan Türkçe odaklı bir proje yürütme
eklentisidir. Ürün kararlarının yerine geçmez; mevcut proje belgelerini bulur,
aktif işi kısa bir kontrol noktasında tutar ve doğrulamayı değişikliğin riskine
göre katmanlandırır.

- Güncel sürüm `v0.5.0`'dır (Project Memory Contract). Windows kurucusu, taşınabilir ZIP,
  `Update` ve `Doctor` akışları 0.4.x üzerinde doğrulanmıştır; 0.5 bellek sözleşmesi
  yerel `verify` ile kanıtlanır.

## Hızlı başlangıç

En güncel, taşınabilir sürümü indir:

[Pala Project Studio 0.5.0'ı indir](https://github.com/trugurpala/pala-project-studio/releases/latest/download/pala-project-studio-0.5.0.zip)

ZIP'i açtıktan sonra içindeki klasörde şu komutu çalıştır:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
```

Pala kurulum sırasında ne yapacağını açıkça gösterir. `-WhatIf` ile önce
önizleyebilir, `-Mode Doctor` ile kurulumun sağlığını kontrol edebilirsin.

Kayıtlı bir projede hafızayı insan dilinde görmek için:

```powershell
py -3 scripts\pala_state.py memory --cwd .
```

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

## Açık kaynağa katkı

Bir vibe coder Pala'ya örneğin `bugün açık kaynağa katkı yapalım` diyebilir.
Pala hedef depoda önce salt-okunur keşif yapar; katkı kurallarını, AI kullanım
politikasını, atanma/claim şartlarını, CLA/DCO beklentisini, açık PR'ları ve
issue sahipliğini kontrol eder. Güvenlik hassasiyetli, başkasına atanmış,
mevcut uygulama PR'ı bulunan veya AI katkısını yasaklayan adayları otomatik
katkı akışından çıkarır.

Uygun iş seçildikten sonra değişiklik hedef projenin mevcut test ve kalite
kapılarıyla doğrulanır. `scripts/pala_oss.py` politika, açıklanabilir issue
puanlama, approval fingerprint ve draft-PR publish kapısını ağsız ve
deterministik yürütür. OSV-Scanner ve zizmor yalnız zaten kuruluysa ve ilgili
proje yüzeyi varsa isteğe bağlı ek kanıt sağlar; bunların yokluğu Pala'yı
çalışamaz hâle getirmez.

Fork, branch push ve draft PR üç ayrı uzak-yazma yetkisidir. Merge, tag,
release, force-push, silme ve görünürlük değişimi bu akıştan otomatik yetki
almaz. Ayrıntılı sözleşme için
[OSS Contribution Flow](skills/pala-project-finisher/references/oss-contribution.md)
belgesine bakın.

## Windows kurulumu

GitHub deposunu indirdikten veya portable ZIP'i açtıktan sonra kök klasörde tek
komut yeterlidir:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
```

Kurucu mevcut Codex ve Pala envanterini önce okur. Doğru sürüm varsa dosyalara
dokunmadan `Zaten hazır` der; eksik veya Pala'ya ait eski sürümü doğrulanmış
staging alanından kurar; aynı adlı yabancı kaydı ezmez. Repo marketplace'i ve
eklenti kurulumu yalnız Codex'in desteklenen `codex plugin marketplace` ve
`codex plugin` komutlarıyla yapılır. Kullanıcının kişisel marketplace JSON'u
elle değiştirilmez.

```powershell
# Hiçbir değişiklik yapmadan önizle
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -WhatIf

# Sağlık, proje kaydı ve hook güvenini kontrol et
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor

# Onar, güncelle veya güvenli biçimde kaldır
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Repair
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Update
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Uninstall
```

Kurulum aynı oturumda doğrulanır. Yeni skill ve hook'ların güvenilir biçimde
yüklenmesi için kurulumdan sonra yeni bir Codex sohbeti açılır. Hook güveni
eksikse kurucu güvenlik kontrolünü atlamaz; Codex'te `/hooks` komutunu gösterir.

## Güvenli uzman işçileri

Pala tek karar verici olarak kalır. Aşağıdaki araçlar Pala'nın kendi doğrulanmış
alanında, yalnız gerektiğinde çalışan uzman yardımcılarıdır:

- **Graphify:** Kod ve doküman ilişkilerini yerelde çıkarır. Kod analizi
  `--code-only` çalışır; anlamsal doküman işi yalnız Pala'nın yerel Ollama'sına
  gider.
- **Serena:** Python, JavaScript/TypeScript, PHP ve PowerShell sembol
  gezinmesi için salt-okunur yardımcıdır. Bellek, dashboard, shell ve düzenleme
  araçları kapalıdır.
- **codebase-memory:** Çok büyük veya çok dilli projelerde yalnız tek seferlik
  yerel mimari/kod grafiği komutları çalıştırır.
- **Ollama + Qwen3 4B:** Pala'nın ayrı model klasöründe ve yalnız bilgisayarın
  içinde çalışır; mevcut Ollama modellerini değiştirmez.

Bu işçiler Pala'nın yerine karar vermez, GitHub'a veya bulut servislerine proje
kodunu göndermez. Her indirilen araç kilitli sürüm ve SHA-256 doğrulamasıyla
kontrol edilir.

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
