"""CLI for stars-to-kbs."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .agent_runner import AgentRunner, SUPPORTED_AGENTS
from .config import Config, default_config_path
from .github_api import GitHubStarsClient, load_repos, save_repos
from .markdown import render_kbs_note, render_prompt_payload
from .models import StarsSummary


def cache_path(config: Config) -> Path:
    return config.output.cache_dir / "starred.json"


def summary_path(config: Config) -> Path:
    return config.output.work_dir / "combined-summary.md"


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.config)
    if target.exists() and not args.force:
        print(f"Config already exists: {target}")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile("config.example.toml", target)
    print(f"Created {target}. Edit it before running.")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    max_repos = args.max_repos if args.max_repos is not None else config.github.max_repos
    include_readme = args.with_readme if args.with_readme is not None else config.github.include_readme
    client = GitHubStarsClient.from_env_or_gh(config.github.token_env, config.github.username)
    user = client.authenticated_user()
    repos = client.fetch_starred(max_repos=max_repos, include_readme=include_readme)
    path = save_repos(cache_path(config), repos)
    print(f"Fetched {len(repos)} starred repositories for {user} -> {path}")
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    repos = load_repos(args.input or cache_path(config))
    provider = args.agent or config.agent.provider
    batch_size = args.batch_size or config.agent.batch_size
    runner = AgentRunner(provider, config.output.work_dir)

    outputs: list[str] = []
    for start in range(0, len(repos), batch_size):
        batch = repos[start:start + batch_size]
        batch_name = f"batch-{start // batch_size + 1:03d}"
        prompt = render_prompt_payload(batch, config.agent.language)
        outputs.append(runner.summarize(prompt, batch_name, batch))

    combined = "\n\n".join(output.strip() for output in outputs if output.strip())
    out = summary_path(config)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(combined)
    print(f"Wrote combined summary -> {out}")
    return 0


def cmd_write_note(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    repos = load_repos(args.input or cache_path(config))
    body = Path(args.summary or summary_path(config)).read_text()
    client = GitHubStarsClient.from_env_or_gh(config.github.token_env, config.github.username)
    user = config.github.username or client.authenticated_user()
    provider = args.agent or config.agent.provider
    summary = StarsSummary.now(user, provider, len(repos), body)
    note = render_kbs_note(summary)
    note_path = config.kbs.note_path
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(note)
    print(f"Wrote KBS note -> {note_path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    fetch_args = argparse.Namespace(config=args.config, max_repos=args.max_repos, with_readme=args.with_readme)
    summarize_args = argparse.Namespace(config=args.config, input=None, agent=args.agent, batch_size=args.batch_size)
    write_args = argparse.Namespace(config=args.config, input=None, summary=None, agent=args.agent)
    for fn, ns in [(cmd_fetch, fetch_args), (cmd_summarize, summarize_args), (cmd_write_note, write_args)]:
        code = fn(ns)
        if code:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stars-to-kbs")
    parser.add_argument(
        "--config",
        default=str(default_config_path()),
        help="Path to TOML config (default: ~/.config/stars-to-kbs/config.toml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create local config.toml from config.example.toml")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    fetch = sub.add_parser("fetch", help="Fetch GitHub starred repositories")
    fetch.add_argument("--max-repos", type=int, default=None)
    fetch.add_argument("--with-readme", action="store_true", default=None)
    fetch.set_defaults(func=cmd_fetch)

    summarize = sub.add_parser("summarize", help="Summarize cached repositories with selected AI CLI")
    summarize.add_argument("--input")
    summarize.add_argument("--agent", choices=sorted(SUPPORTED_AGENTS))
    summarize.add_argument("--batch-size", type=int)
    summarize.set_defaults(func=cmd_summarize)

    write = sub.add_parser("write-note", help="Write combined summary to configured KBS note path")
    write.add_argument("--input")
    write.add_argument("--summary")
    write.add_argument("--agent", choices=sorted(SUPPORTED_AGENTS))
    write.set_defaults(func=cmd_write_note)

    run = sub.add_parser("run", help="Fetch, summarize, and write the KBS note")
    run.add_argument("--agent", choices=sorted(SUPPORTED_AGENTS))
    run.add_argument("--max-repos", type=int, default=None)
    run.add_argument("--batch-size", type=int)
    run.add_argument("--with-readme", action="store_true", default=None)
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
