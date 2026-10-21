#!/usr/bin/env python3
"""
SolarSense EMS — Automated Daily Engineering Log Generator
==========================================================
Scans local or CI git repository commits over the designated lookback period,
attributes work to team members (Abubakar & Zaeem), breaks down modified files
and subsystems, and outputs a formatted markdown log into docs/daily_logs/.

Usage:
    python scripts/generate_daily_report.py                  # Generates report for last 24h
    python scripts/generate_daily_report.py --hours 48       # Generates report for last 48h
    python scripts/generate_daily_report.py --date 2026-10-21 # Generates report for specific date
    python scripts/generate_daily_report.py --dry-run        # Prints to console without writing file
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple


class CommitRecord(NamedTuple):
    hash_short: str
    author_name: str
    author_email: str
    timestamp: str
    subject: str
    files_changed: List[Tuple[str, int, int]]  # (filename, additions, deletions)


TEAM_MEMBERS = {
    "abubakar": {
        "display_name": "Abubakar",
        "role": "Team Lead / Systems, Optimization & Time-Series Forecasting",
        "aliases": ["abubakar", "abubakar651", "bakar", "abubakariqbal651@gmail.com"],
    },
    "zaeem": {
        "display_name": "Zaeem",
        "role": "Computer Vision, Panel Defects & Load Analytics",
        "aliases": ["zaeem", "zaeem571", "zaeem.m571@gmail.com"],
    },
}

SUBSYSTEM_RULES = [
    (r"^src/optimizer/", "⚡ Battery Optimization & MILP Solver"),
    (r"^src/forecast/", "📈 Solar PV & Factory Load Forecasting"),
    (r"^src/data_engineering/", "🗄️ Backend Feature Store & Data Engine"),
    (r"^src/grid_outage/", "🔌 Grid Outage & Reliability Prediction"),
    (r"^src/vision/|^data/.*(?:panel|defect|images)", "👁️ Computer Vision & Panel Defect Detection"),
    (r"^notebooks/", "📊 Exploratory Data Analysis & Prototyping"),
    (r"^tests/", "🧪 Test Suite & Invariant Validation"),
    (r"^docs/|.*\.md$|.*\.docx$|.*\.pptx$", "📝 Documentation, Specs & Milestones"),
    (r"^\.github/", "⚙️ CI/CD & Automated Workflows"),
    (r"^scripts/", "🛠️ DevOps, Scripts & Automation"),
]


def classify_subsystem(filepath: str) -> str:
    for pattern, subsystem_name in SUBSYSTEM_RULES:
        if re.search(pattern, filepath, re.IGNORECASE):
            return subsystem_name
    return "🔧 Project Infrastructure & Config"


def match_team_member(name: str, email: str) -> str:
    name_clean = name.lower().strip()
    email_clean = email.lower().strip()

    for member_key, info in TEAM_MEMBERS.items():
        for alias in info["aliases"]:
            if alias in name_clean or alias in email_clean:
                return member_key

    # Fallback to display name if unknown contributor
    return name or "Contributor"


def run_git_command(args: List[str], repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git error running {' '.join(args)}: {e.stderr}", file=sys.stderr)
        return ""


def parse_commit_stats(numstat_output: str) -> List[Tuple[str, int, int]]:
    files = []
    for line in numstat_output.splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 3:
            adds, dels, filename = parts
            add_count = int(adds) if adds.isdigit() else 0
            del_count = int(dels) if dels.isdigit() else 0
            files.append((filename, add_count, del_count))
    return files


def collect_commits(
    repo_root: Path,
    since_str: Optional[str] = None,
    until_str: Optional[str] = None,
) -> List[CommitRecord]:
    git_args = ["log", "--no-merges", "--pretty=format:COMMIT_START|%h|%an|%ae|%ad|%s", "--date=iso-strict"]

    if since_str:
        git_args.append(f"--since={since_str}")
    if until_str:
        git_args.append(f"--until={until_str}")

    raw_log = run_git_command(git_args, repo_root)
    if not raw_log:
        return []

    commit_lines = [line for line in raw_log.splitlines() if line.startswith("COMMIT_START|")]
    commits: List[CommitRecord] = []

    for header in commit_lines:
        parts = header.split("|")
        if len(parts) >= 6:
            _, hash_short, author_name, author_email, timestamp, subject = parts[:6]
            # Fetch numstat for this specific commit
            stat_out = run_git_command(["show", "--numstat", "--pretty=format:", hash_short], repo_root)
            files = parse_commit_stats(stat_out)
            commits.append(
                CommitRecord(
                    hash_short=hash_short,
                    author_name=author_name,
                    author_email=author_email,
                    timestamp=timestamp,
                    subject=subject,
                    files_changed=files,
                )
            )

    return commits


def format_markdown_report(
    target_date: str,
    commits: List[CommitRecord],
    lookback_window_desc: str,
) -> str:
    total_commits = len(commits)
    total_additions = sum(add for c in commits for _, add, _ in c.files_changed)
    total_deletions = sum(d for c in commits for _, _, d in c.files_changed)
    unique_files = len({f for c in commits for f, _, _ in c.files_changed})

    # Group by team member
    grouped: Dict[str, List[CommitRecord]] = {}
    for c in commits:
        member = match_team_member(c.author_name, c.author_email)
        grouped.setdefault(member, []).append(c)

    lines: List[str] = []
    lines.append(f"# ☀️ SolarSense EMS — Daily Engineering Log")
    lines.append(f"**Date:** `{target_date}` | **Coverage Window:** `{lookback_window_desc}` | **Generated:** `{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`")
    lines.append("")
    lines.append("## 📊 Daily Summary Metric")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"| :--- | :--- |")
    lines.append(f"| **Total Commits Merged** | `{total_commits}` |")
    lines.append(f"| **Active Team Contributors** | `{len(grouped)}` |")
    lines.append(f"| **Unique Files Touched** | `{unique_files}` |")
    lines.append(f"| **Code Volume** | `+{total_additions:,}` / `-{total_deletions:,}` lines |")
    lines.append("")

    if not commits:
        lines.append("> [!NOTE]")
        lines.append(f"> No new commits were pushed during the designated period ({lookback_window_desc}). Team likely focused on offline research, analysis, or weekend rest.")
        return "\n".join(lines) + "\n"

    lines.append("---")
    lines.append("")
    lines.append("## 👥 Individual Workstream Breakdown")
    lines.append("")

    # Display members in fixed order: Abubakar, then Zaeem, then any others
    ordered_keys = ["abubakar", "zaeem"] + [k for k in grouped.keys() if k not in ["abubakar", "zaeem"]]

    for key in ordered_keys:
        member_commits = grouped.get(key, [])
        info = TEAM_MEMBERS.get(key, {"display_name": key.title(), "role": "Contributor"})
        name = info["display_name"]
        role = info["role"]

        lines.append(f"### 👤 {name} — *{role}*")
        lines.append("")

        if not member_commits:
            lines.append("*(No commits pushed in this window)*")
            lines.append("")
            continue

        member_adds = sum(add for c in member_commits for _, add, _ in c.files_changed)
        member_dels = sum(d for c in member_commits for _, _, d in c.files_changed)
        lines.append(f"**Contributions:** `{len(member_commits)} commit(s)` | `+{member_adds:,} / -{member_dels:,} lines`")
        lines.append("")
        lines.append("#### Key Deliverables & Commits:")
        for c in member_commits:
            lines.append(f"- [`{c.hash_short}`] {c.subject}")

        # Group files by subsystem
        subsystem_map: Dict[str, List[Tuple[str, int, int]]] = {}
        for c in member_commits:
            for fname, add, delete in c.files_changed:
                subsystem = classify_subsystem(fname)
                subsystem_map.setdefault(subsystem, []).append((fname, add, delete))

        lines.append("")
        lines.append("#### Subsystems & Modules Impacted:")
        for subsys, flist in sorted(subsystem_map.items()):
            lines.append(f"- **{subsys}**")
            # Deduplicate filenames while aggregating counts
            file_counts: Dict[str, Tuple[int, int]] = {}
            for fn, a, d in flist:
                prev_a, prev_d = file_counts.get(fn, (0, 0))
                file_counts[fn] = (prev_a + a, prev_d + d)

            for fn, (a, d) in sorted(file_counts.items()):
                lines.append(f"  - `{fn}` (`+{a} / -{d}`)")

        lines.append("")

    lines.append("---")
    lines.append("## 🔍 Inspection & Audit Trail")
    lines.append("This document was generated deterministically from git commit metadata without external API dependencies. All changes are verified in the Git tree.")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate daily engineering log for SolarSense EMS")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours (default: 24)")
    parser.add_argument("--date", type=str, default=None, help="Target date in YYYY-MM-DD format (overrides --hours)")
    parser.add_argument("--output-dir", type=str, default="docs/daily_logs", help="Target output directory")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout without writing file")
    parser.add_argument("--force", action="store_true", help="Write report even if no commits occurred")

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    if args.date:
        try:
            target_dt = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.", file=sys.stderr)
            return 1
        target_date_str = args.date
        since_str = f"{target_date_str} 00:00:00"
        until_str = f"{target_date_str} 23:59:59"
        window_desc = f"Date {target_date_str} (00:00 - 23:59 PKT/Local)"
    else:
        target_date_str = dt.date.today().strftime("%Y-%m-%d")
        since_str = f"{args.hours} hours ago"
        until_str = None
        window_desc = f"Past {args.hours} hours"

    commits = collect_commits(repo_root, since_str=since_str, until_str=until_str)

    if not commits and not args.force and not args.dry_run:
        print(f"No commits found for {window_desc}. Skipping file creation (use --force to override).")
        return 0

    markdown_content = format_markdown_report(target_date_str, commits, window_desc)

    if args.dry_run:
        print(markdown_content)
        return 0

    out_dir = repo_root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{target_date_str}.md"

    out_file.write_text(markdown_content, encoding="utf-8")
    print(f"Successfully generated daily engineering log: {out_file.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
