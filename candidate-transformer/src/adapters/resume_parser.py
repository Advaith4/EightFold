"""Deterministic parsing logic for unstructured resume text."""

import re
from typing import Any

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
    """Normalize raw dates into canonical YYYY or YYYY-MM formats."""
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


# Common regex patterns
MONTH_REGEX = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|Spring|Summer|Fall|Winter)"
DATE_RANGE_PATTERN = f"({MONTH_REGEX}\\s+\\d{{4}}|\\d{{4}}|{MONTH_REGEX})\\s*(?:-|to|–|—)\\s*({MONTH_REGEX}\\s+\\d{{4}}|\\d{{4}}|Present|Current)"
DATE_PATTERN = f"(?:{MONTH_REGEX}\\s+)?\\d{{4}}"
PHONE_PATTERN = r"\+?\d[\d\s().-]{8,}\d"
EMAIL_PATTERN = r"[\w.+-]+@[\w-]+\.[\w.-]+"


class DeterministicResumeParser:
    """Parses unstructured resume text into a structured dictionary."""

    def __init__(self, text: str):
        self.text = text
        self.lines = [line.strip() for line in text.split("\n") if line.strip()]
        self.sections = self._chunk_sections()

    def parse(self) -> dict[str, Any]:
        """Extract all available fields."""
        payload: dict[str, Any] = {"resume_text": self.text}

        # 1. Identity & Contact
        identity = self._extract_identity()
        if identity:
            payload.update(identity)

        contact = self._extract_contact()
        if contact:
            payload.update(contact)

        # 2. Sections
        education = self._extract_education()
        if education:
            payload["education"] = education

        experience = self._extract_experience()
        if experience:
            payload["experiences"] = experience

        projects = self._extract_projects()
        if projects:
            payload["projects"] = projects

        skills = self._extract_skills()
        if skills:
            payload["skills"] = skills

        certifications = self._extract_certifications()
        if certifications:
            payload["certifications"] = certifications

        achievements = self._extract_achievements()
        if achievements:
            payload["achievements"] = achievements

        # Extract links from everywhere
        links = self._extract_links()
        if links:
            payload.update(links)

        return payload

    def _chunk_sections(self) -> dict[str, list[str]]:
        """Group lines by major section headers."""
        sections: dict[str, list[str]] = {"UNASSIGNED": []}
        current_section = "UNASSIGNED"

        headers = {
            "EDUCATION": [
                "EDUCATION",
                "ACADEMICS",
                "ACADEMIC BACKGROUND",
                "QUALIFICATIONS",
            ],
            "EXPERIENCE": [
                "EXPERIENCE",
                "WORK EXPERIENCE",
                "INTERNSHIPS",
                "PROFESSIONAL EXPERIENCE",
                "EMPLOYMENT",
                "INTERNSHIP & EXPERIENCE",
            ],
            "PROJECTS": ["PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"],
            "SKILLS": ["SKILLS", "TECHNICAL SKILLS", "TECHNOLOGIES"],
            "CERTIFICATIONS": ["CERTIFICATIONS", "LICENSES", "COURSES"],
            "ACHIEVEMENTS": ["ACHIEVEMENTS", "AWARDS", "PUBLICATIONS"],
        }

        for line in self.lines:
            upper_line = line.upper().strip()
            # Try to match a header
            matched_header = None
            for key, keywords in headers.items():
                if upper_line in keywords or any(
                    upper_line.startswith(kw) for kw in keywords
                ):
                    matched_header = key
                    break

            if matched_header:
                current_section = matched_header
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(line)

        return sections

    def _extract_identity(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if not self.lines:
            return result

        # First non-empty line under 50 chars without @ is usually the name
        first_line = self.lines[0]
        if len(first_line) < 50 and "@" not in first_line:
            result["full_name"] = first_line
            parts = first_line.split()
            if len(parts) >= 2:
                result["first_name"] = parts[0]
                result["last_name"] = " ".join(parts[1:])
            else:
                result["first_name"] = first_line

        # Look for location (simple heuristic: city, state or country pattern)
        for line in self.lines[:10]:
            if re.search(r"^[a-zA-Z\s]+,\s*[A-Z]{2}(?:\s+\d{5})?$", line) or re.search(
                r"^[A-Z][a-z]+,\s*[A-Z][a-z]+$", line
            ):
                if line != result.get("full_name"):
                    result["location"] = line
                    break

        return result

    def _extract_contact(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        # Email
        email_match = re.search(EMAIL_PATTERN, self.text)
        if email_match:
            result["email"] = email_match.group(0)

        # Phone
        phone_match = re.search(PHONE_PATTERN, self.text)
        if phone_match:
            result["phone"] = phone_match.group(0).strip()

        return result

    def _extract_links(self) -> dict[str, Any]:
        result: dict[str, Any] = {}

        github = re.search(r"github\.com/([a-zA-Z0-9-]+)", self.text, re.IGNORECASE)
        if github:
            result["github_url"] = f"https://github.com/{github.group(1)}"

        linkedin = re.search(
            r"linkedin\.com/in/([a-zA-Z0-9-]+)", self.text, re.IGNORECASE
        )
        if linkedin:
            result["linkedin_url"] = f"https://www.linkedin.com/in/{linkedin.group(1)}"

        return result

    def _extract_education(self) -> list[dict[str, Any]]:
        section = self.sections.get("EDUCATION", [])
        if not section:
            return []

        entries = []
        current_entry: dict[str, Any] = {}

        for line in section:
            # Date range detection
            date_match = re.search(DATE_RANGE_PATTERN, line, re.IGNORECASE)

            if date_match:
                raw_start = date_match.group(1).strip()
                raw_end = date_match.group(2).strip()

                end_norm = normalize_date(raw_end)
                fallback_year = (
                    end_norm[:4]
                    if end_norm and re.search(r"^\d{4}", end_norm)
                    else None
                )
                start_norm = normalize_date(raw_start, fallback_year)

                if start_norm:
                    current_entry["start_date"] = start_norm
                if end_norm:
                    current_entry["end_date"] = end_norm

                line = line.replace(date_match.group(0), "").strip()
                if not line:
                    entries.append(current_entry)
                    current_entry = {}
                continue

            # If we already have an institution and a credential and a date, any new line starts a new entry
            if "institution" in current_entry and "start_date" in current_entry:
                entries.append(current_entry)
                current_entry = {}

            # Naive assignment if it looks like an institution or degree
            if not line:
                continue

            if "institution" not in current_entry and (
                "University" in line
                or "College" in line
                or "School" in line
                or "Institute" in line
            ):
                current_entry["institution"] = line.strip(" ,.-|")
            elif "credential" not in current_entry and (
                "Bachelor" in line
                or "Master" in line
                or "B.Tech" in line
                or "B.E." in line
                or "Degree" in line
                or "BSc" in line
                or "MSc" in line
            ):
                current_entry["credential"] = line.strip(" ,.-|")
            elif "field_of_study" not in current_entry and (
                "Engineering" in line or "Science" in line or "Arts" in line
            ):
                current_entry["field_of_study"] = line.strip(" ,.-|")
            else:
                # If we don't have an institution yet, grab the first non-date line
                if "institution" not in current_entry:
                    current_entry["institution"] = line.strip(" ,.-|")
                elif "credential" not in current_entry:
                    current_entry["credential"] = line.strip(" ,.-|")

        if current_entry:
            entries.append(current_entry)

        return entries

    def _extract_experience(self) -> list[dict[str, Any]]:
        section = self.sections.get("EXPERIENCE", [])
        if not section:
            return []

        entries = []
        current_entry: dict[str, Any] = {}

        for line in section:
            date_match = re.search(DATE_RANGE_PATTERN, line, re.IGNORECASE)

            if date_match:
                raw_start = date_match.group(1).strip()
                raw_end = date_match.group(2).strip()

                end_norm = normalize_date(raw_end)
                fallback_year = (
                    end_norm[:4]
                    if end_norm and re.search(r"^\d{4}", end_norm)
                    else None
                )
                start_norm = normalize_date(raw_start, fallback_year)

                if start_norm:
                    current_entry["start_date"] = start_norm
                if end_norm:
                    current_entry["end_date"] = end_norm

                if "current" in raw_end.lower() or "present" in raw_end.lower():
                    current_entry["is_current"] = True
                else:
                    current_entry["is_current"] = False

                line = line.replace(date_match.group(0), "").strip()
                if not line:
                    continue
            elif (
                current_entry
                and "start_date" in current_entry
                and not line.startswith("-")
                and not line.startswith("•")
                and not line.startswith("*")
                and len(line) < 60
            ):
                entries.append(current_entry)
                current_entry = {}

            is_bullet = (
                line.startswith("-") or line.startswith("•") or line.startswith("*")
            )
            is_long_desc = "start_date" in current_entry and len(line) >= 60

            if is_bullet or is_long_desc:
                if "description" not in current_entry:
                    current_entry["description"] = line.lstrip("-•* ")
                else:
                    current_entry["description"] += "\n" + line.lstrip("-•* ")
            else:
                # Assume organization comes first, then role
                if "organization" not in current_entry:
                    current_entry["organization"] = line.strip(" ,.-|")
                elif "title" not in current_entry:
                    current_entry["title"] = line.strip(" ,.-|")

        if current_entry:
            entries.append(current_entry)

        return entries

    def _extract_projects(self) -> list[dict[str, Any]]:
        section = self.sections.get("PROJECTS", [])
        if not section:
            return []

        entries = []
        current_entry: dict[str, Any] = {}

        for line in section:
            # We assume projects might not have dates, so we start a new one when a line doesn't start with a bullet
            if line.startswith("-") or line.startswith("•") or line.startswith("*"):
                if "description" not in current_entry:
                    current_entry["description"] = line.lstrip("-•* ")
                else:
                    current_entry["description"] += "\n" + line.lstrip("-•* ")
            else:
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                # Split tech stack if pipe or colon is used
                if "|" in line:
                    parts = line.split("|")
                    current_entry["name"] = parts[0].strip()
                    techs = parts[1].split(",")
                    current_entry["technologies"] = [
                        t.strip() for t in techs if t.strip()
                    ]
                else:
                    current_entry["name"] = line.strip()

        if current_entry:
            entries.append(current_entry)

        return entries

    def _extract_skills(self) -> list[str]:
        # Always check the skills section specifically
        section = self.sections.get("SKILLS", [])
        found_skills = []

        # Check explicit section first
        for line in section:
            # Split by common delimiters
            parts = re.split(r"[,|:•-]", line)
            for part in parts:
                cleaned = part.strip()
                # Ignore headers like "Programming Languages:" if split didn't catch it perfectly
                if cleaned and " " not in cleaned.strip(": "):
                    found_skills.append(cleaned.strip(": "))
                elif cleaned:
                    found_skills.append(cleaned)

        # Fallback to the broad search used previously
        tech_keywords = [
            "Python",
            "Java",
            "C++",
            "C#",
            "JavaScript",
            "TypeScript",
            "Go",
            "Rust",
            "Ruby",
            "PHP",
            "AWS",
            "Azure",
            "GCP",
            "Docker",
            "Kubernetes",
            "SQL",
            "PostgreSQL",
            "MongoDB",
            "React",
            "Angular",
            "Vue",
            "Machine Learning",
            "Data Science",
            "Streamlit",
            "TensorFlow",
            "PyTorch",
            "Linux",
            "Git",
            "FastAPI",
            "Flask",
            "Redis",
            "ChromaDB",
        ]

        text_lower = self.text.lower()
        for kw in tech_keywords:
            if (
                re.search(r"\b" + re.escape(kw.lower()) + r"\b", text_lower)
                and kw not in found_skills
            ):
                found_skills.append(kw)

        # Deduplicate while preserving case from original list
        final_skills = []
        seen = set()
        for skill in found_skills:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                final_skills.append(skill)

        return final_skills

    def _extract_certifications(self) -> list[dict[str, Any]]:
        section = self.sections.get("CERTIFICATIONS", [])
        if not section:
            return []

        entries = []
        for line in section:
            if not line:
                continue
            date_match = re.search(DATE_PATTERN, line)
            entry = {}
            if date_match:
                entry["year"] = date_match.group(0).strip()
                line = line.replace(date_match.group(0), "").strip()

            entry["name"] = line.strip(" ,.-|")
            if entry["name"]:
                entries.append(entry)

        return entries

    def _extract_achievements(self) -> list[dict[str, Any]]:
        section = self.sections.get("ACHIEVEMENTS", [])
        if not section:
            return []

        entries = []
        for line in section:
            if not line:
                continue
            date_match = re.search(DATE_PATTERN, line)
            entry = {}
            if date_match:
                entry["year"] = date_match.group(0).strip()
                line = line.replace(date_match.group(0), "").strip()

            # Simple assumption: anything left is the achievement title
            entry["name"] = line.strip(" ,.-|•*")
            if entry["name"]:
                entries.append(entry)

        return entries
