import re
from urllib.parse import urlparse
import socket
import ipaddress

# Strict regex to allow ONLY https://github.com/org/repo or https://www.github.com/org/repo
# No query params, fragments, sub-shell characters, or alternative schemes like ssh/git allowed.
GITHUB_URL_REGEX = re.compile(
    r"^https:\/\/(www\.)?github\.com\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+(\.git)?$"
)

def validate_github_url(url: str) -> bool:
    """
    Validates a repository URL strictly against a GitHub HTTPS pattern.
    Prevents command injection and limits to GitHub boundaries.
    """
    if not url:
        return False
        
    return bool(GITHUB_URL_REGEX.match(url))


# Hosts allowed for repository ingestion (SSRF allowlist)
ALLOWED_REPO_HOSTS = frozenset(("github.com", "www.github.com"))

# Private/internal IP check for SSRF mitigation
LOCALHOST_NAMES = frozenset(("localhost", "localhost.", "127.0.0.1", "::1", "0.0.0.0"))


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        if addr.is_loopback or addr.is_private or addr.is_link_local:
            return True
        if addr.version == 6 and addr in ipaddress.IPv6Network("::1/128"):
            return True
        return False
    except ValueError:
        return True


def ensure_no_ssrf_host(url: str) -> None:
    """
    Ensures the URL host does not resolve to private/internal IPs (SSRF mitigation).
    Call after validate_github_url(); raises ValueError if the host is disallowed.
    """
    if not url:
        raise ValueError("Empty URL")
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname or hostname in LOCALHOST_NAMES:
        raise ValueError("Invalid or localhost host")
    if hostname not in ALLOWED_REPO_HOSTS:
        raise ValueError("Host not in allowlist")
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None, socket.AF_UNSPEC):
            ip_str = sockaddr[0]
            if _is_private_ip(ip_str):
                raise ValueError("Host resolves to private/internal IP")
    except socket.gaierror:
        raise ValueError("Host resolution failed")
