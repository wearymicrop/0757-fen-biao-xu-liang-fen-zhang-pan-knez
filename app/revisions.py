"""账单修订：在不触碰已签归档的前提下合并迟到读数与归属更正。

修订本身按（旧账单 + 规范化更正）内容寻址，同一更正重复提交或发布失败
重试都只会回到同一条修订；只有对平且旧归档仍可读取时才能发布。
"""
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.errors import InputError
from app.manifest import sha256
from app.pipeline import validate
from app.runs import archive_run


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    late_readings: list[dict[str, Any]] = []
    mapping_replacements: list[dict[str, Any]] = []
    note: str | None = None


class RevisionRequest(Correction):
    base_run_id: str


def _as_row_list(value, code):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise InputError(code, "更正内容应为对象数组")
    return value


def check_correction(payload: Correction):
    late = _as_row_list(payload.late_readings, "REVISION_BAD_ROW")
    mappings = _as_row_list(payload.mapping_replacements, "REVISION_BAD_ROW")
    if not late and not mappings:
        raise InputError("REVISION_EMPTY", "修订至少包含一条迟到读数或归属更正")
    reading_keys = {"gateway", "meter", "at", "value", "unit"}
    mapping_keys = {"meter", "account", "version", "start", "end"}
    for row in late:
        if set(row) != reading_keys:
            raise InputError("REVISION_BAD_ROW", "迟到读数字段须与 readings 表一致")
    for row in mappings:
        if set(row) != mapping_keys:
            raise InputError("REVISION_BAD_ROW", "归属更正字段须与 mappings 表一致")
    note = payload.note
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise InputError("REVISION_BAD_ROW", "修订说明不能为空字符串")
    return {"late_readings": late, "mapping_replacements": mappings,
            "note": note.strip() if note else None}


def merge_correction(base_input: dict, correction: dict):
    """合并出修订批次：迟到读数追加，归属更正按表号整表替换。

    被替换的旧映射行原样保留在依据里，旧输入本身永不改写。
    """
    readings = [*base_input["readings"], *correction["late_readings"]]
    replaced_meters = {row["meter"] for row in correction["mapping_replacements"]}
    replaced_basis = [row for row in base_input["mappings"] if row["meter"] in replaced_meters]
    mappings = [row for row in base_input["mappings"] if row["meter"] not in replaced_meters]
    mappings.extend(correction["mapping_replacements"])
    merged = {**base_input, "readings": readings, "mappings": mappings}
    validate(merged)
    return merged, replaced_basis


def _billing_lines(result):
    return {row["account"]: row for row in result["billing"]["lines"]}


def _peak_brief(result):
    peak = result["peak"]["peak"]
    if peak is None:
        return {"window": None, "label": "无完整公共窗口", "kw": None}
    return {"window": peak["window"], "label": peak["label"], "kw": peak["kw"],
            "sources": peak["sources"]}


def build_comparison(old_result: dict, new_result: dict):
    old_lines, new_lines = _billing_lines(old_result), _billing_lines(new_result)
    accounts = []
    for account in sorted(set(old_lines) | set(new_lines), key=lambda value: (value is None, value or "")):
        before, after = old_lines.get(account), new_lines.get(account)
        accounts.append({
            "account": account,
            "before_cents": None if before is None else before["amount_cents"],
            "after_cents": None if after is None else after["amount_cents"],
            "delta_cents": (0 if after is None else after["amount_cents"]) - (0 if before is None else before["amount_cents"]),
            "before_kw": None if before is None else before["kw"],
            "after_kw": None if after is None else after["kw"],
        })
    return {
        "peak": {"before": _peak_brief(old_result), "after": _peak_brief(new_result),
                 "moved": _peak_brief(old_result)["window"] != _peak_brief(new_result)["window"]},
        "accounts": accounts,
        "total": {"before_cents": old_result["billing"]["total_cents"],
                  "after_cents": new_result["billing"]["total_cents"],
                  "delta_cents": (new_result["billing"]["total_cents"] or 0) - (old_result["billing"]["total_cents"] or 0)},
        "unallocated": {
            "before_kw": old_result["balance"]["unallocated_kw"],
            "after_kw": new_result["balance"]["unallocated_kw"],
            "before_w_sum": old_result["balance"]["unallocated_w_sum"],
            "after_w_sum": new_result["balance"]["unallocated_w_sum"],
        },
        "balance": {"before": old_result["balance"]["status"], "after": new_result["balance"]["status"]},
    }


def _adopted_basis(correction, replaced_basis, old_record, new_run_id):
    return {
        "late_readings": correction["late_readings"],
        "mapping_replacements": correction["mapping_replacements"],
        "replaced_mappings": replaced_basis,
        "note": correction["note"],
        "old_run_id": old_record["id"],
        "new_run_id": new_run_id,
        "rule_version": old_record["manifest"]["rule_version"],
    }


def revision_identity(base_run_id: str, correction: dict):
    return sha256(["revision", base_run_id, correction])


def create_revision(store, base_run_id: str, payload: Correction):
    correction = check_correction(payload)
    old_record = store.runs.find(base_run_id)
    if old_record is None:
        raise InputError("REVISION_BASE_MISSING", "旧账单归档已丢失，不能发起修订", 409)
    if old_record["result"]["billing"]["state"] == "held":
        raise InputError("REVISION_BASE_NOT_SIGNED", "原账单未达到可签发状态，不能作为修订底稿", 422)
    digest = revision_identity(base_run_id, correction)
    existing = store.revisions.find(digest)
    if existing is not None:
        return existing, True
    merged, replaced_basis = merge_correction(old_record["input"], correction)
    new_run = archive_run(store.runs, merged, None)
    new_result = new_run["result"]
    comparison = build_comparison(old_record["result"], new_result)
    record = {
        "id": digest,
        "state": "draft",
        "base_run_id": base_run_id,
        "new_run_id": new_run["id"],
        "correction": correction,
        "comparison": comparison,
        "basis": _adopted_basis(correction, replaced_basis, old_record, new_run["id"]),
        "publishable": (new_result["balance"]["status"] == "MATCHED"
                        and new_result["billing"]["state"] == "ready"),
        "blockers": _publish_blockers(old_record, new_result),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "published_at": None,
    }
    # 内容寻址 + 插入忽略：并发的同一更正只会落一行，其余线程回读同一记录。
    return store.revisions.save(record)


def _publish_blockers(old_record, new_result):
    blockers = []
    if new_result["balance"]["status"] != "MATCHED":
        blockers.append({"code": "REVISION_NOT_PUBLISHABLE",
                         "message": f"功率勾稽未对平：{new_result['balance']['status']}"})
    if new_result["billing"]["state"] != "ready":
        blockers.append({"code": "REVISION_NOT_PUBLISHABLE",
                         "message": f"新账单未达可签发状态：{new_result['billing']['state']}"})
    if new_result["balance"]["reading_difference"]:
        blockers.append({"code": "REVISION_NOT_PUBLISHABLE", "message": "原始读数计数存在差异"})
    if old_record is None:
        blockers.append({"code": "REVISION_BASE_MISSING", "message": "旧账单归档已丢失"})
    return blockers


def publish_revision(store, revision_id: str):
    revision = store.revisions.get(revision_id)
    # 发布（含对已发布版本的重复调用）前都重新核对旧归档仍在、新批次仍对平，
    # 任一不满足即拒绝；旧据缺失时连已发布状态也不能作为免核对理由。
    old_record = store.runs.find(revision["base_run_id"])
    if old_record is None:
        raise InputError("REVISION_BASE_MISSING", "旧账单归档已丢失，禁止发布", 409)
    new_record = store.runs.find(revision["new_run_id"])
    if new_record is None:
        raise InputError("REVISION_BASE_MISSING", "修订批次归档缺失，禁止发布", 409)
    if revision["state"] == "published":
        return revision
    blockers = _publish_blockers(old_record, new_record["result"])
    if blockers or not revision["publishable"]:
        raise InputError("REVISION_NOT_PUBLISHABLE", "修订尚未对平，不能发布为唯一新账单", 422)
    return store.revisions.mark_published(revision_id)


def export_bundle(store, revision_id: str):
    revision = store.revisions.get(revision_id)
    old_record = store.runs.get(revision["base_run_id"])
    new_record = store.runs.get(revision["new_run_id"])
    return {
        "schema": "bill-revision",
        "revision": revision,
        "old_signed_run": old_record,
        "revised_run": new_record,
        "evidence": {
            "late_readings": revision["correction"]["late_readings"],
            "mapping_replacements": revision["correction"]["mapping_replacements"],
            "replaced_mappings": revision["basis"]["replaced_mappings"],
            "correction_sha256": sha256(revision["correction"]),
            "merged_input_sha256": new_record["manifest"]["input_sha256"],
            "old_input_sha256": old_record["manifest"]["input_sha256"],
        },
    }
