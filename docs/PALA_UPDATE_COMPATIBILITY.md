# Pala güncelleme uyumluluğu

Bu sözleşme Pala'nın “güncel mi?” kontrolü ile gerçek kurulum yükseltmesini
birbirinden ayırır. **Sürüm kontrolü kurulum yapmaz.** Uzak release bilgisini en
fazla 24 saatte bir okuyup yalnız `current`, `update-available` veya
`unknown` sonucu verir. Güncelleme, yeni resmi portable paketin `Update` moduyla
çalıştırılmasıdır.

## 1.2.0 için yayınlanmış-byte yükseltme matrisi

| Başlangıç | Kurulum türü | `1.2.0` hedef davranışı |
| --- | --- | --- |
| `0.4.4` | Yönetilen ve doğrulanmış legacy | İki yol da izole profilde atomik olarak güncellenir; legacy kaynak yerinde korunur. |
| `0.8.0` | Yönetilen ve doğrulanmış legacy | İki yol da izole profilde atomik olarak güncellenir; legacy kaynak yerinde korunur. |
| `0.8.1` | Yönetilen resmi release | Yeni bundle atomik kurulur; Codex kaydı ve cache yenilenir. |
| `1.0.0` | Yönetilen resmi release | Sürüm farkı görünür; yeni runtime, skill ve hook dosyaları bütünüyle aktarılır. |
| `1.1.2` | Yönetilen public baseline | No-op ikinci kurulum, Doctor sağlığı, SQLite ve Failure Intelligence sürekliliği korunur. |

Her satır yalnız SHA-256 pinli yayımlanmış ZIP byte'larıyla, ayrı geçici
profilde çalıştırılan gerçek upgrade matrix sonucu `passed` olduğunda kanıttır.
Matrix; ikinci kurulumun no-op olduğunu, Doctor sağlığını, Pala SQLite şema ve
Failure Intelligence satırlarını doğrular. Ağ kullanan bu release kapısı yerel
`verify.py` kapısından ayrıdır; sonuç yoksa durum `not-run` kalır.

## Koruma durumları

- Kurulum ağacında eklenmiş, değiştirilmiş, eksik veya symlink dosya varsa
  sonuç `modified` olur. Pala kullanıcı malzemesini birleştirmez veya ezmez.
- Aynı isimli fakat resmi Pala olarak doğrulanamayan kurulum ya da marketplace
  kaydı `external_conflict` olur ve değiştirilmez.
- Aktivasyon veya Codex CLI adımı başarısızsa önceki çalışan bundle rollback ile
  geri getirilir.
- Yeni çekirdek dosyalar portable bundle'ın tam allowlist'i üzerinden aktarılır;
  eksik zorunlu runtime sibling paketi daha staging başlamadan reddettirir.

## Professional Workbench ve oturum sınırı

CodeGraph ve Semgrep yalnız Pala'nın checksum/provenance doğrulamalı
transaction akışıyla, versioned Pala state klasörlerine kurulur. Playwright
yalnız proje profili gerektirdiğinde kullanılır; Serena lazy fallback, Context7
ise explicit optional external kalır. Retired helper installer'ı artık current
kurulum yüzeyi değildir.

Kurulum diskteki plugin ve Codex cache içeriğini yeniler; açık bir sohbetin
önceden yüklediği skill listesini geriye dönük değiştirdiğini iddia etmez.
Güncellemeden sonra yeni sohbet açılır ve Doctor sonucu yeniden okunur.
