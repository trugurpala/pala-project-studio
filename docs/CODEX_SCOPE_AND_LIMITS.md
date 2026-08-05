# Codex Kapsamı ve Limitleri

Bu kayıt 2026-08-05 tarihinde yerelde alınan güncel Codex manual'i üzerinden
doğrulanmıştır. Host davranışı sürümle değişebileceği için Pala bu sayıları
kod içinde genel ürün gerçeği gibi dondurmaz.

## Doğrulanmış sınırlar

| Yüzey | Codex davranışı | Pala 0.3 kararı |
| --- | --- | --- |
| Skill keşfi | İlk skill listesi model bağlamının en fazla %2'sini, bağlam bilinmiyorsa 8.000 karakteri kullanır. Tam `SKILL.md` yalnız skill seçilince yüklenir. | Tek, açık çağrılan ve 450 kelimenin altında bir yönlendirici skill; ayrıntılar ihtiyaca göre referanslardan okunur. |
| Proje talimatı | Birleştirilmiş proje `AGENTS.md` zinciri varsayılan olarak 32 KiB ile sınırlıdır ve ayarlanabilir. | Değişen plan/durum `AGENTS.md` içine konmaz; ayrı belgelerde tutulur. |
| Hook çıktısı | Modelin görebildiği hook çıktısı varsayılan olarak yaklaşık 2.500 token sonrasında dosyaya taşar. | `SessionStart` için ayrıca 800 token üst sınırı vardır; gerçek çıktı sözleşme testinde 800 karakterin altında tutulur. |
| Oturum sıkıştırma | `PreCompact` ve sıkıştırma sonrası `SessionStart` çalışabilir. | Hook yalnız aktif ticket ve uzlaştırma işaretini korur; tam planı veya test logunu bağlama kopyalamaz. |
| Turn sonu | `Stop` içindeki `decision: block`, ajan için otomatik bir devam istemi oluşturur. | Yalnız açıkça `dirty` kalan aktif işin durum/checkpoint kaydını tamamlatır; test veya build başlatmaz. |
| Hook güveni | Yerel/eklenti hook'ları çalışmadan önce incelenip güvenilmelidir; değişiklik sonrası yeniden güven istenebilir. | Hook kaynakları küçük ve denetlenebilirdir; test, build, ağ, GitHub ve deploy komutu içermez. |

Kaynaklar: [Build skills](https://learn.chatgpt.com/docs/build-skills),
[AGENTS.md talimatları](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Hooks](https://learn.chatgpt.com/docs/hooks),
[Plugin mimarisi](https://developers.openai.com/plugins/concepts/plugins).

## Pala'nın yapabildiği

- Verilen dosya ve araç yetkileri içinde projeyi keşfetmek, plan/durum
  belgelerini uzlaştırmak ve yetkilendirilmiş yerel işi uygulamak.
- Aktif işi dosyada saklayıp yeni oturum veya compaction sonrasında kısa bağlama
  geri yüklemek.
- Değişen belge ve Git çalışma ağacı içeriğini checkpoint ile karşılaştırmak.
- Dar, ticket, milestone ve release doğrulamasını doğru sınırda seçmek.
- Kullanıcının ayrı yetkisi ve mevcut kimlik doğrulaması varsa Git/GitHub
  işlemlerini normal proje akışı olarak yürütmek.

## Pala'nın yapamadığı

- Modelin context window'unu, token kotasını, hızını veya reasoning kapasitesini
  büyütmek.
- Oturum ve araç çalışması dışında sürekli çalışan bağımsız bir ajan olmak.
- Olmayan erişim, kimlik bilgisi, bütçe veya sağlayıcı yetkisi üretmek.
- Kullanıcı kararı gerektiren ürün kapsamını güvenle tahmin edip kalıcılaştırmak.
- Hook içinden gizlice test, ödeme, push, release veya deploy yapmak.
- Runtime veya tarayıcı açılmadan gerçekmiş gibi ekran görüntüsü üretmek.

## Token ve süre yaklaşımı

Pala'nın katkısı yeni token sağlamak değil, aktif prompta taşınan gereksiz
malzemeyi azaltmaktır. Sıra şöyledir: kısa context, durum belgesi, planın yalnız
aktif ticket bölümü, sonra gerekliyse ürün/karar/domain belgeleri. Uzun komut
çıktısı sohbet yerine kısa kanıt özetiyle durum belgesine yazılır.

“%60–80 hızlanma” gibi bir sayı ölçüm olmadan doğru kabul edilemez. Yüzde iddia
edilecekse aynı makine, aynı başlangıç durumu, aynı iş, aynı komutlar ve birden
fazla karşılaştırmalı çalıştırma kaydedilmelidir. Pala 0.3 böyle bir ölçüm yoksa
yüzde raporlamayı açıkça yasaklar.

## Neden MCP eklenmedi?

Pala'nın çekirdek işi yerel proje belgeleri ve Git durumu üzerindedir. Skill,
hook ve deterministik Python scriptleri bunu karşılar. Ayrı MCP sunucusu; süreç,
ağ, kimlik doğrulama ve bakım yükü ekleyecek ama bu sürümde yeni bir yetenek
kazandırmayacaktır. GitHub veya başka canlı sağlayıcı gerektiğinde kurulu
uzman connector/skill koşullu kullanılır.
