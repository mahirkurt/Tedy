# TEDY API Baglanti Kilavuzu

Isik'in okul verilerine programatik erisim saglayan REST API.

## Kimlik Dogrulama

Tum isteklerde API key gereklidir. Iki yontemle gonderebilirsiniz:

**Header (onerilen):**
```
Authorization: Bearer tdyK_YOUR_KEY
```

**Query parameter:**
```
?api_key=tdyK_YOUR_KEY
```

Base URL: `https://tedy.online`

---

## Endpoint'ler

### Ders Programi

```
GET /api/schedule
```

Haftalik ders programini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/schedule
```

---

### Odevler

```
GET /api/homework
```

Tum odevleri (portal + foto + ozel ders) dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/homework
```

---

### Notlar

```
GET /api/grades
```

Sinav sonuclari ve notlari dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/grades
```

---

### Takvim

```
GET /api/calendar
```

Okul takvim etkinliklerini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/calendar
```

---

### Birlesik Takvim

```
GET /api/calendar/unified
```

Tum etkinlikleri (ders, sinav, odev, takim, takvim) tek bir timeline'da birlestirir.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/calendar/unified
```

---

### Takimlar

```
GET /api/teams
```

Takim aktivitelerini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/teams
```

---

### Ders Icerikleri

```
GET /api/content
```

Ders icerikleri ve materyallerini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/content
```

---

### Duyurular

```
GET /api/announcements
```

Okul duyurularini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/announcements
```

---

### Ogrenci Profili

```
GET /api/student/profile
```

Ogrenci bilgilerini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/student/profile
```

---

### Platform Ilerleme

```
GET /api/progress/ec    # EnglishCentral ilerleme
GET /api/progress/a3k   # Achieve3000 ilerleme
```

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/progress/ec
```

---

### SEBIT

```
GET /api/sebit
```

SEBIT odev verilerini dondurur.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/sebit
```

---

### AI Zenginlestirme

```
GET /api/enrichment
```

Eski `enrichment_cache.json` kaydini dondurur (varsa). Classroom yazan
zenginlestirme yolu kaldirildi; yeni not uretilmez.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/enrichment
```

---

### Sistem Sagligi

```
GET /api/health
```

Son senkronizasyon durumu, hata sayisi ve sure bilgisi.

```bash
curl -H "Authorization: Bearer tdyK_YOUR_KEY" \
  https://tedy.online/api/health
```

---

## Ozel Dersler

```
GET  /api/private-lessons          # Listele
POST /api/private-lessons          # Yeni ekle
```

POST body ornegi:
```json
{
  "course": "Matematik",
  "teacher": "Ahmet Hoca",
  "time": "16:00",
  "weekday": "Pazartesi",
  "recurring": true
}
```

---

## Hata Kodlari

| Kod | Anlami |
|-----|--------|
| 200 | Basarili |
| 401 | Gecersiz veya eksik API key |
| 404 | Endpoint bulunamadi |
| 500 | Sunucu hatasi |

Tum hatalar JSON formatinda dondurulur:
```json
{"error": "Unauthorized"}
```

---

## Notlar

- Tum response'lar JSON formatindadir
- Veriler her 15 dakikada otomatik guncellenir (cron sync)
- Google Classroom, Calendar veya Drive yazma yolu yoktur
- Rate limit yoktur, makul kullanim beklenir
- API key'i guvenli tutun, paylasmayin. Orneklerdeki `tdyK_YOUR_KEY`
  yer tutucusunu kendi anahtarinizla degistirin
  (`python src/dashboard_api.py --generate-key`)
