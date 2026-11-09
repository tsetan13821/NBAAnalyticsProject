"""Refresh the live predictions and publish them: what the scheduled runs do.

    python -m src.game_model.refresh                          # refresh only (like src.game_model.live)
    python -m src.game_model.refresh --push                   # then commit the data and push it to main
    python -m src.game_model.refresh --push --injuries-only   # from a cloud server (see below)

Two machines publish. GitHub Actions (.github/workflows/refresh-games.yml) refreshes the injury report
through the day; stats.nba.com refuses cloud servers, so it can't fetch results. A scheduled task on a
home PC (scripts/install-refresh-task.ps1) refreshes everything, results and schedule included.

When both push at about the same time, the later push is rejected. That run then starts again from the
other's commit and re-does its refresh, rather than merging generated files line by line.

--push only runs on a clean checkout of main with nothing unpushed (a CI checkout, or the dedicated
clone the scheduled task uses), so it never touches work in progress.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from src.game_model.live import build_live
from src.paths import PROJECT_ROOT

DATA_FILES = ['data/raw/games', 'data/raw/injuries', 'data/processed/game_predictions.csv',
              'data/processed/game_players.csv', 'data/processed/live_meta.json']
TIMESTAMP_ONLY = 'data/processed/live_meta.json'  # changes on every run; not worth a commit on its own
COMMIT_MESSAGE = "data: refresh game predictions [skip ci]"
ATTEMPTS = 3


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(['git', *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:  # raised here, with git's own message
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def start_from_main() -> None:
    """Bring a clean, fully pushed main up to date with GitHub; refuse anything else."""
    if git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip() != 'main':
        sys.exit("--push needs main checked out")
    if git('status', '--porcelain', '--untracked-files=no').stdout.strip():
        sys.exit("--push needs a clean working tree")
    git('fetch', '-q', 'origin', 'main')
    if git('rev-list', 'origin/main..HEAD').stdout.strip():
        sys.exit("--push: main has commits that aren't on GitHub")
    git('merge', '-q', '--ff-only', 'origin/main')


def check_serving_database() -> None:
    """Build the database the API serves, in a temporary folder: don't publish data it can't serve."""
    from src.export_db import build_database
    with tempfile.TemporaryDirectory() as folder:
        build_database(Path(folder) / 'nba.db')


def stage_changes() -> bool:
    """Stage the data; True if anything besides the timestamp changed."""
    git('add', '--', *DATA_FILES)
    return git('diff', '--cached', '--quiet', '--', '.', f':!{TIMESTAMP_ONLY}', check=False).returncode == 1


def refresh(push: bool, stats: bool) -> None:
    if not push:
        build_live(fetch=True, stats=stats)
        return
    start_from_main()
    for attempt in range(1, ATTEMPTS + 1):
        build_live(fetch=True, stats=stats)
        if not stage_changes():
            git('reset', '-q', '--hard')  # drop the new timestamp, leaving the checkout clean for next time
            print("No new results or statuses: nothing to publish.")
            return
        check_serving_database()
        git('commit', '-q', '-m', COMMIT_MESSAGE)
        if git('push', '-q', 'origin', 'HEAD:main', check=False).returncode == 0:
            print("Published.")
            return
        print(f"  push rejected (attempt {attempt}): the other refresh published first; starting again from its commit")
        git('fetch', '-q', 'origin', 'main')
        git('reset', '-q', '--hard', 'origin/main')
    sys.exit(f"Could not publish after {ATTEMPTS} attempts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--push', action='store_true', help="Commit the refreshed data and push it to main.")
    parser.add_argument('--injuries-only', action='store_true',
                        help="Skip stats.nba.com (results and schedule): for cloud servers, which it refuses.")
    args = parser.parse_args()
    refresh(push=args.push, stats=not args.injuries_only)
