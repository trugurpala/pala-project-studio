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
- Hook içinde test, build, ağ veya GitHub işlemi çalıştırmaz.
- Commit, push, PR, release ve deploy için ayrı kullanıcı yetkisini korur.

Pala daha fazla token veya daha geniş bir Codex bağlamı oluşturamaz. Katkısı,
gereksiz belgeleri her turda tekrar yüklemeyi ve ağır doğrulamayı yanlış yerde
çalıştırmayı azaltmaktır. Ölçülmemiş hız ya da token tasarrufu yüzdesi vaat
etmez.

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
