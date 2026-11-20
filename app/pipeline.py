from app.contract import TABLES, STAGES
from app.errors import InputError
from app.manifest import canonical


def validate(data):
    if not isinstance(data, dict) or set(data) != set(TABLES) | {"config"}:
        raise InputError("INPUT_TABLES", "输入表或批次设置不齐")
    if not isinstance(data["config"], dict):
        raise InputError("INPUT_CONFIG", "批次设置有误")
    for name in TABLES:
        table = data[name]
        if not isinstance(table, list) or len(table) > 10000 or any(not isinstance(row, dict) for row in table):
            raise InputError("INPUT_ROWS", f"{name} 行格式有误或超过一万行")
    try:
        canonical(data)
    except (TypeError, ValueError) as error:
        raise InputError("INPUT_VALUES", "输入包含非标准 JSON 值") from error
    return data


def calculate(data, until=None):
    validate(data)
    result = {}
    for name, _, operation, _ in STAGES:
        result[name] = operation(data, result)
        if name == until:
            break
    return result
