from app.modules.m6_balance.rules import run as reconcile
from app.pipeline import calculate


def test_clean_exact_balance(clean):
    total = clean["balance"]
    assert (total["main_w_sum"],total["assigned_w_sum"],total["unallocated_w_sum"],total["difference_w_sum"]) == (540001,501000,39001,0)


def test_dirty_residual_and_unmapped(dirty):
    total = dirty["balance"]
    assert (total["main_kw"],total["assigned_kw"],total["unallocated_kw"],total["residual_kw"]) == ("174.000","132.000","42.000","6.000")


def test_raw_input_count_reconciles(dirty):
    assert dirty["sampling"]["counts"] == dict(input=101,accepted=94,replay=1,quarantined=6)
    assert dirty["balance"]["reading_difference"] == 0


def test_negative_residual_review(clean_data):
    for row in clean_data["readings"]:
        if row["meter"] == "M-003": row.update(value="200",unit="kW")
    result = calculate(clean_data)["balance"]
    assert result["residual_w_sum"] < 0 and result["issues"][0]["code"] == "NEGATIVE_RESIDUAL"


def test_injected_reading_count_difference(clean):
    clean["sampling"]["counts"]["accepted"] -= 1
    assert reconcile(None,clean)["status"] == "DIFFERENCE"


def test_matched_and_review(clean, dirty):
    assert clean["balance"]["status"] == "MATCHED" and dirty["balance"]["status"] == "REVIEW"
