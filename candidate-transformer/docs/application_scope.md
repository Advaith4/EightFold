# Candidate Intelligence Transformation Engine - Application Scope

## Purpose

The Candidate Intelligence Transformation Engine is a deterministic backend and Streamlit demonstration application for consolidating heterogeneous candidate data sources into presentation-ready candidate intelligence.

The application accepts candidate inputs from resumes, ATS JSON, recruiter CSV, and GitHub profile URLs. It loads and classifies those inputs, converts them into raw candidate records, performs deterministic candidate intelligence, preserves provenance-oriented audit data, computes explainable workflow outputs, and renders recruiter-facing presentation views.

The system is intentionally deterministic. It does not use LLMs, AI inference, OCR, probabilistic extraction, repository cloning, or external enrichment beyond the GitHub REST API.

## In Scope

### Supported Inputs

- PDF resume files
- DOCX resume files
- ATS-style JSON files
- Recruiter CSV files
- GitHub user profile URLs

### File Loading

The loader layer is responsible only for technical file handling:

- Validate file existence, extension, readability, and non-empty content
- Load CSV and JSON as text
- Validate JSON syntax without interpreting business meaning
- Extract deterministic text from PDFs with a text layer
- Extract deterministic text from DOCX paragraphs and tables in document order
- Populate `FilePayload` and `FileMetadata`
- Record technical extraction status where applicable

Loaders do not parse candidates, infer fields, detect source type, perform business logic, or call AI/OCR systems.

### Source Detection

The source detection layer classifies loaded payloads or URLs using structural signals only:

- File extension
- MIME/content type
- JSON top-level keys
- CSV headers
- GitHub URL shape

Source detection does not inspect resume text for semantic resume keywords and does not perform candidate extraction.

### GitHub Integration

The GitHub integration supports public GitHub user profiles.

In scope:

- Validate `https://github.com/<username>` profile URLs
- Reject repositories, organizations, issues, pull requests, and reserved GitHub paths
- Fetch public profile data using the GitHub REST API
- Fetch public repository metadata
- Fetch repository language metadata
- Use `GITHUB_TOKEN` from environment or local `.env` when available
- Preserve raw GitHub profile, repository, language, and provenance metadata

Out of scope:

- Repository cloning
- Code analysis
- Inferring skills, seniority, experience, or education from repositories
- GitHub organization/repository source ingestion
- AI or external enrichment services

### Adapters

Adapters convert loaded or fetched source payloads into immutable `RawCandidateRecord` objects.

In scope:

- Resume adapter converts deterministic resume text extraction into raw resume payload fields
- ATS JSON adapter normalizes common shallow JSON field shapes
- Recruiter CSV adapter reads the first candidate row and normalizes headers
- GitHub adapter preserves raw GitHub API data in a raw candidate record

Adapters may parse explicit source fields, but they must not make probabilistic or AI-based inferences.

### Resume Extraction

The resume parser performs deterministic extraction from explicit text.

In scope:

- Identity
- Contact information
- Location
- Education
- Experience
- Projects
- Skills
- Certifications
- Achievements
- GitHub and LinkedIn links
- Partial date normalization to documented string formats

Limitations:

- Extraction is heuristic and layout-sensitive
- No OCR is performed for scanned PDFs
- No semantic AI parsing is used
- Complex resume layouts may produce incomplete output

### Candidate Intelligence

The Candidate Intelligence Agent transforms raw records into canonical candidate output using deterministic rules.

In scope:

- Detect available fields by source
- Detect duplicate source observations
- Group records using explicit deterministic match keys
- Build canonical candidate data from explicit raw values
- Apply source precedence for scalar conflicts
- Build decision logs
- Preserve provenance for scalar mapped fields
- Generate workflow status
- Compute deterministic confidence based on current policy and profile completeness
- Surface GitHub repository languages as explicit skill names when present in GitHub API metadata

Current grouping keys include:

- Email
- Phone
- GitHub URL or login
- LinkedIn URL
- Exact normalized name
- Name plus company/organization

### Merge Behavior

The current merge behavior is deterministic and source-priority based.

Priority order:

1. ATS
2. Resume
3. GitHub
4. Recruiter CSV
5. LinkedIn

Scalar fields are selected according to priority. Conflicting values are recorded in decision logs and workflow context.

### Presentation

The Presentation Agent converts intelligence output into UI/API-friendly view models.

In scope:

- Candidate header
- Candidate overview
- Confidence summary
- Provenance table rows
- Decision timeline
- Recruiter projection
- HR projection
- Engineering projection
- Raw JSON export view
- Missing and conflicting field summaries

Presentation does not modify canonical candidate data and does not perform new candidate reasoning.

### Streamlit UI

The Streamlit app provides a demonstration interface.

In scope:

- Upload resume, ATS JSON, and recruiter CSV files
- Enter a GitHub profile URL
- Run the backend processing service
- Display candidate summary
- Display pipeline status, decision log, confidence, provenance, recruiter view, and raw JSON
- Show user-friendly errors for processing failures

The UI is a demonstration client, not a production REST API.

## Out of Scope

The following are intentionally out of scope for the current deterministic application:

- LLM reasoning
- AI extraction
- OCR
- Probabilistic parsing
- Repository cloning
- Source enrichment outside GitHub REST API
- LinkedIn API integration
- Browser automation
- Background jobs
- Persistent database storage
- Authentication and authorization
- Multi-user session management
- Production deployment infrastructure
- PDF/DOCX export generation
- REST API implementation
- CLI implementation

## Primary Execution Flow

```text
User inputs
  -> CandidateProcessingService
  -> AgentOrchestrator
  -> IntakeAgent
  -> Loaders or GitHubFetcher
  -> SourceDetector
  -> Source Adapters
  -> RawCandidateRecord[]
  -> CandidateIntelligenceAgent
  -> CandidateGroup[]
  -> CanonicalCandidate[]
  -> IntelligenceResult
  -> PresentationAgent
  -> PresentationResult
  -> Streamlit UI
```

## Package Responsibilities

### `src/loaders/`

Technical file loading only. Produces `FilePayload` objects.

### `src/detection/`

Deterministic source classification using structural signals.

### `src/github/`

GitHub profile fetching and raw GitHub payload adaptation.

### `src/adapters/`

Conversion from source-specific payloads into `RawCandidateRecord`.

### `src/models/`

Domain models, canonical candidate aggregate, value objects, provenance, confidence, decision logs, and enums.

### `src/agents/`

Agent orchestration, intake routing, candidate intelligence, grouping metadata, deterministic merge behavior, and presentation projection.

### `src/services/`

Application-level service entry point and dependency container.

### `src/ui/`

Streamlit rendering components, tabs, formatting helpers, upload handling, and layout orchestration.

### `src/pipeline/` and `src/interfaces/`

Foundational pipeline contracts and interfaces retained for architecture structure and future extension.

### `tests/`

Unit and integration-style tests for loaders, detection, adapters, GitHub, agents, services, models, configuration, logging, and UI startup.

## Data Contracts

### `FilePayload`

Represents exactly one loaded file representation:

- `text`, or
- `content_bytes`

Includes loader-owned `FileMetadata`.

### `RawCandidateRecord`

Represents immutable source data before canonical transformation.

Contains:

- source type
- source system
- source record ID
- payload format
- raw payload
- optional raw text
- checksum
- metadata

### `CandidateGroup`

Represents deterministic grouping of raw records believed to describe the same candidate.

Contains:

- group ID
- grouped raw records
- explicit match keys used for grouping

### `CanonicalCandidate`

Aggregate root for normalized candidate information.

Contains:

- identity
- contact info
- location
- experience
- education
- skills
- links
- summary
- confidence
- provenance
- decision logs
- audit information

### `IntelligenceResult`

Carries candidate intelligence output:

- primary canonical candidate
- decision context
- candidate groups
- canonical candidates

### `PresentationResult`

Presentation-ready export model consumed by Streamlit and future clients.

## Determinism Rules

- Same inputs should produce equivalent outputs except timestamp fields.
- Source priority controls scalar merge decisions.
- Duplicate grouping uses explicit normalized source values.
- Confidence is rule-based and explainable.
- No model may rely on AI, OCR, or probabilistic inference.

## Known Current Limitations

- Streamlit currently presents the primary candidate result rather than a full multi-candidate list.
- Resume parsing is deterministic but heuristic and may miss fields in unusual layouts.
- Provenance presentation is simplified and does not yet expose every canonical field's full provenance detail.
- Confidence is explainable at a high level but not yet a full per-field formula with all calculation inputs displayed.
- Recruiter CSV adapter currently processes the first row of a CSV payload.
- GitHub rate-limit behavior is handled, but live API behavior still depends on network availability and token permissions.
- No persistent storage is implemented.

## Release Demonstration Scope

A successful Version 1.0 demonstration should show:

- Uploading a resume file
- Processing an ATS JSON payload
- Processing a recruiter CSV payload
- Entering a GitHub profile URL
- Combining overlapping sources for the same candidate
- Producing a canonical candidate profile
- Showing deterministic decisions and conflicts
- Showing provenance-oriented output
- Showing confidence and missing-field summaries
- Rendering presentation views without backend crashes
