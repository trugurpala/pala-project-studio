# Pala kurulumu — sıfır bilgili rehber (Türkçe)

Bu belge **Codex** için Pala Project Studio kurulumunu anlatır.
ChatGPT Plus düz sohbet eklentisi değildir. Ölçülmemiş hız / token yüzdesi
vaat etmez. Kanıt etiketleri yalnız:
`passed` | `not-run` | `blocked` | `configured-not-verified`.

İlk 10 dakika akışı: [VIBE_FIRST_SESSION.md](VIBE_FIRST_SESSION.md).
Kısa ZIP kapısı: kök [KUR.md](../KUR.md).

## Önce karar ağacı

1. **ChatGPT Work / Codex** veya **Codex CLI** açık mı?
   - Evet → aşağıdaki **birincil kapı** (2 CLI komutu).
   - Hayır → dur. Yanlış uygulama (Plus sohbet, Cursor “plugin kur”, vs.).
2. Codex’te **Plugins** / `/plugins` görünüyor mu?
   - Görünüyorsa yüzey doğru; kurulumdan sonra `/hooks` adımına geçeceksin.
3. İnternet / GitHub yok mu, veya tam Doctor–Repair–Update istiyor musun?
   - Evet → **Çevrimdışı / ZIP** bölümü (`Kur.cmd` veya `Install-Pala.ps1`).

## Mitler (bilerek yok)

| Mit | Gerçek |
| --- | --- |
| Codex Plugins’e ZIP yükle → Install | **Yok.** Codex’te Claude tarzı ZIP-upload UI yok. ZIP = çıkar → kaydet. |
| ChatGPT Plus’a ZIP / metin yapıştır = kurulum | **Yok.** Plus düz sohbet plugin yüzeyi değil. |
| Cursor’da “Pala Codex plugin kurulu” | **Yok.** Cursor ince rule/skill + ortak `pala.sqlite`; Codex hook parity yok. |
| Doctor `hook_safety=passed` = `/hooks` güveni bitti | **Yok.** `hook_safety` dosya kontrolü; trust Codex Work’te manuel. |
| Soft “bitti / ok / hızlı” | Kanıt sayılmaz. Etiket kullan. |
| 0.8.0 indirdim, kaynak 0.8.1 — hangisi? | GitHub’da yayımlı indirme hâlâ **0.8.0** olabilir; kaynak ağaç **0.8.1** hazırlığı. Tag/release owner işi. |

## Önkoşullar

- Windows’ta Codex CLI veya ChatGPT desktop **Codex / Work**
- Yerel checkout **veya** GitHub’dan `trugurpala/pala-project-studio` erişimi
  (birincil kapı için)
- Çevrimdışı tam toolkit için: portable ZIP + Python ≥ 3.10 (`py -3`) + Git
  (Doctor bunları raporlar)
- ExecutionPolicy Bypass korkutucu görünür; yalnız `Install-Pala.ps1` / `Kur.cmd`
  için tek seferlik çalıştırma bayrağıdır — ürün “güvenlik kapat” demek değildir

## Birincil kapı — Codex-native CLI (2 komut)

Marketplace adı ve eklenti adı: `pala-project-studio`
(`plugin@marketplace` → `pala-project-studio@pala-project-studio`).

**GitHub uzak (PATH’te `codex` varsa):**

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

**Yerel klasör (klon veya çıkarılmış ağaç kökü):**

```powershell
codex plugin marketplace add C:\path\to\pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

`<path>` = `.agents/plugins/marketplace.json` içeren repo / ZIP kökü.
İç içe yanlış klasörde çalıştırma.

## Üç GUI adımı (CLI’dan sonra zorunlu)

1. Codex Work’te Plugins / Directory yüzeyi açık (doğru app).
2. `/hooks` → Pala hook’larına **güven** (bypass yok; `codex exec` ile bitmez).
3. **Yeni sohbet** aç (eski `/hooks` thread’inde kalma). Başlık önerisi:
   **Kodlamaya başla**.

Beklenen presence (kayıtlı projede SessionStart / skill):  
`Pala burada — bu oturumda yanındayım.`  
(Token/kota büyütme iddiası yok.)

## Çevrimdışı / tam kurulum (ZIP ikincil)

ZIP, Codex Plugins’e yüklenmez. Sıra:

1. ZIP’i aç.
2. İçindeki **kök** klasörde `Kur.cmd` çift tık **veya**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

3. Kurucu desteklenen `codex plugin marketplace add` / `codex plugin add`
   akışını bağlar; kişisel marketplace JSON’unu elle bozmaz.
4. Aynı üç GUI adımı: `/hooks` → güven → yeni sohbet.

Ayrıntı: kök [KUR.md](../KUR.md).

## Doctor vs `/hooks`

| Kontrol | Anlamı |
| --- | --- |
| Doctor `plugin_ready` / `healthy` | Python, Git, Codex CLI, plugin envanteri (çekirdek) |
| Doctor `hook_safety` | `hooks.json` + `pala_hook.py` + workflow dosya sağlığı |
| Codex `/hooks` trust | İnsan tıklaması; UI adımı |
| `hooks_next_step` | Doctor’ın “şimdi `/hooks` + yeni sohbet” hatırlatması |

`hook_safety=passed` yazmak `/hooks` güvenini `passed` yapmaz → genelde
`configured-not-verified` kalır ta ki Work’te güvenirsin.

## Başarı belirtileri

- `codex plugin list` içinde `pala-project-studio@pala-project-studio` (enabled)
- Yeni sohbette presence satırı
- Doctor çekirdek `plugin_ready` / `healthy` (ZIP/Install yolunda)
- İlk iş: STATUS → PLAN aktif kart → tek task ID (uydurma ticket yok)

## Başarısızlık / sık sürtünme

| Belirti | Ne yap |
| --- | --- |
| Plus sohbette “kur” diyorsun | Work / Codex CLI’ye geç |
| ZIP’i Plugins’e sürükledin | Bırak; çıkar → CLI veya `Kur.cmd` |
| `marketplace add` yol hatası | Kök klasöre in; iç içe `pala-project-studio\pala-project-studio` değil |
| `codex` bulunamadı | PATH veya Install-Pala (Windows konum taraması) |
| Defender / Bypass uyarısı | Beklenen sürtünme; Bypass yalnız o script çalıştırma |
| Eski sohbette hook yok | **Yeni sohbet** |
| Doctor yeşil, presence yok | `/hooks` trust eksik olabilir |
| 0.8.0 vs 0.8.1 karışıklığı | İndirme linki hâlâ 0.8.0 ise o asset’i kullan; kaynak 0.8.1 = henüz tag yoksa `not-run` |

## Güncelleme fiilleri

- Codex: `codex plugin marketplace` / plugin upgrade akışları (host CLI)
- Pala toolkit: `Install-Pala.ps1 -Mode Update` (ZIP/source kökünden)
- İkisi aynı cümle değil; vibe ilk kurulumda **add** yeter

## Dağıtım sınırı

- ChatGPT Plus paste kurulum yok
- Codex native ZIP-upload UI yok
- `--dangerously-bypass-hook-trust` ürün varsayılanı değil
- Commit / push / release / deploy ayrı yetki

See also: [PALA_EVERYWHERE.md](PALA_EVERYWHERE.md),
[CODEX_SCOPE_AND_LIMITS.md](CODEX_SCOPE_AND_LIMITS.md),
[RELEASE_0.8.1_CHECKLIST.md](RELEASE_0.8.1_CHECKLIST.md).
