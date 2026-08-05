# Pala Project Studio Durumu

- Aktif milestone: M9 — 0.4 ürün sözleşmesi ve araç seçimi (`completed`)
- Aktif ticket: PALA-040 — Tek-kapı, idempotent Windows kurulum ve büyük-iş
  dayanıklılık sözleşmesi tamamlandı.
- Son tamamlanan sonuç: 0.3.3 kaynak ve private GitHub release'i `742fb86`
  üzerinde doğrulandı. Yerel `python scripts/verify.py` 54 testi ve tekrarlanabilir
  portable SHA-256 kapısını geçti.
- Gerçek kurulum farkı: Kaynak/release `0.3.3` olmasına rağmen Codex'te etkin
  kişisel Pala hâlâ `0.3.2+codex.20260805142731`. Bu, oturum güncelleme
  kontrolünün 0.3.3'te bulunmadığını kanıtlıyor.
- Makine: Windows 11 Pro 64-bit; Ryzen 5 5500 (6C/12T), 15.9 GB RAM ve C:
  üzerinde yaklaşık 111 GB boş alan. Codex, Git, GitHub CLI, Python 3.12,
  `uv`, Node 24, npm, pnpm, ripgrep ve PowerShell 7 hazır.
- Araç durumu: `code-review-graph` 2.3.7 `uv` altında ve bu repo için yerel
  graph mevcut; doğrudan PowerShell keşfi ile Pala adaptörü arasında PATH farkı
  var. RTK kurulu değil. Context7 ve Playwright MCP kayıtları etkin, ancak
  sürüm/sahiplikleri Pala tarafından yönetilmiyor.
- Doğrulama: `python scripts/verify.py` — 54 test passed;
  `reproducible_zip_sha256=625350E412F16ECC48296115CE7B83B5C1894A12C34B6B9B67CDDC62233E4383`.
  GitHub Actions `31021033644` Windows ve Ubuntu için başarılı.
- PALA-040 kanıtı: `python -m unittest` ile tek-kapı ve çakışan orkestratör
  kararlarını koruyan 2 yeni sözleşme testi geçti; `git diff --check` temiz.
- Engel: Yok.
- Tek sonraki iş: PALA-041 idempotent tek komut Windows kurucu çekirdeğini
  test-first uygula.
- Güncelleme: 2026-08-05
