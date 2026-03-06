#!/usr/bin/env python3
"""
Extract cybersecurity-related PR/issue titles from ros_robotics_data.

Scans ../data/ros_robotics_data for pull_requests.json and issues.json,
filters titles using a fixed cybersecurity regex, and writes:

owner,repo,repository,type,number,title,html_url,state,created_at,closed_at,author,source_path
"""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any


# === FIXED CONFIGURATION ===
ROOT = Path("../data/ros_robotics_data").resolve()
OUT = Path("../ros_robotics_data_titles.csv").resolve()

KEYWORD_RE = re.compile(
    r"\b(?:"
    r"security|cybersecurity|secure|insecure|"
    r"attack\w*|threat\w*|vulnerab\w*|exploit\w*|"
    r"cve-\d{4}-\d+|"
    r"auth(?:entication|orization)?|"
    r"privilege|permission|access\s*control|"
    r"encrypt\w*|decrypt\w*|crypto\w*|certificate|tls|ssl|"
    r"injection|xss|csrf|"
    r"buffer\s*overflow|overflow|memory\s*leak|use-after-free|"
    r"race\s*condition|sandbox|hardening|patch"
    r")\b",
    re.IGNORECASE,
)


def iter_json_files(root: Path):
    for dirpath, _dirs, files in os.walk(root):
        if "pull_requests.json" in files:
            yield Path(dirpath) / "pull_requests.json", "pull_request"
        if "issues.json" in files:
            yield Path(dirpath) / "issues.json", "issue"


def load_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception as e:
        print(f"Skipping unreadable JSON: {path} ({e})")
        return None


def safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def synthesize_url(kind: str, owner: str, repo: str, number: str) -> str:
    if kind == "pull_request":
        return f"https://github.com/{owner}/{repo}/pull/{number}"
    return f"https://github.com/{owner}/{repo}/issues/{number}"


def run() -> int:
    if not ROOT.exists():
        print(f"Root path does not exist: {ROOT}")
        return 2

    OUT.parent.mkdir(parents=True, exist_ok=True)

    written = 0

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "owner",
                "repo",
                "repository",
                "type",
                "number",
                "title",
                "html_url",
                "state",
                "created_at",
                "closed_at",
                "author",
                "source_path",
            ]
        )

        for path, kind in iter_json_files(ROOT):
            obj = load_json(path)
            if obj is None:
                continue

            meta = obj.get("_meta", {})
            owner = meta.get("owner")
            repo = meta.get("repo")

            if not owner or not repo:
                print(f"Missing owner/repo metadata in {path}")
                continue

            items = obj.get("data")
            if not isinstance(items, list):
                continue

            repository = f"{owner}/{repo}"
            matched_here = 0

            for it in items:
                if not isinstance(it, dict):
                    continue

                title = it.get("title")
                if not isinstance(title, str) or not title.strip():
                    continue

                title = title.strip()

                if not KEYWORD_RE.search(title):
                    continue

                number = safe_str(it.get("number") or it.get("id"))
                url = synthesize_url(kind, owner, repo, number) if number else ""

                writer.writerow(
                    [
                        owner,
                        repo,
                        repository,
                        kind,
                        number,
                        title,
                        url,
                        safe_str(it.get("state")),
                        safe_str(it.get("created_at")),
                        safe_str(it.get("closed_at")),
                        safe_str(it.get("author")),
                        str(path),
                    ]
                )

                written += 1
                matched_here += 1

            print(f"{repository}: matched {matched_here} {kind}(s)")

    print(f"Wrote {written} rows to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())