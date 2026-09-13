# SVG Üretim Kılavuzu (svg-authoring.md)

Bu belge, `carbon-edupedia` modüllerinde **tema-duyarlı, erişilebilir ve responsive
satır-içi SVG** üretmenin kurallarını ve hazır arketiplerini tanımlar. Çıktı tek dosya
ve çevrimdışı açıldığından, en güçlü ve en güvenilir araç **el-yazımı satır-içi
SVG**'dir (harici kütüphane/CDN bağımlılığı yok). Motor üç yol sunar:

1. **`vizChart(spec)`** — çubuk/çizgi grafik (veri → SVG). Otomatik tema-duyarlı + erişilebilir.
2. **`svgFigure(inner, caption)`** — herhangi bir özel SVG'yi başlıklı, çerçeveli figüre sarar.
3. **Ham `visual.kind:"svg"`** — `teach` segmentinde özgün diyagram; aşağıdaki kurallara uymalı.

---

## 1. Dört değişmez kural

| Kural | Nasıl |
| --- | --- |
| **Responsive** | Sabit `width/height` yerine `viewBox="0 0 W H"`; CSS `max-width:100%`. |
| **Tema-duyarlı** | Renkleri **asla ham hex** verme. `currentColor`, `var(--accent)`, `var(--accent-tint)`, kategorik `var(--viz-1..5)` veya anlamsal `var(--viz-sun/water/cloud)` kullan. Metin rengini hiç verme — `.viz text` otomatik `--cds-text-primary` yapar; ikincil etiket için `class="viz-muted"`. |
| **Erişilebilir** | Bilgi taşıyan SVG: `role="img"` + `<title id>` + (gerekirse) `<desc id>` + `aria-labelledby`. Salt-dekor SVG: `aria-hidden="true"`. |
| **Sakin** | Otomatik/sürekli animasyon yok. Hareket gerekiyorsa `@media (prefers-reduced-motion:no-preference)` altında, tek ve kısa. |

İskelet:
```html
<svg class="viz" viewBox="0 0 480 240" role="img" aria-labelledby="t1 d1">
  <title id="t1">Kısa başlık</title>
  <desc id="d1">Görseli sözle betimleyen bir-iki cümle.</desc>
  <!-- şekiller: fill="var(--accent)" stroke="var(--viz-axis)" ... -->
  <text x="…" y="…">Etiket</text>            <!-- rengi CSS verir -->
  <text class="viz-muted" x="…" y="…">alt</text>
</svg>
```
`teach` görselinde bunu doğrudan `visual:{ kind:"svg", caption:"Şekil 1 — …", ref:`…` }`
ile ver; motor `svgFigure` ile başlık/çerçeve/altyazıyı ekler.

---

## 2. Renk paleti (tema token'ları)

| Token | Açık | Koyu | Kullanım |
| --- | --- | --- | --- |
| `--accent` | Mavi 60 | Mavi 50 | Birincil/tek-seri vurgu |
| `--accent-tint` | Mavi 10 | (koyu zemin) | Dolgu/zemin alanı |
| `--viz-1..5` | cyan/teal/magenta/mor/kırmızı | açık karşılıkları | Kategorik çoklu seri |
| `--viz-sun/water/cloud` | sarı/mavi/gri | açık karşılıkları | Doğa/illüstrasyon anlamsal |
| `--viz-axis` / `--viz-grid` | gri | koyu gri | Eksen / ızgara çizgileri |

Tek seriyse `var(--accent)`; çok seriyse `--viz-1..5` sırayla. Anlam taşıyan illüstrasyonda
(güneş, su, bulut) anlamsal token'ları yeğle.

---

## 3. Öğretim SVG arketipleri

Aşağıdaki desenler `viewBox` koordinatlarıyla, hep token-renkli kurulur.

1. **Etiketli parçalar (labeled parts):** Bir nesne + ok/çizgi ile etiketler. Hücre,
   çiçek, devre, harita. `line` + `text`; oklar için `marker-end="url(#vz-arrow)"` (bkz. §3.1).
2. **Döngü (cycle):** Dairesel akış (su döngüsü, yaşam döngüsü). Aşama kutuları +
   eğri `path` oklar + uç için `marker-end="url(#vz-arrow)"` (`stroke-dasharray` ile akış hissi). Örnek: ana modüldeki su döngüsü.
3. **Süreç/akış (process):** Soldan sağa adımlar; kutu → ok → kutu. Düz `path`/`line` + `marker-end="url(#vz-arrow)"`.
4. **Karşılaştırma (compare):** Yan yana 2–3 panel (katı/sıvı/gaz gibi). Eş ölçekli `rect`
   çerçeveler + içerik. Örnek: ana modüldeki tanecik düzeni.
5. **Sayı doğrusu (number line):** Yatay eksen + işaretler; kesir/tam sayı/işlem.
6. **Parça-bütün (part–whole):** Bölünmüş dikdörtgen ya da daire dilimleri (kesir, yüzde).
   Daire-dilim için özet `donut` mantığı (yalnız özet ekranı) örnek alınabilir.
7. **Çubuk/çizgi grafik (chart):** **`vizChart` kullan** — elle çizme. Veri okuryazarlığı,
   karşılaştırma, zaman serisi.
8. **Zaman çizelgesi (timeline):** Olay dizisi — `timeline` segmenti (SVG değil, DOM) yeğlenir.
9. **Ağaç/hiyerarşi (tree):** Düğüm + bağlantı; şecere, sınıflandırma. `line` + daire/kutu düğüm.
10. **Venn/küme:** İki-üç yarı-saydam daire (`fill` token + `opacity` veya `fill-opacity`).

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
  data:[{label,value,color?}],  // color yalnız kategorik vurgu gerektiğinde (--viz-*)
  max?:Number,            // y-ekseni tavanı (yoksa veriden)
  legend?:true,           // color'lı veride lejant
  caption?:"Şekil n — ..."} // figcaption
```
- Tek seri → otomatik `var(--accent)`. Çok renkli → `data[].color: "var(--viz-2)"` vb.
- Eksen/ızgara/etiketler tema token'larıyla; **animasyon yok**.
- `chart` **görüntüleme** segmenti olarak da kullanılabilir (puanlanmaz): `{ type:"chart", chart:{…} }`
  ya da `teach` içinde `visual:{ kind:"chart", … }`.
- **Donut**: ustalık göstergesi olarak yalnız özet ekranına ayrılmıştır (`donutSvg`).

---

## 5. Erişilebilirlik ve kontrast

- Renk **tek** ayırt edici olmamalı: etiket/şekil + renk birlikte. CVD güvenli paletten seç.
- Metin ≥ 11px; ana etiket `--cds-text-primary`, ikincil `--cds-text-secondary` (`viz-muted`).
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
