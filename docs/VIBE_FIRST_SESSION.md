# Vibe coder — ilk 10 dakika

Tek cümle: Codex'i aç; Pala kuruluysa yeni sohbette yazılım işi söyle.
ChatGPT Plus düz sohbet değil.

## Sıra

1. Codex CLI veya ChatGPT desktop **Codex / Work** yüzeyini aç.
2. Repo veya portable ZIP kökünde kur ve doğrula:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Doctor'da çekirdek `plugin_ready` / `healthy` beklenir.

**Doctor `hook_safety=passed` ≠ Codex `/hooks` trust.**  
`hook_safety` yalnız dosya kontrolüdür (`hooks.json` + `pala_hook.py` + workflow).
Kullanıcı trust Codex Work'te interaktiftir; `codex exec` ile tamamlanmaz.

3. Codex Work'te `/hooks` ile Pala hook'larını **güven**; **yeni sohbet** aç
   (başlık önerisi: **Kodlamaya başla**). Eski `/hooks`'ta takılı thread'i zorlama.
4. İlk mesaj (yapıştır):

```
Bu projeyi sürdür. Önce mevcut durumu oku, aktif işi bul, yetkilendirilmiş yerel uygulamaya kaldığı yerden devam et.

Kapsam: read-first. Commit/push/release yapma. Hook içinde test/build başlatma.
STATUS.md ve docs/VIBE_FIRST_SESSION.md ile uyumlu ilerle; tek sonraki işi söyle.
```

5. Beklenen ilk sonuç:
   - SessionStart veya skill açılışı: **Pala burada — bu oturumda yanındayım.**
     (güven satırı; token/kota büyütme iddiası yok)
   - SessionStart metni Codex `additionalContext` token tavanının altında kalır
     (Pala çift bütçe: char + approx-token). Uzun sağlık düzyazısı cold packet’in
     önüne geçmez; middle-truncate olsa bile presence satırı korunacak şekilde
     tasarlanır.
   - STATUS/PROGRESS/workflow okunur
   - Aktif ticket yoksa açıkça söylenir (uydurma ticket yok)
   - Commit/push/verify otomatik başlamaz

**Çoklu ajan / görev:** İşe başlamadan önce `STATUS.md` → `PLAN.md` içindeki
aktif `M*-T*` veya `DEMO-*` kartları → `DEBUGGING.md` sırasıyla oku; **tek bir
task ID** seç ve o kartın dosyalarında kal. Kanıt yalnız
`passed` | `not-run` | `blocked` | `configured-not-verified`. Hook'lar test,
build veya ağ çağrısını kendiliğinden başlatmaz.

6. İsteğe bağlı dışarıdan:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
py -3 scripts\pala_state.py memory --cwd .
py -3 scripts\pala_demo.py seed --demo-root examples\demo-software-project
py -3 scripts\pala_self_audit.py
```

Yerel store: `%USERPROFILE%\Desktop\Codex\pala.sqlite`.
Fork paketi: [FORK_PACK.md](FORK_PACK.md).

## Bilerek yok

- ChatGPT Plus sohbete ZIP yapıştırarak kurulum
- Ölçülmemiş “daha hızlı / daha az token” yüzdesi
- Hook içinden commit, push, release veya deploy
- Doctor yeşil = tam yetki iddiası

Dağıtım sınırları: [PALA_EVERYWHERE.md](PALA_EVERYWHERE.md).
Release (owner): [RELEASE_0.8.1_CHECKLIST.md](RELEASE_0.8.1_CHECKLIST.md).
