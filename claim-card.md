# CLAIM CARD

**Operation**: POST /realms/perf/protocol/openid-connect/token

**Workload**: 10 users , think time 0.1-0.3 s, duration 35 s (5 s warmup and 30 s run time), cache state WARM: one user (user1) for every request, Keycloak and DB up for the whole run, user1 already authenticated since this Keycloak start by previous runs

| **Statistic**: | Run 1 | Run 2 | Run 3 |
| --- | --- | --- | --- |
| p50 | 238.88 | 232.70 | 240.19 |
| p50 bootstrap CI | [236.24, 241.41] | [230.29, 234.50] | [238.10, 242.53] |
| p95 | 283.08 | 268.69 | 284.18 |
| p95 bootstrap CI | [278.22, 288.63] | [267.01, 273.28] | [280.52, 288.76] |
| p99 | 310.11 | 289.54 | 303.15 |
| p99 bootstrap CI | [298.93, 333.15] | [282.74, 324.29] | [297.93, 320.11] |
| mean | 242.48 | 234.46 | 242.77 |
| error rate | 0.0 | 0.0 | 0.0 |
percentiles estimated with linear interpolation at (n-1)*p

**n observed**: run 1 = 662, run 2 = 668, run 3 = 662 (total 1992)

**Threshold**: error rate stays below 1 % over each 30 s window

**Decision rule**: ship if every repetition meets the error-rate threshold, hold if any single repetition exceeds 1 % errors, and the release owner decides.

**Limitation** : Covers only one warm, cached user with Keycloak and DB up. Does not cover more users, longer runs, multiple nodes or another host. The IID bootstrap does not capture temporal dependence or host uncertainty.