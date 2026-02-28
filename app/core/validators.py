import re
from urllib.parse import urlparse

# Strict regex to allow ONLY https://github.com/org/repo or https://www.github.com/org/repo
# No query params, fragments, sub-shell characters, or alternative schemes (e.g. ssh/git) allowed.
# SSRF: only GitHub HTTPS is permitted; internal IPs, localhost, and other hosts are rejected by pattern.
GITHUB_URL_REGEX = re.compile(
    r"^https:\/\/(www\.)?github\.com\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+(\.git)?$"
)

# Explicit allowlist for SSRF: only these hosts may be used for repository ingestion.
ALLOWED_GITHUB_HOSTS = frozenset(("github.com", "www.github.com"))


def validate_github_url(url: str) -> bool:
    """
    Validates a repository URL strictly against a GitHub HTTPS pattern.
    Prevents SSRF and command injection by restricting to GitHub HTTPS only;
    rejects localhost, internal IPs, and any non-GitHub host.
    """
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not GITHUB_URL_REGEX.match(url):
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().split(":")[0]
        return host in ALLOWED_GITHUB_HOSTS
    except Exception:
        return False
