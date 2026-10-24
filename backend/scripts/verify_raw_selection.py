"""Offline audit against preserved raw forecast responses, not normalized selection."""
import json
from pathlib import Path
from datetime import date
from app.analysis import decision, timestamp
from app.main import load_snapshot, DATA_DIR


def main():
    snapshot, manifest = load_snapshot()
    raw = []
    for request in manifest['requests']:
        if '/WINDFOR/' in request['url']:
            path = DATA_DIR / request['raw_file']
            import hashlib
            blob = path.read_bytes()
            assert hashlib.sha256(blob).hexdigest() == request['sha256']
            raw.extend(json.loads(blob))
    examples = []
    for day, cutoff, hour in [('2026-01-01','10:00',0),('2026-01-15','10:00',12),('2026-01-31','10:00',23),('2026-01-15','04:30',0)]:
        result = decision(snapshot,date.fromisoformat(day),cutoff)
        selected = result['observations'][hour]
        candidates = [r for r in raw if r['startTime']==selected['start_time'] and timestamp(r['publishTime'])<=timestamp(result['decision_timestamp'])]
        expected = max(candidates,key=lambda r:timestamp(r['publishTime']))
        assert selected['publish_time']==expected['publishTime']
        assert selected['forecast_mw']==expected['generation']
        examples.append(dict(decision_cutoff=result['decision_timestamp'], target=selected['start_time'], selected_publication=selected['publish_time'], forecast_mw=selected['forecast_mw']))
    print(json.dumps(examples,indent=2))

if __name__=='__main__':
    main()
