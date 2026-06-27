"""Leaderboard scraper — snapshots rival submissions (RAMA C / infra).

The REFUGIO platform (https://refugio-hackathon-nine.vercel.app/) publishes every
team's code and result PUBLICLY, with no auth. This tool snapshots it so other
agents can study the strongest rival layouts/policies, re-score them in our bench
(`tools/benchmark.py`), and propose better solutions. Reading public leaderboard
solutions is part of the intended meta (see `AGENTS.md` / `submissions/SUBMITS.md`).

What it reads (all server-rendered HTML, stdlib only — no extra deps, no browser):
  GET /jobs            -> authoritative table of every job (id, team, status,
                          points, deliveries, runtime, timestamps, code/replay links)
  GET /code/<job_id>   -> page embedding the full submission source in <pre><code>
  GET /jobs/<job_id>   -> per-official-run breakdown + LLM safety review (--details)

What it writes (under --out, default `scraped/`):
  jobs.json                 every job's metadata
  standings.json            per-team best deliveries/points (derived)
  snapshot.json             scrape time + frontier (max deliveries) + our standing
  solutions/<NNNN>__<team>__<job>.py
                            each succeeded job's source, NNNN = zero-padded
                            deliveries so files sort best-first, with a metadata
                            header (team, deliveries, points, url) prepended
  INDEX.md                  human/agent-readable standings + how to use

Usage (from repo root `warehouse/`):
  python tools/scrape.py                 # snapshot everything into scraped/
  python tools/scrape.py --details       # also pull per-run breakdown + safety text
  python tools/scrape.py --force         # re-download code even if already saved
  python tools/scrape.py --no-code       # metadata only (fast)

Idempotent: re-run any time. By default it only downloads source it does not
already have, and reports which jobs are new since the last snapshot.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

BASE_URL = "https://refugio-hackathon-nine.vercel.app"
OUR_TEAM = "Equipo 10"
USER_AGENT = "refugio-team10-scraper/1.0 (local research tool)"
REQUEST_DELAY_S = 0.3
REQUEST_TIMEOUT_S = 20
MAX_RETRIES = 3


# --------------------------------------------------------------------------- #
# HTTP                                                                         #
# --------------------------------------------------------------------------- #
def fetch(path: str) -> str:
    """GET an absolute-or-relative path and return decoded text, with retries."""
    url = path if path.startswith("http") else f"{BASE_URL}{path}"
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover
            last_err = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_err}")


# --------------------------------------------------------------------------- #
# Parsing helpers                                                              #
# --------------------------------------------------------------------------- #
def _text(fragment: str) -> str:
    """Strip tags and unescape entities to plain text."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _num(value: str) -> float | int | None:
    """Parse a table cell into int/float, or None for '-'/empty."""
    value = value.strip().rstrip("s")  # runtime cells look like '21.68s'
    if not value or value == "-":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None


def _first(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# Data model                                                                   #
# --------------------------------------------------------------------------- #
@dataclass
class Job:
    job_id: str
    team: str
    team_slug: str | None
    status: str
    points: int | None
    deliveries: int | None
    runtime_s: float | None
    submitted: str | None
    committed: str | None
    has_code: bool
    has_replay: bool
    # filled in by --details
    runs: list[dict] = field(default_factory=list)
    safety_status: str | None = None
    safety_review: str | None = None
    code_saved_to: str | None = None


# --------------------------------------------------------------------------- #
# /jobs table -> Job list                                                      #
# --------------------------------------------------------------------------- #
def parse_jobs_table(html_text: str) -> list[Job]:
    tbody = _first(r"<tbody>(.*?)</tbody>", html_text)
    if tbody is None:
        raise RuntimeError("could not find <tbody> on /jobs — page layout changed?")

    jobs: list[Job] = []
    for row in re.findall(r"<tr>(.*?)</tr>", tbody, re.S):
        cells = re.findall(r"<td>(.*?)</td>", row, re.S)
        if len(cells) < 9:
            continue
        job_id = _text(cells[0])
        team_slug = _first(r'href="/teams/([^"]+)"', cells[1])
        links_cell = cells[8]
        jobs.append(
            Job(
                job_id=job_id,
                team=_text(cells[1]),
                team_slug=team_slug,
                status=_text(cells[2]),
                points=_num(_text(cells[3])),
                deliveries=_num(_text(cells[4])),
                runtime_s=_num(_text(cells[5])),
                submitted=_text(cells[6]) or None,
                committed=_text(cells[7]) or None,
                has_code=f"/code/{job_id}" in links_cell,
                has_replay=f"/replays/{job_id}" in links_cell,
            )
        )
    return jobs


# --------------------------------------------------------------------------- #
# /code/<id> -> source text                                                    #
# --------------------------------------------------------------------------- #
def parse_code_page(html_text: str) -> tuple[str, str]:
    """Return (filename_label, source_code) from a /code/<id> page."""
    block = _first(r"<pre><code>(.*?)</code></pre>", html_text)
    if block is None:
        raise RuntimeError("no <pre><code> block on code page — layout changed?")
    filename = _first(r'class="eyebrow">([^<]+)</span>', html_text) or "policy.py"
    return html.unescape(filename).strip(), html.unescape(block)


# --------------------------------------------------------------------------- #
# /jobs/<id> -> per-run breakdown + safety (optional, --details)               #
# --------------------------------------------------------------------------- #
def parse_job_detail(html_text: str) -> tuple[list[dict], str | None, str | None]:
    # The page is easiest to parse as flat text. Per-run rows read:
    #   "Official run <n> <packages/deliveries> <blocked> <remaining> <policy_time>s"
    text = _text(html_text)
    runs: list[dict] = []
    for m in re.finditer(r"Official run\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)s", text):
        runs.append(
            {
                "run": int(m.group(1)),
                "deliveries": int(float(m.group(2))),
                "blocked_moves": int(float(m.group(3))),
                "remaining_distance": int(float(m.group(4))),
                "policy_time_s": float(m.group(5)),
            }
        )
    sm = re.search(r"LLM safety review\s+Status\s+(\w+)\s+(.*?)\s*(?:Code Replay|$)", text)
    safety_status = sm.group(1) if sm else None
    safety_review = sm.group(2).strip() if sm else None
    return runs, safety_status, safety_review


# --------------------------------------------------------------------------- #
# Output writers                                                               #
# --------------------------------------------------------------------------- #
def slugify(team: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", team.lower()).strip("-") or "team"


def solution_filename(job: Job) -> str:
    rank = f"{job.deliveries:04d}" if isinstance(job.deliveries, int) else "0000"
    return f"{rank}__{slugify(job.team)}__{job.job_id}.py"


def write_solution(out_dir: Path, job: Job, filename_label: str, source: str) -> Path:
    sol_dir = out_dir / "solutions"
    sol_dir.mkdir(parents=True, exist_ok=True)
    path = sol_dir / solution_filename(job)
    header = (
        f'# === SCRAPED RIVAL SOLUTION (do not edit; regenerated by tools/scrape.py) ===\n'
        f"# team:       {job.team}\n"
        f"# job:        {job.job_id}  ({BASE_URL}/jobs/{job.job_id})\n"
        f"# deliveries: {job.deliveries}    points: {job.points}    runtime: {job.runtime_s}s\n"
        f"# submitted:  {job.submitted}\n"
        f"# code page:  {BASE_URL}/code/{job.job_id}    original file label: {filename_label}\n"
        f"# To evaluate in our bench: python tools/benchmark.py {path.as_posix()} --count 20\n"
        f"# ===========================================================================\n\n"
    )
    path.write_text(header + source, encoding="utf-8")
    return path


def build_standings(jobs: list[Job]) -> list[dict]:
    by_team: dict[str, dict] = {}
    for job in jobs:
        d = job.deliveries if isinstance(job.deliveries, int) else -1
        p = job.points if isinstance(job.points, int) else -1
        cur = by_team.setdefault(
            job.team,
            {"team": job.team, "best_deliveries": -1, "best_points": -1, "jobs": 0, "best_job": None},
        )
        cur["jobs"] += 1
        if d > cur["best_deliveries"]:
            cur["best_deliveries"] = d
            cur["best_job"] = job.job_id
        cur["best_points"] = max(cur["best_points"], p)
    standings = sorted(by_team.values(), key=lambda r: r["best_deliveries"], reverse=True)
    for i, row in enumerate(standings, 1):
        row["rank_by_deliveries"] = i
    return standings


def write_index(out_dir: Path, jobs: list[Job], standings: list[dict], snapshot: dict) -> None:
    succeeded = [j for j in jobs if j.status == "succeeded" and isinstance(j.deliveries, int)]
    succeeded.sort(key=lambda j: j.deliveries, reverse=True)
    frontier = snapshot["frontier_deliveries"]
    ours = snapshot["our_best_deliveries"]

    lines: list[str] = []
    lines.append("# Scraped leaderboard snapshot\n")
    lines.append(f"_Generated by `tools/scrape.py` at {snapshot['scraped_at']} — do not edit by hand._\n")
    lines.append(f"- **Frontier (max deliveries):** {frontier}")
    lines.append(f"- **{OUR_TEAM} best deliveries:** {ours}"
                 + ("" if ours is None else f"  (gap to frontier: {frontier - ours})"))
    lines.append(f"- **Jobs seen:** {len(jobs)}  ·  **with downloadable code:** "
                 f"{sum(1 for j in jobs if j.has_code)}\n")

    lines.append("## Standings (by best deliveries)\n")
    lines.append("| # | Team | Best deliveries | Best points | Jobs |")
    lines.append("|---|------|-----------------|-------------|------|")
    for r in standings:
        bd = r["best_deliveries"] if r["best_deliveries"] >= 0 else "-"
        bp = r["best_points"] if r["best_points"] >= 0 else "-"
        star = " ⭐" if r["team"] == OUR_TEAM else ""
        lines.append(f"| {r['rank_by_deliveries']} | {r['team']}{star} | {bd} | {bp} | {r['jobs']} |")
    lines.append("")

    lines.append("## Downloaded solutions (best first)\n")
    lines.append("Re-score any of these with `python tools/benchmark.py scraped/solutions/<file> --count 20`.\n")
    lines.append("| Deliveries | Points | Team | File |")
    lines.append("|------------|--------|------|------|")
    for j in succeeded:
        if j.code_saved_to:
            rel = Path(j.code_saved_to).relative_to(out_dir).as_posix()
            lines.append(f"| {j.deliveries} | {j.points} | {j.team} | `{rel}` |")
    lines.append("")
    (out_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #
def scrape(out_dir: Path, *, want_code: bool, force: bool, details: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    prev_ids = set()
    prev_path = out_dir / "jobs.json"
    if prev_path.exists():
        prev_ids = {j["job_id"] for j in json.loads(prev_path.read_text())}

    print(f"Fetching {BASE_URL}/jobs ...")
    jobs = parse_jobs_table(fetch("/jobs"))
    print(f"  found {len(jobs)} jobs")

    new_ids = [j.job_id for j in jobs if j.job_id not in prev_ids]
    if prev_ids:
        print(f"  new since last snapshot: {len(new_ids)}"
              + (": " + ", ".join(new_ids) if new_ids else ""))

    for job in jobs:
        if details and job.status != "running":
            time.sleep(REQUEST_DELAY_S)
            job.runs, job.safety_status, job.safety_review = parse_job_detail(
                fetch(f"/jobs/{job.job_id}")
            )

        if not (want_code and job.has_code):
            continue
        dest = out_dir / "solutions" / solution_filename(job)
        if dest.exists() and not force:
            job.code_saved_to = str(dest)
            continue
        time.sleep(REQUEST_DELAY_S)
        try:
            label, source = parse_code_page(fetch(f"/code/{job.job_id}"))
            job.code_saved_to = str(write_solution(out_dir, job, label, source))
            print(f"  saved code: {job.team} {job.job_id} ({job.deliveries} deliveries)")
        except RuntimeError as exc:
            print(f"  WARN: could not save code for {job.job_id}: {exc}")

    standings = build_standings(jobs)
    deliveries = [j.deliveries for j in jobs if isinstance(j.deliveries, int)]
    our_best = max(
        (j.deliveries for j in jobs if j.team == OUR_TEAM and isinstance(j.deliveries, int)),
        default=None,
    )
    snapshot = {
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "source": BASE_URL,
        "total_jobs": len(jobs),
        "frontier_deliveries": max(deliveries, default=0),
        "our_team": OUR_TEAM,
        "our_best_deliveries": our_best,
        "new_job_ids": new_ids,
    }

    (out_dir / "jobs.json").write_text(
        json.dumps([asdict(j) for j in jobs], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "standings.json").write_text(
        json.dumps(standings, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_index(out_dir, jobs, standings, snapshot)

    print("-" * 60)
    print(f"frontier (max deliveries): {snapshot['frontier_deliveries']}")
    print(f"{OUR_TEAM} best: {our_best}")
    print(f"wrote: {out_dir}/jobs.json, standings.json, snapshot.json, INDEX.md")
    print(f"solutions in: {out_dir}/solutions/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape the REFUGIO public leaderboard.")
    parser.add_argument("--out", type=Path, default=Path("scraped"), help="Output directory.")
    parser.add_argument("--no-code", action="store_true", help="Metadata only; skip source download.")
    parser.add_argument("--force", action="store_true", help="Re-download code even if already saved.")
    parser.add_argument("--details", action="store_true", help="Also fetch per-run breakdown + safety review.")
    args = parser.parse_args()
    scrape(args.out, want_code=not args.no_code, force=args.force, details=args.details)


if __name__ == "__main__":
    main()
