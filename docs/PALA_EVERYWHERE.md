# Pala — Her yerde çalışır hale (standart + üstü)

Bu belge “ChatGPT Plus sohbete ZIP yapıştır” fantezisini değil, gerçek
dağıtım sözleşmesini tanımlar.

## Standart (Codex)

Resmi sıra ([Codex Plugins](https://developers.openai.com/codex/plugins)):

1. Codex CLI veya ChatGPT desktop **Codex / Work** yüzeyi
2. Marketplace kaydı
3. Plugin kurulumu
4. `/hooks` güveni (manuel; bypass yok)
5. **Yeni sohbet**

### Kapı A — Windows tek komut (önerilen)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Kurucu Codex’i PATH’te bulamazsa bilinen Windows konumlarını da tarar
(`%LOCALAPPDATA%\OpenAI\Codex\bin\...\codex.exe`, `%APPDATA%\npm\codex.cmd`).

Doctor ayrımı:

- `plugin_ready` / `healthy` — çekirdek (Python≥3.10, Git, Codex CLI, plugin)
- `experts_ready` — isteğe bağlı (Node, uv, uzman işçiler)
- `hooks_next_step` — `/hooks` + yeni sohbet hatırlatması

### Kapı B — Saf Codex CLI (git URL)

Python kurucu olmadan (Codex CLI PATH’teyse):

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

Sonra: yeni sohbet → `/hooks` → skill `pala-project-finisher`.

Yerel checkout:

```powershell
codex plugin marketplace add C:\path\to\pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

## Standart+ (üstüne çıkış — Pala 0.7.1)

Üst standart = aynı skill gövdesini bozmadan **daha az sürtünme**:

1. Windows Codex PATH keşfi (bu sürüm)
2. Core/experts sağlıklı ayrımı (bu sürüm)
3. Yerel SQLite store + durum paneli (0.7)
4. Git URL marketplace kapısı (dokümante)
5. İleride (ayrı ticket): Agent Skills taşınabilir çekirdek → Claude/Cursor
   skill kopyası — **aynı UX iddiası yok**

## Multi-host gerçeklik

| Yüzey | Durum |
| --- | --- |
| Codex CLI / desktop Codex | Birinci sınıf |
| ChatGPT Work + Plugins Directory | Aynı katalog ailesi; GUI ayrı |
| ChatGPT Plus düz sohbet | **Desteklenmez** — plugin yüzeyi değil |
| Claude Code / Cursor skills | Taşınabilir `SKILL.md` çekirdeği mümkün; hook/marketplace ayrı |
| IDE extension / mobile | Hedef değil |

Kaynak standart: [agentskills.io](https://agentskills.io) — portable olan skill
klasörü; host plugin/hook değil.

## Bilerek yok

- ChatGPT Plus chat paste ile kurulum
- `--dangerously-bypass-hook-trust` ürün varsayılanı
- Ölçülmemiş “%X her yerde hız”
- İkinci bir sync SaaS / bulut marketplace ürünü

See also: `docs/CODEX_SCOPE_AND_LIMITS.md`, ADR-006/007/015.
