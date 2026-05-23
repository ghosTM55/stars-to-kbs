# stars-to-kbs

Local-first GitHub Stars organizer for a personal KBS.

It fetches your GitHub starred repositories, asks a configurable local AI CLI (`codex`, `claude`, or `hermes`) to organize and summarize them, then writes an Obsidian-friendly Markdown note to a configurable KBS path.

## Why this exists

This project is inspired by [`amirhmoradi/starred`](https://github.com/amirhmoradi/starred), but differs in one important way: it does **not** call LLM provider APIs directly. Instead, it shells out to already-authenticated AI CLI tools so you can reuse subscription-based tooling when available.

## Privacy model

Committed files are safe for a public repository. Private material is ignored by git:

- `config.toml` for your local paths and preferences
- `.env` for tokens
- `.cache/` for fetched GitHub stars
- `.work/` for prompts and agent outputs
- `output/` for generated local notes

Important: using `codex`, `claude`, or `hermes` still sends selected repository metadata to that tool's backend according to that tool's own privacy/account settings. This project avoids direct API-key billing; it does not make AI processing fully local.

## Quick start

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp config.example.toml config.toml
# edit config.toml
stars-to-kbs run --agent hermes --max-repos 20
```

If `GH_TOKEN` is not set, the tool tries `gh auth token`.

## Commands

```bash
stars-to-kbs init
stars-to-kbs fetch
stars-to-kbs summarize --agent hermes
stars-to-kbs write-note
stars-to-kbs run --agent hermes --max-repos 20
```

## Agent providers

- `hermes`: `hermes chat -q <prompt>`
- `codex`: `codex exec --skip-git-repo-check -o <file> <prompt>`
- `claude`: `claude -p <prompt>`
- `none`: deterministic fallback grouping without AI, useful for testing

## License

MIT
