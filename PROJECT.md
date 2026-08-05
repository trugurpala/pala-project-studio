# Pala Project Studio

## Ürün amacı

Pala Project Studio, Codex'in mevcut bir yazılım projesini veya yeni bir ürün fikrini doğru kapsamda keşfetmesini, uygulanabilir ticket'lara ayırmasını, aktif işi gerçekten yürütmesini ve sonucu kanıtla kapatmasını sağlayan kişisel bir Codex eklentisidir.

## Ana kullanıcı sonucu

Kullanıcı, AZR Reklam gibi çok fazlı bir projeyi her oturumda yeniden anlatmadan sürdürebilmeli; Codex yalnız aktif iş için gerekli bağlamı okumalı, dar geliştirme döngüsünde hızlı kalmalı ve milestone sonunda tam doğrulamayı atlamamalıdır.

## Temel akış

1. Projeyi ve geçerli talimat zincirini salt okunur keşfet.
2. Mevcut ürün, plan, durum, karar ve Git kanıtını uzlaştır.
3. Yalnız aktif ticket'ı ayrıntılandır ve uygulamaya başla.
4. Dar testlerle ilerle; ilgili ticket kapısını çalıştır.
5. Durumu, gerçek doğrulama kanıtını ve tek sonraki işi checkpoint et.
6. Milestone sonunda tam kalite/runtime kapısını çalıştır.
7. Açık yetki varsa yerel commit, GitHub push/PR veya release işlemini ayrı ayrı gerçekleştir.

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
- Plugin ve skill doğrulayıcıları, birim testleri ve portable paket testi geçer.
- Kişisel Codex eklentisi yeni sürümle kurulur ve yeni oturumda keşfedilir.
