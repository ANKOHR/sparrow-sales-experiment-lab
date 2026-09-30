import json
import subprocess
import sys

import pytest

from sel.cli import main
from sel.errors import (CorruptStoreError, DuplicateEntryError, DuplicateExperimentError,
                        InvalidResultError, MinSampleTooSmallError, UnknownExperimentError)
from sel.fixtures import generate
from sel.log import log_result
from sel.niches import rank_niches
from sel.report import HONESTY_BANNER, render_report, render_verdict
from sel.stats import verdict, wilson_interval
from sel.store import find, load, register


@pytest.fixture
def store(tmp_path):
    return generate(tmp_path)


def test_wilson_interval_matches_hand_computation():
    # Independent calculator: p=.15, denom=1.09604, centre=.19802,
    # delta approximately .120628, yielding these rounded bounds.
    assert tuple(round(v, 4) for v in wilson_interval(6, 40)) == (0.0706, 0.2907)


def test_thin_data_verdict_inconclusive(store):
    result = verdict(find(load(store), 'thin-data'))
    assert (result['status'], result['reason'], result['rule']) == ('INCONCLUSIVE', 'sample too small', 'a')


def test_clear_winner_declared(store):
    result = verdict(find(load(store), 'clear-winner'))
    assert (result['status'], result['winner'], result['rule']) == ('WINNER', 'b', 'b')
    assert result['variants']['a']['interval'] == pytest.approx((0.0833732, 0.2851448), abs=1e-6)
    assert tuple(round(v, 4) for v in result['variants']['b']['interval']) == (0.3116, 0.5769)


def make_experiment(tmp_path, counts, min_n=30):
    path = tmp_path / 'custom.json'
    register('test', 'first', 'second', 'real niche', min_n, path)
    for variant, (sent, replies) in zip(('a', 'b'), counts):
        if sent:
            log_result('test', variant, sent, replies, path=path)
    return path


def test_overlapping_intervals_inconclusive(tmp_path):
    path = make_experiment(tmp_path, [(50, 10), (50, 12)])
    result = verdict(find(load(path), 'test'))
    assert (result['status'], result['reason'], result['rule']) == ('INCONCLUSIVE', 'no clear separation', 'c')


@pytest.mark.parametrize('sent,replies', [(4, 5), (0, 0), (-1, 0), (5, -1)])
def test_invalid_results_rejected(store, sent, replies):
    with pytest.raises(InvalidResultError):
        log_result('clear-winner', 'a', sent, replies, path=store)


def test_duplicate_entry_rejected(store):
    log_result('clear-winner', 'a', 40, 6, path=store, batch_date='2026-10-01')
    before = store.read_bytes()
    with pytest.raises(DuplicateEntryError):
        log_result('clear-winner', 'A', 40, 6, note='different note', path=store, batch_date='2026-10-01')
    assert store.read_bytes() == before


def test_min_n_below_10_rejected(tmp_path, capsys):
    with pytest.raises(MinSampleTooSmallError):
        register('test', 'a', 'b', 'niche', 5, tmp_path / 'bad.json')
    assert main(['experiment', '--store', str(tmp_path / 'bad.json'), '--name', 'test',
                 '--variant-a', 'a', '--variant-b', 'b', '--niche', 'niche', '--min-n', '5']) == 2
    assert 'MinSampleTooSmallError' in capsys.readouterr().err


def test_variant_case_normalized(store):
    assert log_result('clear-winner', 'A', 40, 6, path=store)['variant'] == 'a'
    assert find(load(store), 'clear-winner')['observations'][-1]['variant'] == 'a'


def test_niches_ranked_by_rate(store):
    rows = rank_niches(load(store))
    assert [r['niche'] for r in rows] == ['synthetic operations', 'synthetic tiny niche']
    assert [r['rate'] for r in rows] == pytest.approx([30 / 100, 5 / 17])
    assert not rows[0]['thin_data'] and rows[1]['thin_data']
    assert all(r['provenance'] == 'synthetic' for r in rows)


def test_fixture_labelled_synthetic(store):
    assert all(e['synthetic'] and all('SYNTHETIC' in o['note'] for o in e['observations'])
               for e in load(store)['experiments'])


@pytest.mark.parametrize('format', ['md', 'json'])
def test_honesty_banner_in_report(store, format):
    output = render_report(verdict(find(load(store), 'clear-winner')), format)
    assert HONESTY_BANNER in output
    assert 'non-overlapping intervals' in output
    if format == 'json':
        assert json.loads(output)['verdict']['variants']['a']['sent'] == 50


def test_determinism(store):
    def run():
        return subprocess.run([sys.executable, '-m', 'sel', 'verdict', '--store', str(store),
                               '--experiment', 'clear-winner'], capture_output=True, check=True).stdout
    assert run() == run()
    for format in ('md', 'json'):
        assert render_report(verdict(find(load(store), 'clear-winner')), format) == render_report(verdict(find(load(store), 'clear-winner')), format)


def test_fixture_determinism(tmp_path):
    first = generate(tmp_path / 'one')
    second = generate(tmp_path / 'two')
    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(FileExistsError):
        generate(tmp_path / 'one')


def test_cli_smoke(tmp_path, capsys):
    path = tmp_path / 'demo' / 'experiments.json'
    assert main(['fixtures', '--out', str(path.parent), '--store', str(path)]) == 0
    assert main(['--store', str(path), 'experiment', '--name', 'subject-lines',
                 '--variant-a', 'question', '--variant-b', 'metric', '--niche', 'finance ops']) == 0
    assert main(['log', '--store', str(path), '--experiment', 'subject-lines', '--variant', 'a', '--sent', '40', '--replies', '6']) == 0
    for name in ('clear-winner', 'thin-data', 'subject-lines'):
        assert main(['verdict', '--store', str(path), '--experiment', name]) == 0
    assert main(['niches', '--store', str(path)]) == 0
    for format in ('md', 'json'):
        out = tmp_path / ('report.' + format)
        assert main(['report', '--store', str(path), '--experiment', 'clear-winner', '--format', format, '--out', str(out)]) == 0
        assert HONESTY_BANNER in out.read_text()
    output = capsys.readouterr().out
    assert 'WINNER variant B' in output and 'sample too small' in output and 'thin data' in output


@pytest.mark.parametrize('counts,expected', [([(10, 0), (10, 10)], 'WINNER'), ([(10, 2), (10, 3)], 'INCONCLUSIVE'), ([(9, 0), (100, 100)], 'INCONCLUSIVE'), ([(0, 0), (0, 0)], 'INCONCLUSIVE')])
def test_sample_guard_and_minimum(tmp_path, counts, expected):
    path = make_experiment(tmp_path, counts, min_n=10)
    assert verdict(find(load(path), 'test'))['status'] == expected


def test_unknown_experiment_rejected(store):
    before = store.read_bytes()
    with pytest.raises(UnknownExperimentError):
        log_result('missing', 'a', 5, 1, path=store)
    assert store.read_bytes() == before


@pytest.mark.parametrize('replies', [0, 10])
def test_boundary_intervals(replies):
    lower, upper = wilson_interval(replies, 10)
    assert 0 <= lower <= replies / 10 <= upper <= 1


def test_full_reply_batch_accepted(store):
    assert log_result('clear-winner', 'b', 10, 10, path=store)['replies'] == 10


def test_negative_sent_on_load(store):
    data = load(store)
    data['experiments'][0]['observations'][0]['sent'] = -50
    store.write_text(json.dumps(data))
    with pytest.raises(InvalidResultError):
        load(store)


@pytest.mark.parametrize('content', ['{broken', '{}', 'null', '{"version":1,"experiments":[null]}'])
def test_corrupt_store_named_error(tmp_path, content):
    path = tmp_path / 'bad.json'
    path.write_text(content)
    with pytest.raises(CorruptStoreError):
        load(path)


def test_duplicate_experiment_rejected(store):
    with pytest.raises(DuplicateExperimentError):
        register('clear-winner', 'x', 'y', 'niche', path=store)


def test_invalid_variant_rejected(store):
    with pytest.raises(InvalidResultError):
        log_result('clear-winner', 'c', 10, 1, path=store)


def test_empty_and_mixed_niche_ranking(tmp_path):
    path = make_experiment(tmp_path, [(0, 0), (0, 0)])
    rows = rank_niches(load(path))
    assert rows[0]['rate'] is None and rows[0]['thin_data']
    data = load(path)
    duplicate = dict(data['experiments'][0], name='synthetic', synthetic=True)
    data['experiments'].append(duplicate)
    assert rank_niches(data)[0]['provenance'] == 'mixed synthetic and user-entered'


def test_failed_atomic_replace_preserves_store(store, monkeypatch):
    from sel import store as module
    before = store.read_bytes()
    def fail(*args):
        raise OSError('simulated replacement failure')
    monkeypatch.setattr(module.os, 'replace', fail)
    with pytest.raises(OSError):
        log_result('clear-winner', 'a', 40, 6, path=store)
    assert store.read_bytes() == before
    assert not list(store.parent.glob('.sel-*.tmp'))
