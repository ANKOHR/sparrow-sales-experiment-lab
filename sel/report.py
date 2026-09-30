"""Deterministic reports with explicit provenance and math inputs."""
import json

HONESTY_BANNER = 'HONESTY NOTE: all data in this report was entered by the user. No scraped, purchased, or invented outreach data. Fixtures are synthetic and labelled.'


def render_verdict(result):
    lines = [f"{result['experiment']}: {result['status']}" + (f" variant {result['winner'].upper()}" if result['winner'] else ''),
             f"Rule ({result['rule']}): {result['reason']}; min_n={result['min_n']} per variant; z={result['z']}",
             'Provenance: ' + ('synthetic fixture' if result['synthetic'] else 'user-entered')]
    for name, v in result['variants'].items():
        math = f"rate={v['rate']:.6f}; Wilson 95% CI=[{v['interval'][0]:.6f}, {v['interval'][1]:.6f}]" if v['sent'] else 'rate=undefined; Wilson 95% CI=undefined (no sends)'
        lines.append(f"{name.upper()}: replies={v['replies']}; sent={v['sent']}; {math}")
    return '\n'.join(lines) + '\n'


def render_report(result, format='md'):
    if format == 'json':
        return json.dumps(dict(honesty_note=HONESTY_BANNER, verdict=result), sort_keys=True, indent=2) + '\n'
    if format != 'md':
        raise ValueError('format must be md or json')
    return '# Sparrow Sales Experiment Lab\n\n' + HONESTY_BANNER + '\n\n```text\n' + render_verdict(result) + '```\n\nMath inputs: replies, sent, p=replies/sent, z=1.96.\nFormula: denom=1+z^2/sent; centre=p+z^2/(2*sent); delta=z*sqrt(p*(1-p)/sent+z^2/(4*sent^2)); bounds=(centre +/- delta)/denom.\n'
