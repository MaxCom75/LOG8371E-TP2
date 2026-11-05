# VERSIONS

## Services

| Component | Image | Version reported at runtime |
|---|---|---|
| Keycloak | `quay.io/keycloak/keycloak:24.0.5@sha256:f8ade94c1d0ad2f2fa7734a455fee5392764f402c43ca35e9af6bf63a2541dc9` | Keycloak 24.0.5, JVM OpenJDK 17.0.14+7-LTS (Red Hat), `start-dev` mode |
| PostgreSQL | `docker.io/library/postgres:16.9-bookworm@sha256:253815cf7579ffa05e1673d92e78d37273e61be0e4414e9a1449337d7925be94` | PostgreSQL 16.9 (Debian 16.9-1.pgdg120+1) |
| Chaos proxy | `docker.io/library/python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db` | Python 3.12.10, runs `chaos/proxy.py` |

Platform pulled for all three images: `linux/amd64`. Local image IDs:
Keycloak `f8ade94c1d0a`, PostgreSQL `253815cf7579`, proxy `fd95fa221297`.

## Realm configuration

| Setting | Value |
|---|---|
| `perf` realm `passwordPolicy` | `hashIterations(210000)` (Keycloak 24 default hashing, PBKDF2-SHA512) for the baseline and all faults |
| Intervention only | `hashIterations(21000)`, restored to `210000` before the fault runs |
| Users | `user1`–`user30`, created by `seed.sh` |

## Load generator and analysis

| Component | Version |
|---|---|
| Locust | 2.32.10 (`requirements.txt`) |
| Python (Locust venv, `analyse.py`, `faults/run_fault.py`) | 3.14.2 |
| Percentile estimator | linear interpolation at (n-1)·p (`analyse.py`) |
| Bootstrap | IID resampling of requests, 1000 repetitions, seed 8371, 95 % percentile interval |

## Container runtime

| Component | Version |
|---|---|
| Docker Engine (client and server) | 29.2.1, linux/amd64 |
| Docker Compose | v5.1.0 |
| Docker Desktop VM kernel | 6.6.87.2-microsoft-standard-WSL2 (WSL 2 backend) |
| Resources visible to Docker | 16 CPUs, 15.6 GiB memory |

## Host

| Component | Value |
|---|---|
| OS | Windows 11 Home, build 10.0.26200 |
| CPU | Intel Core i7-10700F @ 2.90 GHz (8 cores / 16 threads) |
| RAM | 32 GB |
| Load generator location | same host as the stack (Locust on Windows, stack in the WSL 2 VM, over `127.0.0.1`) |
