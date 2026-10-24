"""Stage the verified runtime snapshot inside the independent backend service root."""
import hashlib
import json
from pathlib import Path
import shutil

BACKEND_ROOT = Path(__file__).resolve().parents[1]

def prepare(source=None, destination=None):
    source = Path(source) if source is not None else BACKEND_ROOT.parent / "data"
    destination = Path(destination) if destination is not None else BACKEND_ROOT / "data"
    manifest_bytes = (source / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    identity = manifest["snapshot_id"]
    if not isinstance(identity, str) or len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("Invalid snapshot identity")
    relative = Path("processed") / (identity + ".json")
    snapshot_bytes = (source / relative).read_bytes()
    if hashlib.sha256(snapshot_bytes).hexdigest() != identity:
        raise ValueError("Snapshot checksum mismatch; refusing to package")
    (destination / "processed").mkdir(parents=True, exist_ok=True)
    # Only immutable runtime inputs are copied: no raw records, network or ingestion.
    shutil.copyfile(source / relative, destination / relative)
    (destination / "manifest.json").write_bytes(manifest_bytes)
    return identity

if __name__ == "__main__":
    print("Backend snapshot staged: " + prepare())
