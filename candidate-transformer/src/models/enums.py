"""Domain enum definitions from the candidate domain specification."""

from enum import Enum


class SourceType(str, Enum):  # noqa: UP042
    """Supported source categories for raw records and provenance."""

    CSV = "CSV"
    ATS = "ATS"
    RESUME = "Resume"
    LINKEDIN = "LinkedIn"
    GITHUB = "GitHub"


class PayloadFormat(str, Enum):  # noqa: UP042
    """Supported raw payload formats."""

    CSV_ROW = "csv_row"
    JSON_DOCUMENT = "json_document"
    PDF_TEXT = "pdf_text"
    DOCX_TEXT = "docx_text"
    API_RESPONSE = "api_response"


class IdentifierType(str, Enum):  # noqa: UP042
    """Supported candidate identifier types."""

    EMAIL = "email"
    PHONE = "phone"
    ATS_ID = "ats_id"
    LINKEDIN_URL = "linkedin_url"
    GITHUB_URL = "github_url"
    SOURCE_RECORD_ID = "source_record_id"


class RemotePreference(str, Enum):  # noqa: UP042
    """Supported remote work preference values."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class SkillCategory(str, Enum):  # noqa: UP042
    """Supported skill categories."""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    SOFT_SKILL = "soft_skill"
    DOMAIN = "domain"


class LinkType(str, Enum):  # noqa: UP042
    """Supported candidate link types."""

    LINKEDIN = "linkedin"
    GITHUB = "github"
    PORTFOLIO = "portfolio"
    RESUME = "resume"
    ATS_PROFILE = "ats_profile"
    OTHER = "other"


class DecisionType(str, Enum):  # noqa: UP042
    """Supported deterministic decision categories."""

    MAPPING = "mapping"
    NORMALIZATION = "normalization"
    GROUPING = "grouping"
    MERGE = "merge"
    VALIDATION = "validation"
    PROJECTION = "projection"


class ValidationStatus(str, Enum):  # noqa: UP042
    """Supported audit validation statuses."""

    NOT_VALIDATED = "not_validated"
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"
