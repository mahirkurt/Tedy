"""Validate scraped data quality before saving."""


def _count_section(key, data):
    """Return the item count for a section, or 0 if missing/empty."""
    val = data.get(key)
    if val is None:
        return 0
    if key == "ogrenci_profili":
        # Count populated identity, not dict keys: scrape_ogrenci_profili
        # always returns its eight keys, so a key count reads a 404 page as
        # a full profile.
        if not isinstance(val, dict):
            return 0
        named = sum(
            1 for f in ("name", "student_no", "class_name", "branch")
            if str(val.get(f, "") or "").strip()
        )
        extra = val.get("fields")
        return named + (len(extra) if isinstance(extra, dict) else 0)
    if key == "odevlerim":
        return len(val.get("homework", {}).get("rows", []))
    if key == "ders_programi":
        return len(val) if isinstance(val, list) else (1 if val else 0)
    if key == "takvim":
        return len(val) if isinstance(val, list) else 0
    if key == "gelisim_raporu":
        return len(val.get("grades", [])) + len(val.get("rubrics", []))
    if key == "ders_icerikleri":
        if isinstance(val, dict):
            return sum(
                len(v) if isinstance(v, list) else 1
                for v in val.values()
            )
        return 0
    if key == "takim_calismalari":
        activities = val.get("activities", [])
        # extract_table returns {"headers", "rows", ...}; older shape is a list
        if isinstance(activities, dict):
            return len(activities.get("rows", []))
        return len(activities)
    if key == "ogep":
        return len(val.get("sessions", {}).get("rows", []))
    if key == "duyurular":
        return len(val.get("announcements", []))
    return 0


# Minimum thresholds (0 = no minimum, section can be empty)
SECTION_RULES = {
    # The dashboard is about one child; if their name, number and class come
    # back blank while we are logged in, the page we read is not the page we
    # think it is. Critical, so it reddens health rather than sitting in a
    # warning list nobody opens.
    "ogrenci_profili":   {"min": 1,  "critical": True},
    # 1, not 5: an absolute floor is the wrong tool for "did the scrape
    # break". Measured 2026-09-21 — the portal held exactly 2 homework items
    # and every other section was complete, yet six consecutive syncs were
    # marked failed and the family's dashboard read "Senkron: Başarısız".
    # A school assigning two pieces of homework is not a fault. Data loss is
    # caught by the drop check below (DROP_THRESHOLD), which compares against
    # what the previous run saw; critical stays on so a scrape that returns
    # nothing, with no word from the portal explaining it, still fails.
    "odevlerim":         {"min": 1,  "critical": True},
    "ders_programi":     {"min": 1,  "critical": True},
    "takvim":            {"min": 1,  "critical": False},
    "gelisim_raporu":    {"min": 5,  "critical": True},
    "ders_icerikleri":   {"min": 1,  "critical": False},
    "takim_calismalari": {"min": 0,  "critical": False},
    "ogep":              {"min": 0,  "critical": False},
    "duyurular":         {"min": 1,  "critical": False},
}

DROP_THRESHOLD = 0.5  # Warn if count drops by more than 50%


def _has_empty_state(val, depth=2):
    """True when a scraper recorded that the portal rendered an empty table."""
    if not isinstance(val, dict) or depth < 0:
        return False
    if val.get("empty_state"):
        return True
    return any(_has_empty_state(v, depth - 1) for v in val.values())


def _explained_absence(section, data, unavailable):
    """Return why a section is empty, when the portal itself told us.

    An absence the portal explained - no permission, a closed module, or a
    table's own empty state - is not a scrape failure and must not be
    reported as one.
    """
    blocked = (unavailable or {}).get(section)
    if blocked:
        return f"{blocked.get('reason', 'erisilemez')}: {blocked.get('detail', '')}".strip(": ")
    if _has_empty_state(data.get(section)):
        return "portalda kayıt yok (boş tablo)"
    return None


def validate_scraped_data(new_data: dict, previous_data: dict | None,
                          unavailable: dict | None = None) -> dict:
    """
    Validate scraped data. Returns:
    {
        "valid": bool,
        "errors": [str],
        "warnings": [str],
        "section_counts": {section: count},
    }
    """
    errors = []
    warnings = []
    section_counts = {}

    for section, rules in SECTION_RULES.items():
        count = _count_section(section, new_data)
        section_counts[section] = count

        # An absence the portal explained is not a failure - say why, once,
        # and skip both the minimum and the drop check.
        reason = _explained_absence(section, new_data, unavailable) \
            if count < rules["min"] else None
        if reason:
            warnings.append(f"{section}: veri yok - {reason}")
            continue

        # Check minimum threshold
        if count < rules["min"] and rules["critical"]:
            errors.append(
                f"{section}: {count} items (minimum {rules['min']})")
        elif count < rules["min"]:
            warnings.append(
                f"{section}: {count} items (expected >= {rules['min']})")

        # Compare with previous data
        if previous_data:
            prev_count = _count_section(section, previous_data)
            if prev_count > 0 and count < prev_count * DROP_THRESHOLD:
                pct = round((1 - count / prev_count) * 100)
                warnings.append(
                    f"{section}: {prev_count}\u2192{count}, %{pct} düşüş")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "section_counts": section_counts,
    }
