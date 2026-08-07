# Güvenlik Politikası / Security Policy

## Türkçe

Güvenlik açığını herkese açık issue içinde ayrıntılandırmayın. Tercihen
[GitHub Private Vulnerability Reporting](https://github.com/trugurpala/pala-project-studio/security/advisories/new)
kullanın.

Rapor; etkilenen sürümü, yeniden üretme adımlarını, beklenen etkiyi ve mümkünse
zararsız bir kanıtı içermelidir. Gerçek token, parola, müşteri verisi veya başka
bir projenin özel dosyalarını rapora eklemeyin.

Pala hook'ları test, build, ağ, GitHub veya deploy komutu çalıştırmamalıdır.
Böyle bir davranış gözlenirse eklentiyi devre dışı bırakın ve sürüm bilgisiyle
birlikte özel olarak bildirin.

## English

Do **not** file public issues with exploit detail. Prefer
[GitHub Private Vulnerability Reporting](https://github.com/trugurpala/pala-project-studio/security/advisories/new).

Include: affected version, reproduction steps, expected impact, and a harmless
proof if possible. Never attach real tokens, passwords, customer data, or
another project's private files.

Pala hooks must not run tests, builds, network calls, GitHub mutations, or
deploys. If you observe that, disable the plugin and report privately with the
version string.
