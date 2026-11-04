"""Own-run statistics. Stdlib only; linear-interpolated percentiles and bootstrap CI.

python3 analyse.py results/run.csv --bootstrap 1000 --seed 8371
Warmup rows are excluded. Failed-request latency remains in the population.
IID bootstrap describes request resampling, NOT host/run-to-run uncertainty.
"""
import argparse
import csv
import json
import math
import random
import statistics


def percentile(values, p):
    values = sorted(values)
    if not values:
        raise ValueError('empty population')
    index = (len(values) - 1) * p / 100
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def analyse(path, repetitions=1000, seed=8371):
    with open(path, newline='') as handle:
        rows = [row for row in csv.DictReader(handle) if row['phase'] == 'measurement']
    if not rows:
        raise ValueError('no measurement rows')
    values = [float(row['response_ms']) for row in rows]
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('invalid response time')
    if any(row['success'] not in ('0', '1') for row in rows):
        raise ValueError('success must be 0 or 1')
    rng = random.Random(seed)
    cis = {}
    for p in (50, 95, 99):
        estimates = [percentile(rng.choices(values, k=len(values)), p)
                     for _ in range(repetitions)]
        cis[f'p{p}'] = [percentile(estimates, 2.5), percentile(estimates, 97.5)]
    failures = sum(row['success'] == '0' for row in rows)
    return {'n': len(rows), 'failures': failures, 'error_rate': failures / len(rows),
            'population': 'measurement rows; successful and failed requests',
            'estimator': 'linear interpolation at (n-1)*p',
            'mean_ms': statistics.mean(values),
            'percentiles_ms': {f'p{p}': percentile(values, p) for p in (50, 95, 99)},
            'bootstrap_ci95_ms': cis, 'bootstrap_repetitions': repetitions, 'seed': seed,
            'limitation': 'IID request bootstrap does not capture temporal dependence or host uncertainty'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    parser.add_argument('--bootstrap', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=8371)
    args = parser.parse_args()
    if args.bootstrap < 100:
        parser.error('use at least 100 bootstrap resamples')
    print(json.dumps(analyse(args.csv, args.bootstrap, args.seed), indent=2))
