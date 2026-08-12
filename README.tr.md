# Pala Project Studio

Pala, yapay zeka destekli yazilim projelerini planlayan, koordine eden,
dogrulayan ve paketleyen **Provider-Independent Local Software Delivery OS**
uygulamasidir.

Surum: **1.0.0**
Tasima paketi: `pala-project-studio-1.0.0.zip`

## Pala nedir?

Pala kullanici fikrini ProductSpec'e, sinirli gorevlere ve gercek dogrulama
kanitlarina baglar. Proje durumu, gorev sahipligi, kalite kaniti, bilinen hata
cozumleri ve yayin kimligi yerel ve incelenebilir kalir.

## Nasil kurulur?

Codex icin once GitHub marketplace'ini ekleyip eklentiyi kurun:

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

Tasima ZIP'ini cikartip tam yerel arac setini kullanmak icin:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
```

Kurulumdan sonra `/hooks` guven ayarini inceleyin ve yeni bir Codex sohbeti
acip Pala'ya projenizi anlatin.

## Ilk proje nasil baslatilir?

"Bir su takip uygulamasi yapmak istiyorum" veya "Bu projeyi kaldigi yerden
devam ettir" demeniz yeterlidir. Pala mevcut talimatlari okur, tek canonical
gorevi secer, gerekli kalite kapilarini calistirir ve sonucu kanitla kapatir.

## Pala neyi kendi yapar?

- ProductSpec ve bounded task plani hazirlar.
- AI worker'lara sinirli yerel is verir.
- Test, build ve kalite kanitlarini kaydeder.
- Dogrulanmis hata cozumlerini gizli veri saklamadan yeniden kullanir.
- Surum tutarliligini, secret taramasini ve reproducible paketi kontrol eder.

## Ne zaman kullaniciya sorar?

Commit, push, PR, merge, tag, GitHub Release, repository visibility, billing,
koruma kurallari ve hosting/deploy dis aksiyonlardir. Pala bunlari kendiliginden
yapmaz; acik owner yetkisi olmadan uzaktaki durumu degistirmez.

## GitHub yayininda ne olur?

Kalite -> repository hygiene -> secret taramasi -> surum tutarliligi ->
dokumantasyon -> yayin on kontrolu -> maliyet/risk -> owner yetkisi -> yayin ->
remote read-back zinciri izlenir. Son adimda GitHub'daki tag, Release, asset,
README ve ana dal gercekten okunup ReleaseTruth ile karsilastirilir.

## Hata tekrar ederse Pala ne yapar?

Pala hatayi normalize eder, hassas degerleri redakte eder, Failure Intelligence
icinden uyumlu ve VERIFIED bir cozum arar. Tekrarlanan basarisiz tarifleri
sonsuzca denemez. Uretim deploy'u Pala 1.0 GitHub yayin kanitinin parcasi degildir.

Detay: [English README](README.md), [kurulum](docs/VIBE_INSTALL.md),
[guvenlik](SECURITY.md), [belge dizini](docs/README.md).
