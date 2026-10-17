# Modül şablonu: 4K eşliği ve kalan Carbon sapmaları — uygulama planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modül şablonunu panonun kök yazı ölçeğine bağlamak ve §11'de açık kalan üç Carbon sapmasını (S19, S11, yarıçap) kapatmak.

**Architecture:** Dört iş birbirinden bağımsız: (1) `--viz-*` paletini nötr rampaya çevirip onu ezen kaskadı onarmak, (2) dilbilgisi rollerini renkten `text-decoration` biçimine taşımak, (3) statik yüzey gölgesini ve iki `rgba()`'yı kaldırmak, (4) yarıçapı token'a bağlamak. Beşinci iş 4K: şablonun px ölçüleri `rem`'e çevrilir ve pano, kök yazı boyunu mevcut `edupedia:appearance` mesajına eklenen isteğe bağlı `rootPx` alanıyla bildirir. Köprü işi `src/mcp_server/sablon.py`'de (TEDY'nin kendi kodu) olur; vendored şablon yalnız CSS tarafında değişir.

**Tech Stack:** Vanilla CSS/JS (vendored HTML şablonu), Python (`sablon.py`, `gates_ek.py`, pytest), TypeScript (`moduleBridge.ts`, `ModuleViewer.tsx`), node (şablon işlevlerini testte koşturmak için), Playwright (e2e).

**Spec:** `docs/superpowers/specs/2026-10-15-modul-sablonu-carbon-sapmalari-design.md`

## Global Constraints

- Vendored tek kaynak: `src/mcp_server/vendor/` altındaki her dosya değişiminden sonra `.venv/bin/python -m src.mcp_server.vendor_sync --pin`; dosya ve `PROVENANCE.json` **aynı commit'te**.
- `sablon.py`'nin 8 çapası (`PATCHES`: bridge, answer, segment, complete, ready, visual, audio, slots) ve `HOST_THEME_HOOK` metni **değişmez**; hepsi JS bloğundadır, CSS bloğu (satır 23–1013) çapasızdır.
- 18 kapı FAIL'siz kalır; doğrudan ilgili olanlar `G-CARBON`, `G-CARBON-GRID`, `G-TOKEN`, `G-CONTRAST`, `G-SVG`, `G-BRIDGE`.
- Yeşil kalacak testler: `tests/test_tedy_tasarim_tutarliligi.py`, `tests/test_ders_renkleri.py`, `tests/test_pano_talimatname_borclari.py`, `tests/test_pano_tasarim_sistemi.py`.
- Kontrast tabanı: metin-dışı grafik için **3:1**; zeminler şablonun kendi `--cds-layer-01` değerleri (g10 `#ffffff`, white `#f4f4f4`, g100 `#262626`).
- px→rem dönüşümü: `n px → n/16 rem`. **İstisnalar px kalır:** kenarlık ve ≤ 3 px saç çizgileri, `@media` kırılma noktaları (`max-width:560px`, `max-width:400px`), SVG `viewBox` birimsiz değerleri.
- `--sp-*` zaten `--cds-spacing-*`'a bağlıdır (rem) — çevrilmez.
- Renk aritmetiği yasak (D1): `rgba()`, gradient, `filter`, `color-mix` eklenmez.
- Emoji yok (G-EMOJI); tüm görünür dizge cümle düzeni (B70/B41).
- `MODULE_DATA`'ya renk/tema/CSS yazılmaz; bu plan `MODULE_DATA` şemasına dokunmaz.
- Kullanıcının `main`'de commit'lenmemiş işi var: **önce dal açılır**, staging dosya adıyla yapılır, `git add -A` kullanılmaz.

## Review Focus

- **`rootPx` düşmanca değer taşır** (`NaN`, `"32"`, `Infinity`, `-5`, `1e9`): modül sayıyı yok saymalı ya da 12–48 aralığına kıstırmalı, asla `font-size: NaNpx` yazmamalı. → Görev 7 testi.
- **Modül tek başına açılır** (mesaj hiç gelmez): kök 16 px kalmalı ve sayfa bugünkü gibi çizilmeli — geriye uyum. → Görev 7 testi.
- **Okur temayı kendi değiştirir** (`toggleTheme`) pano `rootPx` gönderdikten sonra: yazı ölçeği korunmalı, tema değişimi kök boyunu sıfırlamamalı. → Görev 7 testi.
- **Koyu temada etkin palet**: kaskad onarımından sonra g100'de kazanan değer koyu rampa olmalı; bildirilen değeri değil **kaskaddan sonra kazananı** ölçen test gerekir (bugünkü hata tam buydu). → Görev 2 testi.
- **Yazar `p.color` ile ders ailesi geçirir**: palet artık sunmasa da yazar elle geçirebilir; lejant yuvarlağı ve çubuk yine zemine karşı okunur kalmalı, grafik çizilmeye devam etmeli (sessiz bozulma yok). → Görev 2 testi.

---

### Task 1: Dal ve taban ölçümü

**Files:**
- Değişmez; yalnız dal ve taban kaydı.

**Interfaces:**
- Consumes: —
- Produces: `modul-4k-carbon` dalı; `/tmp/taban-kapilar.txt` taban kapı raporu.

- [ ] **Step 1: Dalı aç**

```bash
git branch modul-4k-carbon
git checkout modul-4k-carbon
```

- [ ] **Step 2: Kullanıcının işini doğrula (dokunulmayacak)**

```bash
git status --short
```
Beklenen: `src/run_sync.py`, `src/scrape_achieve3000.py`, `src/scrape_englishcentral.py`, `docs/books/`, `tests/test_platform_girisleri.py` değişik/izlenmemiş kalır. Bu dosyalar bu planda **hiç** staging'e alınmaz.

- [ ] **Step 3: Taban kapı raporunu al**

```bash
.venv/bin/python -m src.mcp_server.derleme --ornek QUIZ --cikti /tmp/quiz-taban.html | tee /tmp/taban-kapilar.txt
```
Beklenen: FAIL yok.

- [ ] **Step 4: Taban testleri koştur**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_tedy_tasarim_tutarliligi.py tests/test_ders_renkleri.py tests/test_pano_talimatname_borclari.py tests/test_pano_tasarim_sistemi.py
```
Beklenen: hepsi geçer. Geçmiyorsa **dur** ve bildir: taban kırıksa bu planın testleri anlamsız.

- [ ] **Step 5: Vendored pin'in temiz olduğunu doğrula**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --check
```
Beklenen: sapma yok.

---

### Task 2: S19 — nötr rampa ve kaskad onarımı

**Files:**
- Modify: `src/mcp_server/vendor/assets/module-template.html` (satır 308, 378 ve g10 `:215` / white `:252` blokları)
- Modify: `src/mcp_server/vendor/PROVENANCE.json` (pin)
- Test: `tests/test_pano_talimatname_borclari.py`

**Interfaces:**
- Consumes: Görev 1'in dalı.
- Produces: `--viz-1..5` üç tema bloğunda nötr gri rampa olarak bildirilir; çıplak `:root` artık `--viz-*` bildirmez.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_pano_talimatname_borclari.py` sonuna ekle:

```python
VIZ_DERS_AILESI = {  # tagPairs ders aileleri (carbon-v11-authority.json) — viz yuvasında olmamalı
    "#6929c4", "#002d9c", "#1192e8", "#007d79", "#9f1853",
    "#be95ff", "#78a9ff", "#33b1ff", "#08bdba", "#ff7eb6",
}


def _viz_bloklari():
    """Her tema seçicisi için o blokta bildirilen --viz-* değerleri."""
    metin = SABLON.read_text(encoding="utf-8")
    bloklar = {}
    for eslesme in re.finditer(r"(?m)^(:root[^{\n]*|\[data-theme=\"[a-z0-9]+\"\])\{", metin):
        bas = eslesme.end()
        son = metin.index("}", bas)
        govde = metin[bas:son]
        viz = dict(re.findall(r"--viz-([1-5])\s*:\s*(#[0-9a-fA-F]{6})", govde))
        if viz:
            bloklar.setdefault(eslesme.group(1), {}).update(viz)
    return bloklar


def test_s19_viz_yuvalari_ders_ailesi_degil():
    for secici, viz in _viz_bloklari().items():
        for yuva, deger in viz.items():
            assert deger.lower() not in VIZ_DERS_AILESI, f"{secici} --viz-{yuva} ders ailesi tonu: {deger}"


def test_s19_viz_ciplak_rootta_bildirilmez():
    """Kaskad: ciplak :root, [data-theme=g100]'den SONRA gelir ve esit ozgullukte oldugu icin
    onu ezer. Bu yuzden --viz-* yalniz tema bloklarinda bildirilir."""
    bloklar = _viz_bloklari()
    assert ":root" not in bloklar, "--viz-* ciplak :root'ta bildirilmis; koyu tema paletini ezer"
    assert '[data-theme="g100"]' in bloklar, "koyu tema --viz-* bildirmiyor"
```

- [ ] **Step 2: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s19_viz_yuvalari_ders_ailesi_degil tests/test_pano_talimatname_borclari.py::test_s19_viz_ciplak_rootta_bildirilmez
```
Beklenen: ikisi de FAIL — birincisi ders ailesi tonları yüzünden, ikincisi `:root`'ta bildirim olduğu için.

- [ ] **Step 3: Kontrast kapısı testini yaz**

```python
def _kontrast(a: str, b: str) -> float:
    def kanal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    def parlaklik(h):
        h = h.lstrip("#")
        r, g, bl = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * kanal(r) + 0.7152 * kanal(g) + 0.0722 * kanal(bl)
    la, lb = parlaklik(a), parlaklik(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Temanın kendi --cds-layer-01 zemini: grafik .stage içinde çizilir.
VIZ_ZEMIN = {':root,[data-theme="g10"]': "#ffffff",
             '[data-theme="white"]': "#f4f4f4",
             '[data-theme="g100"]': "#262626"}


def test_s19_viz_zemine_karsi_3_1():
    bloklar = _viz_bloklari()
    for secici, zemin in VIZ_ZEMIN.items():
        viz = bloklar.get(secici)
        assert viz, f"{secici} --viz-* bildirmiyor"
        for yuva, deger in viz.items():
            oran = _kontrast(deger, zemin)
            assert oran >= 3.0, f"{secici} --viz-{yuva} {deger} zemin {zemin}: {oran:.2f}:1 < 3:1"
```

- [ ] **Step 4: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s19_viz_zemine_karsi_3_1
```
Beklenen: FAIL — g10 ve white blokları `--viz-*` bildirmiyor (bugün çıplak `:root`'ta).

- [ ] **Step 5: Şablonu düzelt**

`module-template.html`:

1. Satır 378'deki `--viz-1..5` bildirimini çıplak `:root{` bloğundan **sil**.
2. g10 bloğuna (`:root,[data-theme="g10"]{`, satır 215) ekle:

```css
  --viz-1:#161616; --viz-2:#262626; --viz-3:#393939; --viz-4:#525252; --viz-5:#6f6f6f;
```

3. White bloğuna (`[data-theme="white"]{`, satır 252) **aynı** beş satırı ekle (zemin `#f4f4f4`, gray-60 orada 4,25:1).
4. g100 bloğundaki (satır 308) bildirimi şununla değiştir:

```css
  --viz-1:#f4f4f4; --viz-2:#e0e0e0; --viz-3:#c6c6c6; --viz-4:#a8a8a8; --viz-5:#8d8d8d;
```

Satır 366'daki yorumun yanına, paletin neden nötr olduğunu söyleyen bir satır ekle:

```css
  /* --viz-*: kategoriyi BİÇİM taşır, hue değil (S19). Ders aileleri ders işaretine, kırmızı/yeşil/
     sarı/turuncu anlama ayrılmıştır; kategorik palete yedek hue kalmaz. Yuvalar nötr gri rampadır ve
     her tema kendi zeminine karşı ≥ 3:1 taşır. Tema bloklarında bildirilir: çıplak :root g100'ü ezer. */
```

- [ ] **Step 6: Testleri koştur, geçtiğini gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py -k "s19 or b52"
```
Beklenen: yeni üç test PASS; `test_b52_seriler_viz_paletinde` hâlâ PASS (token adları korundu).

- [ ] **Step 7: Yazarın geçirdiği hue sessizce bozmuyor (Review Focus)**

```python
def test_s19_yazarin_gecirdigi_renk_grafigi_bozmaz():
    """Palet ders ailesi sunmasa da yazar p.color ile elle gecirebilir: grafik yine cizilir."""
    svg = _grafik_calistir(
        "vizChart({legend:true,data:[{label:'A',value:3,color:'#9f1853'},{label:'B',value:5}]})")
    assert svg.count("<rect") == 2
    assert "#9f1853" in svg, "yazarin degeri dusurulmus"
    assert "var(--viz-1)" in svg, "varsayilan yuva kullanilmamis"
```

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s19_yazarin_gecirdigi_renk_grafigi_bozmaz
```
Beklenen: PASS.

- [ ] **Step 8: Pin ve commit**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --pin
.venv/bin/python -m src.mcp_server.vendor_sync --check
git add src/mcp_server/vendor/assets/module-template.html src/mcp_server/vendor/PROVENANCE.json tests/test_pano_talimatname_borclari.py
git commit -m "fix(modül): S19 — viz paleti nötr rampa, kaskad onarıldı"
```

---

### Task 3: Dilbilgisi rolleri biçimle ayrılır

**Files:**
- Modify: `src/mcp_server/vendor/assets/module-template.html:945-952`
- Modify: `src/mcp_server/vendor/PROVENANCE.json`
- Test: `tests/test_pano_talimatname_borclari.py`

**Interfaces:**
- Consumes: Görev 2'nin nötr rampası.
- Produces: `.tok[data-role=…]` kuralları renk değil `text-decoration-style` taşır; `art` işaretsizdir.

- [ ] **Step 1: Başarısız testi yaz**

```python
def test_s19_dilbilgisi_rolleri_renkle_ayrilmaz():
    metin = SABLON.read_text(encoding="utf-8")
    kurallar = re.findall(r'\.tok\[data-role="([a-z]+)"\][^{]*\{([^}]*)\}', metin)
    assert kurallar, ".tok rol kurallari bulunamadi"
    biciminden = {}
    for rol, govde in kurallar:
        assert "var(--viz-" not in govde, f"{rol} rolu viz paletinden renk aliyor"
        assert "var(--accent" not in govde, f"{rol} rolu ders aksanindan renk aliyor"
        bicim = re.search(r"text-decoration-style\s*:\s*([a-z]+)", govde)
        if bicim:
            biciminden[rol] = bicim.group(1)
    assert len(set(biciminden.values())) == len(biciminden), f"iki rol ayni bicimi paylasiyor: {biciminden}"
    assert len(biciminden) >= 5, f"bes isaretli rol bekleniyordu: {biciminden}"
```

- [ ] **Step 2: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s19_dilbilgisi_rolleri_renkle_ayrilmaz
```
Beklenen: FAIL — kurallar `var(--viz-*)` ve `var(--accent)` taşıyor.

- [ ] **Step 3: Şablonu düzelt**

Satır 945–952 şu hâle gelir:

```css
.tok .w{font-weight:600;padding-bottom:3px;
  text-decoration-line:underline;text-decoration-color:var(--cds-border-strong);
  text-decoration-thickness:3px;text-underline-offset:3px}
.tok .tg{font-size:.72rem;font-weight:600;color:var(--cds-text-secondary)}
/* Rol BİÇİMLE ayrılır, renkle değil (S19): ders aileleri ders işaretine ayrılmıştır. Taşıyıcı
   zaten .tg etiketidir (satır 942: "DAİMA etiketle birlikte"); biçim ikincil, CVD-güvenli ipuçtur.
   border-style'da `wavy` yok; sözcük işaretlemenin doğru özelliği text-decoration'dır. */
.tok[data-role="masc"] .w{text-decoration-style:solid}
.tok[data-role="fem"]  .w{text-decoration-style:double}
.tok[data-role="verb"] .w{text-decoration-style:dotted}
.tok[data-role="noun"] .w{text-decoration-style:dashed}
.tok[data-role="adj"]  .w{text-decoration-style:wavy}
/* art: işlev sözcüğü, işaretsiz — altıncı ayrı biçim yerine işaretin yokluğu. */
.tok[data-role="art"]  .w{text-decoration-line:none}
```

- [ ] **Step 4: Testi koştur, geçtiğini gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s19_dilbilgisi_rolleri_renkle_ayrilmaz
```
Beklenen: PASS.

- [ ] **Step 5: Pin ve commit**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --pin
git add src/mcp_server/vendor/assets/module-template.html src/mcp_server/vendor/PROVENANCE.json tests/test_pano_talimatname_borclari.py
git commit -m "fix(modül): dilbilgisi rolleri renk yerine alt çizgi biçimiyle ayrılır (S19)"
```

---

### Task 4: S11 — statik yüzeyde gölge yok

**Files:**
- Modify: `src/mcp_server/vendor/assets/module-template.html:249, 281, 318, 429, 517` ve satır 516 yorumu
- Modify: `src/mcp_server/vendor/PROVENANCE.json`
- Test: `tests/test_pano_talimatname_borclari.py`

**Interfaces:**
- Consumes: —
- Produces: `--tedy-shadow-card` tamamen kalkar; şablonda `rgba(` kalmaz.

- [ ] **Step 1: Başarısız testi yaz**

```python
def test_s11_modulde_statik_yuzey_golgesiz():
    metin = SABLON.read_text(encoding="utf-8")
    assert "--tedy-shadow-card" not in metin, "statik kart golgesi token'i hala tanimli (S11)"
    for secici in (".topbar{", ".stage{"):
        bas = metin.index(secici)
        govde = metin[bas:metin.index("}", bas)]
        assert "box-shadow" not in govde, f"{secici} hala golge tasiyor (S11)"
    # Geçici yüzey gölgesi Carbon'da ve S11'de meşrudur: kalmalı.
    bas = metin.index(".def-pop{")
    assert "box-shadow:0 2px 6px var(--cds-shadow)" in metin[bas:metin.index("}", bas)]


def test_d1_modulde_alfa_rengi_yok():
    metin = SABLON.read_text(encoding="utf-8")
    stil = metin[metin.index("<style>"):metin.index("</style>")]
    assert "rgba(" not in stil, "D1: stil blogunda alfa rengi var"
```

- [ ] **Step 2: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py -k "s11_modulde or d1_modulde"
```
Beklenen: ikisi de FAIL.

- [ ] **Step 3: Şablonu düzelt**

1. Satır 249 ve 281'deki `--tedy-shadow-card:0 1px 3px rgba(...),0 1px 2px rgba(...);` bildirimlerini **sil**.
2. Satır 318'deki `--tedy-shadow-card:none;` bildirimini **sil**.
3. Satır 429 `.topbar{…}`: `;box-shadow:var(--tedy-shadow-card)` kısmını sil. `border:1px solid var(--cds-border-subtle)` **kalır**.
4. Satır 517 `.stage{…}`: `box-shadow:var(--tedy-shadow-card);` kısmını sil. Kenarlık kalır.
5. Satır 516 yorumunu güncelle:

```css
/* .stage: derinlik katman token'ı ve 1 px kenarla kurulur; statik yüzey gölge almaz (S11, P4).
   Gölge yalnız geçici yüzeyde (tanım popover'ı) kalır. */
```

- [ ] **Step 4: Testleri koştur, geçtiğini gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py -k "s11_modulde or d1_modulde"
```
Beklenen: PASS.

- [ ] **Step 5: Kapıları koştur**

```bash
.venv/bin/python -m src.mcp_server.derleme --ornek QUIZ --cikti /tmp/quiz-s11.html
```
Beklenen: FAIL yok (`G-CARBON-GRID` zaten statik kart gölgesine FAIL veriyordu; bu değişiklik onu gevşetmiyor).

- [ ] **Step 6: Pin ve commit**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --pin
git add src/mcp_server/vendor/assets/module-template.html src/mcp_server/vendor/PROVENANCE.json tests/test_pano_talimatname_borclari.py
git commit -m "fix(modül): statik yüzey gölgesi ve iki rgba() kaldırıldı (S11, D1)"
```

---

### Task 5: Yarıçap token'a bağlanır

**Files:**
- Modify: `src/mcp_server/vendor/assets/module-template.html:532, 550`
- Modify: `src/mcp_server/vendor/PROVENANCE.json`
- Test: `tests/test_pano_talimatname_borclari.py`

**Interfaces:**
- Consumes: —
- Produces: Stil bloğunda `border-radius` değeri olarak düz px kalmaz.

- [ ] **Step 1: Başarısız testi yaz**

```python
def test_s10_modulde_yaricap_token_referansi():
    metin = SABLON.read_text(encoding="utf-8")
    stil = metin[metin.index("<style>"):metin.index("</style>")]
    duz = [d for d in re.findall(r"border-radius\s*:\s*([^;}\n]+)", stil)
           if "var(" not in d and d.strip() not in {"0", "50%", "inherit"}]
    assert not duz, f"token'a baglanmamis yaricap: {duz}"
    bas = stil.index(".def-pop{")
    assert "border-radius:var(--cds-border-radius-02)" in stil[bas:stil.index("}", bas)], \
        "popover Carbon'un 2 px'ine inmemis"
    bas = stil.index("mark.term{")
    assert "border-radius:var(--cds-border-radius-00)" in stil[bas:stil.index("}", bas)], \
        "satir ici terim vurgusu S10'un 'geri kalan 0' kovasinda degil"
```

- [ ] **Step 2: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s10_modulde_yaricap_token_referansi
```
Beklenen: FAIL — `mark.term` düz `4px`, `.def-pop` `-04`.

- [ ] **Step 3: Şablonu düzelt**

- Satır 532: `border-radius:4px` → `border-radius:var(--cds-border-radius-00)`
- Satır 550: `border-radius:var(--cds-border-radius-04)` → `border-radius:var(--cds-border-radius-02)`

- [ ] **Step 4: Testi koştur, geçtiğini gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py::test_s10_modulde_yaricap_token_referansi
```
Beklenen: PASS.

- [ ] **Step 5: Pin ve commit**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --pin
git add src/mcp_server/vendor/assets/module-template.html src/mcp_server/vendor/PROVENANCE.json tests/test_pano_talimatname_borclari.py
git commit -m "fix(modül): yarıçap token'a bağlandı (S10)"
```

---

### Task 6: Şablon px → rem

**Files:**
- Modify: `src/mcp_server/vendor/assets/module-template.html` (stil bloğu 23–1013)
- Create: `scripts/sablon_px_rem.py`
- Modify: `src/mcp_server/vendor/PROVENANCE.json`
- Test: `tests/test_pano_talimatname_borclari.py`

**Interfaces:**
- Consumes: Görev 2–5'in CSS değişiklikleri.
- Produces: Stil bloğunda ölçü birimleri rem; `.wrap{max-width:55rem}`.

- [ ] **Step 1: Başarısız testi yaz**

```python
# Kenarlık/saç çizgisi ve @media kırılma noktaları px kalır (medya sorgusunda rem kök boyunu değil
# tarayıcı varsayılanını kullanır); viewBox birimsizdir.
PX_IZINLI_OZELLIK = re.compile(r"(border(-[a-z]+)?|outline(-[a-z]+)?|text-decoration-thickness"
                               r"|text-underline-offset|box-shadow|stroke-width)\s*:")


def test_4k_sablon_olculeri_rem():
    metin = SABLON.read_text(encoding="utf-8")
    stil = metin[metin.index("<style>"):metin.index("</style>")]
    stil = re.sub(r"@media[^{]*\{", "{", stil)          # kırılma noktaları hariç
    stil = re.sub(r"/\*.*?\*/", "", stil, flags=re.S)    # yorumlar hariç
    kotu = []
    for bildirim in re.findall(r"[-a-z]+\s*:[^;}\n]*", stil):
        if "px" not in bildirim or PX_IZINLI_OZELLIK.match(bildirim):
            continue
        for deger in re.findall(r"(\d+(?:\.\d+)?)px", bildirim):
            if float(deger) > 3:
                kotu.append(bildirim.strip())
                break
    assert not kotu, f"rem'e cevrilmemis olcu ({len(kotu)}): {kotu[:8]}"


def test_4k_okuma_sutunu_rem():
    metin = SABLON.read_text(encoding="utf-8")
    bas = metin.index(".wrap{")
    assert "max-width:55rem" in metin[bas:metin.index("}", bas)], "okuma sutunu hala px"
```

- [ ] **Step 2: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py -k "4k_sablon or 4k_okuma"
```
Beklenen: ikisi de FAIL; birincisi 200'den fazla bildirim listeler.

- [ ] **Step 3: Dönüştürme betiğini yaz**

`scripts/sablon_px_rem.py`:

```python
"""Modül şablonunun stil bloğundaki ölçüleri px'ten rem'e çevirir (n px → n/16 rem).

Dokunulmayanlar: @media kırılma noktaları, kenarlık/saç çizgisi özellikleri, ≤ 3 px değerler,
SVG viewBox, yorumlar. Betik bir kez koşar; çıktı diff olarak okunur (plan Görev 6 Adım 4).
"""
import re
import sys
from pathlib import Path

SABLON = Path("src/mcp_server/vendor/assets/module-template.html")
KORUNAN = re.compile(r"(border(-[a-z]+)?|outline(-[a-z]+)?|text-decoration-thickness"
                     r"|text-underline-offset|box-shadow|stroke-width)\s*:")


def cevir_bildirim(bildirim: str) -> str:
    if KORUNAN.match(bildirim):
        return bildirim

    def bir(m):
        deger = float(m.group(1))
        if deger <= 3:
            return m.group(0)
        rem = deger / 16
        metin = f"{rem:.4f}".rstrip("0").rstrip(".")
        return f"{metin}rem"

    return re.sub(r"(\d+(?:\.\d+)?)px", bir, bildirim)


def main() -> int:
    metin = SABLON.read_text(encoding="utf-8")
    bas, son = metin.index("<style>"), metin.index("</style>")
    stil = metin[bas:son]
    parcalar, konum = [], 0
    # @media satırlarını ve yorumları atlayarak yalnız bildirimleri çevir.
    for m in re.finditer(r"(@media[^{]*\{)|(/\*.*?\*/)|([-a-z]+\s*:[^;}\n]*)", stil, flags=re.S):
        parcalar.append(stil[konum:m.start()])
        parcalar.append(m.group(0) if (m.group(1) or m.group(2)) else cevir_bildirim(m.group(3)))
        konum = m.end()
    parcalar.append(stil[konum:])
    SABLON.write_text(metin[:bas] + "".join(parcalar) + metin[son:], encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Betiği koştur ve diff'i oku**

```bash
.venv/bin/python scripts/sablon_px_rem.py
git diff --stat src/mcp_server/vendor/assets/module-template.html
git diff src/mcp_server/vendor/assets/module-template.html | head -120
```
Diff'i **gerçekten oku**: `@media (max-width:560px)` ve `(max-width:400px)` px kalmalı; `border:1px`, `border-bottom:3px` px kalmalı.

- [ ] **Step 5: Okuma sütununu ve kalan elle kalemleri düzelt**

```bash
grep -nE 'max-width:880px|max-width:540px|font-size:10px' src/mcp_server/vendor/assets/module-template.html
```
Betiğin atladığı ya da yuvarladığı kalemler elle: `.wrap{max-width:55rem}`, `.card{max-width:33.75rem}`, `.quest-map__label{font-size:.625rem}`.

- [ ] **Step 6: Testleri koştur, geçtiğini gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_pano_talimatname_borclari.py -k "4k_sablon or 4k_okuma"
```
Beklenen: PASS.

- [ ] **Step 7: Kapılar ve görsel kontrol**

```bash
.venv/bin/python -m src.mcp_server.derleme --ornek QUIZ --cikti /tmp/quiz-rem.html
```
Beklenen: FAIL yok. `/tmp/quiz-rem.html` tarayıcıda açılır; g10 ve g100'de yerleşim bozulmamış olmalı.

- [ ] **Step 8: Pin ve commit**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --pin
git add src/mcp_server/vendor/assets/module-template.html src/mcp_server/vendor/PROVENANCE.json scripts/sablon_px_rem.py tests/test_pano_talimatname_borclari.py
git commit -m "feat(modül): şablon ölçüleri rem tabanlı (4K hazırlığı)"
```

---

### Task 7: Pano kök ölçeğini bildirir (`rootPx`)

**Files:**
- Modify: `src/mcp_server/sablon.py:88` (`BRIDGE_JS` appearance dalı)
- Modify: `dashboard/src/utils/moduleBridge.ts:70-72`
- Modify: `dashboard/src/components/ModuleViewer.tsx` (`onFrameLoad` + resize)
- Test: `tests/test_modul_kok_olcegi.py`, `dashboard/tests/moduleBridge.test.ts`

**Interfaces:**
- Consumes: Görev 6'nın rem tabanlı şablonu (ölçek ancak rem'le işe yarar).
- Produces: `appearanceMessage(theme: ModuleTheme, rootPx?: number)` → `{type:'edupedia:appearance', v:1, theme, rootPx?}`; köprüde `adoptHostRootSize(rootPx)`.

- [ ] **Step 1: Başarısız köprü testini yaz**

`tests/test_modul_kok_olcegi.py`:

```python
"""Pano kök yazı boyunu bildirir; modül onu kıstırarak uygular (spec §10.2).

Köprü JS'i sablon.py'nin yamasıdır; burada node'da koşturulur.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.mcp_server import sablon

ARALIK = (12, 48)


def _kopru_calistir(cagrilar: str) -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node yok")
    govde = re.search(r"function adoptHostRootSize\(rootPx\)\{.*?\n  \}", sablon.BRIDGE_JS, re.S)
    assert govde, "adoptHostRootSize köprüde yok"
    kod = "\n".join([
        "const document={documentElement:{style:{}}};",
        govde.group(0),
        cagrilar,
    ])
    return subprocess.run([node, "-e", kod], capture_output=True, text=True,
                          check=True, timeout=30).stdout


def test_gecerli_deger_uygulanir():
    out = _kopru_calistir("adoptHostRootSize(32);"
                          "process.stdout.write(String(document.documentElement.style.fontSize));")
    assert out == "32px"


@pytest.mark.parametrize("deger", ["NaN", '"32"', "Infinity", "-5", "1e9", "null", "undefined", "{}"])
def test_dusmanca_deger_yok_sayilir_ya_da_kistirilir(deger):
    out = _kopru_calistir(f"adoptHostRootSize({deger});"
                          "process.stdout.write(String(document.documentElement.style.fontSize||''));")
    assert "NaN" not in out, f"{deger} için NaNpx yazıldı"
    if out:
        sayi = float(out.removesuffix("px"))
        assert ARALIK[0] <= sayi <= ARALIK[1], f"{deger} aralık dışına çıktı: {out}"
```

- [ ] **Step 2: Testi koştur, düştüğünü gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_modul_kok_olcegi.py
```
Beklenen: FAIL — `adoptHostRootSize` yok.

- [ ] **Step 3: Köprüye uygulayıcıyı ekle**

`src/mcp_server/sablon.py`, `BRIDGE_JS` içinde, appearance dalından önce:

```javascript
  /* Panonun kök yazı boyu (spec §10.2). İsteğe bağlıdır: mesaj yoksa modül 16 px'te kalır.
     Okurun tarayıcı tercihi panonun clamp() tabanında (100%) zaten var, hesaplanmış değer onu taşır. */
  function adoptHostRootSize(rootPx){
    const n = typeof rootPx === "number" ? rootPx : NaN;
    if(!isFinite(n)) return false;
    const kistirilmis = Math.min(48, Math.max(12, n));
    document.documentElement.style.fontSize = kistirilmis + "px";
    return true;
  }
```

Satır 88'deki dalı güncelle:

```javascript
        if(d.type === "edupedia:appearance"){ adoptHostTheme(d.theme); adoptHostRootSize(d.rootPx); return; }
```

- [ ] **Step 4: Testi koştur, geçtiğini gör**

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_modul_kok_olcegi.py
```
Beklenen: PASS (9 test).

- [ ] **Step 5: Tema değişimi ölçeği sıfırlamıyor (Review Focus)**

`tests/test_modul_kok_olcegi.py` sonuna:

```python
SABLON_YOLU = Path("src/mcp_server/vendor/assets/module-template.html")


def test_tema_degisimi_kok_olcegini_sifirlamaz():
    """applyTheme yalnız data-theme yazar; style.fontSize'a dokunmaz (spec §10.6)."""
    kaynak = SABLON_YOLU.read_text(encoding="utf-8")
    bas = kaynak.index("function applyTheme(next){")
    govde = kaynak[bas:kaynak.index("\n  }", bas)]
    assert "fontSize" not in govde, "applyTheme kök yazı boyuna dokunuyor"
```

```bash
unshare -rn .venv/bin/python -m pytest -q tests/test_modul_kok_olcegi.py::test_tema_degisimi_kok_olcegini_sifirlamaz
```
Beklenen: PASS (mevcut `applyTheme` yalnız `setAttribute` yapıyor).

- [ ] **Step 6: `G-BRIDGE` regresyon testi (kapı değişmez)**

`G-BRIDGE` mesaj **tiplerini** denetler, alanları değil (`gates_ek.py:127-130`) ve
`edupedia:appearance` zaten `OPTIONAL_BRIDGE_TYPES`'tadır (`gates_ek.py:17`). `rootPx` yeni bir tip
değil, bir alandır — **kapıya dokunulmaz.** Geçtiğini sabitleyen test, `tests/test_modul_kok_olcegi.py`
sonuna:

```python
def test_g_bridge_root_px_ile_gecer():
    """rootPx bir alandir, yeni mesaj tipi degil: kapi FAIL vermemeli."""
    from src.mcp_server import derleme
    html = derleme.ornek_derle("QUIZ") if hasattr(derleme, "ornek_derle") else None
    if html is None:
        pytest.skip("ornek derleyici yuzeyi yok; Adim 7'deki CLI kapi raporu gecerli")
    assert "adoptHostRootSize" in html
    assert "edupedia:appearance" in html
```

Not: bu test derleyici yüzeyine bağlıdır; asıl kapı kanıtı Adım 7'nin CLI raporudur.

- [ ] **Step 7: Kapıları koştur**

```bash
.venv/bin/python -m src.mcp_server.derleme --ornek QUIZ --cikti /tmp/quiz-bridge.html
```
Beklenen: 18 kapıda FAIL yok, `G-BRIDGE` PASS.

- [ ] **Step 8: Pano tarafını yaz (başarısız birim testi)**

`dashboard/tests/moduleBridge.test.ts`:

```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { appearanceMessage } from '../src/utils/moduleBridge'

test('appearance mesajı kök yazı boyunu taşır', () => {
  assert.deepEqual(appearanceMessage('g10', 32),
    { type: 'edupedia:appearance', v: 1, theme: 'g10', rootPx: 32 })
})

test('kök boyu verilmezse alan hiç yazılmaz (geriye uyum)', () => {
  assert.deepEqual(appearanceMessage('g10'),
    { type: 'edupedia:appearance', v: 1, theme: 'g10' })
})
```

```bash
cd dashboard && npm run test:birim
```
Beklenen: FAIL — `appearanceMessage` ikinci argümanı almıyor.

- [ ] **Step 9: `moduleBridge.ts`'i düzelt**

```ts
/** Parent → module: which Carbon theme to render in, and the host's computed root font size.
 *  rootPx is optional: without it the module stays at 16px (standalone and older hosts). */
export function appearanceMessage(theme: ModuleTheme, rootPx?: number) {
  return rootPx === undefined
    ? ({ type: 'edupedia:appearance', v: 1, theme } as const)
    : ({ type: 'edupedia:appearance', v: 1, theme, rootPx } as const)
}
```

- [ ] **Step 10: Testi koştur, geçtiğini gör**

```bash
cd dashboard && npm run test:birim
```
Beklenen: PASS.

- [ ] **Step 11: `ModuleViewer`'ı bağla**

`onFrameLoad` içinde kök boyunu oku ve gönder; pencere yeniden boyutlanınca değer değiştiyse yeniden gönder:

```tsx
const kokPx = () => parseFloat(getComputedStyle(document.documentElement).fontSize) || 16

const gonderGorunum = useCallback(() => {
  frameRef.current?.contentWindow?.postMessage(appearanceMessage(DASHBOARD_THEME, kokPx()), '*')
}, [])

useEffect(() => {
  let son = kokPx()
  let bekleyen = 0
  const olcVeGonder = () => {
    bekleyen = 0
    const simdi = kokPx()
    if (simdi !== son) { son = simdi; gonderGorunum() }   // değişmediyse gönderme
  }
  const onResize = () => { if (!bekleyen) bekleyen = requestAnimationFrame(olcVeGonder) }
  window.addEventListener('resize', onResize)
  return () => { window.removeEventListener('resize', onResize); if (bekleyen) cancelAnimationFrame(bekleyen) }
}, [gonderGorunum])
```

`onFrameLoad` artık `gonderGorunum()` çağırır.

- [ ] **Step 12: e2e testi yaz**

Çerçeve ayrı ve opak kökenli bir belgedir; içine Playwright'tan ölçüm yapmak bilet akışını da
gerektirir. Bu yüzden e2e **mesajın girdisini ve çerçeve geometrisini** ölçer (uygulayıcıyı Adım 1–4'ün
node testleri, görsel sonucu Görev 6 Adım 7 kapsar).

`dashboard/tests/e2e/modul-4k.spec.ts`:

```ts
import { test, expect } from '@playwright/test'
import { sabitAc } from './_gorsel-yardim'

const kok = async (page: import('@playwright/test').Page) =>
  page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize))

test('modül çerçevesi ve kök ölçek 3840 px&apos;te iki katı', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 })
  await sabitAc(page, '/moduller')
  const kok1920 = await kok(page)
  expect(kok1920).toBeCloseTo(16, 1)

  await page.setViewportSize({ width: 3840, height: 2160 })
  const kok3840 = await kok(page)
  expect(kok3840).toBeCloseTo(32, 1)

  // Yana kaydırma yok (ekran-4k.spec.ts ile aynı kapı).
  const tasma = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(tasma).toBeLessThanOrEqual(1)
})
```

Çalıştır:

```bash
cd dashboard && env -u ANTHROPIC_API_KEY npx playwright test modul-4k
```
Beklenen: PASS. (`/moduller` yayınlanmış modül taşımıyorsa `sabitAc`'ın sahte kataloğu kullanılır;
çerçeveli görünüm için `moduller.spec.ts`'in bilet sahtesi örnek alınır.)

```bash
cd dashboard && env -u ANTHROPIC_API_KEY npx playwright test modul-4k
```
Beklenen: PASS.

- [ ] **Step 13: Commit**

```bash
git add src/mcp_server/sablon.py tests/test_modul_kok_olcegi.py \
        dashboard/src/utils/moduleBridge.ts dashboard/src/components/ModuleViewer.tsx \
        dashboard/tests/moduleBridge.test.ts dashboard/tests/e2e/modul-4k.spec.ts
git commit -m "feat(modül): pano kök yazı ölçeğini bildirir, modül izler (4K eşliği)"
```

---

### Task 8: Belgeler

**Files:**
- Modify: `docs/tedy-ui-ux-talimatnamesi.md` (§9.3 Sütun ve Gölge satırları, §9.4 ve altındaki cümle, §11 S10/S11/S19 ve "4 px" satırları, §13 B2, değişiklik kaydı)
- Modify: `src/mcp_server/vendor/references/tedy-integration.md` (§2 `rootPx`, §4 köşe ve gölge)
- Modify: `src/mcp_server/vendor/references/color-system.md` (`--viz-*` rolü)
- Modify: `src/mcp_server/vendor/PROVENANCE.json`
- Modify: `CLAUDE.md` (modül şablonu satırı)

**Interfaces:**
- Consumes: Görev 2–7'nin kararları.
- Produces: Geri alınan her karar yeni gerekçe ve 2026-10-15 tarihiyle yazılı.

- [ ] **Step 1: Talimatname satırlarını yeniden yaz**

Satır silinmez, güncellenir:
- §11 **S19**: modül grafikleri nötr rampa; kategoriyi etiket ve alt çizgi biçimi taşır; `--viz-*` ders ailesi değil; kaskad onarıldı (koyu palet artık ölü kod değil).
- §11 **S11**: `.topbar`/`.stage` gölgesi kalktı; "modülün kendi kararı" ibaresi düşer; geçici yüzey gölgesi kalır.
- §11 "4 px" satırı: `.def-pop` 2 px'e indi, `mark.term` 0'a; ikisi de token referansı.
- §9.3 "Sütun" satırı: 880 px → 55rem, modül rem tabanlı.
- §9.3 "Gölge" satırı: pano ve modül aynı — yeni statik gölge yok.
- §9.4 altındaki "Tasarım açısından akan **tek şey** temadır" cümlesi: artık tema **ve** kök ölçek akar.
- §13 **B2**: modül tarafı kapandı; pano tarafı açık kalır.
- §11'e yeni satır: modülün kök ölçeği panodan gelir (sapma değil, eşlik).

- [ ] **Step 2: Vendored referansları güncelle**

- `tedy-integration.md` §2: `edupedia:appearance`'ın `rootPx` alanı, 12–48 kıstırma, mesaj yoksa 16 px.
- `tedy-integration.md` §4: statik yüzey gölgesiz; yarıçap token tablosu.
- `color-system.md`: `--viz-*` nötr rampadır, kategori taşıyıcısı değil.

- [ ] **Step 3: CLAUDE.md'yi güncelle**

"Şablonda oyunlaştırma yok" maddesinin yanına: şablon rem tabanlıdır ve kök ölçeği panodan `rootPx` ile alır; `--viz-*` nötr rampadır; statik yüzey gölgesizdir.

- [ ] **Step 4: Pin, tüm süit, commit**

```bash
.venv/bin/python -m src.mcp_server.vendor_sync --pin
unshare -rn .venv/bin/python -m pytest -q
.venv/bin/python -m src.mcp_server.derleme --ornek QUIZ --cikti /tmp/quiz-son.html
git add docs/tedy-ui-ux-talimatnamesi.md src/mcp_server/vendor/references/tedy-integration.md \
        src/mcp_server/vendor/references/color-system.md src/mcp_server/vendor/PROVENANCE.json CLAUDE.md
git commit -m "docs(modül): S10/S11/S19 ve 4K eşliği kararları yazıldı"
```
Beklenen: süitte bu planla ilgisiz iki bilinen düşük (`test_year_rollover_sync.py::test_archive_failure_in_main_does_not_abort_the_sync` kullanıcının WIP'inden, `test_mcp_server.py::…[edupedia_derle]` yalıtımda geçiyor) dışında yeşil; 18 kapıda FAIL yok.
