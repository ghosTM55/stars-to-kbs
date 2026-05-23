"""Configuration loading for stars-to-kbs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

DEFAULT_NOTE_NAME = "GitHub Stars Index.md"
APP_CONFIG_DIR = "stars-to-kbs"
SUPPORTED_AGENT_NAMES = {"codex", "claude", "hermes", "none"}


def default_config_path() -> Path:
    """Return the default per-user config file path under $HOME/.config."""
    return Path.home() / ".config" / APP_CONFIG_DIR / "config.toml"


def resolve_kbs_note_path(path_value: str | Path) -> Path:
    """Resolve a configured KBS path to the final Markdown note path."""
    path = Path(path_value).expanduser()
    if path.suffix.lower() == ".md":
        return path
    return path / DEFAULT_NOTE_NAME


def _section(data: dict[str, Any], name: str, allowed: set[str]) -> dict[str, Any]:
    section_data = data.get(name, {})
    if not isinstance(section_data, dict):
        raise ValueError(f"Config section [{name}] must be a table")
    unknown = sorted(set(section_data) - allowed)
    if unknown:
        raise ValueError(f"Unknown config key(s) in [{name}]: {', '.join(unknown)}")
    return section_data


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
    timeout_seconds: int = 900


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
        config = cls(GitHubConfig(), AgentConfig(), KbsConfig(), OutputConfig())
        config.validate()
        return config

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        config_path = Path(path) if path is not None else default_config_path()
        data: dict[str, Any] = {}
        if config_path.exists():
            data = tomllib.loads(config_path.read_text())

        top_unknown = sorted(set(data) - {"github", "agent", "kbs", "output"})
        if top_unknown:
            raise ValueError(f"Unknown config section(s): {', '.join(top_unknown)}")

        github_data = _section(data, "github", set(GitHubConfig.__dataclass_fields__))
        agent_data = _section(data, "agent", set(AgentConfig.__dataclass_fields__))
        kbs_data = _section(data, "kbs", set(KbsConfig.__dataclass_fields__))
        output_data = _section(data, "output", {"cache_dir", "work_dir"})

        config = cls(
            github=GitHubConfig(**github_data),
            agent=AgentConfig(**agent_data),
            kbs=KbsConfig(**kbs_data),
            output=OutputConfig(
                cache_dir=Path(output_data.get("cache_dir", ".cache")),
                work_dir=Path(output_data.get("work_dir", ".work")),
            ),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.github.max_repos < 0:
            raise ValueError("github.max_repos must be >= 0")
        if self.agent.batch_size <= 0:
            raise ValueError("agent.batch_size must be > 0")
        if self.agent.timeout_seconds <= 0:
            raise ValueError("agent.timeout_seconds must be > 0")
        provider = self.agent.provider.lower()
        if provider not in SUPPORTED_AGENT_NAMES:
            raise ValueError(f"agent.provider must be one of: {', '.join(sorted(SUPPORTED_AGENT_NAMES))}")
        self.agent.provider = provider
