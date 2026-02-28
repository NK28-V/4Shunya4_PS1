import re

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
