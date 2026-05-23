from email.message import Message
from urllib.error import HTTPError

from stars_to_kbs.github_api import GitHubStarsClient


def test_has_next_page_parses_link_header():
    link = '<https://api.github.com/user/starred?page=2>; rel="next", <https://api.github.com/user/starred?page=5>; rel="last"'
    assert GitHubStarsClient._has_next_page(link)
    assert not GitHubStarsClient._has_next_page('<https://api.github.com/user/starred?page=5>; rel="last"')


def test_get_json_rate_limit_error(monkeypatch):
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    headers["X-RateLimit-Reset"] = "123"

    def raise_http_error(*_args, **_kwargs):
        raise HTTPError("https://api.github.com/user/starred", 403, "rate limit", headers, None)

    monkeypatch.setattr("stars_to_kbs.github_api.urlopen", raise_http_error)
    client = GitHubStarsClient(token="token")
    try:
        client._get_json("https://api.github.com/user/starred")
    except RuntimeError as exc:
        assert "rate limit" in str(exc).lower()
    else:
        raise AssertionError("expected RuntimeError")
