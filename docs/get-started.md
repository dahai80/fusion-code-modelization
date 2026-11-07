---
doc_id: fusion-code-modelization/get-started
product: fusion-code-modelization
class: app
entry: service
doc_type: get-started
title: {zh: "Fusion-Code-Modelization 快速上手", en: "Fusion-Code-Modelization Get Started"}
audience: engineer
status: draft
version: 0.7.5
updated: 2026-11-07
owner: "@dahai"
source_of_truth:
  - README.md
  - start.sh
  - pyproject.toml
---

# Fusion-Code-Modelization 快速上手 / Get Started

前置条件：Python >= 3.12；fusion-gateway 在 `:11432` 运行（fusion-mlx 已挂载）；仓库根 venv 已激活。

## 1. 安装

```bash
cd /Users/dahai/fusion
pip install -e fusion-code-modelization
```

确认点：`fusion-code-modelization version` 输出 `0.7.5`。

## 2. 第一次 CLI 运行（不依赖网关的部分）

```bash
cd /path/to/any/target-repo
fusion-code-modelization analyze . --output analyze-report.json
```

确认点：生成 `analyze-report.json`，内含依赖图数据。`analyze` 的静态部分离线可跑。

## 3. 启动 REST API 服务

```bash
/Users/dahai/fusion/fusion-code-modelization/start.sh start
```

确认点：日志输出 `healthy (pid ...)`；`curl -sf http://127.0.0.1:11459/health` 返回 200。进程标题为 `fusion-code-modelization serve :11459`。

## 4. 发起一次会话（要求网关在线）

```bash
curl -s http://127.0.0.1:11459/api/sessions -X POST -H 'Content-Type: application/json' -d '{"name": "demo"}'
```

确认点：返回带 `session_id` 的 JSON。随后 `POST /api/sessions/{session_id}/chat` 与 LLM 交互。网关不可达时 chat 报错——这是预期失败路径，检查 `FUSION_GATEWAY_URL`。

## 5. 跑测试套件

```bash
cd /Users/dahai/fusion/fusion-code-modelization
python -m pytest tests/ -q        # addopts 默认 -m 'not live'
```

确认点：离线套件全绿。`live` 标记的用例需要真实 fusion-gateway，显式 `-m live` 才运行。

## 6. 校验文档契约

```bash
python3 ci/validate_docs.py --root . --product fusion-code-modelization --class app --entry service
```

确认点：输出 `ERROR 0`。

## 常用运维

```bash
start.sh status     # pid + health
start.sh log -f     # follow stdout/stderr
start.sh stop       # graceful stop, SIGKILL after 10s
```

## 下一步

- 端点细节：`docs/api-reference.md`
- 环境变量：`docs/config-reference.md`
- 故障排查：`docs/troubleshooting.md`
