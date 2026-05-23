from stars_to_kbs.models import Repository
from stars_to_kbs.validation import extract_repo_headings, validate_summary


def repo(name: str) -> Repository:
    return Repository(full_name=name, html_url=f"https://github.com/{name}")


def test_extract_repo_headings():
    body = """
## 分类目录

### Tools

#### owner/repo
- GitHub 链接：https://github.com/owner/repo

#### other/project
- GitHub 链接：https://github.com/other/project
"""
    assert extract_repo_headings(body) == ["owner/repo", "other/project"]


def test_validate_summary_passes_when_every_repo_once():
    result = validate_summary(
        [repo("owner/repo"), repo("other/project")],
        "#### owner/repo\n\n#### other/project\n",
    )
    assert result.passed


def test_validate_summary_reports_missing_extra_and_duplicates():
    result = validate_summary(
        [repo("owner/repo"), repo("missing/repo")],
        "#### owner/repo\n\n#### owner/repo\n\n#### extra/repo\n",
    )
    assert not result.passed
    assert result.missing == ["missing/repo"]
    assert result.extra == ["extra/repo"]
    assert result.duplicates == ["owner/repo"]
