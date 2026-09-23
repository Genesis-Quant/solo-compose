# Solo Compose

Solo 个人量化研究工作台的部署仓库，通过 Git submodule 固定各组件版本。

| 目录 | 仓库 |
| --- | --- |
| `backend` | [solo-backend](https://github.com/Genesis-Quant/solo-backend) |
| `frontend` | [solo-frontend](https://github.com/Genesis-Quant/solo-frontend) |
| `jupyter` | [solo-jupyter](https://github.com/Genesis-Quant/solo-jupyter) |
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

复制 `.env.example` 为 `.env`，填写 PostgreSQL 账号、密码和 `JUPYTER_TOKEN`。首次启动还需生成 Jupyter 凭据库密钥（PowerShell）：

```powershell
New-Item -ItemType Directory -Force .secrets | Out-Null
if (-not (Test-Path .secrets/jupyter-keyring-password)) {
    $keyringPassword = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText((Join-Path $PWD '.secrets/jupyter-keyring-password'), $keyringPassword)
}
```

如构建需要代理，在 `.env` 中设置 `BUILD_HTTP_PROXY`、`BUILD_HTTPS_PROXY`，例如 `http://host.docker.internal:7897`。Jupyter 运行代理使用独立的 `JUPYTER_HTTP_PROXY`、`JUPYTER_HTTPS_PROXY`，默认留空。然后在根目录执行：

```bash
docker compose up -d --build --wait
```

- 前端：<http://127.0.0.1:5174>
- 后端文档：<http://127.0.0.1:8010/docs>
- 健康检查：<http://127.0.0.1:8010/health>
- Jupyter：<http://127.0.0.1:8888/lab>，使用根目录 `.env` 中的 `JUPYTER_TOKEN` 登录。

当前根目录 Compose 统一启动 Backend、Frontend 和 Jupyter，使用 Solo 自己的 Docker 网络。前端使用固定报告示例；后端为基础骨架。DolphinScheduler Worker 尚未部署。

## 共享目录

| Docker 命名卷 | 容器路径 | 用途 | 挂载服务 |
| --- | --- | --- | --- |
| `solo_solo-projects` | `/shared/projects` | 研究项目源码、Notebook、项目 uv 环境 | Backend、Jupyter，均可读写 |
| `solo_solo-runs` | `/shared/runs` | 按运行 ID 保存报告 Parquet 和其他运行输出 | Backend、Jupyter，均可读写 |
| `solo_jupyter-keyrings` | `/home/jovyan/.local/share/keyrings` | 加密凭据库 | Jupyter |
| `solo_codex-home` | `/home/jovyan/.codex` | Codex 配置和登录状态 | Jupyter |

Backend 和 Jupyter 统一使用 `SOLO_SHARED_DIR=/shared`。Jupyter 文件浏览器根目录为 `/shared`，项目链接使用 `/lab/tree/projects/<项目目录>`。Frontend 通过 Backend 获取报告，不直接挂载共享卷。后续 Worker 应挂载同一个 `solo_solo-runs` 卷到 `/shared/runs`，由 Runtime 写出报告。

Jupyter 使用镜像自带的 `CHOWN_HOME`、`CHOWN_EXTRA` 在启动时设置卷归属，Backend 等待 Jupyter 健康后启动；两个服务的业务进程均使用 UID 1000、GID 100，无独立初始化服务。命名卷保存在 Docker Desktop 的 Linux 文件系统中，适合项目虚拟环境；不是 Windows 源码目录的映射。Jupyter 配置仍由 `jupyter/config` 持久化。

`docker compose down` 保留数据，`docker compose down -v` 会删除上述命名卷。备份加密凭据库时同时保存 `.secrets/jupyter-keyring-password`，已有密钥不要重新生成。`.env` 和 `.secrets` 均不提交到 Git。

验证共享目录（宿主机 Python 3.10+，仅使用标准库）：

```bash
python scripts/check_shared.py
```

脚本以 UID 1000 验证双向文件和 Parquet 读写，并验证 Jupyter Contents API，结束后清理测试文件。加 `--recreate` 会重建 Backend 和 Jupyter，再检查数据仍在；重建会结束现有 Notebook 内核。

## 更新组件

在子仓库中提交并推送改动后，再在本仓库提交对应 submodule 的版本指针。嵌套的 `scheme` 改动需依次推送 `scheme`、`algos` 和本仓库。
