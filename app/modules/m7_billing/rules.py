from fractions import Fraction

from app.units import demand_kw


def charge_rows(entries, rate):
    exact = [Fraction(row["w_sum"] * rate, 3000) for row in entries]
    floor = [int(value) for value in exact]
    total = int(sum(exact) + Fraction(1, 2))
    order = sorted(range(len(entries)), key=lambda i: (-(exact[i] - floor[i]), entries[i]["account"] is None, entries[i]["account"] or ""))
    awards = set(order[:total - sum(floor)])
    rows = [{**row, "exact_cents": str(exact[i]), "tail_cent": int(i in awards), "amount_cents": floor[i] + (i in awards)}
            for i, row in enumerate(entries)]
    return rows, total


def run(_data, previous):
    peak = previous["peak"]["peak"]
    balance = previous["balance"]
    rate = previous["sampling"]["rate_cents_per_kw"]
    if not peak or balance["status"] == "DIFFERENCE" or balance["residual_w_sum"] < 0:
        return {"state": "held", "currency": "CNY", "rate_cents_per_kw": rate, "total_cents": None,
                "difference_cents": None, "lines": [], "issues": []}
    entries = [{**row, "state": "attributed"} for row in previous["allocation"]["accounts"]]
    unallocated = balance["unallocated_w_sum"]
    if unallocated:
        entries.append({"account": None, "w_sum": unallocated, "kw": demand_kw(unallocated), "state": "unallocated", "meters": []})
    lines, total = charge_rows(entries, rate)
    return {"state": "ready" if balance["status"] == "MATCHED" else "review", "window": peak["window"],
            "currency": "CNY", "rate_cents_per_kw": rate, "total_cents": total, "lines": lines,
            "difference_cents": total - sum(row["amount_cents"] for row in lines), "issues": []}
