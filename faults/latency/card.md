FAULT CARD - LATENCY
 Steady-state claim : "under 10 users, think time 0.1-0.3 s, one user (user1),
                      realm policy hashIterations(210000), requests through
                      the proxy, p99 stays within the control-arm 95 % CI and
                      the error rate stays below 1 % over each 30 s window"
 Fault              : 300 ms added once per request on the generator -> proxy
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
 Blast radius       : only the local proxy container. Keycloak, DB and the
                      direct port 8080 are not touched. Delay is bounded by
                      the proxy to 1000 ms and 60 s. Locust timeout is 5 s.
                      Stop early with the same curl and {"milliseconds":0},
                      then Ctrl+C on Locust.
 Stop condition     : sustained errors (error rate above 1 % for 5 s in a row)
                      or the delay still active after offset 40 s -> send
                      {"milliseconds":0} and stop load.
 Observed           : (filled after the run)
 What this shows    : (filled after the run)
