"""Data models for stars-to-kbs."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Repository:
    full_name: str
    html_url: str
    description: str = ""
    language: str = ""
    topics: list[str] = field(default_factory=list)
    stars: int = 0
    forks: int = 0
    starred_at: str = ""
    updated_at: str = ""
    archived: bool = False
    readme_excerpt: str = ""

    @classmethod
    def from_github_star(cls, item: dict[str, Any]) -> "Repository":
        """Build a Repository from GitHub's star+json response shape."""
        repo = item.get("repo", item)
        return cls(
            full_name=repo["full_name"],
            html_url=repo.get("html_url") or f"https://github.com/{repo['full_name']}",
            description=repo.get("description") or "",
            language=repo.get("language") or "",
            topics=list(repo.get("topics") or []),
            stars=int(repo.get("stargazers_count") or 0),
            forks=int(repo.get("forks_count") or 0),
            starred_at=item.get("starred_at", ""),
            updated_at=repo.get("updated_at", ""),
            archived=bool(repo.get("archived", False)),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Repository":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in allowed})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StarsSummary:
    generated_at: datetime
    github_user: str
    agent_provider: str
    total_repos: int
    body: str

    @classmethod
    def now(cls, github_user: str, agent_provider: str, total_repos: int, body: str) -> "StarsSummary":
        return cls(
            generated_at=datetime.now(timezone.utc),
            github_user=github_user,
            agent_provider=agent_provider,
            total_repos=total_repos,
            body=body,
        )
