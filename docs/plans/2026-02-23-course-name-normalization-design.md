# Course Name Normalization Design

**Date:** 2026-02-23
**Status:** Approved

## Problem

Same course appears with different names across Google Workspace services because each portal page uses its own naming convention. No normalization layer exists.

Examples:
- Fransızca: "İkinci Yabancı Dil" (program), "İkinci Yabancı Dil (Fransızca)" (ödev), "2. Yabancı Dil (F)" (tab)
- Din Kültürü: "Din Kültürü ve Ahlak Bilgisi" (program/ödev), "DKAB" (tab)
- İngilizce: "İngilizce (Language)" (ödev), "İngilizce Language" (tab), "İngilizce (2)" (tab)

## Approach

Centralized `normalize_course()` function in `sync_to_google.py`. Scraper output stays untouched — normalization happens at sync time only.

## Canonical Names

```
Matematik, Türkçe, Fen Bilimleri, Sosyal Bilgiler, Din Kültürü,
İngilizce, İngilizce Literature, Fransızca, Bilişim, Görsel Sanatlar,
Müzik, Beden Eğitimi, Ahlak ve Yurttaşlık, PDR, Sınıf Öğretmeni
```

İngilizce split: Language+genel → "İngilizce", Literature → "İngilizce Literature".

## Alias Mapping

| Canonical | Aliases |
|-----------|---------|
| Fransızca | İkinci Yabancı Dil, İkinci Yabancı Dil (Fransızca), 2. Yabancı Dil (F) |
| Din Kültürü | Din Kültürü ve Ahlak Bilgisi, DKAB |
| Beden Eğitimi | Beden Eğitimi ve Spor |
| İngilizce | İngilizce (Language), İngilizce Language, İngilizce (2) |
| İngilizce Literature | İngilizce (Literature) |
| Bilişim | Bilişim Teknolojileri |

Fallback: strip parenthesized suffixes via regex, retry lookup. If still no match, return original name unchanged.

## Changes in `sync_to_google.py`

1. Add `COURSE_ALIASES` dict and `normalize_course(name)` function at top of file
2. `sync_ders_programi` — normalize `lesson_name`
3. `sync_odevlerim` — normalize `ders` (affects Task title, Calendar event, Drive folder name)
4. `sync_takvim` — expand keyword list to include all canonical names
5. `sync_ders_icerikleri` — normalize `ders_name`
6. `sync_gelisim_raporu` — normalize `ders`
7. `sync_attachments_to_drive` — normalize `att["ders"]`

## Bonus Fix

`parse_week_range`: replace hardcoded `year = 2026` with `datetime.now().year`.

## Out of Scope

- Scraper changes (scrape_all.py, scrape_eba_textbooks.py, etc.)
- Google API structure
- Migration of existing events/tasks (old names stay, new ones use normalized names)
