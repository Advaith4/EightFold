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
MONTH_REGEX = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?"
    r"|Nov(?:ember)?|Dec(?:ember)?|Spring|Summer|Fall|Winter)"
)
DATE_RANGE_PATTERN = (
    f"({MONTH_REGEX}\\s+\\d{{4}}|\\d{{4}}|{MONTH_REGEX})"
    f"\\s*(?:-|to|–|—)\\s*"
    f"({MONTH_REGEX}\\s+\\d{{4}}|\\d{{4}}|Present|Current)"
)
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

        # Generate Decision Log / Parsing Summary
        summary = ["Resume Parsing Summary\n"]
        if "full_name" in payload:
            summary.append("✓ Name extracted")
        else:
            summary.append("Missing: Name")

        if "email" in payload:
            summary.append("✓ Email extracted")
        else:
            summary.append("Missing: Email")

        if "phone" in payload:
            summary.append("✓ Phone extracted")
        else:
            summary.append("Missing: Phone")

        if "github_url" in payload:
            summary.append("✓ GitHub extracted")
        else:
            summary.append("Missing: GitHub")

        if "skills" in payload and payload["skills"]:
            summary.append(f"✓ Skills extracted ({len(payload['skills'])})")
        else:
            summary.append("Missing: Skills")

        if "experiences" in payload and payload["experiences"]:
            summary.append(f"✓ Experience extracted ({len(payload['experiences'])})")
        else:
            summary.append("Missing: Experience")

        if "education" in payload and payload["education"]:
            summary.append(f"✓ Education extracted ({len(payload['education'])})")
        else:
            summary.append("Missing: Education")

        if "projects" in payload and payload["projects"]:
            summary.append(f"✓ Projects extracted ({len(payload['projects'])})")
        else:
            summary.append("Missing: Projects")

        if "certifications" in payload and payload["certifications"]:
            summary.append(
                f"✓ Certifications extracted ({len(payload['certifications'])})"
            )
        else:
            summary.append("Missing: Certifications")

        missing_links = []
        if "linkedin_url" not in payload:
            missing_links.append("LinkedIn")
        if "portfolio_url" not in payload:
            missing_links.append("Portfolio")

        if missing_links:
            summary.append("\nMissing:")
            for link in missing_links:
                summary.append(f"• {link}")

        # Attach parsing summary to metadata for the RawCandidateRecord.
        payload["metadata"] = {"parsing_summary": "\n".join(summary)}

        return payload

    def _chunk_sections(self) -> dict[str, list[str]]:
        """Group lines by major section headers."""
        sections: dict[str, list[str]] = {"UNASSIGNED": []}
        current_section = "UNASSIGNED"

        headers = {
            "SUMMARY": ["SUMMARY", "PROFILE", "OBJECTIVE", "PROFESSIONAL SUMMARY"],
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
                "WORK HISTORY",
            ],
            "PROJECTS": ["PROJECTS", "PERSONAL PROJECTS", "ACADEMIC PROJECTS"],
            "SKILLS": [
                "SKILLS",
                "TECHNICAL SKILLS",
                "TECHNOLOGIES",
                "CORE SKILLS",
                "CORE COMPETENCIES",
            ],
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

        # First line is often the name if it is short and doesn't contain contact info
        for line in self.lines[:5]:
            if (
                len(line) < 50
                and "@" not in line
                and not re.search(PHONE_PATTERN, line)
            ):
                # Avoid section headers
                if line.upper() in [
                    "SUMMARY",
                    "PROFILE",
                    "OBJECTIVE",
                    "EXPERIENCE",
                    "EDUCATION",
                    "SKILLS",
                ]:
                    continue
                # Probably a name
                result["full_name"] = line
                parts = line.split()
                if len(parts) >= 2:
                    result["first_name"] = parts[0]
                    result["last_name"] = " ".join(parts[1:])
                else:
                    result["first_name"] = line
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

        patterns = {
            "github_url": r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9-]+)",
            "linkedin_url": r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-]+)",
            "kaggle_url": r"(?:https?://)?(?:www\.)?kaggle\.com/([a-zA-Z0-9-]+)",
            "leetcode_url": r"(?:https?://)?(?:www\.)?leetcode\.com/u?/([a-zA-Z0-9-]+)",
            "hackerrank_url": r"(?:https?://)?(?:www\.)?hackerrank\.com/([a-zA-Z0-9-]+)",
            "codeforces_url": r"(?:https?://)?(?:www\.)?codeforces\.com/profile/([a-zA-Z0-9-]+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                if key == "github_url":
                    result[key] = f"https://github.com/{match.group(1)}"
                elif key == "linkedin_url":
                    result[key] = f"https://www.linkedin.com/in/{match.group(1)}"
                elif key == "kaggle_url":
                    result[key] = f"https://www.kaggle.com/{match.group(1)}"
                elif key == "leetcode_url":
                    result[key] = f"https://leetcode.com/{match.group(1)}"
                elif key == "hackerrank_url":
                    result[key] = f"https://www.hackerrank.com/{match.group(1)}"
                elif key == "codeforces_url":
                    result[key] = f"https://codeforces.com/profile/{match.group(1)}"

        # Portfolio detection
        portfolio_match = re.search(
            r"(?:https?://)?([a-zA-Z0-9-]+\.(?:com|net|org|dev|io|me))/?\b",
            self.text,
            re.IGNORECASE,
        )
        if portfolio_match:
            domain = portfolio_match.group(1).lower()
            if not any(
                x in domain
                for x in [
                    "github",
                    "linkedin",
                    "kaggle",
                    "leetcode",
                    "hackerrank",
                    "codeforces",
                    "gmail",
                    "yahoo",
                ]
            ):
                result["portfolio_url"] = f"https://{domain}"

        return result

    def _extract_education(self) -> list[dict[str, Any]]:
        section = self.sections.get("EDUCATION", [])
        if not section:
            return []

        entries = []
        current_entry: dict[str, Any] = {}

        for line in section:
            date_match = re.search(DATE_RANGE_PATTERN, line, re.IGNORECASE)

            if not date_match:
                single_date_match = re.search(DATE_PATTERN, line)
                if single_date_match:
                    raw_end = single_date_match.group(0).strip()
                    date_match = single_date_match
                else:
                    date_match = None

            if date_match:
                if len(date_match.groups()) > 1 and date_match.group(2):
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
                else:
                    end_norm = normalize_date(date_match.group(0).strip())
                    if end_norm:
                        current_entry["end_date"] = end_norm

                line = line.replace(date_match.group(0), "").strip(" ,.-|")
                if not line:
                    continue

            clean_line = line.strip(" ,.-|")
            if not clean_line:
                continue

            if ("start_date" in current_entry or "end_date" in current_entry) and len(
                clean_line
            ) < 60:
                entries.append(current_entry)
                current_entry = {}

            if "institution" not in current_entry and any(
                kw in clean_line
                for kw in ["University", "College", "School", "Institute", "Academy"]
            ):
                current_entry["institution"] = clean_line
            elif "credential" not in current_entry and any(
                kw in clean_line
                for kw in [
                    "Bachelor",
                    "Master",
                    "B.Tech",
                    "B.E.",
                    "BSc",
                    "MSc",
                    "PhD",
                    "Degree",
                    "B.S.",
                    "M.S.",
                    "Diploma",
                ]
            ):
                current_entry["credential"] = clean_line
            elif "field_of_study" not in current_entry and any(
                kw in clean_line
                for kw in [
                    "Engineering",
                    "Science",
                    "Arts",
                    "Computer",
                    "Business",
                    "Mathematics",
                    "Physics",
                ]
            ):
                current_entry["field_of_study"] = clean_line
            elif "gpa" in clean_line.lower() or "cgpa" in clean_line.lower():
                pass
            else:
                if "institution" not in current_entry:
                    current_entry["institution"] = clean_line
                elif "credential" not in current_entry:
                    current_entry["credential"] = clean_line

        if current_entry and (
            "institution" in current_entry or "credential" in current_entry
        ):
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

                current_entry["is_current"] = bool(
                    "current" in raw_end.lower() or "present" in raw_end.lower()
                )

                remainder = line.replace(date_match.group(0), "").strip(" ,.-|")
                if remainder and "organization" not in current_entry:
                    current_entry["organization"] = remainder
                continue

            is_bullet = (
                line.startswith("-") or line.startswith("•") or line.startswith("*")
            )
            clean_line = line.strip(" ,.-|")

            # A short non-bullet line after a date starts a new entry.
            if not is_bullet and "start_date" in current_entry and len(clean_line) < 60:
                entries.append(current_entry)
                current_entry = {}

            if is_bullet:
                desc = line.lstrip("-•* ")
                if "description" not in current_entry:
                    current_entry["description"] = desc
                else:
                    current_entry["description"] += "\n" + desc
            else:
                if len(clean_line) < 60:
                    if "organization" not in current_entry:
                        current_entry["organization"] = clean_line
                    elif "title" not in current_entry:
                        current_entry["title"] = clean_line
                    else:
                        if "description" not in current_entry:
                            current_entry["description"] = clean_line
                        else:
                            current_entry["description"] += "\n" + clean_line
                else:
                    if "description" not in current_entry:
                        current_entry["description"] = clean_line
                    else:
                        current_entry["description"] += "\n" + clean_line

        if current_entry and (
            "organization" in current_entry or "title" in current_entry
        ):
            entries.append(current_entry)

        return entries

    def _extract_projects(self) -> list[dict[str, Any]]:
        section = self.sections.get("PROJECTS", [])
        if not section:
            return []

        entries = []
        current_entry: dict[str, Any] = {}

        for line in section:
            # Projects might not have dates, so a non-bullet line
            # starts a new entry.
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

        alias_map = {
            "js": "JavaScript",
            "reactjs": "React",
            "react.js": "React",
            "node": "Node.js",
            "nodejs": "Node.js",
            "node.js": "Node.js",
            "ml": "Machine Learning",
            "ai": "Artificial Intelligence",
            "tensorflow": "TensorFlow",
            "tensor flow": "TensorFlow",
            "pytorch": "PyTorch",
            "aws": "AWS",
            "gcp": "GCP",
            "vuejs": "Vue",
            "vue.js": "Vue",
        }

        # Check explicit section first
        for line in section:
            # Split by common delimiters
            parts = re.split(r"[,|:•-]", line)
            for part in parts:
                cleaned = part.strip()
                # Ignore headers like "Programming Languages:"
                if cleaned and " " not in cleaned.strip(": "):
                    found_skills.append(cleaned.strip(": "))
                elif cleaned:
                    found_skills.append(cleaned)

        # Fallback to the broad search used previously for missing skills
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
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text_lower):
                found_skills.append(kw)

        # Deduplicate and normalize
        final_skills = []
        seen = set()
        for skill in found_skills:
            normalized_raw = skill.strip(" .,;*•").lower()
            if not normalized_raw:
                continue

            canonical = alias_map.get(normalized_raw, skill.strip(" .,;*•"))

            # Simple title case for unmapped skills if they are lowercase
            if canonical == normalized_raw and canonical.islower():
                canonical = canonical.title()

            if canonical.lower() not in seen:
                seen.add(canonical.lower())
                final_skills.append(canonical)

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
