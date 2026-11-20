from app.evidence import issue


def run(_data, previous):
    sampling = previous["sampling"]
    windows = previous["alignment"]["windows"]
    main = sampling["main_meter"]
    valid = [window for window in windows if window["eligible"]]
    winner = min(valid, key=lambda row: (-row["meters"][main]["w_sum"], row["window"])) if valid else None
    peak = None if winner is None else {"window": winner["window"], "label": winner["label"], **winner["meters"][main]}
    series = [{"window": row["window"], "label": row["label"], "eligible": row["eligible"],
               "w_sum": row["meters"][main]["w_sum"], "kw": row["meters"][main]["kw"],
               "gaps": len(row["missing"])} for row in windows]
    individual = []
    for meter in sampling["meters"]:
        candidates = [row for row in windows if row["meters"][meter]["w_sum"] is not None]
        if not candidates:
            continue
        local = min(candidates, key=lambda row: (-row["meters"][meter]["w_sum"], row["window"]))
        at_peak = winner["meters"][meter]["kw"] if winner else None
        individual.append({"meter": meter, "window": local["window"], "label": local["label"],
                           "kw": local["meters"][meter]["kw"], "at_common_peak_kw": at_peak,
                           "sources": local["meters"][meter]["sources"]})
    return {"peak": peak, "eligible": len(valid), "excluded": len(windows) - len(valid), "series": series,
            "individual": individual, "issues": [] if winner else [issue("NO_COMMON_PEAK")]}
