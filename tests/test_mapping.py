from app.pipeline import calculate


def test_half_open_version_boundary(clean):
    """TRAP-23：干净样例 M-001 恰在 09:00 切换。"""
    windows = clean["mapping"]["windows"]
    assert windows["2026-11-20T00:45:00+00:00"]["M-001"]["account"] == "厂房甲"
    assert windows["2026-11-20T01:00:00+00:00"]["M-001"]["account"] == "厂房丁"


def test_overlapping_maps_pending(dirty):
    """TRAP-25：脏样例 M-003 两版覆盖同一窗口。"""
    assert [r["code"] for r in dirty["mapping"]["issues"]] == ["MAP_OVERLAP","MAP_OVERLAP"]
    assert [r["line"] for r in dirty["mapping"]["issues"][0]["sources"]] == [4,5]


def test_full_window_assignments(clean, dirty):
    assert clean["mapping"]["assigned"] == 24 and dirty["mapping"]["assigned"] == 22


def test_midwindow_transition(clean_data):
    clean_data["mappings"][0]["end"] = clean_data["mappings"][1]["start"] = "2026-11-20T08:55:00+08:00"
    assert calculate(clean_data)["mapping"]["issues"][0]["code"] == "MAP_TRANSITION"


def test_missing_map_rows(clean_data):
    clean_data["mappings"].pop()
    items = calculate(clean_data)["mapping"]["issues"]
    assert len(items) == 8 and {row["code"] for row in items} == {"MAP_UNASSIGNED"}


def test_main_meter_cannot_be_billed_as_submeter(clean_data):
    clean_data["mappings"][0]["meter"] = "M-000"
    assert calculate(clean_data)["mapping"]["issues"][0]["code"] == "BAD_MAPPING"
