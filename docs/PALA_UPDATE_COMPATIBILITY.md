# Pala güncelleme uyumluluğu

Bu sözleşme Pala'nın “güncel mi?” kontrolü ile gerçek kurulum yükseltmesini
birbirinden ayırır. **Sürüm kontrolü kurulum yapmaz.** Uzak release bilgisini en
fazla 24 saatte bir okuyup yalnız `current`, `update-available` veya
`unknown` sonucu verir. Güncelleme, yeni resmi portable paketin `Update` moduyla
çalıştırılmasıdır.

## Desteklenen 0.8.2 yükseltme matrisi

| Başlangıç | Hedef | Beklenen davranış |
| --- | --- | --- |
| `0.8.0 -> 0.8.2` | Yönetilen eski kurulum | Yeni bundle atomik kurulur; Codex kaydı ve cache yenilenir. |
| `0.8.1 -> 0.8.2` | Yönetilen mevcut release | Sürüm farkı görünür; yeni runtime/skill/hook dosyaları bütünüyle aktarılır. |
| Doğrulanmış legacy Pala | Yönetim kaydı olmayan resmi eski kurulum | Manifest adı, resmi repository ve author doğrulanır; kaynak eski klasör değiştirilmeden yeni yönetilen kurulum etkinleştirilir. |

Bu satırlar release kanıtı ancak gerçek yayımlanmış paket matrisi çalıştırılıp
`passed` kaydedildiğinde olur. Sözleşmenin bulunması tek başına yükseltme kanıtı
değildir.

## Koruma durumları

- Kurulum ağacında eklenmiş, değiştirilmiş, eksik veya symlink dosya varsa
  sonuç `modified` olur. Pala kullanıcı malzemesini birleştirmez veya ezmez.
- Aynı isimli fakat resmi Pala olarak doğrulanamayan kurulum ya da marketplace
  kaydı `external_conflict` olur ve değiştirilmez.
- Aktivasyon veya Codex CLI adımı başarısızsa önceki çalışan bundle rollback ile
  geri getirilir.
- Yeni çekirdek dosyalar portable bundle'ın tam allowlist'i üzerinden aktarılır;
  eksik zorunlu runtime sibling paketi daha staging başlamadan reddettirir.

## Uzmanlar ve oturum sınırı

Yeni isteğe bağlı uzmanlar normal Install/Repair/Update sırasında indirilmez.
Yalnız owner açıkça `-InstallExperts` verdiğinde sürüm ve SHA-256 kilitleriyle
Pala'ya ait ayrı state klasörüne kurulur. Eksik uzman çekirdek Pala kurulumunu
bozuk göstermez.

Kurulum diskteki plugin ve Codex cache içeriğini yeniler; açık bir sohbetin
önceden yüklediği skill listesini geriye dönük değiştirdiğini iddia etmez.
Güncellemeden sonra yeni sohbet açılır ve Doctor sonucu yeniden okunur.
