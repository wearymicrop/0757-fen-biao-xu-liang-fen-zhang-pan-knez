from app.pipeline import calculate


def test_all_regular_windows(clean):
    assert clean["alignment"]["eligible"] == 8 and clean["alignment"]["missing_slots"] == 0


def test_first_window_exact_sum(clean):
    window = clean["alignment"]["windows"][0]
    assert window["meters"]["M-000"]["w_sum"] == 360000 and window["label"] == "11/20 08:00"


def test_conflict_evidence_in_gap(dirty):
    window = dirty["alignment"]["windows"][2]
    assert not window["eligible"] and window["meters"]["M-002"]["w_sum"] is None
    assert len(window["missing"][0]["sources"]) == 2


def test_gap_does_not_fill_zero(dirty):
    window = dirty["alignment"]["windows"][-1]
    assert window["missing"] == [{"meter":"M-003","timestamp":"2026-11-20T01:55:00+00:00","sources":[]}]


def test_missing_slots_total(dirty):
    assert dirty["alignment"]["eligible"] == 6 and dirty["alignment"]["missing_slots"] == 2


def test_cross_midnight_and_year(clean_data):
    clean_data["config"].update(start="2026-12-31T23:45:00+08:00",end="2027-01-01T00:15:00+08:00")
    assert [r["label"] for r in calculate(clean_data)["alignment"]["windows"]] == ["12/31 23:45","01/01 00:00"]
