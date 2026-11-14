"""Persist only one worker's status/result; never raw observations or credentials.

Used inside GitHub Actions. Do not invoke locally against a real remote during testing.
Checkpoint upload happens before this command, so rejected pushes retain recovery evidence.
"""

import argparse
import subprocess
from pathlib import Path

from src.pipeline.job_store import LocalJobStore


def persist(job_id: str, branch: str) -> None:
    LocalJobStore._check_id(job_id)
    subprocess.run(["git", "check-ref-format", f"refs/heads/{branch}"], check=True)
    paths = [Path(f"data/jobs/jobs/{job_id}.json")]
    if not paths[0].is_file():
        raise ValueError("Cannot persist a missing job status")
    result = Path(f"data/jobs/results/{job_id}.json")
    if result.is_file():
        paths.append(result)
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "add", "-f", "--", *map(str, paths)], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
        return
    subprocess.run(
        ["git", "commit", "-m", f"chore(jobs): persist {job_id}", "--only", *map(str, paths)],
        check=True,
    )
    # Preserve unrelated commits that arrived while NASA was processing. A real
    # conflict stops publication; the uploaded evidence must be recovered manually.
    subprocess.run(["git", "pull", "--rebase", "origin", branch], check=True)
    subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    persist(args.job_id, args.branch)
