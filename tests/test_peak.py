from app.pipeline import calculate


def test_clean_official_peak(clean):
    assert clean["peak"]["peak"]["window"] == "2026-11-20T00:30:00+00:00"
    assert clean["peak"]["peak"]["w_sum"] == 540001


def test_incomplete_higher_main_does_not_win(dirty):
    assert dirty["peak"]["peak"]["kw"] == "174.000"
    assert dirty["peak"]["series"][2]["kw"] == "180.000" and not dirty["peak"]["series"][2]["eligible"]


def test_ties_take_earliest_window(clean_data):
    clean_data["readings"] = [{**row,"value":"180000","unit":"W"} if row["meter"]=="M-000" else row for row in clean_data["readings"]]
    assert calculate(clean_data)["peak"]["peak"]["label"] == "11/20 08:00"


def test_independent_peak_never_used_for_attribution(clean):
    individual = clean["peak"]["individual"][0]
    assert (individual["label"],individual["kw"],individual["at_common_peak_kw"]) == ("11/20 08:45","90.000","43.000")


def test_all_windows_ineligible(clean_data):
    clean_data["readings"] = []
    result = calculate(clean_data)["peak"]
    assert result["peak"] is None and result["excluded"] == 8 and result["issues"][0]["code"] == "NO_COMMON_PEAK"


def test_counts_excluded_windows(dirty):
    assert (dirty["peak"]["eligible"],dirty["peak"]["excluded"]) == (6,2)
