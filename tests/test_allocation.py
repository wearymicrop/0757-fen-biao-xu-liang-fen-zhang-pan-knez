from app.pipeline import calculate


def test_common_window_account_values(clean):
    amounts = {r["account"]:r["kw"] for r in clean["allocation"]["accounts"]}
    assert amounts == {"厂房甲":"43.000","厂房乙":"80.000","仓配丙":"44.000"}


def test_dirty_held_meter_stays_unmapped(dirty):
    assert dirty["allocation"]["unmapped_w_sum"] == 108000
    assert "仓配临时" not in {r["account"] for r in dirty["allocation"]["accounts"]}


def test_same_account_combines_meter_contributions(clean_data):
    clean_data["mappings"][2]["account"] = "厂房甲"
    row = next(r for r in calculate(clean_data)["allocation"]["accounts"] if r["account"] == "厂房甲")
    assert row["meters"] == ["M-001","M-002"] and row["kw"] == "123.000"


def test_attribution_shows_source_mapping(clean):
    row = clean["allocation"]["meters"][0]
    assert [s["line"] for s in row["sources"]] == [26,30,34]
    assert row["mapping_sources"][0]["line"] == 1


def test_all_unmapped_held_outside_accounts(clean_data):
    clean_data["mappings"] = []
    result = calculate(clean_data)["allocation"]
    assert result["unmapped_w_sum"] == 501000 and result["accounts"] == []


def test_no_allocation_without_peak(clean_data):
    clean_data["readings"] = []
    assert calculate(clean_data)["allocation"]["assigned_w_sum"] is None
