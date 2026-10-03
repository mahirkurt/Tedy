# TEDY kalan planlar ve yayın takibi

Kapsam: 3 Ekim süreç kaydındaki kalan B2–B6 ve D1/D2 planlarının
tamamlanması, mevcut portal/OCR ve D3 arayüz dallarının bütünleştirilmesi,
test edilmiş sürümün `tedy.online` üzerinde yayını.

- [x] Kaynak çalışma ağaçları ve canlı user service doğrulandı.
- [x] B2 son kapısı: 2769 Python testi geçti, 69 atlandı; lint/build ve
  26 dosya yükleme/öğretmen tarayıcı testi geçti.
- [x] B3 sohbet geçmişi, sahiplik, aile salt okuma ve notlar.
- [x] B4 alıştırma, sunucu puanlama, öğrenme günlüğü ve rubrikler.
- [x] B5 sesli okuma, onaylı mikrofon ve erişilebilir arayüz.
- [x] B6 kaynak/öğretmen denetimi ve açık onaylı değerlendirme komutu.
- [x] D1 zengin bloklar, formüller, tablolar ve seçenekli netleştirme.
- [x] D2 ortak yükleme, ödeve bağlama ve fotoğraftan onaylı ödev.
- [x] Üretim, portal/OCR ve D3 dalları birlikte doğrulandı.
- [x] Kaynak/bundle yedeği, yayın ve gerçek URL kontrolü.
- [ ] Android Google girişi: mevcut ortamın ilgili Google projesine erişimi
  3 Ekim yeniden ölçümünde yok. Yetkili konsolda Android OAuth istemcisi gerekir.

Testler ayrı çalışma ağacında, sentetik veriyle ve ücretli model çağrısı
olmadan çalışır. Canlı `.env`, `output/` ve kullanıcıya ait `docs/books/`
testlere bağlanmaz. Canlıya alma öncesi hash taşıyan eski assetler korunur;
yeni assetler önce, `index.html` en son yayınlanır. Backend için yalnız
`ted-dashboard.service` yeniden başlatılır.

## Son doğrulama

- Uygulama sürümü: `b6661b446d9245994a3f470847b81f2fb6dcc911`.
- Tam Python: **3395 geçti, 69 atlandı, 4 uyarı, 0 hata** (370,07 sn,
  exit 0). Atlananlar izole çalışma ağacında bulunmayan scraper verisine bağlıdır.
- ESLint/Stylelint ve üretim build: exit 0. Ses yardımcıları: 3/3 başarılı.
- **490 benzersiz tarayıcı senaryosu** doğrulandı: 395 davranış/erişilebilirlik,
  84 mevcut görsel/ARIA, 11 D1 senaryosu. İlk koşudaki eski sohbet mock'ları
  ve test Python yolu düzeltildikten sonra ilgili tekrarlar tüm açıkları
  kapattı; sonuç tek bir toplu koşuya değil bu doğrulanmış birleşime aittir.
- Canlı Python bağımlılıkları ve `pip check`: başarılı. Kurulu systemd
  birimi depo tanımıyla aynı. Üretimde auth bypass kapalı.
- Canlı servis ortamıyla cevap/denetim modellerinin katalog erişimi ve
  Maarif/OER araçlarının gerçek okuma çağrıları doğrulandı.
- B6'nın 12 soruluk ücretli değerlendirmesi çalıştırılmadı; komut ve
  değerlendirme sözleşmesi test edildi.

## Yayın hazırlığı

Önceki kaynak dalı `cursor/tedy-android-client-f942`, commit
`0f102ae4b646e3568536df24bda495ab40a4b49a`. Önceki arayüz yedeği ve kaynak
kimliği `/mnt/thunderbolt/backups/tedy/releases/20261003T190956Z` altında.
Kullanıcıya ait `docs/books/`, sırlar ve çalışma zamanı verileri korunur.

Tam indeks yenilemesi sürüm 3 dışlama kurallarını uygular: özel yüklemeler,
OCR önbelleği ve sohbet SQLite dosyaları ortak arama indeksine girmez.
Yayın sırasındaki yenileme yalnız mevcut OCR önbelleğini kullanır; yeni OCR
çağrısı yapmaz. Normal servis OCR ayarları değişmez. İleride geri dönüş
gerekirse bu gizlilik dışlamaları korunmalı; eski indeks geri yüklenmemelidir.

## Canlı yayın sonucu

- Yayın: **2026-10-03 19:36:19 UTC**, `release/tedy-20261003` dalı.
  Çalışan uygulama commit'i yukarıdaki `b6661b4`; bu kayıt sonraki yalnız
  dokümantasyon commit'iyle aynı dala eklendi.
- `ted-dashboard.service`: `active/running`, yeni süreç, `Result=success`.
  Yeniden başlatma sonrası incelenen 70 log kaydında hata yok.
- Yerel kök ve `https://tedy.online`: HTTP 200. Yayındaki beş giriş asset'i
  üretilen dosyalarla SHA-256 düzeyinde aynı. Dış HTML'deki tek ekleme
  Cloudflare betiği; uygulama dosya referansları değişmiyor.
- Yerel ve dış URL'de öğretmenler, sohbetler ve öğrenme günlüğü: oturumsuz
  HTTP 401; gerçek öğrenci/aile yetkileriyle HTTP 200 ve beklenen JSON şeması.
  Auth bypass kullanılmadı; sohbet veya ödev oluşturulmadı.
- Tam indeks: **112 dosya, 3166 parça**, manifest sürümü **3**; özel yükleme,
  OCR önbelleği veya sohbet veritabanından indekslenen parça **0**.
  Üç tarama `ocr_suruyor` durumuyla normal OCR yenilemesine bırakıldı;
  tam okunmuş gibi işaretlenmedi. Yayın yenilemesinde yeni OCR çağrısı yok.
- D2 embedding bağımlılığı: canlı Ollama sürüm/model uçları HTTP 200 ve
  gerekli `bge-m3` modeli mevcut. Hesaplama çağrısı yapılmadı.
- Kullanıcının `docs/books/` dosyalarının yayın öncesi/sonrası içerik
  hash'leri aynı; eski hash taşıyan arayüz asset'leri korundu.
- Canlı doğrulama: **2026-10-03 19:37:48 UTC**, exit 0.

Android Google girişi dış bağımlılık olarak açık: `ted-asistan` projesinde
Android OAuth istemcisini oluşturabilecek konsol erişimi bu oturumda yok.
APK üretimi bu yetkilendirmeyi sağlamaz; web yayını bu eksiklikten bağımsızdır.
