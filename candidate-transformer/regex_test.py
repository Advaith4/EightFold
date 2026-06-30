import re

MONTH_MAP = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "september": "09",
    "sept": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
    "spring": "03",
    "summer": "06",
    "fall": "09",
    "winter": "12",
}


def normalize_date(
    raw_date: str | None, fallback_year: str | None = None
) -> str | None:
    if not raw_date:
        return None
    raw = raw_date.strip().lower()
    if raw in ("present", "current"):
        return None

    year_match = re.search(r"\d{4}", raw)
    year = year_match.group(0) if year_match else fallback_year

    if not year:
        return raw_date  # couldn't normalize

    month_val = None
    for word in re.findall(r"[a-z]+", raw):
        if word in MONTH_MAP:
            month_val = MONTH_MAP[word]
            break

    if month_val:
        return f"{year}-{month_val}"
    return year


MONTH_REGEX = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|Spring|Summer|Fall|Winter)"
DATE_RANGE_PATTERN = f"({MONTH_REGEX}\\s+\\d{{4}}|\\d{{4}}|{MONTH_REGEX})\\s*(?:-|to|–|—)\\s*({MONTH_REGEX}\\s+\\d{{4}}|\\d{{4}}|Present|Current)"
DATE_PATTERN = f"(?:{MONTH_REGEX}\\s+)?\\d{{4}}"

test_cases = [
    "Dec 2025",
    "Jan 2026",
    "May 2025",
    "June 2025",
    "May – June 2025",
    "May-Jun 2025",
    "2023-2027",
    "2023 – 2027",
    "Dec 2025 - Present",
    "Current",
]

for t in test_cases:
    m_range = re.search(DATE_RANGE_PATTERN, t, re.IGNORECASE)
    if m_range:
        raw_start = m_range.group(1).strip()
        raw_end = m_range.group(2).strip()
        end_norm = normalize_date(raw_end)
        fallback = end_norm[:4] if end_norm and re.search(r"^\d{4}", end_norm) else None
        start_norm = normalize_date(raw_start, fallback)
        print(f"Range: {t:20} -> {start_norm} TO {end_norm}")
    else:
        m_single = re.search(DATE_PATTERN, t, re.IGNORECASE)
        if m_single:
            print(f"Single: {t:20} -> {normalize_date(m_single.group(0))}")
        else:
            print(f"Single/None: {t:20} -> {normalize_date(t)}")
