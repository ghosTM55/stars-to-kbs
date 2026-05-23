from datetime import datetime, timezone

from stars_to_kbs.markdown import render_fallback_summary, render_kbs_note, render_prompt_payload
from stars_to_kbs.models import Repository, StarsSummary


def sample_repo() -> Repository:
    return Repository(
        full_name="owner/repo",
        html_url="https://github.com/owner/repo",
        description="A useful tool",
        language="Python",
        topics=["cli", "automation"],
        stars=123,
        forks=4,
        starred_at="2026-01-02T03:04:05Z",
        updated_at="2026-01-03T00:00:00Z",
    )


def test_render_prompt_payload_contains_repo_metadata():
    payload = render_prompt_payload([sample_repo()], language="zh-CN")
    assert "owner/repo" in payload
    assert "A useful tool" in payload
    assert "zh-CN" in payload


def test_render_prompt_payload_does_not_request_unwanted_output_fields():
    payload = render_prompt_payload([sample_repo()], language="zh-CN")
    assert "语言、stars、starred_at" not in payload
    assert "标签。" not in payload
    assert "标签信息" in payload
    assert "必须逐字使用 JSON 里的 `full_name`" in payload
    assert "每个项目只包含：GitHub 链接、stars、一句话总结、为什么值得关注、适合用途" in payload


def test_fallback_summary_omits_language_starred_and_tags():
    output = render_fallback_summary([sample_repo()])
    assert "- Language:" not in output
    assert "- Starred at:" not in output
    assert "- 标签：" not in output
    assert "- GitHub:" in output
    assert "- Stars:" in output


def test_render_kbs_note_contains_frontmatter_and_repo_links():
    summary = StarsSummary(
        generated_at=datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc),
        github_user="alice",
        agent_provider="none",
        total_repos=1,
        body="## 分类目录\n\n### CLI Tools\n\n#### owner/repo\n- GitHub: https://github.com/owner/repo\n",
    )
    note = render_kbs_note(summary)
    assert note.startswith("---\n")
    assert "title: GitHub Stars Index" in note
    assert "github_user: alice" in note
    assert "https://github.com/owner/repo" in note
