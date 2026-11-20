from collections import defaultdict
from datetime import timedelta

from app.errors import InputError
from app.evidence import interval, issue, key, rows, timestamp
from app.timegrid import STEP, WINDOW
from app.units import watts


def configuration(raw):
    start, end = interval(raw)
    try:
        if start.minute % 15 or end.minute % 15 or start.second or end.second or start.microsecond or end.microsecond:
            raise ValueError
        if not isinstance(raw["meters"], list):
            raise ValueError
        site, main = key(raw["site"]), key(raw["main_meter"])
        meters = [key(value) for value in raw["meters"]]
        rate = raw["rate_cents_per_kw"]
        if not meters or len(set(meters)) != len(meters) or main in meters or type(rate) is not int or not 0 <= rate <= 10**7:
            raise ValueError
        if ((end - start) // WINDOW) * (len(meters) + 1) > 15000:
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise InputError("BAD_CONFIG", "表册、费率或十五分钟批次设置有误") from error
    return start, end, {"site": site, "main_meter": main, "meters": sorted(meters), "rate_cents_per_kw": rate}


def calibrations(data):
    candidates, issues = defaultdict(list), []
    for raw, source in rows(data, "gateways"):
        try:
            candidates[key(raw["gateway"])].append(source)
        except (KeyError, ValueError):
            issues.append(issue("BAD_GATEWAY", source))
    offsets = {}
    for gateway, sources in sorted(candidates.items()):
        value = sources[0]["raw"].get("offset_seconds")
        if len(sources) > 1:
            issues.append(issue("GATEWAY_CONFLICT", *sources))
        elif type(value) is not int or not -900 <= value <= 900:
            issues.append(issue("BAD_GATEWAY", *sources))
        else:
            offsets[gateway] = {"offset_seconds": value, "source": sources[0]}
    return offsets, issues


def run(data, _previous):
    start, end, config = configuration(data["config"])
    roster = {config["main_meter"], *config["meters"]}
    offsets, issues = calibrations(data)
    by_slot, dispositions, last = defaultdict(list), {}, {}
    for row, source in rows(data, "readings"):
        code = None
        try:
            meter, gateway = key(row["meter"]), key(row["gateway"])
            instant = timestamp(row["at"])
            value = watts(row["value"], row["unit"])
        except (KeyError, TypeError, ValueError, OverflowError):
            code = "BAD_READING"
        else:
            if meter not in roster:
                code = "UNKNOWN_METER"
            elif gateway not in offsets:
                code = "UNKNOWN_GATEWAY"
            else:
                bias = offsets[gateway]["offset_seconds"]
                try:
                    instant -= timedelta(seconds=bias)
                except OverflowError:
                    code = "BAD_READING"
                else:
                    if not start <= instant < end:
                        code = "OUTSIDE_WINDOW"
                    elif (instant - start) % STEP:
                        code = "OFF_GRID"
        if code:
            dispositions[source["line"]] = "quarantined"
            issues.append(issue(code, source))
            continue
        late = meter in last and instant < last[meter]
        last[meter] = max(last.get(meter, instant), instant)
        by_slot[meter, instant.isoformat()].append({"w": value, "source": source, "late": late, "offset_seconds": bias})
    samples, conflicts, replays = [], [], []
    for (meter, instant), candidates in sorted(by_slot.items()):
        sources = [row["source"] for row in candidates]
        if len({row["w"] for row in candidates}) > 1:
            issues.append(issue("REPLAY_CONFLICT", *sources))
            for source in sources:
                dispositions[source["line"]] = "quarantined"
            conflicts.append({"meter": meter, "timestamp": instant, "sources": sources})
            continue
        kept = candidates[0]
        dispositions[kept["source"]["line"]] = "accepted"
        samples.append({"meter": meter, "timestamp": instant, **kept})
        if kept["late"]:
            issues.append(issue("LATE_READING", kept["source"]))
        if len(sources) > 1:
            for source in sources[1:]:
                dispositions[source["line"]] = "replay"
            replays.append({"meter": meter, "timestamp": instant, "sources": sources})
    counts = {"input": len(data["readings"]), **{state: list(dispositions.values()).count(state) for state in ("accepted", "replay", "quarantined")}}
    return {**config, "start": start.isoformat(), "end": end.isoformat(), "counts": counts,
            "calibrations": offsets, "samples": samples, "conflicts": conflicts, "replays": replays,
            "late": sum(row["late"] for row in samples), "issues": issues}
