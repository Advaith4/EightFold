"""GitHub source integration tests for Sprint 5.1."""

from __future__ import annotations

import json
from email.message import Message
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest
from src.exceptions import AdapterError, ValidationError
from src.github.exceptions import (
    GitHubAPIException,
    GitHubNetworkException,
    GitHubRateLimitException,
    GitHubTimeoutException,
    GitHubUserNotFoundException,
    InvalidGitHubURLException,
)
from src.github import GitHubAdapter, GitHubFetcher, GitHubPayload
from src.models import PayloadFormat, RawCandidateRecord
from src.models.enums import SourceType


class FakeResponse:
    """Minimal context-manager response for mocked GitHub API calls."""

    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class FakeGitHubAPI:
    """Path-keyed fake GitHub API opener."""

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.paths: list[str] = []

    def __call__(self, request: Request, timeout: float) -> FakeResponse:
        del timeout
        path = request.full_url.removeprefix("https://api.github.com")
        self.paths.append(path)
        response = self.responses[path]
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


def github_responses(
    *,
    repositories: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build deterministic mocked GitHub API responses."""
    repos = repositories if repositories is not None else [repository()]
    responses: dict[str, object] = {
        "/users/octocat": (
            profile
            if profile is not None
            else {
                "login": "octocat",
                "name": "The Octocat",
                "bio": "GitHub mascot",
                "company": "GitHub",
                "location": "Internet",
                "blog": "https://github.blog",
                "email": "octocat@example.com",
                "html_url": "https://github.com/octocat",
            }
        ),
        "/users/octocat/repos": repos,
    }
    for repo in repos:
        full_name = repo["full_name"]
        responses[f"/repos/{full_name}/languages"] = {"Python": 120, "HTML": 20}
    return responses


def repository() -> dict[str, Any]:
    """Return public repository metadata like the GitHub API."""
    return {
        "name": "hello-world",
        "full_name": "octocat/hello-world",
        "description": "Example repository",
        "html_url": "https://github.com/octocat/hello-world",
        "topics": ["example", "demo"],
        "fork": False,
        "archived": False,
    }


def test_github_fetcher_fetches_profile_repositories_and_languages() -> None:
    """GitHubFetcher returns raw profile, repository, and language payloads."""
    api = FakeGitHubAPI(github_responses())

    payload = GitHubFetcher(opener=api).fetch("https://github.com/octocat")

    assert isinstance(payload, GitHubPayload)
    assert payload.profile["login"] == "octocat"
    assert payload.repositories[0]["full_name"] == "octocat/hello-world"
    assert payload.languages["octocat/hello-world"] == {"Python": 120, "HTML": 20}
    assert api.paths == [
        "/users/octocat",
        "/users/octocat/repos",
        "/repos/octocat/hello-world/languages",
    ]


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/octocat",
        "https://example.com/octocat",
        "https://github.com/octocat/hello-world",
        "https://github.com/settings",
    ],
)
def test_github_fetcher_rejects_invalid_profile_urls(url: str) -> None:
    """GitHubFetcher accepts only HTTPS single-profile GitHub URLs."""
    with pytest.raises(InvalidGitHubURLException):
        GitHubFetcher(opener=FakeGitHubAPI({})).fetch(url)


def test_github_fetcher_rejects_repository_url() -> None:
    """Repository URLs are out of scope for Sprint 5.1."""
    with pytest.raises(InvalidGitHubURLException):
        GitHubFetcher(opener=FakeGitHubAPI({})).fetch(
            "https://github.com/octocat/hello-world"
        )


def test_github_fetcher_rejects_reserved_github_path() -> None:
    """Reserved GitHub paths are not user profiles."""
    with pytest.raises(InvalidGitHubURLException):
        GitHubFetcher(opener=FakeGitHubAPI({})).fetch("https://github.com/settings")


def test_github_fetcher_maps_404_to_adapter_error() -> None:
    """Missing profiles surface as existing adapter errors."""
    api = FakeGitHubAPI(
        {
            "/users/octocat": HTTPError(
                url="https://api.github.com/users/octocat",
                code=404,
                msg="not found",
                hdrs=Message(),
                fp=None,
            )
        }
    )

    with pytest.raises(GitHubUserNotFoundException, match="not found"):
        GitHubFetcher(opener=api).fetch("https://github.com/octocat")


def test_github_fetcher_maps_rate_limit_to_adapter_error() -> None:
    """Rate limits surface as existing adapter errors."""
    api = FakeGitHubAPI(
        {
            "/users/octocat": HTTPError(
                url="https://api.github.com/users/octocat",
                code=403,
                msg="rate limited",
                hdrs=Message(),
                fp=None,
            )
        }
    )

    with pytest.raises(GitHubRateLimitException, match="rate limit"):
        GitHubFetcher(opener=api).fetch("https://github.com/octocat")


def test_github_fetcher_maps_network_failure_to_adapter_error() -> None:
    """Network failures do not leak urllib exceptions."""
    api = FakeGitHubAPI({"/users/octocat": URLError("offline")})

    with pytest.raises(GitHubNetworkException, match="network"):
        GitHubFetcher(opener=api).fetch("https://github.com/octocat")


def test_github_fetcher_maps_timeout_failure() -> None:
    """Timeout failures are mapped to GitHubTimeoutException."""
    api = FakeGitHubAPI({"/users/octocat": URLError(TimeoutError("timed out"))})

    with pytest.raises(GitHubTimeoutException, match="timed out"):
        GitHubFetcher(opener=api).fetch("https://github.com/octocat")


def test_github_fetcher_rejects_invalid_urls() -> None:
    """Invalid URLs raise InvalidGitHubURLException."""
    with pytest.raises(InvalidGitHubURLException, match="profile URL"):
        GitHubFetcher().fetch("https://github.com/octocat/hello-world")

    with pytest.raises(InvalidGitHubURLException, match="user profile URL"):
        GitHubFetcher().fetch("https://github.com/settings")


def test_github_fetcher_handles_empty_repositories() -> None:
    """Profiles without public repositories still produce a GitHubPayload."""
    payload = GitHubFetcher(
        opener=FakeGitHubAPI(github_responses(repositories=[]))
    ).fetch("https://github.com/octocat")

    assert payload.repositories == []
    assert payload.languages == {}


def test_github_fetcher_rejects_empty_profile() -> None:
    """Empty API profile objects surface as existing adapter errors."""
    api = FakeGitHubAPI(github_responses(profile={}))

    with pytest.raises(AdapterError, match="empty"):
        GitHubFetcher(opener=api).fetch("https://github.com/octocat")


def test_github_fetcher_preserves_missing_profile_fields() -> None:
    """Missing nullable GitHub fields remain absent or null without inference."""
    profile = {"login": "octocat", "name": None, "email": None}
    payload = GitHubFetcher(
        opener=FakeGitHubAPI(github_responses(profile=profile))
    ).fetch("https://github.com/octocat")

    assert payload.profile == profile


def test_github_adapter_converts_payload_to_raw_candidate_record() -> None:
    """GitHubAdapter preserves raw API data in a RawCandidateRecord."""
    payload = GitHubPayload(
        profile={"login": "octocat", "name": "The Octocat"},
        repositories=[repository()],
        languages={"octocat/hello-world": {"Python": 120}},
    )

    record = GitHubAdapter().parse(payload)

    assert isinstance(record, RawCandidateRecord)
    assert record.record_id == "github_octocat"
    assert record.source_type == SourceType.GITHUB.value
    assert record.source_system == "github"
    assert record.source_record_id == "octocat"
    assert record.payload_format == PayloadFormat.API_RESPONSE.value
    assert record.payload["profile"] == payload.profile
    assert record.payload["repositories"] == payload.repositories
    assert record.payload["languages"] == payload.languages
    provenance = cast(dict[str, Any], record.payload["provenance"])
    assert provenance["source"] == "GitHub"
    assert provenance["method"] == "REST API"
    assert record.checksum.startswith("sha256:")


def test_github_adapter_load_returns_constructor_payload() -> None:
    """GitHubAdapter can expose an already fetched payload through the base contract."""
    payload = GitHubPayload(profile={"login": "octocat"})

    assert GitHubAdapter(payload).load() == payload


def test_github_adapter_rejects_missing_login() -> None:
    """Adapter does not fabricate source record IDs from missing profile data."""
    payload = GitHubPayload(profile={"name": "Anonymous"})

    with pytest.raises(AdapterError, match="missing profile login"):
        GitHubAdapter().parse(payload)


def test_github_adapter_rejects_invalid_payload_type() -> None:
    """Adapter accepts only GitHubPayload inputs."""
    with pytest.raises(AdapterError):
        GitHubAdapter().parse({"login": "octocat"})
