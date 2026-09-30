"""Explicitly synthetic, deterministic test data. Never real outreach."""
from pathlib import Path
from .store import save


def generate(out, path=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    experiments = []
    for name, niche, counts in [('clear-winner', 'synthetic operations', [(50, 8), (50, 22)]),
                                ('thin-data', 'synthetic tiny niche', [(8, 2), (9, 3)])]:
        experiments.append(dict(name=name, niche=niche, variant_a='synthetic problem opener',
                                variant_b='synthetic offer opener', min_n=30,
                                registered='2026-09-30', synthetic=True,
                                observations=[dict(variant=v, sent=n, replies=r, date='2026-09-30',
                                                   note='SYNTHETIC fixture, invented for testing')
                                              for v, (n, r) in zip(('a', 'b'), counts)]))
    target = Path(path) if path is not None else out / 'experiments.json'
    if target.exists():
        raise FileExistsError(f'refusing to overwrite existing store: {target}')
    save(dict(version=1, experiments=experiments), target)
    return target
