from app.modules.m7_billing.rules import charge_rows
from app.pipeline import calculate


def test_clean_bill_exact_cents(clean):
    assert clean["billing"]["total_cents"] == 244260 and clean["billing"]["state"] == "ready"


def test_dirty_bill_draft(dirty):
    assert dirty["billing"]["total_cents"] == 236118 and dirty["billing"]["state"] == "review"
    assert dirty["billing"]["lines"][-1]["amount_cents"] == 56994


def test_cent_tail_conservation():
    """TRAP-24：两个半分金额只应分到 1 分。"""
    lines,total = charge_rows([{"account":"B","w_sum":1500},{"account":"A","w_sum":1500}],1)
    assert total == 1 and [r["amount_cents"] for r in lines] == [0,1]


def test_no_billing_on_negative_physical_residual(clean_data):
    for row in clean_data["readings"]:
        if row["meter"]=="M-003": row.update(value="200",unit="kW")
    result = calculate(clean_data)["billing"]
    assert result["state"] == "held" and result["lines"] == [] and result["total_cents"] is None


def test_zero_rate_remains_valid(clean_data):
    clean_data["config"]["rate_cents_per_kw"] = 0
    assert calculate(clean_data)["billing"]["total_cents"] == 0


def test_exact_fraction_preserved(clean):
    last = clean["billing"]["lines"][-1]
    assert last["exact_cents"] == "52924357/3000" and clean["billing"]["difference_cents"] == 0
