FAULT CARD - DATABASE
 Steady-state claim : "under 10 users, think time 0.1-0.3 s, one user,
                      realm policy hashIterations(210000), p99 stays within
                      the baseline 95 % CI and the error rate stays below 1 %
                      over each 30 s window"
 Fault              : docker compose stop db at offset 20 s of a 60 s run,
                      docker compose start db at offset 40 s at the latest.
                      UTC time and elapsed offset of stop and start are recorded.
                      Two arms, same commands:
                        arm A (warm) : USERNAME=user1, authenticated once by a
                                       short load run with DB up after the
                                       last Keycloak restart (precondition).
                        arm B (cold) : USERNAME=user30, never authenticated
                                       since this Keycloak start.
                      Windows analysed (measurement rows only):
                        before = 5 s -> 20 s
                        during = 20 s -> db start
                        after  = db start -> 60 s
 Blast radius       : only the local log8371-tp2 stack (db container). The
                      db-data volume is never deleted, kc and proxy are not
                      touched. Locust timeout is 5 s per request.
                      Stop with docker compose start db, then Ctrl+C on Locust.
 Stop condition     : DB stopped for 20 s, or sustained errors (error rate
                      above 1 % for 5 s in a row) -> docker compose start db
                      immediately and stop load.
 Observed           : (filled after the run)
 What this shows    : (filled after the run)
