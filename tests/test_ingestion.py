import pytest
from app.core.validators import validate_github_url

class TestGitHubUrlSanitization:
    
    @pytest.mark.parametrize("url", [
        "https://github.com/user/repo",
        "https://www.github.com/org-name/repo_name",
        "https://github.com/user123/repo.git",
        "https://github.com/a/b.js"
    ])
    def test_valid_urls(self, url):
        assert validate_github_url(url) is True

    @pytest.mark.parametrize("url", [
        "http://github.com/user/repo",  # Non-HTTPS
        "git@github.com:user/repo.git", # SSH protocol
        "ssh://git@github.com/user/repo", # SSH scheme
        "https://gitlab.com/user/repo", # Not GitHub
        "https://github.com/user/repo;rm -rf /", # Command injection semi-colon
        "https://github.com/user/repo|whoami", # Command injection pipe
        "https://github.com/user/`whoami`", # Sub-shell backtick
        "https://github.com/user/repo$(id)", # Sub-shell execution
        "https://github.com/user/repo&echo 1", # Background execution
        "http://169.254.169.254/latest/meta-data/", # SSRF attempt AWS
        "https://github.com/user/repo?token=123", # Query params not allowed
        "https://github.com/user/repo#123", # Fragments not allowed
        "ftp://github.com/user/repo", # FTP scheme
        "file:///etc/passwd", # Local file inclusion
        "", # Empty string
        "None" # String None
    ])
    def test_invalid_and_poisoned_urls(self, url):
        assert validate_github_url(url) is False
