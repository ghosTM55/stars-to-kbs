from stars_to_kbs.cli import main
from stars_to_kbs.models import Repository


class DummyGitHubClient:
    def authenticated_user(self) -> str:
        return "alice"

    def fetch_starred(self, max_repos: int = 0, include_readme: bool = False) -> list[Repository]:
        repos = [
            Repository(full_name="owner/repo1", html_url="https://github.com/owner/repo1", description="One", stars=1),
            Repository(full_name="owner/repo2", html_url="https://github.com/owner/repo2", description="Two", stars=2),
        ]
        return repos[:max_repos] if max_repos else repos


def test_run_pipeline_with_none_agent(monkeypatch, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(f"""
[github]
username = "alice"

[agent]
provider = "none"
batch_size = 1
language = "zh-CN"

[kbs]
path = "{tmp_path / 'kbs'}"

[output]
cache_dir = "{tmp_path / 'cache'}"
work_dir = "{tmp_path / 'work'}"
""".strip())

    monkeypatch.setattr(
        "stars_to_kbs.cli.GitHubStarsClient.from_env_or_gh",
        classmethod(lambda cls, token_env="GH_TOKEN", username="": DummyGitHubClient()),
    )

    code = main(["--config", str(config), "run", "--agent", "none", "--max-repos", "2", "--batch-size", "1"])
    assert code == 0
    note = tmp_path / "kbs" / "GitHub Stars Index.md"
    text = note.read_text()
    assert "#### owner/repo1" in text
    assert "#### owner/repo2" in text
    assert (tmp_path / "work" / "batch-summaries.md").exists()
    assert (tmp_path / "work" / "combined-summary.md").exists()
