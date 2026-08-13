# Vibe coder — ilk 10 dakika

Tek cümle: Codex’i aç; Pala’yı **Codex-native** kur; yeni sohbette yazılım işi söyle.
ChatGPT Plus düz sohbet değil. ZIP Plugins’e yüklenmez.

Tam kurulum mitleri / hata tablosu: [VIBE_INSTALL.md](VIBE_INSTALL.md).

## 1) Karar ağacı

1. **ChatGPT Work / Codex** veya **Codex CLI** var mı?
   - **Hayır** → dur. Yanlış yüzey (Plus sohbet ≠ kurulum).
   - **Evet** → adım 2.
2. İnternet + GitHub veya yerelde Pala klasörü var mı?
   - **Evet** → **birincil kapı** (aşağıdaki 2 CLI komutu).
   - **Yok / tam Doctor toolkit** → [Çevrimdışı / tam kurulum](#çevrimdışı--tam-kurulum).

## 2) Birincil kapı — doğal dil kurulumu

Normal kullanıcı Codex'e “`https://github.com/trugurpala/pala-project-studio`
eklenti­sini kur ve güncel olduğunu doğrula” demelidir. Pala mevcut Git
marketplace snapshot'ını inceler, gerekirse yeniler, plugin cache'ini yeniden
kurar ve Doctor ile temel sürümleri doğrular.

İleri CLI akışı yalnız kurulu Codex yardımında desteklendiği doğrulandıktan
sonra kullanılmalıdır:

Marketplace ve eklenti adı: `pala-project-studio`
→ kurulum kimliği `pala-project-studio@pala-project-studio`.

**GitHub uzak:**

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

**Yerel checkout / klasör kökü** (`.agents/plugins/marketplace.json` burada):

```powershell
codex plugin marketplace add C:\path\to\pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

`C:\path\to\pala-project-studio` yerine kendi kök yolunu yaz.

## 3) Üç GUI adımı

1. Codex Work’te Plugins / Directory görünüyor (doğru app).
2. `/hooks` → Pala hook’larına **güven** (bypass yok).
3. **Yeni sohbet** aç (başlık önerisi: **Kodlamaya başla**).
   Eski `/hooks` thread’inde kalma.

**Doctor `hook_safety=passed` ≠ Codex `/hooks` trust.**  
`hook_safety` yalnız dosya kontrolüdür. Trust Work’te interaktiftir;
`codex exec` ile tamamlanmaz.

## 4) İlk mesaj (yapıştır)

```
Bu projeyi sürdür. Önce mevcut durumu oku, aktif işi bul, yetkilendirilmiş yerel uygulamaya kaldığı yerden devam et.

Kapsam: read-first. Commit/push/release yapma. Hook içinde test/build başlatma.
STATUS.md ve docs/VIBE_FIRST_SESSION.md ile uyumlu ilerle; tek sonraki işi söyle.
```

## 5) Beklenen ilk sonuç

- **Kayıtlı projede** SessionStart veya skill açılışı:
  **Pala burada — bu oturumda yanındayım.** (güven satırı; token/kota büyütme
  iddiası yok)
- **Kayıtsız klasörde** SessionStart **boş** kalır — bozuk kurulum değil;
  önce Pala register / `pala_state` akışı gerekir. Plugin kurulu ≠ her cwd’de
  otomatik hafıza.
- SessionStart metni Codex `additionalContext` token tavanının altında kalır
  (Pala çift bütçe: char + approx-token). Uzun sağlık düzyazısı cold packet’in
  önüne geçmez; middle-truncate olsa bile presence satırı korunacak şekilde
  tasarlanır.
- STATUS/PROGRESS/workflow okunur
- Aktif ticket yoksa açıkça söylenir (uydurma ticket yok)
- Commit/push/verify otomatik başlamaz

**Çoklu ajan / görev:** İşe başlamadan önce `STATUS.md` → `PLAN.md` içindeki
aktif `M*-T*` veya `DEMO-*` kartları → `DEBUGGING.md` sırasıyla oku; **tek bir
task ID** seç ve o kartın dosyalarında kal. Kanıt yalnız
`passed` | `not-run` | `blocked` | `configured-not-verified`. Hook'lar test,
build veya ağ çağrısını kendiliğinden başlatmaz.

## Çevrimdışı / tam kurulum

ZIP = **çıkar → kaydet**, Codex Plugins ZIP-upload değil.

1. Portable ZIP’i aç; **kök** klasöre gir.
2. `Kur.cmd` çift tık **veya**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Doctor’da çekirdek `plugin_ready` / `healthy` beklenir. Sonra aynı **üç GUI
adımı** (`/hooks` → güven → yeni sohbet).

Kısa ZIP notu: [KUR.md](../KUR.md). Mitler: [VIBE_INSTALL.md](VIBE_INSTALL.md).

## İsteğe bağlı (kurulumdan sonra)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
py -3 scripts\pala_state.py memory --cwd .
py -3 scripts\pala_demo.py seed --demo-root examples\demo-software-project
py -3 scripts\pala_self_audit.py
```

Yerel store: `%USERPROFILE%\Desktop\Codex\pala.sqlite`.
Fork paketi: [FORK_PACK.md](FORK_PACK.md).

## Codex unuttu → ne olur?

Pala **sürekli bellek değildir**; Codex host event’lerinde kısa yön yeniden
enjekte eder. Pencere/kota büyütmez.

| Durum | Pala ne yapar? | Sen ne yaparsın? |
| --- | --- | --- |
| Yeni sohbet / `startup` | SessionStart → presence + cold packet + aktif ticket + next | Genelde otomatik; STATUS’a güven |
| `resume` / `clear` | SessionStart yeniden enjekte (matcher: startup\|resume\|clear\|compact) | Aktif ticket’ı onayla; uydurma yok |
| Sıkıştırma (`PreCompact` → `compact`) | PreCompact `needs_reconcile`; sonraki SessionStart cold packet + “Context was compacted…” | Edite geçmeden STATUS + aktif PLAN kartı |
| Turn **içinde** unutma (host event yok) | **Yeniden enjekte yok** — mid-turn hook yok | Yaz: `durumu oku` / yeni sohbet; veya cold packet iste |
| Soft restart (bazı CLI sürümleri SessionStart atlar) | Hook çalışmayabilir (host boşluğu) | Yeni sohbet veya açıkça STATUS/PLAN oku |
| Kayıtsız cwd | SessionStart **sessiz** (bozuk değil) | Önce register |

Kalıcı gerçek: dosyalar (`STATUS.md` / `PLAN.md` / workflow) + isteğe bağlı cold
packet. Soft “hatırlıyorum” kanıt sayılmaz.

Dağıtım sınırları: [PALA_EVERYWHERE.md](PALA_EVERYWHERE.md).
Kapsam: [CODEX_SCOPE_AND_LIMITS.md](CODEX_SCOPE_AND_LIMITS.md).
Local candidate (owner): [RELEASE_1.1.1.md](RELEASE_1.1.1.md).

## Bilerek yok

- ChatGPT Plus sohbete ZIP / metin yapıştırarak kurulum
- Codex Plugins’e ZIP yükleme UI
- Ölçülmemiş “daha hızlı / daha az token” yüzdesi
- Hook içinden commit, push, release veya deploy
- Doctor yeşil = tam yetki / `/hooks` bitti iddiası
- Mid-turn “unutunca kendini getir” iddiası (host event olmadan)
