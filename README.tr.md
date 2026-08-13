# Pala

**Provider-Independent Local Software Delivery OS**

Pala, bir yazılım fikrini veya mevcut projeyi kalıcı plana, sınırlı uygulamaya,
doğrulanmış kalite kanıtına ve yayınlanabilir pakete dönüştürür. Kullanıcı
kontrolünü korur; AI sağlayıcıları değiştirilebilir kalır.

Codex'e şunu yaz:

> https://github.com/trugurpala/pala-project-studio eklentisini kur ve guncel oldugunu dogrula.

Codex kurulum sözleşmesi: Yalnız eklentinin kaydedilmesi başarı değildir. Codex
aynı kurulum yolculuğunda kurulu eklenti kökünü bulur, içindeki Pala installer
transaction'ını çalıştırır ve ancak plugin, runtime bundle, zorunlu Workbench
ve sürüm Doctor tarafından sağlıklı doğrulanırsa başarılı
der. Kullanıcının bu iç adımları bilmesi veya elle çalıştırması gerekmez.

Güncel sürüm: **1.1.2**

## Pala ne yapar?

- Kod anlayışı için güncel ve gerekli bağlamı seçer.
- Yerel güvenlik kontrollerini sınırlı ve kanıta bağlı çalıştırır.
- Proje gerektiriyorsa gerçek tarayıcı doğrulaması üretir.
- Quality Engine ile gerçek test sonuçlarını kabul maddelerine bağlar.
- Failure Intelligence ile doğrulanmış hata çözümlerini güvenle hatırlar.
- ReleaseTruth ile yerel paket, public yayın ve deploy gerçeğini ayırır.
- Tek, salt-okunur PALA CONTROL CENTER üzerinden kullanıcı durumunu gösterir.

## Güvenli teslim

Pala aynı anda tek canonical görevi yürütür. Dar geliştirme kontrollerini ve
release sınırındaki tam kapıları birbirinden ayırır. Test çalışmadıysa `passed`
demez; commit, push, PR, tag, yayın ve deploy işlemlerini açık yetki olmadan
yapmaz.

Durum ve kanıt yerel kalır. Credential, `.env`, transcript, cache, gerçek
müşteri verisi ve makineye özel kurulum durumu pakete girmez. Hook'lar test,
build, ağ veya GitHub mutasyonu başlatmaz.

## Kurulum ve güncelleme

Aynı doğal dil isteği temiz kurulum, onarım ve güvenli güncellemeyi yönetir.
Pala mevcut kurulumu ve sahipliği denetler, bütünlüğü doğrular, değişikliği
geçici alanda hazırlar, health kontrolünden sonra atomik etkinleştirir ve
hata durumunda geri alır. Sağlıklı exact sürüm zaten varsa ikinci kurulum
no-op olur. Yalnız plugin sürümünün eşit olması `CURRENT` sayılmaz.

Portable paket çıkarıldıysa:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
```

Devam: [kurulum](docs/VIBE_INSTALL.md), [ilk oturum](docs/VIBE_FIRST_SESSION.md),
[güvenlik](SECURITY.md), [belgeler](docs/README.md), [English README](README.md).

## İleri teknik ayrıntılar

Provider sürümleri, provenance, integrity, freshness ve lifecycle politikaları
[mimari belgesinde](docs/ARCHITECTURE.md) yer alır. Bu araçlar advisory kalır;
tamamlanma kararını yalnız Quality Engine verir.
