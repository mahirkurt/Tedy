#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_carbon_tokens.py — carbon-edupedia ⇄ @carbon/* otorite senkronizasyonu.

Tek doğruluk kaynağı carbon-design-system/carbon monorepo'sudur (npm @carbon/*).
Bu araç iki iş yapar:

  --check    (varsayılan) assets/carbon-v11-authority.json içindeki otorite
             değerlerini assets/module-template.html tema bloklarıyla (g10 · white · g100)
             ve Tedy katmanını (`tedyLayer`, tedy-* token'ları) karşılaştırır;
             sapma tablosu basar. Çevrimdışı çalışır.
  --refresh  Ağ + npm varsa @carbon/{themes,type,motion,layout,colors} paketlerini
             geçici dizine kurar, token'ları yeniden çıkarır ve
             assets/carbon-v11-authority.json dosyasını günceller; ardından --check.
             Ayrıca @carbon/icons ve @carbon/charts paketlerini (varsa) kurup
             sürüm/ikon-sayısı bilgisini "canonical_sources" bloğuna kaydeder —
             bunlar token DEĞİL, envanter/sürüm izlenebilirliğidir (--check bu
             blok üzerinde sapma denetimi yapmaz). Kurulamazsa sessizce atlanır.

Çıkış kodu: 0 = sapma yok · 1 = sapma var · 2 = ortam/IO hatası.
Kullanım:  python scripts/sync_carbon_tokens.py [--check|--refresh] [--template YOL]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTH = ROOT / "assets" / "carbon-v11-authority.json"
TPL  = ROOT / "assets" / "module-template.html"

# CSS değişkeni -> otorite JSON yolu ("themes.<tema>.<anahtar>" ya da özel yol)
CORE = {
    "--cds-background": "background", "--cds-layer-01": "layer01", "--cds-layer-02": "layer02",
    "--cds-layer-03": "layer03", "--cds-layer-hover-01": "layerHover01",
    "--cds-layer-active-01": "layerActive01", "--cds-layer-selected-01": "layerSelected01",
    "--cds-layer-hover-02": "layerHover02", "--cds-layer-selected-02": "layerSelected02",
    "--cds-layer-accent-01": "layerAccent01", "--cds-field-01": "field01",
    "--cds-field-hover-01": "fieldHover01", "--cds-border-subtle-00": "borderSubtle00",
    "--cds-border-subtle-01": "borderSubtle01", "--cds-border-strong-01": "borderStrong01",
    "--cds-border-tile-01": "borderTile01", "--cds-border-interactive": "borderInteractive",
    "--cds-text-primary": "textPrimary", "--cds-text-secondary": "textSecondary",
    "--cds-text-helper": "textHelper", "--cds-text-placeholder": "textPlaceholder",
    "--cds-text-on-color": "textOnColor", "--cds-icon-primary": "iconPrimary",
    "--cds-icon-secondary": "iconSecondary", "--cds-icon-on-color": "iconOnColor",
    "--cds-interactive": "interactive", "--cds-link-primary": "linkPrimary",
    "--cds-link-primary-hover": "linkPrimaryHover", "--cds-focus": "focus",
    "--cds-focus-inset": "focusInset", "--cds-highlight": "highlight",
    "--cds-overlay": "overlay", "--cds-shadow": "shadow",
    "--cds-skeleton-background": "skeletonBackground", "--cds-skeleton-element": "skeletonElement",
    "--cds-support-success": "supportSuccess", "--cds-support-error": "supportError",
    "--cds-support-warning": "supportWarning", "--cds-support-info": "supportInfo",
}
COMPONENT = {  # @carbon/themes generated component-token haritaları
    "--cds-button-primary": ("componentTokens", "buttonPrimary"),
    "--cds-button-primary-hover": ("componentTokens", "buttonPrimaryHover"),
    "--cds-button-primary-active": ("componentTokens", "buttonPrimaryActive"),
    "--cds-notification-background-success": ("notification", "success"),
    "--cds-notification-background-info": ("notification", "info"),
    "--cds-notification-background-warning": ("notification", "warning"),
    "--cds-notification-background-error": ("notification", "error"),
}
# Kanonik adın şablonda yokluğunda (eski modül) denetlenen kısa adlar.
LEGACY = {
    "--cds-border-strong-01": "--cds-border-strong", "--cds-border-tile-01": "--cds-border-tile",
    "--cds-notification-background-success": "--cds-notif-success-bg",
    "--cds-notification-background-info": "--cds-notif-info-bg",
    "--cds-notification-background-warning": "--cds-notif-warning-bg",
    "--cds-notification-background-error": "--cds-notif-error-bg",
}

NODE_EXTRACT = r"""
const fs=require('fs');
const themes=require('@carbon/themes'), type=require('@carbon/type');
const motion=require('@carbon/motion'), layout=require('@carbon/layout'), colors=require('@carbon/colors');
const keys=%KEYS%;
const pick=(o,k)=>Object.fromEntries(k.filter(x=>o[x]!==undefined).map(x=>[x,o[x]]));
const out={_provenance:{source:'carbon-design-system/carbon via npm',
  packages:Object.fromEntries(['@carbon/themes','@carbon/type','@carbon/motion','@carbon/layout','@carbon/colors']
    .map(p=>[p,require(p+'/package.json').version])),
  extracted:new Date().toISOString().slice(0,10)},
  themes:{}, motion:{durations:pick(motion,['fast01','fast02','moderate01','moderate02','slow01','slow02']),
  easings:motion.easings},
  layout:{spacing:Object.fromEntries(layout.spacing.map((v,i)=>['spacing'+String(i+1).padStart(2,'0'),v])),
  sizes:layout.sizes}};
for(const t of ['white','g10','g90','g100']) out.themes[t]=pick(themes[t],keys);
const ts=['code01','code02','label01','label02','helperText01','bodyCompact02','body02',
  'heading03','heading04','heading05','expressiveParagraph01','quotation02'];
out.type=pick(type,ts); out.type.fontFamilies=type.fontFamilies;
// @carbon/icons + @carbon/charts: envanter/sürüm izlenebilirliği — token değil.
// Kurulu değilse (npm varsa-değilse) sessizce atlanır, çıkarımı bozmaz.
const canonicalSources={};
try{
  const iconsMeta=require('@carbon/icons/metadata.json');
  const iconsPkg=require('@carbon/icons/package.json');
  const iconCount=Array.isArray(iconsMeta) ? iconsMeta.length
    : (Array.isArray(iconsMeta && iconsMeta.icons) ? iconsMeta.icons.length : undefined);
  canonicalSources.icons={version:iconsPkg.version, count:iconCount};
}catch(e){/* @carbon/icons kurulu değil — atla */}
try{
  const chartsPkg=require('@carbon/charts/package.json');
  canonicalSources.charts={version:chartsPkg.version};
}catch(e){/* @carbon/charts kurulu değil — atla */}
if(Object.keys(canonicalSources).length) out.canonical_sources=canonicalSources;
fs.writeFileSync('out.json',JSON.stringify(out,null,1));
"""

def norm(v: str) -> str:
    """Boşlukları kaldırır, küçük harfe indirger ve '0.' önekini '.' yapar (token normalizasyonu)."""
    return re.sub(r"\s+", "", str(v)).lower().replace("0.", ".")

def theme_block(html: str, selector: str) -> str:
    """Verilen CSS seçicisine ait ilk kural bloğunun (süslü parantez içi) gövdesini döndürür."""
    i = html.find(selector)
    if i < 0: return ""
    j = html.find("{", i); k = html.find("}", j)
    return html[j + 1:k] if j >= 0 and k >= 0 else ""

def read_var(block: str, var: str) -> str | None:
    """Bir CSS bloğu içinden tek bir özel değişkenin (custom property) değerini okur."""
    m = re.search(re.escape(var) + r"\s*:\s*([^;}]+)", block)
    return m.group(1).strip() if m else None

def authority_value(auth: dict, theme: str, var: str) -> str | None:
    """Otorite JSON'undan bir CSS değişkeninin ilgili temadaki kanonik değerini çözer."""
    if var in CORE:
        return auth.get("themes", {}).get(theme, {}).get(CORE[var])
    if var in COMPONENT:
        kind, key = COMPONENT[var]
        if kind == "componentTokens":
            node = auth.get("componentTokens", {}).get(key, {})
            return node.get("all") or node.get(theme)
        return auth.get("componentTokens", {}).get("notificationBackground", {}).get(theme, {}).get(key)
    return None

def _block_drift(block: str, theme: str, auth: dict) -> int:
    """Tek bir tema bloğundaki sapan token sayısını döndürür; her sapmayı stdout'a yazar."""
    drift = 0
    for var in list(CORE) + list(COMPONENT):
        got = read_var(block, var)
        if got is None and var in LEGACY:
            got = read_var(block, LEGACY[var])
        want = authority_value(auth, theme, var)
        if got is None or want is None or norm(got).startswith("var("):
            continue
        if norm(got) != norm(want):
            drift += 1
            print(f"SAPMA [{theme}] {var}: şablon={got}  otorite={want}")
    return drift


def _tedy_drift(html: str, auth: dict) -> int:
    """Tedy katmanı (tedy-*) değerlerini otorite JSON'undaki `tedyLayer` ile karşılaştırır.

    Katmanı taşımayan (v1.9.0 öncesi) şablonlar denetlenmez. `scope: all` token'lar tema-bağımsız
    `:root,[data-theme]` bloğunda, diğerleri her temanın kendi bloğunda aranır.
    """
    layer = auth.get("tedyLayer", {}).get("tokens", {})
    if not layer or "--tedy-" not in html:
        return 0
    common = theme_block(html, ":root,[data-theme]")
    blocks = {"g10": theme_block(html, '[data-theme="g10"]'),
              "white": theme_block(html, '[data-theme="white"]'),
              "g100": theme_block(html, '[data-theme="g100"]')}
    drift = checked = 0
    for token, spec in layer.items():
        themes = ("g10",) if spec.get("scope") == "all" else ("g10", "white", "g100")
        for theme in themes:
            block = common if spec.get("scope") == "all" else blocks[theme]
            if not block:
                continue
            want = spec[theme][1]
            got = read_var(block, "--" + token)
            checked += 1
            if got is None or norm(got) != norm(want):
                drift += 1
                where = "ortak" if spec.get("scope") == "all" else theme
                print(f"SAPMA [tedy/{where}] --{token}: şablon={got}  otorite={want} ({spec[theme][0]})")
    print(f"Tedy katmanı: {checked} değer denetlendi.")
    return drift


# ---- Tedy ders renk sistemi (tedyLayer.subjectThemes) → şablonun üretilmiş iki bölgesi ----
CSS_MARK = ("/* tedy:ders-renkleri */", "/* /tedy:ders-renkleri */")
JS_MARK = ("/* tedy:ders-alanlari */", "/* /tedy:ders-alanlari */")
ROLE_VARS = (("accent", "--subject-accent"), ("text", "--subject-text"), ("surface", "--subject-surface"),
             ("onSurface", "--subject-on-surface"), ("surfaceHover", "--subject-surface-hover"),
             ("border", "--subject-border"), ("onAccent", "--subject-on-accent"))
_FOLD = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})


def fold(text: str) -> str:
    """src/subject_themes.py ve şablondaki foldTr() ile aynı katlama."""
    lowered = str(text).replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"\s+", " ", lowered.translate(_FOLD)).strip()


def _roles(modes: dict, mode: str) -> str:
    other = "dark" if mode == "light" else "light"
    decl = [f"{var}:{modes[mode][role][1]}" for role, var in ROLE_VARS]
    decl.append(f"--subject-text-inverse:{modes[other]['text'][1]}")
    return ";".join(decl)


def subject_css(auth: dict) -> str:
    """Aile başına açık (white, g10) ve koyu (g100) rol blokları; varsayılan `fallback` ailesidir."""
    st = auth["tedyLayer"]["subjectThemes"]
    fams, default = st["families"], st["fallback"]["family"]
    lines = [CSS_MARK[0],
             "/* Üretilir: scripts/sync_carbon_tokens.py --write-subjects — elle düzenlemeyin. Kaynak:",
             "   carbon-v11-authority.json → tedyLayer.subjectThemes (Carbon tagTokens + @carbon/colors).",
             "   Açık rol değerleri white ve g10'da, koyu değerler g100'de geçerlidir. */",
             f":root{{{_roles(fams[default], 'light')}}}"]
    lines += [f':root[data-subject-family="{f}"]{{{_roles(m, "light")}}}' for f, m in fams.items()]
    lines.append(f':root[data-theme="g100"]{{{_roles(fams[default], "dark")}}}')
    lines += [f':root[data-theme="g100"][data-subject-family="{f}"]{{{_roles(m, "dark")}}}'
              for f, m in fams.items()]
    lines.append(CSS_MARK[1])
    return "\n".join(lines)


def subject_js(auth: dict) -> str:
    st = auth["tedyLayer"]["subjectThemes"]
    rows = [[d["id"], d["family"], [fold(x) for x in d["stems"]]] for d in st["domains"]]
    fb = [st["fallback"]["id"], st["fallback"]["family"]]
    return (JS_MARK[0] + "\n"
            + "  const SUBJECT_DOMAINS=" + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n"
            + "  const SUBJECT_FALLBACK=" + json.dumps(fb, separators=(",", ":")) + ";\n"
            + "  const SUBJECT_FAMILIES=" + json.dumps(list(st["families"]), separators=(",", ":")) + ";\n"
            + "  " + JS_MARK[1])


def _region(html: str, marks: tuple[str, str]) -> tuple[int, int] | None:
    i = html.find(marks[0])
    j = html.find(marks[1], i + 1) if i >= 0 else -1
    return (i, j + len(marks[1])) if i >= 0 and j >= 0 else None


def write_subjects(template: Path) -> int:
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    html = template.read_text(encoding="utf-8")
    for marks, body in ((CSS_MARK, subject_css(auth)), (JS_MARK, subject_js(auth))):
        span = _region(html, marks)
        if span is None:
            print(f"HATA: {marks[0]} bölgesi şablonda yok."); return 2
        html = html[:span[0]] + body + html[span[1]:]
    template.write_text(html, encoding="utf-8")
    print(f"Ders renk sistemi yazıldı: {template.name}")
    return 0


def _subject_drift(html: str, auth: dict) -> int:
    """Şablonun üretilmiş ders bölgelerini otoriteden yeniden üretilenle karşılaştırır.

    Bölgeleri taşımayan (ders renk sistemi öncesi) şablonlar denetlenmez.
    """
    st = auth.get("tedyLayer", {}).get("subjectThemes")
    if not st or CSS_MARK[0] not in html:
        return 0
    drift = 0
    for marks, want in ((CSS_MARK, subject_css(auth)), (JS_MARK, subject_js(auth))):
        span = _region(html, marks)
        if span is None or html[span[0]:span[1]] != want:
            drift += 1
            print(f"SAPMA [ders-renkleri] {marks[0]} bölgesi otoriteden farklı "
                  "(düzeltmek için: --write-subjects)")
    values = len(st["families"]) * 2 * len(ROLE_VARS)
    print(f"Ders renk sistemi: {len(st['families'])} aile × 2 mod × {len(ROLE_VARS)} rol = {values} değer, "
          f"{len(st['domains'])} alan denetlendi.")
    return drift


def check(template: Path) -> int:
    """Şablon tema bloklarını otorite JSON ile karşılaştırır; sapma sayısını çıkış koduna çevirir."""
    try:
        auth = json.loads(AUTH.read_text(encoding="utf-8"))
        html = template.read_text(encoding="utf-8")
    except OSError as e:
        print(f"HATA: {e}"); return 2
    pkgs = auth.get("_provenance", {}).get("packages", {})
    print(f"Otorite: @carbon/themes {pkgs.get('@carbon/themes','?')} "
          f"(çıkarım {auth.get('_provenance',{}).get('extracted','?')})\n")
    has_g10 = '[data-theme="g10"]' in html
    blocks = {"g10":   theme_block(html, '[data-theme="g10"]'),
              "white": theme_block(html, '[data-theme="white"]') or
                       ("" if has_g10 else theme_block(html, ":root")),
              "g100":  theme_block(html, '[data-theme="g100"]')}
    drift = sum(
        _block_drift(block, theme, auth) if block else (0 if theme == "g10" and not has_g10 else _missing(theme))
        for theme, block in blocks.items()
    )
    drift += _tedy_drift(html, auth)
    drift += _subject_drift(html, auth)
    print("\nSonuç: " + ("sapma yok — şablon otoriteyle birebir." if drift == 0
                          else f"{drift} token sapıyor."))
    return 0 if drift == 0 else 1


def _missing(theme: str) -> int:
    """Tema bloğu bulunamadığında uyarı basar ve sapmaya katkısız 0 döndürür."""
    print(f"UYARI: {theme} tema bloğu bulunamadı.")
    return 0

def refresh() -> int:
    """@carbon/* paketlerini geçici dizine kurar, token'ları çıkarır ve otorite JSON'u tazeler."""
    keys = json.dumps(sorted(set(CORE.values())))
    script = NODE_EXTRACT.replace("%KEYS%", keys)
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "extract.js").write_text(script, encoding="utf-8")
        try:
            subprocess.run(["npm", "init", "-y"], cwd=td, capture_output=True, check=True)
            subprocess.run(["npm", "i", "--no-audit", "--no-fund", "--legacy-peer-deps",
                            "@carbon/themes", "@carbon/type", "@carbon/motion",
                            "@carbon/layout", "@carbon/colors"],
                           cwd=td, capture_output=True, check=True, timeout=300)
            # @carbon/icons + @carbon/charts opsiyoneldir (yalnızca canonical_sources
            # envanteri için); kurulamazlarsa asıl token çıkarımını düşürmeden atla.
            try:
                subprocess.run(["npm", "i", "--no-audit", "--no-fund", "--legacy-peer-deps",
                                "@carbon/icons", "@carbon/charts"],
                               cwd=td, capture_output=True, check=True, timeout=300)
            except (subprocess.SubprocessError, FileNotFoundError) as e:
                print(f"UYARI: @carbon/icons/@carbon/charts kurulamadı ({e}) — "
                      f"canonical_sources bu çalıştırmada atlanacak.")
            subprocess.run(["node", "extract.js"], cwd=td, capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"HATA: npm/node çıkarımı başarısız ({e}). --check çevrimdışı çalışmaya devam eder.")
            return 2
        fresh = json.loads((tdp / "out.json").read_text(encoding="utf-8"))
    # mevcut dosyadaki tagPairs/componentTokens/palette korunur; tema/tip/hareket tazelenir
    try:
        current = json.loads(AUTH.read_text(encoding="utf-8")) if AUTH.exists() else {}
        for k in ("themes", "type", "motion", "layout", "_provenance"):
            current[k] = fresh[k]
        if "canonical_sources" in fresh:
            current["canonical_sources"] = fresh["canonical_sources"]
        AUTH.write_text(json.dumps(current, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as e:
        print(f"HATA: otorite dosyası okunamadı/yazılamadı ({e})."); return 2
    cs = fresh.get("canonical_sources", {})
    cs_note = (f" · ikonlar {cs['icons']['version']} ({cs['icons'].get('count','?')} adet)"
               if "icons" in cs else "") + \
              (f" · charts {cs['charts']['version']}" if "charts" in cs else "")
    print(f"Yenilendi: {AUTH.relative_to(ROOT)} "
          f"(@carbon/themes {fresh['_provenance']['packages']['@carbon/themes']}{cs_note})\n")
    return 0

def main() -> None:
    """CLI giriş noktası: --refresh/--template bayraklarını ayrıştırır ve uygun işi çalıştırır."""
    ap = argparse.ArgumentParser(description="carbon-edupedia Carbon token senkronizasyonu")
    ap.add_argument("--refresh", action="store_true", help="npm'den yeniden çıkar ve JSON'u güncelle")
    ap.add_argument("--check", action="store_true",
                     help="sapma denetimi (varsayılan davranış; bayrak açıkça da verilebilir, no-op)")
    ap.add_argument("--template", type=Path, default=TPL, help="denetlenecek şablon/modül HTML")
    ap.add_argument("--write-subjects", action="store_true",
                    help="ders renk sistemi bölgelerini (CSS + JS) otoriteden yeniden yaz")
    args = ap.parse_args()
    if args.write_subjects:
        rc = write_subjects(args.template)
        if rc != 0: sys.exit(rc)
    if args.refresh:
        rc = refresh()
        if rc != 0: sys.exit(rc)
    sys.exit(check(args.template))

if __name__ == "__main__":
    main()
