# TP2 local starter

Python 3.10+ and Docker Compose v2 required. Local disposable teaching stack only:
hardcoded credentials, development mode, and loopback-bound ports; never deploy it.

```sh
docker compose pull
docker compose up -d
sh seed.sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p results
RAW_CSV=results/baseline-1.csv WARMUP_SECONDS=5 USERNAME=user1 \
  locust -f locustfile.py --headless -u 10 -r 10 -t 35s --host http://127.0.0.1:8080
python3 analyse.py results/baseline-1.csv > results/baseline-1.json
```

Repeat with new filenames at least three times. Never overwrite evidence. The first
five seconds are warmup; statistics use the remaining rows. Locust's built-in
percentiles may use a different estimator; use raw rows for the required analysis.
Each request authenticates again; do not reuse bearer tokens. Reading realm policy:
`docker compose exec kc /opt/keycloak/bin/kcadm.sh config credentials --server
http://localhost:8080 --realm master --user admin --password lab-only-admin`, then
`docker compose exec kc /opt/keycloak/bin/kcadm.sh get realms/perf --fields passwordPolicy`.

## Faults: dedicated local stack only

Write each card before running. Record UTC time and elapsed run offset for injection
and recovery. No production resources or other people's services are in scope.
Use a 60-second run with five-second warmup and state the analysed window explicitly.

1. **Restart**: in a second terminal at your stated offset:
   `docker compose restart kc`. Stop load and inspect logs if readiness has not
   returned within 60 seconds. `docker compose up -d kc` restores the service.
2. **Database**: after every restart, explicitly authenticate `user1` once while
   the DB is up (a short load run does this). Seeding alone does not warm credentials.
   Then `docker compose stop db`; restore within 20 seconds with
   `docker compose start db`. A warmed-user null result is expected but conditional:
   explain it, do not grade the exact number. Contrast with `USERNAME=user30` which
   must not have authenticated since this Keycloak start. Stop on sustained errors
   or expiry of the 20-second window. Never delete a volume to implement this fault.
3. **Latency hop**: use `--host http://127.0.0.1:8081` for BOTH control and fault
   arms. This path forwards to Keycloak; it does not alter DB latency. Inject:
   `curl -fsS -X POST http://127.0.0.1:9090/delay -H 'Content-Type: application/json'
   -d '{"milliseconds":300,"seconds":20}'`. Delay expires automatically; stop early
   using the same command with `{"milliseconds":0}`. Stop load if errors are sustained.

For a DB-down startup contrast, stop `kc`, stop `db`, then use a disposable service
instance: `docker compose run --no-deps --rm kc`. Record logs and interrupt within
60 seconds if it has not exited. Verify the original DB is still stopped: some
providers automatically restart dependencies even on `start kc`, invalidating the
experiment. Do not use `up` or a dependency-starting command as evidence of DB-down
startup. Restore DB before restarting the original Keycloak. Changing `KC_DB` is a
separate configuration experiment: copy this directory, use a different Compose
project name and host ports, and remove ALL DB settings in that copy; never silently
change the measured stack or interpret this as the same condition.

## Submission layout

README.md, claim-card.md, hypothesis.md, synthesis.md, VERSIONS.md, results/*.csv;
faults/{restart,database,latency}/card.md and before.csv, during.csv, after.csv.
Also keep the complete raw run covering injection and recovery. Fault-arm extracts
must preserve the raw schema; mark their rows `measurement` and explain boundaries.
Include raw data, configurations, analysis outputs, estimator, bootstrap assumptions,
and actual image/Locust/Docker versions. Report each percentile with n and its CI.
Commit dates are not proof of experimental ordering and are not grading criteria.

`docker compose down` stops this project's services. It retains DB data. Volume
deletion is neither necessary nor recommended during experiments.
