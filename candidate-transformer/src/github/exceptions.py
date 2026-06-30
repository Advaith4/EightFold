"""GitHub integration specific exceptions."""

from src.exceptions import AdapterError


class GitHubAPIException(AdapterError):
    """Base exception for GitHub API failures."""


class InvalidGitHubURLException(GitHubAPIException):
    """Raised when a provided GitHub URL is malformed or invalid."""


class GitHubUserNotFoundException(GitHubAPIException):
    """Raised when a GitHub profile cannot be found (404)."""


class GitHubRateLimitException(GitHubAPIException):
    """Raised when the GitHub API rate limit is reached (403, 429)."""


class GitHubTimeoutException(GitHubAPIException):
    """Raised when a request to the GitHub API times out."""


class GitHubNetworkException(GitHubAPIException):
    """Raised when a low-level network failure occurs connecting to GitHub."""
