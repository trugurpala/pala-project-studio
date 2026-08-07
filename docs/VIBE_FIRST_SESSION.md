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

Doctor'da çekirdek `plugin_ready` / `healthy` beklenir. Hook güveni atlanmaz.

3. Codex'te `/hooks` ile Pala hook'larını güven; **yeni sohbet** aç.
4. Proje klasöründe yazılım işi söyle (ör. “bu projeyi sürdür”) veya skill
   `pala-project-finisher` çağır.
5. Beklenen: Status HTML / rapor yüzeyi; sonra discover → aktif ticket;
   checkpoint. Hook kendi başına test/build/ağ çalıştırmaz.
6. İsteğe bağlı dışarıdan:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
py -3 scripts\pala_state.py memory --cwd .
```

Yerel store: `%USERPROFILE%\Desktop\Codex\pala.sqlite`.

## Bilerek yok

- ChatGPT Plus sohbete ZIP yapıştırarak kurulum
- Ölçülmemiş “daha hızlı / daha az token” yüzdesi
- Hook içinden commit, push, release veya deploy

Dağıtım sınırları: [PALA_EVERYWHERE.md](PALA_EVERYWHERE.md).
