# Pala Project Studio Durumu

- Aktif milestone: M8 — Checkpoint commit öz-referansı ve 0.3.2 (`in_progress`)
- Aktif ticket: PALA-033 — 0.3.2 doğrulama ve dağıtım
- Son tamamlanan sonuç: Gerçek AZR checkpoint commit'iyle yeniden üretilen yanlış stale uyarısı test-first düzeltildi. Pala yalnız checkpoint'teki yol/içerik snapshot'ını eksiksiz taşıyan descendant commit'i aynı sonuç kabul eder; sonraki veya farklı commit uzlaştırma ister.
- Çalışma ağacı: `main`; 0.3.2 değişiklikleri henüz commit/push edilmedi. Kurulu güvenli fallback sürümü `0.3.1+codex.20260805142013`.
- Doğrulama: Yeni kırmızı sözleşme doğru nedenle kırıldı; üç hedefli checkpoint testi geçti. Tam plugin/portable/kurulum/GitHub kapıları henüz çalıştırılmadı.
- Engel: Yok.
- Tek sonraki iş: 0.3.2 tam doğrulama, paketleme, kurulum ve private CI kanıtını tamamla.
- Güncelleme: 2026-08-05
