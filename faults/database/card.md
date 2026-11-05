# FAULT CARD - DATABASE with a warm user (user1)

Data: faults/database/warm/

**Steady-state claim** : "under 10 users, think time 0.1-0.3 s, one user (user1), realm policy hashIterations(210000), p99 stays within the baseline 95 % CI and the error rate stays below 1 % over each 30 s window"

**Fault**: docker compose stop db at offset 20 s of a 60 s run, docker compose start db at offset 40 s at the latest. UTC time and elapsed offset of stop and start are recorded. Precondition: docker compose restart kc, wait for readiness, then a 15 s user1 load run with DB up (warms realm, client and user1). user1 for the whole 60 s run. Windows analysed: before = 5 s -> 20 s; during = 20 s -> db start; after  = db start -> 60 s.

**Blast radius**: only the local log8371-tp2 stack (db container, plus the kc restart of the precondition). The db-data volume is never deleted, proxy is not touched. Locust timeout is 5 s per request. Stop with docker compose start db, then Ctrl+C on Locust.

**Stop condition**: DB stopped for 20 s, or sustained errors (error rate above 1 % for 5 s in a row) -> docker compose start db immediately and stop load; the after window is then a separate 20 s run with the same user.

**Observed**: kc ready 19:54:50.505, warm-up 303/303 OK. stop 19:55:27.194 (20.03 s), start 19:55:46.274
(39.11 s), DB down 19.1 s, no stop.
| window | n | error | p99 | p99 bootstrap CI |
| --- | --- | --- | --- | --- |
| before | 299 | 0 % | 348.4 | [338.6, 354.0] |
| during | 372 | 0 % | 382.0 | [370.6, 387.0] |
| after |  409 | 0 % | 365.4 | [354.7, 369.1] |

**What this shows**: the DB is not on the path for a cached user: no errors during a 19 s outage. Keycloak's cache already held the realm, the client and user1 with its password hash, so checking the password needs only CPU. p50 ~295 ms in every window, above baseline (237 ms): residual slowness after the kc restart, so p99 is outside the baseline CI even before the fault.


# QUESTIONS FROM 4.3

**What exactly was cached, and by whom?**
After a first request with user1, it is held in the cache, along with its stored credentials, meaning that even if the DB is down, user1's credentials can still be accessed via the cache.

**Which requests in your workload actually reached the database?**
Ony the first request when a user is still cold. Once a user becomes warm and has its credentials within cache, Keycloak fetches them from the cache, not from the database.

**What would you have to change for the fault to become visible?**
Testing a request on a user that is still cold after the dabase has been stopped. Since the credentials will not be in cache, Keycloak will have to access the database for them, which will reveal the fault.

**Does your conclusion still hold for a user who has not logged in recently?**
No, the conclusion would not hold, since a user that has never logged in would not have its credentials in the cache. Keycloak would have to access the database to access them, which it won't be able to do, since the database will be down. I would then expect failure for all requests of a user that was not authenticated before the shutdown.

# FAULT CARD - DATABASE with a cold user (user30)

Data: faults/database/cold/

**Steady-state claim**: "under 10 users, think time 0.1-0.3 s, one user at a time (user1, then user30), realm policy hashIterations(210000), p99 stays within the baseline 95 % CI and the error rate stays below 0 % over each 30 s window"

**Fault**: docker compose stop db at offset 20 s of a 60 s run, docker compose start db at offset 40 s at the latest. UTC time and elapsed offset of stop, user switch and
start are recorded. Precondition: docker compose restart kc, wait for readiness, then a 15 s user1 load run with DB up (warms realm, client and user1). user30 is never sent before the DB stop, so it is not cached in Keycloak. user1 until the DB stop returns, then the same Locust run switches to user30. Windows analysed: before = 5 s -> 20 s; during = 20 s -> db start; after  = db start -> 60 s.

**Blast radius**: only the local log8371-tp2 stack (db container, plus the kc restart of the precondition). The db-data volume is never deleted, proxy is not touched. Locust timeout is 5 s per request. Stop with docker compose start db, then Ctrl+C on Locust.

**Stop condition**: DB stopped for 20 s, or sustained errors (error rate above 1 % for 5 s in a row) -> docker compose start db immediately and stop load; the after window is then a separate 20 s run with the same user.

**Observed**: kc ready 19:56:22.643, warm-up 257/257 OK. stop 19:56:59.300 (20.03 s), switch to user30 20.51 s. STOP CONDITION 26.13 s -> start 19:57:05.398 (DB down 6.1 s), load stopped.
| window | n | error | p99 | p99 bootstrap CI |
| --- | --- | --- | --- | --- |
| before | 298 | 0 % | 361.3 | [346.4, 371.8] |
| during | 93 | 83.9 % (15 OK = user1 in flight, 78x 500; 21-24 s no completions, then 500s in ~6 ms) | - | - |
| after |  594 | 58.4 %, all 500s in its first 7.2 s (UnknownHostException: db), then 0 % errors. | - | - |

**What this shows**: a user not yet cached must be loaded from the DB, so requests fail at once (HTTP 500) and break the error-rate claim. Recovery is not immediate: Keycloak kept failing for ~8 s after the DB was back.
