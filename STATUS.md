# Pala Project Studio Durumu

- Güncelleme: 2026-08-06
- Aktif milestone: M19 — Pala 0.5A Truth Core (`completed; integration pending`).
- Aktif ticket: PALA-053 — uygulama ve bağımsız inceleme tamamlandı; entegrasyon bekliyor.
- Son tamamlanan sonuç: Pala Project Studio `v0.4.4`, GitHub'da `Latest`
  release olarak yayınlandı ve yerel kurulum `0.4.4+codex.20260806055124`
  sürümüne güncellendi.
- Çalışma ağacı: `codex/pala-0.5a-truth-core` bağlı worktree'sinde snapshot,
  worktree identity, migration, checkpoint, typed reconciliation, session
  isolation ve ayrık doctor katmanları uygulanıyor. Routing, installer/Core
  ayrımı ve benchmark koduna dokunulmadı.
- Doğrulama kanıtı:
  - `v0.4.4` release ve `pala-project-studio-0.4.4.zip` asset'i mevcut.
  - Release ZIP SHA-256:
    `F092D2066CE15BC6900C40B09B8AEDDB2939AB779C7178C9DED61092CD254B4F`.
  - Gerçek ZIP üzerinden `Update` idempotent tamamlandı; `Doctor` çekirdek,
    Codex, hook ve uzman işçileri `healthy/ready` raporladı.
  - Son `main` kalite kapısı: GitHub Actions `31076145048`, Windows ve Ubuntu
    `success`; yerel 154 test geçti.
  - Shields.io'nun private repo için anonim dinamik sorgusu yanlış kırmızı
    sonuç üretiyordu; yeni statik `v0.4.4` rozeti HTTP 200 ile doğru metni
    render ediyor.
- Yeni tasarım kanıtı: kaynak commit `58c12a4` üzerinde üç bağımsız salt-okunur
  denetim; gerçek Codex CLI/MCP şema kontrolü; Pala ve anonimleştirilecek linked
  worktree durum yeniden üretimleri; 36 kanıtlı öneri ve dört sürüm dilimi.
- Tasarım kalite kapısı: `py -3 scripts/verify.py`; 154/154 test geçti,
  portable paket iki üretimde aynı
  `BA12F013F66E0DBE9876E39CABA19F31276A52306354CDB2FA8ED64D149CAA27`
  SHA-256 değerini verdi ve komut `exit 0` ile tamamlandı.
- Taze uygulama kanıtı: Üç bağımsız inceleme turundaki tüm önemli bulgular
  test-first kapatıldı. Tam `py -3 scripts/verify.py` milestone kapısı 189/189
  geçti; iki portable üretim aynı
  `809435D7FC11BF7FEE54F5472B931F8BE428E225867C219B8C03B4411A6E1829`
  SHA-256 değerini verdi ve komut `exit 0` ile tamamlandı.
- Engel: Yok.
- Tek sonraki iş: 0.5A için commit/entegrasyon yetkisini üreticiden al.
  0.5B planı ayrı onaydan önce başlamaz.
