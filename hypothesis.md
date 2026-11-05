# HYPOTHESIS
 
**Suspect**: CPU-bound password hashing in Keycloak. Every token request runs PBKDF2-SHA512 with 210000 iterations, which no cache can skip.

**Predicted signal**: p50, p95, p99 and mean should all drop roughly in proportion to the iteration count.

**Intervention**: Lower the perf realm policy to hashIterations(21000), with the same workload as the baseline (user1, 10 users, 35 s).

**Falsifier**: p50, p95, p99 and mean all stay within the baseline range or drop by less than half.
