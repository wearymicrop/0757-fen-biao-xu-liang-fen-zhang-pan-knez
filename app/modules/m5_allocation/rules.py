from collections import defaultdict

from app.units import demand_kw


def run(_data, previous):
    peak = previous["peak"]["peak"]
    if peak is None:
        return {"accounts": [], "meters": [], "assigned_w_sum": None, "unmapped_w_sum": None, "issues": []}
    time = peak["window"]
    mapping = previous["mapping"]["windows"][time]
    aligned = next(row["meters"] for row in previous["alignment"]["windows"] if row["window"] == time)
    accounts, meters = defaultdict(list), []
    for meter, relation in mapping.items():
        reading = aligned[meter]
        row = {"meter": meter, "account": relation["account"], "mapping_state": relation["state"],
               "version": relation["version"], "w_sum": reading["w_sum"], "kw": reading["kw"],
               "sources": reading["sources"], "mapping_sources": relation["sources"]}
        meters.append(row)
        accounts[relation["account"]].append(row)
    unmapped = sum(row["w_sum"] for row in accounts.pop(None, []))
    groups = []
    for account, members in sorted(accounts.items()):
        total = sum(row["w_sum"] for row in members)
        groups.append({"account": account, "w_sum": total, "kw": demand_kw(total), "meters": [row["meter"] for row in members]})
    return {"window": time, "accounts": groups, "meters": meters,
            "assigned_w_sum": sum(row["w_sum"] for row in groups), "unmapped_w_sum": unmapped, "issues": []}
