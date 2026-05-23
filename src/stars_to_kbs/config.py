"""Configuration loading for stars-to-kbs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

DEFAULT_NOTE_NAME = "GitHub Stars Index.md"
APP_CONFIG_DIR = "stars-to-kbs"


def default_config_path() -> Path:
    """Return the default per-user config file path under $HOME/.config."""
    return Path.home() / ".config" / APP_CONFIG_DIR / "config.toml"


def resolve_kbs_note_path(path_value: str | Path) -> Path:
    """Resolve a configured KBS path to the final Markdown note path."""
    path = Path(path_value).expanduser()
    if path.suffix.lower() == ".md":
        return path
    return path / DEFAULT_NOTE_NAME


@dataclass(slots=True)
class GitHubConfig:
    username: str = ""
    token_env: str = "GH_TOKEN"
    include_readme: bool = False
    max_repos: int = 0


@dataclass(slots=True)
class AgentConfig:
    provider: str = "codex"
    batch_size: int = 20
    language: str = "zh-CN"


@dataclass(slots=True)
class KbsConfig:
    path: str = "output"

    @property
    def note_path(self) -> Path:
        return resolve_kbs_note_path(self.path)


@dataclass(slots=True)
class OutputConfig:
    cache_dir: Path = Path(".cache")
    work_dir: Path = Path(".work")


@dataclass(slots=True)
class Config:
    github: GitHubConfig
    agent: AgentConfig
    kbs: KbsConfig
    output: OutputConfig

    @classmethod
    def default(cls) -> "Config":
        return cls(GitHubConfig(), AgentConfig(), KbsConfig(), OutputConfig())

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        config_path = Path(path) if path is not None else default_config_path()
        data: dict = {}
        if config_path.exists():
            data = tomllib.loads(config_path.read_text())

        github_data = data.get("github", {})
        agent_data = data.get("agent", {})
        kbs_data = data.get("kbs", {})
        output_data = data.get("output", {})

        return cls(
            github=GitHubConfig(**{k: v for k, v in github_data.items() if k in GitHubConfig.__dataclass_fields__}),
            agent=AgentConfig(**{k: v for k, v in agent_data.items() if k in AgentConfig.__dataclass_fields__}),
            kbs=KbsConfig(**{k: v for k, v in kbs_data.items() if k in KbsConfig.__dataclass_fields__}),
            output=OutputConfig(
                cache_dir=Path(output_data.get("cache_dir", ".cache")),
                work_dir=Path(output_data.get("work_dir", ".work")),
            ),
        )
