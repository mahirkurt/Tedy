# Tedy Books — kitap ekleme rehberi

Panelde **Tedy Books** menüsü (`/kitaplar`) bu klasörü okur. Bir kitap, `books/`
altındaki tek bir klasördür; klasör adı aynı zamanda URL'deki slug'dır
(`books/yuzuklerin-efendisi` → `/kitaplar/yuzuklerin-efendisi`).

Slug yalnız küçük harf, rakam ve tire içerebilir.

```
books/
└─ yuzuklerin-efendisi/
   ├─ book.json                          ← künye + tam içindekiler
   ├─ B01_Dort_Gozle_Beklenen_Davet.md   ← bölüm metni
   ├─ B02_Gecmisin_Golgesi.md
   └─ ...
```

## Yeni bölüm eklemek

**Tek adım:** bölümün `.md` dosyasını kitap klasörüne kopyala. Kod değişikliği,
yeniden derleme veya servis yeniden başlatma gerekmez — API her istekte klasörü
tarar, bölüm anında okunabilir hale gelir ve "Yakında" etiketi kalkar.

Eklendikten sonra kontrol etmek istersen:

```bash
python src/check_books.py                      # tüm raf
python src/check_books.py yuzuklerin-efendisi   # tek kitap
```

Bölümleri panelin kullandığı kod yolundan geçirir; dosya adı eşleşmediyse,
künye bloğu tanınmadıysa veya gövde boşsa uyarır ve sıfırdan farklı çıkar.

Dosya adı, `book.json` içindeki bölüm `id`'si ile başlamalı ve ardından bir
ayraç (`_`, `-`, `.` veya boşluk) gelmelidir:

| `book.json` `id` | Eşleşen dosya adı |
|---|---|
| `B02` | `B02_Gecmisin_Golgesi.md` |
| `B17` | `B17-Khazad-dum-Koprusu.md` |
| `EK-A` | `EK-A_Aragorn.md` veya `EK_A_Aragorn.md` |

Manifestteki hiçbir `id` ile eşleşmeyen `.md` dosyaları da kaybolmaz; listenin
sonuna adından türetilmiş bir başlıkla eklenir.

## Bölüm dosyasının biçimi

Markdown. Dosyanın başındaki künye bloğu okuyucu tarafından otomatik ayıklanır;
okuma ekranı kendi kapak sayfasını `book.json`'daki bilgilerden dizer, yani
başlık metinde iki kez görünmez. Ayıklayıcı baştaki başlık satırlarını tüketip
ilk düzyazı satırında durur, dolayısıyla iki biçim de çalışır:

```markdown
### BÖLÜM III

ÜÇ KAFADAR

Bölümün ilk paragrafı buradan başlar…
```

ya da ayraçlı uzun biçim:

```markdown
# BİRİNCİ KİTAP

## BÖLÜM II — GEÇMİŞİN GÖLGESİ

*J.R.R. Tolkien, Yüzüklerin Efendisi · çev. Çiğdem Erkal İpek (Metis)*

---

Bölümün ilk paragrafı buradan başlar…
```

Okuyucunun desteklediği Markdown: başlıklar, `---` ayraçları, `**kalın**`,
`*italik*`, `` `kod` ``, madde listeleri ve `>` alıntı blokları.

### Şiir ve şarkılar

Manzum parçalar için `>` kullanmak **tercih edilen** yoldur — satır sonları
korunur ve kıta italik bir sütun olarak dizilir:

```markdown
> Yol uzayıp gider durmadan
> Başladığı kapıdan uzağa
```

`>` konmamışsa okuyucu manzumu yine de yakalamaya çalışır: art arda gelen,
boş satırla ayrılmış, 80 karakterden kısa ve tırnak/çizgi ile başlamayan
**iki veya daha fazla** satırlık dizileri kıta olarak dizer. Diyalog satırları
tırnakla başladığı için bu ayrıma takılmaz.

Bu bir tahmindir, sözleşme değil. Sonuç yanlışsa — kısa cümleler yanlışlıkla
kıtaya dönüştüyse ya da bir şiir yakalanmadıysa — o parçayı `>` ile işaretle;
açık işaret her zaman tahmini geçersiz kılar.

## `book.json`

Kitabın künyesi ve **tam** içindekiler listesi. Henüz yazılmamış bölümler de
buraya yazılır — panelde "Yakında" olarak görünür, böylece kitabın tamamı
baştan bellidir ve ilerleme yüzdesi anlamlı olur.

```jsonc
{
  "slug": "yuzuklerin-efendisi",
  "title": "Yüzüklerin Efendisi",
  "subtitle": "Üç cilt bir arada",
  "author": "J.R.R. Tolkien",
  "translator": "Çiğdem Erkal İpek",
  "publisher": "Metis Yayıncılık",
  "edition": "14 yaş uyarlaması",
  "description": "Raf kartında görünen tanıtım metni.",
  "epigraph": "Kitap sayfasında görünen kısa alıntı.",
  "cover": { "palette": "forest", "monogram": "YE" },
  "wordsPerMinute": 180,
  "chapters": [
    {
      "id": "B01",
      "order": 1,
      "volume": "I — Yüzük Kardeşliği",   // içindekilerde üst başlık
      "part": "BİRİNCİ KİTAP",             // içindekilerde alt başlık
      "numeral": "I",                      // satır başındaki numara
      "label": "Bölüm I",                  // okuma ekranındaki üst satır
      "title": "Dört Gözle Beklenen Davet",
      "sourceWords": 8055                  // bilgi amaçlı; okuma süresi
    }                                      // gerçek dosyadan hesaplanır
  ]
}
```

`cover.palette` için üç seçenek var: `forest` (varsayılan, koyu yeşil bez cilt),
`oxblood` (bordo), `midnight` (lacivert).

`book.json` zorunlu değildir: sadece `.md` dosyaları içeren bir klasör de
geçerli bir kitaptır, künyesi klasör adından türetilir.

## API

| Uç | Döndürdüğü |
|---|---|
| `GET /api/books` | Raftaki kitapların künyesi ve ilerleme sayıları |
| `GET /api/books/<slug>` | Künye + tam içindekiler (her bölüm için `available`) |
| `GET /api/books/<slug>/chapters/<id>` | Bölüm metni + önceki/sonraki bölüm |

Hepsi panelin normal oturum kimlik doğrulamasına tabidir.

## Okuma konumu

Kaldığı yer, tema, punto, satır aralığı ve sütun genişliği tarayıcının
`localStorage`'ında tutulur (`tedy-books-progress`, `tedy-books-settings`).
Sunucuya yazılmaz; yani cihaz başına ayrıdır.
