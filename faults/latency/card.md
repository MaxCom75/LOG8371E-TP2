# FAULT CARD - LATENCY

**Steady-state claim** :  "under 10 users, think time 0.1-0.3 s, one user (user1),
                          realm policy hashIterations(210000), requests through
                          the proxy, p99 stays within the control-arm 95 % CI and
                          the error rate stays below 1 % over each 30 s window"

**Fault**              :  300 ms added once per request on the generator -> proxy
                          -> Keycloak hop, at offset 20 s of a 60 s run, for 20 s:
                          curl -fsS -X POST http://127.0.0.1:9090/delay
                            -H 'Content-Type: application/json'
                            -d '{"milliseconds":300,"seconds":20}'
                          Delay expires automatically at offset 40 s. UTC time and
                          elapsed offset of injection and expiry are recorded.
                          Control arm: same 60 s run through port 8081, no delay.
                          Windows analysed (measurement rows only):
                            before = 5 s -> 20 s
                            during = 20 s -> 40 s
                            after  = 40 s -> 60 s

**Blast radius**       :  only the local proxy container. Keycloak, DB and the
                          direct port 8080 are not touched. Delay is bounded by
                          the proxy to 1000 ms and 60 s. Locust timeout is 5 s.
                          Stop early with the same curl and {"milliseconds":0},
                          then Ctrl+C on Locust.

**Stop condition**     :  sustained errors (error rate above 1 % for 5 s in a row)
                          or the delay still active after offset 40 s -> send
                          {"milliseconds":0} and stop load.

**Observed**           :  inject 19:39:13.150 (20.06 s, HTTP 204), auto-expiry
                          19:39:33.093 (40.00 s), no stop. 0 errors in all runs.
                          control (control/): during n=390 p50 301.5 p99 374.4
                                              [368.7, 378.7], 19.5 req/s
                          fault   before n=303 p50 288.6 p99 333.6 [330.3, 334.2]
                                  during n=266 p50 543.2 p99 607.3 [596.8, 613.0]
                                        13.3 req/s
                                  after  n=392 p50 294.5 p99 573.8 [362.0, 588.2]

**What this shows**    :  claim broken on latency, not on errors: during-window
                          p99 is far outside the control CI while errors stay
                          0 %. The delay adds ~250 ms to p50 (not the full 300:
                          the closed loop drops to 13 req/s, so Keycloak is less
                          loaded) and cuts throughput ~33 %. Latency returns to
                          control level after expiry; the high after-p99 is
                          requests started before 40 s and finishing after it.
