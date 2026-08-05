# Pala Project Studio çalışma kuralları

## Amaç

- Codex için küçük, güvenli ve token-verimli bir proje yürütme eklentisi geliştir.
- Eklenti bağlam penceresini veya kullanım kotasını artırdığını iddia etmez; yalnız gerekli bağlamı seçerek israfı azaltır.
- AZR Reklam gibi uzun soluklu projelerde plan, durum, karar, doğrulama ve tek sonraki işi oturumlar arasında sürdürülebilir tut.

## Kaynak gerçek ve kapsam

1. Kullanıcının güncel açık talimatı.
2. `PROJECT.md` ve `DECISIONS.md`.
3. `PLAN.md` ve `STATUS.md`.
4. Skill ve referans belgeleri.

- Kalıcı kuralları `AGENTS.md`, değişen işi `PLAN.md` ve `STATUS.md` içinde tut.
- Skill gövdesini kısa tut; ayrıntıyı doğrudan bağlı referanslara ve deterministik scriptlere taşı.
- Pala hiçbir hook içinde test, build, commit, push veya ağ çağrısını kendiliğinden başlatmaz.
- Ölçülmemiş hız, token veya kalite yüzdesi raporlama.

## Kalite ve güvenlik

- Yeni davranışta önce sözleşme testi yaz ve doğru nedenle kırmızı sonucu gör.
- Geliştirme döngüsünde dar testi; ticket sonunda ilgili kapıyı; milestone/release sonunda tam kapıyı çalıştır.
- Bir kapı çalıştırılmadıysa `passed` yazma.
- Secret, token, transcript, gerçek proje verisi veya kişisel plugin verisini kaynak pakete, Git'e ya da hook çıktısına yazma.
- Commit, push, PR, release, görünürlük değişimi ve deploy ayrı yetkilerdir.

## Doğrulama komutları

- Dar test: `py -3 -m unittest scripts.test_pala_tools scripts.test_plugin_experience -v`
- Tam yerel kapı: `py -3 scripts/verify.py`
- Skill doğrulama: sistem `skill-creator/scripts/quick_validate.py`
- Plugin doğrulama: sistem `plugin-creator/scripts/validate_plugin.py`

Her tamamlanan ticket sonrasında `STATUS.md`, `PLAN.md` ve Pala checkpoint kaydını gerçek kanıtla güncelle.
