"""Canonical course names used when portal text reaches the dashboard.

Scrapers keep portal-native names. Normalization happens at the API
boundary so İşler, Dersler and exams share one vocabulary.
"""
import re

COURSE_ALIASES = {
    "Fransızca": [
        "İkinci Yabancı Dil",
        "İkinci Yabancı Dil (Fransızca)",
        "2. Yabancı Dil (F)",
        "2. Yabancı Diller",
    ],
    "Din Kültürü": [
        "Din Kültürü ve Ahlak Bilgisi",
        "DKAB",
    ],
    "Beden Eğitimi": [
        "Beden Eğitimi ve Spor",
    ],
    "İngilizce": [
        "İngilizce (Language)",
        "İngilizce Language",
        "İngilizce (2)",
        "İngilizce Literature",
        "İngilizce (Literature)",
    ],
    "Bilişim": [
        "Bilişim Teknolojileri",
    ],
    "Ahlak ve Yurttaşlık": [
        "Ahlak ve Yurttaşlık Eğitimi",
    ],
}

_ALIAS_LOOKUP = {}
for _canonical, _aliases in COURSE_ALIASES.items():
    _ALIAS_LOOKUP[_canonical] = _canonical
    for _alias in _aliases:
        _ALIAS_LOOKUP[_alias] = _canonical
_ALIAS_LONGEST_FIRST = sorted(_ALIAS_LOOKUP.keys(), key=len, reverse=True)


def normalize_course(name):
    """Normalize a course name to its canonical form.

    1. Exact match in alias lookup
    2. Prefix match against known aliases (longest first)
    3. Strip parenthesized suffix, retry
    4. Return original if no match
    """
    name = name.strip()
    if not name:
        return name

    if name in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[name]

    # Prefix match: handles "İngilizce (Literature) (i-403 (İngilizce))"
    # by matching the known alias "İngilizce (Literature)" as a prefix
    for alias in _ALIAS_LONGEST_FIRST:
        if name.startswith(alias) and (
            len(name) == len(alias) or name[len(alias)] == " "
        ):
            return _ALIAS_LOOKUP[alias]

    stripped = re.sub(r"\s*\(.*\)\s*$", "", name).strip()
    if stripped != name and stripped in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[stripped]

    return stripped if stripped != name else name
