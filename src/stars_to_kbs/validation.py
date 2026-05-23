"""Validate generated Markdown summaries against fetched repositories."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

from .models import Repository

REPO_HEADING_RE = re.compile(r"^####\s+([^\n#]+?)\s*$", re.MULTILINE)


@dataclass(slots=True)
class ValidationResult:
    expected: list[str]
    present: list[str]
    missing: list[str]
    extra: list[str]
    duplicates: list[str]

    @property
    def passed(self) -> bool:
        return not self.missing and not self.extra and not self.duplicates

    def report(self) -> str:
        lines = [
            f"Expected repositories: {len(self.expected)}",
            f"Repository headings: {len(self.present)}",
            f"Unique headings: {len(set(self.present))}",
        ]
        if self.missing:
            lines.append("Missing repositories:")
            lines.extend(f"- {name}" for name in self.missing)
        if self.extra:
            lines.append("Unexpected repositories:")
            lines.extend(f"- {name}" for name in self.extra)
        if self.duplicates:
            lines.append("Duplicate repositories:")
            lines.extend(f"- {name}" for name in self.duplicates)
        lines.append("Validation: PASS" if self.passed else "Validation: FAIL")
        return "\n".join(lines)


def extract_repo_headings(markdown: str) -> list[str]:
    """Extract `#### owner/repo` headings from a generated Markdown summary."""
    return [match.group(1).strip() for match in REPO_HEADING_RE.finditer(markdown)]


def expected_repo_names(repos: list[Repository]) -> list[str]:
    """Return unique repository full names while preserving input order."""
    seen: set[str] = set()
    names: list[str] = []
    for repo in repos:
        if repo.full_name not in seen:
            seen.add(repo.full_name)
            names.append(repo.full_name)
    return names


def validate_summary(repos: list[Repository], markdown: str) -> ValidationResult:
    """Check that every fetched repo appears exactly once in the Markdown output."""
    expected = expected_repo_names(repos)
    present = extract_repo_headings(markdown)
    expected_set = set(expected)
    present_set = set(present)
    counts = Counter(present)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    missing = [name for name in expected if name not in present_set]
    extra = sorted(name for name in present_set if name not in expected_set)
    return ValidationResult(expected, present, missing, extra, duplicates)
