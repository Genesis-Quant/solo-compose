# Solo Compose

Solo 个人量化研究工作台的部署仓库，通过 Git submodule 固定各组件版本。

| 目录 | 仓库 |
| --- | --- |
| `backend` | [solo-backend](https://github.com/Genesis-Quant/solo-backend) |
| `frontend` | [solo-frontend](https://github.com/Genesis-Quant/solo-frontend) |
| `backtest` | [backtest](https://github.com/Genesis-Quant/backtest) |
| `algos` | [solo-algos](https://github.com/Genesis-Quant/solo-algos) |
| `algos/scheme` | [solo-algo-scheme](https://github.com/Genesis-Quant/solo-algo-scheme)，由 `algos` 管理 |

## 获取代码

```bash
git clone --recurse-submodules https://github.com/Genesis-Quant/solo-compose.git
cd solo-compose
```

已有工作区更新到仓库固定的组件版本：

```bash
git pull --ff-only
git submodule update --init --recursive
```

## 本地运行

使用 Docker Desktop / WSL2。连接本机现有 PostgreSQL 容器，提前创建 `solo`、`solo_ds` 数据库并配置访问账号。

复制 `.env.example` 为 `.env`，填写 PostgreSQL 账号和密码后执行：

```bash
docker compose up -d --build
```

- 前端：<http://127.0.0.1:5174>
- 后端文档：<http://127.0.0.1:8010/docs>
- 健康检查：<http://127.0.0.1:8010/health>

当前 Compose 包含 Backend 和 Frontend。前端使用固定报告示例；后端为基础骨架。Jupyter、DolphinScheduler Worker 和研究输出共享目录尚未接入部署。

在子仓库中提交并推送改动后，再在本仓库提交对应 submodule 的版本指针。嵌套的 `scheme` 改动需依次推送 `scheme`、`algos` 和本仓库。
