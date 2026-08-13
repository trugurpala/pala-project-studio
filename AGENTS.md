# Pala Project Studio çalışma kuralları

## Amaç

- PALA `1.1.0-local-rc` Provider-Independent Local Software Delivery OS'u
  güvenli, yerel ve kanıta bağlı olarak tamamla.
- Yeni üründe niyeti kalıcı ProductSpec ve canonical task akışına; mevcut
  projede canonical context/task akışına bağla.
- Eklenti bağlam penceresini veya kullanım kotasını artırdığını iddia etmez; yalnız gerekli bağlamı seçerek israfı azaltır.
- Büyük ve uzun soluklu projelerde plan, durum, karar, doğrulama ve tek sonraki
  işi oturumlar arasında sürdürülebilir tut.

## Kaynak gerçek ve kapsam

1. Kullanıcının güncel açık talimatı.
2. `product-identity.json`, `PROJECT.md` ve `DECISIONS.md`.
3. TaskContract → WorkflowStore → Pala Quality Engine canonical runtime.
4. Generated STATUS/cockpit/handoff, plan/progress/tooling/debugging ve git.
5. Skill ve referans belgeleri.

- Kalıcı kuralları `AGENTS.md`, değişen işi canonical runtime ve ExecPlan
  içinde tut. STATUS/cockpit/handoff yalnız generated read modeldir; elle ikinci
  authority oluşturma.
- Bilinen hatayı tekrarlamadan önce `DEBUGGING.md` oku; yeni arızada kök neden,
  belirtiler, fix criteria, kanıt komutları ve ilgili dosyaları `### INC-…`
  formatında kaydet (sır/token/transcript yok).
- Skill gövdesini kısa tut; ayrıntıyı doğrudan bağlı referanslara ve deterministik scriptlere taşı.
- Pala hiçbir hook içinde test, build, commit, push veya ağ çağrısını kendiliğinden başlatmaz.
- Ölçülmemiş hız, token veya kalite yüzdesi raporlama.
- Soft “bitti/done/ok” kanıt sayılmaz; `name=passed|not-run|blocked|configured-not-verified` kullan.

## Multi-host hafıza (ADR-017)

- Bu `AGENTS.md` kalıcı kurallar için **tek kaynak** (single source).
- Cursor `.cursor/rules/pala-memory.mdc` ve `portable/cursor/SKILL.md` yalnız ince
  hatırlatıcıdır; kuralları burada çoğaltma.
- Codex + Cursor + CLI aynı makine-yerel `pala.sqlite` (hit); bilinmeyen host = miss
  (ikinci store yok). Ayrıntı: `docs/PALA_SHARED_MEMORY.md`.
- Cursor’da Codex hook / “Pala Cursor plugin kurulu” iddiası yok.

## Kalite ve güvenlik

- Canonical completion zinciri: **TaskContract** task semantics ve `DONE`
  eligibility sahibidir; **WorkflowStore** persistence/lease sahibidir; mevcut
  **Pala Quality Engine** tek verification/evidence authority'dir. Explicit
  `acceptance` maddeleri current Quality check ID'leri ve exit code `0` kanıtı
  olmadan `DONE` olamaz.
- Canonical uygulama sırası: `pala_report.py` / context → tek task card →
  `pala_state.py begin --ticket` claim → Quality mapping → `acceptance` →
  `DONE`.
- Handoff, cold packet, STATUS ve diğer `generated` projection'lar read modeldir;
  canonical authority değildir ve completion kararı üretemez.
- Yeni davranışta önce sözleşme testi yaz ve doğru nedenle kırmızı sonucu gör.
- Geliştirme döngüsünde dar testi; ticket sonunda ilgili kapıyı; milestone/release sonunda tam kapıyı çalıştır.
- Bir kapı çalıştırılmadıysa `passed` yazma.
- Secret, token, transcript, gerçek proje verisi veya kullanıcıya ait plugin
  verisini kaynak pakete, Git'e ya da hook çıktısına yazma.
- Commit, push, PR, release, görünürlük değişimi ve deploy ayrı yetkilerdir.

## Çoklu ajan / görev kartı

- Uygulama öncesi: `STATUS.md` → aktif `PLAN.md` görev kartları (`M*-T*` / ticket ID) → `DEBUGGING.md`.
- Tam olarak bir görev ID'si seç; `Sahip ajan` ve `Dosyalar` sahipliğine uy.
- Kanıt etiketleri: `passed|not-run|blocked|configured-not-verified`.
- Kapalı veya kanıtlı kartları yeniden planlama; yalnız seçilen ID'yi uygula.
- Hook'lar test, build veya ağ çağrısını kendiliğinden başlatmaz.

## Doğrulama komutları

- Dar test: `py -3 -m unittest scripts.test_pala_tools scripts.test_plugin_experience -v`
- Tam yerel kapı: `py -3 scripts/verify.py`
- Skill doğrulama: sistem `skill-creator/scripts/quick_validate.py`
- Plugin doğrulama: sistem `plugin-creator/scripts/validate_plugin.py`

Her tamamlanan ticket sonrasında canonical checkpoint ve ilgili ExecPlan'i
gerçek kanıtla güncelle; STATUS/cockpit projection'ını canonical kayıttan yeniden üret.
