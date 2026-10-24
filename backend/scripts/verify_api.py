"""Smoke-test a running backend and save actual responses for the frontend handoff."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://localhost:8001')
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'docs'/'api-examples.json')
    args=parser.parse_args()
    paths={
        'health':'/api/v1/health',
        'metadata':'/api/v1/metadata',
        'decision':'/api/v1/decision?date=2026-01-15&cutoff=10:00',
        'evaluation':'/api/v1/evaluation?date=2026-01-31&cutoff=10:00',
        'accuracy':'/api/v1/accuracy?from=2026-01-01&to=2026-01-31&cutoff=10:00',
        'forecast_vintages':'/api/v1/forecast-vintages?start_time=2026-02-01T00:00:00Z',
    }
    results={}
    for name,path in paths.items():
        with urlopen(args.base_url+path,timeout=20) as response:
            assert response.status==200
            results[name]=dict(path=path,status=response.status,response=json.load(response))
        print(f'200 {path}')
    assert results['health']['response']['dataset_ready'] is True
    assert results['metadata']['response']['actual_interval_minutes']==30
    assert all('actual_mw' not in row for row in results['decision']['response']['observations'])
    assert results['evaluation']['response']['delivery_date']=='2026-02-01'
    summary=results['accuracy']['response']['metrics']
    expected=json.loads((Path(__file__).resolve().parents[2]/'docs'/'snapshot-summary.json').read_text())
    assert summary==expected['metrics'],(summary,expected['metrics'])
    assert summary['matched_count']==summary['expected_count']==744
    assert results['health']['response']['snapshot_id']==expected['snapshot_id']
    for daily in results['accuracy']['response']['daily']:
        for row in daily['observations']:
            assert row['publish_time']<=daily['decision_timestamp']
    try:
        urlopen(args.base_url+'/api/v1/decision?date=2026-02-01',timeout=10)
        raise AssertionError('Invalid request accepted')
    except HTTPError as error:
        assert error.code==422
        results['invalid_date']=dict(path='/api/v1/decision?date=2026-02-01',status=error.code,response=json.load(error))
    args.output.write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    print('Snapshot identity, period metrics, 744/744 coverage, outcome exclusion and publication cutoffs verified.')

if __name__=='__main__':
    main()
