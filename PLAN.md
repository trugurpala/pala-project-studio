# Pala Project Studio 0.3–0.3.2 Uygulama Planı

## M1 — Codex-native kapsam ve hafıza

- [x] Codex plugin, skill, hook, AGENTS, proje, context ve GitHub sınırlarını güncel resmî manual üzerinden doğrula.
- [x] ZIP kaynağını ayrı Git çalışma alanına al ve mevcut kurulu sürümle eşliğini doğrula.
- [x] Ürün, plan, durum ve karar belgelerini Pala'ya kaydet.
- [x] AZR gibi mevcut belge adlarını otomatik keşif adaylarına ekle.
- [x] Checkpoint kanıt özeti ve belge/Git fingerprint'iyle durum eskimesini algıla.

## M2 — Token-verimli aktif yürütme

- [x] SessionStart çıktısını aktif ticket, tek sonraki iş, engel ve gerekli belge yollarıyla sınırla.
- [x] Skill'i bütün planı okumak yerine durum + aktif ticket bölümüyle progressive disclosure kullanacak biçimde güncelle.
- [x] Ticket'ı mikro checkbox değil, bağımsız doğrulanabilir kullanıcı sonucu olarak tanımla.
- [x] Uzun işte yeniden planlamayı engelle; gerçek blocker yoksa güvenli yerel işi sürdür.

## M3 — Doğrulama ve performans dürüstlüğü

- [x] Dar, ticket, milestone ve release doğrulama katmanlarını tanımla.
- [x] Pala hook'larının hiçbir kalite komutunu otomatik çalıştırmadığını sözleşme testiyle koru.
- [x] Süre/başlangıç ölçümü olmadan yüzde hız veya token kazancı raporlamayı yasakla.
- [x] Tek komutlu tam plugin doğrulama scripti ekle.

## M4 — GitHub ve dağıtım

- [x] GitHub'a alınan/alınmayan verileri ve ayrı yetki sınırlarını skill referansına işle.
- [x] Manifest, README, lisans, güvenlik ve CI yüzeylerini tamamla.
- [x] Birim, sözleşme, skill, plugin ve portable paket doğrulamalarını çalıştır.
- [x] Yeni portable ZIP üret ve SHA-256 kaydet.
- [x] Kişisel marketplace kaynağını güncelle, cachebuster uygula ve eklentiyi yeniden kur.
- [x] Kaynağı secretsız özel GitHub deposunda sakla ve CI sonucunu doğrula.

## M5 — AZR'ye dönüş

- [x] AZR'nin gerçek F2 durumunun ayrı `feat/f2-collection-requests` worktree'inde ilerlediğini salt okunur doğrula.
- [x] Aktif Task 8 oturumuna dosya çakışması yaratmadan kesin dönüş noktasını ve bekleyen görsel kabul işini belirle.

## M6 — Büyük repo kod zekâsı

- [x] PALA-031: `code-review-graph` entegrasyonunu isteğe bağlı ve yerel-first olarak ekle.
- [x] Graph bulunmadığında dürüst `git diff`/`rg` fallback'i sağla.
- [x] Windows kurulumu, lisans kaydı, bağımsız testler ve portable paketi doğrula.

## M7 — Owner demo ve 0.3.1 dağıtımı

- [x] Kullanıcıya gösterilebilir ticket sonunda güncellenen secretsız `OWNER_DEMO.md` profilini ve şablonunu ekle.
- [x] Demo belgesini keşif/kayıt/fingerprint akışına bağla; gerçek tarayıcı olmadan ekran kanıtı üretmeyi yasakla.
- [x] 0.3.1 cachebuster, portable ZIP, kişisel kurulum, private GitHub push ve CI kanıtını tamamla.

## M8 — Checkpoint commit öz-referansı ve 0.3.2

- [x] Temiz AZR ağacında checkpoint commit'inden sonra oluşan yanlış stale uyarısını gerçek kullanımda yeniden üret.
- [x] Değişen yol sayısı + birleşik içerik özetiyle yalnız aynı snapshot'ı taşıyan descendant commit'i kabul et.
- [x] Aynı checkpoint'ten sonraki ek/farklı commit'in uzlaştırma gerektirmeye devam ettiğini sözleşme testiyle koru.
- [ ] 0.3.2 tam doğrulama, portable ZIP, kişisel kurulum, private GitHub push ve CI kanıtını tamamla.
