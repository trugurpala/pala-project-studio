# Pala — Her yerde çalışır hale (standart + üstü)

Bu belge “ChatGPT Plus sohbete ZIP yapıştır” fantezisini değil, gerçek
dağıtım sözleşmesini tanımlar. Codex’te **native ZIP-upload / Plugins’e ZIP
yükle** UI **yok**; ZIP yalnız çıkar → kaydet paketidir.

Sıfır-bilgi kurulum: [VIBE_INSTALL.md](VIBE_INSTALL.md).
İlk 10 dakika: [VIBE_FIRST_SESSION.md](VIBE_FIRST_SESSION.md).

## Standart (Codex)

Resmi sıra ([Codex Plugins](https://developers.openai.com/codex/plugins)):

1. Codex CLI veya ChatGPT desktop **Codex / Work** yüzeyi
2. Marketplace kaydı
3. Plugin kurulumu
4. `/hooks` güveni (manuel; bypass yok)
5. **Yeni sohbet**

### Kapı A — Saf Codex CLI (birincil)

Python kurucu olmadan (Codex CLI PATH’teyse). Kimlik:
`pala-project-studio@pala-project-studio`.

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

Yerel checkout:

```powershell
codex plugin marketplace add C:\path\to\pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

Sonra: `/hooks` → güven → yeni sohbet → skill `pala-project-finisher`.

### Kapı B — Windows ZIP / Install-Pala (ikincil, çevrimdışı / tam toolkit)

Portable ZIP’i çıkar; kökte `Kur.cmd` veya:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Kurucu Codex’i PATH’te bulamazsa bilinen Windows konumlarını da tarar
(`%LOCALAPPDATA%\OpenAI\Codex\bin\...\codex.exe`, `%APPDATA%\npm\codex.cmd`).
Arka planda yine desteklenen `codex plugin marketplace add` /
`codex plugin add` kullanılır.

Doctor ayrımı:

- `plugin_ready` / `healthy` — çekirdek (Python≥3.10, Git, Codex CLI, plugin)
- `experts_ready` — isteğe bağlı (Node, uv, uzman işçiler)
- `hook_safety` — dosya kontrolü; **≠** Codex `/hooks` UI trust
- `hooks_next_step` — `/hooks` + yeni sohbet hatırlatması

Kısa ZIP notu: [KUR.md](../KUR.md).

## Standart+ (üstüne çıkış — Pala 0.7.1+)

Üst standart = aynı skill gövdesini bozmadan **daha az sürtünme**:

1. Windows Codex PATH keşfi
2. Core/experts sağlıklı ayrımı
3. Yerel SQLite store + durum paneli (0.7)
4. Git URL marketplace kapısı (birincil dokümante kapı)
5. İleride (ayrı ticket): Agent Skills taşınabilir çekirdek → Claude/Cursor
   skill kopyası — **aynı UX iddiası yok**
6. **M25 / Wave E:** `portable/cursor/SKILL.md` + `.cursor/rules/pala-memory.mdc`
   + `pala_shared_memory.py` — aynı `pala.sqlite`, Codex hook parity yok
   (ADR-017). Hit/miss + Doctor `shared_store`: `docs/PALA_SHARED_MEMORY.md`.

## Multi-host gerçeklik

| Yüzey | Durum |
| --- | --- |
| Codex CLI / desktop Codex | Birinci sınıf |
| ChatGPT Work + Plugins Directory | Aynı katalog ailesi; GUI ayrı; native ZIP UI yok |
| ChatGPT Plus düz sohbet | **Desteklenmez** — plugin yüzeyi değil |
| Cursor (bu checkout) | İnce rule + portable skill; ortak sqlite; hook yok |
| Claude Code / diğer agentskills | `portable/cursor/SKILL.md` kopyalanabilir |
| IDE extension / mobile | Hedef değil |

Kaynak standart: [agentskills.io](https://agentskills.io) — portable olan skill
klasörü; host plugin/hook değil.

## Bilerek yok

- ChatGPT Plus chat paste ile kurulum
- Codex Plugins’e ZIP yükleme (native UI yok)
- `--dangerously-bypass-hook-trust` ürün varsayılanı
- Ölçülmemiş “%X her yerde hız”
- İkinci bir sync SaaS / bulut marketplace ürünü
- Doctor `hook_safety=passed` = `/hooks` bitti iddiası

See also: `docs/CODEX_SCOPE_AND_LIMITS.md`, ADR-006/007/015.
