# Pala kurulumu — sıfır bilgili rehber (Türkçe)

Bu belge **Codex** için Pala Project Studio kurulumunu anlatır.
ChatGPT Plus düz sohbet eklentisi değildir. Ölçülmemiş hız / token yüzdesi
vaat etmez. Kanıt etiketleri yalnız:
`passed` | `not-run` | `blocked` | `configured-not-verified`.

İlk 10 dakika akışı: [VIBE_FIRST_SESSION.md](VIBE_FIRST_SESSION.md).
Kısa ZIP kapısı: kök [KUR.md](../KUR.md).

## Tek normal kurulum cümlesi

Codex'e şunu yazın:

```text
https://github.com/trugurpala/pala-project-studio eklentisini kur ve güncel olduğunu doğrula.
```

Pala'nın beklenen davranışı:

`marketplace exists → Git snapshot refresh/upgrade → plugin install/reinstall → version verify → Doctor → new Codex conversation`

Kullanıcının marketplace root, plugin cache veya manifest ayrıntılarını bilmesi
gerekmez. `marketplace add` başarılı dönse bile mevcut Git snapshot stale
olabilir; bu tek başına kurulum kanıtı değildir.

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
| Kaynak, bundle ve Codex sürümleri farklı görünüyor | `+codex.*` build metadata'sını ayırıp temel sürümü karşılaştırın; Doctor source, expected, bundle, plugin ve marketplace snapshot kimliklerini birlikte raporlar. |

## Önkoşullar

- Windows’ta Codex CLI veya ChatGPT desktop **Codex / Work**
- Yerel checkout **veya** GitHub’dan `trugurpala/pala-project-studio` erişimi
  (birincil kapı için)
- Çevrimdışı tam toolkit için: portable ZIP + Python ≥ 3.10 (`py -3`) + Git
  (Doctor bunları raporlar)
- ExecutionPolicy Bypass korkutucu görünür; yalnız `Install-Pala.ps1` / `Kur.cmd`
  için tek seferlik çalıştırma bayrağıdır — ürün “güvenlik kapat” demek değildir

## İleri kapı — Codex-native CLI

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

3. Kurucu Codex yardımını okur; mevcut Git marketplace'ini gerektiğinde yeniler,
   plugin'i yeniden kurar ve sürümü doğrular. Kişisel marketplace JSON'unu elle
   bozmaz.
4. Aynı üç GUI adımı: `/hooks` → güven → yeni sohbet.

Ayrıntı: kök [KUR.md](../KUR.md).

## Doctor vs `/hooks`

| Kontrol | Anlamı |
| --- | --- |
| Doctor `plugin_ready` / `healthy` | Python, Git, Codex CLI, plugin envanteri ve marketplace/cache durumunun çekirdek sonucu |
| Doctor `version_ready` | Source/bundle/Codex plugin temel sürümleri beklenen sürümle eşleşir ve Codex sağlıklıdır |
| Doctor `marketplace_refresh_status` | Git snapshot yenilemesi: `not-needed`, `required`, `blocked` veya `not-applicable` |
| Doctor `plugin=drifted` | source≠install fingerprint; **healthy sayma** → Repair/Update/marketplace sync |
| Doctor `hook_safety` | `hooks.json` + `pala_hook.py` + workflow dosya sağlığı |
| Codex `/hooks` trust | İnsan tıklaması; UI adımı |
| `hooks_next_step` | Doctor’ın “şimdi `/hooks` + yeni sohbet” hatırlatması |
| `plugin_next_step` | Doctor’ın drifted onarım satırı (source≠install) |

`hook_safety=passed` yazmak `/hooks` güvenini `passed` yapmaz → genelde
`configured-not-verified` kalır ta ki Work’te güvenirsin.

## Başarı belirtileri

- `codex plugin list` içinde `pala-project-studio@pala-project-studio` (enabled)
- **Kayıtlı** projede yeni sohbette presence satırı
- Doctor çekirdek `plugin_ready` / `healthy` (ZIP/Install yolunda; drifted değil)
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
| Doctor yeşil, presence yok | Önce cwd **kayıtlı mı** bak; kayıtlıysa `/hooks` trust |
| Plugin kurulu, SessionStart boş | Kayıtsız klasör — bozuk değil; Pala register et |
| `plugin=drifted` / `healthy=False` | `Install-Pala -Mode Repair` veya Update / marketplace sync |
| Sürüm veya cache karışıklığı | `Install-Pala.ps1 -Mode Doctor` çalıştırın; `marketplace add` tek başına güncellik kanıtı değildir. |

## Güncelleme fiilleri

- Codex: `codex plugin marketplace` / plugin upgrade akışları (host CLI)
- Pala toolkit: `Install-Pala.ps1 -Mode Update` (ZIP/source kökünden)
- Normal kurulum cümlesi: “Pala'yı kur ve güncel olduğunu doğrula.” `add`,
  refresh, reinstall ve Doctor adımları bu isteğin parçasıdır.

## Dağıtım sınırı

- ChatGPT Plus paste kurulum yok
- Codex native ZIP-upload UI yok
- `--dangerously-bypass-hook-trust` ürün varsayılanı değil
- Commit / push / release / deploy ayrı yetki

See also: [PALA_EVERYWHERE.md](PALA_EVERYWHERE.md),
[CODEX_SCOPE_AND_LIMITS.md](CODEX_SCOPE_AND_LIMITS.md),
[RELEASE_1.1.1.md](RELEASE_1.1.1.md). The published `1.1.0` notes remain
[historical release notes](RELEASE_1.1.0.md).
