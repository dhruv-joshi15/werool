"""Check a running Vercel services router without modifying deployment settings."""
import argparse
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:3011')
    args = parser.parse_args()
    for path in ['/', '/decision-explorer', '/accuracy/2026-01-15']:
        with urlopen(Request(args.base_url + path, headers={'Accept': 'text/html'}), timeout=20) as response:
            body = response.read().decode()
            assert response.status == 200 and '<div id="root">' in body, (path, response.status)
            print('Frontend HTML and refresh:', path)
            if path == '/':
                scripts = re.findall(r'<script[^>]+src="([^"]+)"', body)
                assert scripts, 'Frontend page has no entry script'
                for script in scripts:
                    if script.startswith('/'):
                        with urlopen(Request(args.base_url + script, headers={'Accept': '*/*'}), timeout=20) as asset:
                            assert asset.status == 200 and 'text/html' not in asset.headers.get('Content-Type', ''), script
                            print('JavaScript asset preserved:', script)
    with urlopen(args.base_url + '/docs', timeout=20) as response:
        assert 'swagger-ui' in response.read().decode()
    with urlopen(args.base_url + '/openapi.json', timeout=20) as response:
        schema = json.load(response)
        assert '/api/v1/health' in schema['paths']
    for path in ['/api', '/api/does-not-exist', '/api/api/v1/health', '/api/v1/does-not-exist']:
        try:
            urlopen(args.base_url + path, timeout=20)
            raise AssertionError(f'{path}: API route was swallowed by frontend')
        except HTTPError as error:
            assert error.code == 404, (path, error.code)
            assert 'application/json' in error.headers.get('Content-Type', '')
            assert json.load(error)['detail'] == 'Not Found'
            print('Backend JSON 404 (no SPA fallback):', path)
    with urlopen(args.base_url + '/api/v1/health', timeout=20) as response:
        assert json.load(response)['dataset_ready'] is True
    print('Service routing, API prefix, snapshot readiness and SPA refresh checks passed.')

if __name__ == '__main__':
    main()
