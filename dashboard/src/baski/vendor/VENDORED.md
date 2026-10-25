# Baskı için depoya alınmış varlıklar

Pano `node_modules`'u canlı checkout'a bağlı olduğundan (çalışma ağaçları `npm install` yapamaz) ve baskı ağsız
koşmak zorunda olduğundan (spec 2026-10-25 §5.2: "sürüm sabit, depoya alınmış; CDN yok") bu dosyalar **hiç
düzenlenmez**; güncelleme yalnız aynı komutlarla yeni sürümü indirip `SHA256SUMS`'u yeniden üretmektir.

| Varlık | Sürüm | Kaynak | Lisans |
|---|---|---|---|
| `pagedjs-0.4.3/paged.esm.js` | pagedjs 0.4.3 | `npm pack pagedjs@0.4.3` (`dist.integrity` sha512-YtAN9JAjsQw1142gxEjEAwXvOF5nYQuDwnQ67RW2HZDkMLI+b4RsBE37lULZa9gAr6kDAOGBOhXI4wGMoY3raw==) | MIT (`pagedjs-0.4.3/LICENSE.md`) |
| `dashboard/public/fonts/plex/IBMPlexSans-*.woff2` | @ibm/plex-sans 1.1.0, `fonts/complete/woff2/` | `npm pack @ibm/plex-sans@1.1.0` | OFL-1.1 (`dashboard/public/fonts/plex/OFL.txt`) |
| `dashboard/public/fonts/plex/IBMPlexMono-*.woff2` | @ibm/plex-mono 2.5.0, `fonts/complete/woff2/` | `npm pack @ibm/plex-mono@2.5.0` | OFL-1.1 |

Ağırlıklar Carbon'un üç ağırlığıdır (300, 400, 600) ve gövde italiği; `complete` dosyaları Türkçe harflerin
tamamını taşır.

Doğrulama (depo kökünden):

```bash
sha256sum -c --quiet dashboard/src/baski/vendor/SHA256SUMS
```
