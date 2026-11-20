# 接口与证据

- `GET /api/health` 返回项目和规则版本。
- `GET /api/{模块}/{样例}` 单独计算到该阶段。模块与样例见深度登记。
- `POST /api/runs` 接收 `{"sample":"clean"}`、`{"sample":"dirty"}` 或 `{"data":{…}}`，返回完整计算和归档 ID。
- `GET /api/runs/{id}` 查询不可变归档。`POST /api/runs/{id}/rerun` 用归档输入与当前规则运行。相同规则与来源复用原记录。
- `GET /api/runs/{id}/export` 下载 JSON 证据。内含批次设置、各输入表、原行号、各阶段计算及规则版本。

## 账单修订（月末更正）

已签账单所在 run 永久不可变，更正只生成内容寻址的修订记录，旧版在核对完成前不会被替换。

- `POST /api/revisions` 接收 `{"base_run_id","late_readings":[…readings 行…],"mapping_replacements":[…mappings 行…],"note"?}`。迟到读数追加到原批次；归属更正按表号整表替换，被替换行原样进入依据。返回修订草案与新旧峰窗、账户差额、未分配量差额对照。同 `(base_run_id, 规范化更正)` 重复提交或失败重试只回到同一条记录（`reused=true`），不新增修订。
- `GET /api/revisions/{id}` 查询修订；`GET /api/revisions/base/{base_run_id}` 列出同一底稿下的全部修订。
- `POST /api/revisions/{id}/publish` 发布闸门：旧归档与修订批次归档均可读、功率勾稽 `MATCHED`、账单 `ready` 才发布；任一不满足返回 422/409 且状态保持 `draft`。同一底稿由部分唯一索引保证至多一条 `published`，竞争发布返回 409 `REVISION_ALREADY_PUBLISHED`。对已发布修订重复调用是空操作，但仍会先复核旧据未丢失。
- `GET /api/revisions/{id}/export` 下载证据包（`schema=bill-revision`）：含修订记录、已签旧版完整归档 `old_signed_run`、修订批次 `revised_run`、补录读数、归属更正、被替换旧映射与三份输入哈希。旧版仍可经 `GET /api/runs/{base_run_id}/export` 单独追回。
- `GET /revisions/{id}` 裁决页面：新旧峰窗、住户金额与未分配量差额、采用依据、发布闸门并列对照。

行号从 1 开始，按各 JSON 数组的位置计。归档键由项目、规则版本、来源名和规范化输入 JSON 计算。输入摘要为规范化 JSON 的 SHA-256。耗时与生成时刻只在首次提交时落库，便于重启后比较同一份记录。修订键为 `SHA-256(["revision", base_run_id, 规范化更正])`。
