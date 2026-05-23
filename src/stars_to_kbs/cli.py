"""CLI for stars-to-kbs."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .agent_runner import AgentRunner, SUPPORTED_AGENTS
from .config import Config, default_config_path
from .github_api import GitHubStarsClient, load_repos, save_repos
from .markdown import render_kbs_note, render_merge_prompt_payload, render_prompt_payload
from .models import StarsSummary
from .validation import validate_summary


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def cache_path(config: Config) -> Path:
    return config.output.cache_dir / "starred.json"


def batch_summaries_path(config: Config) -> Path:
    return config.output.work_dir / "batch-summaries.md"


def summary_path(config: Config) -> Path:
    return config.output.work_dir / "combined-summary.md"


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.config)
    if target.exists() and not args.force:
        print(f"Config already exists: {target}")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[2] / "config.example.toml"
    if not source.exists():
        source = Path("config.example.toml")
    if not source.exists():
        raise FileNotFoundError("Could not find config.example.toml")
    shutil.copyfile(source, target)
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
    repos = load_repos(Path(args.input) if args.input else cache_path(config))
    provider = args.agent or config.agent.provider
    batch_size = args.batch_size or config.agent.batch_size
    runner = AgentRunner(provider, config.output.work_dir)

    outputs: list[str] = []
    for start in range(0, len(repos), batch_size):
        batch = repos[start:start + batch_size]
        batch_name = f"batch-{start // batch_size + 1:03d}"
        prompt = render_prompt_payload(batch, config.agent.language)
        outputs.append(runner.summarize(prompt, batch_name, batch, use_cache=args.resume))

    combined = "\n\n---\n\n".join(output.strip() for output in outputs if output.strip())
    out = batch_summaries_path(config)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(combined)
    print(f"Wrote batch summaries -> {out}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    repos = load_repos(Path(args.input) if args.input else cache_path(config))
    provider = args.agent or config.agent.provider
    batch_body = Path(args.batch_summaries or batch_summaries_path(config)).read_text()
    batch_outputs = [part.strip() for part in batch_body.split("\n\n---\n\n") if part.strip()]
    runner = AgentRunner(provider, config.output.work_dir)

    if provider == "none":
        merged = runner.summarize("", "merged", repos, use_cache=args.resume)
    elif len(batch_outputs) <= 1:
        merged = batch_outputs[0] if batch_outputs else "## 分类目录\n"
    else:
        prompt = render_merge_prompt_payload(batch_outputs, repos, config.agent.language)
        merged = runner.summarize(prompt, "merged", repos, use_cache=args.resume)

    out = Path(args.output) if args.output else summary_path(config)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(merged.strip() + "\n")
    print(f"Wrote merged summary -> {out}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    repos = load_repos(Path(args.input) if args.input else cache_path(config))
    body = Path(args.summary or summary_path(config)).read_text()
    result = validate_summary(repos, body)
    print(result.report())
    return 0 if result.passed else 1


def cmd_write_note(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    repos = load_repos(Path(args.input) if args.input else cache_path(config))
    body = Path(args.summary or summary_path(config)).read_text()
    if not args.skip_validate:
        result = validate_summary(repos, body)
        if not result.passed:
            print(result.report())
            return 1
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
    summarize_args = argparse.Namespace(
        config=args.config,
        input=None,
        agent=args.agent,
        batch_size=args.batch_size,
        resume=args.resume,
    )
    merge_args = argparse.Namespace(
        config=args.config,
        input=None,
        batch_summaries=None,
        output=None,
        agent=args.agent,
        resume=args.resume,
    )
    validate_args = argparse.Namespace(config=args.config, input=None, summary=None)
    write_args = argparse.Namespace(config=args.config, input=None, summary=None, agent=args.agent, skip_validate=True)
    for fn, ns in [
        (cmd_fetch, fetch_args),
        (cmd_summarize, summarize_args),
        (cmd_merge, merge_args),
        (cmd_validate, validate_args),
        (cmd_write_note, write_args),
    ]:
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
    summarize.add_argument("--batch-size", type=positive_int)
    summarize.add_argument("--resume", action="store_true", help="Reuse existing non-empty batch summary files")
    summarize.set_defaults(func=cmd_summarize)

    merge = sub.add_parser("merge", help="Merge batch summaries into one global taxonomy")
    merge.add_argument("--input", help="Repository cache JSON path")
    merge.add_argument("--batch-summaries", help="Batch summaries Markdown path")
    merge.add_argument("--output", help="Merged summary output path")
    merge.add_argument("--agent", choices=sorted(SUPPORTED_AGENTS))
    merge.add_argument("--resume", action="store_true", help="Reuse existing merged summary if present")
    merge.set_defaults(func=cmd_merge)

    validate = sub.add_parser("validate", help="Validate final Markdown contains every fetched repo exactly once")
    validate.add_argument("--input", help="Repository cache JSON path")
    validate.add_argument("--summary", help="Merged summary Markdown path")
    validate.set_defaults(func=cmd_validate)

    write = sub.add_parser("write-note", help="Write merged summary to configured KBS note path")
    write.add_argument("--input")
    write.add_argument("--summary")
    write.add_argument("--agent", choices=sorted(SUPPORTED_AGENTS))
    write.add_argument("--skip-validate", action="store_true")
    write.set_defaults(func=cmd_write_note)

    run = sub.add_parser("run", help="Fetch, summarize, merge, validate, and write the KBS note")
    run.add_argument("--agent", choices=sorted(SUPPORTED_AGENTS))
    run.add_argument("--max-repos", type=int, default=None)
    run.add_argument("--batch-size", type=positive_int)
    run.add_argument("--with-readme", action="store_true", default=None)
    run.add_argument("--resume", action="store_true", help="Reuse existing non-empty agent output files")
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
