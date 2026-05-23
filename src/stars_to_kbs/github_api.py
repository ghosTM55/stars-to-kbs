"""GitHub REST API access for starred repositories."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Repository

GITHUB_API = "https://api.github.com"


class GitHubStarsClient:
    def __init__(self, token: str | None = None, username: str = ""):
        self.token = token or ""
        self.username = username

    @classmethod
    def from_env_or_gh(cls, token_env: str = "GH_TOKEN", username: str = "") -> "GitHubStarsClient":
        token = os.environ.get(token_env, "")
        if not token:
            try:
                token = subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL).strip()
            except (FileNotFoundError, subprocess.CalledProcessError):
                token = ""
        return cls(token=token, username=username)

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "stars-to-kbs/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get_json(self, url: str, accept: str = "application/vnd.github+json") -> tuple[Any, dict[str, str]]:
        req = Request(url, headers=self._headers(accept))
        try:
            with urlopen(req, timeout=60) as response:
                body = response.read().decode("utf-8")
                headers = dict(response.headers)
                return json.loads(body), headers
        except HTTPError as exc:
            headers = dict(exc.headers)
            retry_after = headers.get("Retry-After")
            remaining = headers.get("X-RateLimit-Remaining")
            reset = headers.get("X-RateLimit-Reset")
            if exc.code in {403, 429} and (remaining == "0" or retry_after):
                raise RuntimeError(
                    "GitHub API rate limit reached"
                    + (f"; retry after {retry_after}s" if retry_after else "")
                    + (f"; reset epoch {reset}" if reset else "")
                ) from exc
            detail = exc.read().decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(f"GitHub API request failed: HTTP {exc.code} for {url}. {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub API request failed for {url}: {exc.reason}") from exc

    def authenticated_user(self) -> str:
        if self.username:
            return self.username
        data, _ = self._get_json(f"{GITHUB_API}/user")
        self.username = data["login"]
        return self.username

    @staticmethod
    def _has_next_page(link_header: str) -> bool:
        links = [part.strip() for part in link_header.split(",") if part.strip()]
        return any('rel="next"' in link for link in links)

    def fetch_starred(self, max_repos: int = 0, include_readme: bool = False) -> list[Repository]:
        repos: list[Repository] = []
        seen: set[str] = set()
        page = 1
        while True:
            params = urlencode({"per_page": 100, "page": page})
            url = f"{GITHUB_API}/user/starred?{params}"
            data, headers = self._get_json(url, accept="application/vnd.github.star+json")
            if not data:
                break
            for item in data:
                repo = Repository.from_github_star(item)
                if repo.full_name in seen:
                    continue
                seen.add(repo.full_name)
                if include_readme:
                    repo.readme_excerpt = self.fetch_readme_excerpt(repo.full_name)
                    time.sleep(0.1)
                repos.append(repo)
                if max_repos and len(repos) >= max_repos:
                    return repos
            if not self._has_next_page(headers.get("Link", "")):
                break
            page += 1
        return repos

    def fetch_readme_excerpt(self, full_name: str, max_chars: int = 1200) -> str:
        url = f"{GITHUB_API}/repos/{full_name}/readme"
        req = Request(url, headers=self._headers("application/vnd.github.raw+json"))
        try:
            with urlopen(req, timeout=30) as response:
                text = response.read(max_chars * 4).decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                return ""
            raise RuntimeError(f"GitHub README request failed: HTTP {exc.code} for {full_name}") from exc
        return text[:max_chars]


def save_repos(path: Path, repos: list[Repository]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([repo.to_dict() for repo in repos], ensure_ascii=False, indent=2))
    return path


def load_repos(path: Path) -> list[Repository]:
    return [Repository.from_dict(item) for item in json.loads(path.read_text())]
