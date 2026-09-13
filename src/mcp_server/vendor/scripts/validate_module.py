#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
carbon-edupedia · Modül Kalite Kapısı Doğrulayıcı (validate_module.py)
====================================================================
Üretilen bir etkileşimli öğrenim modülü HTML'ini SKILL.md §12 kalite
kapılarına göre denetler. Salt-metin (regex/heuristik) denetimdir;
tarayıcı gerektirmez. Çıkış kodu: 0 = tüm FAIL kapıları geçti, 1 = ihlal.

Kullanım:
    python scripts/validate_module.py <modul.html> [--strict] [--json]

    --json  stdout'a YALNIZ geçerli JSON basar (renk/banner/insan-okur metin YOK);
            şekil manifest'in `quality_gates` alanına DOĞRUDAN gömülebilir:
            {"G-EMOJI": {"status": "PASS"}, "G-A11Y": {"status": "FAIL", "detail": "..."}, ...}
            `status` yalnız PASS/FAIL/WARN/SKIPPED olur; koşturulmayan/uygulanamayan
            kapı (imza yok / uygulanmaz dalı) her zaman SKIPPED'dir (asla PASS).
            Varsayılan (bayraksız) insan-okur konsol raporu bu bayraktan etkilenmez;
            çıkış kodu sözleşmesi de (0=tüm FAIL kapıları geçti, 1=ihlal) aynen korunur.

Kapılar:
    G-EMOJI         (FAIL) — çıktıda emoji bulunmamalı
    G-CARBON        (FAIL) — IBM Plex Sans/Serif/Mono inline @font-face; çekirdek
                    --cds-* token'ları tanımlı/kullanımda
    G-A11Y          (FAIL) — lang, <title>, reduced-motion, ARIA, odak görünürlüğü
    G-INTERACT      (FAIL) — her quiz sorusunda correctIndex; (WARN) explanation
    G-SELFCONTAINED (FAIL) — runtime kaynakları yalnız satır içi/data URI
    G-CONTRAST      (WARN) — metin rengi token'ı; aksanın küçük metinde kullanımı uyarısı
    G-WELLBEING     (FAIL) — cezalandırıcı/süre-baskısı dili yok; (WARN) uzun modülde mola/azaltılmış hareket
    G-VOICE         (FAIL) — öğrenci yüzeyinde kaynak-meta atıf yok ("kitabın tanımı",
                    "kitaptaki yazıyı hatırla", "ders kitabında", "ünitede gördüğün");
                    anlatım bu modülün kendi nihai dilidir. verification/sourceCitation
                    yazar katmanıdır, taranmaz.
    G-SVG           (FAIL) — figür SVG'leri role="img"+başlık; (WARN) ham-hex yerine token renk
    G-AUDIO         (FAIL) — ses varsa: susturulabilir + reduced-motion + otomatik-oynatma/döngü yok
    G-TOKEN         (WARN) — çekirdek --cds-* değerleri @carbon/themes otoritesiyle birebir; white support-info regresyonu FAIL
    G-CURRICULUM    (FAIL) — koşullu: CURRICULUM modu/curriculum bloğu varsa kazanım→segment izlenebilirliği
    G-VERIFY        (FAIL) — koşullu: müfredat-temelli modülde kapsam+doğruluk denetiminin KAYDI
                    (her iddia dayanağıyla). Yargı modelin; kapı yalnız dayanağın GÖSTERİLDİĞİNİ
                    ölçer — doğruluğu, belgenin varlığını, sayfayı DOĞRULAYAMAZ (MCP erişimi yok)
    G-FLOW          (FAIL) — koşullu: gamification imzası varsa merak-boşluğu kapanışı, gain-only streak,
                    kaygısız pacingDisk, etiketlemeyen uyarlanır zorluk
    G-CARBON-GRID   (FAIL) — statik kartta (gerçek/non-inset) drop-shadow (layer-elevation ihlali);
                    (WARN) 2x-grid konteyneri, en-boy oranı (aspect-ratio), koreografi >500ms
    G-EXAM          (FAIL) — koşullu: mode EXAM/exam bloğu varsa sınav-sorusu yapısı —
                    soru transkribe + doğrulama segmentine bağlı, zincir segmentlere
                    izlenebilir, cevap fadeFrom ile öğrenciye bırakılmış. Yargı modelin;
                    kapı transkripsiyonun sadakatini/çözümün doğruluğunu ÖLÇEMEZ
"""
import sys, re, argparse, json, unicodedata
from html.parser import HTMLParser

# ---- Emoji aralıkları (yaygın bloklar) ----
EMOJI_RE = re.compile(
    "[" 
    "\U0001F300-\U0001FAFF"   # semboller, piktograflar, ek semboller
    "\U00002600-\U000027BF"   # çeşitli semboller + dingbats
    "\U0001F000-\U0001F0FF"   # mahjong/domino/playing cards
    "\U0001F1E6-\U0001F1FF"   # bölgesel bayrak harfleri
    "\U00002190-\U000021FF"   # oklar (bazı emoji oklar) — yanlış pozitifi azaltmak için VS16 ile birlikte aranır
    "\U0000FE0F"              # variation selector-16 (emoji sunum)
    "\U00002028-\U00002029"   # line/para separators (zararsız ama temizlik)
    "\U0001F004\U0001F0CF\U0000203C\U00002049"
    "]"
)
# Daha güvenli emoji yakalama: VS16 veya ana emoji blokları
CORE_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]"
    "|\U0000FE0F"
)

RESET="\033[0m"; RED="\033[31m"; GRN="\033[32m"; YEL="\033[33m"; BOLD="\033[1m"; DIM="\033[2m"

class Result:
    def __init__(self):
        """Boş bulgu listesi ve fail bayrağı başlatır."""
        self.rows=[]; self.fail=False
        # gate id'leri: bu koşumda "uygulanmaz/koşturulmayan" dala düşenler.
        # (rows tuple şekli — (gate,status,msg) — testlerin `for g,s,_ in rows`
        # 3'lü açımı için KASTEN 3 alanlı kalır; uygulanabilirlik ayrı izlenir.)
        self.not_applicable=set()
    def add(self, gate, status, msg, applicable=True):
        """Bir kapı sonucunu (PASS|FAIL|WARN) kaydeder; FAIL ise fail bayrağını kaldırır.

        applicable=False: bu çağrı kapının "uygulanmaz/koşturulmayan" (skip) dalından
        geliyor demektir (imza yok, mod uymuyor, vb.) — konsol raporunda mevcut
        PASS/WARN metni AYNEN kalır, ama --json çıktısında bu kapı SKIPPED olarak
        yazılır (asla PASS).
        """
        self.rows.append((gate,status,msg))
        if status=="FAIL": self.fail=True
        if not applicable: self.not_applicable.add(gate)
    def to_json_gates(self):
        """--json modu için: R.rows'u {gate: {status, detail}} sözlüğüne indirger.

        Aynı gate adı altında birden çok satır varsa (yalnız G-INTERACT: PASS/FAIL +
        opsiyonel açıklama-WARN'ı) en kötü durum (FAIL>WARN>PASS) seçilir ve mesajlar
        birleştirilir. `not_applicable` işaretli kapılar iç durumdan bağımsız SKIPPED
        yazılır (asla PASS) — "koşturulmayan/uygulanamayan kapı" sözleşmesi.
        """
        severity = {"FAIL": 3, "WARN": 2, "PASS": 1, "SKIPPED": 0}
        grouped = {}
        order = []
        for gate, status, msg in self.rows:
            if gate not in grouped:
                grouped[gate] = []
                order.append(gate)
            grouped[gate].append((status, msg))
        gates = {}
        for gate in order:
            entries = grouped[gate]
            if gate in self.not_applicable:
                status = "SKIPPED"
            else:
                status = max((s for s, _ in entries), key=lambda s: severity.get(s, 0))
            detail = "; ".join(m for _, m in entries if m)
            gate_obj = {"status": status}
            if detail:
                gate_obj["detail"] = detail
            gates[gate] = gate_obj
        return gates
    def report(self):
        """Renkli, hizalı denetim raporunu stdouta basar.

        KAPI OTORİTESİ --json'dur; konsol onunla TUTARLI olmak ZORUNDA. Bir kapı
        `not_applicable` işaretliyse iç durumu PASS/WARN bile olsa konsolda ATLANDI
        (SKIPPED) gösterilir — yoksa konsol "GEÇTİ/UYARI" derken --json "SKIPPED"
        der ve rapor kendi içinde yalan söyler. Aynı gerekçeyle atlanan kapı uyarı
        sayısına DA girmez.
        """
        print(f"\n{BOLD}carbon-edupedia · Modül Doğrulama Raporu{RESET}")
        print("="*64)
        for gate,status,msg in self.rows:
            eff = "SKIPPED" if gate in self.not_applicable else status
            c={"PASS":GRN,"FAIL":RED,"WARN":YEL,"SKIPPED":DIM}[eff]
            tag={"PASS":"GEÇTİ","FAIL":"İHLAL","WARN":"UYARI","SKIPPED":"ATLANDI"}[eff]
            print(f"  {c}{tag:7}{RESET}  {BOLD}{gate:16}{RESET} {msg}")
        print("="*64)
        n_fail=sum(1 for g,s,_ in self.rows if s=="FAIL" and g not in self.not_applicable)
        n_warn=sum(1 for g,s,_ in self.rows if s=="WARN" and g not in self.not_applicable)
        n_skip=len(self.not_applicable)
        verdict = f"{RED}{n_fail} İHLAL{RESET}" if n_fail else f"{GRN}TÜM FAIL KAPILARI GEÇTİ{RESET}"
        print(f"  Sonuç: {verdict}  ·  {YEL}{n_warn} uyarı{RESET}  ·  {DIM}{n_skip} atlandı{RESET}\n")

def gate_emoji(html, R):
    """G-EMOJI: çıktıda emoji bulunmadığını doğrular (FAIL kapısı)."""
    hits=CORE_EMOJI_RE.findall(html)
    # VS16 tek başına bazen meşru olabilir; emoji bloğuyla birlikteyse kesin emoji
    real=[h for h in hits if h!="\ufe0f"] or hits
    if real:
        sample=", ".join(sorted(set(real))[:6])
        R.add("G-EMOJI","FAIL", f"{len(real)} emoji bulundu (örn: {sample}). Carbon ikon/piktogram/SVG kullanın.")
    else:
        R.add("G-EMOJI","PASS","Emoji yok.")

def gate_carbon(html, R):
    """G-CARBON: IBM Plex ve çekirdek --cds-* token kullanımını doğrular (FAIL)."""
    issues=[]
    font_faces = re.findall(r"@font-face\s*\{(.*?)\}", html, re.I | re.S)
    inline_families = set()
    for block in font_faces:
        family = re.search(r"font-family\s*:\s*(['\"]?)(IBM Plex (?:Sans|Serif|Mono))\1", block, re.I)
        if family and re.search(r"url\(\s*['\"]?data:font/woff2;base64,", block, re.I):
            inline_families.add(family.group(2).casefold())
    required_families = {"ibm plex sans", "ibm plex serif", "ibm plex mono"}
    missing_families = sorted(required_families - inline_families)
    if missing_families:
        issues.append(
            "inline @font-face eksik: " + ", ".join(name.title() for name in missing_families)
        )
    core=["--cds-text-primary","--cds-background","--cds-interactive",
          "--cds-support-success","--cds-support-error"]
    missing=[t for t in core if t not in html]
    if missing: issues.append("eksik token: "+", ".join(missing))
    # token kullanımı: var(--cds-text-primary) gerçekten kullanılıyor mu
    if "var(--cds-text-primary)" not in html and "var(--accent" not in html:
        issues.append("token'lar tanımlı ama kullanımda görünmüyor")
    if issues:
        R.add("G-CARBON","FAIL","; ".join(issues))
    else:
        R.add(
            "G-CARBON",
            "PASS",
            "IBM Plex Sans/Serif/Mono inline @font-face + çekirdek Carbon token'ları "
            "tanımlı ve kullanımda.",
        )

def gate_a11y(html, R):
    """G-A11Y: lang, title, reduced-motion, aria-live, odak ve görsel rollerini denetler (FAIL)."""
    issues=[]
    if not re.search(r'<html[^>]*\blang=', html): issues.append("<html lang> yok")
    if not re.search(r'<title>.*?</title>', html, re.S): issues.append("<title> yok")
    if "prefers-reduced-motion" not in html: issues.append("reduced-motion bloğu yok")
    if "aria-live" not in html: issues.append("aria-live (anlık geri bildirim) yok")
    # outline:none kötüye kullanımı (odak halkası kaldırılmış mı)
    bad_outline = re.findall(r'outline\s*:\s*none', html)
    if bad_outline and "focus-visible" not in html:
        issues.append("outline:none var ama :focus-visible yedeği yok")
    if "role=\"img\"" not in html and "aria-hidden" not in html:
        issues.append("görsel rolleri (role=img / aria-hidden) yok")
    if issues:
        R.add("G-A11Y","FAIL","; ".join(issues))
    else:
        R.add("G-A11Y","PASS","lang, title, reduced-motion, aria-live, odak ve görsel rolleri tamam.")

def gate_interact(html, R):
    """G-INTERACT: her quiz sorusunda correctIndex; explanation eksikse WARN (FAIL).

    `exam` / `exams[]` sayımın DIŞINDA tutulur: `stem` bir quiz sorusu değil, sınav
    sorusunun metnidir ve cevap anahtarı taşımaz — doğru cevap `worked` segmentinin
    son adımındaki `answer` ile çeldirici `mcq`'sünün `correctIndex`'inde yaşar
    (references/exam-solving.md §3). Çıkarılmazsa her EXAM modülü sahte bir
    "cevapsız soru" FAIL'i üretir ve hiç teslim edilemez.
    """
    # MODULE_DATA içindeki quiz bütünlüğü (heuristik)
    scope = html
    exam_m = re.search(r'\bexam\s*:\s*\{', scope)
    if exam_m:
        scope = _blank_bracketed(scope, exam_m.end() - 1, "{", "}")
    exams_m = re.search(r'\bexams\s*:\s*\[', scope)
    if exams_m:
        scope = _blank_bracketed(scope, exams_m.end() - 1, "[", "]")
    stems=len(re.findall(r'\bstem\s*:', scope))
    correct=len(re.findall(r'\bcorrectIndex\s*:', scope))
    expl=len(re.findall(r'\bexplanation\s*:', scope))
    if stems==0:
        R.add("G-INTERACT","WARN","MODULE_DATA'da quiz sorusu (stem) bulunamadı (mod quiz değilse normal).",
              applicable=False)
        return
    if correct < stems:
        R.add("G-INTERACT","FAIL",
              f"{stems} soru var ama {correct} correctIndex; her soruda doğru cevap zorunlu.")
    else:
        R.add("G-INTERACT","PASS", f"{stems} sorunun her birinde correctIndex mevcut.")
    if expl < stems:
        R.add("G-INTERACT","WARN",
              f"{stems} sorudan {expl} tanesinde açıklama (explanation) var; her soruya açıklama önerilir.")

_RESOURCE_LINK_RELS = {
    "stylesheet", "preload", "modulepreload", "prefetch", "preconnect",
    "dns-prefetch", "icon", "apple-touch-icon", "manifest", "font",
}
_SRC_RESOURCE_TAGS = {"img", "video", "audio", "source", "track"}
_SVG_RESOURCE_TAGS = {"image", "feimage", "use"}


def _inline_resource(ref):
    """Bir runtime kaynak başvurusu dosyanın içinde mi (data:/#fragment)?"""
    value = (ref or "").strip()
    return bool(value) and (value.casefold().startswith("data:") or value.startswith("#"))


def _srcset_urls(value):
    """srcset aday URL'lerini descriptor'lardan ayırır.

    Data URI içindeki virgül ayraç değildir. Tarayıcı sözdiziminin tamamını yeniden
    uygulamak yerine URL token'larını doğrulayıcının gereksindiği kadar, doğrusal
    zamanda çıkarır.
    """
    urls = []
    i = 0
    n = len(value)
    while i < n:
        while i < n and (value[i].isspace() or value[i] == ","):
            i += 1
        if i >= n:
            break
        start = i
        is_data = value[i:i + 5].casefold() == "data:"
        if is_data:
            while i < n and not value[i].isspace():
                i += 1
            token = value[start:i]
            separated = token.endswith(",")
            if separated:
                token = token[:-1]
            urls.append(token)
            if separated:
                continue
        else:
            while i < n and not value[i].isspace() and value[i] != ",":
                i += 1
            urls.append(value[start:i])
            if i < n and value[i] == ",":
                i += 1
                continue
        parens = 0
        while i < n:
            ch = value[i]
            if ch == "(":
                parens += 1
            elif ch == ")" and parens:
                parens -= 1
            elif ch == "," and not parens:
                i += 1
                break
            i += 1
    return urls


def _css_string(css, start):
    """CSS quoted string'inin (çözülmemiş) içeriğini ve bitiş indeksini döndürür."""
    quote = css[start]
    chars = []
    i = start + 1
    while i < len(css):
        ch = css[i]
        if ch == "\\" and i + 1 < len(css):
            chars.append(css[i + 1])
            i += 2
            continue
        if ch == quote:
            return "".join(chars), i + 1
        chars.append(ch)
        i += 1
    return "".join(chars), i


def _css_url(css, start):
    """start konumundaki url(...) işlevinden (ref, end) çıkarır."""
    i = start + 3
    while i < len(css) and css[i].isspace():
        i += 1
    if i >= len(css) or css[i] != "(":
        return None, start + 1
    i += 1
    while i < len(css) and css[i].isspace():
        i += 1
    if i < len(css) and css[i] in "\"'":
        ref, i = _css_string(css, i)
        while i < len(css) and css[i].isspace():
            i += 1
        return ref, i + 1 if i < len(css) and css[i] == ")" else i
    begin = i
    while i < len(css) and css[i] != ")":
        if css[i] == "\\" and i + 1 < len(css):
            i += 2
        else:
            i += 1
    return css[begin:i].strip(), i + 1 if i < len(css) else i


def _css_image_set(css, start, function_name):
    """image-set(...) içindeki üst-seviye aday URL'leri ve bitiş indeksini döndürür."""
    index = start + len(function_name)
    while index < len(css) and css[index].isspace():
        index += 1
    if index >= len(css) or css[index] != "(":
        return [], start + 1
    refs = []
    depth = 1
    index += 1
    while index < len(css) and depth:
        if css.startswith("/*", index):
            close = css.find("*/", index + 2)
            index = len(css) if close < 0 else close + 2
            continue
        if css[index] in "\"'":
            ref, stop = _css_string(css, index)
            if depth == 1:
                refs.append(("CSS image-set()", ref))
            index = stop
            continue
        if css[index:index + 3].casefold() == "url":
            ref, stop = _css_url(css, index)
            if ref is not None:
                refs.append(("CSS image-set() url()", ref))
            index = stop
            continue
        if css[index] == "(":
            depth += 1
        elif css[index] == ")":
            depth -= 1
        index += 1
    return refs, index


def _css_resource_refs(css):
    """CSS yorumları/prose string'leri dışındaki @import ve url(...) kaynakları."""
    refs = []
    i = 0
    n = len(css)
    while i < n:
        if css.startswith("/*", i):
            close = css.find("*/", i + 2)
            i = n if close < 0 else close + 2
            continue
        if css[i] in "\"'":
            _, i = _css_string(css, i)
            continue
        image_set_name = next(
            (
                name for name in ("-webkit-image-set", "image-set")
                if css[i:i + len(name)].casefold() == name
                and (not i or not (css[i - 1].isalnum() or css[i - 1] in "_-"))
            ),
            None,
        )
        if image_set_name:
            found, i = _css_image_set(css, i, image_set_name)
            refs.extend(found)
            continue
        if css[i:i + 7].casefold() == "@import":
            j = i + 7
            while j < n and css[j].isspace():
                j += 1
            if j < n and css[j] in "\"'":
                ref, j = _css_string(css, j)
                refs.append(("@import", ref))
                i = j
                continue
        if css[i:i + 3].casefold() == "url":
            before = css[i - 1] if i else ""
            after = css[i + 3] if i + 3 < n else ""
            if not (before and (before.isalnum() or before in "_-")) and (
                after.isspace() or after == "("
            ):
                ref, i = _css_url(css, i)
                if ref is not None:
                    refs.append(("CSS url()", ref))
                continue
        i += 1
    return refs


_INLINE_JS_SCAN_LIMIT = 4 * 1024 * 1024
_JS_RESOURCE_CALLS = {
    "fetch", "XMLHttpRequest", "WebSocket", "EventSource",
    "sendBeacon", "Worker", "SharedWorker",
}
_JS_RESOURCE_ATTRS = {"src", "href"}


def _js_string_token(js, start):
    """Bir JS string/template literalini yorumlamadan tek token olarak geçirir."""
    quote = js[start]
    chars = []
    index = start + 1
    while index < len(js):
        ch = js[index]
        if ch == "\\" and index + 1 < len(js):
            chars.append(js[index + 1])
            index += 2
            continue
        if ch == quote:
            return "".join(chars), index + 1
        chars.append(ch)
        index += 1
    raise ValueError("kapanmamış inline JavaScript string'i")


def _js_regex_allowed(tokens):
    """`/` bu konumda bölme değil regex literal başlangıcı olabilir mi?"""
    if not tokens:
        return True
    kind, value = tokens[-1]
    if kind == "punct":
        return value in "([{=,:;!?&|+-*%^~<>"
    return kind == "identifier" and value in {
        "return", "case", "throw", "else", "do", "typeof", "instanceof",
        "in", "of", "yield", "await",
    }


def _js_regex_end(js, start):
    """JS regex literalini string karakterlerini kod sanmadan geçirir."""
    index = start + 1
    in_class = False
    while index < len(js):
        ch = js[index]
        if ch == "\\" and index + 1 < len(js):
            index += 2
            continue
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "/" and not in_class:
            index += 1
            while index < len(js) and js[index].isalpha():
                index += 1
            return index
        elif ch in "\r\n":
            return start + 1
        index += 1
    return start + 1


def _js_tokens(js):
    """Yorumları atıp string'leri veri token'ı olarak koruyan sınırlı JS lexer."""
    if len(js) > _INLINE_JS_SCAN_LIMIT:
        raise ValueError("inline JavaScript tarama sınırını aşıyor")
    tokens = []

    def scan_template(index):
        """Template'in ham metnini atlar, yalnız ${...} kodunu yeniden lexer'a verir."""
        index += 1
        while index < len(js):
            if js[index] == "\\" and index + 1 < len(js):
                index += 2
                continue
            if js[index] == "`":
                return index + 1
            if js.startswith("${", index):
                index = scan_code(index + 2, stop_at_brace=True)
                continue
            index += 1
        raise ValueError("kapanmamış inline JavaScript template literal'i")

    def scan_code(index, stop_at_brace=False):
        brace_depth = 0
        while index < len(js):
            if js[index].isspace():
                index += 1
                continue
            if js.startswith("//", index):
                newline = js.find("\n", index + 2)
                index = len(js) if newline < 0 else newline + 1
                continue
            if js.startswith("/*", index):
                close = js.find("*/", index + 2)
                if close < 0:
                    raise ValueError("kapanmamış inline JavaScript blok yorumu")
                index = close + 2
                continue
            if js[index] == "/" and _js_regex_allowed(tokens):
                stop = _js_regex_end(js, index)
                if stop > index + 1:
                    index = stop
                    continue
            if js[index] in "\"'":
                value, index = _js_string_token(js, index)
                tokens.append(("string", value))
                continue
            if js[index] == "`":
                index = scan_template(index)
                continue
            match = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", js[index:])
            if match:
                value = match.group(0)
                tokens.append(("identifier", value))
                index += len(value)
                continue
            if js[index] == "{":
                brace_depth += 1
            elif js[index] == "}":
                if stop_at_brace and brace_depth == 0:
                    return index + 1
                brace_depth = max(0, brace_depth - 1)
            tokens.append(("punct", js[index]))
            index += 1
        if stop_at_brace:
            raise ValueError("kapanmamış inline JavaScript template ifadesi")
        return index

    scan_code(0)
    return tokens


def _js_call_arguments(tokens, open_index):
    """Bir çağrının üst-seviye argüman token'larını döndürür."""
    args = [[]]
    depth = 0
    index = open_index + 1
    while index < len(tokens):
        kind, value = tokens[index]
        if kind == "punct" and value in "([{":
            depth += 1
        elif kind == "punct" and value in ")]}":
            if value == ")" and depth == 0:
                return args, index
            depth = max(0, depth - 1)
        elif kind == "punct" and value == "," and depth == 0:
            args.append([])
            index += 1
            continue
        args[-1].append(tokens[index])
        index += 1
    return args, len(tokens)


def _js_reference_expression_is_inline(tokens):
    """Sabit parçaları yalnız data:/#fragment olan bir kaynak ifadesini kabul eder."""
    if (
        len(tokens) >= 2
        and tokens[0][0] == "string"
        and _inline_resource(tokens[0][1])
        and tokens[1] == ("punct", "+")
    ):
        # "#"+dynamicIcon biçimi her sonuçta aynı-belge fragmenti üretir.
        return True
    try:
        question = tokens.index(("punct", "?"))
    except ValueError:
        question = -1
    value_tokens = tokens[question + 1:] if question >= 0 else tokens
    refs = [value for kind, value in value_tokens if kind == "string"]
    return bool(refs) and all(_inline_resource(ref) for ref in refs)


def _js_runtime_loaders(js):
    """Yorum/string prose dışındaki ağ API'lerini ve dinamik kaynak atamalarını bulur."""
    tokens = _js_tokens(js)
    bad = []
    index = 0
    while index < len(tokens):
        kind, value = tokens[index]
        call_index = index + 1
        while (
            call_index < len(tokens)
            and tokens[call_index][0] == "punct"
            and tokens[call_index][1] in {"?", "."}
        ):
            call_index += 1
        if kind == "identifier" and (
            value in _JS_RESOURCE_CALLS or value == "import"
        ) and call_index < len(tokens) and tokens[call_index] == ("punct", "("):
            bad.append(f"inline JS {value}(...)")
        if kind == "identifier" and value == "import" and index + 1 < len(tokens):
            next_token = tokens[index + 1]
            previous_token = tokens[index - 1] if index else None
            if (
                previous_token != ("punct", ".")
                and next_token != ("punct", ".")
                and next_token != ("punct", "(")
                and (
                    next_token[0] in {"identifier", "string"}
                    or next_token == ("punct", "{")
                    or next_token == ("punct", "*")
                )
            ):
                bad.append("inline JS static import bildirimi")
        if kind == "identifier" and value == "export" and index + 1 < len(tokens):
            next_token = tokens[index + 1]
            source_index = None
            if next_token == ("punct", "*"):
                cursor = index + 2
                while cursor + 1 < len(tokens) and tokens[cursor] != ("punct", ";"):
                    if (
                        tokens[cursor] == ("identifier", "from")
                        and tokens[cursor + 1][0] == "string"
                    ):
                        source_index = cursor + 1
                        break
                    cursor += 1
            elif next_token == ("punct", "{"):
                cursor = index + 2
                depth = 1
                while cursor < len(tokens) and depth:
                    if tokens[cursor] == ("punct", "{"):
                        depth += 1
                    elif tokens[cursor] == ("punct", "}"):
                        depth -= 1
                    cursor += 1
                if (
                    cursor + 1 < len(tokens)
                    and tokens[cursor] == ("identifier", "from")
                    and tokens[cursor + 1][0] == "string"
                ):
                    source_index = cursor + 1
            if source_index is not None:
                bad.append("inline JS static export-from bildirimi")
        if (
            kind == "string"
            and value in _JS_RESOURCE_CALLS
            and index > 0
            and tokens[index - 1] == ("punct", "[")
            and index + 2 < len(tokens)
            and tokens[index + 1] == ("punct", "]")
        ):
            computed_call = index + 2
            while (
                computed_call < len(tokens)
                and tokens[computed_call][0] == "punct"
                and tokens[computed_call][1] in {"?", "."}
            ):
                computed_call += 1
            if (
                computed_call < len(tokens)
                and tokens[computed_call] == ("punct", "(")
            ):
                bad.append(f"inline JS computed {value}(...)")
        if (
            kind == "identifier"
            and value == "setAttribute"
            and index + 1 < len(tokens)
            and tokens[index + 1] == ("punct", "(")
        ):
            args, stop = _js_call_arguments(tokens, index + 1)
            if (
                len(args) >= 2
                and len(args[0]) == 1
                and args[0][0][0] == "string"
                and args[0][0][1].casefold() in _JS_RESOURCE_ATTRS
                and not _js_reference_expression_is_inline(args[1])
            ):
                bad.append(f"inline JS setAttribute({args[0][0][1]})")
        property_name = None
        assignment_index = None
        if (
            tokens[index:index + 2] == [("punct", "."), ("identifier", "src")]
            or tokens[index:index + 2] == [("punct", "."), ("identifier", "href")]
        ):
            property_name = tokens[index + 1][1]
            assignment_index = index + 2
        elif (
            index + 3 < len(tokens)
            and tokens[index] == ("punct", "[")
            and tokens[index + 1][0] == "string"
            and tokens[index + 1][1].casefold() in _JS_RESOURCE_ATTRS
            and tokens[index + 2] == ("punct", "]")
        ):
            property_name = tokens[index + 1][1].casefold()
            assignment_index = index + 3
        if (
            property_name
            and assignment_index < len(tokens)
            and tokens[assignment_index] == ("punct", "=")
            and (
                assignment_index + 1 >= len(tokens)
                or tokens[assignment_index + 1] != ("punct", "=")
            )
        ):
            stop = assignment_index + 1
            depth = 0
            while stop < len(tokens):
                token = tokens[stop]
                if token[0] == "punct" and token[1] in "([{":
                    depth += 1
                elif token[0] == "punct" and token[1] in ")]}":
                    depth = max(0, depth - 1)
                elif token[0] == "punct" and token[1] == ";" and depth == 0:
                    break
                stop += 1
            if not _js_reference_expression_is_inline(tokens[assignment_index + 1:stop]):
                bad.append(f"inline JS .{property_name} ataması")
            index = max(index, stop)
        index += 1
    return bad


class _SelfContainedParser(HTMLParser):
    """Gerçek HTML etiketlerini tarar; yorum/prose/script içeriğini kaynak sanmaz."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bad = []
        self._style_depth = 0
        self._style_chunks = []
        self._script_depth = 0
        self._script_chunks = []
        self._svg_depth = 0

    def _record(self, where, ref):
        if not _inline_resource(ref):
            shown = (ref or "<boş>").strip() or "<boş>"
            self.bad.append(f"{where}: {shown}")

    def _block(self, where, detail):
        self.bad.append(f"{where}: {detail}")

    def _tag(self, tag, attrs):
        tag = tag.casefold()
        values = {name.casefold(): value or "" for name, value in attrs}

        if tag == "iframe":
            self._block("iframe", "alt belge fail-closed olarak desteklenmiyor")
        if tag == "script" and "src" in values:
            self._record("script[src]", values["src"])
        if tag in _SRC_RESOURCE_TAGS and "src" in values:
            self._record(f"{tag}[src]", values["src"])
        if tag in {"img", "source"} and "srcset" in values:
            for ref in _srcset_urls(values["srcset"]):
                self._record(f"{tag}[srcset]", ref)
        if tag == "video" and "poster" in values:
            self._record("video[poster]", values["poster"])
        if tag == "input" and values.get("type", "").casefold() == "image" and "src" in values:
            self._record("input[type=image][src]", values["src"])
        if tag == "object":
            for attr in ("data", "src"):
                if attr in values:
                    self._record(f"object[{attr}]", values[attr])
        if tag == "embed" and "src" in values:
            self._record("embed[src]", values["src"])
        if tag in _SVG_RESOURCE_TAGS:
            for attr in ("href", "xlink:href"):
                if attr in values:
                    self._record(f"svg {tag}[{attr}]", values[attr])
        if tag == "link" and "href" in values:
            rels = set(values.get("rel", "").casefold().split())
            if rels & _RESOURCE_LINK_RELS or values.get("as", "").casefold() == "font":
                self._record("link[href]", values["href"])
        if tag == "link" and "imagesrcset" in values:
            for ref in _srcset_urls(values["imagesrcset"]):
                self._record("link[imagesrcset]", ref)
        if tag == "form" and "action" in values:
            self._record("form[action]", values["action"])
        if tag in {"button", "input"} and "formaction" in values:
            self._record(f"{tag}[formaction]", values["formaction"])
        if tag == "base" and "href" in values:
            self._block("base[href]", values["href"] or "<boş>")
        if tag == "meta" and values.get("http-equiv", "").casefold() == "refresh":
            self._block("meta[http-equiv=refresh]", values.get("content", "<boş>"))
        if tag == "html" and "manifest" in values:
            self._record("html[manifest]", values["manifest"])
        if "background" in values:
            self._record(f"{tag}[background]", values["background"])
        if "ping" in values:
            for ref in values["ping"].split():
                self._record(f"{tag}[ping]", ref)
        if self._svg_depth or tag == "svg":
            for attr, value in values.items():
                if attr == "style":
                    continue
                for where, ref in _css_resource_refs(value):
                    self._record(f"svg {tag}[{attr}] {where}", ref)
        if "style" in values:
            for where, ref in _css_resource_refs(values["style"]):
                self._record(f"style attribute {where}", ref)
        for attr, value in values.items():
            if attr.startswith("on"):
                for issue in _js_runtime_loaders(value):
                    self._block(f"{tag}[{attr}]", issue)

    def handle_starttag(self, tag, attrs):
        self._tag(tag, attrs)
        folded = tag.casefold()
        if folded == "style":
            self._style_depth += 1
        if folded == "script":
            self._script_depth += 1
        if folded == "svg":
            self._svg_depth += 1

    def handle_startendtag(self, tag, attrs):
        self._tag(tag, attrs)

    def handle_data(self, data):
        if self._style_depth:
            self._style_chunks.append(data)
        if self._script_depth:
            self._script_chunks.append(data)

    def handle_endtag(self, tag):
        folded = tag.casefold()
        if folded == "style" and self._style_depth:
            self._style_depth -= 1
            if not self._style_depth:
                css = "".join(self._style_chunks)
                self._style_chunks = []
                for where, ref in _css_resource_refs(css):
                    self._record(where, ref)
        if folded == "script" and self._script_depth:
            self._script_depth -= 1
            if not self._script_depth:
                js = "".join(self._script_chunks)
                self._script_chunks = []
                for issue in _js_runtime_loaders(js):
                    self._block("script", issue)
        if folded == "svg" and self._svg_depth:
            self._svg_depth -= 1


def gate_selfcontained(html, R):
    """G-SELFCONTAINED: runtime kaynakları yalnız inline/data olmalı (FAIL)."""
    parser = _SelfContainedParser()
    try:
        parser.feed(html)
        parser.close()
    except (TypeError, ValueError) as exc:
        R.add("G-SELFCONTAINED", "FAIL", f"HTML kaynak taraması tamamlanamadı: {exc}")
        return
    if parser.bad:
        R.add(
            "G-SELFCONTAINED",
            "FAIL",
            "satır içi/data olmayan runtime bağımlılığı: " + "; ".join(parser.bad[:6]),
        )
    else:
        R.add(
            "G-SELFCONTAINED",
            "PASS",
            "Runtime varlıkları satır içi/data URI; yerel veya ağ bağımlılığı yok.",
        )

def gate_contrast(html, R):
    """G-CONTRAST: gövde metni text-primary, aksanın küçük metinde kullanımını uyarır (WARN)."""
    # heuristik: gövde metni aksan rengiyle mi boyanmış? (küçük metinde aksan riski)
    warn=[]
    # body color aksan değil text-primary olmalı
    if re.search(r'body\s*\{[^}]*color\s*:\s*var\(--accent', html):
        warn.append("gövde metni aksan rengiyle boyanmış (kontrast riski)")
    if not re.search(r'color\s*:\s*var\(--cds-text-primary\)', html):
        warn.append("--cds-text-primary metin rengi olarak kullanılmamış")
    if warn:
        R.add("G-CONTRAST","WARN","; ".join(warn)+" — küçük metin daima text-primary olmalı.")
    else:
        R.add("G-CONTRAST","PASS","Metin rengi token'ı uygun; aksan büyük/dolgu öğelerinde.")

def gate_wellbeing(html, R):
    """G-WELLBEING: DEHB klinik kanıtına dayalı sorumlu/etik kullanım kapısı.

    - Cezalandırıcı / süre-baskısı dili → FAIL. DEHB'de duygu-düzenleme kırılganlığı
      (Groves 2021) ve oyun-bağımlılığı yatkınlığı (Rodrigo-Yanguas 2022) nedeniyle
      başarısızlık/zaman baskısı dili kullanılmaz.
    - >=6 segmentlik modülde beyin molası yoksa → WARN (Zhu 2023 NMA; ped §4).
    - prefers-reduced-motion yoksa → WARN (aşırı-uyarım; A11Y ile örtüşür).
    """
    punitive = re.compile(
        r"(kaybettin|kaybettiniz|s\u00fcre doldu|s\u00fcren doldu|s\u00fcreniz doldu|"
        r"zaman doldu|game over|oyun bitti|ba\u015far\u0131s\u0131z oldun)", re.IGNORECASE)
    hits = sorted(set(m.group(0).lower() for m in punitive.finditer(html)))
    warns = []
    types = re.findall(r'type\s*:\s*"([a-z]+)"', html)
    total = len(types); breaks = types.count("brainbreak")
    if total >= 6 and breaks == 0:
        warns.append(f"{total} segmentte beyin molası yok — uzun modülde en az 1 brainbreak önerilir")
    if "prefers-reduced-motion" not in html:
        warns.append("prefers-reduced-motion bildirimi yok")
    if hits:
        R.add("G-WELLBEING","FAIL","cezalandırıcı/süre-baskısı dili: "+", ".join(hits))
    elif warns:
        R.add("G-WELLBEING","WARN","; ".join(warns))
    else:
        R.add("G-WELLBEING","PASS","Cezalandırıcı/süre-baskısı dili yok; mola ritmi ve hareket-azaltma uygun.")

SVG_BLOCK_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.S | re.I)
def _svg_decorative(open_tag):
    """Sprite / @carbon ikon / piktogram gibi salt-dekor SVG mi?"""
    return ('aria-hidden="true"' in open_tag or "display:none" in open_tag
            or "cds-icon" in open_tag or 'class="pic"' in open_tag)

def _svg_accessible(block, open_tag):
    """Figür SVG erişilebilir mi: role=\"img\" + başlık/etiket."""
    has_role  = 'role="img"' in open_tag
    has_label = ("<title" in block) or ("aria-label=" in open_tag) or ("aria-labelledby=" in open_tag)
    return has_role and has_label

def _svg_report(R, checked, fails, warns):
    """G-SVG sonucunu Result'a yazar."""
    if checked == 0:
        R.add("G-SVG","PASS","Figür SVG yok; yalnız dekoratif ikon/sprite mevcut.", applicable=False)
    elif fails:
        R.add("G-SVG","FAIL", f"{len(fails)} figür SVG erişilemez: " + "; ".join(fails[:3]))
    elif warns:
        R.add("G-SVG","WARN", "; ".join(sorted(set(warns))) + f" ({checked} figür SVG denetlendi)")
    else:
        R.add("G-SVG","PASS", f"{checked} figür SVG erişilebilir ve tema-duyarlı (role+başlık, token renk).")

def _strip_comments_for_svg_scan(html):
    """G-SVG taraması için yorum-körlüğünü giderir: HTML ve JS blok yorumlarını
    çalışma kopyasından siler (yalnız bu tarama için — diğer gate'ler orijinal
    html'i görmeye devam eder). `//` satır yorumları KASTEN silinmez (URL'leri
    bozar, ör. https://)."""
    stripped = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
    return stripped

def gate_svg(html, R):
    """Figür SVG'leri erişilebilir (role=img + başlık) ve tema-duyarlı (token renk) olmalı.

    Dekoratif SVG'ler (sprite, @carbon ikon/piktogram) aria-hidden / cds-icon / class=pic
    ile dışlanır; yalnız diyagram ve grafik figürleri denetlenir. Tarama, HTML/JS yorumları
    içindeki örnek <svg> parçalarını yok saymak için yorum-körlüğü giderilmiş bir çalışma
    kopyası üzerinde çalışır (bkz. _strip_comments_for_svg_scan).
    """
    fails=[]; warns=[]; checked=0
    scan_html = _strip_comments_for_svg_scan(html)
    for b in SVG_BLOCK_RE.findall(scan_html):
        open_tag = b[:b.find(">")+1]
        if _svg_decorative(open_tag):
            continue
        checked += 1
        if not _svg_accessible(b, open_tag):
            fails.append('role="img"+<title>/aria eksik (' + re.sub(r"\s+", " ", open_tag)[:60] + "…)")
        if re.search(r'(?:fill|stroke)="#', b):
            warns.append('ham hex renk (fill/stroke="#…") yerine var(--…)/currentColor kullanın')
    _svg_report(R, checked, fails, warns)

def _audio_earcon_issues(html):
    """Earcon/ses-efekti katmanının güvenlik ihlallerini toplar (susturma, autoplay, loop)."""
    issues=[]
    if not re.search(r'state\.sound|toggleSound|id="soundBtn"', html):
        issues.append("earcon: susturma kontrolü yok (state.sound/toggleSound/#soundBtn)")
    if re.search(r"<audio[^>]*\bautoplay", html) or re.search(r"<video[^>]*\bautoplay", html):
        issues.append("earcon: autoplay ile otomatik ses")
    if re.search(r"\bloop\s*[:=]\s*true", html) or re.search(r"\.loop\s*=\s*true", html):
        issues.append("earcon: döngülü (loop) ses — sürekli arka plan sesi yasak")
    return issues


def _audio_tts_issues(html):
    """Sesli-okuma/TTS katmanının güvenlik ihlallerini toplar (kontrol, durdurma, varsayılan kapalı)."""
    issues=[]
    if not re.search(r'toggleTTS|id="ttsBtn"|#ttsBtn|state\.tts', html):
        issues.append("TTS: kullanıcı kontrolü yok (toggleTTS/#ttsBtn/state.tts)")
    if ".cancel(" not in html:
        issues.append("TTS: konuşma durdurma yok (speechSynthesis.cancel)")
    if not re.search(r'data-tts["\']\s*,\s*["\']off', html):
        issues.append('TTS: varsayılan kapalı değil (init data-tts="off" ayarı bulunamadı)')
    return issues


def _audio_pass_msg(uses_earcon, uses_tts):
    """G-AUDIO başarı mesajını üretir (kullanılan katmanlara göre)."""
    layers=[]
    if uses_earcon: layers.append("earcon susturulabilir")
    if uses_tts: layers.append("TTS kullanıcı-denetimli/durdurulabilir, varsayılan kapalı")
    return ("İşitsel katman(lar) güvenli ("+", ".join(layers)
            +"); reduced-motion duyarlı, otomatik-oynatma/döngü yok.")


def gate_audio(html, R):
    """G-AUDIO: işitsel katmanlar (earcon + sesli-okuma/TTS) opsiyonel, susturulabilir/durdurulabilir,
    reduced-motion duyarlı ve varsayılan kapalı olmalı; sürekli arka plan sesi (autoplay/loop) yasak (FAIL).

    DEHB'de sürekli/alakasız işitsel uyaran dağıtıcıdır; kısa olay-earcon'ları geçici uyarıcı etki
    sağlayabilir, metin-konuşma (TTS) ise kod-çözme yükünü azaltıp dinleme-anlama ile okumayı eşleştirir
    — ANCAK her iki katman da opsiyonel, kullanıcı-denetimli ve varsayılan kapalı olmalı; otomatik-oynatma,
    döngü ve istem-dışı otomatik okuma yasaktır. İki katman ayrı ayrı denetlenir.
    """
    uses_earcon = bool(re.search(r"\b(?:webkit)?AudioContext\b", html)) or ("<audio" in html)
    uses_tts    = bool(re.search(r"\bspeechSynthesis\b", html)) or ("SpeechSynthesisUtterance" in html)
    if not uses_earcon and not uses_tts:
        R.add("G-AUDIO","PASS","İşitsel katman kullanılmıyor (uygulanmaz).", applicable=False)
        return
    issues=[]
    if "prefers-reduced-motion" not in html:
        issues.append("prefers-reduced-motion referansı yok")
    if uses_earcon:
        issues += _audio_earcon_issues(html)
    if uses_tts:
        issues += _audio_tts_issues(html)
    if issues:
        R.add("G-AUDIO","FAIL","; ".join(issues))
    else:
        R.add("G-AUDIO","PASS",_audio_pass_msg(uses_earcon, uses_tts))

def _curriculum_collect(block, html):
    """curriculum bloğundan kazanım kodlarını, text sayısını ve mappedTo→segment
    eşleme durumunu toplar. (gate_curriculum karmaşıklığını düşürmek için ayrıldı.)

    Döndürür: (codes, n_texts, mapped_ids, missing_ids)
    """
    codes = re.findall(r'\bcode\s*:\s*["\']([^"\']+)["\']', block)
    n_texts = len(re.findall(r'\btext\s*:', block))
    mapped_ids = set()
    for arr in re.findall(r'mappedTo\s*:\s*\[([^\]]*)\]', block):
        mapped_ids |= set(re.findall(r'["\']([^"\']+)["\']', arr))
    all_ids = set(re.findall(r'\bid\s*:\s*["\']([^"\']+)["\']', html))
    missing = [mid for mid in sorted(mapped_ids) if mid not in all_ids]
    return codes, n_texts, mapped_ids, missing


def _curriculum_cite_ok(html):
    """meta.sourceCitation kazanım kodu (FB.5.3.1.1) veya korpus/MCP anahtarı içeriyor mu."""
    cite_m = re.search(r'sourceCitation\s*:\s*["\']?(.*?)["\']?\s*\n', html, re.S)
    cite = cite_m.group(1) if cite_m else ""
    return bool(re.search(r'[A-ZÇĞİÖŞÜ]{1,4}\.\d', cite)) or \
           bool(re.search(r'(?i)(müfredat|maarif|corpus|kazanım|tymm)', cite))


def _curriculum_eval(codes, n_texts, mapped_ids, missing, cite_ok):
    """Toplanan sinyallerden (issues, warns) listelerini üretir. Saf karar mantığı."""
    issues=[]; warns=[]
    if not codes:
        issues.append("curriculum.outcomes[] boş veya `code` içermiyor")
    if n_texts < len(codes):
        warns.append(f"{len(codes)} kazanımdan {n_texts} tanesinde `text` var (her kazanımda metin önerilir)")
    if mapped_ids and missing:
        issues.append("mappedTo segment id'si segments[]'te yok: "+", ".join(missing[:5]))
    if not mapped_ids and codes:
        warns.append("hiçbir kazanım segmente bağlanmamış (mappedTo eksik) — izlenebilirlik zayıf")
    if not cite_ok:
        warns.append("meta.sourceCitation kazanım kodu/korpus referansı içermiyor")
    return issues, warns


_CARBON_AUTHORITY = {
    # @carbon/themes 11.75.0 — çekirdek token otorite haritası (white | g100).
    # Kaynak: assets/carbon-v11-authority.json (scripts/sync_carbon_tokens.py üretir).
    "white": {
        "--cds-background":"#ffffff","--cds-layer-01":"#f4f4f4","--cds-layer-02":"#ffffff",
        "--cds-layer-03":"#f4f4f4","--cds-border-subtle-00":"#e0e0e0","--cds-border-subtle-01":"#c6c6c6",
        "--cds-border-strong":"#8d8d8d","--cds-text-primary":"#161616","--cds-text-secondary":"#525252",
        "--cds-interactive":"#0f62fe","--cds-link-primary":"#0f62fe","--cds-focus":"#0f62fe",
        "--cds-button-primary":"#0f62fe","--cds-button-primary-hover":"#0050e6",
        "--cds-button-primary-active":"#002d9c","--cds-support-success":"#24a148",
        "--cds-support-error":"#da1e28","--cds-support-warning":"#f1c21b","--cds-support-info":"#0043ce",
    },
    "g100": {
        "--cds-background":"#161616","--cds-layer-01":"#262626","--cds-layer-02":"#393939",
        "--cds-layer-03":"#525252","--cds-border-subtle-00":"#393939","--cds-border-subtle-01":"#525252",
        "--cds-border-strong":"#6f6f6f","--cds-text-primary":"#f4f4f4","--cds-text-secondary":"#c6c6c6",
        "--cds-interactive":"#4589ff","--cds-link-primary":"#78a9ff","--cds-focus":"#ffffff",
        "--cds-button-primary":"#0f62fe","--cds-button-primary-hover":"#0050e6",
        "--cds-button-primary-active":"#002d9c","--cds-support-success":"#42be65",
        "--cds-support-error":"#fa4d56","--cds-support-warning":"#f1c21b","--cds-support-info":"#4589ff",
    },
}

def _theme_block(html, selector):
    """Verilen tema seçicisinin ilk CSS bloğunu döndürür (yoksa '')."""
    i = html.find(selector)
    if i < 0: return ""
    j = html.find("{", i); k = html.find("}", j)
    return html[j+1:k] if j >= 0 and k >= 0 else ""

def _classify_token(theme, tok, val, block, norm):
    """Tek bir --cds-* token'ını otoriteyle karşılaştırır.

    Döndürür: (drift_item, fail_item). Token tanımsız, alias (var(...)) veya
    otoriteyle birebirse her ikisi de None'dur. white/support-info #4589ff
    bilinen AA-kontrast regresyonu fail_item olarak işaretlenir.
    """
    m = re.search(re.escape(tok) + r"\s*:\s*([^;}]+)", block)
    if not m:
        return None, None  # tanımsız token denetlenmez (eksiklik G-CARBON'un işi)
    got = norm(m.group(1))
    if got.startswith("var("):
        return None, None  # alias kabul
    if got == norm(val):
        return None, None
    item = f"{theme} {tok}: {m.group(1).strip()} (otorite: {val})"
    if theme == "white" and tok == "--cds-support-info" and got == "#4589ff":
        return None, item + " — AA kontrast regresyonu"
    return item, None


def gate_token_authority(html, R):
    """G-TOKEN: tanımlı çekirdek --cds-* token'larının @carbon/themes otorite
    değerleriyle eşleştiğini denetler. Sapma = WARN (eski modüllerle geriye uyum);
    bilinen AA regresyonu (white'ta support-info #4589ff) = FAIL."""
    drift, fail = [], []
    blocks = {"white": _theme_block(html, '[data-theme="white"]') or _theme_block(html, ":root"),
              "g100":  _theme_block(html, '[data-theme="g100"]')}
    norm = lambda v: re.sub(r"\s+", "", v).lower().replace("0.", ".")
    for theme, expect in _CARBON_AUTHORITY.items():
        block = blocks.get(theme, "")
        if not block: continue
        for tok, val in expect.items():
            d, f = _classify_token(theme, tok, val, block, norm)
            if d: drift.append(d)
            if f: fail.append(f)
    if fail:
        R.add("G-TOKEN","FAIL","otorite ihlali: " + "; ".join(fail))
    elif drift:
        R.add("G-TOKEN","WARN", f"{len(drift)} token otoriteden sapıyor: " + "; ".join(drift[:4]) +
              (" …" if len(drift) > 4 else "") + " — scripts/sync_carbon_tokens.py --check ile ayrıntı.")
    else:
        R.add("G-TOKEN","PASS","Çekirdek --cds-* token'ları @carbon/themes 11.75.0 ile birebir.")

def gate_curriculum(html, R):
    """G-CURRICULUM (koşullu): Müfredat-temelli modüllerde kazanım izlenebilirliği.

    Yalnız mod CURRICULUM ise veya bir `curriculum` bloğu varsa tetiklenir; aksi
    halde atlanır (geriye dönük uyum — mevcut MCP'siz modüller etkilenmez).

    Denetler:
    - mode:"CURRICULUM" ise `curriculum` bloğu zorunlu (yoksa FAIL).
    - `curriculum.outcomes[]` boş olmamalı; her öğede `code` ve `text` (FAIL/WARN).
    - Her `outcomes[].mappedTo` segment id'si `segments[]` içinde tanımlı bir
      id'ye karşılık gelmeli (kazanım→segment izlenebilirliği; eksikse FAIL).
    - meta.sourceCitation kazanım kodu/korpus referansı içermeli (eksikse WARN).

    Not: Salt-metin (regex/heuristik) denetimdir; MODULE_DATA JS nesnesi parse
    edilmez. `curriculum` ve `mode` sinyalleri metin örüntüsüyle tespit edilir.
    """
    is_curr_mode = bool(re.search(r'\bmode\s*:\s*["\']CURRICULUM["\']', html))
    has_curr_block = bool(re.search(r'\bcurriculum\s*:\s*\{', html))
    if not is_curr_mode and not has_curr_block:
        R.add("G-CURRICULUM","PASS","Müfredat-temelli modül değil (uygulanmaz).", applicable=False)
        return
    if is_curr_mode and not has_curr_block:
        R.add("G-CURRICULUM","FAIL",
              "mode CURRICULUM ama `curriculum` bloğu yok; kazanım provenansı zorunlu.")
        return

    block_m = re.search(r'curriculum\s*:\s*\{(.*?)\n\s*\}\s*,?\s*\n', html, re.S)
    block = block_m.group(1) if block_m else html
    codes, n_texts, mapped_ids, missing = _curriculum_collect(block, html)
    issues, warns = _curriculum_eval(codes, n_texts, mapped_ids, missing,
                                     _curriculum_cite_ok(html))

    if issues:
        R.add("G-CURRICULUM","FAIL","; ".join(issues))
    elif warns:
        R.add("G-CURRICULUM","WARN","; ".join(warns)
              + f" ({len(codes)} kazanım, {len(mapped_ids)} segment-eşleme denetlendi)")
    else:
        R.add("G-CURRICULUM","PASS",
              f"{len(codes)} kazanım segmente izlenebilir; kaynak damgalı.")

_JSISH_SCAN_LIMIT = 4 * 1024 * 1024
_JSISH_VALUE_LIMIT = 2 * 1024 * 1024
_JSISH_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_VERIFY_FRAME_KINDS = {"textbook", "program"}
_VERIFY_VERDICTS = {
    "supported",
    "supported_by_program",
    "supported_by_source",
    "general_knowledge",
    "unsupported",
    "unverified",
}


class _JSishError(ValueError):
    """MODULE_DATA'nın güvenle ayrıştırılamayan sınırlı JS-ish alt-kümesi."""


def _jsish_skip(text, index, end=None):
    """Boşluk ve JS yorumlarını doğrusal zamanda atlar."""
    end = len(text) if end is None else end
    while index < end:
        if text[index].isspace():
            index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index + 2, end)
            index = end if newline < 0 else newline + 1
            continue
        if text.startswith("/*", index):
            close = text.find("*/", index + 2, end)
            if close < 0:
                raise _JSishError("kapanmamış blok yorumu")
            index = close + 2
            continue
        break
    return index


def _jsish_string(text, start, end=None):
    """JS tek/çift/backtick string'ini, kaçışları yorumlamadan güvenle geçer."""
    end = len(text) if end is None else end
    quote = text[start]
    chars = []
    index = start + 1
    while index < end:
        ch = text[index]
        if ch == "\\":
            if index + 1 >= end:
                raise _JSishError("string sonunda kaçış")
            escaped = text[index + 1]
            chars.append({
                "n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v",
            }.get(escaped, escaped))
            index += 2
            continue
        if ch == quote:
            return "".join(chars), index + 1
        chars.append(ch)
        index += 1
    raise _JSishError("kapanmamış string")


def _jsish_balanced_end(text, start, end=None):
    """Nesne/dizi/parantezi string ve yorumları saymadan dengeli kapatır."""
    end = len(text) if end is None else end
    pairs = {"{": "}", "[": "]", "(": ")"}
    opener = text[start]
    if opener not in pairs:
        raise _JSishError("dengeli değer açılış karakteri değil")
    hard_end = min(end, start + _JSISH_VALUE_LIMIT)
    stack = [opener]
    index = start + 1
    while index < hard_end:
        index = _jsish_skip(text, index, hard_end)
        if index >= hard_end:
            break
        ch = text[index]
        if ch in "\"'`":
            _, index = _jsish_string(text, index, hard_end)
            continue
        if ch in pairs:
            stack.append(ch)
        elif ch in "}])":
            if not stack or pairs[stack[-1]] != ch:
                raise _JSishError("uyumsuz kapanış karakteri")
            stack.pop()
            if not stack:
                return index + 1
        index += 1
    if hard_end < end:
        raise _JSishError("JS-ish değer izin verilen boyutu aşıyor")
    raise _JSishError("dengesiz JS-ish değer")


def _jsish_value_end(text, start, end):
    """Bir nesne üyesi/dizi öğesinin üst-seviye virgülden önceki sonunu bulur."""
    index = start
    stack = []
    pairs = {"{": "}", "[": "]", "(": ")"}
    while index < end:
        index = _jsish_skip(text, index, end)
        if index >= end:
            break
        ch = text[index]
        if ch in "\"'`":
            _, index = _jsish_string(text, index, end)
            continue
        if ch in pairs:
            stack.append(ch)
        elif ch in "}])":
            if stack and pairs[stack[-1]] == ch:
                stack.pop()
        elif ch == "," and not stack:
            return index
        index += 1
    return index


def _jsish_members(inner):
    """Bir JS-ish nesne içeriğini üst-seviye anahtar → ham değer haritasına çevirir."""
    members = {}
    index = 0
    end = len(inner)
    while True:
        index = _jsish_skip(inner, index, end)
        while index < end and inner[index] == ",":
            index = _jsish_skip(inner, index + 1, end)
        if index >= end:
            return members
        if inner[index] in "\"'":
            key, index = _jsish_string(inner, index, end)
        else:
            match = _JSISH_IDENTIFIER_RE.match(inner, index)
            if not match:
                raise _JSishError(f"nesne anahtarı okunamadı (indeks {index})")
            key = match.group(0)
            index = match.end()
        index = _jsish_skip(inner, index, end)
        if index >= end or inner[index] != ":":
            raise _JSishError(f"`{key}` anahtarından sonra ':' yok")
        start = _jsish_skip(inner, index + 1, end)
        stop = _jsish_value_end(inner, start, end)
        if key in members:
            raise _JSishError(f"yinelenen `{key}` anahtarı")
        members[key] = inner[start:stop].strip()
        index = stop + 1 if stop < end and inner[stop] == "," else stop


def _jsish_object(raw):
    """Ham değer tam bir nesne ise üyelerini, değilse None döndürür."""
    if raw is None:
        return None
    start = _jsish_skip(raw, 0)
    if start >= len(raw) or raw[start] != "{":
        return None
    stop = _jsish_balanced_end(raw, start)
    if _jsish_skip(raw, stop) != len(raw):
        return None
    return _jsish_members(raw[start + 1:stop - 1])


def _jsish_array(raw):
    """Ham değer tam bir dizi ise üst-seviye öğelerini, değilse None döndürür."""
    if raw is None:
        return None
    start = _jsish_skip(raw, 0)
    if start >= len(raw) or raw[start] != "[":
        return None
    stop = _jsish_balanced_end(raw, start)
    if _jsish_skip(raw, stop) != len(raw):
        return None
    inner = raw[start + 1:stop - 1]
    items = []
    index = 0
    while True:
        index = _jsish_skip(inner, index)
        while index < len(inner) and inner[index] == ",":
            index = _jsish_skip(inner, index + 1)
        if index >= len(inner):
            return items
        item_end = _jsish_value_end(inner, index, len(inner))
        value = inner[index:item_end].strip()
        if value:
            items.append(value)
        index = item_end + 1 if item_end < len(inner) else item_end


def _jsish_literal(raw):
    """String(ler) veya basit scalar değeri yan etkisiz metne çevirir; kodu reddeder."""
    if raw is None:
        return None
    index = _jsish_skip(raw, 0)
    if index >= len(raw):
        return ""
    if raw[index] not in "\"'`":
        value = raw[index:].strip()
        if re.fullmatch(r"(?:-?\d+(?:\.\d+)?|true|false|null|undefined)", value):
            return value
        return None
    parts = []
    while index < len(raw):
        if raw[index] not in "\"'`":
            return None
        if raw[index] == "`" and _jsish_template_interpolates(raw, index):
            return None
        part, index = _jsish_string(raw, index)
        parts.append(part)
        index = _jsish_skip(raw, index)
        if index >= len(raw):
            return "".join(parts)
        if raw[index] != "+":
            return None
        index = _jsish_skip(raw, index + 1)
    return "".join(parts)


def _jsish_template_interpolates(text, start):
    """Backtick literalinde kaçış-dışı `${...}` ifadesi var mı?"""
    index = start + 1
    while index < len(text):
        if text[index] == "\\" and index + 1 < len(text):
            index += 2
            continue
        if text.startswith("${", index):
            return True
        if text[index] == "`":
            return False
        index += 1
    return True


def _jsish_scalar(raw):
    """JS-ish basit değeri türünü koruyarak döndürür; kod/nesne için invalid."""
    if raw is None:
        return "missing", None
    index = _jsish_skip(raw, 0)
    if index >= len(raw):
        return "string", ""
    if raw[index] in "\"'`":
        value = _jsish_literal(raw)
        return ("string", value) if value is not None else ("invalid", None)
    value = raw[index:].strip()
    if re.fullmatch(r"-?\d+", value):
        return "integer", int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return "number", float(value)
    if value == "true":
        return "boolean", True
    if value == "false":
        return "boolean", False
    if value in {"null", "undefined"}:
        return "null", None
    return "invalid", None


def _jsish_bool(raw):
    kind, value = _jsish_scalar(raw)
    if kind == "boolean":
        return value
    return None


def _field(members, key):
    kind, value = _jsish_scalar(members.get(key) if members is not None else None)
    if kind == "string":
        return value.strip()
    if kind == "integer":
        return str(value)
    return ""


def _normalized_provenance_text(value):
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.replace("ı", "i")


def _is_placeholder(value):
    """Künye/provenans alanlarında ortak boş ve placeholder denetimi."""
    if not isinstance(value, str) or not value.strip():
        return True
    normalized = _normalized_provenance_text(value.strip())
    strict = re.search(
        r"(?:^|[^a-z0-9])(?:tbd|unknown|todo|placeholder|replace)"
        r"(?:$|[^a-z0-9])"
        r"|(?:^|[^a-z0-9])n[\s/-]*a(?:$|[^a-z0-9])"
        r"|buraya\s+yaz",
        normalized,
    )
    if strict:
        return True
    trimmed = re.sub(r"^[^a-z0-9]+|[^a-z0-9]+$", "", normalized)
    if re.fullmatch(r"(?:(?:kaynak|source|citation)\s*[:=-]?\s*)?ornek", trimmed):
        return True
    return bool(re.search(
        r"(?:^|[^a-z0-9])ornek\s+(?:kaynak|metin|citation)(?:$|[^a-z0-9])",
        normalized,
    ))


def _text_scalar(raw):
    kind, value = _jsish_scalar(raw)
    if kind != "string" or _is_placeholder(value):
        return None
    return value.strip()


def _identity_scalar(raw):
    """Belge/kaynak kimliği: pozitif tamsayı veya gerçek, placeholder olmayan dizgi."""
    kind, value = _jsish_scalar(raw)
    if kind == "integer" and value > 0:
        return value
    if kind == "string" and not _is_placeholder(value):
        return value.strip()
    return None


_LOCATOR_HINT_RE = re.compile(
    r"\d|sayfa|page|pages|bölüm|bolum|section|chapter|madde|paragraf|"
    r"şekil|sekil|figure|tablo|table|başlık|baslik",
    re.I,
)


def _locator_scalar(members):
    """Pozitif sayfa veya kesin/izlenebilir yapısal locator döndürür."""
    if not members:
        return ""
    if "page" in members:
        kind, value = _jsish_scalar(members["page"])
        if kind == "integer" and value > 0:
            return f"page:{value}"
    if "pages" in members:
        kind, value = _jsish_scalar(members["pages"])
        if kind == "integer" and value > 0:
            return f"pages:{value}"
        if (
            kind == "string"
            and not _is_placeholder(value)
            and re.fullmatch(r"\s*\d+\s*(?:[-–]\s*\d+\s*)?", value)
        ):
            return f"pages:{value.strip()}"
    if "locator" in members:
        value = _text_scalar(members["locator"])
        if value and _LOCATOR_HINT_RE.search(value):
            return f"locator:{value}"
    if "url" in members:
        value = _text_scalar(members["url"])
        if value and re.match(r"https?://\S+$", value, re.I):
            return f"url:{value}"
    return ""


class _ScriptCollector(HTMLParser):
    """MODULE_DATA araması için yalnız gerçek inline <script> gövdelerini toplar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_script = False
        self.current = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag.casefold() == "script":
            self.in_script = True
            self.current = []

    def handle_data(self, data):
        if self.in_script:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.casefold() == "script" and self.in_script:
            self.scripts.append("".join(self.current))
            self.in_script = False
            self.current = []


def _assignment_object(script, name):
    """name = {...} atamasını yorum/string dışından bulur."""
    if len(script) > _JSISH_SCAN_LIMIT:
        raise _JSishError("script izin verilen boyutu aşıyor")
    index = 0
    while index < len(script):
        index = _jsish_skip(script, index)
        if index >= len(script):
            break
        if script[index] in "\"'`":
            _, index = _jsish_string(script, index)
            continue
        match = _JSISH_IDENTIFIER_RE.match(script, index)
        if not match:
            index += 1
            continue
        token = match.group(0)
        index = match.end()
        if token != name:
            continue
        cursor = _jsish_skip(script, index)
        if cursor >= len(script) or script[cursor] != "=":
            continue
        cursor = _jsish_skip(script, cursor + 1)
        if cursor >= len(script) or script[cursor] != "{":
            continue
        stop = _jsish_balanced_end(script, cursor)
        return script[cursor:stop]
    return None


def _module_members(html):
    """MODULE_DATA nesnesini HTML yorum/prosesinden ayırarak güvenle çıkarır."""
    parser = _ScriptCollector()
    parser.feed(html)
    parser.close()
    for script in parser.scripts:
        raw = _assignment_object(script, "MODULE_DATA")
        if raw is not None:
            return _jsish_object(raw)
    return None


def _citation_issue(module):
    """Her modda zorunlu sourceCitation'ın boş/placeholder olmadığını denetler."""
    meta = _jsish_object(module.get("meta")) if module else None
    if meta is None or "sourceCitation" not in meta:
        return "meta.sourceCitation eksik veya boş; gerçek kaynak künyesi her modda zorunlu"
    kind, citation = _jsish_scalar(meta["sourceCitation"])
    if kind != "string" or not citation.strip():
        return "meta.sourceCitation metin olmalı ve boş bırakılamaz"
    if _is_placeholder(citation):
        return "meta.sourceCitation placeholder içeriyor; gerçek kaynak künyesi yazılmalı"
    return None


def _verify_collect(raw):
    """Dengeli ayrıştırılmış verification yapısını alan alan toplar."""
    issues = []
    warns = []
    verification = _jsish_object(raw)
    if verification is None:
        return ["verification bir nesne olmalı"], warns

    frame = _jsish_object(verification.get("frame_source"))
    frame_kind = _field(frame, "kind")
    if frame is None:
        issues.append("verification.frame_source boş veya nesne değil")
    else:
        if frame_kind not in _VERIFY_FRAME_KINDS:
            issues.append(
                "verification.frame_source.kind `textbook` | `program` olmalı "
                f"(bulunan: {frame_kind or '—'})"
            )
        if _identity_scalar(frame.get("document_id")) is None:
            issues.append("verification.frame_source document_id pozitif tamsayı veya "
                          "gerçek belge kimliği olmalı")
        if not _locator_scalar(frame):
            issues.append("verification.frame_source pozitif sayfa veya kesin locator taşımıyor")

    scope = _jsish_object(verification.get("scope"))
    in_frame = _jsish_bool(scope.get("in_frame")) if scope else None
    if in_frame is None:
        issues.append("verification.scope.in_frame yok")
    elif not in_frame:
        issues.append("scope.in_frame:false — içerik müfredat/ders kitabı çerçevesinin "
                      "DIŞINDA; yayınlanamaz")

    claim_values = _jsish_array(verification.get("claims"))
    if not claim_values:
        issues.append("verification.claims[] boş — her olgusal iddia dayanağıyla listelenmeli")
        return issues, warns

    n_general = 0
    n_source = 0
    n_unverified = 0
    for number, raw_claim in enumerate(claim_values, 1):
        claim = _jsish_object(raw_claim)
        prefix = f"claims[{number}]"
        if claim is None:
            issues.append(f"{prefix} nesne değil")
            continue
        claim_kind, claim_text = _jsish_scalar(claim.get("claim"))
        if claim_kind != "string" or not claim_text.strip():
            issues.append(f"{prefix}.claim boş veya yok")
        verdict = _field(claim, "verdict")
        if verdict not in _VERIFY_VERDICTS:
            issues.append(
                f"{prefix}.verdict bilinmiyor: {verdict or '—'} "
                f"(izinli: {', '.join(sorted(_VERIFY_VERDICTS))})"
            )
            continue
        grounding = _jsish_object(claim.get("grounding"))
        if grounding is None or not grounding:
            issues.append(f"{prefix}.grounding boş veya yok (dayanaksız iddia geçemez)")
            continue
        if verdict in {"supported", "supported_by_program"}:
            if _identity_scalar(grounding.get("document_id")) is None:
                issues.append(
                    f"{prefix}.{verdict} grounding document_id pozitif tamsayı veya "
                    "gerçek belge kimliği değil"
                )
            if not _locator_scalar(grounding):
                issues.append(
                    f"{prefix}.{verdict} grounding pozitif sayfa veya kesin locator taşımıyor"
                )
        elif verdict == "supported_by_source":
            n_source += 1
            if _identity_scalar(grounding.get("source")) is None:
                issues.append(f"{prefix}.supported_by_source kaynak künyesi taşımıyor")
            if not _locator_scalar(grounding):
                issues.append(
                    f"{prefix}.supported_by_source pozitif sayfa/kesin locator/URL taşımıyor"
                )
            if _text_scalar(grounding.get("license")) is None:
                issues.append(f"{prefix}.supported_by_source `license` taşımıyor")
            if (
                "provenance" in grounding
                and _text_scalar(grounding.get("provenance")) is None
            ):
                issues.append(
                    f"{prefix}.supported_by_source `provenance` placeholder/boş olamaz"
                )
        elif verdict == "general_knowledge":
            n_general += 1
        elif verdict == "unsupported":
            reason = _text_scalar(grounding.get("reason")) or _text_scalar(claim.get("reason"))
            issues.append(
                f"{prefix}.unsupported — kaynak iddiayı desteklemiyor"
                + (f" ({reason})" if reason else "; açık reason da eksik/placeholder")
            )
        elif verdict == "unverified":
            n_unverified += 1
            reason = _text_scalar(grounding.get("reason")) or _text_scalar(claim.get("reason"))
            if not reason:
                issues.append(f"{prefix}.unverified gerçek, placeholder olmayan reason taşımıyor")

    n_claims = len(claim_values)
    if n_general:
        ratio = n_general / n_claims
        msg = (f"{n_general}/{n_claims} iddia `general_knowledge` — "
               "ders kitabına/programa/kaynağa dayanmıyor")
        if ratio > 0.5:
            issues.append(msg + "; çoğunluk dayanaksız")
        else:
            warns.append(msg + "; kaynağını bul ya da çıkar")
    if n_unverified:
        warns.append(
            f"{n_unverified}/{n_claims} iddia unverified; açık gerekçe kayıtlı "
            "ama kaynak doğrulaması tamamlanmamış"
        )
    if n_source and frame_kind != "program":
        ratio = n_source / n_claims
        msg = (f"{n_source}/{n_claims} iddia `supported_by_source` ama çerçeve `program` değil "
               f"(kind:{frame_kind or '—'}) — alternatif-kaynak omurga yalnız ders kitabı "
               "OLMAYAN (program-çerçeveli) sınıflarda meşru")
        if ratio > 0.5:
            issues.append(msg + "; çoğunluk → ders kitabına dayan ya da çerçeveyi düzelt")
        else:
            warns.append(msg + "; ders kitabına dayan ya da çerçeveyi `program` yap")
    return issues, warns


def gate_verify(html, R):
    """G-VERIFY (koşullu): kapsam + doğruluk denetiminin KAYDI var mı.

    Kullanıcı sözleşmesi (2026-07-17): içerik, (a) müfredat/ders kitabı çerçevesinin içinde
    olduğu ve (b) bilimsel/eğitsel olarak doğru-tutarlı olduğu denetlenmeden canlıya alınmaz.

    YARGIYI MODEL YAPAR — Python "bilimsel olarak doğru mu" diye karar veremez. Bu kapı YAPIYI
    denetler: her iddianın dayanağı GÖSTERİLMİŞ mi. Değeri şudur: iddiayı yazmak dayanağını
    yazmayı zorunlu kılar, yani "denetledim" demek ucuzken "şu sayfada geçiyor" demek
    kontrol edilebilir hâle gelir.

    DENETLEYEMEZ (fazla güvenmeyin): document_id'nin gerçek olduğunu, kind:"textbook" yazan
    belgenin page_count>0 olduğunu, iddianın o sayfada geçtiğini, iddianın DOĞRU olduğunu —
    hiçbiri çevrimdışı ölçülemez (validator'ın MCP erişimi yok, G-CURRICULUM gibi salt-metin).
    Doğruluk yargısı modelin ve insan denetimine tabidir.
    """
    try:
        module = _module_members(html)
    except _JSishError as exc:
        R.add("G-VERIFY", "FAIL", f"MODULE_DATA güvenle ayrıştırılamadı: {exc}")
        return
    if module is None:
        R.add("G-VERIFY", "FAIL",
              "MODULE_DATA bulunamadı; meta.sourceCitation ve provenans doğrulanamadı")
        return
    citation_issue = _citation_issue(module)
    if citation_issue:
        R.add("G-VERIFY", "FAIL", citation_issue)
        return

    meta = _jsish_object(module.get("meta")) or {}
    mode = _field(module, "mode") or _field(meta, "mode")
    is_curr_mode = mode == "CURRICULUM"
    has_curr_block = "curriculum" in module
    if not is_curr_mode and not has_curr_block:
        R.add("G-VERIFY", "PASS", "Müfredat-temelli modül değil (uygulanmaz).", applicable=False)
        return
    if "verification" not in module:
        R.add("G-VERIFY", "FAIL",
              "Müfredat-temelli modül ama `verification` bloğu yok; kapsam + doğruluk "
              "denetiminin kaydı zorunlu (references/curriculum-integration.md §6.1).")
        return
    try:
        issues, warns = _verify_collect(module["verification"])
    except _JSishError as exc:
        R.add("G-VERIFY", "FAIL", f"verification güvenle ayrıştırılamadı: {exc}")
        return
    if issues:
        R.add("G-VERIFY", "FAIL", "; ".join(issues))
    elif warns:
        R.add("G-VERIFY", "WARN", "; ".join(warns))
    else:
        R.add("G-VERIFY", "PASS",
              "Kapsam içi; her olgusal iddia dayanağıyla kayıtlı. "
              "(Kapı dayanağın GÖSTERİLDİĞİNİ kanıtlar, doğruluğunu değil.)")


def _slice_bracketed(text, start_idx, open_ch="[", close_ch="]"):
    """text[start_idx] konumundaki açılış karakterinden EŞLEŞEN kapanışa kadar
    olan iç dilimi döndürür (açılış/kapanış hariç). Eşleşme yoksa "" döner.

    Neden: mevcut kapılar `\\{(.*?)\\n\\s*\\}` gibi girinti-bağımlı desenler kullanır;
    bunlar iç içe dizi/nesne içeren bloklarda (exam.chain[] içinde mappedTo[]) erken
    kapanır. Bu yardımcı sayarak eşleştirir.

    SINIR: string literali içindeki parantezleri saymaz (ör. concept: "a[b]" bloğu
    erken kapatır). Bu, kapının genel salt-metin/heuristik sınırıyla aynı düzeydedir
    (bkz. gate_curriculum notu) ve bilinçlidir.
    """
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return text[start_idx + 1:i]
    return ""


def _blank_bracketed(text, start_idx, open_ch, close_ch):
    """start_idx konumundaki eşleşen çiftin içini siler; dış kabuk kalır."""
    inner = _slice_bracketed(text, start_idx, open_ch, close_ch)
    if not inner:
        return text
    return text[: start_idx + 1] + text[start_idx + 1 + len(inner):]


def _iter_balanced_objects(text):
    """Dizi/gövde içindeki `{...}` nesne literallerinin iç dilimlerini üretir."""
    i = 0
    n = len(text)
    while i < n:
        j = text.find("{", i)
        if j < 0:
            return
        inner = _slice_bracketed(text, j, "{", "}")
        close = j + 1 + len(inner)
        if close >= n or text[close] != "}":
            return
        yield inner
        i = close + 1


def _array_inner(html, key):
    """`key: [` dizisinin içini döndürür. Anahtar yoksa None; `[]` ise ''."""
    m = re.search(rf"\b{re.escape(key)}\s*:\s*\[", html)
    if not m:
        return None
    return _slice_bracketed(html, m.end() - 1)


def _exam_worked_fade_ok(seg):
    """Bir worked segment diliminde fadeFrom < adım sayısı mı?"""
    fade_m = re.search(r'\bfadeFrom\s*:\s*(\d+)', seg)
    if not fade_m:
        return False
    steps_i = seg.find("steps")
    if steps_i < 0:
        return False
    arr_i = seg.find("[", steps_i)
    if arr_i < 0:
        return False
    n_steps = len(re.findall(r'\btext\s*:', _slice_bracketed(seg, arr_i)))
    return bool(n_steps and int(fade_m.group(1)) < n_steps)


def _exam_worked_ok(html):
    """En az bir `worked` segmentinde fadeFrom, adım sayısından KÜÇÜK mü?

    Bu, G-EXAM'ın çekirdek denetimidir: fadeFrom < adım sayısı ise son adım(lar)
    öğrenciye boş bırakılmış demektir — yani cevap doğrudan verilmemiştir.
    fadeFrom == adım sayısı ise tüm çözüm görünür (kopya), fadeFrom yoksa motor
    zaten segmenti kuramaz.

    HEURİSTİK: `type:"worked"` işaretinden geriye en yakın `{` bulunur ve o segment
    dilimlenir; dilim içindeki `steps` dizisinde `text:` sayılır. İç içe olağandışı
    biçimlendirme yanıltabilir — kapı beyanın BİÇİMİNİ ölçer, içeriğini değil.

    Yalnız legacy `exam:{}` yolunda kullanılır. Çoklu `exams[]` öğe başına
    `_exam_worked_ok_id` ister — modülde herhangi bir worked yetmez.
    """
    for m in re.finditer(r'\btype\s*:\s*["\']worked["\']', html):
        brace = html.rfind("{", 0, m.start())
        if brace < 0:
            continue
        seg = _slice_bracketed(html, brace, "{", "}")
        if _exam_worked_fade_ok(seg):
            return True
    return False


def _exam_worked_ok_id(html, seg_id):
    """`id` eşleşen `worked` segmentinde fadeFrom < adım sayısı mı?"""
    if not seg_id:
        return False
    pat = re.compile(r'\bid\s*:\s*["\']' + re.escape(seg_id) + r'["\']')
    for m in pat.finditer(html):
        brace = html.rfind("{", 0, m.start())
        if brace < 0:
            continue
        seg = _slice_bracketed(html, brace, "{", "}")
        if not re.search(r'\btype\s*:\s*["\']worked["\']', seg):
            continue
        return _exam_worked_fade_ok(seg)
    return False


def _exam_parse_topics(html):
    """topics[] → {id: chain_slice}. Anahtar yoksa veya id'siz öğe atlanır."""
    inner = _array_inner(html, "topics")
    if inner is None:
        return {}
    out = {}
    for obj in _iter_balanced_objects(inner):
        id_m = re.search(r'\bid\s*:\s*["\']([^"\']+)["\']', obj)
        if not id_m:
            continue
        chain_slice = ""
        chain_i = obj.find("chain")
        if chain_i >= 0:
            arr_i = obj.find("[", chain_i)
            if arr_i >= 0:
                chain_slice = _slice_bracketed(obj, arr_i)
        out[id_m.group(1)] = chain_slice
    return out


EXAM_INTEGRITY_VALUES = {"sound", "flawed", "out_of_frame"}
_EXAM_CHAIN_UNSET = object()


def _exam_collect(block, html, *, worked_ok=None, chain_slice=_EXAM_CHAIN_UNSET,
                  prefix="exam", worked_id="", skip_chain=False, require_worked_id=False):
    """exam bloğundan G-EXAM sinyallerini toplar (saf veri çıkarımı)."""
    stem_m = re.search(r'\bstem\s*:\s*["\'](.*?)["\']\s*,', block, re.S)
    integ_m = re.search(r'\bintegrity\s*:\s*["\']([^"\']*)["\']', block)
    note_m = re.search(r'\bintegrityNote\s*:\s*["\'](.*?)["\']', block, re.S)
    tcheck_m = re.search(r'\btranscriptionCheck\s*:\s*["\']([^"\']*)["\']', block)
    source_m = re.search(r'\bsource\s*:\s*["\'](.*?)["\']', block, re.S)
    distr_m = re.search(r'\bdistractorAnalysis\s*:\s*["\']([^"\']*)["\']', block)

    if chain_slice is _EXAM_CHAIN_UNSET:
        chain_slice = ""
        chain_i = block.find("chain")
        if chain_i >= 0:
            arr_i = block.find("[", chain_i)
            if arr_i >= 0:
                chain_slice = _slice_bracketed(block, arr_i)

    mapped_ids = set()
    for arr in re.findall(r'mappedTo\s*:\s*\[([^\]]*)\]', chain_slice):
        mapped_ids |= set(re.findall(r'["\']([^"\']+)["\']', arr))
    all_ids = set(re.findall(r'\bid\s*:\s*["\']([^"\']+)["\']', html))

    return {
        "prefix": prefix,
        "stem_ok": bool(stem_m and stem_m.group(1).strip()),
        "integrity": integ_m.group(1) if integ_m else "",
        "has_note": bool(note_m and note_m.group(1).strip()),
        "tcheck": tcheck_m.group(1) if tcheck_m else "",
        "all_ids": all_ids,
        "n_chain": len(re.findall(r'\bconcept\s*:', chain_slice)),
        "n_mapped": len(re.findall(r'\bmappedTo\s*:', chain_slice)),
        "missing_ids": [i for i in sorted(mapped_ids) if i not in all_ids],
        "has_source": bool(source_m and source_m.group(1).strip()),
        "has_options": bool(re.search(r'\boptions\s*:\s*\[', block)),
        "has_distractor": bool(distr_m and distr_m.group(1).strip()),
        "worked_ok": _exam_worked_ok(html) if worked_ok is None else worked_ok,
        "worked_id": worked_id,
        "skip_chain": skip_chain,
        "require_worked_id": require_worked_id,
    }


def _exam_eval(sig):
    """Toplanan sinyallerden (issues, warns) üretir. Saf karar mantığı."""
    prefix = sig.get("prefix", "exam")
    issues = []; warns = []
    if not sig["stem_ok"]:
        issues.append(f"{prefix}.stem boş veya yok; transkribe edilmiş soru metni zorunlu")
    if sig["integrity"] not in EXAM_INTEGRITY_VALUES:
        issues.append(f'{prefix}.integrity "sound" | "flawed" | "out_of_frame" olmalı '
                      f'(bulunan: "{sig["integrity"]}")')
    elif sig["integrity"] != "sound" and not sig["has_note"]:
        issues.append(f'{prefix}.integrity "{sig["integrity"]}" ama integrityNote boş; '
                      "sorunun nesinin bozuk/çerçeve dışı olduğu yazılmalı")
    if not sig["tcheck"]:
        issues.append(f"{prefix}.transcriptionCheck yok; transkripsiyon doğrulama segmenti "
                      "atlanamaz (soru yanlış okunmuşsa her şey yanlış)")
    elif sig["tcheck"] not in sig["all_ids"]:
        issues.append(f'{prefix}.transcriptionCheck "{sig["tcheck"]}" segments[] içinde yok')
    if not sig["worked_ok"]:
        if sig.get("require_worked_id") and not sig.get("worked_id"):
            issues.append(f"{prefix}.workedId yok; çoklu yolda her sorunun kendi "
                          "worked fadeFrom taşımalı")
        elif sig.get("worked_id"):
            issues.append(
                f'{prefix}: fadeFrom < adım sayısı olan `worked` '
                f'(workedId "{sig["worked_id"]}") yok; cevap doğrudan verilemez — '
                "son adım(lar) öğrenciye bırakılmalı"
            )
        else:
            issues.append("fadeFrom < adım sayısı olan bir `worked` segmenti yok; cevap "
                          "doğrudan verilemez — son adım(lar) öğrenciye bırakılmalı")
    if not sig.get("skip_chain"):
        if not sig["n_chain"]:
            issues.append(f"{prefix}.chain[] boş veya `concept` içermiyor; geriye çözümleme "
                          "zinciri zorunlu")
        elif sig["n_mapped"] < sig["n_chain"]:
            issues.append(f'{sig["n_chain"]} zincir halkasından {sig["n_mapped"]} tanesinde '
                          "mappedTo var; her halka bir segmente bağlanmalı")
        if sig["missing_ids"]:
            issues.append(f"{prefix}.chain mappedTo id'si segments[] içinde yok: "
                          + ", ".join(sig["missing_ids"][:5]))
    if not sig["has_source"]:
        warns.append(f"{prefix}.source beyanı yok (sorunun kaynağı belirsiz)")
    if sig["has_options"] and not sig["has_distractor"]:
        warns.append(f"{prefix}.options var ama {prefix}.distractorAnalysis yok; çeldirici "
                     "analizi segmenti önerilir (yeni nesil çeldirici doğru ama ilgisizdir)")
    return issues, warns


def _exam_eval_multi_item(obj, html, topics):
    """Tek bir exams[] öğesini değerlendirir; (issues, warns) döner."""
    id_m = re.search(r'\bid\s*:\s*["\']([^"\']+)["\']', obj)
    eid = id_m.group(1) if id_m else "?"
    prefix = f"exams[{eid}]"
    extra = []
    topic_m = re.search(r'\btopicId\s*:\s*["\']([^"\']*)["\']', obj)
    topic_id = topic_m.group(1) if topic_m else ""
    wid_m = re.search(r'\bworkedId\s*:\s*["\']([^"\']*)["\']', obj)
    worked_id = wid_m.group(1) if wid_m else ""

    skip_chain = False
    chain_slice = ""
    if not topic_id:
        extra.append(f"{prefix}.topicId yok")
        skip_chain = True
    elif topic_id not in topics:
        extra.append(f'{prefix}.topicId "{topic_id}" topics[] içinde yok')
        skip_chain = True
    else:
        chain_slice = topics[topic_id]

    worked_ok = _exam_worked_ok_id(html, worked_id) if worked_id else False
    issues, warns = _exam_eval(_exam_collect(
        obj, html,
        worked_ok=worked_ok,
        chain_slice=chain_slice,
        prefix=prefix,
        worked_id=worked_id,
        skip_chain=skip_chain,
        require_worked_id=True,
    ))
    return extra + issues, warns


def gate_exam(html, R):
    """G-EXAM (koşullu): sınav-sorusu modülünün yapısal bütünlüğü.

    Tetik: mode EXAM veya `exam:{}` veya dolu `exams:[]`. Aksi halde atlanır
    (geriye dönük uyum — mevcut modüller etkilenmez).

    ÇEKİRDEK DEĞER: `worked` segmentinde fadeFrom < adım sayısı ZORUNLUDUR. Böylece
    cevap hiçbir zaman doğrudan verilmez, öğrenci son adımı kendisi tamamlar —
    ödev-çözme makinesi olmak iyi niyete değil YAPIYA bağlanır. Çoklu yolda bu
    her öğenin KENDİ `workedId` si üzerinde aranır; modülde başka bir worked yetmez.

    DENETLEYEMEZ (fazla güvenmeyin): transkripsiyonun fotoğrafa sadık olduğunu,
    çözümün DOĞRU olduğunu, zincirin eksiksiz olduğunu, outcomeCode'un gerçek bir
    kazanım olduğunu — hiçbiri çevrimdışı ölçülemez (MCP erişimi yok, G-CURRICULUM
    ve G-VERIFY ile aynı salt-metin sınırı). Kapı beyanın BİÇİMİNİ ölçer.
    Tam kural: references/exam-solving.md.
    """
    is_exam_mode = bool(re.search(r'\bmode\s*:\s*["\']EXAM["\']', html))
    exam_m = re.search(r'\bexam\s*:\s*\{', html)
    exams_inner = _array_inner(html, "exams")
    exam_items = list(_iter_balanced_objects(exams_inner)) if exams_inner else []

    if not is_exam_mode and not exam_m and not exam_items:
        R.add("G-EXAM", "PASS", "Sınav-sorusu modülü değil (uygulanmaz).", applicable=False)
        return

    if exam_items:
        topics = _exam_parse_topics(html)
        issues, warns = [], []
        n = len(exam_items)
        if n > 4:
            warns.append(f"exams.length {n} > 4; oturum uzayacak (yumuşak tavan, FAIL değil)")
        for obj in exam_items:
            i, w = _exam_eval_multi_item(obj, html, topics)
            issues.extend(i)
            warns.extend(w)
        if issues:
            R.add("G-EXAM", "FAIL", "; ".join(issues))
        elif warns:
            R.add("G-EXAM", "WARN", "; ".join(warns))
        else:
            R.add("G-EXAM", "PASS",
                  f"{n} soru transkribe; konu zinciri segmentlere izlenebilir; "
                  "her worked fadeFrom ile öğrenciye bırakılmış. "
                  "(Kapı yapıyı ölçer, çözümün doğruluğunu değil.)")
        return

    if not exam_m:
        R.add("G-EXAM", "FAIL",
              "mode EXAM ama ne `exam` bloğu ne dolu `exams[]` var; soru provenansı "
              "ve çözüm disiplini zorunlu (references/exam-solving.md).")
        return
    block = _slice_bracketed(html, exam_m.end() - 1, "{", "}")
    issues, warns = _exam_eval(_exam_collect(block, html))
    if issues:
        R.add("G-EXAM", "FAIL", "; ".join(issues))
    elif warns:
        R.add("G-EXAM", "WARN", "; ".join(warns))
    else:
        R.add("G-EXAM", "PASS",
              "Soru transkribe + doğrulama segmentine bağlı; zincir segmentlere "
              "izlenebilir; cevap fadeFrom ile öğrenciye bırakılmış. "
              "(Kapı yapıyı ölçer, çözümün doğruluğunu değil.)")


FLOW_LOSS_RE = re.compile(r"(seri(n|ni)?\s*(kaybett|sıfırla|bozdu)|kaybettin|streak\s*lost|başarısız oldun)", re.I)
FLOW_LABEL_RE = re.compile(r"(zorlan[ıi]yorsun|çok kolay geliyor|seviyen düştü)", re.I)
def gate_flow(html, R):
    """Koşullu: gamification akış değişmezleri (merak-boşluğu kapanır, gain-only streak,
    kaygısız pacingDisk, uyarlanır-zorluk etiketlemez). İmza yoksa uygulanmaz."""
    has_hook = 'data-seg="hook"' in html or "data-hook" in html
    has_streak = "streakChip" in html or "streak-chip" in html
    has_disk = "pacingDisk" in html or "pacing-disk" in html
    if not (has_hook or has_streak or has_disk):
        R.add("G-FLOW","PASS","Gamification akış imzası yok (uygulanmaz).", applicable=False); return
    issues=[]
    # açık merak-boşluğu: her hook 'data-hook-resolved' ile kapanmalı
    n_hook = html.count('data-seg="hook"')
    n_res  = html.count("data-hook-resolved")
    if n_hook and n_res < n_hook: issues.append(f"{n_hook - n_res} merak-boşluğu kapanmıyor (data-hook-resolved eksik)")
    if FLOW_LOSS_RE.search(html): issues.append("streak/kayıp cezalandırıcı dili (gain-only olmalı)")
    if FLOW_LABEL_RE.search(html): issues.append("uyarlanır-zorluk kullanıcıyı etiketliyor")
    if has_disk and re.search(r"pacing-?[Dd]isk[^>]*data-countdown", html): issues.append("tempo diski geri-sayım (kaygısız/kesintisiz olmalı)")
    if issues: R.add("G-FLOW","FAIL","; ".join(issues))
    else: R.add("G-FLOW","PASS","Akış değişmezleri: merak-boşluğu kapanıyor, gain-only streak, kaygısız disk.")

# item 3/4 (carbon-excellence.md §3): statik kart/segment/tile/teach seçicisinde GERÇEK
# (non-inset) box-shadow = layer-elevation ihlali. `inset` gölgeler kasıtlı olarak dışlanır:
# sıfır-blur/sıfır-offset bir inset box-shadow (ör. `inset 0 0 0 2px var(--accent)`) görsel
# olarak `border`den ayırt edilemeyen bir sınır simülasyonu tekniğidir — "yüzen/yükselen"
# bir derinlik hissi vermez, dolayısıyla madde 3/4'ün hedeflediği ihlal değildir (bkz.
# assets/module-template.html .card/.card--back flashcard kullanımı — ampirik false-positive).
STATIC_SHADOW_RE = re.compile(
    r"\.(card|seg|tile|teach)[^{]*\{[^}]*box-shadow\s*:(?!\s*(?:none|inset)\b)",
    re.I | re.S)

def gate_carbon_grid(html, R):
    """WARN→FAIL: Carbon kompozisyon disiplini (carbon-excellence.md §3 makine-alt-kümesi).

    Statik kart gölgesi = FAIL (layer-elevation ihlali; yalnız gerçek/non-inset drop-shadow —
    bir inset box-shadow sınır simülasyonudur, derinlik hissi vermez, ihlal sayılmaz).
    2x-grid konteyneri / en-boy oranı (aspect-ratio) yokluğu ve >500ms koreografi = WARN.

    Kapsam notu: carbon-excellence.md §3 dört maddeyi kapsar (1 grid, 2 aspect-ratio,
    3/4 layer-shadow, 9 koreografi-zamanlaması). Madde 10 (expressive/productive tip-seti
    karışımı) bu kapıda YOK: aynı bileşen/kart alt-ağacında iki tip-setinin birlikteliğini
    güvenilir tespit etmek DOM iç-içelik/düzen muhakemesi gerektirir — CSS metin sırası DOM
    ağacındaki gerçek ebeveyn-çocuk ilişkisini garanti etmediğinden saf regex bunu güvenilir
    yapamaz → module-auditor'a devredildi (regex ile güvenilir denetlenemez; madde 6 ile
    aynı gerekçe kategorisi — bkz. carbon-excellence.md §3 "Not").
    """
    fails=[]; warns=[]
    if STATIC_SHADOW_RE.search(html): fails.append("statik kartta drop-shadow (layer-elevation kullan; gölge yalnız floating)")
    if "cds--grid" not in html and "carbon-grid" not in html and "grid-template-columns" not in html:
        warns.append("2x grid konteyneri saptanmadı (ad-hoc genişlik riski)")
    if "aspect-ratio" not in html:
        warns.append("Carbon en-boy oranı (aspect-ratio) kullanılmıyor")
    for m in re.finditer(r"transition[^;]*?(\d+)ms", html):
        if int(m.group(1))>500: warns.append(f"koreografi {m.group(1)}ms >500ms"); break
    if fails: R.add("G-CARBON-GRID","FAIL","; ".join(fails))
    elif warns: R.add("G-CARBON-GRID","WARN","; ".join(warns[:3]))
    else: R.add("G-CARBON-GRID","PASS","Carbon kompozisyon: layer-elevation, grid, en-boy oranı, koreografi <500ms.")


# Öğrenci yüzeyinde yasak kaynak-meta atıf. Kitap yazarın doğruluk kaynağıdır;
# öğrenciye görünen dil bu modülün kendi tamamlanmış (nihai) cümleleridir.
# Türkçe edebi eser olarak "kitap" ("bu kitabın yazarı") meşrudur — taranmaz.
_VOICE_PATTERNS = (
    r"kitab[ıiIİ]n\s+tan[ıiIİ]m",
    r"kitaptaki\s+(?:yaz[ıiIİ]|tan[ıiIİ]m|metin|anlat[ıiIİ])",
    r"yaz[ıiIİ]y[ıiIİ]\s+hat[ıiIİ]rla",
    r"ders\s*kitab",
    r"kitab(?:[ıiIİ]m[ıiIİ]z|[ıiIİ]n[ıiIİ]z)da",
    r"kitaba\s+g[öoÖO]re",
    r"kitapta\s+(?:ge[cç]en|yaz[ıiIİ]ld|belirt|anlat[ıiIİ]lan|g[öoÖO]rd)",
    r"kitaptan\s+hat[ıiIİ]rla",
    r"kitab[ıiIİ]n\s+(?:ifadesi|c[üuÜU]mlesi)",
    r"[üuÜU]nitede\s+(?:g[öoÖO]rd|[öoÖO]ğrendi|ge[cç]en|anlat[ıiIİ]lan)",
    r"kaynak\s+metinde",
    r"kaynakta\s+(?:oldu[ğg]u|belirt|yaz[ıiIİ]ld|ge[cç]ti[ğg]i)",
    r"(?:sayfa|s\.)\s*\d{1,3}\b",
)
VOICE_DEIXIS_RE = re.compile("|".join("(?:%s)" % p for p in _VOICE_PATTERNS), re.I)


def _blank_keyed_objects(text, key):
    """`key: { ... }` nesnelerini (verification, grounding, curriculum, frame_source) siler.

    Öğrenci bunları görmez; tarama yanlış pozitif üretmesin diye yazar katmanı çıkarılır.
    """
    pat = re.compile(r"\b" + re.escape(key) + r"\s*:")
    out = text
    pos = 0
    while True:
        m = pat.search(out, pos)
        if not m:
            break
        brace = out.find("{", m.end())
        if brace == -1 or brace > m.end() + 80:
            pos = m.end()
            continue
        interior = _slice_bracketed(out, brace, "{", "}")
        if not interior and out[brace:brace + 2] != "{}":
            pos = m.end()
            continue
        end = brace + len(interior) + 2
        out = out[:m.start()] + " " + out[end:]
        pos = m.start()
    return out


def _student_surface(html):
    """Öğrencinin gördüğü metni bırakır; yazar/provenans katmanını çıkarır.

    Çıkarılan: HTML/JS blok yorumları, verification, grounding, frame_source,
    curriculum (kazanım kaydı öğrenciye render edilmez), sourceCitation, sourceRef.
    PhET CC BY-NC künyesi öğrenci yüzeyinde kalır — o lisans atfıdır, kitap-meta değil.
    """
    text = _strip_comments_for_svg_scan(html)
    for key in ("verification", "grounding", "frame_source", "curriculum"):
        text = _blank_keyed_objects(text, key)
    text = re.sub(r"\bsourceCitation\s*:\s*(['\"])(?:\\.|(?!\1).)*\1", " ", text, flags=re.S)
    text = re.sub(r"\bsourceRef\s*:\s*(['\"])(?:\\.|(?!\1).)*\1", " ", text)
    return text


def gate_voice(html, R):
    """G-VOICE: öğrenci yüzeyinde kaynak-meta atıf yok; anlatım nihai dilde (FAIL).

    Kitap/program yazarın doğruluk kaynağıdır (SKILL.md §7, G-VERIFY). Öğrenciye
    görünen body/stem/explanation/recap/prompt/keyTerms o kaynağı *anımsatmaz* —
    kavramı bu modülün kendi tamamlanmış cümleleriyle anlatır. "Kitabın tanımı",
    "kitaptaki yazıyı hatırla" bir atıf değil, yarım dildir.

    DENETLEYEMEZ: cümlenin gerçekten orijinal olup olmadığını (yalnız deixis
    kalıplarını tarar). Edebi eser olarak "kitap" ("bu kitabın yazarı") meşrudur.
    """
    surface = _student_surface(html)
    hits = []
    seen = set()
    for m in VOICE_DEIXIS_RE.finditer(surface):
        token = re.sub(r"\s+", " ", m.group(0)).strip()
        key = token.casefold()
        if key not in seen:
            seen.add(key)
            hits.append(token)
    if hits:
        sample = ", ".join("«%s»" % h for h in hits[:4])
        R.add("G-VOICE", "FAIL",
              "öğrenci yüzeyinde kaynak-meta atıf: %s. Tanımı/anlatımı bu modülün "
              "kendi cümleleriyle, tamamlanmış (nihai) dilde yaz; kitaba/sayfaya/"
              "üniteye gönderme yalnız verification + sourceCitation'da kalır "
              "(SKILL.md §7)." % sample)
    else:
        R.add("G-VOICE", "PASS",
              "Öğrenci yüzeyi nihai dil: kaynak-meta atıf yok.")


def main():
    """CLI giriş noktası: HTML yolunu alır, kapıları çalıştırır, rapor basar, çıkış kodu döndürür."""
    ap=argparse.ArgumentParser(description="carbon-edupedia modül doğrulayıcı")
    ap.add_argument("html", help="modül HTML dosyası")
    ap.add_argument("--strict", action="store_true", help="WARN'ları da ihlal say")
    ap.add_argument("--json", action="store_true",
                    help="stdout'a yalnız geçerli JSON bas (manifest quality_gates alanına gömülebilir)")
    args=ap.parse_args()
    try:
        html=open(args.html, encoding="utf-8").read()
    except OSError as e:
        if args.json:
            print(json.dumps({"error": f"Dosya okunamadı: {e}"}, ensure_ascii=False))
        else:
            print(f"{RED}Dosya okunamadı:{RESET} {e}")
        sys.exit(2)

    R=Result()
    gate_emoji(html,R)
    gate_carbon(html,R)
    gate_a11y(html,R)
    gate_interact(html,R)
    gate_selfcontained(html,R)
    gate_contrast(html,R)
    gate_wellbeing(html,R)
    gate_voice(html,R)
    gate_svg(html,R)
    gate_audio(html,R)
    gate_token_authority(html,R)
    gate_curriculum(html,R)
    gate_verify(html,R)
    gate_flow(html,R)
    gate_carbon_grid(html,R)
    gate_exam(html,R)

    if args.json:
        print(json.dumps(R.to_json_gates(), ensure_ascii=False, indent=2))
    else:
        R.report()

    if R.fail or (args.strict and any(s=="WARN" for _,s,_ in R.rows)):
        sys.exit(1)
    sys.exit(0)

if __name__=="__main__":
    main()
