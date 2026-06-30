"""Infrastructure fetcher for public GitHub profile data."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request

from src.detection.detector import GITHUB_RESERVED_PATHS
from src.github.exceptions import (
    GitHubAPIException,
    GitHubNetworkException,
    GitHubRateLimitException,
    GitHubTimeoutException,
    GitHubUserNotFoundException,
    InvalidGitHubURLException,
)
from src.github.models import GitHubPayload
from src.models.base import JsonValue

GitHubResponse = dict[str, JsonValue] | list[dict[str, JsonValue]]
UrlOpener = Callable[[Request, float], Any]


def default_urlopen(request: Request, timeout_seconds: float) -> Any:
    """Open a URL request with timeout while bypassing system proxies."""
    import urllib.request

    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    return opener.open(request, timeout=timeout_seconds)


class GitHubFetcher:
    """Fetch raw public GitHub profile, repository, and language data."""

    api_base_url = "https://api.github.com"

    def __init__(self, opener: UrlOpener | None = None, timeout_seconds: float = 10.0):
        """Initialize the fetcher with an optional test HTTP opener."""
        self._opener = opener or default_urlopen
        self._timeout_seconds = timeout_seconds
        self._token = self._resolve_token()

    def fetch(self, profile_url: str) -> GitHubPayload:
        """Fetch a public GitHub profile and associated repository metadata."""
        username = self._username_from_profile_url(profile_url)
        profile = self._get_object(f"/users/{username}")
        if not profile:
            raise GitHubAPIException("GitHub profile is empty")
        repositories = self._get_list(f"/users/{username}/repos")
        languages: dict[str, dict[str, int]] = {}
        for repository in repositories:
            full_name = repository.get("full_name")
            if isinstance(full_name, str) and full_name:
                try:
                    languages[full_name] = self._get_language_map(
                        f"/repos/{full_name}/languages"
                    )
                except GitHubRateLimitException:
                    # Keep profile/repository data already fetched before the limit.
                    break
        return GitHubPayload(
            profile=profile,
            repositories=repositories,
            languages=languages,
        )

    def _username_from_profile_url(self, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            raise InvalidGitHubURLException(
                "GitHubFetcher requires an HTTPS github.com profile URL"
            )
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) != 1:
            raise InvalidGitHubURLException("GitHubFetcher only supports profile URLs")
        username = path_parts[0]
        if username.lower() in GITHUB_RESERVED_PATHS or username.startswith("."):
            raise InvalidGitHubURLException(
                "GitHubFetcher only supports user profile URLs"
            )
        return username

    def _get_object(self, path: str) -> dict[str, JsonValue]:
        response = self._get_json(path)
        if not isinstance(response, dict):
            raise GitHubAPIException("GitHub API returned an unexpected object shape")
        return response

    def _get_list(self, path: str) -> list[dict[str, JsonValue]]:
        response = self._get_json(path)
        if not isinstance(response, list):
            raise GitHubAPIException("GitHub API returned an unexpected list shape")
        return response

    def _get_language_map(self, path: str) -> dict[str, int]:
        response = self._get_json(path)
        if not isinstance(response, dict):
            raise GitHubAPIException("GitHub API returned an unexpected language shape")
        languages: dict[str, int] = {}
        for key, value in response.items():
            if isinstance(key, str) and isinstance(value, int):
                languages[key] = value
        return languages

    def _get_json(self, path: str) -> GitHubResponse:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "candidate-transformer",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"

        request = Request(
            f"{self.api_base_url}{path}",
            headers=headers,
        )
        try:
            with self._opener(request, self._timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code == 404:
                raise GitHubUserNotFoundException(
                    "GitHub profile was not found"
                ) from exc
            if exc.code in {403, 429}:
                raise GitHubRateLimitException(
                    "GitHub API rate limit was reached. "
                    f"You may need to wait or authenticate. ({exc.reason})"
                ) from exc
            raise GitHubAPIException(
                f"GitHub API request failed ({exc.code}): {exc.reason}"
            ) from exc
        except URLError as exc:
            if (
                isinstance(exc.reason, TimeoutError)
                or "timed out" in str(exc.reason).lower()
            ):
                raise GitHubTimeoutException(
                    f"GitHub API network request timed out: {exc.reason}"
                ) from exc
            raise GitHubNetworkException(
                f"GitHub API network request failed: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise GitHubTimeoutException(
                f"GitHub API network request timed out: {exc}"
            ) from exc
        except OSError as exc:
            raise GitHubNetworkException(
                f"GitHub API response could not be read: {exc}"
            ) from exc
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise GitHubAPIException("GitHub API returned malformed JSON") from exc
        if not isinstance(parsed, (dict, list)):
            raise GitHubAPIException("GitHub API returned an unsupported JSON shape")
        return parsed

    def _resolve_token(self) -> str | None:
        token = os.getenv("GITHUB_TOKEN")
        if token is not None and token.strip():
            return token.strip()
        env_token = self._token_from_env_file()
        if env_token is not None and env_token.strip():
            return env_token.strip()
        return None

    def _token_from_env_file(self) -> str | None:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if not env_file.exists():
            return None
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "GITHUB_TOKEN":
                return value.strip().strip('"').strip("'")
        return None
