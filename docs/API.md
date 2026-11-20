# 接口与证据

- `GET /api/health` 返回项目和规则版本。
- `GET /api/{模块}/{样例}` 单独计算到该阶段。模块与样例见深度登记。
- `POST /api/runs` 接收 `{"sample":"clean"}`、`{"sample":"dirty"}` 或 `{"data":{…}}`，返回完整计算和归档 ID。
- `GET /api/runs/{id}` 查询不可变归档。`POST /api/runs/{id}/rerun` 用归档输入与当前规则运行。相同规则与来源复用原记录。
- `GET /api/runs/{id}/export` 下载 JSON 证据。内含批次设置、各输入表、原行号、各阶段计算及规则版本。

行号从 1 开始，按各 JSON 数组的位置计。归档键由项目、规则版本、来源名和规范化输入 JSON 计算。输入摘要为规范化 JSON 的 SHA-256。耗时与生成时刻只在首次提交时落库，便于重启后比较同一份记录。
