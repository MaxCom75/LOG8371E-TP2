# Synthesis

## 1. Bottleneck hypothesis

**Hypothesis:** the token endpoint is bound by CPU spent on password hashing
(PBKDF2-SHA512, 210000 iterations per request), which no cache can skip.
Cutting the iterations by 90 % (210000 -> 21000) reduced p50, p95, p99 and
mean by about 90 % (p50 237.3 -> 24.3 ms), as predicted (see
[intervention.md](intervention.md)).

**Measurement that would change my mind:** a third run at 105000 iterations,
same workload. If p50 does not land near half the baseline (~120 ms), latency
is not proportional to the iteration count. The two-point result would then be
a coincidence, not proof that hashing is the bottleneck.

## 2. Chaos hypothesis (fault 2)

**Expected:** stopping the DB should make token requests fail, because
Keycloak stores users and credentials in PostgreSQL.

**Observed:**
- Warm user (user1): 0 % errors during a 19 s outage (n=372), with p99
  close to the before window.
- Never-authenticated user (user30): 83.9 % errors (78/93, HTTP 500) right
  away, which hit the stop condition. Errors continued for ~7 s after
  the DB was back.

**Why they differ:** Keycloak's in-memory cache (Infinispan) already held the
realm, the client and user1, including the stored password hash.
Checking the password is pure CPU work, so no request for user1 reached the
DB. user30 was not in the cache, so Keycloak had to load it from the DB and
failed.

## 3. What I cannot conclude

Every run used 10 concurrent users and a single Keycloak instance on one
laptop, and in practice one or two users. So I cannot conclude anything about
behaviour with more users, with many distinct users that would fill or evict
the user cache, or with more than one Keycloak node.
