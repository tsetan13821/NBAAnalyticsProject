"""Publishing the refresh (src.game_model.refresh --push) against throwaway local git repositories."""
import json
import subprocess

import pytest

from src.game_model import refresh


def run_git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write_data(root, predictions: str, as_of: str):
    (root / 'data' / 'raw' / 'games').mkdir(parents=True, exist_ok=True)
    (root / 'data' / 'raw' / 'injuries').mkdir(parents=True, exist_ok=True)
    (root / 'data' / 'raw' / 'games' / 'schedule.csv').write_text('GAME_ID\n1\n')
    (root / 'data' / 'raw' / 'injuries' / 'injuries.csv').write_text('PLAYER_ID\n1\n')
    (root / 'data' / 'processed').mkdir(parents=True, exist_ok=True)
    (root / 'data' / 'processed' / 'game_predictions.csv').write_text(predictions)
    (root / 'data' / 'processed' / 'game_players.csv').write_text('PLAYER_ID\n1\n')
    (root / 'data' / 'processed' / 'live_meta.json').write_text(json.dumps({'as_of': as_of}))


@pytest.fixture
def repos(tmp_path, monkeypatch):
    """GitHub (a bare repository), this machine's checkout of main, and the other machine's."""
    for var, value in (('GIT_AUTHOR_NAME', 'test'), ('GIT_AUTHOR_EMAIL', 'test@example.com'),
                       ('GIT_COMMITTER_NAME', 'test'), ('GIT_COMMITTER_EMAIL', 'test@example.com')):
        monkeypatch.setenv(var, value)
    origin, here, other = tmp_path / 'origin.git', tmp_path / 'here', tmp_path / 'other'
    run_git(tmp_path, 'init', '-q', '--bare', '-b', 'main', str(origin))
    run_git(tmp_path, 'clone', '-q', str(origin), str(here))
    run_git(here, 'checkout', '-q', '-b', 'main')
    write_data(here, 'GAME_ID,PROB\n1,0.5\n', 'monday')
    run_git(here, 'add', '.')
    run_git(here, 'commit', '-q', '-m', 'start')
    run_git(here, 'push', '-q', 'origin', 'main')
    run_git(tmp_path, 'clone', '-q', str(origin), str(other))

    monkeypatch.setattr(refresh, 'PROJECT_ROOT', here)
    monkeypatch.setattr(refresh, 'check_serving_database', lambda: None)
    return here, other, origin


def test_a_new_timestamp_alone_is_not_published(repos, monkeypatch):
    here, _, origin = repos
    monkeypatch.setattr(refresh, 'build_live', lambda **_: write_data(here, 'GAME_ID,PROB\n1,0.5\n', 'tuesday'))
    refresh.refresh(push=True, stats=True)
    assert run_git(origin, 'log', '--format=%s', 'main') == 'start'
    assert run_git(here, 'status', '--porcelain') == ''  # left clean for the next run


def test_a_rejected_push_starts_again_from_the_other_machines_commit(repos, monkeypatch):
    here, other, origin = repos
    runs = []

    def build_live(**_):
        if not runs:  # the other machine publishes while this one is refreshing
            write_data(other, 'GAME_ID,PROB\n1,0.6\n', 'tuesday 1')
            run_git(other, 'commit', '-q', '-am', 'other machine')
            run_git(other, 'push', '-q', 'origin', 'main')
        runs.append(1)
        write_data(here, f'GAME_ID,PROB\n1,0.{6 + len(runs)}\n', f'tuesday {len(runs) + 1}')

    monkeypatch.setattr(refresh, 'build_live', build_live)
    refresh.refresh(push=True, stats=True)
    assert len(runs) == 2
    assert run_git(origin, 'log', '--format=%s', 'main').splitlines() == [
        refresh.COMMIT_MESSAGE, 'other machine', 'start']
    assert run_git(origin, 'show', 'main:data/processed/game_predictions.csv') == 'GAME_ID,PROB\n1,0.8'


def test_push_refuses_a_checkout_with_work_in_progress(repos, monkeypatch):
    here, _, origin = repos
    monkeypatch.setattr(refresh, 'build_live', lambda **_: pytest.fail("refreshed a dirty checkout"))
    (here / 'data' / 'processed' / 'game_players.csv').write_text('edited by hand\n')
    with pytest.raises(SystemExit, match='clean working tree'):
        refresh.refresh(push=True, stats=True)
    run_git(here, 'checkout', '-q', '-b', 'feature')
    with pytest.raises(SystemExit, match='needs main'):
        refresh.refresh(push=True, stats=True)
    assert run_git(origin, 'log', '--format=%s', 'main') == 'start'
