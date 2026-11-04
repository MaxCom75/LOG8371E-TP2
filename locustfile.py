"""Single-process closed-loop token workload; authenticate again on every request.

RAW_CSV=results/run.csv USERNAME=user1 WARMUP_SECONDS=5 locust ...
Raw timing is Locust request-event timing, including failed requests. Never store tokens.
Use one new file per run; distributed runs are deliberately unsupported.
"""
import csv
import os
import time
from pathlib import Path
from locust import HttpUser, between, events, task

writer = None
output = None
start = None


@events.test_start.add_listener
def open_raw(environment, **kwargs):
    global writer, output, start
    path = Path(os.environ.get('RAW_CSV', 'results/raw.csv'))
    path.parent.mkdir(parents=True, exist_ok=True)
    output = path.open('x', newline='')
    writer = csv.writer(output)
    writer.writerow(['elapsed_s', 'response_ms', 'success', 'status_code', 'exception', 'phase'])
    start = time.monotonic()


@events.request.add_listener
def capture(request_type, name, response_time, response_length, exception,
            response=None, **kwargs):
    if writer is None:
        return
    elapsed = time.monotonic() - start
    warmup = float(os.environ.get('WARMUP_SECONDS', '5'))
    writer.writerow([f'{elapsed:.6f}', f'{response_time:.6f}', int(exception is None),
                     getattr(response, 'status_code', '') or '',
                     type(exception).__name__ if exception else '',
                     'warmup' if elapsed < warmup else 'measurement'])
    output.flush()


@events.test_stop.add_listener
def close_raw(environment, **kwargs):
    global writer
    if output:
        output.close()
    writer = None


class Login(HttpUser):
    wait_time = between(0.1, 0.3)

    @task
    def authenticate(self):
        self.client.post('/realms/perf/protocol/openid-connect/token', data={
            'grant_type': 'password', 'client_id': 'perf-client',
            'username': os.environ.get('USERNAME', 'user1'),
            'password': 'lab-password'}, name='POST /token', timeout=5)
