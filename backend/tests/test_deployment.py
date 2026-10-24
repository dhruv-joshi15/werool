"""Deployment-only regressions: preserve the analysis and public API contract."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from scripts.prepare_deployment import prepare

ROOT = Path(__file__).resolve().parents[2]


def fixture_snapshot(path):
    blob = json.dumps({'forecasts': [], 'actuals': []}).encode()
    identity = hashlib.sha256(blob).hexdigest()
    (path / 'processed').mkdir(parents=True)
    (path / 'processed' / f'{identity}.json').write_bytes(blob)
    (path / 'manifest.json').write_text(json.dumps({'snapshot_id': identity}))
    (path / 'raw').mkdir()
    (path / 'raw' / 'not-for-runtime.json').write_text('[]')
    return identity


def test_snapshot_packaging_is_minimal_and_checks_sums(tmp_path):
    source, destination = tmp_path / 'source', tmp_path / 'bundle'
    identity = fixture_snapshot(source)
    assert prepare(source, destination) == identity
    assert sorted(str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()) == [
        'manifest.json', f'processed/{identity}.json'
    ]
    (source / 'processed' / f'{identity}.json').write_text('corrupt')
    with pytest.raises(ValueError, match='checksum'):
        prepare(source, destination)


def test_real_snapshot_works_in_isolated_service_bundle(tmp_path):
    bundle = tmp_path / 'isolated-backend'
    shutil.copytree(ROOT / 'backend' / 'app', bundle / 'app', ignore=shutil.ignore_patterns('__pycache__'))
    prepare(ROOT / 'data', bundle / 'data')
    # No repository-root data directory or working-directory assumptions are available.
    script = '''
import sys
sys.path.insert(0, sys.argv[1])
from fastapi.testclient import TestClient
from app.main import app, DATA_DIR
from pathlib import Path
assert DATA_DIR == Path(sys.argv[1]) / 'data'
client = TestClient(app)
assert client.get('/api/v1/health').json()['dataset_ready'] is True
response = client.get('/api/v1/evaluation?date=2026-01-31')
assert response.status_code == 200
assert response.json()['delivery_date'] == '2026-02-01'
assert response.json()['metrics']['matched_count'] == 24
assert client.get('/api/not-a-route').status_code == 404
assert client.get('/v1/health').status_code == 404
assert client.get('/api/api/v1/health').status_code == 404
'''
    result = subprocess.run([sys.executable, '-I', '-c', script, str(bundle)], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_checkout_prefers_source_snapshot_over_previous_build_copy(tmp_path, monkeypatch):
    import app.main as main
    source = tmp_path / 'data'
    bundled = tmp_path / 'backend' / 'data'
    fixture_snapshot(source)
    fixture_snapshot(bundled)
    monkeypatch.setattr(main, '__file__', str(tmp_path / 'backend' / 'app' / 'main.py'))
    assert main.default_data_dir() == source
