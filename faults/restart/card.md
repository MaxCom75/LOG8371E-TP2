# FAULT CARD - RESTART

**Steady-state claim**: "under 10 users, think time 0.1-0.3 s, one user (user1), realm policy hashIterations(210000), p99 stays within the baseline 95 % CI and the error rate stays below 1 % over each 30 s window"

**Fault**: docker compose restart kc at offset 15 s of a 60 s run. UTC time and elapsed offset of the injection and of the first successful request after it are recorded. Windows analysed: before = 5 s -> 15 s; during = 15 s -> first success after restart; after  = first success after restart -> 60 s.

**Blast radius**: only the local log8371-tp2 stack (kc container). DB, proxy and the db-data volume are not touched. Locust timeout is 5 s per request, so no request hangs. Stop by Ctrl+C on Locust, then docker compose up -d kc to restore the service.

**Stop condition**: Keycloak readiness has not returned within 60 s of the restart -> stop load, docker compose logs --tail 50 kc, docker compose up -d kc.

**Observed**: restart issued 19:33:43.464 (15.02 s), first failure 15.27 s, first success 26.68 s (~11.4 s outage, readiness well under 60 s, no stop).

| window | n | error | p99 | p99 bootstrap CI |
| --- | --- | --- | --- | --- |
| before | 220 | 0 % | 285.9 | [275.8, 296.5] |
| during | 449 | 98.7 % (RemoteDisconnected, fast fails) | - | - |
| after |  651 | 0 % | 1568.1 ms | [399.2, 1647.3] |

**What this shows**: claim broken: the error rate in the 30 s window holding the restart is far above 1 %. Keycloak recovers on its own in ~11 s, but the after window stays slower than baseline (cold JVM/caches), so p99 is outside the baseline CI after recovery too.
