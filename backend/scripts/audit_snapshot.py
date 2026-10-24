"""Offline audit of every default-cutoff selection against preserved source records."""
from collections import defaultdict, Counter
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from app.analysis import decision, timestamp
from app.main import DATA_DIR, load_snapshot


def main():
    snapshot, manifest = load_snapshot()
    raw = defaultdict(list)
    for request in manifest['requests']:
        blob = (DATA_DIR / request['raw_file']).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == request['sha256']
        dataset = 'WINDFOR' if '/WINDFOR/' in request['url'] else 'FUELHH'
        raw[dataset].extend(json.loads(blob))
    forecasts, actuals = defaultdict(list), defaultdict(set)
    for row in raw['WINDFOR']:
        forecasts[row['startTime']].append(row)
    for row in raw['FUELHH']:
        if row['fuelType'] == 'WIND':
            actuals[row['startTime']].add(row['generation'])
    count = 0
    for offset in range(31):
        day = date(2026, 1, 1) + timedelta(days=offset)
        result = decision(snapshot, day, '10:00', True)
        assert result['delivery_date'] == (day+timedelta(days=1)).isoformat()
        assert len(result['observations']) == 24
        for selected in result['observations']:
            candidates = [row for row in forecasts[selected['start_time']] if timestamp(row['publishTime']) <= timestamp(result['decision_timestamp'])]
            expected = max(candidates, key=lambda r: timestamp(r['publishTime'])) if candidates else None
            assert selected['publish_time'] == (expected['publishTime'] if expected else None)
            assert selected['forecast_mw'] == (expected['generation'] if expected else None)
            assert actuals[selected['start_time']] == {selected['actual_mw']}
            count += 1
    def spacing(rows):
        targets = sorted({timestamp(row['start_time']) for row in rows})
        return dict(Counter(str(int((b-a).total_seconds()/60)) for a,b in zip(targets,targets[1:])))
    report = dict(snapshot_id=manifest['snapshot_id'], source_datasets=['WINDFOR','FUELHH'], checked_default_cutoff_selections=count, checked_delivery_days=31, forecast_target_spacing_minutes=spacing(snapshot['forecasts']), actual_target_spacing_minutes=spacing(snapshot['actuals']), raw_requests_verified=len(manifest['requests']), row_counts=manifest['row_counts'], quality=manifest['quality'])
    destination = Path(__file__).resolve().parents[2]/'docs'/'snapshot-audit.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
