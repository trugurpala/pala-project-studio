---
name: pala-control-center
description: >-
  Pala Control Center durum panelini aç. "paneli aç", "paneli ac", "Pala paneli",
  "Pala durumunu göster", "Pala Control Center" veya "neredeyiz" niyetlerinde
  kullan. İlgisiz panel isteklerinde kullanma: "tarayıcı panelini aç",
  "uygulamanın admin panelini aç" ve "browser panel" Pala tarafından
  yakalanmamalıdır.
---

# Pala Control Center

Host'un bu beceri için okuduğu `SKILL.md` yolundan `..\..\scripts\pala_report.py` dosyasını resolve et; dosya araması yapma. Kullanıcının tam niyetiyle `py -3 "<resolved pala_report.py>" --open --intent "<exact user intent>"` çalıştır.

Bu işlem read-only olmalı: raporu yenile, Control Center'ı exactly once aç ve canonical truth'u değiştirme. Proje sözleşmesi isteme. Helper veya provider UI açma. Başka panel niyetlerini Pala'ya yönlendirme.
