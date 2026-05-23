"""Markdown rendering and prompt construction."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import timezone

from .models import Repository, StarsSummary


def render_prompt_payload(repos: list[Repository], language: str = "zh-CN") -> str:
    """Create a compact prompt asking the selected AI CLI for Markdown output."""
    repo_payload = [repo.to_dict() for repo in repos]
    return f"""你是一个帮助整理个人 Knowledge Base 的技术研究助理。请使用 {language} 输出。

任务：根据下面 GitHub starred repositories 的元数据，把这些项目归纳为有用的分类，并为每个项目写简短笔记。

输出要求：
- 只输出 Markdown，不要输出解释性前言。
- 使用二级标题 `## 分类目录` 开始。
- 每个分类用三级标题，例如 `### AI / Agents`。
- 每个项目用四级标题 `#### owner/repo`。
- 每个项目包含：GitHub 链接、语言、stars、starred_at、一句话总结、为什么值得关注、适合用途、标签。
- 不要编造仓库不存在的信息；如果元数据不足，请明确写“信息不足”。

Repositories JSON:
```json
{json.dumps(repo_payload, ensure_ascii=False, indent=2)}
```
"""


def render_kbs_note(summary: StarsSummary) -> str:
    generated = summary.generated_at.astimezone(timezone.utc).isoformat()
    body = summary.body.strip()
    return f"""---
title: GitHub Stars Index
type: github-stars-index
generated_at: {generated}
source: github-stars
agent: {summary.agent_provider}
github_user: {summary.github_user}
total_repos: {summary.total_repos}
---

# GitHub Stars Index

> 自动生成：GitHub Stars → {summary.agent_provider} → KBS。<br>
> Generated at: {generated}

## 概览

- GitHub user: `{summary.github_user}`
- Repositories processed: **{summary.total_repos}**
- Agent: `{summary.agent_provider}`

{body}
"""


def render_fallback_summary(repos: list[Repository]) -> str:
    """Deterministic no-AI grouping for smoke tests or offline runs."""
    groups: dict[str, list[Repository]] = defaultdict(list)
    for repo in repos:
        key = repo.language or (repo.topics[0] if repo.topics else "未分类")
        groups[key].append(repo)

    lines = ["## 分类目录", ""]
    if not repos:
        lines += ["### 未分类", "", "暂无仓库数据。", ""]
        return "\n".join(lines)

    for category, items in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0].lower())):
        lines += [f"### {category}", ""]
        for repo in sorted(items, key=lambda r: r.stars, reverse=True):
            desc = repo.description or "信息不足"
            tags = ", ".join(repo.topics[:6]) if repo.topics else "信息不足"
            lines += [
                f"#### {repo.full_name}",
                f"- GitHub: {repo.html_url}",
                f"- Language: {repo.language or '信息不足'}",
                f"- Stars: {repo.stars:,}",
                f"- Starred at: {repo.starred_at or '信息不足'}",
                f"- 一句话总结：{desc}",
                "- 为什么值得关注：需要 AI 进一步归纳；当前为无 AI fallback 输出。",
                "- 适合用途：待人工确认。",
                f"- 标签：{tags}",
                "",
            ]
    return "\n".join(lines)
