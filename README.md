# TP2 — Keycloak token endpoint: performance and reliability

Investigation of `POST /realms/perf/protocol/openid-connect/token` on a local
Keycloak + PostgreSQL stack: baseline, one bottleneck intervention, and three
injected faults (restart, database stop, 300 ms proxy delay).

Local disposable teaching stack only: hardcoded credentials, development mode,
loopback-bound ports. Never deploy it.

## Where to read

| File | Content |
|---|---|
| [claim-card.md](claim-card.md) | Claim, workload, threshold and decision rule (§3.4) |
| [hypothesis.md](hypothesis.md) | Bottleneck hypothesis, written before the intervention (§3.5) |
| [intervention.md](intervention.md) | Result of the one-factor intervention (`hashIterations` 210000 → 21000) |
| [faults/restart/card.md](faults/restart/card.md) | Fault 1: `docker compose restart kc` mid-run |
| [faults/database/card.md](faults/database/card.md) | Fault 2: `docker compose stop db`, warmed user vs never-authenticated user |
| [faults/latency/card.md](faults/latency/card.md) | Fault 3: +300 ms on the proxy → Keycloak hop, with a control arm |
| [synthesis.md](synthesis.md) | §7 answers |
| [VERSIONS.md](VERSIONS.md) | Docker, Keycloak, PostgreSQL, Locust, Python and host versions |

## Requirements

Docker Compose v2 and Python 3.10+. The commands below are for PowerShell on
Windows, which is what the results were produced with. On Linux/macOS, activate with
`. .venv/bin/activate` and change `LOCUST` at the top of `faults/run_fault.py`
to `.venv/bin/locust`.

## 1. Start the stack and seed users

```powershell
docker compose pull
docker compose up -d
sh seed.sh                      # perf realm, perf-client, user1..user30
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Baseline (3 repetitions)

Workload: 10 users, spawn rate 10/s, think time 0.1–0.3 s (closed loop),
35 s run, of which the first 5 s are warmup and excluded. Every request uses
`user1` and authenticates again (no token reuse). Locust timeout: 5 s.

```powershell
foreach ($i in 1..3) {
  $env:RAW_CSV = "results/baseline-$i.csv"; $env:WARMUP_SECONDS = "5"; $env:USERNAME = "user1"
  locust -f locustfile.py --headless -u 10 -r 10 -t 35s --host http://127.0.0.1:8080
  python analyse.py results/baseline-$i.csv | Out-File -Encoding utf8 results/baseline-$i.json
}
```

`analyse.py` uses only the `measurement` rows. It reports n, failures,
error rate, mean, p50/p95/p99 (linear interpolation at (n-1)·p) and an IID
bootstrap 95 % CI for each percentile (1000 resamples, seed 8371).

## 3. Intervention (one factor: hash iterations)

```powershell
$kcadm = "/opt/keycloak/bin/kcadm.sh"
docker compose exec kc $kcadm config credentials --server http://localhost:8080 --realm master --user admin --password lab-only-admin
docker compose exec kc $kcadm update realms/perf -s 'passwordPolicy=hashIterations(21000)'
docker compose exec kc $kcadm get realms/perf --fields passwordPolicy                          # verify
# same loop as the baseline, with results/intervention-$i.csv / .json
docker compose exec kc $kcadm update realms/perf -s 'passwordPolicy=hashIterations(210000)'   # restore
docker compose exec kc $kcadm get realms/perf --fields passwordPolicy                          # verify
```

The policy must be back at `hashIterations(210000)` before the fault runs.

## 4. Faults

`faults/run_fault.py` runs one 60 s Locust run (5 s warmup) and injects the fault at
a fixed offset. It logs the UTC time and run offset of every action to
`events.log` and checks the stop condition from the card. It then writes the
`before/during/after` extracts and their analysis. It refuses to overwrite an existing
`raw.csv`.

```powershell
python faults/run_fault.py restart          faults/restart                   # restart kc at 15 s
python faults/run_fault.py latency-control  faults/latency/control           # proxy, no delay
python faults/run_fault.py latency          faults/latency                   # proxy, +300 ms at 20 s for 20 s
python faults/run_fault.py db-warm          faults/database/warm  user1      # stop db at 20 s
python faults/run_fault.py db-cold          faults/database/cold  user30     # stop db at 20 s, switch to user30
```

Precondition for both database arms (done by the script): `docker compose restart kc`,
wait for readiness, then a 15 s `user1` run with the DB up (`warmup/`). `user30` is
never sent before the DB stops. The DB is restarted with `docker compose start db`
no more than 20 s after the stop, or earlier if the stop condition trips. The
`db-data` volume is never deleted.

Manual restore commands, if a run is interrupted:

```powershell
docker compose up -d kc
docker compose start db
curl.exe -fsS -X POST http://127.0.0.1:9090/delay -H "Content-Type: application/json" -d '{\"milliseconds\":0}'
```

## Data layout

```
results/
  baseline-{1,2,3}.csv/.json        raw rows + analysis, 35 s runs
  intervention-{1,2,3}.csv/.json    same workload, hashIterations(21000)
faults/<fault>/
  card.md                           fault card (written before the run)
  raw.csv                           complete run, including injection and recovery
  before.csv  during.csv  after.csv extracts of raw.csv (same schema, measurement rows)
  *.json, summary.json              analysis of each window
  events.log                        UTC time and run offset of every action
faults/latency/control/             control arm (proxy, no delay), same layout
faults/database/warm/               arm A: user1 throughout
faults/database/cold/               arm B: user1 then user30 after the DB stop
  warmup/                           precondition run after the kc restart
  after-run/                        cold arm only: separate 20 s run after the stop condition
```

CSV columns: `elapsed_s` (completion time in seconds since Locust test start),
`response_ms`, `success`, `status_code`, `exception`, `phase` (`warmup` or
`measurement`). The window boundaries for each fault are stated in its card. A request
falls into the window that contains its completion time.

`docker compose down` stops the stack and keeps the DB volume.
