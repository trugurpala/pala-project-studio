# Pala Project Studio

## Ürün amacı

Pala Project Studio, Codex'in mevcut bir yazılım projesini veya yeni bir ürün
fikrini doğru kapsamda keşfetmesini, uygulanabilir ticket'lara ayırmasını, aktif
işi gerçekten yürütmesini ve sonucu kanıtla kapatmasını sağlayan kurulabilir bir
Codex eklentisidir.

## Ana kullanıcı sonucu

Kullanıcı, büyük ve çok fazlı bir projeyi her oturumda yeniden anlatmadan
sürdürebilmeli; Codex yalnız aktif iş için gerekli bağlamı okumalı, dar
geliştirme döngüsünde hızlı kalmalı ve milestone sonunda tam doğrulamayı
atlamamalıdır.

## 0.4 tek-kapı kullanıcı sözleşmesi

Kullanıcı Pala'yı bir kez kurduktan sonra ayrı yardımcı araç adlarını öğrenmek
veya her sohbette ayrı skill çağırmak zorunda kalmamalıdır. Normal bir yazılım
isteği Pala'nın yönlendirici skill'ini örtük olarak etkinleştirebilmeli; Pala
mevcut proje, risk ve araç durumuna göre yalnız gereken uzmanı veya yerel aracı
seçmelidir.

Kurulum tek, görüş bildirmeyen bir Windows akışıdır. Aynı komut:

1. mevcut Codex, Pala, Git, Python, Node, `uv`, MCP ve yardımcı araç durumunu
   keşfeder;
2. doğru sürüm zaten varsa `zaten hazır` diye raporlar ve yeniden kurmaz;
3. eksik veya Pala'ya ait eski parçaları sabitlenmiş sürüm ve doğrulanmış
   bütünlük bilgisiyle kurar;
4. kullanıcıya ait mevcut ayarları, kimlik bilgilerini ve aynı adlı yabancı
   entegrasyonları ezmez;
5. doctor sonucunu ve gerekiyorsa yeni sohbet sınırını doğal Türkçe ile açıklar.

Pala her oturum başlangıcında yalnız yerel ve hızlı sağlık/güncellik durumunu
okur. Ağ kullanan sürüm sorgusu hook içinde çalışmaz; Pala'nın ilk ilgili iş
adımında süreli önbellekle en fazla günde bir kez yapılır. Böylece her oturum
güncellik durumunu görürken çevrimdışı kullanım, başlangıç hızı ve hook güveni
korunur.

## Yönetilen araç politikası

- `RTK`, yalnız eşdeğerlik testlerinden geçen güvenli ve salt-okunur komutlarda
  Pala'nın `PreToolUse` adaptörüyle kullanılabilir. Belirsiz, bileşik veya
  durumu değiştiren komutlar aynen bırakılır.
- `code-review-graph`, büyük veya çapraz modüllü incelemelerde Pala adaptöründen
  çağrılır. Kendi Codex hook, skill veya MCP kurulumunu yaparak ikinci bir
  orkestratör oluşturmaz.
- Context7 ve Playwright mevcutsa korunur; eksikse Codex'in desteklediği MCP
  komutlarıyla eklenir. Aynı isimli farklı kullanıcı ayarı sessizce değiştirilmez.
- OpenSpec bulunan projelerle birlikte çalışılır. Pala'nın kalıcı plan/durum
  sahibi olduğu projelere ikinci bir plan sistemi zorla eklenmez.
- `planning-with-files`ın dayanıklı dosya hafızası ve tamamlanma kapısı
  ilkeleri Pala'nın kendi durum modelinde uygulanır; çakışan hook ve plan
  dosyaları ayrıca kurulmaz.
- `developer-roadmap` mimari ve kalite kapsam kontrolünde başvuru kaynağıdır,
  çalıştırılabilir bağımlılık değildir.
- Ruflo 0.4 çekirdeğine alınmaz; ayrı ajan, daemon, hafıza ve MCP sahipliği
  Pala'nın tek-kapı ve küçük güven yüzeyi hedefiyle çelişir.

## Temel akış

1. Projeyi ve geçerli talimat zincirini salt okunur keşfet.
2. Mevcut ürün, plan, durum, karar ve Git kanıtını uzlaştır.
3. Yalnız aktif ticket'ı ayrıntılandır ve uygulamaya başla.
4. Dar testlerle ilerle; ilgili ticket kapısını çalıştır.
5. Durumu, gerçek doğrulama kanıtını ve tek sonraki işi checkpoint et.
6. Milestone sonunda tam kalite/runtime kapısını çalıştır.
7. Açık yetki varsa yerel commit, GitHub push/PR veya release işlemini ayrı ayrı gerçekleştir.

## Truth Core sözleşmesi

- Bütün durum okuyucuları aynı immutable `ProjectSnapshot` sonucunu tüketir.
- Ortak Git deposu ve her worktree ayrı kimliklenir; kalıcı kayda mutlak özel
  yollar değil sınırlı özetler girer.
- Açık/mevcut worktree, oturumun sahip olduğu dirty ticket, tek uyumlu aktif
  ticket ve çelişkisiz checkpoint sırasıyla değerlendirilir; belirsizlikte
  tahmin yapılmaz.
- v3 canlı oturum koordinasyonudur, kayıtlı Markdown kalıcı ürün projeksiyonudur
  ve migration marker sonrasında v2 yalnız audit/rollback girdisidir.
- Session checkpoint gerçek doğrulama kanıtı, tier, blocker ve non-null basis
  olmadan işi temiz saymaz.

## Değişmez sınırlar

- Eklenti modelin bağlam penceresini, kullanım kotasını veya token bütçesini büyütmez.
- Token katkısı, gereksiz belge ve hook çıktısını ana bağlama taşımamakla sınırlıdır.
- Hook'lar test/build/ağ/GitHub mutasyonu çalıştırmaz; yalnız kısa durum bağlamı ve güvenli devam uyarısı sağlar.
- GitHub isteğe bağlı kalıcılık ve işbirliği yüzeyidir; gizli anahtar veya transcript deposu değildir.
- Kullanıcı yetkisi olmadan commit, push, PR, release, deploy, repo oluşturma veya görünürlük değişikliği yapılmaz.
- Haricî sağlayıcılar ve güncel Codex davranışı için kurulu uzman skill/connector ve resmî kaynaklar kullanılır.

## Git ve GitHub'a alınabilenler

- Plugin manifesti, skill, referanslar, hook tanımı ve deterministik scriptler.
- Testler, CI, paketleme kuralları, ürün/plan/durum/karar belgeleri.
- Hedef projelerde secretsız `.codex/pala-project.json`; proje politikası açıkça
  gerektiriyorsa gözden geçirilmiş `.codex/pala-workflow.json`.
- Gerçek komut adları, sonuç özetleri, süreler ve commit kimlikleri.

## Git ve GitHub'a alınmayanlar

- Token, parola, API anahtarı, OAuth verisi, `.env`, credential veya kişisel veri.
- Sohbet transcriptleri, ham model düşüncesi, hook spill çıktıları ve plugin cache'i.
- Gerçek müşteri/kart/kimlik/banka verisi veya hassas belge içeriği.
- Kullanıcının açıkça paylaşmadığı özel proje içeriği.

## Tamamlanma ölçütü

- Pala durum eskimesini güvenilir biçimde algılar ve yeniden planlama yerine uzlaştırma ister.
- SessionStart bağlamı kısa, secretsız ve aktif ticket odaklıdır.
- Doğrulama katmanları dar/ticket/milestone/release olarak nettir.
- Ölçülmemiş performans iddiası sözleşme testiyle engellenir.
- Kullanıcıya gösterilebilir ticket'larda secretsız owner-demo handoff'u ve
  yalnız gerçek tarayıcı kabulünden gelen görsel kanıt güncellenir.
- Plugin ve skill doğrulayıcıları, birim testleri ve portable paket testi geçer.
- Eklenti GitHub checkout'u veya portable ZIP'den desteklenen Codex CLI
  akışıyla temiz kullanıcı profilinde kurulur ve yeni oturumda keşfedilir.
- Kurulum belirli bir bilgisayar, kullanıcı yolu veya kişisel katalog
  varsaymaz; mevcut kullanıcı kayıtlarını keşfeder ve çakışmaları korur.
