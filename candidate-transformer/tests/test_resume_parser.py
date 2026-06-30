from src.adapters.resume_parser import DeterministicResumeParser

MOCK_RESUME = """John Doe
john.doe@example.com
+1 (555) 123-4567
San Francisco, CA

SUMMARY
A passionate software engineer with extensive experience in building AI pipelines.

EDUCATION
Sri Ramakrishna Engineering College
Bachelor of Engineering in Computer Science
Aug 2018 - May 2022

SBOA Matriculation Higher Secondary School
High School Diploma
2016 - 2018

EXPERIENCE
Larsen & Toubro
Software Engineer
June 2022 - Present
- Developed scalable microservices using Python and Docker.
- Improved pipeline efficiency by 40%.

NxtLogic
Intern
Jan 2022 - May 2022
- Assisted in building a React frontend for the main dashboard.

Tata iQ
Data Science Intern
May 2021 - Aug 2021
- Built predictive models using TensorFlow and PyTorch.

PROJECTS
TalentForgeAI | Python, FastAPI, Docker
- Built an AI-driven resume parser and intelligence engine.
- https://github.com/johndoe/talentforgeai

PsyCare
- Mental health chatbot.

FORENSSIAI | Python, React
- Forensic analysis tool.

SKILLS
Programming Languages: Python, Java
Frameworks: React, FastAPI, Flask
Databases: PostgreSQL, MongoDB, Redis, ChromaDB
Tools: Docker, Linux, Git
AI/ML: TensorFlow, PyTorch

ACHIEVEMENTS
StartupTN Hackathon - 2023
L&T EduTech Hackathon - 2022
BITS Pilani Hackathon - 2021
IEEE Paper - 2022

CERTIFICATIONS
CrewAI - 2023
Google Cloud - 2022
"""


def test_resume_parser_identity_and_contact() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert result["full_name"] == "John Doe"
    assert result["first_name"] == "John"
    assert result["last_name"] == "Doe"
    assert result["email"] == "john.doe@example.com"
    assert result["phone"] == "+1 (555) 123-4567"
    assert result["location"] == "San Francisco, CA"


def test_resume_parser_education() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert "education" in result
    edu = result["education"]
    assert len(edu) == 2
    assert edu[0]["institution"] == "Sri Ramakrishna Engineering College"
    assert edu[0]["credential"] == "Bachelor of Engineering in Computer Science"
    assert edu[0]["start_date"] == "2018-08"
    assert edu[0]["end_date"] == "2022-05"

    assert edu[1]["institution"] == "SBOA Matriculation Higher Secondary School"
    assert edu[1]["start_date"] == "2016"
    assert edu[1]["end_date"] == "2018"


def test_resume_parser_experience() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert "experiences" in result
    exp = result["experiences"]
    assert len(exp) == 3

    assert exp[0]["organization"] == "Larsen & Toubro"
    assert exp[0]["title"] == "Software Engineer"
    assert exp[0]["start_date"] == "2022-06"
    assert "end_date" not in exp[0] or exp[0]["end_date"] is None
    assert exp[0]["is_current"] is True
    assert "Developed scalable microservices" in exp[0]["description"]

    assert exp[1]["organization"] == "NxtLogic"
    assert exp[1]["title"] == "Intern"
    assert exp[1]["start_date"] == "2022-01"
    assert exp[1]["end_date"] == "2022-05"

    assert exp[2]["organization"] == "Tata iQ"
    assert exp[2]["title"] == "Data Science Intern"
    assert exp[2]["start_date"] == "2021-05"
    assert exp[2]["end_date"] == "2021-08"


def test_resume_parser_projects() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert "projects" in result
    proj = result["projects"]
    assert len(proj) == 3

    assert proj[0]["name"] == "TalentForgeAI"
    assert "Python" in proj[0]["technologies"]
    assert "FastAPI" in proj[0]["technologies"]

    assert proj[1]["name"] == "PsyCare"
    assert proj[2]["name"] == "FORENSSIAI"


def test_resume_parser_skills() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert "skills" in result
    skills = set([s.lower() for s in result["skills"]])
    expected = {
        "python",
        "java",
        "react",
        "docker",
        "postgresql",
        "tensorflow",
        "pytorch",
        "linux",
        "git",
        "fastapi",
        "flask",
        "mongodb",
        "redis",
        "chromadb",
    }
    for skill in expected:
        assert skill in skills


def test_resume_parser_achievements() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert "achievements" in result
    achievements = [a["name"] for a in result["achievements"]]

    assert "StartupTN Hackathon" in achievements
    assert "L&T EduTech Hackathon" in achievements
    assert "BITS Pilani Hackathon" in achievements
    assert "IEEE Paper" in achievements


def test_resume_parser_certifications() -> None:
    parser = DeterministicResumeParser(MOCK_RESUME)
    result = parser.parse()

    assert "certifications" in result
    certs = [c["name"] for c in result["certifications"]]

    assert "CrewAI" in certs
    assert "Google Cloud" in certs


def test_resume_parser_date_normalization() -> None:
    from src.adapters.resume_parser import normalize_date

    assert normalize_date("Dec 2025") == "2025-12"
    assert normalize_date("Jan 2026") == "2026-01"
    assert normalize_date("May 2025") == "2025-05"
    assert normalize_date("June 2025") == "2025-06"
    assert normalize_date("2023") == "2023"
    assert normalize_date("Present") is None
    assert normalize_date("Current") is None

    # testing the fallback mapping behavior (which normally happens inside _extract_experience/education)
    assert normalize_date("May", fallback_year="2025") == "2025-05"

    # End-to-end range extraction tests
    parser = DeterministicResumeParser("EDUCATION\nUniversity\nMay – June 2025")
    res = parser.parse()
    assert res["education"][0]["start_date"] == "2025-05"
    assert res["education"][0]["end_date"] == "2025-06"

    parser = DeterministicResumeParser("EXPERIENCE\nCompany\n2023 - 2027")
    res = parser.parse()
    assert res["experiences"][0]["start_date"] == "2023"
    assert res["experiences"][0]["end_date"] == "2027"
