# Kur (ZIP klasörü)

Bu klasörü ZIP’ten açtıysan: Codex Plugins’e ZIP yükleme. Sıra:

1. Bu kökte `Kur.cmd` çift tık  
   **veya**  
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1`
2. Codex Work → `/hooks` → Pala’ya **güven**
3. **Yeni sohbet** aç → yazılım işini söyle

Birincil (ZIP'siz) kapı — Codex doğal dil kurulumu:

```text
https://github.com/trugurpala/pala-project-studio eklentisini kur ve güncel olduğunu doğrula.
```

Pala mevcut marketplace'i yeniler, plugin'i gerektiğinde yeniden kurar ve
Doctor ile sürümü doğrular. İleri CLI yalnız kurulu Codex yardımında destek
olduğu doğrulandıktan sonra kullanılır:

```powershell
codex plugin marketplace add C:\path\to\pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

(GitHub uzak: `codex plugin marketplace add trugurpala/pala-project-studio` sonra aynı `plugin add`.)

Tam rehber: [docs/VIBE_INSTALL.md](docs/VIBE_INSTALL.md) · İlk 10 dk: [docs/VIBE_FIRST_SESSION.md](docs/VIBE_FIRST_SESSION.md).
