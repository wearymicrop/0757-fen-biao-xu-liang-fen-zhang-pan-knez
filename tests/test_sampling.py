def test_clean_reading_counts(clean):
    assert clean["sampling"]["counts"] == dict(input=96,accepted=96,replay=0,quarantined=0)


def test_normalized_replay(dirty):
    """TRAP-06：脏样例全角千位重传。"""
    replay = dirty["sampling"]["replays"][0]
    assert [r["raw"]["value"] for r in replay["sources"]] == ["74000", "７４,０００"]


def test_gateway_and_zone_normalization(dirty):
    """TRAP-11：脏样例 Z 与 +08:00 落于同一格点。"""
    replay = dirty["sampling"]["replays"][0]
    assert replay["timestamp"] == "2026-11-20T00:25:00+00:00"
    assert [r["raw"]["at"] for r in replay["sources"]] == ["2026-11-20T08:24:30+08:00","2026-11-20T00:24:30Z"]


def test_late_sample_still_counted(dirty):
    """TRAP-13：脏样例拖到批尾的第一条分表记录。"""
    assert dirty["sampling"]["late"] == 1
    assert [(r["meter"],r["timestamp"]) for r in dirty["sampling"]["samples"] if r["late"]] == [("M-001","2026-11-20T00:00:00+00:00")]


def test_sentinel_quarantined(dirty):
    """TRAP-07：脏样例读数的空值哨兵。"""
    assert [r["sources"][0]["raw"]["value"] for r in dirty["sampling"]["issues"] if r["code"]=="BAD_READING"] == ["N/A"]


def test_conflicting_replay_not_last_write(dirty):
    """TRAP-14：脏样例同表同刻不同值。"""
    row = dirty["sampling"]["conflicts"][0]
    assert row["meter"] == "M-002" and len(row["sources"]) == 2
    assert not any(r["meter"]==row["meter"] and r["timestamp"]==row["timestamp"] for r in dirty["sampling"]["samples"])


def test_mixed_power_units(clean):
    """TRAP-15：干净样例按格点混用 W 和 kW。"""
    rows = [r for r in clean["sampling"]["samples"] if r["meter"]=="M-000"][:3]
    assert [r["source"]["raw"]["unit"] for r in rows] == ["W","kW","W"]
    assert [r["w"] for r in rows] == [119000,120000,121000]
