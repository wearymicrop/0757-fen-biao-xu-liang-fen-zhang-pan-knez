from collections import defaultdict

from app.evidence import issue, key, rows, timestamp
from app.timegrid import WINDOW, window_starts


def run(data, previous):
    limits = previous["sampling"]
    start, end = timestamp(limits["start"]), timestamp(limits["end"])
    roster = set(limits["meters"])
    versions, issues = defaultdict(list), []
    for row, source in rows(data, "mappings"):
        try:
            meter, account, version = (key(row[field]) for field in ("meter", "account", "version"))
            begin, finish = timestamp(row["start"]), timestamp(row["end"])
            if meter not in roster or begin >= finish:
                raise ValueError
        except (KeyError, ValueError, OverflowError):
            issues.append(issue("BAD_MAPPING", source))
            continue
        versions[meter].append({"account": account, "version": version, "source": source, "start": begin, "end": finish})
    windows = {}
    for instant in window_starts(start, end):
        finish = instant + WINDOW
        window = {}
        for meter in limits["meters"]:
            matches = [row for row in versions[meter] if row["start"] < finish and row["end"] > instant]
            sources = [row["source"] for row in matches]
            code = None
            if not matches:
                code = "MAP_UNASSIGNED"
            elif len(matches) == 1 and matches[0]["start"] <= instant and matches[0]["end"] >= finish:
                window[meter] = {"account": matches[0]["account"], "version": matches[0]["version"],
                                 "sources": sources, "state": "assigned"}
            else:
                spans = sorted((max(row["start"], instant), min(row["end"], finish)) for row in matches)
                overlap = any(current[0] < previous[1] for previous, current in zip(spans, spans[1:]))
                code = "MAP_OVERLAP" if overlap else "MAP_TRANSITION"
            if code:
                window[meter] = {"account": None, "version": None, "sources": sources, "state": code}
                issues.append({**issue(code, *sources), "meter": meter, "window": instant.isoformat()})
        windows[instant.isoformat()] = window
    return {"windows": windows, "assigned": sum(r["state"] == "assigned" for group in windows.values() for r in group.values()), "issues": issues}
