from src.agents.intelligence import CandidateIntelligenceAgent
from src.models import PayloadFormat, RawCandidateRecord, SourceType

resume = RawCandidateRecord(
    record_id="resume1",
    source_type=SourceType.RESUME,
    source_system="Manual",
    payload_format=PayloadFormat.JSON_DOCUMENT,
    checksum="resume1_chk",
    payload={
        "name": "Arjun",
        "email": "arjun@test.com",
        "experience": [
            {"company": "L&T", "title": "Software Intern", "start_date": "2025-06"}
        ],
        "education": [{"school": "NIT", "degree": "BTech"}],
        "skills": ["python", "java"],
        "resume_url": "http://resume",
    },
)

ats = RawCandidateRecord(
    record_id="ats1",
    source_type=SourceType.ATS,
    source_system="Greenhouse",
    payload_format=PayloadFormat.JSON_DOCUMENT,
    checksum="ats1_chk",
    payload={
        "name": "Arjun",
        "email": "arjun@test.com",
        "experience": [
            {
                "company": "L&T",
                "title": "Software Engineering Intern",
                "start_date": "2025-06",
            }
        ],
        "education": [{"school": "NIT", "degree": "BTech"}],
        "skills": ["python"],
        "portfolio_url": "http://portfolio",
    },
)

csv = RawCandidateRecord(
    record_id="csv1",
    source_type=SourceType.CSV,
    source_system="Eightfold",
    payload_format=PayloadFormat.CSV_ROW,
    checksum="csv1_chk",
    payload={
        "name": "Arjun",
        "email": "arjun@test.com",
        "experience": [
            {"company": "L&T", "title": "Software Intern", "start_date": "2025-06"}
        ],
        "education": [{"school": "NIT", "degree": "BTech"}],
        "skills": ["java"],
        "linkedin_url": "http://linkedin",
    },
)

agent = CandidateIntelligenceAgent()
result = agent.process([resume, ats, csv])

print(f"Groups: {len(result.candidate_groups)}")
print(f"Candidates: {len(result.canonical_candidates)}")

canonical = result.canonical_candidates[0]
print(f"Experiences: {len(canonical.experiences)}")
for exp in canonical.experiences:
    print(f" - {exp.organization} : {exp.title}")

print(f"Education: {len(canonical.education)}")
for edu in canonical.education:
    print(f" - {edu.institution} : {edu.credential}")

print(f"Skills: {len(canonical.skills)}")
print(f"Links: {len(canonical.links)}")

try:
    canonical.model_validate(canonical.model_dump())
    print("VALIDATION SUCCESS")
except Exception as e:
    print("VALIDATION FAILED", e)
