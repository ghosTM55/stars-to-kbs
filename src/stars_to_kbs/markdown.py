"""Markdown rendering and prompt construction."""

from __future__ import annotations

from collections import defaultdict
from datetime import timezone
import json

from .models import Repository, StarsSummary


def render_prompt_payload(repos: list[Repository], language: str = "zh-CN") -> str:
    """Create a compact prompt asking the selected AI CLI for one batch of Markdown output."""
    repo_payload = [repo.to_dict() for repo in repos]
    return f"""你是一个帮助整理个人 Knowledge Base 的技术研究助理。请使用 {language} 输出。

任务：根据下面 GitHub starred repositories 的元数据，把这些项目归纳为有用的分类，并为每个项目写简短笔记。

输出要求：
- 只输出 Markdown，不要输出解释性前言。
- 使用二级标题 `## 分类目录` 开始。
- 每个分类用三级标题，例如 `### AI / Agents`。
- 每个项目用四级标题 `#### owner/repo`。
- 四级标题中的 `owner/repo` 必须逐字使用 JSON 里的 `full_name`，不要修正、翻译、缩写或猜测仓库名。
- 每个项目只包含：GitHub 链接、stars、一句话总结、为什么值得关注、适合用途。
- 不要在每个项目条目里输出语言、starred_at 或标签信息。
- 不要编造仓库不存在的信息；如果元数据不足，请明确写“信息不足”。

Repositories JSON:
```json
{json.dumps(repo_payload, ensure_ascii=False, indent=2)}
```
"""


def render_merge_prompt_payload(batch_summaries: list[str], repos: list[Repository], language: str = "zh-CN") -> str:
    """Create a prompt that merges batch summaries into one global taxonomy."""
    expected_names = [repo.full_name for repo in repos]
    summaries = []
    for index, summary in enumerate(batch_summaries, start=1):
        summaries.append(f"### Batch {index}\n\n{summary.strip()}")
    summaries_text = "\n\n---\n\n".join(summaries)
    return f"""你是一个帮助整理个人 Knowledge Base 的技术研究助理。请使用 {language} 输出。

任务：下面是多个 batch 生成的 GitHub Stars 分类笔记。请把它们合并成一个全局统一的分类目录。

全局合并要求：
- 只输出 Markdown，不要输出解释性前言。
- 只保留一个二级标题 `## 分类目录`。
- 合并重复或相近分类，形成统一 taxonomy。
- 同类项目必须放到同一个三级分类下，不要因为 batch 来源不同而拆散。
- 每个项目用四级标题 `#### owner/repo`。
- 四级标题中的 `owner/repo` 必须逐字使用 Expected repository full_name list 中的名字，不要修正、翻译、缩写或猜测仓库名。
- 每个 expected repository 必须且只能出现一次。
- 不要加入 expected list 之外的仓库。
- 每个项目只包含：GitHub 链接、stars、一句话总结、为什么值得关注、适合用途。
- 不要在每个项目条目里输出语言、starred_at 或标签信息。
- 如果原 batch 信息不足，请保留项目并写“信息不足”，不要删除。

Expected repository full_name list:
```json
{json.dumps(expected_names, ensure_ascii=False, indent=2)}
```

Batch summaries:

{summaries_text}
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
            lines += [
                f"#### {repo.full_name}",
                f"- GitHub 链接：{repo.html_url}",
                f"- stars：{repo.stars:,}",
                f"- 一句话总结：{desc}",
                "- 为什么值得关注：需要 AI 进一步归纳；当前为无 AI fallback 输出。",
                "- 适合用途：待人工确认。",
                "",
            ]
    return "\n".join(lines)
