"""Talimatname §13 debts closed in dashboard code, pinned so they stay closed.

Each test names its debt. Tedy Books is out of scope throughout (its own world,
surface designs §4.11): `BookReader*.scss`, the Books block at the end of
`ted-theme.scss`, and the Books/reader TSX files. The old assistant UI went with
plan Görev 21 (2026-10-11); nothing is excluded for it any more.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard" / "src"
THEME = DASH / "theme" / "ted-theme.scss"
BOOKS_HEADER = "   Tedy Books\n"


def _yorumsuz_stil(metin: str) -> str:
    metin = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), metin, flags=re.S)
    return re.sub(r"(?m)(^|[ \t])//[^\n]*", lambda m: " " * len(m.group(0)), metin)


def _stiller() -> list[tuple[str, str]]:
    """Every dashboard stylesheet under src/, Books excluded (B13: rglob, not one folder)."""
    out = []
    for p in sorted(DASH.rglob("*.scss")):
        if p.name.startswith("BookReader"):
            continue
        metin = p.read_text(encoding="utf-8")
        if p == THEME:
            kesim = metin.rindex("/*", 0, metin.index(BOOKS_HEADER))
            son = metin.index("end of the Tedy Books block")  # B14: the rules after the Books block are pano again
            metin = metin[:kesim] + re.sub(r"[^\n]", " ", metin[kesim:son]) + metin[son:]
        out.append((str(p.relative_to(DASH)), _yorumsuz_stil(metin)))
    return out


def _kaynaklar() -> list[Path]:
    out = []
    for p in sorted(list(DASH.rglob("*.tsx")) + list(DASH.rglob("*.ts"))):
        if "Book" in p.name or "Reader" in p.name or p.name.endswith(".d.ts"):
            continue
        out.append(p)
    return out


def _yorumsuz_kod(metin: str) -> str:
    metin = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), metin, flags=re.S)
    metin = re.sub(r"\{/\*.*?\*/\}", lambda m: " " * len(m.group(0)), metin, flags=re.S)
    return re.sub(r"(?m)(^|[^:'\"`])//[^\n]*", lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), metin)


def _satir(metin: str, konum: int) -> int:
    return metin.count("\n", 0, konum) + 1


# ── B70 (S38): capitals belong neither to CSS nor to the source ─────────────

def test_b70_buyuk_harf_donusumu_yok():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"text-transform:\s*uppercase", metin):
            ihlal.append(f"{ad}:{_satir(metin, m.start())}")
    assert not ihlal, "text-transform: uppercase (S38, B70):\n" + "\n".join(ihlal)


# Acronyms and HTTP verbs keep their own spelling; the portal's own caps day names are data it is matched against.
KISALTMA = {"TEDY", "TED", "PDF", "POST", "GET", "PUT", "PATCH", "DELETE", "ÖGEP", "SEBIT", "SEBİT", "PDR",
            "DKAB", "EBA", "MEBİ", "MEB", "AI", "OK", "URL", "ID", "API", "HTTP", "JSON", "SSE", "CSS", "DOM",
            "PAZARTESİ", "PAZARTESI", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR", "XP"}


def test_b70_kaynakta_tumu_buyuk_dizge_yok():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for m in re.finditer(r"(['\"`>])([A-ZÇĞİÖŞÜ]{3,}(?:\s+[A-ZÇĞİÖŞÜ]{2,})*)(?=['\"`<])", temiz):
            kelimeler = m.group(2).split()
            if all(k in KISALTMA for k in kelimeler):
                continue
            ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, m.start())}  {m.group(2)}")
    assert not ihlal, "kaynakta tümü büyük harf dizge (S38, B70):\n" + "\n".join(ihlal)


# ── B41 (S38, İ9): visible labels are sentence case ──────────────────────────

# Proper names keep their capitals.
OZEL_AD = {"Tedy Books", "TED Rönesans Koleji", "Rönesans Koleji", "Carbon AI", "Google Drive", "Microsoft Teams",
           "Ayşe Yılmaz", "Öğrenci Gelişim Programı"}  # an example teacher name; ÖGEP spelled out
_KELIME = r"[A-ZÇĞİÖŞÜ][a-zçğıöşüâîû]+"
_BASLIK_DUZENI = re.compile(rf"{_KELIME}(?:\s+{_KELIME})+")
_ETIKET_PROP = r"(?:title|label|labelText|titleText|aria-label|description|primaryButtonText|secondaryButtonText|" \
               r"iconDescription|placeholder|helperText|eyebrow|actionLabel)"


def _gorunur_metinler(temiz: str):
    """JSX text between tags, and string values of the label props."""
    for m in re.finditer(r">([^<>{}]+)<", temiz):
        yield m.start(1), m.group(1)
    for m in re.finditer(rf"\b{_ETIKET_PROP}=\"([^\"]+)\"", temiz):
        yield m.start(1), m.group(1)
    for m in re.finditer(rf"\b{_ETIKET_PROP}=\{{'([^']+)'\}}", temiz):
        yield m.start(1), m.group(1)
    # Object fields that become a section title or a label, e.g. renderAccordionSection({ title: 'Aktif ödevler' }).
    for m in re.finditer(r"\b(?:title|label):\s*'([^']+)'", temiz):
        yield m.start(1), m.group(1)


def test_b41_gorunur_etiketler_cumle_duzeninde():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for konum, metin in _gorunur_metinler(temiz):
            for m in _BASLIK_DUZENI.finditer(metin):
                if any(m.group(0) in ad or ad in metin for ad in OZEL_AD):
                    continue
                # A Title Case run that starts the string is a sentence-case label only when its first word is
                # alone; "Öğretmen Adı" is two capitalised words.
                ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, konum)}  {m.group(0)}")
    assert not ihlal, "başlık düzeninde görünür etiket (S38, B41):\n" + "\n".join(ihlal)


def test_b41_tek_cikis_fiili_ve_tek_tarih_bicimi():
    header = _yorumsuz_kod((DASH / "components" / "DashboardHeader.tsx").read_text(encoding="utf-8"))
    assert 'aria-label="Çıkış yap"' in header
    assert "toLocaleString" not in header, "saniyeli ikinci tarih biçimi (B41)"
    assert 'labelA="Odak"' not in header, "odak anahtarı labelText + hideLabel ile adlanır (B41)"
    assert not re.search(r"[>\"']Son (?:Başarılı Tam )?Sync|Senkron Sağlığı", header), "tek sözlük: senkron (B41)"


# ── B32 ([3.2-2]): a component's token stays in its component ────────────────

def test_b32_bilesen_tokeni_odunc_alinmaz():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"var\(--cds-(?:notification|button)-[a-z-]+", metin):
            ihlal.append(f"{ad}:{_satir(metin, m.start())}  {m.group(0)})")
    assert not ihlal, "bildirim/düğme token'ı bileşeni dışında (B32):\n" + "\n".join(ihlal)


# ── B22 (D3, D4): no browser alert ───────────────────────────────────────────

def test_b22_tarayici_uyarisi_yok():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for m in re.finditer(r"\bwindow\.(?:alert|confirm|prompt)\(|(?<![\w.])alert\(", temiz):
            ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, m.start())}")
    assert not ihlal, "tarayıcı uyarısı (B22):\n" + "\n".join(ihlal)


# ── B38 ([3.7-1]): no emoji standing in for an icon ──────────────────────────

_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def test_b38_emoji_ikon_yerine_kullanilmaz():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for m in _EMOJI.finditer(temiz):
            ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, m.start())}  {m.group(0)}")
    assert not ihlal, "emoji ikon yerine (B38):\n" + "\n".join(ihlal)


# ── B10 (§3.4): one way to write Carbon's md breakpoint ──────────────────────

def test_b10_md_kirilimi_tek_yazimla():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"@media[^{]*\b42rem\b", metin):
            ihlal.append(f"{ad}:{_satir(metin, m.start())}  {m.group(0).strip()}")
    assert not ihlal, "md kırılımı 42rem yazılmış; tek yazım 671px/672px (B10):\n" + "\n".join(ihlal)


# ── the module template (vendor; changed only through vendor_sync --pin) ─────

SABLON = ROOT / "src" / "mcp_server" / "vendor" / "assets" / "module-template.html"


def test_b70_modul_sablonunda_buyuk_harf_yok():
    metin = SABLON.read_text(encoding="utf-8")
    assert "text-transform:uppercase" not in metin.replace(" ", ""), "modül şablonunda büyük harf dönüşümü (B70)"
    basliklar = re.findall(r'segHead\(s,"([^"]+)"', metin)
    assert basliklar
    baslik_duzeni = [b for b in basliklar if _BASLIK_DUZENI.search(b)]
    assert not baslik_duzeni, f"modül kaşları başlık düzeninde (S38): {baslik_duzeni}"


def test_b42_modulde_denenmis_kelime_okunur_kalir():
    """A tried wrong word is content (B42): aria-disabled, not `disabled`, and not faded with inline opacity (B34)."""
    metin = SABLON.read_text(encoding="utf-8")
    assert 'btn.disabled=true; btn.style.opacity=".4"' not in metin
    assert 'tried=true; btn.setAttribute("aria-disabled","true");' in metin
    assert 'if(btn.getAttribute("aria-disabled")==="true") return;' in metin


# ── B44 (İ9, D4): Carbon's English default names are replaced ───────────────

def _acilis_etiketleri(metin: str, ad: str):
    """Each `<Ad …>` / `<Ad … />` opening tag, braces balanced (props may hold arrow functions with `>`)."""
    for m in re.finditer(rf"<{ad}\b", metin):
        i, derinlik = m.end(), 0
        while i < len(metin):
            c = metin[i]
            if c == "{":
                derinlik += 1
            elif c == "}":
                derinlik -= 1
            elif c == ">" and derinlik == 0:
                break
            i += 1
        yield m.start(), metin[m.start(): i + 1]


def test_b44_carbon_varsayilan_ingilizce_adlar_turkcelesir():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for ad, gerekli in (("InlineNotification", "statusIconDescription"), ("InlineLoading", "iconDescription"),
                            ("Modal", "closeButtonLabel")):
            for konum, etiket in _acilis_etiketleri(temiz, ad):
                if gerekli not in etiket:
                    ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, konum)}  <{ad}> {gerekli} yok")
                if ad == "InlineNotification" and "hideCloseButton" not in etiket and "aria-label=" not in etiket:
                    ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, konum)}  <{ad}> kapatma düğmesi adsız")
    assert not ihlal, "Carbon'un İngilizce varsayılan adı (B44):\n" + "\n".join(ihlal)


# ── 4th round (2026-10-11): the CSS passes ───────────────────────────────────

def _bloklar(metin: str):
    """Yield (headers, own_body, offset) for every `{…}` block: headers are the enclosing selector/at-rule
    texts from outermost to this one, own_body the block's declarations without its nested blocks."""
    yigin: list[tuple[str, int, list[str]]] = []
    bas = 0
    for i, c in enumerate(metin):
        if c == "{":
            baslik = metin[bas:i].strip().split(";")[-1].strip()
            yigin.append((baslik, i, []))
            bas = i + 1
        elif c == "}":
            if not yigin:
                bas = i + 1
                continue
            baslik, acilis, govde = yigin.pop()
            govde.append(metin[bas:i])
            yield [y[0] for y in yigin] + [baslik], "".join(govde), acilis
            bas = i + 1
        elif c == ";" and yigin:
            yigin[-1][2].append(metin[bas:i + 1])
            bas = i + 1


_KOSE_IZNI = re.compile(r"^(0|50%|999px|var\(--ted-radius-(card|pill)\)|"
                        r"var\(--ted-radius-card\) var\(--ted-radius-card\) 0 0)$")


def test_b1_kose_yalniz_kart_hap_daire_ya_da_kare():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"border(?:-[a-z]+)*-radius:\s*([^;]+);", metin):
            if not _KOSE_IZNI.match(m.group(1).strip()):
                ihlal.append(f"{ad}:{_satir(metin, m.start())}  {m.group(0)}")
        if "--ted-radius-sm" in metin:
            ihlal.append(f"{ad}: --ted-radius-sm (kaldırıldı)")
    assert not ihlal, "ara köşe değeri (S10, B1):\n" + "\n".join(ihlal)


def test_b2_statik_yuzey_golge_almaz():
    """S11: a shadow only on a transient surface (a popover, the opened phone nav)."""
    gecici = re.compile(r"popover|side-nav--expanded")
    ihlal = []
    for ad, metin in _stiller():
        for basliklar, govde, konum in _bloklar(metin):
            for m in re.finditer(r"box-shadow:\s*([^;]+);", govde):
                deger = m.group(1).strip()
                if deger.startswith(("none", "inset", "0 0 0")):
                    continue  # an inset edge or a focus ring, not elevation
                if not gecici.search(" ".join(basliklar)):
                    ihlal.append(f"{ad}:{_satir(metin, konum)}  {basliklar[-1]} {{ box-shadow: {deger} }}")
            if re.search(r"var\(--ted-shadow-card", govde):
                ihlal.append(f"{ad}:{_satir(metin, konum)}  {basliklar[-1]} --ted-shadow-card")
    assert not ihlal, "statik gölge (S11, B2):\n" + "\n".join(ihlal)


def test_b3_hover_any_hover_icinde():
    ihlal = []
    for ad, metin in _stiller():
        for basliklar, _govde, konum in _bloklar(metin):
            if not any(":hover" in b for b in basliklar if not b.startswith("@")):
                continue
            if not any(b.startswith("@media") and "any-hover: hover" in b for b in basliklar):
                ihlal.append(f"{ad}:{_satir(metin, konum)}  {basliklar[-1]}")
    assert not ihlal, "@media (any-hover: hover) dışında :hover (S17, B3):\n" + "\n".join(sorted(set(ihlal)))


def test_b24_kademe_yok_ve_azaltilmis_harekette_gecikme_sifir():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"(animation|transition)-delay:\s*([^;]+);", metin):
            if m.group(2).replace("!important", "").strip() not in ("0s", "0ms"):
                ihlal.append(f"{ad}:{_satir(metin, m.start())}  {m.group(0)}")
    tema = _yorumsuz_stil(THEME.read_text(encoding="utf-8"))
    azaltma = tema[tema.index("@media (prefers-reduced-motion: reduce)"):]
    azaltma = azaltma[: azaltma.index("\n}\n")]
    assert "animation-delay: 0s !important" in azaltma, "azaltılmış hareket gecikmeyi sıfırlamıyor (B24)"
    assert ".stack-sm > *" not in tema, "liste satırları kademeyle giriyor (S26, B24)"
    assert not ihlal, "sıfırdan büyük gecikme (S26, B24):\n" + "\n".join(ihlal)


def test_b33_rol_tokeni_palet_literaline_yazilmaz():
    tema = _yorumsuz_stil(THEME.read_text(encoding="utf-8"))
    assert "--ted-highlight-active: var(--cds-highlight)" in tema
    assert "--ted-highlight-today: var(--cds-interactive)" in tema
    ihlal = []
    for ad, metin in _stiller():
        if ad.endswith("_subjects.scss"):
            continue  # generated subject palette steps (scripts/gen_subject_themes.py), not roles
        # g10: blue-20 is $highlight, blue-60 $interactive, gray-10 $layer-02 / $background. The brand band's own
        # two steps (--ted-color-brand-*) are the Tedy layer, not a role.
        for m in re.finditer(r"colors\.\$(blue-20|blue-60|gray-10)\b", metin):
            satir = metin[metin.rfind("\n", 0, m.start()) + 1: m.start()]
            if "--ted-color-brand-" in satir:
                continue
            ihlal.append(f"{ad}:{_satir(metin, m.start())}  {m.group(0)}")
    assert not ihlal, "rol token'ıyla aynı palet literali (B33):\n" + "\n".join(ihlal)


def test_b35_elle_harf_araligi_yok_ve_yuklenen_agirliklar():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"letter-spacing:", metin):
            ihlal.append(f"{ad}:{_satir(metin, m.start())}")
    assert not ihlal, "elle letter-spacing; type-style kendi izlemesini taşır (B35):\n" + "\n".join(ihlal)
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    for aile in ("IBM+Plex+Sans", "IBM+Plex+Mono"):
        m = re.search(rf"family={re.escape(aile)}:[a-z,]*@([0-9;,]+)", html)
        assert m, aile
        agirliklar = {int(p.split(",")[-1]) for p in m.group(1).split(";")}
        assert agirliklar <= {300, 400, 600}, f"{aile} gereksiz ağırlık yüklüyor: {sorted(agirliklar)} (B35)"


CARBON_KIRILIMLARI = {"671px", "672px", "1055px", "1056px", "65.98rem", "66rem"}


def test_b37_yalniz_carbon_kirilimlari():
    ihlal = []
    for ad, metin in _stiller():
        for m in re.finditer(r"@media([^{]*)\{", metin):
            for a, b in re.findall(r"(?:min|max)-width:\s*([\d.]+(?:px|rem))|width\s*[<>]=?\s*([\d.]+(?:px|rem))",
                                   m.group(1)):
                if (a or b) not in CARBON_KIRILIMLARI:
                    ihlal.append(f"{ad}:{_satir(metin, m.start())}  {m.group(0).strip()}")
    assert not ihlal, "Carbon'un olmayan kırılımı (B37, §3.4):\n" + "\n".join(ihlal)


def test_b39_mikro_etkilesim_hizli_ve_azaltma_odak_kipini_yener():
    tema = _yorumsuz_stil(THEME.read_text(encoding="utf-8"))
    assert "--ted-duration-fast: #{motion.$duration-fast-02};" in tema
    sonra = tema[tema.index(".app-shell-content--focus {"):]
    assert re.search(r"@media \(prefers-reduced-motion: reduce\) \{\s*\.app-shell-content--focus \*", sonra), \
        "azaltılmış hareket odak kipinin !important hızlandırmasından sonra ve daha özgül yazılmalı (B39)"
    kaynak = (DASH / "components" / "SourcePanel.tsx").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in kaynak, "JS yumuşak kaydırması azaltılmış harekete bakmıyor (B39)"


def test_b34_durum_opaklikla_cizilmez():
    """S24, S31: a state is a token, a mark or a word — opacity only animates (inside @keyframes)."""
    ihlal = []
    for ad, metin in _stiller():
        for basliklar, govde, konum in _bloklar(metin):
            if any(b.startswith("@keyframes") for b in basliklar):
                continue
            for m in re.finditer(r"(?<![-\w])opacity:\s*([^;]+);", govde):
                if m.group(1).strip() not in ("1", "0"):
                    ihlal.append(f"{ad}:{_satir(metin, konum)}  {basliklar[-1]} {{ opacity: {m.group(1)} }}")
    assert not ihlal, "opaklıkla durum (S24, B34):\n" + "\n".join(ihlal)


def test_b38_ikon_carbon_boyunda_ve_metnin_renginde():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for m in re.finditer(r"<[A-Z]\w*\s[^>]*?\bsize=\{(\d+)\}", temiz):
            if int(m.group(1)) not in (16, 20, 24, 32):
                ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, m.start())}  size={{{m.group(1)}}}")
    assert not ihlal, "Carbon boyu dışı ikon (16/20/24/32; B38):\n" + "\n".join(ihlal)
    tema = _yorumsuz_stil(THEME.read_text(encoding="utf-8"))
    for secici in (".dashboard-card__title svg", ".calendar-legend__icon", ".calendar-event__icon"):
        blok = tema[tema.index(secici + " {"):]
        blok = blok[: blok.index("}")]
        assert "icon-secondary" not in blok, f"{secici}: ikon metnin rengini alır (B38)"
    assert "border-left: 4px" not in tema, "şerit 3 px ([3.5-3], B38)"


_DURUM_ISARETI = ("Süresi doldu", "Henüz girilmedi", "Devam ediyor", "Bekliyor", "Önceki öğretim yılı",
                  "countdown.text", "status.label", "cfg.label")


def test_b16_durum_etiketi_ikon_tasir():
    """S4: a status Tag carries an icon with its word (Carbon draws renderIcon only from md up, so sm Tags take the
    icon as a child)."""
    ihlal, sayi = [], 0
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for m in re.finditer(r"<Tag\b(.*?)</Tag>", temiz, flags=re.S):
            blok = m.group(0)
            if not any(isaret in blok for isaret in _DURUM_ISARETI):
                continue
            sayi += 1
            if not re.search(r"<[A-Za-z][\w.]*\s+size=\{16\}|renderIcon=", blok):
                ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, m.start())}")
    assert sayi >= 8, f"durum etiketi bulunamadı ({sayi})"
    assert not ihlal, "ikonsuz durum etiketi (S4, B16):\n" + "\n".join(ihlal)


def test_b58_olumlu_eylem_birincilsiz_secondary_degil_ve_dis_baglanti_soyler():
    ihlal = []
    for p in _kaynaklar():
        temiz = _yorumsuz_kod(p.read_text(encoding="utf-8"))
        for konum, etiket in _acilis_etiketleri(temiz, "Button"):
            # The floating assistant launcher is the one named exception (S12 side-panel launcher, B17).
            if 'kind="secondary"' in etiket and p.name != "AsistanBaslatici.tsx":
                ihlal.append(f"{p.relative_to(DASH)}:{_satir(temiz, konum)}  kind=\"secondary\"")
    for ad, dosya in (("Kaynağında aç", "components/patterns/EkBaglantisi.tsx"),
                      ("Eki aç", "components/Announcements.tsx")):
        metin = (DASH / dosya).read_text(encoding="utf-8")
        i = metin.rindex(ad)   # the JSX, not a comment above it
        assert "Launch" in metin[max(0, i - 300): i + 120], f"{dosya}: \"{ad}\" sayfadan çıktığını söylemiyor (B58)"
    assert not ihlal, "birincilsiz secondary (B58, §4.2):\n" + "\n".join(ihlal)


def test_b74_baslik_tokeni_agirligini_tasir():
    ihlal = []
    for ad, metin in _stiller():
        for basliklar, govde, konum in _bloklar(metin):
            if re.search(r"type-style\('heading-0[3-7]'", govde) and "font-weight" in govde:
                ihlal.append(f"{ad}:{_satir(metin, konum)}  {basliklar[-1]}")
    assert not ihlal, "heading-03…07 bloğunda font-weight (S44, B74):\n" + "\n".join(ihlal)


def test_b4_b12_statik_jsx_denetimi_eslint_te():
    cfg = (ROOT / "dashboard" / "eslint.config.js").read_text(encoding="utf-8")
    assert "jsxA11y.flatConfigs.recommended" in cfg, "jsx-a11y önerilen set (B12)"
    assert "no-restricted-syntax" in cfg and 'name.name="style"' in cfg, "statik style literali kuralı (B4, B12)"
    assert '"eslint-plugin-jsx-a11y"' in (ROOT / "dashboard" / "package.json").read_text(encoding="utf-8")


def test_b14_stylelint_kose_boyut_gecikme_kurallari():
    cfg = (ROOT / "dashboard" / "stylelint.config.mjs").read_text(encoding="utf-8")
    assert "declaration-property-value-allowed-list" in cfg and "radius" in cfg and "delay" in cfg
    assert "declaration-property-value-disallowed-list" in cfg and "inline-size" in cfg
    tema = THEME.read_text(encoding="utf-8")
    for yon in ("disable", "enable"):
        satir = next(s for s in tema.splitlines() if s.startswith(f"/* stylelint-{yon} carbon/theme-use"))
        assert "declaration-property-value-allowed-list" in satir, f"Books bloğu yeni kuralı {yon} etmiyor"


def test_b19_carbon_colors_dogrudan_bagimlilik():
    import json
    paket = json.loads((ROOT / "dashboard" / "package.json").read_text(encoding="utf-8"))
    kilit = json.loads((ROOT / "dashboard" / "package-lock.json").read_text(encoding="utf-8"))
    assert "@carbon/colors" in paket["dependencies"], "B19"
    kurulu = kilit["packages"]["node_modules/@carbon/colors"]["version"]
    assert paket["dependencies"]["@carbon/colors"].lstrip("^~") == kurulu
    assert "@carbon/colors" in kilit["packages"][""]["dependencies"]

# ── module/vendor rows, 4th round (2026-10-11): B18, B34, B52, B73, B74 ────────

VENDOR = ROOT / "src" / "mcp_server" / "vendor"


def _sablon_kurallari(metin: str):
    """(selector, body) of every CSS rule in the template's <style> blocks, comments dropped."""
    for blok in re.findall(r"<style[^>]*>(.*?)</style>", metin, flags=re.S):
        blok = re.sub(r"/\*.*?\*/", " ", blok, flags=re.S)
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", blok):
            yield " ".join(m.group(1).split()), m.group(2)


def test_b18_vendor_carbon_baglantilari_building_blocks():
    """Every carbondesignsystem.com link the vendored skill gives an author is on today's site map (B18).

    Verified 2026-10-11: each of the 36 distinct links answers 200 under /building-blocks/ and each anchor exists
    on its page; the retired roots (/elements/, /components/, /data-visualization/ …) only redirect.
    """
    ihlal = []
    for p in sorted(VENDOR.rglob("*")):
        if p.suffix not in {".md", ".html", ".py", ".json"} or not p.is_file():
            continue
        for m in re.finditer(r"https?://(?:www\.)?carbondesignsystem\.com(/[^\s)\"'>`\]]*)?",
                             p.read_text(encoding="utf-8")):
            yol = m.group(1) or "/"
            if not yol.startswith("/building-blocks/") and yol != "/":
                ihlal.append(f"{p.relative_to(VENDOR)}: {m.group(0)}")
    assert not ihlal, "bayat Carbon bağlantısı (B18):\n" + "\n".join(ihlal)


def test_b74_modul_baslik_agirligi_tokendan():
    """heading-03/04 sizes carry the token's own weight, 400 (S44, B74)."""
    metin = SABLON.read_text(encoding="utf-8")
    ihlal = []
    for secici, govde in _sablon_kurallari(metin):
        if re.search(r"font-size:\s*var\(--fs-h-(seg|sub)\)", govde):
            agirlik = re.findall(r"font-weight:\s*(\d+)", govde)
            if any(a != "400" for a in agirlik):
                ihlal.append(f"{secici} {{font-weight:{','.join(agirlik)}}}")
            if secici.split()[-1].startswith(("h2", "h3")) and not agirlik:
                ihlal.append(f"{secici}: başlık öğesi ağırlıksız (tarayıcı varsayılanı kalın)")
    assert not ihlal, "modül başlık token'ı 400 dışında (B74):\n" + "\n".join(ihlal)
    tablo = (VENDOR / "references" / "carbon-child-system.md").read_text(encoding="utf-8")
    assert "şablon bugün **600**" not in tablo


def test_b34_modulde_durum_opaklikla_cizilmez():
    """Disabled and held states are drawn with Carbon's disabled tokens, never faded (S24, B34)."""
    metin = SABLON.read_text(encoding="utf-8")
    ihlal = [f"{s} {{{g.strip()}}}" for s, g in _sablon_kurallari(metin)
             if re.search(r"\[disabled\]|\[aria-disabled|--locked|\[data-held", s)
             and re.search(r"(^|;)\s*opacity\s*:", g)]
    assert not ihlal, "modülde opaklıkla durum (B34):\n" + "\n".join(ihlal)
    for secici in (".btn[disabled]", ".chip-btn[disabled]", ".cmap-edge__remove[disabled]"):
        govde = next((g for s, g in _sablon_kurallari(metin) if s == secici), None)
        assert govde is not None and "-disabled" in govde, f"{secici} Carbon devre dışı token'ı taşımıyor"
    # a solved step's answer is content: read-only, not disabled (§5.9)
    assert "input.readOnly=true;" in metin and "input.disabled=true;" not in metin
    assert any(s == ".worked-input[readonly]" for s, _ in _sablon_kurallari(metin))


def test_b73_modulde_odul_hareketi_seri_ve_rozet_yok():
    """No reward motion, streak counter, badge case or reward sound in the module (S43, anayasa §9, B73).

    XP stays an internal number the progress bridge reports; the reader never sees it.
    """
    metin = SABLON.read_text(encoding="utf-8")
    for iz in ('id="xpValue"', 'class="xp"', "xp-float", "xpPulse", "xpRise", "streakChip", "streak-chip",
               "streakHit", "streak-float", "STREAK_MILESTONES", "badgePop", "badge--new", "badge--locked",
               'id="badgeCase"', '" XP"', "Toplam XP", "En uzun seri", "Tebrikler", "reward:[[",
               'playSound("reward")', "--reward", "stat--xp", "donut__pct"):
        assert iz not in metin, f"modülde oyunlaştırma izi kaldı (B73): {iz}"
    # the progress bridge still reports a number
    assert "state.xp+=n" in metin.replace(" ", "")
    dogrulayici = (VENDOR / "scripts" / "validate_module.py").read_text(encoding="utf-8")
    assert "S43" in dogrulayici, "G-FLOW seri sayacını reddetmiyor"


# ── B52 (§8.2, S19): module charts never invent data, step evenly, draw series in --viz-* ──

def _js_fonksiyon(metin: str, ad: str) -> str:
    bas = metin.index(f"function {ad}(")
    i = metin.index("{", bas)
    derinlik = 0
    for j in range(i, len(metin)):
        if metin[j] == "{":
            derinlik += 1
        elif metin[j] == "}":
            derinlik -= 1
            if derinlik == 0:
                return metin[bas:j + 1]
    raise AssertionError(ad)


def _grafik_calistir(ifade: str) -> str:
    import shutil
    import subprocess
    node = shutil.which("node")
    if node is None:
        import pytest
        pytest.skip("node yok")
    metin = SABLON.read_text(encoding="utf-8")
    esc = re.search(r"const esc = s => [^\n]*", metin).group(0)
    kod = "\n".join([esc] + [_js_fonksiyon(metin, ad) for ad in ("vizId", "svgFigure", "vizNice", "vizChart",
                                                                   "fractionBar")]
                    + [f"process.stdout.write(String({ifade}));"])
    return subprocess.run([node, "-e", kod], capture_output=True, text=True, check=True, timeout=30).stdout


def test_b52_eksik_deger_sifir_cizilmez():
    svg = _grafik_calistir('vizChart({title:"T",data:[{label:"A",value:3},{label:"B"},{label:"C",value:7}]})')
    assert svg.count("<rect") == 2, "eksik değer 0 yüksekliğinde çubuk olarak çiziliyor"
    assert "veri yok" in svg
    assert "B: veri yok" in re.search(r"<desc[^>]*>(.*?)</desc>", svg).group(1)
    cizgi = _grafik_calistir(
        'vizChart({kind:"line",data:[{label:"A",value:3},{label:"B",value:null},{label:"C",value:7}]})')
    assert cizgi.count("<circle") == 2
    yol = re.search(r'<path d="([^"]+)"', cizgi).group(1)
    assert "L" not in yol and yol.count("M") == 2, "çizgi eksik noktanın üstünden geçiyor"


def test_b52_eksen_esit_ve_yuvarlak_adimli():
    for veri, beklenen in (("[{label:'a',value:10}]", [0, 2, 4, 6, 8, 10]), ("[{label:'a',value:7}]", [0, 2, 4, 6, 8]),
                           ("[{label:'a',value:37}]", [0, 10, 20, 30, 40]), ("[{label:'a',value:3}]", [0, 1, 2, 3])):
        svg = _grafik_calistir(f"vizChart({{data:{veri}}})")
        etiketler = [int(x) for x in re.findall(r'text-anchor="end"[^>]*>([^<]+)<', svg)]
        assert sorted(etiketler) == beklenen, (veri, etiketler)


def test_b52_seriler_viz_paletinde():
    for ifade in ("vizChart({data:[{label:'a',value:1},{label:'b',value:2}]})",
                  "vizChart({kind:'line',data:[{label:'a',value:1},{label:'b',value:2}]})",
                  "fractionBar({num:2,den:5})", "fractionBar({ratio:[2,3],labels:['x','y']})",
                  "fractionBar({addends:[1,2],den:4})"):
        svg = _grafik_calistir(ifade)
        assert "var(--accent" not in svg, f"grafik serisi ders aksanında (S19): {ifade}"
        assert "var(--viz-1)" in svg, ifade


# ── S19 (§7.5 P5, §8): kategoriyi biçim taşır, hue değil ──────────────────────
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


def test_s19_yazarin_gecirdigi_renk_grafigi_bozmaz():
    """Palet ders ailesi sunmasa da yazar p.color ile elle gecirebilir: grafik yine cizilir.

    Karakterizasyon testi (Review Focus): davranis zaten vardi, bu degisiklik onu bozmamali.
    """
    svg = _grafik_calistir(
        "vizChart({legend:true,data:[{label:'A',value:3,color:'#9f1853'},{label:'B',value:5}]})")
    assert svg.count("<rect") == 2
    assert "#9f1853" in svg, "yazarin degeri dusurulmus"
    assert "var(--viz-1)" in svg, "varsayilan yuva kullanilmamis"


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
    """D1 renk aritmetigi yasagi TEDY'nin YAZDIGI bildirimler icindir.

    Carbon'un kendi token degerleri (--cds-overlay, --cds-shadow, --cds-text-placeholder,
    --cds-*-disabled) ustte rgba() tasir ve G-TOKEN bu degerleri @carbon/themes otoritesine
    karsi denetler; onlari yasaklamak Carbon'dan sapmayi zorunlu kilardi. Bu yuzden test
    yalnizca --cds-* tanimi OLMAYAN bildirimlere bakar.
    """
    metin = SABLON.read_text(encoding="utf-8")
    stil = metin[metin.index("<style>"):metin.index("</style>")]
    kotu = [f"{ad}:{deger.strip()}"
            for ad, deger in re.findall(r"(--[-a-z0-9]+|[-a-z]+)\s*:\s*([^;}\n]*)", stil)
            if "rgba(" in deger and not ad.startswith("--cds-")]
    assert not kotu, f"D1: TEDY'nin yazdigi bildirimde alfa rengi: {kotu}"


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
