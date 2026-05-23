# stars-to-kbs

Local-first GitHub Stars organizer for a personal Knowledge Base System (KBS).

`stars-to-kbs` fetches your GitHub starred repositories, asks a configurable AI CLI (`hermes`, `codex`, or `claude`) to organize and summarize them, then writes an Obsidian-friendly Markdown note to your configured KBS path.

> 中文说明：see [README.zh-CN.md](README.zh-CN.md).

## Why this exists

This project is inspired by [`amirhmoradi/starred`](https://github.com/amirhmoradi/starred), but takes a different approach:

- It does **not** call OpenAI, Anthropic, or other LLM provider APIs directly.
- It shells out to already-authenticated local AI CLIs instead.
- It keeps private configuration outside the repository.
- It writes a single Markdown note that can be dropped into Obsidian or another personal KBS.

This is useful when you already pay for tools such as Codex, Claude, or Hermes and want to avoid maintaining separate API keys or API-billed summarization pipelines.

## Current status and scale behavior

The pipeline is now designed for larger star collections by separating batch summarization from global consolidation:

```text
fetch -> summarize-batches -> merge-summaries -> validate -> write-note
```

Repositories are first summarized in batches controlled by `batch_size`. The `merge` stage then asks the selected AI CLI to consolidate all batch outputs into one global taxonomy, and the `validate` stage checks that every fetched `full_name` appears exactly once in the final Markdown.

Recommended large-collection settings:

```toml
[agent]
batch_size = 50
language = "zh-CN"

[github]
include_readme = false
max_repos = 0
```

For 400+ or 1000+ repositories, this is much better than simple batch concatenation, but the final quality still depends on the selected AI CLI's context window and output reliability. If validation fails, inspect `.work/combined-summary.md`, lower `batch_size`, or rerun with `--resume` after fixing the failed batch.

## Privacy and security model

Committed files are intended to be safe for a public repository. Private material should stay outside git.

The default private config path is:

```text
$HOME/.config/stars-to-kbs/config.toml
```

Ignored local files include:

- `.env` — optional local secrets;
- `config.toml` and `*.local.toml` — local config copies;
- `.cache/` — fetched GitHub star data;
- `.work/` — prompts and AI CLI outputs;
- `output/` and `agent-output/` — generated local notes or artifacts;
- `.venv/`, `dist/`, test/lint caches.

Important privacy notes:

- GitHub tokens are read from the configured environment variable or from `gh auth token`.
- This project does not store LLM provider API keys.
- Using `hermes`, `codex`, or `claude` may still send repository metadata to that tool's backend according to that tool's own account, privacy, and retention settings.
- Setting `include_readme = true` sends more repository text to the selected agent and makes runs slower.
- Do not commit generated cache/work/output files if your stars reveal private research interests.

## Requirements

- Python `>= 3.11`
- GitHub access via one of:
  - `GH_TOKEN` or another configured token environment variable; or
  - the GitHub CLI (`gh`) already authenticated with `gh auth login`
- Optional AI CLI provider:
  - `hermes`
  - `codex`
  - `claude`

The `none` provider requires no AI CLI and is useful for smoke tests.

## Installation

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/ghosTM55/stars-to-kbs.git
cd stars-to-kbs
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Verify the CLI is available:

```bash
stars-to-kbs --help
```

If you use `gh` instead of a token environment variable, verify GitHub auth:

```bash
gh auth status
```

## Configuration

Create a private config file:

```bash
stars-to-kbs init
```

By default this writes:

```text
$HOME/.config/stars-to-kbs/config.toml
```

Edit that file before running the full pipeline.

Example:

```toml
[github]
username = "YOUR_GITHUB_USERNAME"
token_env = "GH_TOKEN"
include_readme = false
max_repos = 0

[agent]
provider = "hermes"
batch_size = 50
language = "zh-CN"

[kbs]
path = "/absolute/path/to/your/Obsidian/Personal Notes"

[output]
cache_dir = ".cache"
work_dir = ".work"
```

### Config reference

| Key | Meaning |
| --- | --- |
| `github.username` | GitHub user whose authenticated stars should be fetched. If empty, the authenticated user is detected. |
| `github.token_env` | Environment variable containing a GitHub token. Defaults to `GH_TOKEN`. |
| `github.include_readme` | Fetch README excerpts for each repo. Better summaries, but slower and more data sent to the agent. |
| `github.max_repos` | Maximum repositories to fetch. `0` means all stars. Useful for tests. |
| `agent.provider` | One of `hermes`, `codex`, `claude`, or `none`. |
| `agent.batch_size` | Number of repositories per AI summarization batch. Use smaller values for stability. |
| `agent.language` | Output language requested in the AI prompt. |
| `kbs.path` | Absolute path to a directory or final Markdown file. If it is a directory, `GitHub Stars Index.md` is created inside it. |
| `output.cache_dir` | Local cache directory for fetched stars. Ignored by git. |
| `output.work_dir` | Local work directory for prompts and agent outputs. Ignored by git. |

You can override the config path:

```bash
stars-to-kbs --config /path/to/config.toml run
```

## Quick start

Run a small test first:

```bash
stars-to-kbs run --agent none --max-repos 20
```

Then run with your preferred AI CLI:

```bash
stars-to-kbs run --agent hermes --max-repos 20
```

If the output looks right, run the full collection:

```bash
stars-to-kbs run --agent hermes
```

## Commands

```bash
stars-to-kbs init
stars-to-kbs fetch
stars-to-kbs summarize --agent hermes
stars-to-kbs merge --agent hermes
stars-to-kbs validate
stars-to-kbs write-note
stars-to-kbs run --agent hermes
```

### `init`

Creates a private config file from `config.example.toml`.

```bash
stars-to-kbs init
stars-to-kbs init --force
```

### `fetch`

Fetches GitHub starred repositories and writes them to the cache.

```bash
stars-to-kbs fetch
stars-to-kbs fetch --max-repos 50
stars-to-kbs fetch --with-readme
```

### `summarize`

Reads cached repositories, splits them by `batch_size`, and calls the selected AI CLI.

```bash
stars-to-kbs summarize --agent hermes
stars-to-kbs summarize --agent codex --batch-size 50
stars-to-kbs summarize --agent none
```

Current output:

```text
.work/batch-summaries.md
```

Use `--resume` to reuse existing non-empty `.work/batch-XXX.summary.md` files.

### `merge`

Merges batch summaries into one global taxonomy and writes the final summary.

```bash
stars-to-kbs merge --agent hermes
stars-to-kbs merge --agent codex --resume
```

Current output:

```text
.work/combined-summary.md
```

### `validate`

Checks that every fetched repository appears exactly once as a `#### owner/repo` heading in the merged summary.

```bash
stars-to-kbs validate
```

### `write-note`

Writes the validated merged summary to the configured KBS note path.

```bash
stars-to-kbs write-note
```

### `run`

Runs `fetch`, `summarize`, `merge`, `validate`, and `write-note` in sequence.

```bash
stars-to-kbs run --agent hermes
stars-to-kbs run --agent none --max-repos 20
```

## Agent providers

| Provider | Command pattern | Notes |
| --- | --- | --- |
| `hermes` | `hermes chat -Q -q <prompt>` | Uses Hermes quiet mode and captures stdout. |
| `codex` | `codex exec --skip-git-repo-check -o <file> <prompt>` | Writes output to a file when supported. |
| `claude` | `claude -p <prompt>` | Captures stdout. |
| `none` | No subprocess | Deterministic fallback grouping for tests/offline smoke runs. |

The project assumes these CLIs are already installed and authenticated. It does not install or configure them for you.

## Output format

The generated note includes frontmatter and a body like:

```markdown
---
title: GitHub Stars Index
type: github-stars-index
...
---

# GitHub Stars Index

## 概览

## 分类目录

### AI / Agents

#### owner/repo
- GitHub 链接：https://github.com/owner/repo
- stars：12345
- 一句话总结：...
- 为什么值得关注：...
- 适合用途：...
```

The intended per-repository fields are:

- GitHub link;
- stars;
- one-sentence summary;
- why it is worth watching;
- suitable use cases.

The prompt asks agents not to include language, `starred_at`, or tags in each item.

## Large star collections

GitHub stars are fetched with API pagination (`100` repositories per page). Summarization is batched locally according to `batch_size`.

Guidance:

- Start with `--max-repos 20` to verify config and output path.
- Use `include_readme = false` for large collections unless you really need README context.
- Prefer `batch_size = 50` to `100` for more stable output from CLI agents.
- Use `--resume` to reuse existing non-empty batch or merged outputs after a failed run.
- If a batch fails, inspect `.work/batch-XXX.prompt.md` and `.work/batch-XXX.summary.md`.
- If validation fails, inspect `.work/combined-summary.md`; the validator prints missing, extra, and duplicate repo headings.

## Troubleshooting

### `Config already exists`

`stars-to-kbs init` does not overwrite an existing config unless you pass:

```bash
stars-to-kbs init --force
```

### GitHub authentication fails

Set a token:

```bash
export GH_TOKEN=...
```

Or authenticate `gh`:

```bash
gh auth login
gh auth status
```

### Agent command not found

Install and authenticate the selected CLI, or run a smoke test without AI:

```bash
stars-to-kbs run --agent none --max-repos 20
```

### Validation fails for many stars

The final `validate` step compares fetched repository `full_name` values with `#### owner/repo` headings in `.work/combined-summary.md`. If it reports missing, duplicate, or unexpected repositories, rerun the merge step, lower `batch_size`, or inspect the merged file manually:

```bash
stars-to-kbs merge --agent hermes
stars-to-kbs validate
```

### Generated note went to the wrong place

Check:

```toml
[kbs]
path = "/absolute/path/to/your/notes"
```

If `path` points to a directory, the file will be:

```text
GitHub Stars Index.md
```

inside that directory.

## Development

Install dev dependencies:

```bash
pip install -e '.[dev]'
```

Run tests and lint:

```bash
python -m pytest -q
ruff check .
```

Build:

```bash
python -m build
```

Before publishing changes, verify that no private data is included:

```bash
git status --short
git diff --cached
```

## Roadmap

High-priority improvements:

- Add hierarchical merge for very large collections when the final merge prompt becomes too large.
- Improve agent prompt-size estimation and automatic batch-size recommendations.
- Add richer retry/backoff behavior for transient GitHub/API/network failures.
- Add optional filters such as archived repositories, forks, and minimum star count.
- Package and publish releases for easier installation.

## License

MIT
