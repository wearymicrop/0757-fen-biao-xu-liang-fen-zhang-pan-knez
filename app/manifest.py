import hashlib
import json
from datetime import datetime, timezone

from app.settings import PROJECT, RULE_VERSION


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha256(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identity(data, sample):
    return sha256([PROJECT, RULE_VERSION, sample, data])


def make_manifest(data, sample, digest, elapsed_ms):
    return {
        "digest": digest,
        "input_sha256": sha256(data),
        "rule_version": RULE_VERSION,
        "project": PROJECT,
        "sample": sample,
        "elapsed_ms": elapsed_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
