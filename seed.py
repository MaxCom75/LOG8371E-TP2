"""Seed only the dedicated local perf realm. Existing realms are not overwritten."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:8080'


def request(path, data=None, token=None, form=False):
    headers = {}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if data is not None:
        data = (urllib.parse.urlencode(data) if form else json.dumps(data)).encode()
        headers['Content-Type'] = ('application/x-www-form-urlencoded' if form
                                   else 'application/json')
    with urllib.request.urlopen(urllib.request.Request(BASE + path, data, headers),
                                timeout=10) as response:
        body = response.read()
        return json.loads(body) if body else None


def main():
    deadline = time.monotonic() + 180
    while True:
        try:
            request('/realms/master/.well-known/openid-configuration')
            break
        except (OSError, urllib.error.URLError):
            if time.monotonic() >= deadline:
                raise SystemExit('Keycloak not ready after 180 seconds; inspect compose logs.')
            time.sleep(2)
    token = request('/realms/master/protocol/openid-connect/token', {
        'grant_type': 'password', 'client_id': 'admin-cli',
        'username': 'admin', 'password': 'lab-only-admin'}, form=True)['access_token']
    try:
        realm = request('/admin/realms/perf', token=token)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    else:
        print('perf already exists; no changes made. Verify its settings before measuring.')
        print('passwordPolicy:', realm.get('passwordPolicy'))
        return
    realm = {
        'realm': 'perf', 'enabled': True, 'sslRequired': 'none',
        'passwordPolicy': 'hashAlgorithm(pbkdf2-sha512) and hashIterations(210000)',
        'clients': [{'clientId': 'perf-client', 'enabled': True, 'publicClient': True,
                     'directAccessGrantsEnabled': True}],
        'users': [{'username': f'user{i}', 'enabled': True, 'emailVerified': True,
                   'email': f'user{i}@example.invalid', 'firstName': 'Lab',
                   'lastName': str(i), 'requiredActions': [],
                   'credentials': [{'type': 'password', 'value': 'lab-password',
                                    'temporary': False}]} for i in range(1, 31)]}
    request('/admin/realms', realm, token=token)
    actual = request('/admin/realms/perf', token=token)
    print('Created 30 users. Seeding does not authenticate/warm them.')
    print('passwordPolicy:', actual.get('passwordPolicy'))


if __name__ == '__main__':
    main()
