# Sparrow Sales Experiment Lab

"No winner on thin data. Every verdict shows its math."

`sel` is Henry's local outreach lab notebook. It registers A/B positioning
experiments, accepts manually entered batches, computes Wilson 95% intervals,
and ranks measured niche reply rates. Python 3.10+; runtime dependencies are
standard library only. No network calls, GPU packages, or language-model calls.

## Quickstart

From this repository, `python -m sel` works without installation. To install the
`sel` command using an existing local setuptools installation:

```powershell
python -m pip install --no-deps --no-build-isolation -e .
sel fixtures --out demo --store demo/experiments.json
sel verdict --store demo/experiments.json --experiment thin-data
sel verdict --store demo/experiments.json --experiment clear-winner
sel niches --store demo/experiments.json
sel report --store demo/experiments.json --experiment clear-winner --format md --out demo/report.md
```

If Windows installs `sel.exe` in a Scripts directory outside PATH, use
`python -m sel` in place of `sel`, or add the Scripts directory printed by pip
to PATH.

These first three inspection commands form the two-minute demo: the thin-data
experiment is INCONCLUSIVE because its sample is too small; clear-winner declares
B; the niche table ranks measured rates and flags thin data. Every fixture result
is labelled synthetic.

First real use, with Henry supplying his own actual batch counts:

```powershell
sel experiment --name problem-vs-offer --variant-a "problem-first opener" --variant-b "offer-first opener" --niche "ops consultancies" --min-n 30
sel log --experiment problem-vs-offer --variant a --sent 40 --replies 6 --note "Tue batch"
sel verdict --experiment problem-vs-offer
```

The example log command illustrates syntax; only run it against a real store if
those numbers describe your own actual batch. No real results ship with this repo.

Run development checks with `python -m pytest -q` (pytest is a development tool,
not a runtime dependency).

## Architecture

```text
store -> log -> verdict -> niches
  |       |       |          |
  JSON    dated   Wilson     aggregated niche rates
  registry batches rules
                  |
                  report (Markdown or JSON)
fixtures -> explicitly synthetic store
```

`sel/store.py` validates all loaded records and atomically replaces the JSON file
after writing and flushing a temporary file. `sel/log.py` appends batches;
`sel/stats.py` computes the verdict; `sel/niches.py` ranks niche totals;
`sel/report.py` renders deterministic reports; `sel/fixtures.py` writes fixtures;
`sel/cli.py` connects the commands. The default store is
`./.sel-experiments.json`. Use one writer at a time: atomic replacement prevents
partial files, but this is not a concurrent database. Back up valuable stores.

## HONESTY BOUNDARY

All real outreach data is user-supplied. The tool performs no outreach, scraping,
purchasing, fetching, or importing of outreach results. No real outreach figures
are invented. The only generated figures are explicitly labelled synthetic
fixtures, solely for testing. A verdict never declares a winner below the
experiment's minimum sample size per variant. Reports carry this exact banner:

> HONESTY NOTE: all data in this report was entered by the user. No scraped, purchased, or invented outreach data. Fixtures are synthetic and labelled.

Fixture reports additionally identify synthetic provenance. Niche rows identify
synthetic, user-entered, or mixed provenance. Synthetic and real experiments can
be aggregated in the same store, so keep fixtures in a separate store for real
decisions. The niche table measures response, not causality or lead quality.

## Formula reference

Wilson score interval, with fixed `z = 1.96`:

```text
p = replies / sent
denom = 1 + z^2 / sent
centre = p + z^2 / (2 * sent)
delta = z * sqrt(p * (1 - p) / sent + z^2 / (4 * sent^2))
lower = (centre - delta) / denom
upper = (centre + delta) / denom
```

Worked example: 6 replies in 40 sends gives `p=0.15`, `z^2=3.8416`,
`denom=1.09604`, `centre=0.19802`, and `delta` approximately `0.120628`.
The interval is `[0.0706109171, 0.2907262604]`, or `[7.0611%, 29.0726%]`.
Zero replies and all replies are supported. A variant with zero sends has an
undefined rate and interval, displayed explicitly; it necessarily fails rule (a).
Floating point bounds are clipped to [0, 1] to handle boundary rounding.

## Decision-rule reference

Applied in this order:

1. Rule (a): if either variant's sent total is below `min_n`, INCONCLUSIVE,
   reason `sample too small`.
2. Rule (b): otherwise, strictly non-overlapping intervals yield WINNER for the
   higher-rate variant, reason `non-overlapping intervals`.
3. Rule (c): otherwise INCONCLUSIVE, reason `no clear separation`.

Intervals touching at an endpoint count as overlap. `min_n` defaults to 30 and
cannot be below 10. At exactly 10 sends per variant, a sufficiently wide gap may
produce a winner: this follows the registered rule and output shows the small
sample. A 95% interval is not a guarantee of a winner's future performance; this
conservative separation rule is not an exact two-sample significance test.

## CLI reference

`--store PATH` works before or after the subcommand. Names are case-sensitive.

| Command | Arguments and behavior |
| --- | --- |
| `experiment` | Required `--name`, `--variant-a`, `--variant-b`, `--niche`; optional `--min-n` (30). Registers date and descriptions. |
| `log` | Required `--experiment`, `--variant a\|b`, `--sent`, `--replies`; optional `--note`, `--date YYYY-MM-DD` (today). Appends batch. |
| `verdict` | Required `--experiment`. Shows rule, counts, rates, Wilson intervals, minimum n and provenance. |
| `niches` | Aggregates all experiments by niche, sorts descending reply rate, shows sends and provenance; under 30 total sends is `thin data`. |
| `report` | Required `--experiment`; `--format md\|json` (md); optional `--out FILE`, otherwise stdout. Includes banner, rule and math inputs. |
| `fixtures` | Required `--out DIR`; optional `--store PATH`, otherwise DIR/experiments.json. Refuses to overwrite an existing store. |

Rates are fractions; `0.300000` means 30%. Unobserved niches have undefined
rates and sort last; equal rates sort alphabetically. JSON preserves full math
precision, while text displays six decimals. Reports and verdicts have no render
timestamp: the same store gives byte-identical output across repeated runs.
Dates are local calendar dates, ISO formatted. Runtime errors exit 2 with a named
error; successful commands exit 0. Invalid CLI arguments also exit 2.

## Error catalogue

| Error | Meaning |
| --- | --- |
| `MinSampleTooSmallError` | Minimum n is not an integer of at least 10. |
| `DuplicateExperimentError` | Name already registered, including in a hand-edited store. |
| `UnknownExperimentError` | Requested experiment absent; never silently created. |
| `InvalidResultError` | Sent is not a positive integer, replies outside [0, sent], or variant invalid. |
| `DuplicateEntryError` | Same experiment, normalized variant, sent, replies and date already present. Note differences do not bypass this. |
| `CorruptStoreError` | Invalid JSON, schema, stored date or provenance marker. |
| `FileExistsError` | Fixture destination already exists; no overwrite. |
| `OSError` subclasses | Filesystem read/write failure. |

All stored observations are validated on load, so a hand-edited negative sent
count raises `InvalidResultError`. Variants are normalized on logging. Near
duplicates on different dates remain the user's responsibility. Two genuinely
distinct identical batches on the same date cannot be entered separately: combine
them into one accurate batch before logging. No edit/delete CLI is provided.

## Fixture documentation

Fixtures use a fixed date, 2026-09-30, and carry `synthetic: true` on every
experiment and SYNTHETIC notes on every observation. Generation is byte-identical
across directories. Two experiments are generated:

| Experiment | A | B | Expected |
| --- | --- | --- | --- |
| clear-winner | 8/50 (16%) | 22/50 (44%) | WINNER B; A CI [0.0834, 0.2851], B CI [0.3116, 0.5769] |
| thin-data | 2/8 (25%) | 3/9 (33.3333%) | INCONCLUSIVE, sample too small |

Ranking: synthetic operations, 30/100 = 30%, then synthetic tiny niche,
5/17 = 29.4118%, flagged thin data. The overlap path is exercised in tests with
10/50 versus 12/50; it is not a third generated experiment.

## Designing variants and improvement hook

Register the niche and sample threshold before examining results. Change one
positioning dimension at a time, assign comparable audiences to A and B, use the
same reply window, and enter each completed batch once. A reply is not a qualified
lead: feed the evidence into the outreach pipeline's 14-point lead quality
thinking, alongside qualification judgment. Do not infer a pattern from one reply.

After five real experiments have verdict records, review which clause binds.
The trigger is 4 out of 5 verdicts binding on the same clause. If minimum n binds,
raise the default minimum in your experiment registration practice (pass a higher
`--min-n`) and plan sufficiently sized experiments. If interval overlap binds
despite sufficient samples, test more different variants, not more sends. Save
reports as review evidence; this review is manual and synthetic experiments do
not count toward the five.

Maintain this as internal instrumentation. Integrate verdicts into outreach
pipeline docs; never commercialise it as a standalone product. Kill only if
outreach stops being experiment-driven. KOML lesson: adapt on patterns, not
single data points. Any comparison of outreach angles or demo flows should state
its sample size and decision rule before declaring a winner.
