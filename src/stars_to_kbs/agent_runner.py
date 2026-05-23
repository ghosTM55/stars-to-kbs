"""Run local AI CLI tools for summarization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from .markdown import render_fallback_summary
from .models import Repository

SUPPORTED_AGENTS = {"codex", "claude", "hermes", "none"}
DEFAULT_TIMEOUT_SECONDS = 900


class AgentRunner:
    def __init__(self, provider: str, work_dir: str | Path, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
        self.provider = provider.lower()
        self.work_dir = Path(work_dir)
        self.timeout_seconds = timeout_seconds
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def build_command(self, prompt_path: Path, output_path: Path) -> list[str]:
        """Build an argv-safe command for the configured local AI CLI."""
        if self.provider == "codex":
            return ["codex", "exec", "--skip-git-repo-check", "-o", str(output_path), "-"]
        if self.provider == "claude":
            return ["claude", "-p"]
        if self.provider == "hermes":
            prompt_ref = str(prompt_path).replace('"', '\\"')
            query = f'请严格执行 @file:"{prompt_ref}" 中的任务。只输出最终 Markdown。'
            return ["hermes", "chat", "-Q", "-q", query]
        if self.provider == "none":
            return []
        raise ValueError(f"Unsupported agent provider: {self.provider}. Supported: {', '.join(sorted(SUPPORTED_AGENTS))}")

    def clean_output(self, text: str) -> str:
        """Remove CLI bookkeeping lines from captured agent stdout."""
        lines = [line for line in text.splitlines() if not line.startswith("session_id:")]
        return "\n".join(lines).strip()

    def manifest_path(self, batch_name: str) -> Path:
        return self.work_dir / f"{batch_name}.manifest.json"

    def cache_manifest(self, prompt: str, repos: list[Repository]) -> dict[str, object]:
        return {
            "version": 1,
            "provider": self.provider,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "repo_full_names": [repo.full_name for repo in repos],
        }

    def cache_matches(self, batch_name: str, prompt: str, repos: list[Repository]) -> bool:
        path = self.manifest_path(batch_name)
        if not path.exists():
            return False
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            return False
        return existing == self.cache_manifest(prompt, repos)

    def write_manifest(self, batch_name: str, prompt: str, repos: list[Repository]) -> None:
        self.manifest_path(batch_name).write_text(
            json.dumps(self.cache_manifest(prompt, repos), ensure_ascii=False, indent=2) + "\n"
        )

    def summarize(self, prompt: str, batch_name: str, repos: list[Repository], *, use_cache: bool = False) -> str:
        """Run one agent prompt, optionally reusing a matching cached output file."""
        if self.provider == "none":
            return render_fallback_summary(repos)

        prompt_path = self.work_dir / f"{batch_name}.prompt.md"
        output_path = self.work_dir / f"{batch_name}.summary.md"

        if use_cache and output_path.exists() and self.cache_matches(batch_name, prompt, repos):
            cached = output_path.read_text()
            if cached.strip():
                return self.clean_output(cached)

        prompt_path.write_text(prompt)

        cmd = self.build_command(prompt_path, output_path)
        stdin = prompt if self.provider in {"codex", "claude"} else None
        try:
            result = subprocess.run(
                cmd,
                input=stdin,
                text=True,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"{self.provider} timed out for {batch_name} after {self.timeout_seconds} seconds"
            ) from exc
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"{self.provider} failed for {batch_name}: {stderr[-2000:]}")

        output_text = output_path.read_text() if output_path.exists() else ""
        if output_text.strip():
            cleaned = self.clean_output(output_text)
            self.write_manifest(batch_name, prompt, repos)
            return cleaned

        cleaned = self.clean_output(result.stdout or "")
        if cleaned:
            output_path.write_text(cleaned)
            self.write_manifest(batch_name, prompt, repos)
        return cleaned
