# FAULT CARD - DATABASE

**Steady-state claim** :  "under 10 users, think time 0.1-0.3 s, one user,
                          realm policy hashIterations(210000), p99 stays within
                          the baseline 95 % CI and the error rate stays below 1 %
                          over each 30 s window"

**Fault**              :  docker compose stop db at offset 20 s of a 60 s run,
                          docker compose start db at offset 40 s at the latest.
                          UTC time and elapsed offset of stop and start are recorded.
                          Precondition for each arm: docker compose restart kc,
                          wait for readiness, then a 15 s user1 load run with DB
                          up (warms realm, client and user1; user30 never sent).
                          Two arms, same commands:
                            arm A (warm/) : user1 for the whole 60 s run.
                            arm B (cold/) : user1 until the DB stop returns, then
                                            the same Locust run switches to
                                            user30 (USERNAME_FILE); switch time
                                            is recorded.
                          Windows analysed (measurement rows only):
                            before = 5 s -> 20 s
                            during = 20 s -> db start
                            after  = db start -> 60 s

**Blast radius**       :  only the local log8371-tp2 stack (db container, plus
                          the kc restart of the precondition). The db-data volume
                          is never deleted, proxy is not touched. Locust timeout
                          is 5 s per request.
                          Stop with docker compose start db, then Ctrl+C on Locust.

**Stop condition**     :  DB stopped for 20 s, or sustained errors (error rate
                          above 1 % for 5 s in a row) -> docker compose start db
                          immediately and stop load; the after window is then a
                          separate 20 s run with the same user.

**Observed**           :  arm A (warm/): kc ready 19:54:50.505, warm-up 303/303 OK.
                          stop 19:55:27.194 (20.03 s), start 19:55:46.274
                          (39.11 s), DB down 19.1 s, no stop.
                            before n=299 err 0 % p99 348.4 [338.6, 354.0]
                            during n=372 err 0 % p99 382.0 [370.6, 387.0]
                            after  n=409 err 0 % p99 365.4 [354.7, 369.1]
                          arm B (cold/): kc ready 19:56:22.643, warm-up 257/257
                          OK. stop 19:56:59.300 (20.03 s), switch to user30
                          20.51 s. STOP CONDITION 26.13 s -> start 19:57:05.398
                          (DB down 6.1 s), load stopped.
                            before n=298 err 0 %    p99 361.3 [346.4, 371.8]
                            during n=93  err 83.9 % (15 OK = user1 in flight,
                                  78x 500; 21-24 s no completions, then 500s
                                  in ~6 ms)
                            after  separate 20 s user30 run from 19:57:05.982:
                                  n=594 err 58.4 %, all 500s in its first 7.2 s
                                  (UnknownHostException: db), then 0 % errors.

**What this shows**    :  the DB is not on the path for a cached user: arm A sees
                          no change during a 19 s outage. A user not yet cached
                          must be loaded from the DB, so arm B fails at once (500)
                          and breaks the 1 % claim. Recovery is not immediate:
                          Keycloak kept failing for ~8 s after the DB was back.
                          p50 ~295 ms in every OK window, above baseline (237 ms):
                          residual slowness after the kc restart.
