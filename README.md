# 分表需量分账盘

园区计量人员从网关取样核实园区共同峰，按相同时间窗口计算分表贡献，并核对住户账单、未分配量及异常证据。

```sh
docker compose up --build
```

访问 `http://127.0.0.1:18451`。点选「园区找峰」图下时间查看该窗原始读数。切换到脏样例，08:30 的总表峰因分表缺样被排除，08:45 成为共同峰。在「住户分摊」对比各表独立峰和共同峰贡献，保存账单证据后可下载归档。

`docker compose exec -T app pytest -q` 运行测试。命名卷 `records` 保存归档。宿主可用 `DB_PATH` 指定 SQLite 文件，安装 `requirements.txt` 后执行 `uvicorn app.main:app --port 18451`。

- [七个模块与陷阱](docs/DEPTH.md)
- [计量字段、单位和时间](docs/DATA-DICTIONARY.md)
- [接口与证据](docs/API.md)
