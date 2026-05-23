# stars-to-kbs

Organize GitHub Stars into a personal knowledge-base Markdown note.

`stars-to-kbs` fetches your starred repositories, sends repository metadata to a local authenticated AI CLI (Hermes / Codex / Claude), merges the generated summaries into one taxonomy, validates repo coverage, and writes an Obsidian-friendly Markdown file.

[中文](README.md)

## Features

- Fetch GitHub Stars with pagination
- Use `hermes`, `codex`, `claude`, or `none`
- No built-in LLM API key integration
- Private config stored outside the repo
- Batch summarization + global merge + validation
- Obsidian-friendly Markdown output

## Install

```bash
git clone https://github.com/ghosTM55/stars-to-kbs.git
cd stars-to-kbs
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Requirements:

- Python `>= 3.11`
- GitHub token, or authenticated `gh` CLI
- Optional AI CLI: `hermes`, `codex`, `claude`

## Configuration

Create local config:

```bash
stars-to-kbs init
```

Default path:

```text
~/.config/stars-to-kbs/config.toml
```

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
path = "/absolute/path/to/your/notes"

[output]
cache_dir = ".cache"
work_dir = ".work"
```

| Key | Description |
| --- | --- |
| `github.username` | GitHub user; empty means authenticated user |
| `github.token_env` | token environment variable, default `GH_TOKEN` |
| `github.include_readme` | fetch README excerpts; slower and sends more text to the AI CLI |
| `github.max_repos` | max repositories; `0` means all |
| `agent.provider` | `hermes` / `codex` / `claude` / `none` |
| `agent.batch_size` | repositories per summarization batch |
| `agent.language` | requested output language |
| `kbs.path` | KBS directory or final Markdown path |

## Usage

Smoke test:

```bash
stars-to-kbs run --agent none --max-repos 20
stars-to-kbs run --agent hermes --max-repos 20
```

Full run:

```bash
stars-to-kbs run --agent hermes
```

Resume from existing batch outputs:

```bash
stars-to-kbs run --agent hermes --resume
```

## Commands

```bash
stars-to-kbs fetch
stars-to-kbs summarize --agent hermes
stars-to-kbs merge --agent hermes
stars-to-kbs validate
stars-to-kbs write-note
```

Pipeline:

```text
fetch -> summarize -> merge -> validate -> write-note
```

Outputs:

| Stage | File |
| --- | --- |
| fetch | `.cache/starred.json` |
| summarize | `.work/batch-summaries.md` |
| merge | `.work/combined-summary.md` |
| write-note | `<kbs.path>/GitHub Stars Index.md` |

## Large star lists

GitHub fetches up to 100 starred repositories per page. Summaries are generated in batches and then merged into a global taxonomy.

Recommended settings:

```toml
[agent]
batch_size = 50

[github]
include_readme = false
```

`validate` checks the final Markdown for:

- missing repositories
- unexpected repositories
- duplicate repositories

## Privacy

The repo ignores local config and generated outputs by default.

Do not commit:

- `.env`
- `config.toml`
- `.cache/`
- `.work/`
- `output/`

Note: this project does not store LLM API keys, but `hermes`, `codex`, or `claude` may still send repository metadata to their own backends.

## Development

```bash
python -m pytest -q
ruff check .
python -m build
```

## License

MIT
