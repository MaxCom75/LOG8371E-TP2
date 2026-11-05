"""Bounded fault run: one 60 s Locust run, a timed fault, then before/during/after extracts.

python faults/run_fault.py restart|db-warm|db-cold|latency|latency-control|warmup OUT_DIR [USERNAME]
db-warm: kc restart, user1 warm-up, USERNAME for the whole run.
db-cold: same, user1 until the DB stops, then USERNAME (must be cold).
Offsets are seconds since Locust test_start (same clock origin as elapsed_s in the CSV).
Windows use request completion time (elapsed_s) and measurement rows only.
"""
import csv
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analyse import analyse  # noqa: E402

LOCUST = ROOT / '.venv' / 'Scripts' / 'locust.exe'
FIELDS = ['elapsed_s', 'response_ms', 'success', 'status_code', 'exception', 'phase']


class Run:
    def __init__(self, out, username, host, seconds, warmup=5, switch=None):
        self.out, self.raw = out, out / 'raw.csv'
        out.mkdir(parents=True, exist_ok=True)
        self.log = (out / 'events.log').open('a')
        env = {**__import__('os').environ, 'RAW_CSV': str(self.raw), 'USERNAME': username,
               'WARMUP_SECONDS': str(warmup)}
        env.pop('USERNAME_FILE', None)
        if switch:
            env['USERNAME_FILE'] = str(switch)
        self.event(f'locust start user={username} host={host} duration={seconds}s warmup={warmup}s',
                   offset=False)
        self.proc = subprocess.Popen(
            [str(LOCUST), '-f', str(ROOT / 'locustfile.py'), '--headless', '-u', '10', '-r', '10',
             '-t', f'{seconds}s', '--host', host, '--only-summary'],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while not self.raw.exists():
            time.sleep(0.01)
        self.t0 = time.monotonic()

    def now(self):
        return time.monotonic() - self.t0

    def event(self, text, offset=True):
        utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        off = f'{self.now():7.2f}s' if offset else '      -'
        line = f'{utc} | {off} | {text}'
        print(line, flush=True)
        self.log.write(line + '\n')
        self.log.flush()

    def wait_until(self, offset, stop_check=None):
        while self.now() < offset:
            if stop_check and stop_check(self):
                return True
            time.sleep(0.2)
        return False

    def rows(self):
        with self.raw.open(newline='') as handle:
            return list(csv.DictReader(handle))

    def finish(self):
        self.proc.wait()
        self.event('locust exited')

    def kill(self):
        self.proc.terminate()
        self.proc.wait()
        self.event('locust stopped (stop condition)')


def compose(run, *args):
    run.event('issue: docker compose ' + ' '.join(args))
    result = subprocess.run(['docker', 'compose', *args], cwd=ROOT, capture_output=True, text=True)
    run.event(f'return: docker compose {" ".join(args)} (exit {result.returncode})')
    return result.returncode


def set_delay(run, ms, seconds=20):
    body = json.dumps({'milliseconds': ms, 'seconds': seconds}).encode()
    req = urllib.request.Request('http://127.0.0.1:9090/delay', body,
                                 {'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=5) as response:
        run.event(f'proxy delay {body.decode()} -> HTTP {response.status}')


def sustained_errors(since):
    """Card stop condition: every 1 s bucket of the last 5 s, after `since`, above 1 % errors."""
    def check(run):
        now = int(run.now())
        if now - 5 < since:
            return False
        buckets = {s: [0, 0] for s in range(now - 5, now)}
        for row in run.rows():
            second = int(float(row['elapsed_s']))
            if second in buckets:
                buckets[second][0] += 1
                buckets[second][1] += row['success'] == '0'
        if all(total == 0 or fails / total > 0.01 for total, fails in buckets.values()):
            run.event(f'STOP CONDITION: sustained errors in [{now - 5}, {now}) s {buckets}')
            return True
        return False
    return check


def ready():
    try:
        urllib.request.urlopen('http://127.0.0.1:8080/realms/perf', timeout=2)
        return True
    except OSError:
        return False


def split(out, raw, bounds, rows=None):
    """Write before/during/after extracts (raw schema, measurement rows) plus analysis."""
    if rows is None:
        with raw.open(newline='') as handle:
            rows = list(csv.DictReader(handle))
    summary = {}
    for name, (lo, hi) in bounds.items():
        part = [r for r in rows if r['phase'] == 'measurement' and lo <= float(r['elapsed_s']) < hi]
        path = out / f'{name}.csv'
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, FIELDS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(part)
        codes = {}
        for r in part:
            key = r['status_code'] or r['exception'] or 'none'
            codes[key] = codes.get(key, 0) + 1
        info = {'window_s': [lo, hi], 'n': len(part), 'status_counts': codes}
        if part:
            stats = analyse(path)
            (out / f'{name}.json').write_text(json.dumps(stats, indent=2))
            span = (hi if hi != float('inf') else max(float(r['elapsed_s']) for r in part)) - lo
            info.update(failures=stats['failures'], error_rate=round(stats['error_rate'], 4),
                        throughput_rps=round(len(part) / span, 1) if span > 0 else None,
                        p50=round(stats['percentiles_ms']['p50'], 1),
                        p95=round(stats['percentiles_ms']['p95'], 1),
                        p99=round(stats['percentiles_ms']['p99'], 1),
                        mean=round(stats['mean_ms'], 1),
                        ci95={k: [round(a, 1), round(b, 1)]
                              for k, (a, b) in stats['bootstrap_ci95_ms'].items()})
        summary[name] = info
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def restart(out, user):
    run = Run(out, user, 'http://127.0.0.1:8080', 60)
    run.wait_until(15)
    inject = run.now()
    compose(run, 'restart', 'kc')
    run.finish()
    if not ready():
        run.event('kc not ready at end of run; waiting up to 60 s after restart')
        while not ready() and time.monotonic() - run.t0 < inject + 60:
            time.sleep(1)
        if not ready():
            run.event('STOP CONDITION: readiness not back within 60 s')
            subprocess.run(['docker', 'compose', 'logs', '--tail', '50', 'kc'], cwd=ROOT)
            compose(run, 'up', '-d', 'kc')
    rows = run.rows()
    after = [r for r in rows if float(r['elapsed_s']) >= inject]
    first_fail = next((float(r['elapsed_s']) for r in after if r['success'] == '0'), None)
    first_ok = next((float(r['elapsed_s']) for r in after
                     if first_fail is not None and float(r['elapsed_s']) > first_fail
                     and r['success'] == '1'), None)
    run.event(f'derived: first failure after injection at {first_fail} s, '
              f'first success after restart at {first_ok} s')
    split(out, run.raw, {'before': (5, inject), 'during': (inject, first_ok or 60),
                         'after': (first_ok or 60, float('inf'))}, rows)


def fresh_kc(out):
    """Precondition: restart kc, wait for readiness, then a 15 s user1 run with DB up."""
    log = Run.__new__(Run)
    out.mkdir(parents=True, exist_ok=True)
    log.log, log.t0 = (out / 'events.log').open('a'), time.monotonic()
    compose(log, 'restart', 'kc')
    while not ready():
        if log.now() > 60:
            log.event('STOP CONDITION: readiness not back within 60 s')
            subprocess.run(['docker', 'compose', 'logs', '--tail', '50', 'kc'], cwd=ROOT)
            compose(log, 'up', '-d', 'kc')
            sys.exit(1)
        time.sleep(0.5)
    log.event('kc ready after restart')
    log.log.close()
    warmup(out / 'warmup', 'user1')


def database(out, user, cold=None):
    """Arm A: `user` throughout. Arm B: switch to `cold` once the DB stop has returned."""
    fresh_kc(out)
    switch = out / 'switch-user.txt'
    run = Run(out, user, 'http://127.0.0.1:8080', 60, switch=switch if cold else None)
    run.wait_until(20)
    stop = run.now()
    compose(run, 'stop', 'db')
    if cold:
        switch.with_suffix('.tmp').write_text(cold)
        switch.with_suffix('.tmp').replace(switch)
        run.event(f'user switch: {user} -> {cold} (new requests only)')
    tripped = run.wait_until(stop + 19, sustained_errors(int(stop) + 1))
    start = run.now()
    compose(run, 'start', 'db')
    run.event(f'db down window: stop issued {stop:.2f} s, start issued {start:.2f} s '
              f'({start - stop:.2f} s)')
    if not tripped:
        run.finish()
        split(out, run.raw, {'before': (5, stop), 'during': (stop, start),
                             'after': (start, float('inf'))})
        return
    run.kill()
    while subprocess.run(['docker', 'compose', 'exec', '-T', 'db', 'pg_isready', '-U', 'keycloak'],
                         cwd=ROOT, capture_output=True).returncode != 0:
        time.sleep(0.5)
    run.event('db healthy; separate 20 s after-run (load was stopped by the stop condition)')
    run.log.close()
    rows = run.rows()
    after = Run(out / 'after-run', cold or user, 'http://127.0.0.1:8080', 20, warmup=0)
    after.finish()
    split(out, run.raw, {'before': (5, stop), 'during': (stop, start)}, rows)
    split(out / 'after-run', after.raw, {'after': (0, float('inf'))})
    (out / 'after-run' / 'after.csv').replace(out / 'after.csv')
    (out / 'after-run' / 'after.json').replace(out / 'after.json')


def latency(out, user, inject=True):
    run = Run(out, user, 'http://127.0.0.1:8081', 60)
    tripped = run.wait_until(20)
    if inject:
        set_delay(run, 300, 20)
        tripped = run.wait_until(40, sustained_errors(21))
        if tripped:
            set_delay(run, 0)
            run.kill()
        else:
            run.event('delay expires (proxy auto-expiry, 20 s after injection)')
    else:
        run.event('control arm: no injection at 20 s')
        run.wait_until(40)
        run.event('control arm: 40 s boundary')
    if not tripped:
        run.finish()
    split(out, run.raw, {'before': (5, 20), 'during': (20, 40), 'after': (40, float('inf'))})


def warmup(out, user):
    run = Run(out, user, 'http://127.0.0.1:8080', 15)
    run.finish()
    rows = run.rows()
    ok = sum(r['success'] == '1' for r in rows)
    run.event(f'warm-up: {ok}/{len(rows)} successful requests for {user}')


if __name__ == '__main__':
    kind, out = sys.argv[1], Path(sys.argv[2])
    user = sys.argv[3] if len(sys.argv) > 3 else 'user1'
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'raw.csv').exists():
        sys.exit(f'{out / "raw.csv"} exists; never overwrite evidence')
    {'restart': restart, 'db-warm': database, 'db-cold': lambda o, u: database(o, 'user1', cold=u),
     'warmup': warmup,
     'latency': latency, 'latency-control': lambda o, u: latency(o, u, inject=False)}[kind](out, user)
