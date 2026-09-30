"""Plain-math Wilson intervals and ordered decision rules."""
from math import sqrt
from .store import validate_result

Z = 1.96


def wilson_interval(replies, sent):
    validate_result(sent, replies, 'a')
    # p = replies / sent; denom = 1 + z^2 / sent
    # centre = p + z^2 / (2 * sent)
    # delta = z * sqrt(p*(1-p)/sent + z^2/(4*sent^2))
    # bounds = (centre +/- delta) / denom
    p = replies / sent
    denom = 1 + Z**2 / sent
    centre = p + Z**2 / (2 * sent)
    delta = Z * sqrt(p * (1 - p) / sent + Z**2 / (4 * sent**2))
    return max(0.0, (centre - delta) / denom), min(1.0, (centre + delta) / denom)


def verdict(exp):
    variants = {}
    for variant in ('a', 'b'):
        observations = [o for o in exp['observations'] if o['variant'] == variant]
        sent = sum(o['sent'] for o in observations)
        replies = sum(o['replies'] for o in observations)
        variants[variant] = dict(sent=sent, replies=replies, rate=replies / sent if sent else None,
                                 interval=list(wilson_interval(replies, sent)) if sent else None)
    a, b = variants['a'], variants['b']
    winner = None
    if min(a['sent'], b['sent']) < exp['min_n']:
        rule, reason = 'a', 'sample too small'
    elif a['interval'][1] < b['interval'][0] or b['interval'][1] < a['interval'][0]:
        rule, reason = 'b', 'non-overlapping intervals'
        winner = 'a' if a['rate'] > b['rate'] else 'b'
    else:
        rule, reason = 'c', 'no clear separation'
    return dict(experiment=exp['name'], niche=exp['niche'], synthetic=exp['synthetic'],
                min_n=exp['min_n'], status='WINNER' if winner else 'INCONCLUSIVE',
                winner=winner, rule=rule, reason=reason, z=Z, variants=variants)
