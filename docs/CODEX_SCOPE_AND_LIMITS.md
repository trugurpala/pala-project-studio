# Codex Kapsamı ve Limitleri

Bu kayıt 2026-08-09 tarihinde Codex host davranışı (plugin hooks /
additionalContext rendering + skill progressive disclosure) üzerinden
yeniden hizalanmıştır. Host sürümü değişebilir; Pala bu sayıları ürün
gerçeği gibi sonsuza dondurmaz — sabitleri değiştirmeden önce resmî
Codex kaynaklarını yeniden oku.

## Doğrulanmış sınırlar (host)

| Yüzey | Codex davranışı | Pala kararı |
| --- | --- | --- |
| Skill keşfi | Skill indeksi küçük tutulur; tam `SKILL.md` seçilince yüklenir. | Tek yönlendirici skill; gövde ince; ayrıntı `references/`. |
| Proje talimatı | Birleşik `AGENTS.md` zinciri boyut sınırlıdır. | Değişen iş STATUS/PLAN/PROGRESS’te; `AGENTS.md` yalnız kalıcı kurallar. |
| Hook çıktısı | Modelin gördüğü hook çıktısı ~2500 token sonra spill dosyasına taşabilir. | Hook kısa, yerel, secretsız; test/build/ağ yok. |
| additionalContext | Her değer ~**1000 token** sert tavan; aşımda middle-truncate. | SessionStart **token+char** çift bütçe; cold packet öncelikli; presence + next action kenarda korunur. |
| Oturum sıkıştırma | `PreCompact` + sonrası `SessionStart` olabilir. | Yalnız aktif ticket / reconcile / cold packet; tam plan veya test logu yok. |
| Turn sonu | `Stop` `decision: block` otomatik devam istemi üretebilir. | Yalnız dirty aktif iş checkpoint; test/build başlatmaz. |
| SessionEnd timeout | Varsayılan 1s; yapılandırılan değer **en fazla 3s**; aşım clamp + `/hooks` uyarısı. | `hooks.json` SessionEnd `timeout: 3`; handler yalnız yerel heartbeat (ağ/test yok). |
| Hook güveni | UI’da incelenip güvenilmeli. | Doctor `hook_safety` ≠ `/hooks` trust (`configured-not-verified` until human). |

Kaynaklar: [Build skills](https://learn.chatgpt.com/docs/build-skills),
[AGENTS.md talimatları](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Hooks](https://learn.chatgpt.com/docs/hooks),
[Plugin mimarisi](https://developers.openai.com/plugins/concepts/plugins),
Codex host `additionalContext` rendering (~1000-token hard cap).

## Codex unuttu → Pala ne zaman geri getirir?

Host `SessionStart` kaynakları: `startup` | `resume` | `clear` | `compact`
([Hooks](https://developers.openai.com/codex/hooks)). Pala matcher’ı bu dördünü
de kapsar. `PreCompact` diskte `needs_reconcile` işaretler; compact sonrası
SessionStart cold packet + aktif ticket + next action enjekte eder (char 1800 +
approx-token ≤900; host ~1000 tavan).

**Yapamaz:** Turn içinde, host event olmadan “unutunca kendini getir”. Mid-turn
forget için kullanıcı `durumu oku` / yeni sohbet / cold packet ister. Soft
restart bazı CLI sürümlerinde SessionStart atlayabilir (host boşluğu; Pala
uydurmaz). Peer kalıp: dosya hafızası + compact sonrası yeniden enjekte — sürekli
sohbet belleği değil.

## Pala'nın yapabildiği

- Verilen dosya ve araç yetkileri içinde projeyi keşfetmek, plan/durum
  belgelerini uzlaştırmak ve yetkilendirilmiş yerel işi uygulamak.
- Aktif işi dosyada saklayıp yeni oturum, resume/clear veya compaction sonrasında
  kısa bağlama (cold packet) geri yüklemek.
- Değişen belge ve Git çalışma ağacı içeriğini checkpoint ile karşılaştırmak;
  aynı snapshot'ın atomik commit edilmesini yeni işten ayırmak.
- Dar, ticket, milestone ve release doğrulamasını doğru sınırda seçmek.
- Kullanıcının ayrı yetkisi ve mevcut kimlik doğrulaması varsa Git/GitHub
  işlemlerini normal proje akışı olarak yürütmek.

## Pala'nın yapamadığı

- Modelin context window'unu, token kotasını, hızını veya reasoning kapasitesini
  büyütmek.
- Host `SessionStart` / `PreCompact` olmadan mid-turn unutmayı otomatik onarmak.
- Oturum ve araç çalışması dışında sürekli çalışan bağımsız bir ajan olmak.
- Olmayan erişim, kimlik bilgisi, bütçe veya sağlayıcı yetkisi üretmek.
- Kullanıcı kararı gerektiren ürün kapsamını güvenle tahmin edip kalıcılaştırmak.
- Hook içinden gizlice test, ödeme, push, release veya deploy yapmak.
- Runtime veya tarayıcı açılmadan gerçekmiş gibi ekran görüntüsü üretmek.
- Doctor `hook_safety=passed` ile Codex `/hooks` UI trust’ını aynı saymak.

## Token ve süre yaklaşımı

Pala'nın katkısı yeni token sağlamak değil, aktif prompta taşınan gereksiz
malzemeyi azaltmaktır. Sıra şöyledir: kısa SessionStart (presence + cold
packet), durum belgesi, planın yalnız aktif ticket bölümü, sonra gerekliyse
ürün/karar/domain belgeleri. Uzun komut çıktısı sohbet yerine kısa kanıt
özetiyle durum belgesine yazılır.

SessionStart çift bütçe kullanır:

- **Karakter tavanı** (`SESSION_CONTEXT_CHAR_LIMIT` = 1800). `hooks.json`
  içindeki `additionalContextLimit: 1800` bu Pala char-sync alanıdır; Codex
  host’un “token spill eşiği” semantiğiyle aynı şey değildir.
- **Yaklaşık token bütçesi** (`SESSION_CONTEXT_TOKEN_BUDGET` = 900), host
  ~1000-token `additionalContext` sert tavanının altında.

Uzun sağlık düzyazısı cold packet’in önüne geçmez; budama gerektiğinde middle
kesilirken presence ve kuyruk (next action / gate) korunur.

“%60–80 hızlanma” gibi bir sayı ölçüm olmadan doğru kabul edilemez. Yüzde iddia
edilecekse aynı makine, aynı başlangıç durumu, aynı iş, aynı komutlar ve birden
fazla karşılaştırmalı çalıştırma kaydedilmelidir. Ölçüm yoksa yüzde raporlamak
yasaktır.

## Neden MCP eklenmedi?

Pala'nın çekirdek işi yerel proje belgeleri ve Git durumu üzerindedir. Skill,
hook ve deterministik Python scriptleri bunu karşılar. Ayrı MCP sunucusu; süreç,
ağ, kimlik doğrulama ve bakım yükü ekleyecek ama bu sürümde yeni bir yetenek
kazandırmayacaktır. GitHub veya başka canlı sağlayıcı gerektiğinde kurulu
uzman connector/skill koşullu kullanılır.
