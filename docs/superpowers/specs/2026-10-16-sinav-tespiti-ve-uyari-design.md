# Sınav tespiti, içerik birleştirme ve uyarı — tasarım

Tarih: 2026-10-16 · Dal: `feat/sinav-uyari` · Durum: kullanıcı onayı bekliyor

## 1. Amaç

Işık'ın yaklaşan sınavlarını **bütün yayın kaynaklarından** eksiksiz yakalamak, her sınava portalda yayınlanan
konu ve hazırlık bilgisini bağlamak ve sınav yaklaştıkça Işık'ı ve aileyi **telefonlarına bildirimle** zamanında
uyarmak.

Başarı ölçütleri:

- Ders içeriği kartında duyurulan bir sınav (ör. "MATEMATİK KONU TARAMA TESTİ (KTT) KONULARI … 15 EKİM") ya da
  takvimde portalın sınav etiketini taşıyan bir kayıt **kaçmaz**.
- Her sınavın konuları **kaynaktan** gelir; kaynakta olmayan konu, tarih ya da sınav uydurulmaz.
- Uyarı, panoyu açmayan kişiye de telefon bildirimi olarak ulaşır; aynı uyarı iki kez gitmez.

## 2. Kullanıcı kararları (2026-10-16)

| Konu | Karar |
|---|---|
| Uyarı kanalı | Pano + telefona bildirim (web push, PWA) |
| Zamanlama | Kademeli: tespit/değişiklik anında, 7 gün, 2 gün ve önceki akşam |
| Alıcılar | Işık ve dört aile üyesi, her biri kendi cihazında açarsa; Işık'a "sen", aileye "siz"; okuyucu hesaplar almaz |
| Çıkarım yaklaşımı | B: takvim doğrudan; serbest metin anahtar kelime süzgecinden sonra Claude Haiku, yapılandırılmış çıktı, uydurma kapısı, aylık bütçe tavanı |

## 3. Bugünkü durum (ölçüldü, 2026-10-16, `main` 20a3c31)

- `/api/exams` (`src/dashboard_api.py` `_sinav_listesi`) sınavı yalnız takvim **başlığındaki** anahtar kelimeden
  (`sınav`, `yazılı`, `exam`, `test`) tanır. Portalın `extendedProps.calendar == "sinav"` etiketi okunmuyor; bu
  yüzden "Sebit Vcloud Kazanım Değerlendirme Uygulaması-1_TM/_FS" (14–15 Ocak) kaçıyor. Canlıda 3 yaklaşan sınav
  var (GİS-1 23.10, GİS-2 11.12, Türkçe Ortak Yazılı 05.01); hiçbirinde konu metni yok.
- Asıl sınav bilgisi ders içeriği kartlarında: Matematik KTT konu listesi, Fen "Büyük Quiz Zamanı… ilk ünitemizin
  tamamı", İngilizce "Irregular Verbs Quiz". Bunlar `/api/exams`'e hiç girmiyor. Duyurularda sınav geçmiyor;
  portal eklerinde sınavla ilgili dosya yok (623 kaydın 604'ü duyuru bağlantısı).
- `relatedContent` ("Konular") bu haftanın ders kartı başlıklarıdır, sınavın konuları değildir. `aiSummary` ve
  `studyGuide` her zaman boş (`exam_content_map.json`/`enrichment_cache.json` yazarı `src/enrich_gemini.py`
  2bd7ad3'te silindi).
- Hiçbir bildirim kanalı yok (push, servis çalışanı, PWA manifest'i, e-posta, Telegram yok); sınavlar için
  "uyarıldı" kaydı yok.
- Pano: İşler'de "Yaklaşan Sınavlar" listesi, gizli `/sinavlar` sayfası (geri sayım, `utils/countdown.ts`),
  Bugün'de "SINAVLAR" listesi.

## 4. Mimari

```
run_sync (15 dk, kilit altında; ek adımından sonra, health.json'dan önce)
  └─ sinav_tespiti adımı (süre bütçeli; düşerse senkronu bozmaz)
       1. Takvim: calendar == "sinav" VEYA başlık anahtar kelimesi → takvim sınavları
       2. Gelişim raporu sınavları (bugünkü mantık, taşınır)
       3. Serbest metin adayları → ön süzgeç → yeni/değişmiş olanlar Haiku → önbellek
       4. Uydurma kapısı → birleştirme → output/sinavlar.json (tek gerçek kaynak, atomik)

output/sinavlar.json → /api/exams (yalnız okur) → Bugün · İşler · Sınavlar · asistanın `sinavlar` aracı

tedy-sinav-uyari.timer (10 dk, senkrondan bağımsız, kilit almaz)
  └─ sinavlar.json + abonelikler + gönderim defteri → vadesi gelen uyarılar → web push (VAPID)
```

Modüller (her biri tek sorumlu, saf mantık ayrı ve testli):

| Modül | Sorumluluk |
|---|---|
| `src/sinav_kaynaklari.py` | Takvim, gelişim raporu ve serbest metin adaylarını kaynak konumu ve yayın tarihi bağlamıyla toplar; ön süzgeç |
| `src/sinav_tarihi.py` | Türkçe/İngilizce tarih ifadelerini yayın bağlamına göre çözer (saf) |
| `src/sinav_cikarimi.py` | Haiku çağrısı, şema, önbellek, bütçe defteri; uydurma kapısı (saf kısım ayrı) |
| `src/sinav_tespiti.py` | Birleştirme, kararlı kimlik, sürüm, `sinavlar.json` yazımı; `run_sync` adımı ve `--kuru` CLI |
| `src/sinav_uyari.py` | Hangi uyarının vadesi geldiğini hesaplar (saf), metni hitapla kurar; zamanlayıcı giriş noktası |
| `src/web_push.py` | VAPID, abonelik deposu (`flock`), gönderim, ölü abonelik temizliği |
| `dashboard/public/sw.js`, `manifest.webmanifest`, ikonlar | Servis çalışanı ve PWA |
| `dashboard/src/components/SinavUyarilari.tsx` | Bu cihazda bildirim aç/kapat, deneme, durum metni |
| `dashboard/src/components/SinavKarti*` | Bugün kartı, İşler'de Yeni/Değişti etiketi, sınav ayrıntısında konular ve kaynaklar |

`sinavlar.json` tek gerçek kaynaktır: bugün `/api/exams` içinde istek anında yapılan takvim ve gelişim raporu
hesabı bu adıma taşınır; `/api/exams` dosyayı okur, geçmiş/yaklaşan ayrımını istek anında İstanbul saatiyle yapar.
Dosya yoksa (ilk kurulum, adım hiç çalışmadıysa) `/api/exams` bugünkü hesaba düşer — sınav listesi asla boş kalmaz.

### 4.1 Veri modeli (`output/sinavlar.json`)

```json
{
  "uretildi": "2026-10-16T14:05:00+03:00",
  "surum": 1,
  "sinavlar": [{
    "id": "…",                    // takvim kaydı varsa bugünkü takvim kimliği (modüller bağlı); yoksa ders+tarih+tür özeti
    "ders": "Matematik",          // normalize_course; ders dışı ortak sınavlar "Genel"
    "tur": "konu_tarama",         // yazili | kisa_sinav | konu_tarama | deneme | ortak_sinav | diger
    "baslik": "Matematik Konu Tarama Testi (KTT)",
    "tarih": "2026-10-15",        // ISO gün ya da null ("tarih belirsiz")
    "saat": "09:00",              // ya da null
    "konular": ["Tam sayılar", "Rasyonel sayılar", "Mutlak değer"],
    "kaynaklar": [{"tur": "ders_karti", "konum": {"bolum": "ders_icerikleri_haftalar", "hafta": "4. Hafta …",
                   "ders": "Matematik", "sira": 3}, "alinti": "MATEMATİK KONU TARAMA TESTİ (KTT) KONULARI …"},
                  {"tur": "takvim", "konum": {"id": "…"}}],
    "ilk_tespit": "2026-10-12T09:15:00+03:00",
    "icerik_surumu": "sha256(tarih|saat|konular)[:12]",
    "degisti": "2026-10-13T08:00:00+03:00"   // son anlamlı değişiklik ya da null
  }],
  "ozet": {"aday": 52, "incelenen": 50, "incelenmedi": 2, "butce_usd": 0.03}
}
```

`ilk_tespit` ve `degisti` bir önceki `sinavlar.json`'dan kimlikle taşınır. Geçmiş sınavlar 30 gün listede kalır.

## 5. Çıkarım ve uydurma kapısı

**Adaylar.** Metin parçaları kaynak konumuyla toplanır: `ders_icerikleri` ve `ders_icerikleri_haftalar` kartları,
öğeleri ve metni (portal artığı `portal_susu` ile temizlenmiş), ödev başlık ve açıklamaları, duyurular, indirilmiş
portal eklerinin metni (`content/portal-ekleri/<id>.txt`, yalnız ilk 4.000 karakter). Her parçanın **yayın tarihi
bağlamı**: hafta etiketinin tarih aralığı, ödevin `first_seen`'i, duyuru tarihi ya da ekin `first_seen`'i.

**Ön süzgeç (ücretsiz, Türkçe katlamalı).** `sınav`, `yazılı`, `kısa sınav`, `quiz`, `KTT`, `konu tarama`,
`deneme`, `test` (kelime), `exam`, `değerlendirme`, `GİS`. Eşleşmeyen parça modele gitmez.

**Model.** `claude-haiku-4-5` (`TEDY_SINAV_MODEL` ile değişir), `src/claude_api.py` istemcisi, yapılandırılmış
çıktı (`output_config.format`). Girdi: parça metni, ders, yayın tarihi aralığı, bugün. Çıktı: sıfır ya da daha fazla
`{ders, tur, tarih|null, tarih_ifadesi, saat|null, konular[], alinti}`. Önbellek
`output/sinav_cikarim_onbellegi.json`, anahtar `sha256(metin) + ISTEM_SURUMU`; aynı metin bir daha ücret doğurmaz.

**Uydurma kapısı (deterministik, modelden sonra).**

1. `alinti` kaynak metinde birebir geçmeli (`turkce_kucult_katla` ve boşluk sadeleştirmesiyle); geçmezse kayıt atılır.
2. Her `konu` kaynakta geçmeli; geçmeyen konu düşer.
3. Metinde açık tarih varsa ("15 EKİM PERŞEMBE", "15.10", "15/10") `sinav_tarihi` çözümlemesi esastır; model farklı
   tarih derse bizimki kazanır. Göreli ifade ("haftaya", "gelecek hafta", "next week", "yarın", "Cuma") yayın
   bağlamına göre çözülür. Çözülemezse `tarih: null` ("tarih belirsiz").
4. Okul yılı dışındaki ya da yayın tarihinden önceki tarih atılır.
5. Ders adı `normalize_course`; kaynağın dersi biliniyorsa (ders kartı) o esastır.

**Birleştirme.** Aynı ders + aynı gün tek sınavdır. Takvim kaydı varsa kimliği, saati ve başlığı esas alınır;
ders kartının konuları ve kaynak bağlantıları eklenir. Tarihsiz bir sınav, aynı dersin 14 gün içindeki tek tarihli
sınavına konu örtüşmesi varsa bağlanır; yoksa ayrı "tarih belirsiz" kayıt kalır.

**Bütçe.** Aylık tavan `TEDY_SINAV_AYLIK_USD` (varsayılan 2), `output/sinav_cikarim_defteri.json`'a
`response.usage`'tan yazılır (OCR defteri deseni). Tavan dolunca yalnız takvim ve gelişim raporu yolu çalışır;
modelden geçmemiş adaylar `ozet.incelenmedi`'de sayılır. Adım süre bütçelidir (`TEDY_SINAV_SURE`, varsayılan 45 sn);
yetişmeyen adaylar sonraki senkronda.

## 6. Uyarılar

**Türler ve zamanlar** (İstanbul saati):

| Tür | Zaman |
|---|---|
| `tespit` | Yeni sınav ya da `icerik_surumu` değişen sınav: sonraki zamanlayıcı turunda; 22:00–07:30 arasıysa 07:30'da |
| `gun_7` | Sınavdan 7 gün önce 18:00 |
| `gun_2` | Sınavdan 2 gün önce 18:00 |
| `aksam` | Sınavdan 1 gün önce 19:00 |

- Hatırlatma, hedef anı geçmiş ve sınav başlamamışsa gider; hedef anı `ilk_tespit`'ten önceye düşen hatırlatma
  atlanır (3 gün kala bulunan sınava `gun_7` gitmez).
- Aynı turda bir kişiye aynı sınav için vadesi gelen birden çok uyarı tek bildirimde birleşir.
- `tarih: null` sınavlar yalnız `tespit` alır.
- Gönderim defteri `output/bildirim_defteri.jsonl`, anahtar `(email, sinav_id, tur, icerik_surumu)`; aynı uyarı
  iki kez gitmez, sınav değişirse yeni sürüm yeni `tespit` doğurur.

**Metin** (`roles.okur_turu`):

- Işık (`ogrenci`, "sen"): "Pazartesi Matematik KTT var — tam sayılar, rasyonel sayılar, mutlak değer. Bugün 10
  dakikayla başla?"
- Aile ("siz", Işık adıyla): "Işık'ın Pazartesi Matematik KTT sınavı var. Konular: tam sayılar, rasyonel sayılar,
  mutlak değer."
- Bildirim başlığı kısa ("Sınav: Matematik KTT · Pazartesi"); dokununca `/sinavlar?sinav=<id>` açılır.

## 7. Web push ve PWA

- VAPID anahtar çifti bir kez üretilir (`.venv/bin/python -m src.web_push anahtar-uret`), `env_prep` ile `.env`'e
  `TEDY_VAPID_PUBLIC`, `TEDY_VAPID_PRIVATE`, `TEDY_VAPID_SUBJECT` (mailto) yazılır.
- Uçlar (oturum + tam rol; okuyucu, API anahtarı ve `/v1` reddedilir; `READER_ENDPOINTS`'e girmez):
  `GET /api/bildirim/anahtar`, `POST /api/bildirim/abonelik` (`{endpoint, keys, cihaz}`; `endpoint` yalnız
  `https://` ve bilinen push servis alan adları), `DELETE /api/bildirim/abonelik`, `POST /api/bildirim/deneme`
  (yalnız çağıranın cihazlarına).
- Depo `output/bildirim_abonelikleri.json`, kişi (email) başına cihaz listesi, `fcntl.flock` altında yazılır
  (gunicorn iki işçi).
- Gönderim `pywebpush` (yeni bağımlılık); 404/410 dönen abonelik silinir; diğer hatalar deftere yazılır.
- Zamanlayıcı: `tedy-sinav-uyari.service` + `.timer` (10 dk, `Environment=TZ=Europe/Istanbul`), repo kökünde
  izlenen unit dosyaları; `.venv/bin/python -m src.sinav_uyari gonder`. Senkron kilidini almaz; `sinavlar.json`'u
  yalnız okur.
- Pano: `dashboard/public/manifest.webmanifest` (ad "TEDY", 192/512 PNG ikonlar `tedy-icon.svg`'den),
  `dashboard/public/sw.js` (`push` → bildirim, `tag` = sınav kimliği; `notificationclick` → açık sekmeyi odakla ya da
  URL'yi aç). Servis çalışanı yalnız bildirim içindir; çevrimdışı önbellek yapmaz.

## 8. Pano

- **Sınav uyarıları kartı** (Sınavlar sayfası; Bugün'den ve Daha fazla'dan bağlantı): bu cihazda Aç/Kapat,
  "Deneme bildirimi gönder", durum: açık · kapalı · izin reddedildi ("tarayıcı ayarlarından açın") · desteklenmiyor
  · iPhone'da Ana Ekrana eklenmemiş ("Paylaş → Ana Ekrana Ekle, sonra buradan açın").
- **Bugün**: 7 gün içindeki en yakın sınav tek, geri sayımlı kart (İ1); konular ilk üçü ve "kaynak" bağlantısı.
  Mevcut "SINAVLAR" listesi kalır.
- **İşler**: sınav listesinde son 48 saatte tespit edilene **Yeni**, `degisti` son 48 saatteyse **Değişti**
  etiketi (gri, metinli; renk tek başına anlam taşımaz).
- **Sınav ayrıntısı** (`/sinavlar`): konular ve kaynaklar (ders kartı → `/dersler` o hafta, ek → `/api/ekler/<id>`,
  ödev → İşler), kısa alıntıyla; "tarih belirsiz" açıkça yazar. Boş `aiSummary`/`studyGuide` alanları kaldırılır.
- Sağlık özeti `health.json`'da `sinav_tespiti` ve `sinav_uyari`; incelenemeyen aday varsa İşler'de "Bazı ders
  duyuruları incelenemedi" notu (D3).

## 9. Asistan

`sinavlar` aracı (`assistant_tools.sinavlar_metni`) `sinavlar.json`'dan gerçek konuları ve kaynakları okur;
"Konular: yok" yalnız gerçekten konu yoksa yazılır. B4 sınav hazırlığı ve öğretmen modlarının "Konular" kuralı
değişmez, artık gerçek konuyla çalışır.

## 10. Hata durumları

- Model, ağ ya da bütçe: takvim + gelişim raporu yolu çalışır; `ozet.incelenmedi` ve `health.json` söyler.
- `sinavlar.json` okunamazsa `/api/exams` bugünkü hesaba düşer.
- Push hatası: deftere yazılır, ölü abonelik silinir; zamanlayıcının son turu `health.json`'da.
- Abonelik uçları geçersiz gövdeye 400, başkasının aboneliğine dokunmaya 404.

## 11. Test

- Birim (saf): ön süzgeç; tarih çözümleme (Türkçe ay adları, gün adları, "haftaya", "next week", sayısal biçimler,
  yıl sınırı); uydurma kapısı (alıntı/konu kaynakta yok, tarih çatışması); birleştirme (takvim + kart, kimlik
  korunur, tarihsiz bağlama); sürüm/değişiklik; uyarı zamanlaması (geç tespit, sessiz saat, birleştirme, sürüm,
  tarihsiz); hitap metni.
- Gerçek veri fikstürleri (kişisel bilgi temizlenmiş): Matematik KTT kartı, Fen quiz öğesi, İngilizce quiz kartı,
  `calendar: "sinav"` taşıyan takvim kayıtları (Sebit dahil) — her biri doğru ders, tarih ve konuyla.
- Model sahte nesneyle; `tests/conftest.py` gerçek anahtarı kaldırır, hiçbir test ücretli çağrı yapmaz.
- API: abonelik uçlarında rol, sahiplik, geçersiz `endpoint`; `/api/exams` yeni alanlar ve dosyasız düşüş.
- Push: sahte uç noktaya gönderim, 410'da silme.
- e2e: Bugün kartı ve geri sayım, Yeni/Değişti etiketleri, uyarı kartının durumları (izin ve `PushManager`
  taklit), axe ve IBM, telefon görünümü, servis çalışanı kaydı.

## 12. Yayın

1. Pano ve tespit (bildirim kapalı): canlı veride `python -m src.sinav_tespiti --kuru` bir kez çalışır, bulunan
   sınavlar ve konular kullanıcıya gösterilir; kaçan/yanlış varsa kural ve istem düzeltilir.
2. VAPID anahtarı, `pywebpush`, zamanlayıcı unit'i kurulur; kullanıcı ve bir aile üyesi deneme bildirimini alır.
3. Bildirimler açılır (`TEDY_SINAV_UYARI=1`). Geri dönüş: zamanlayıcıyı durdurmak ve bayrağı kapatmak.

Yayın (birleştirme ve canlı) kullanıcının açık onayıyla yapılır.

## 13. Kapsam dışı

E-posta ve Telegram; sınav notlarının otomatik girilmesi; okuyucu hesapları; çevrimdışı pano (servis çalışanı
yalnız bildirim için); kişi başına uyarı türü seçimi (yalnız cihaz başına aç/kapat).
