from datetime import datetime, timezone

from app.errors import InputError
from app.reasons import REASONS


def timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("需要带偏移的日期时间")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("需要带偏移的日期时间")
    return parsed.astimezone(timezone.utc)


def key(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("标识不能为空")
    return value.strip()


def evidence(table, line, raw):
    return {"table": table, "line": line, "raw": raw}


def issue(code, *sources):
    return {"code": code, "label": REASONS[code], "sources": list(sources)}


def rows(data, table):
    for line, raw in enumerate(data[table], 1):
        yield raw, evidence(table, line, raw)


def interval(config):
    try:
        start, end = timestamp(config["start"]), timestamp(config["end"])
        if start >= end:
            raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise InputError("INVALID_WINDOW", "时段应含偏移且结束晚于开始") from error
    return start, end
