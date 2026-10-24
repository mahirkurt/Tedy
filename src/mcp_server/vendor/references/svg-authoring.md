# SVG Üretim Kılavuzu (svg-authoring.md)

Bu belge, `carbon-edupedia` modüllerinde **tema-duyarlı, erişilebilir ve responsive
satır-içi SVG** üretmenin kurallarını ve hazır arketiplerini tanımlar. Çıktı tek dosya
ve çevrimdışı açıldığından, en güçlü ve en güvenilir araç **el-yazımı satır-içi
SVG**'dir (harici kütüphane/CDN bağımlılığı yok). Motor üç yol sunar:

1. **`vizChart(spec)`** — çubuk/çizgi grafik (veri → SVG). Otomatik tema-duyarlı + erişilebilir.
2. **`svgFigure(inner, caption)`** — herhangi bir özel SVG'yi başlıklı, çerçeveli figüre sarar.
3. **Ham `visual.kind:"svg"`** — `teach` segmentinde özgün diyagram; aşağıdaki kurallara uymalı ve **metin taşımaz**
   (§1, Kanun M5.6, KB-48). Adı şeklin üstünde gereken şema etiketli şemadır (`visual.kind:"labeled"` ya da
   `diagram` segmenti: `base` yalnız şekil, adlar `labels`'ta).

---

## 1. Dört değişmez kural

| Kural | Nasıl |
| --- | --- |
| **Responsive** | Sabit `width/height` yerine `viewBox="0 0 W H"`; CSS `max-width:100%`. |
| **Tema-duyarlı** | Renkleri **asla ham hex** verme. Yalnız `var(--cds-*)` ve `var(--viz-*)` kullan (Kanun §1 madde 1, M4.7): ör. `var(--cds-border-strong)`, nötr rampa `var(--viz-1..5)`, anlamsal `var(--viz-sun/water/cloud)`. Ders rengi (`--accent`) yazar SVG'sine girmez (M1.5). Metin rengi yazarın işi değildir: yazar SVG'si metin taşımaz (aşağıda **Sakin**). |
| **Erişilebilir** | Bilgi taşıyan SVG: `role="img"` + `<title id>` + (gerekirse) `<desc id>` + `aria-labelledby`. Salt-dekor SVG: `aria-hidden="true"`. |
| **Sakin** | Animasyon yok; hareket yalnız okurun eylemine cevaptır ve motorun işidir (Kanun M2.10). Metin ekranda en az 12 px çizilir (M5.6): şablonun çizicileri (grafik, sayı doğrusu, kesir, etiketli şema, simülasyon) viewBox'ı kutunun genişliğine kurar; yazar SVG'sinde viewBox yazarındır ve kurulamaz. Bu yüzden **yazar SVG'si metin taşımaz** — `visual.kind:"svg"`'nin `ref`'i, etiketli şemanın `base`'i, `hotspot`'un `svg`'si ve gövdeye gömülü SVG'de `<text>`, `<tspan>`, `<textPath>` ya da `<foreignObject>` olursa `edupedia_derle` `sema_hatasi` döner (Kanun M5.6, KB-48). Ad ve etiketi etiketli şemanın `labels`'ına yaz (şablon iğne numarasını kutunun ölçeğinde ≥ 12 px çizer, adı HTML listede yazar) ya da gövde metnine ve altyazıya (`caption`) taşı. `<title>` ve `<desc>` çizilmez, erişilebilir addır; kalır. |

İskelet:
```html
<svg class="viz" viewBox="0 0 480 240" role="img" aria-labelledby="t1 d1">
  <title id="t1">Kısa başlık</title>
  <desc id="d1">Görseli sözle betimleyen bir-iki cümle.</desc>
  <!-- yalnız şekil: fill="var(--viz-2)" stroke="var(--viz-axis)" ... ; metin öğesi yok (KB-48) -->
</svg>
```
`teach` görselinde bunu doğrudan `visual:{ kind:"svg", caption:"Şekil 1 — Soldan sağa …", ref:`…` }`
ile ver; motor `svgFigure` ile başlık/çerçeve/altyazıyı ekler. Panellerin adını altyazı ve gövde söyler
("Soldan sağa katı, sıvı ve gaz: …").

Adı şeklin üstünde gereken şema — hücrenin bölümleri, su döngüsünün aşamaları — etiketli şemadır:
```js
visual:{ kind:"labeled", title:"Su döngüsü şeması", desc:"…", caption:"Şekil 2 — …", viewBox:"0 0 480 300",
  base:`<circle cx="70" cy="55" r="26" fill="var(--viz-sun)" stroke="var(--viz-axis)" stroke-width="2"/>…`,
  labels:[ {x:96, y:80, text:"Güneş"}, {x:336, y:94, text:"Bulut"}, … ] }
```
`base` yalnız şekil taşır; `labels[].x/y` viewBox koordinatıdır ve iğne oraya oturur. Dar ekranda iğne
büyür (yarıçapı en çok ~26 birim): iki iğne arasında en az 52 birim bırak, iğneyi şeklin kenarına koy ki
şekli örtmesin. Ayrı bir görüntüleme segmenti olarak `{ type:"diagram", … }` de aynı alanları alır.

---

## 2. Renk paleti (tema token'ları)

| Token | Açık | Koyu | Kullanım |
| --- | --- | --- | --- |
| `--viz-1..5` | gray100 · gray90 · gray80 · gray70 · gray60 | gray10 … gray50 | Seri ve parça dolgusu; nötr rampa, kategoriyi yerinde etiket taşır (S19, KS-3) |
| `--viz-sun/water/cloud` | sarı/mavi/gri | açık karşılıkları | Doğa/illüstrasyon anlamsal |
| `--viz-axis` / `--viz-grid` | gri | koyu gri | Eksen / ızgara çizgileri |

Tek seri `var(--viz-1)`; çok seri `--viz-1..5` sırayla ve her seri yerinde etiketli. Anlam
taşıyan illüstrasyonda (güneş, su, bulut) anlamsal token'ları yeğle. Ders rengi (`--accent`)
motorun çapalarına aittir; yazar SVG'sinde kullanılmaz (Kanun M1.5).

---

## 3. Öğretim SVG arketipleri

Aşağıdaki desenler `viewBox` koordinatlarıyla, hep token-renkli kurulur.

1. **Etiketli parçalar (labeled parts):** Bir nesne ve parçalarının adları. Hücre,
   çiçek, devre, harita. Etiketli şema (`visual.kind:"labeled"` / `diagram`): şekil `base`'te, adlar
   `labels`'ta; oklar için `marker-end="url(#vz-arrow)"` (bkz. §3.1).
2. **Döngü (cycle):** Dairesel akış (su döngüsü, yaşam döngüsü). Aşama kutuları +
   eğri `path` oklar + uç için `marker-end="url(#vz-arrow)"` (`stroke-dasharray` ile akış hissi); aşama adları
   `labels`'ta. Örnek: ana modüldeki su döngüsü (etiketli şema).
3. **Süreç/akış (process):** Soldan sağa adımlar. SVG çizme: `visual:{ kind:"flow", steps:[…] }` (`relationFlow`) adımları
   HTML kutu → ok → kutu olarak çizer, adım adı gövde boyundadır ve dar ekranda alt alta iner (KB-48).
4. **Karşılaştırma (compare):** Yan yana 2–3 panel (katı/sıvı/gaz gibi). Eş ölçekli `rect`
   çerçeveler + içerik; panel adları altyazıda ("Soldan sağa …"). Örnek: ana modüldeki tanecik düzeni.
5. **Sayı doğrusu (number line):** SVG çizme: `visual:{ kind:"numberline", min, max, step, points:[…] }` (ya da
   `numberline` segmenti); şablon etiketleri her genişlikte ≥ 12 px ve çakışmasız yazar (KB-5, KB-48).
6. **Parça-bütün (part–whole):** Bölünmüş dikdörtgen ya da daire dilimleri (kesir, yüzde).
   Kesir ve oranda daire yerine `fractionBar` çubuk modeli yeğlenir.
7. **Çubuk/çizgi grafik (chart):** **`vizChart` kullan** — elle çizme. Veri okuryazarlığı,
   karşılaştırma, zaman serisi.
8. **Zaman çizelgesi (timeline):** Olay dizisi — `timeline` segmenti (SVG değil, DOM) yeğlenir.
9. **Ağaç/hiyerarşi (tree):** Düğüm + bağlantı; şecere, sınıflandırma. Etiketli şema: `line` + daire/kutu düğüm
   `base`'te, düğüm adları `labels`'ta (KB-48).
10. **Venn/küme:** İki-üç daire `base`'te (`fill` token; kalıcı opaklık yok, KB-41), küme ve kesişim adları
    `labels`'ta (etiketli şema, KB-48).

### 3.1 Yön okları — `vz-arrow` marker (tek doğru yöntem)

Yön okları için **elle `polyline`/chevron çizmeyin.** Şablonun global `<defs>`
sprite'ı tek bir kendiliğinden hizalanan ok-ucu marker'ı sağlar: `vz-arrow`.

- Ok-ucu gereken her çizgiye/eğriye `marker-end="url(#vz-arrow)"` ekleyin
  (`<path … marker-end="url(#vz-arrow)"/>` ya da `<line … marker-end="url(#vz-arrow)"/>`).
- Marker `orient="auto"` ile **eğrinin bitiş teğetine** otomatik döner ve
  `stroke="context-stroke"` ile **çizginin rengini** devralır (mor/gri fark etmez).
- Dolayısıyla ok-ucunun yönü = eğrinin BİTİŞ yönü. Oku istenen yöne baktırmak için
  **eğriyi o yönde bitirin** (aşağı bakan ok → bitiş teğeti aşağı: `M296 38 q42 0 42 24`;
  yukarı → `M234 202 q42 0 42 -24`).

**Neden:** elle yerleştirilen chevron'lar eğrinin ucundan kayar ve teğetle uyumsuz
yöne bakar ("kırık" hizasız ok). Marker bu hata sınıfını kökten kaldırır — tek kaynak,
otomatik hizalama, otomatik renk. Eksen/sayı-doğrusu okları da aynı marker'ı kullanır
(yatay eksen → otomatik sağa bakar).

---

## 4. `vizChart(spec)` sözleşmesi (motor)

```js
{ kind:"bar"|"line",
  title:"...",            // <title> (erişilebilirlik + başlık)
  desc:"...",             // <desc> (ekran okuyucu betimi) — veriyi sözle özetle
  data:[{label,value}],   // color yazılmaz (Kanun M4.7; motor bugün kabul ediyor, borç KB-25)
  max?:Number,            // y-ekseni tavanı (yoksa veriden)
  legend?:true,           // çok seride lejant; mümkünse yerinde etiket
  caption?:"Şekil n — ..."} // figcaption
```
- Tek seri → otomatik `var(--viz-1)`; çok seri `--viz-1..5` sırayla. `data[].color` yazılmaz
  (Kanun M4.7).
- Eksen/ızgara/etiketler tema token'larıyla; **animasyon yok**.
- `chart` **görüntüleme** segmenti olarak da kullanılabilir (puanlanmaz): `{ type:"chart", chart:{…} }`
  ya da `teach` içinde `visual:{ kind:"chart", … }`.
- Özet ekranında halka grafik yoktur (S43); özet düz metindir.

---

## 5. Erişilebilirlik ve kontrast

- Renk **tek** ayırt edici olmamalı: etiket/şekil + renk birlikte. CVD güvenli paletten seç.
- Yazar SVG'si metin taşımaz (§1, KB-48); şablonun çizdiği metin her genişlikte ≥ 12 px'tir (Kanun M5.6).
- `<title>` kısa ad, `<desc>` görseli sözle anlatır (grafikte veriyi özetler).
- Dekoratif çizgiler/ızgara için ekran-okuyucuya bilgi taşıma; tek `role="img"` + başlık yeter.

---

### 5.1 Tırnak tuzağı — G-SVG çift tırnak arar (ölçüldü 2026-07-31)

SVG'yi `MODULE_DATA` içinde bir JS string'i olarak yazarken **öznitelikleri tek tırnakla
yazmayın**. Kapı erişilebilirliği düz metin araması ile denetler:

```python
has_role = 'role="img"' in open_tag        # validate_module.py, _svg_accessible
```

`role='img'` yazan bir SVG **geçerli, erişilebilir ve doğru render olur** — ama kapı onu
göremez ve **FAIL** üretir. Sessiz bir tuzak: hata SVG'de değil, tırnak biçimindedir.

**Doğru yol — backtick sarmalayıcı:**

```js
visual: { kind: "svg", ref: `<svg viewBox="0 0 420 260" role="img"
          aria-label="..."><title>Güneş'in yolu</title>...</svg>` }
```

Backtick, hem öznitelik çift tırnaklarını hem içerikteki Türkçe apostrofu (`Güneş'in`)
kaçışsız taşır. Çift tırnaklı sarmalayıcı (`ref: "<svg …>"`) öznitelikler için kaçış
zorunlu kılar; tek tırnaklı sarmalayıcı ise apostrofta kırılır.

## 6. Doğrulama (G-SVG)

`scripts/validate_module.py` → **G-SVG**:
- **FAIL:** Dekoratif olmayan (aria-hidden/cds-icon olmayan) bir SVG'de `role="img"` veya
  başlık/etiket (`<title>`/`aria-label`/`aria-labelledby`) eksikse.
- **WARN:** Figür SVG'sinde ham `fill="#…"`/`stroke="#…"` varsa (tema-duyarlı değil).
- Sprite ve `@carbon` ikon/piktogramları `aria-hidden="true"` ile dışlanır.

> Kural: bilgi taşıyan her SVG erişilebilir + token-renkli; süs her SVG `aria-hidden`.
