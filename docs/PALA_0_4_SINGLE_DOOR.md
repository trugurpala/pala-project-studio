# Pala 0.4 Tek-Kapı Tasarımı

## Kullanıcı deneyimi

Kullanıcı GitHub deposunu veya portable ZIP'i Codex'e verir ve yalnız “Pala'yı
kur” der. Codex kökteki tek Windows girişini çalıştırır. Kurucu seçenek sihirbazı
açmaz; makineyi keşfeder, doğru bileşeni korur, eksik Pala-owned bileşeni kurar,
doctor çalıştırır ve sonucu doğal Türkçe özetler.

Yeni plugin içeriğinin mevcut model bağlamına geçmişe dönük enjekte edildiği
varsayılmaz. Kurulum aynı oturumda tamamlanıp doğrulanabilir; Pala'nın yeni
skill, MCP ve hook'larının güvenilir biçimde yüklenmesi yeni sohbet sınırıdır.

## Bileşen modeli

```text
Kullanıcı isteği
    -> Pala yönlendirici skill
        -> proje keşfi ve kalıcı durum
        -> uygun kalite/runtime kapısı
        -> gerekirse RTK (kompakt komut çıktısı)
        -> gerekirse code-review-graph (büyük repo etki dilimi)
        -> gerekirse Context7 (güncel kütüphane belgeleri)
        -> gerekirse Playwright (gerçek tarayıcı kabulü)
        -> projede varsa OpenSpec artifact uyumu
```

Yardımcılar aynı anda sürekli çalışmaz. Pala görevin riskine göre en küçük
yeterli aracı çağırır. Son kararın kanıtı her zaman kaynak, test, runtime ve
gerçek sağlayıcı durumudur; graph, roadmap veya model tahmini tek başına kanıt
değildir.

## Kurulum sahipliği

Pala her yönettiği bileşen için ad, sürüm, kaynak, SHA-256, lisans, kurulum
yolu ve son doğrulama zamanını secretsız envanterde tutar. Önceden kurulmuş bir
bileşen üç sınıftan birine girer:

- `ready`: Beklenen kimlik/sürüm; değişiklik yok, “zaten hazır”.
- `managed-update`: Pala'nın eski sürümü; staging + doğrulama + atomik değişim.
- `external-conflict`: Kullanıcının veya başka aracın aynı isimli farklı ayarı;
  değiştirilmez, doctor açıkça raporlar.

Kurucu bütün dosya ağacını silip yeniden kopyalamaz. Yeni içerik geçici
staging alanında doğrulanır; eski çalışan sürüm rollback klasörüne atomik
taşınır; etkinleştirme başarısızsa geri yüklenir. Uninstall yalnız envanterde
Pala-owned olarak kayıtlı ve halen beklenen fingerprint'i taşıyan girdileri
kaldırır.

## Oturum ve güncelleme

SessionStart hook'u ağ kullanmadan kurulu sürüm, son uzak kontrol, bekleyen
güncelleme, hook güveni, aktif ticket ve tek sonraki adımı kısa biçimde okur.
Pala skill'i ilgili bir görevde ilk kez çalıştığında önbellek 24 saatten eskiyse
GitHub release bilgisini salt-okunur sorgular. Çevrimdışı hata işi engellemez.

Güncelleme aktif dirty ticket'ı, kullanıcı projesini veya mevcut sohbet
bağlamını değiştirmez. Yeni paket staging'de doğrulanır ve plugin yeniden
kurulursa kurucu yeni sohbet gerektiğini söyler.

## Büyük işte patlamama kuralları

1. Bir oturum bir coherent ticket sahibi olur; aynı repo içindeki paralel
   oturumlar ayrı kimlikle izlenir.
2. Planın tamamı her tur yüklenmez; aktif ticket ve tek sonraki adım yüklenir.
3. Her hata tekrar denenmez. Aynı nedensel hata için sınırlı tekrar, sonra açık
   blocker ve kanıt kaydı vardır.
4. Küçük işte graph, geniş MCP taraması veya çoklu ajan başlatılmaz.
5. Yeni bağımlılık eklenmeden mevcut proje, resmî üretici ve lisans/güvenlik
   durumu kontrol edilir.
6. Başarısız test veya yarım build temiz/tamamlanmış durum üretemez.
7. Kurulum ve durum JSON'ları atomik; loglar döndürülen, sınırlı ve secretsızdır.
8. Release yalnız source, portable, temiz kurulum, rollback ve Windows/Ubuntu
   CI kanıtlarından sonra hazırlanır.

## Doğrulama matrisi

| Alan | Zorunlu kanıt |
| --- | --- |
| Tek komut | Repo ve ZIP kökünden Windows PowerShell 5.1/7 |
| İdempotency | İzole profilde 50 ardışık install/doctor/update, ikinci çalışmadan sonra sıfır fark |
| Çakışma | Mevcut doğru, eski Pala-owned ve yabancı aynı adlı MCP/tool senaryoları |
| Rollback | Copy, doğrulama ve etkinleştirme hata enjeksiyonunda eski sürüm çalışır |
| RTK | Allowlist, argüman koruma, çıkış kodu, unsafe fallback ve RTK-yok testleri |
| Büyük repo | Graph var/yok/eski durumları ve kaynak+test doğrulaması |
| Oturum | startup, resume, compact, paralel session ve dirty-work koruması |
| Paket | Tekrarlanabilir ZIP, temiz açma, portable içinden verify, secrets taraması, SHA-256 |
| CI | Windows ve Ubuntu source/portable testleri başarılı |

## Codex sınırı

GitHub deposu kendi kendine komut çalıştıramaz. Kullanıcının “kur” talimatı
Codex'e kurucuyu çalıştırma yetkisi verir; Codex dosyaları indirir/denetler,
tek giriş komutunu çalıştırır ve doctor kanıtını verir. Yeni kurulan plugin
bileşenleri desteklenen ürün davranışı gereği yeni sohbette güvenilir biçimde
yüklenir. Pala bu sınırı gizlemez veya “aynı oturumda kesin aktif” diye yanlış
vaatte bulunmaz.
