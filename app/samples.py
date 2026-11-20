import json

from app.errors import InputError
from app.settings import ROOT

SAMPLE_NAMES = {"clean": "干净样例", "dirty": "脏样例"}


def load_sample(name):
    if name not in SAMPLE_NAMES:
        raise InputError("UNKNOWN_SAMPLE", "找不到指定样例", 404)
    return json.loads((ROOT / "sample_data" / f"{name}.json").read_text(encoding="utf-8-sig"))
