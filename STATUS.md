# Pala Project Studio Durumu

- Aktif milestone: M7 — Owner demo ve 0.3.1 dağıtımı (`completed`)
- Aktif ticket: Yok
- Son tamamlanan sonuç: Pala `0.3.1+codex.20260805142013`, secretsız owner-demo handoff'u ve isteğe bağlı local-first Code Review Graph adaptörüyle temiz dağıtım kaynağından kişisel marketplace'e kuruldu. CRG, Codex/MCP ayarını veya graph build'ini varsayılan olarak değiştirmez.
- Çalışma ağacı: `main`; uygulama commit'i `7215de4` private `trugurpala/pala-project-studio` deposuna gönderildi. Etkin dağıtım kaynağı ve Codex cache'i 34/34 dosyada SHA-256 eşleşiyor; güncel skill yeni görevde yüklenir.
- Doğrulama: `py -3 scripts/verify.py` — 50 test passed; skill/plugin doğrulayıcıları geçti; portable SHA-256 `178F0B5BD1A0BC772C51BD24A6F8F0BC46E63585169D3B83CFF2CF17B7D7D110`; kurulum/cache 34/34 hash eşleşti; GitHub Actions `31014818100` başarılı. `code-review-graph` 2.3.7 izole kuruldu, 77 paket uyumlu; gerçek Windows build 11 kaynak/126 düğüm/1.653 ilişki üretti ve UTF-8 brief review çalıştı. Graph'ın test-gap yanlış pozitifleri kaynak ve 50 testle karşılaştırıldı; tasarruf yüzdesi ürün vaadi olarak kullanılmadı.
- Engel: Yok.
- Tek sonraki iş: Yeni Codex görevinde Pala 0.3.1'i yükleyip AZR'nin aktif F2 worktree'ine çakışmadan devam et.
- Güncelleme: 2026-08-05
