#!/usr/bin/env python3
"""Tedy ders renk sistemini panoya üretir: dashboard/src/theme/subjects.ts ve _subjects.scss.

Kaynak: src/mcp_server/vendor/assets/carbon-v11-authority.json → tedyLayer.subjectThemes.
Pano g10 temasında çalışır, bu yüzden SCSS yalnız açık (light) rolleri taşır ve her değeri bir
@carbon/colors adıyla yazar (#{colors.$magenta-60}); TypeScript tablosu ders adını aileye çözer.

Kullanım:  python scripts/gen_subject_themes.py          # dosyaları yazar
           python scripts/gen_subject_themes.py --check  # sapma varsa 1 ile çıkar
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import subject_themes  # noqa: E402

TS_OUT = ROOT / "dashboard" / "src" / "theme" / "subjects.ts"
SCSS_OUT = ROOT / "dashboard" / "src" / "theme" / "_subjects.scss"
ROLE_VARS = (("accent", "--ted-subject-accent"), ("text", "--ted-subject-text"),
             ("surface", "--ted-subject-surface"), ("onSurface", "--ted-subject-on-surface"),
             ("surfaceHover", "--ted-subject-surface-hover"), ("border", "--ted-subject-border"))
HEADER = ("Üretilir: scripts/gen_subject_themes.py — elle düzenlemeyin. Kaynak:\n"
          "src/mcp_server/vendor/assets/carbon-v11-authority.json → tedyLayer.subjectThemes.")


def _scss_name(step: str) -> str:
    return "white-0" if step == "white-0" else step


def render_scss() -> str:
    st = subject_themes.themes()
    lines = ["// " + line for line in HEADER.splitlines()]
    lines += [
        "//",
        "// Ders kimliği (Tedy İ8): renk yalnız işarette, çubukta ve kenarda yaşar; ders adı metni nötr",
        "// kalır. Değerler Carbon Tag token'larının g10 karşılıkları ve @carbon/colors adımlarıdır.",
        "@use '@carbon/colors' as colors;",
        "",
    ]
    default = st["fallback"]["family"]
    for family, modes in [("", st["families"][default])] + list(st["families"].items()):
        selector = ".ted-subject" if not family else f".ted-subject--{family}"
        lines.append(f"{selector} {{")
        for role, var in ROLE_VARS:
            step = modes["light"][role][0]
            lines.append(f"  {var}: #{{colors.${_scss_name(step)}}};")
        lines.append("}")
    return "\n".join(lines) + "\n"


def render_ts() -> str:
    st = subject_themes.themes()
    families = list(st["families"])
    domains = [{"id": d["id"], "label": d["label"], "family": d["family"],
                "stems": [subject_themes.fold(s) for s in d["stems"]]} for d in st["domains"]]
    fallback = st["fallback"]
    union = " | ".join(json.dumps(f) for f in families)
    return f"""// {HEADER.splitlines()[0]}
// {HEADER.splitlines()[1]}
//
// Ders adı → alan → Carbon Tag ailesi. Aynı tablo ve aynı katlama kuralı backend'de
// (src/subject_themes.py) ve modül şablonunda (subjectDomain()) çalışır.

export type SubjectFamily = {union}

export interface SubjectDomain {{
  id: string
  label: string
  family: SubjectFamily
}}

export const SUBJECT_FAMILIES: readonly SubjectFamily[] = {json.dumps(families)}

const DOMAINS: ReadonlyArray<SubjectDomain & {{ stems: readonly string[] }}> = {json.dumps(domains, ensure_ascii=False, indent=2)}

const FALLBACK: SubjectDomain = {json.dumps(fallback, ensure_ascii=False)}

const FOLD: Record<string, string> = {{ ç: 'c', ğ: 'g', ı: 'i', ö: 'o', ş: 's', ü: 'u', â: 'a', î: 'i', û: 'u' }}

export function foldSubject(value: string | null | undefined): string {{
  return String(value ?? '')
    .toLocaleLowerCase('tr')
    .replace(/[çğıöşüâîû]/g, (c) => FOLD[c])
    .replace(/\\s+/g, ' ')
    .trim()
}}

const escape = (s: string) => s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&')
const PATTERNS = DOMAINS.map((d) => ({{
  domain: {{ id: d.id, label: d.label, family: d.family }} as SubjectDomain,
  re: new RegExp('(?:^|[^a-z0-9])(?:' + d.stems.map(escape).join('|') + ')'),
}}))

export function subjectDomain(course: string | null | undefined): SubjectDomain {{
  const folded = foldSubject(course)
  for (const p of PATTERNS) if (p.re.test(folded)) return p.domain
  return FALLBACK
}}

export function subjectFamily(course: string | null | undefined): SubjectFamily {{
  return subjectDomain(course).family
}}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    drift = 0
    for path, body in ((SCSS_OUT, render_scss()), (TS_OUT, render_ts())):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if args.check:
            if current != body:
                drift += 1
                print(f"SAPMA: {path.relative_to(ROOT)} otoriteden farklı (düzeltmek için: scripts/gen_subject_themes.py)")
        elif current != body:
            path.write_text(body, encoding="utf-8")
            print(f"yazıldı: {path.relative_to(ROOT)}")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
