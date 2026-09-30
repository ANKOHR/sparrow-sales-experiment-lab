"""Local CLI. No network or outreach operations."""
import argparse
from pathlib import Path
from .errors import SelError
from .fixtures import generate
from .log import log_result
from .niches import rank_niches
from .report import render_report, render_verdict
from .stats import verdict
from .store import DEFAULT_STORE, find, load, register


def parser():
    root = argparse.ArgumentParser(prog='sel')
    root.add_argument('--store', default=DEFAULT_STORE)
    subs = root.add_subparsers(dest='command', required=True)
    for command in ('experiment', 'log', 'verdict', 'niches', 'report', 'fixtures'):
        p = subs.add_parser(command)
        p.add_argument('--store', default=argparse.SUPPRESS)
        if command == 'experiment':
            for field in ('name', 'variant-a', 'variant-b', 'niche'):
                p.add_argument('--' + field, required=True)
            p.add_argument('--min-n', type=int, default=30)
        if command in ('log', 'verdict', 'report'):
            p.add_argument('--experiment', required=True)
        if command == 'log':
            p.add_argument('--variant', required=True)
            p.add_argument('--sent', type=int, required=True)
            p.add_argument('--replies', type=int, required=True)
            p.add_argument('--note', default='')
            p.add_argument('--date', help='batch date, ISO YYYY-MM-DD (default today)')
        if command == 'report':
            p.add_argument('--format', choices=('md', 'json'), default='md')
            p.add_argument('--out')
        if command == 'fixtures':
            p.add_argument('--out', required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'experiment':
            register(args.name, args.variant_a, args.variant_b, args.niche, args.min_n, args.store)
            print(f'Registered {args.name}')
        elif args.command == 'log':
            log_result(args.experiment, args.variant, args.sent, args.replies, args.note, args.store, args.date)
            print('Logged user-entered batch')
        elif args.command in ('verdict', 'report'):
            result = verdict(find(load(args.store), args.experiment))
            output = render_verdict(result) if args.command == 'verdict' else render_report(result, args.format)
            if args.command == 'report' and args.out:
                Path(args.out).write_bytes(output.encode('utf-8'))
            else:
                print(output, end='')
        elif args.command == 'niches':
            for row in rank_niches(load(args.store)):
                rate = f"{row['rate']:.6f}" if row['rate'] is not None else 'undefined'
                print(f"{row['niche']}: rate={rate}; sent={row['sent']}; replies={row['replies']}; {row['provenance']}" + ('; thin data' if row['thin_data'] else ''))
        else:
            target = generate(args.out, None if args.store == DEFAULT_STORE else args.store)
            print(f'SYNTHETIC fixtures written to {target}')
        return 0
    except (SelError, OSError) as exc:
        print(f'{type(exc).__name__}: {exc}', file=__import__('sys').stderr)
        return 2
