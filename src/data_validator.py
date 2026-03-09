"""Validate scraped data quality before saving."""


def _count_section(key, data):
    """Return the item count for a section, or 0 if missing/empty."""
    val = data.get(key)
    if val is None:
        return 0
    if key == "odevlerim":
        return len(val.get("homework", {}).get("rows", []))
    if key == "ders_programi":
        return len(val) if isinstance(val, list) else (1 if val else 0)
    if key == "takvim":
        return len(val) if isinstance(val, list) else 0
    if key == "gelisim_raporu":
        return len(val.get("grades", []))
    if key == "ders_icerikleri":
        if isinstance(val, dict):
            return sum(
                len(v) if isinstance(v, list) else 1
                for v in val.values()
            )
        return 0
    if key == "takim_calismalari":
        return len(val.get("activities", []))
    if key == "ogep":
        return len(val.get("sessions", {}).get("rows", []))
    if key == "duyurular":
        return len(val.get("announcements", []))
    return 0


# Minimum thresholds (0 = no minimum, section can be empty)
SECTION_RULES = {
    "odevlerim":         {"min": 5,  "critical": True},
    "ders_programi":     {"min": 1,  "critical": True},
    "takvim":            {"min": 1,  "critical": False},
    "gelisim_raporu":    {"min": 5,  "critical": True},
    "ders_icerikleri":   {"min": 1,  "critical": False},
    "takim_calismalari": {"min": 0,  "critical": False},
    "ogep":              {"min": 0,  "critical": False},
    "duyurular":         {"min": 1,  "critical": False},
}

DROP_THRESHOLD = 0.5  # Warn if count drops by more than 50%


def validate_scraped_data(new_data: dict, previous_data: dict | None) -> dict:
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
