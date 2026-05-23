"""GitHub REST API access for starred repositories."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

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
            except Exception:
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
        with urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8")), dict(response.headers)

    def authenticated_user(self) -> str:
        if self.username:
            return self.username
        data, _ = self._get_json(f"{GITHUB_API}/user")
        self.username = data["login"]
        return self.username

    def fetch_starred(self, max_repos: int = 0, include_readme: bool = False) -> list[Repository]:
        repos: list[Repository] = []
        page = 1
        while True:
            params = urlencode({"per_page": 100, "page": page})
            url = f"{GITHUB_API}/user/starred?{params}"
            data, headers = self._get_json(url, accept="application/vnd.github.star+json")
            if not data:
                break
            for item in data:
                repo = Repository.from_github_star(item)
                if include_readme:
                    repo.readme_excerpt = self.fetch_readme_excerpt(repo.full_name)
                    time.sleep(0.1)
                repos.append(repo)
                if max_repos and len(repos) >= max_repos:
                    return repos
            if 'rel="next"' not in headers.get("Link", ""):
                break
            page += 1
        return repos

    def fetch_readme_excerpt(self, full_name: str, max_chars: int = 1200) -> str:
        url = f"{GITHUB_API}/repos/{full_name}/readme"
        req = Request(url, headers=self._headers("application/vnd.github.raw+json"))
        try:
            with urlopen(req, timeout=30) as response:
                text = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                return ""
            raise
        return text[:max_chars]


def save_repos(path: str | Path, repos: list[Repository]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([repo.to_dict() for repo in repos], ensure_ascii=False, indent=2))
    return output


def load_repos(path: str | Path) -> list[Repository]:
    return [Repository.from_dict(item) for item in json.loads(Path(path).read_text())]
