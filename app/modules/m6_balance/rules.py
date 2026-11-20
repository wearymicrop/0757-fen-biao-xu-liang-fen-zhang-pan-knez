from app.evidence import issue
from app.units import demand_kw


def run(_data, previous):
    counts = previous["sampling"]["counts"]
    quality = counts["input"] - sum(counts[part] for part in ("accepted", "replay", "quarantined"))
    peak = previous["peak"]["peak"]
    issues = []
    if quality:
        issues.append(issue("READING_COUNT_DIFFERENCE"))
    if peak is None:
        return {"status": "NO_PEAK", "reading_difference": quality, "difference_w_sum": None,
                "assigned_kw": None, "unallocated_kw": None, "issues": issues}
    alloc = previous["allocation"]
    allocated, unmapped = alloc["assigned_w_sum"], alloc["unmapped_w_sum"]
    total = peak["w_sum"]
    submeter_total = sum(row["w_sum"] for row in alloc["meters"])
    residual = total - submeter_total
    unallocated = unmapped + residual
    difference = total - allocated - unallocated
    if residual < 0:
        issues.append(issue("NEGATIVE_RESIDUAL", *peak["sources"], *(src for row in alloc["meters"] for src in row["sources"])))
    if difference:
        issues.append(issue("POWER_DIFFERENCE"))
    warning = bool(previous["alignment"]["issues"] or previous["mapping"]["issues"] or counts["quarantined"])
    return {"status": "DIFFERENCE" if difference or quality else "REVIEW" if warning or issues else "MATCHED",
            "reading_difference": quality, "main_w_sum": total, "assigned_w_sum": allocated,
            "submeter_w_sum": submeter_total, "unmapped_w_sum": unmapped, "residual_w_sum": residual,
            "unallocated_w_sum": unallocated, "difference_w_sum": difference,
            "main_kw": demand_kw(total), "assigned_kw": demand_kw(allocated), "unallocated_kw": demand_kw(unallocated),
            "residual_kw": demand_kw(residual), "issues": issues}
