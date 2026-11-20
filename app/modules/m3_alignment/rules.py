from app.evidence import issue, timestamp
from app.timegrid import STEP, window_label, window_starts
from app.units import demand_kw


def run(_data, previous):
    sampling = previous["sampling"]
    start, end = timestamp(sampling["start"]), timestamp(sampling["end"])
    lookup = {(row["meter"], row["timestamp"]): row for row in sampling["samples"]}
    conflicts = {(row["meter"], row["timestamp"]): row["sources"] for row in sampling["conflicts"]}
    windows, issues = [], []
    for time in window_starts(start, end):
        timestamps = [(time + increment * STEP).isoformat() for increment in range(3)]
        aligned, missing = {}, []
        for meter in [sampling["main_meter"], *sampling["meters"]]:
            present = [lookup[meter, stamp] for stamp in timestamps if (meter, stamp) in lookup]
            absent = [stamp for stamp in timestamps if (meter, stamp) not in lookup]
            missing.extend({"meter": meter, "timestamp": stamp, "sources": conflicts.get((meter, stamp), [])} for stamp in absent)
            total = sum(row["w"] for row in present) if not absent else None
            aligned[meter] = {"w_sum": total, "kw": demand_kw(total) if total is not None else None,
                              "sources": [row["source"] for row in present], "missing": absent}
        key = time.isoformat()
        if missing:
            issues.append({**issue("WINDOW_GAP", *(source for gap in missing for source in gap["sources"])),
                           "window": key, "missing": missing})
        windows.append({"window": key, "label": window_label(time), "eligible": not missing, "meters": aligned, "missing": missing})
    return {"windows": windows, "eligible": sum(row["eligible"] for row in windows),
            "missing_slots": sum(len(row["missing"]) for row in windows), "issues": issues}
