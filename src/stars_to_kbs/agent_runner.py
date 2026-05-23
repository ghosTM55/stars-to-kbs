"""Run local AI CLI tools for summarization."""

from __future__ import annotations

from pathlib import Path
import subprocess

from .markdown import render_fallback_summary
from .models import Repository

SUPPORTED_AGENTS = {"codex", "claude", "hermes", "none"}


class AgentRunner:
    def __init__(self, provider: str, work_dir: str | Path):
        self.provider = provider.lower()
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def build_command(self, prompt: str, output_path: Path) -> list[str]:
        if self.provider == "codex":
            return ["codex", "exec", "--skip-git-repo-check", "-o", str(output_path), prompt]
        if self.provider == "claude":
            return ["claude", "-p", prompt]
        if self.provider == "hermes":
            return ["hermes", "chat", "-q", prompt]
        if self.provider == "none":
            return []
        raise ValueError(f"Unsupported agent provider: {self.provider}. Supported: {', '.join(sorted(SUPPORTED_AGENTS))}")

    def summarize(self, prompt: str, batch_name: str, repos: list[Repository]) -> str:
        if self.provider == "none":
            return render_fallback_summary(repos)

        prompt_path = self.work_dir / f"{batch_name}.prompt.md"
        output_path = self.work_dir / f"{batch_name}.summary.md"
        prompt_path.write_text(prompt)

        cmd = self.build_command(prompt, output_path)
        result = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"{self.provider} failed for {batch_name}: {stderr[-2000:]}")

        if output_path.exists() and output_path.read_text().strip():
            return output_path.read_text().strip()
        return (result.stdout or "").strip()
