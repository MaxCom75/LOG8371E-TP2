
CLAIM CARD
 Operation     : POST /realms/perf/protocol/openid-connect/token
 Workload      : 10 users , think time 0.1-0.3 s, duration 35 s (5 s warmup
                 and 30 s run time), cache state WARM: one user (user1) for
                 every request, Keycloak and DB up for the whole run, user1
                 already authenticated since this Keycloak start by previous
                 runs
 Statistic     : mean of the three runs are
                  p50 = 237.3
                  p95 = 278.7
                  p99 = 300.9
                  mean = 239.9
                  error rate = 0.0%
                 percentiles estimated with linear interpolation at (n-1)*p
 n observed    : run 1 = 662, run 2 = 668, run 3 = 662 (total 1992)
 Threshold     : error rate stays below 1 % over each 30 s window
 Decision rule : ship if every repetition meets the error-rate threshold,
                 hold if any single repetition exceeds 1 % errors, and the
                 release owner decides.
 Limitation    : IID request bootstrap does not capture temporal dependence
                 or host uncertainty