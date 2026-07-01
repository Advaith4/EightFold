# Candidate Intelligence Transformation Engine

A deterministic candidate intelligence pipeline that ingests heterogeneous candidate data, groups duplicate records, builds canonical candidate profiles, and produces explainable presentation-ready JSON output.


## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
streamlit run app.py
```

On macOS/Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Environment Variables

Create a local `.env` file from the example file:

```bash
copy .env.example .env
```

Use placeholders like this. Do not commit real API keys.

```env
APP_ENV=local
CONFIG_PATH=config/default.yaml
LOGGING_CONFIG_PATH=config/logging.yaml
GITHUB_TOKEN=your_github_fine_grained_token_here
```

Notes:

- `GITHUB_TOKEN` is optional, but recommended for higher GitHub REST API rate limits.
- `.env` is ignored by Git and must stay local.

## Project Overview

The engine transforms candidate data from resumes, ATS exports, recruiter CSV files, and GitHub profiles into canonical, explainable candidate records. It focuses on deterministic processing rather than AI inference, so every grouping and transformation decision is reproducible and auditable.

## Architecture Overview

```mermaid
flowchart LR
    user([User]) --> app[Streamlit Web Application]

    subgraph ui[Input Surface]
        resume[Resume Upload]
        ats[ATS JSON]
        csv[Recruiter CSV]
        github[GitHub Profile URL]
        config[Runtime Config]
    end

    app --> resume
    app --> ats
    app --> csv
    app --> github
    app --> config

    resume --> service[Candidate Processing Service]
    ats --> service
    csv --> service
    github --> service
    config --> service

    service --> orchestrator[Agent Orchestrator]

    orchestrator --> intake[Intake Agent]
    orchestrator --> intelligence[Candidate Intelligence Agent]
    orchestrator --> presentation[Presentation Agent]

    subgraph intakeStage[Intake And Source Conversion]
        detection[Source Detection]
        parser[Resume Parser]
        atsAdapter[ATS Adapter]
        csvAdapter[CSV Adapter]
        githubAdapter[GitHub Adapter]
        raw[RawCandidateRecords]
    end

    intake --> detection
    detection --> parser
    detection --> atsAdapter
    detection --> csvAdapter
    detection --> githubAdapter
    parser --> raw
    atsAdapter --> raw
    csvAdapter --> raw
    githubAdapter --> raw

    raw --> intelligence

    subgraph intelligenceStage[Candidate Intelligence]
        normalize[Data Normalization\nEmail, Phone, Dates, Skills, GitHub Username]
        duplicate[Duplicate Detection]
        groups[Candidate Groups]
        canonicalGen[Canonical Candidate Generation]
        conflict[Conflict Resolution]
        provenance[Provenance Tracking]
        confidence[Confidence Scoring]
        canonical[Canonical Candidate]
    end

    intelligence --> normalize
    normalize --> duplicate
    duplicate --> groups
    groups --> canonicalGen
    canonicalGen --> conflict
    canonicalGen --> provenance
    canonicalGen --> confidence
    conflict --> canonical
    provenance --> canonical
    confidence --> canonical

    canonical --> presentation

    subgraph presentationStage[Current Streamlit Presentation Tabs]
        candidateTab[Candidate]
        decision[Decision Log]
        confView[Confidence]
        provView[Provenance]
        recruiter[Recruiter View]
        rawJson[Raw JSON]
        projection[Runtime Projection Layer\nDefault / Custom Output Schema]
        validation[Schema Validation]
        final[Final JSON + Streamlit Dashboard]
    end

    presentation --> candidateTab
    presentation --> decision
    presentation --> confView
    presentation --> provView
    presentation --> recruiter
    presentation --> rawJson
    canonical --> projection
    candidateTab --> projection
    decision --> projection
    confView --> projection
    provView --> projection
    recruiter --> projection
    rawJson --> projection
    projection --> validation
    validation --> final
```

Current Streamlit presentation tabs:

- Candidate
- Decision Log
- Confidence
- Provenance
- Recruiter View
- Raw JSON

## Supported Input Sources

- Resume PDF
- Resume DOCX
- ATS JSON object or array
- Recruiter CSV with one candidate per row
- GitHub profile URLs, one URL per line in the UI

## Features

- Multi-source ingestion
- Multi-candidate aggregation
- Deterministic duplicate detection
- Canonical profile generation
- Provenance tracking
- Confidence scoring
- Runtime-configurable JSON projection
- Presentation validation warnings
- Streamlit review UI
- Partial failure handling for invalid individual inputs

## Implementation Screenshots

### Main Streamlit UI

![Main Streamlit UI](candidate-transformer/docs/screenshots/ui-overview.png)

### Sample Input Uploads

![Sample Input Uploads](candidate-transformer/docs/screenshots/sample-input.png)

### Successful Processing

![Successful Processing](candidate-transformer/docs/screenshots/process-successful.png)

### Pipeline Overview

![Pipeline Overview](candidate-transformer/docs/screenshots/pipeline-overview.png)

### Decision Pipeline

![Decision Pipeline](candidate-transformer/docs/screenshots/decision-pipeline.png)

### Duplicate Detection

![Duplicate Detection](candidate-transformer/docs/screenshots/duplicate-detection.png)

### Candidate Selection

![Candidate Selection](candidate-transformer/docs/screenshots/candidate-selection.png)

### Candidate Profile

![Candidate Profile](candidate-transformer/docs/screenshots/candidate-profile.png)

### Confidence View

![Confidence View](candidate-transformer/docs/screenshots/confidence.png)

### Confidence Reason Breakdown

![Confidence Reason Breakdown](candidate-transformer/docs/screenshots/confidence-reason.png)

### Provenance View

![Provenance View](candidate-transformer/docs/screenshots/provenance.png)

### Recruiter View

![Recruiter View](candidate-transformer/docs/screenshots/recruiter-view.png)

### JSON Output

![JSON Output](candidate-transformer/docs/screenshots/json-output.png)

## Repository Structure

```text
candidate-transformer/
|-- app.py
|-- requirements.txt
|-- pyproject.toml
|-- README.md
|-- config/
|-- docs/
|   |-- adr/
|   |-- screenshots/
|   `-- application_scope.md
|-- sample_inputs/
|-- output/
|-- src/
|   |-- adapters/
|   |-- agents/
|   |-- detection/
|   |-- github/
|   |-- loaders/
|   |-- models/
|   |-- pipeline/
|   |-- services/
|   `-- ui/
`-- tests/
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running The Application

```bash
streamlit run app.py
```

The sidebar accepts:

- Multiple resume files
- Multiple ATS JSON files
- Multiple recruiter CSV files
- Multiple GitHub profile URLs, one per line

## Running Quality Checks

```bash
python -m pytest
python -m ruff check .
python -m mypy src tests app.py
```

Current validation status:

- `pytest`: 205 passed
- `ruff`: passing
- `mypy`: passing
- Streamlit startup: verified locally

## Sample Inputs

Sample data lives in `sample_inputs/`:

- `tarun_resume.pdf`
- `tarun_resume.txt`
- `tarun_ats.json`
- `tarun_recruiter.csv`
- `arjun_ats.json`
- `arjun_recruiter.csv`

These are deterministic local datasets for reviewer testing. GitHub live fetching is supported separately through public GitHub profile URLs.

## Output JSON Files

Generated pipeline artifacts live in `output/`:

- `output/default_output.json`: full `PresentationResult` generated by the service pipeline.
- `output/custom_output.json`: runtime-configured projection generated from canonical candidates.

These output files are generated by the actual pipeline and are included for submission review.

## Regenerating Output Artifacts

The committed output files were generated from the service pipeline using `sample_inputs/`. To regenerate them, run the application or call `CandidateProcessingService` from a short script using the sample files.

## Edge Cases Handled

- Multiple resumes in one run
- ATS JSON object and array formats
- Multiple recruiter CSV rows
- Multiple GitHub URLs
- Invalid GitHub URLs skipped without aborting the run
- Malformed ATS array entries skipped when possible
- Unsupported file inputs skipped at service aggregation boundaries
- Duplicate candidates grouped by deterministic identity signals
- Missing candidate fields surfaced as presentation warnings

## Considerations
- GitHub API rate limits may apply without a local `GITHUB_TOKEN`.

## Submission Checklist

- Repository contains only required source, docs, tests, sample inputs, outputs, and screenshots.
- Local `.env`, logs, caches, and virtual environments are ignored.
- `requirements.txt` supports clone-and-run setup.
- `sample_inputs/` contains deterministic demo files.
- `output/` contains generated JSON artifacts.
- README includes setup instructions, API key placeholders, screenshots, and quality commands.
- Tests, lint, and type checks pass.

## Future Improvements

- Candidate switching improvements in the Streamlit UI
- Richer field-level provenance presentation
- Expanded validation reporting
- Configurable source priority policies
- Optional persistent GitHub response cache
- API server wrapper around the service layer

## Demo Video 

Demo video link: _to be added before final submission_.

